# MiniMax 搜索与图像理解参考文档概要

## 必要环境变量

需要配置 `MINIMAX_CP_API_KEY`（从 Coding Plan 订阅页获取），以及可选的 `MINIMAX_CP_BASE_URL`（国内默认 api.minimaxi.com，国际设为 api.minimax.io）。

## 请求头

所有请求需包含三项 Header：Authorization（Bearer Token）、Content-Type（application/json）、MM-API-Source（Minimax-MCP）。

## 两种 API 端点

1. **搜索服务**：POST 到 `/v1/coding_plan/search`，JSON body 格式为 `{"q": "搜索关键词"}`
2. **图像理解**：POST 到 `/v1/coding_plan/vlm`，支持两种图片传入方式——直接使用 URL（`image_url` 字段）或 Base64 编码本地文件（格式为 `data:image/jpeg;base64,xxx`）

## 安全注意事项

切勿在终端输出、日志或回复中打印 API Key 的值。
