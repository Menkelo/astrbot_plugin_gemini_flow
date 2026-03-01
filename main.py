import asyncio
import base64
import io
import json
import re
import aiohttp
from typing import Any, List, Tuple, Optional

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

from astrbot import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star
from astrbot.core.message.components import At, Image, Reply, Plain
from astrbot.core.platform.astr_message_event import AstrMessageEvent


class Main(Star):
    """Gemini Flow 绘图插件"""

    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self._http_session = None

        if PILImage is None:
            logger.warning("[GeminiFlow] ⚠️ 缺少 Pillow 依赖，图片自动旋转功能可能失效。")

    async def initialize(self):
        self._http_session = aiohttp.ClientSession()
        if not self.config.get("flow_api_url"):
            logger.warning("[GeminiFlow] 未配置 Flow API URL")
        logger.info("[GeminiFlow] 插件已激活")

    async def terminate(self):
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    # ================== 图片处理 ==================

    def _get_bot(self, event: AstrMessageEvent):
        if hasattr(event, "bot") and event.bot:
            return event.bot
        try:
            return self.context.get_bot()
        except Exception:
            return None

    def _standardize_image(self, image_data: bytes) -> bytes:
        if not PILImage:
            return image_data
        try:
            img = PILImage.open(io.BytesIO(image_data))
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                bg = PILImage.new("RGB", img.size, (255, 255, 255))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

            max_side = 1536
            if max(img.size) > max_side:
                ratio = max_side / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, PILImage.Resampling.LANCZOS)

            out_io = io.BytesIO()
            img.save(out_io, format="JPEG", quality=90)
            return out_io.getvalue()
        except Exception as e:
            logger.warning(f"[GeminiFlow] 图片标准化失败: {e}")
            return image_data

    async def _download_image(self, url: str) -> bytes | None:
        if url.startswith("data:image"):
            try:
                header, encoded = url.split(",", 1)
                return base64.b64decode(encoded)
            except Exception:
                return None

        timeout = self.config.get("timeout", 60)

        try:
            if not self._http_session or self._http_session.closed:
                self._http_session = aiohttp.ClientSession()
            headers = {"User-Agent": "Mozilla/5.0"}
            async with self._http_session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                if len(data) < 100:
                    return None
                return data
        except Exception:
            return None

    async def get_images(self, event: AstrMessageEvent) -> List[bytes]:
        # 1. 获取当前消息中的图片（作为后续图片）
        current_msg_imgs = []
        for comp in event.message_obj.message:
            if isinstance(comp, Image) and comp.url:
                current_msg_imgs.append(comp.url)

        for comp in event.message_obj.message:
            if isinstance(comp, At):
                target_id = getattr(comp, "qq", None) or getattr(comp, "id", None) or getattr(comp, "user_id", None)
                if target_id:
                    current_msg_imgs.append(f"https://q1.qlogo.cn/g?b=qq&nk={target_id}&s=640")

        # 2. 获取引用消息中的图片（作为图1）
        reply_msg_imgs = []
        reply_id = None
        for comp in event.message_obj.message:
            if isinstance(comp, Reply):
                reply_id = comp.id

        # 无论当前消息是否有图，都尝试获取引用消息的图片
        if reply_id:
            bot = self._get_bot(event)
            if bot:
                try:
                    resp = await bot.api.call_action("get_msg", message_id=int(reply_id))
                    if resp and "message" in resp:
                        content = resp["message"]
                        if isinstance(content, list):
                            for seg in content:
                                if isinstance(seg, dict) and seg.get("type") == "image":
                                    u = seg.get("data", {}).get("url") or seg.get("data", {}).get("file")
                                    if u and str(u).startswith("http"):
                                        reply_msg_imgs.append(u)
                        elif isinstance(content, str):
                            urls = re.findall(r"url=(http[^,\]]+)", content)
                            reply_msg_imgs.extend([u.replace("&amp;", "&") for u in urls])
                            if not urls:
                                urls = re.findall(r"file=(http[^,\]]+)", content)
                                reply_msg_imgs.extend([u.replace("&amp;", "&") for u in urls])
                except Exception:
                    pass

        # 3. 拼接：引用图片在前，当前消息图片在后
        all_img_urls = reply_msg_imgs + current_msg_imgs

        final_images = []
        for url in all_img_urls:
            raw_data = await self._download_image(url)
            if raw_data:
                final_images.append(self._standardize_image(raw_data))
        return final_images

    def _bytes_to_base64(self, data: bytes) -> str:
        return f"data:image/jpeg;base64,{base64.b64encode(data).decode()}"

    def _extract_ratio(self, text: str) -> Tuple[str, Optional[str]]:
        # 先识别更具体的比例，避免与“横屏/竖屏”冲突
        aspect_patterns = [
            ("square", [r"1[:：]1", r"正方形", r"方图", r"square"]),
            ("four-three", [r"4[:：]3", r"四[:：]三", r"four[-_ ]?three"]),
            ("three-four", [r"3[:：]4", r"三[:：]四", r"three[-_ ]?four"]),
            ("portrait", [r"9[:：]16", r"2[:：]3", r"1[:：]2", r"竖屏", r"竖版", r"portrait"]),
            ("landscape", [r"16[:：]9", r"3[:：]2", r"2[:：]1", r"横屏", r"横版", r"landscape"]),
        ]

        target_aspect = None
        for aspect, keywords in aspect_patterns:
            matched = False
            for kw in keywords:
                pattern = re.compile(kw, re.IGNORECASE)
                if pattern.search(text):
                    target_aspect = aspect
                    text = pattern.sub("", text)
                    matched = True
                    break
            if matched:
                break

        text = re.sub(r",\s*,", ",", text).strip(" ,")
        return text, target_aspect

    def _replace_model_aspect(self, model_name: str, aspect: str) -> str:
        """将模型后缀替换为指定比例后缀"""
        if aspect not in {"landscape", "portrait", "square", "four-three", "three-four"}:
            return model_name
        return re.sub(
            r"-(landscape|portrait|square|four-three|three-four)$",
            f"-{aspect}",
            model_name
        )

    def _infer_aspect_from_image(self, image_data: bytes) -> Optional[str]:
        """根据首图宽高比推断最接近的模型比例后缀"""
        if not PILImage or not image_data:
            return None
        try:
            img = PILImage.open(io.BytesIO(image_data))
            if img.height == 0:
                return None

            ratio = img.width / img.height
            target_ratios = {
                "landscape": 16 / 9,
                "portrait": 9 / 16,
                "square": 1.0,
                "four-three": 4 / 3,
                "three-four": 3 / 4,
            }
            return min(target_ratios, key=lambda k: abs(ratio - target_ratios[k]))
        except Exception:
            return None

    async def _call_flow_api(
        self,
        images: List[bytes],
        prompt: str,
        model_name: str,
        orientation: str = None
    ) -> Tuple[bool, Any]:
        api_url = self.config.get("flow_api_url", "").strip()
        api_key = self.config.get("flow_api_key")
        if not api_url or not api_key:
            return False, "API配置缺失"

        # 自动补全 URL 后缀
        if not api_url.endswith("chat/completions"):
            api_url = api_url.rstrip("/") + "/v1/chat/completions"

        model = model_name

        # 显式比例优先，否则根据首图推断
        if orientation in {"landscape", "portrait", "square", "four-three", "three-four"}:
            model = self._replace_model_aspect(model, orientation)
        else:
            if images:
                inferred_aspect = self._infer_aspect_from_image(images[0])
                if inferred_aspect:
                    model = self._replace_model_aspect(model, inferred_aspect)

        content = [{"type": "text", "text": prompt}]
        for img_bytes in images:
            content.append({"type": "image_url", "image_url": {"url": self._bytes_to_base64(img_bytes)}})

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "stream": True
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        last_error = ""
        for attempt in range(3):
            try:
                if not self._http_session or self._http_session.closed:
                    self._http_session = aiohttp.ClientSession()

                async with self._http_session.post(api_url, json=payload, headers=headers, timeout=120) as resp:
                    if resp.status in [400, 401, 403, 404]:
                        return False, f"API Error {resp.status}: {await resp.text()}"

                    if resp.status != 200:
                        logger.warning(f"[GeminiFlow] API {resp.status}，重试 ({attempt + 1}/3)...")
                        last_error = f"API Error {resp.status}"
                        await asyncio.sleep(1)
                        continue

                    full_content = ""
                    async for line in resp.content:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                if "choices" in chunk and chunk["choices"]:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        full_content += delta["content"]
                            except Exception:
                                pass

                    if not full_content:
                        logger.warning(f"[GeminiFlow] 返回内容为空，重试 ({attempt + 1}/3)...")
                        last_error = "API返回内容为空"
                        await asyncio.sleep(1)
                        continue

                    logger.info(f"[GeminiFlow] Full Response: {full_content[:100]}...")

                    url_match = re.search(r'https?://[^\s<>")\]]+', full_content)
                    if url_match:
                        img_url = url_match.group(0)
                        dl_res = await self._download_image(img_url)
                        if dl_res:
                            return True, dl_res
                        return False, f"图片下载失败: {img_url}"

                    return False, f"无图片URL，内容: {full_content[:100]}"

            except Exception as e:
                logger.warning(f"[GeminiFlow] 请求异常: {e}，重试 ({attempt + 1}/3)...")
                last_error = str(e)
                await asyncio.sleep(1)

        return False, f"重试3次失败: {last_error}"

    async def _process_generation(
        self,
        event: AstrMessageEvent,
        prompt: str,
        images: List[bytes],
        preset_name: str = None,
        has_extra: bool = False,
        orientation: str = None
    ):
        target_model = self.config.get("model", "gemini-3.0-pro-image-landscape")

        async def run():
            task_type = "图生图" if images else "文生图"
            status_msg = "🎨正在绘图"
            if preset_name:
                status_msg += f"「预设：{preset_name}」"
            if has_extra:
                status_msg += "(已衔接额外提示词)"

            aspect_label_map = {
                "portrait": "竖屏",
                "landscape": "横屏",
                "square": "1:1",
                "four-three": "4:3",
                "three-four": "3:4",
            }
            if orientation in aspect_label_map:
                status_msg += f" [{aspect_label_map[orientation]}]"

            status_msg += "..."
            yield event.plain_result(status_msg)

            success, result = await self._call_flow_api(images, prompt, target_model, orientation)
            if success:
                try:
                    comp = Image.fromBytes(result)
                except Exception:
                    comp = Image.fromBase64(base64.b64encode(result).decode())

                footer_text = f"{task_type}成功"
                yield event.chain_result([comp, Plain(footer_text)])
            else:
                yield event.plain_result(f"❌ 失败: {result}")

        async for r in run():
            yield r

    @filter.command("flow")
    async def cmd_flow(self, event: AstrMessageEvent):
        """
        Flow 绘图指令
        """
        prompt_parts = []
        for comp in event.message_obj.message:
            if isinstance(comp, Plain):
                prompt_parts.append(comp.text)

        full_text = "".join(prompt_parts).strip()
        logger.info(f"[GeminiFlow] 提取的纯文本: '{full_text}'")

        prompt = full_text
        if " " in full_text:
            first_word, rest = full_text.split(" ", 1)
            if first_word.startswith("/") or first_word.startswith("！") or first_word.startswith("!"):
                prompt = rest.strip()
        elif full_text.startswith("/") or full_text.startswith("！") or full_text.startswith("!"):
            prompt = ""

        logger.info(f"[GeminiFlow] 最终用于匹配的提示词: '{prompt}'")

        images = await self.get_images(event)

        preset_name = None
        has_extra = False
        raw_preset_text = ""
        raw_extra_text = ""

        # ============ 1. 预设解析 ============
        if prompt:
            preset_hub = getattr(self.context, "preset_hub", None)
            matched = False

            if preset_hub and hasattr(preset_hub, "get_all_keys"):
                all_keys = preset_hub.get_all_keys()
                all_keys.sort(key=len, reverse=True)

                prompt_lower = prompt.lower()

                for key in all_keys:
                    key_lower = key.lower()
                    if prompt_lower == key_lower or prompt_lower.startswith(key_lower + " "):
                        preset_val = preset_hub.resolve_preset(key)
                        if preset_val:
                            preset_name = key
                            raw_preset_text = preset_val
                            raw_extra_text = prompt[len(key):].strip()
                            if raw_extra_text:
                                has_extra = True
                            matched = True
                            logger.info(f"[GeminiFlow] ✅ 命中预设: [{key}]")
                            break

            if not matched:
                raw_preset_text = ""
                raw_extra_text = prompt

        # ============ 2. 头像自动抓取 ============
        if preset_name and not images:
            user_id = event.get_sender_id()
            if user_id:
                logger.info(f"[GeminiFlow] 触发预设 [{preset_name}] 且无图，自动使用用户头像 I2I")
                avatar_url = f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
                raw_data = await self._download_image(avatar_url)
                if raw_data:
                    images.append(self._standardize_image(raw_data))

        # ============ 3. 比例解析 ============
        orient_preset = None
        if raw_preset_text:
            raw_preset_text, orient_preset = self._extract_ratio(raw_preset_text)

        orient_extra = None
        if raw_extra_text:
            raw_extra_text, orient_extra = self._extract_ratio(raw_extra_text)

        final_orientation = orient_extra if orient_extra else orient_preset

        # ============ 4. 拼接 ============
        final_prompt = ""
        if preset_name:
            if raw_extra_text:
                final_prompt = f"{raw_preset_text}, {raw_extra_text}"
            else:
                final_prompt = raw_preset_text
        else:
            final_prompt = raw_extra_text

        # ============ 5. 执行 ============
        if images:
            if not final_prompt:
                final_prompt = "make it better"
            async for r in self._process_generation(
                event, final_prompt, images, preset_name, has_extra, final_orientation
            ):
                yield r
        else:
            if not final_prompt:
                yield event.plain_result("❌ 请输入描述\n用法: /flow 一只猫 或 /flow 二次元")
                return
            async for r in self._process_generation(
                event, final_prompt, images, preset_name, has_extra, final_orientation
            ):
                yield r
