# MiniMax Search & Image Understanding Skill

## Skill Definition
- **Name**: minimax-search-vlm
- **Purpose**: Enables web search and image understanding via MiniMax Coding Plan API

## Configuration Required
- `MINIMAX_CP_API_KEY` - API key starting with `sk-cp-`, obtained from Coding Plan subscription page
- `MINIMAX_CP_BASE_URL` - Optional; defaults to `https://api.minimaxi.com` (domestic) or set to `https://api.minimax.io` (international)

## Capability 1: Web Search
- **Endpoint**: `POST {base}/v1/coding_plan/search`
- **Headers**: Authorization (Bearer token), Content-Type: application/json, MM-API-Source: Minimax-MCP
- **Body**: `{"q": "search query"}`

## Capability 2: Image Understanding
- **Endpoint**: `POST {base}/v1/coding_plan/vlm`
- **Headers**: Same as above
- **Body**: `{"prompt": "question", "image_url": "url or base64 data"}`
- Supports two image URL formats: direct public URL or Base64-encoded local file (`data:image/jpeg;base64,...`)

## Security Requirements
- Never print, echo, log, or display API keys or environment variable values in outputs, logs, or replies
- Keys are used only in request headers, never exposed to users

## Usage Notes
Keys must be exported before use: `export MINIMAX_CP_API_KEY="your_key"`

All curl examples and detailed reference material available in companion documentation.
