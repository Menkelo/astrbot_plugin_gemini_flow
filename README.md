# Gemini Flow 绘图插件

基于 [Flow2API](https://github.com/TheSmallHanCat/flow2api) 的绘图插件，支持文生图/图生图、全局预设、自动比例模型切换

---

## ✨ 功能特点

- 🎨 **Flow API 支持**：专为 Flow 格式接口设计（如 Gemini Image）。
- 🖼️ **文生图 / 图生图**：支持纯文本生成，也支持带图编辑。
- 📐 **智能比例适配**：
  - 支持显式比例关键词：`landscape` / `portrait` / `square` / `four-three` / `three-four`
  - 支持中文关键词：`横屏`、`竖屏`、`方图`、`4:3`、`3:4` 等
  - 未指定比例时，图生图会根据首图宽高自动匹配最接近模型比例
- 🧩 **预设联动**：可对接全局预设 [astrbot_plugin_preset_hub](https://github.com/Menkelo/astrbot_plugin_preset_hub)，统一使用预设库。
- 📦 **图片标准化**：自动进行格式转换、透明底处理、尺寸压缩。
- 👤 **@用户头像输入**：可将 @ 的用户头像作为图生图输入。
- 🔁 **引用图片优先**：支持读取回复消息中的图片作为第一张输入图。

---

## ⚙️ 配置项

### 必填

- `flow_api_url`：Flow2API 服务地址  
  例如：`http://127.0.0.1:8000`  
  （插件自动补全 `/v1/chat/completions`）

- `flow_api_key`：API Key

### 模型 `model`（已更新）

当前可选模型：

- `gemini-3.0-pro-image-landscape`
- `gemini-3.0-pro-image-portrait`
- `gemini-3.0-pro-image-square`
- `gemini-3.0-pro-image-four-three`
- `gemini-3.0-pro-image-three-four`
- `gemini-3.1-flash-image-landscape`
- `gemini-3.1-flash-image-portrait`
- `gemini-3.1-flash-image-square`
- `gemini-3.1-flash-image-four-three`
- `gemini-3.1-flash-image-three-four`

默认值：`gemini-3.0-pro-image-landscape`

> 插件会根据提示词中的比例关键词（或首图比例）自动替换模型后缀以达到自动切换比例的效果。

---

## 🧪 指令用法

### 基础文生图

```text
/flow 一只赛博朋克风格的猫
```

### 指定比例

```text
/flow 未来城市夜景 横屏
/flow 可爱头像 竖屏
/flow logo设计 1:1
/flow 游戏封面 4:3
/flow 角色立绘 3:4
```

### 图生图（带图）

- 直接发送图片 + `/flow 提示词`
- 或回复一张图片后发送 `/flow 提示词`

无额外提示词时，默认使用：`make it better`

### 预设联动（如果已安装 preset_hub）

```text
/flow 异画 蓝色背景
/flow 预设名 额外提示词
```

- 命中预设后，会自动将“预设内容 + 额外提示词”拼接发送。
- 当命中预设且未带图时，会自动尝试使用发送者头像作为输入图。

---

## 📝 依赖

`requirements.txt`：

```txt
aiohttp>=3.8.0
Pillow>=9.0.0
```

---

## ❗注意事项

- 请确保 Flow2API 端支持所选模型名称。
- 如未安装 Pillow，插件仍可运行，但图片标准化能力会受限。
- 若返回中无图片 URL，插件会提示“无图片URL”并输出部分返回内容便于排查。
