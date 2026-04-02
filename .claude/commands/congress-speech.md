# /congress-speech — Congressional Speech Multi-Agent Analysis

六层并行 + 一层仲裁的国会演讲分析架构。

## 使用方式

```
/congress-speech [Trump演讲文本...]
```

粘贴Trump演讲文本即可自动分析。

## 架构

```
演讲文本
    │
    ├──▶ Agent A: 语言分析师      → 词汇/语气/修辞解码
    ├──▶ Agent B: 事实核查员      → 声明可信度评分
    ├──▶ Agent C: 情景预测师      → 三情景概率分布
    ├──▶ Agent D: 投资策略师      → EV计算 + 仓位建议
    └──▶ Agent E: 魔鬼代言人      → 挑战所有结论
            │
            ▼
    Agent F: 仲裁者（Delphi轮）  → 综合评分 + 最终备忘录
```

## 执行流程

### Step 1: 创建团队

```python
TeamCreate("congress-speech-{timestamp}")
```

### Step 2: 创建任务

```python
TaskCreate("Agent A: Language Analysis")
TaskCreate("Agent B: Fact Check")
TaskCreate("Agent C: Scenario Probability")
TaskCreate("Agent D: Investment EV")
TaskCreate("Agent E: Devil's Advocate")
TaskCreate("Agent F: Delphi Synthesis")
```

### Step 3: 并行启动 Stage 1 (A, B, C)

```python
Agent(name="agent-A", team="congress-speech", task=1)
Agent(name="agent-B", team="congress-speech", task=2)
Agent(name="agent-C", team="congress-speech", task=3)
```

### Step 4: 串行 D (依赖 C 的概率)

收到 C 的输出后，发送概率给 D：
```python
SendMessage(to="agent-D", message=C_probabilities)
```

### Step 5: E 攻击所有 (依赖 A, B, C, D)

收到所有输出后转发给 E：
```python
SendMessage(to="agent-E", message={A, B, C, D})
```

### Step 6: F 综合仲裁 (Delphi)

```python
SendMessage(to="agent-F", message={A, B, C, D, E})
```

### Step 7: 输出最终备忘录

```python
# 打印并保存
reports/congress_analysis/{speech_id}_FINAL_MEMO.json
```

## 三情景框架

| 情景 | 定义 | 典型时间 |
|------|------|---------|
| A: 快速解决 | 2周内停火撤离 | 7-14天 |
| B: 僵局 | 无重大升级，谈判持续 | 30-90天 |
| C: 升级 | 基础设施打击，战事蔓延 | 30+天 |

## 输出格式

```json
{
  "speech_id": "CONGRESS_YYYYMMDD_N",
  "confidence_score": 72,
  "core_judgment": "TACO概率63%",
  "scenario_probabilities": {
    "A_fast_resolution": 0.29,
    "B_stalemate": 0.34,
    "C_escalation": 0.37
  },
  "final_trades": [
    {"asset": "GLD", "direction": "LONG", "size": 0.03}
  ],
  "compliance": {"passes": true, "cash_reserve": 0.93}
}
```

## 演讲文本示例

```
/congress-speech 炸回石器时代！我们将对伊朗实施最严厉的制裁。然而，我也要宣布：我们将在2-3周内撤军，即便霍尔木兹海峡没有完全重新开放。给伊朗一个体面的退出机制。如果他们愿意谈判，我们可以达成协议。
```

## 数据获取协议

所有 Agent 必须遵循 **web-search-fallback** skill 的 6 级降级搜索协议：

```
Level 1: MCP Playwright (Google/X.com) — HIGHEST PRIORITY
Level 2: Brave Search API
Level 3: minimax WebSearch
Level 4: Alternative query reformulation
Level 5: Knowledge Base fallback
Level 6: Annotate "DATA INSUFFICIENT"
```

**API Key**: Brave Search API Key 已配置于 `settings.json`

### 数据获取流程

1. **Stage 1 启动前**: 运行 `python scripts/fetch_speech_context.py` 获取市场数据
2. **Agent B (Fact Checker)**: 对每个声明执行 L1 → L2 → L3 → L4 → L5 → L6 降级搜索
3. **Agent C (Scenario Forecaster)**: 读取 `data/market_snapshot.json` 获取 VIX/原油/SPY 数据
4. **Agent D (Investment Strategist)**: 读取 `data/market_snapshot.json` 获取当前价格

### 缓存策略

- 搜索结果缓存至 `data/speech_search_cache.json`
- 缓存 key: `md5(speech_id + claim[:200])`
- 缓存 TTL: 24 小时

### 数据源标注

所有输出必须包含数据来源层级：
```json
{
  "data_source": "L1",
  "data_source_detail": "MCP Playwright Google search — no confirmed reports",
  "cache_hit": false
}
```

## 协调规则

1. **Stage 1 并行**: A, B, C 同时运行，互不依赖
2. **Stage 2 串行**: D 等待 C 完成
3. **Stage 3 串行**: E 等待 A, B, C, D 完成
4. **Stage 4 串行**: F 等待所有 Agent 完成
5. **消息转发**: 每个 Agent 完成后通过 SendMessage 汇报
6. **任务状态**: 用 TaskUpdate 更新任务状态
7. **关闭**: 所有完成后关闭团队，TeamDelete
