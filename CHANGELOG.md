## [1.6.0] - 2026-03-01

### Added
- 新增模型支持：
  - gemini-3.0-pro-image-landscape
  - gemini-3.0-pro-image-portrait
  - gemini-3.0-pro-image-square
  - gemini-3.0-pro-image-four-three
  - gemini-3.0-pro-image-three-four
  - gemini-3.1-flash-image-landscape
  - gemini-3.1-flash-image-portrait
  - gemini-3.1-flash-image-square
  - gemini-3.1-flash-image-four-three
  - gemini-3.1-flash-image-three-four
- 比例关键词扩展：支持 `square / four-three / three-four` 及对应中文写法（如 `方图`、`4:3`、`3:4`）。

### Changed
- `_conf_schema.json` 的模型下拉选项已替换为新模型列表。
- `main.py` 的模型比例切换逻辑升级：支持 `landscape / portrait / square / four-three / three-four`。
- 图生图在未显式指定比例时，会根据首图宽高比自动匹配最接近模型比例。
- 状态提示文案增加比例显示（如 `[1:1]`、`[4:3]`、`[3:4]`）。

### Removed
- 移除旧模型选项（gemini-2.5-flash-image-*）。
