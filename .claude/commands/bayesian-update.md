# /bayesian-update — Bayesian Reversal Probability Update

注入信号到贝叶斯更新引擎，实时计算后验概率 P_t。

## 核心概念

```
Five-Factor P₀ (静态先验)
    ↓
BayesianReversalUpdater.update_sequence(P₀, signals)
    ↓
P_t (实时后验概率)
```

- **P₀**: 来自 Five-Factor 模型，作为初始先验
- **P_t**: 注入信号后实时更新的后验概率
- **LR**: 似然比，控制每次更新的幅度

## 预检查

```bash
python scripts/realtime_monitor.py --help
# 确保 core.bayesian_updater 可导入
python -c "from core.bayesian_updater import BayesianReversalUpdater; print('OK')"
```

## 使用方式

### 注入单个或多个信号

```
/bayesian-update --statement-id TACO-011 --inject-signal trump_extends_deadline
/bayesian-update --statement-id TACO-011 --inject-signal trump_extends_deadline --inject-signal counterparty_hard_rejection
```

### 指定初始先验 P₀

```
/bayesian-update --statement-id TACO-011 --p0 0.332 --inject-signal trump_says_great_progress
```

### 默认信号序列（用于快速评估）

```
/bayesian-update --statement-id TACO-011
# 使用默认信号: [trump_extends_deadline, counterparty_hard_rejection]
```

## 信号类型与 LR 值

### 强反转信号 (LR > 3)

| 信号 | LR | 说明 |
|------|-----|------|
| `trump_says_great_progress` | 8.5 | 特朗普称"进展顺利" |
| `trump_says_they_called_me` | 12.0 | 特朗普称"他们给我打了电话" |
| `trump_signals_deal_imminent` | 7.2 | 暗示即将达成协议 |
| `trump_extends_deadline` | 3.8 | 延长最后期限 |
| `counterparty_symbolic_concession` | 6.5 | 对手象征性让步 |
| `third_party_mediator_enters` | 5.0 | 第三方调解人介入 |

### 弱反转信号 (LR 1.5–3)

| 信号 | LR | 说明 |
|------|-----|------|
| `trump_hedges_language` | 2.3 | 措辞软化 |
| `back_channel_rumor` | 1.8 | 幕后渠道传言 |
| `market_rally_without_catalyst` | 2.1 | 市场无消息上涨 |

### 反 TACO 信号 (LR < 1)

| 信号 | LR | 说明 |
|------|-----|------|
| `counterparty_hard_rejection` | 0.20 | 对手强硬拒绝 |
| `new_harder_statement` | 0.15 | 更强硬声明 |
| `military_action_confirmed` | 0.05 | 军事行动确认 |
| `trump_says_no_deal_possible` | 0.10 | "不可能达成协议" |
| `ally_publicly_opposes_retreat` | 0.35 | 盟友反对退缩 |

## 输出示例

```
Statement: TACO-011 (military)
P₀ (initial prior): 33.2%
Injecting 2 signals: ['trump_extends_deadline', 'counterparty_hard_rejection']

Bayesian Update Result:
  P_t (final posterior): 27.4%
  Delta: -5.8pp

Trajectory:
        t0: initial_estimate                         →   33.2%  (↑  0.0pp, LR=1.00)
    signal: trump_extends_deadline                   →   65.4%  (↑ 32.2pp, LR=3.80)
    signal: counterparty_hard_rejection             →   27.4%  (↓ 38.0pp, LR=0.20)

🚨 TACO MONITOR ALERT: TACO-011
=====================================
**Target:** Iran
**Type:** military
**Current Reversal Probability:** 27.4%
```

## 内部实现

```python
# core/bayesian_updater.py
updater = BayesianReversalUpdater()
trajectory = updater.update_sequence(
    initial_prior=0.332,
    signals=[
        ("Day 2", "trump_extends_deadline"),
        ("Day 3", "counterparty_hard_rejection"),
    ],
    context={"oil_price": 100.6, "gas_price": 3.50}
)
```

## 场景模拟

```bash
# 模拟伊朗危机出现软化信号
python scripts/realtime_monitor.py \
    --statement-id TACO-011 \
    --p0 0.332 \
    --inject-signal trump_extends_deadline \
    --inject-signal counterparty_symbolic_concession

# 模拟更强硬信号（概率大幅下降）
python scripts/realtime_monitor.py \
    --statement-id TACO-011 \
    --p0 0.332 \
    --inject-signal military_action_confirmed

# 模拟谈判进入（先升后降）
python scripts/realtime_monitor.py \
    --statement-id TACO-011 \
    --p0 0.332 \
    --inject-signal third_party_mediator_enters \
    --inject-signal counterparty_hard_rejection
```
