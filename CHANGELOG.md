# [v1.6.0] - Gemini 模型与比例系统升级

* **🧠 模型列表全面更新**
  * 移除旧模型（`gemini-2.5-flash-image-*`）
  * 新增并统一切换到以下模型：
    * `gemini-3.0-pro-image-landscape`
    * `gemini-3.0-pro-image-portrait`
    * `gemini-3.0-pro-image-square`
    * `gemini-3.0-pro-image-four-three`
    * `gemini-3.0-pro-image-three-four`
    * `gemini-3.1-flash-image-landscape`
    * `gemini-3.1-flash-image-portrait`
    * `gemini-3.1-flash-image-square`
    * `gemini-3.1-flash-image-four-three`
    * `gemini-3.1-flash-image-three-four`

* **📐 比例识别能力增强**
  * 从原先仅支持 `landscape / portrait`，扩展为支持：
    * `landscape / portrait / square / four-three / three-four`
  * 支持中文与比例写法识别（如 `横屏`、`竖屏`、`正方形`、`1:1`、`4:3`、`3:4`）
  * 未显式指定比例时，图生图会根据首图宽高自动匹配最接近模型比例

* **⚙️ 配置结构同步更新**
  * `_conf_schema.json` 的模型下拉选项已替换为新模型全集
  * 默认模型更新为：`gemini-3.0-pro-image-landscape`
  * 模型提示文案同步更新为五种比例后缀自动切换说明

* **🖥️ 交互体验优化**
  * 绘图状态提示增加比例标签展示（如 `[1:1]`、`[4:3]`、`[3:4]`）
  * 比例关键词提取顺序优化，避免关键词冲突导致误判
---
<details>
<summary>📋 点击查看历史更新日志</summary>

# [v1.5.0] - 上一稳定版本

* **✨ 功能列表**
  * Flow2API 文生图 / 图生图
  * 全局预设联动（Preset Hub）
  * 引用图与头像图输入支持

# [v1.0.0] - 初始版本

* **🎉 发布**: 插件初始版本发布
* **✨ 功能列表**:
  * 基础绘图能力
  * 插件配置化接入

</details>
