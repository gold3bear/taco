# TACO Investment Intelligence System

**Trump Always Chickens Out** — statement-driven Trump 威胁分析系统

---

## 快速开始

```bash
# 分析当前 Iran 威胁事件
python scripts/run_statement_analysis.py --batch

# 运行完整 Pipeline（Legacy）
python scripts/run_taco_pipeline.py

# 实时监控信号
python scripts/realtime_monitor.py --check-signals "Trump says great progress" --statement-id TACO-011
```

---

## 核心脚本

### 1. Statement Analysis (新架构)

```bash
# 分析所有活跃声明
python scripts/run_statement_analysis.py --batch

# 分析指定声明
python scripts/run_statement_analysis.py --statement-id TACO-011

# 输出 JSON 结果
python scripts/run_statement_analysis.py --batch --output data/statement_analysis.json
```

**输出示例：**
```
TACO-011: military targeting Iran
- Reversal Probability: 44.7%
- Phase 1: SHORT QQQ, 2.5%, hold 1-3 days
- Phase 2: No trade yet — reversal signals required
```

---

### 2. Real-time Monitor

```bash
# 检查文本中的逆转信号
python scripts/realtime_monitor.py --check-signals "Trump says they called me" --statement-id TACO-011

# 持续监控（Daemon 模式）
python scripts/realtime_monitor.py --daemon --poll-interval 300

# 单次循环检查
python scripts/realtime_monitor.py
```

**检测的信号：**

| 信号 | 效果 |
|------|------|
| `trump_says_great_progress` | +25pp |
| `trump_says_they_called_me` | +30pp |
| `trump_says_beautiful_deal` | +35pp |
| `military_action_confirmed` | -45pp |
| `counterparty_hard_rejection` | -20pp |

---

### 3. Legacy Pipeline (`/taco`)

```bash
# 完整 6-agent Pipeline
python scripts/run_taco_pipeline.py

# 单独运行各步骤
python scripts/build_taco_database.py          # TACO Historian
python scripts/run_event_study.py              # Statistical Analyst
python scripts/fetch_iran_context.py           # Context Analyst
python scripts/run_monte_carlo.py              # Scenario Forecaster
python scripts/calc_portfolio_strategy.py      # Investment Strategist
python scripts/generate_taco_charts.py         # 生成图表
```

---

### 4. Five-Factor Backtest

```bash
# 回测模型准确性
python scripts/backtest_five_factor.py

# 包含分类别分析
python scripts/backtest_five_factor.py --by-category

# 输出 JSON 结果
python scripts/backtest_five_factor.py --output reports/backtest_results.json
```

---

### 5. Alert System

```bash
# 添加 Slack webhook
python scripts/alert_system.py add \
    --name my-alert \
    --webhook-url "https://hooks.slack.com/services/..." \
    --platform slack \
    --min-level warning

# 测试 webhook
python scripts/alert_system.py test --webhook-url "https://..."

# 列出已配置的 webhooks
python scripts/alert_system.py list

# 发送测试告警
python scripts/alert_system.py send --level critical --title "Test" --message "Hello"

# 带告警的实时监控
python scripts/integrate_monitor_with_alerts.py --daemon --poll-interval 300 --alert-level warning
```

---

## 数据文件

| 文件 | 用途 |
|------|------|
| `data/statements.json` | Statement 数据库 (14 事件) |
| `data/taco_events.csv` | 事件数据库 (可回测) |
| `data/taco_pattern_bible.json` | 统计规律 |
| `data/iran_context.json` | 当前 Iran 上下文 |
| `data/market_snapshot.json` | 市场快照 |
| `data/polymarket_geopolitics.json` | Polymarket 概率 |

---

## 五因子模型公式

```
P(reversal) = Factor1 × (1 + 0.25×Factor2) × (1 + Factor3) × (1 + Factor4) × (1 + 0.05×Factor5)
```

| 因子 | 权重 | 描述 |
|------|------|------|
| Factor1 | base | 类型基础概率 (TRADE=82%, MILITARY=38%) |
| Factor2 | 25% | 市场疼痛 (VIX>20=1.0, >10=0.7) |
| Factor3 | 20% | 对手信号 (+20% 让步, -25% 硬拒绝) |
| Factor4 | 10% | 国内压力 (油价>$4=+8pp) |
| Factor5 | 5% | Polymarket 校准 |

---

## 双阶段交易

| 阶段 | 触发 | 仓位 | 持仓 | 退出 |
|------|------|------|------|------|
| Phase 1 | 声明发布 | 2-3% | 1-3天 | 疼痛点 OR 3天 |
| Phase 2 | 逆转信号确认 | prob×10%, max 8% | 直到确认 | 确认 OR 5天 |

---

## 声明类型

| 类型 | 基础概率 | 示例 |
|------|----------|------|
| TRADE_TARIFF | 82% | "25% tariffs on Mexico" |
| PERSONNEL | 78% | "Fire Powell" |
| TERRITORIAL | 58% | "Take back Panama Canal" |
| MILITARY | 38% | "Strike Iran" |
| POLICY | 15% | "Tax cuts" |

---

## 关键发现 (2026-04-01)

| 指标 | 值 |
|------|-----|
| Iran TACO 概率 | 31-45% |
| Polymarket 停火概率 | 8.5% |
| Bearish War 情景 | 59% |
| 唯一正 EV 交易 | GLD (黄金) |
| 回测 Brier Score | 0.0554 (好) |

---

## 报告输出

```bash
# 生成投资备忘录
# 编辑 reports/TACO_Investment_Memo.md

# 查看图表
ls reports/charts/
# - taco_event_timeline.png
# - taco_car_window.png
# - scenario_fan_chart.png
# - asset_heatmap.png
# - pain_point_scatter.png
```

---

## API 参考

```python
from models.statement import Statement, StatementType
from models.five_factor import FiveFactorModel
from models.position_calculator import TwoPhasePositionCalculator

# 1. 计算逆转概率
model = FiveFactorModel()
result = model.calculate(
    statement_type=StatementType.MILITARY,
    vix_current=20.0,
    counterparty_signal="survival_stakes",
    gas_price=3.50,
    midterm_months=18,
    market_drawdown=0.0,
    polymarket_prob=0.085,
    nth_similar_threat=1,
    base_return=-1.8,
)
print(f"P(reversal) = {result.probability:.1%}")

# 2. 计算双阶段仓位
calc = TwoPhasePositionCalculator()
two_phase = calc.calculate_two_phase(
    statement_type=StatementType.MILITARY,
    predicted_return=-1.8,
    reversal_probability=0.45,
    vix_current=20.0,
)
print(f"Phase 1: {two_phase.phase1.direction} {two_phase.phase1.asset}")
```

---

## 配置

Alert 配置：`data/alerts_config.json`

```json
{
  "webhooks": [
    {
      "name": "slack-alerts",
      "url": "https://hooks.slack.com/...",
      "platform": "slack",
      "enabled": true,
      "min_level": "warning"
    }
  ]
}
```
