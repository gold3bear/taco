# /garch-timing — GARCH VIX 时机模型

基于 GARCH(1,1) 波动率持续性模型，预测 VIX 何时回落，为交易时机提供信号。

**核心原则**: GARCH 只用于**交易时机**，不参与概率计算。

```
GARCH: 预测波动率何时回落 → 决定 Phase 2 持有期
Five-Factor: 预测反转概率 → 决定是否建仓
```

## 概念说明

### GARCH(1,1) 参数

| 参数 | 典型值 | 说明 |
|------|--------|------|
| α (alpha) | 0.09 | ARCH term：冲击对波动率的影响 |
| β (beta) | 0.87 | GARCH term：波动率持续性 |
| α+β (persistence) | 0.96 | 高度持续，half-life ≈ 17 天 |
| Half-life | ~17 天 | VIX 回落一半所需交易日数 |

### 时机信号 vs 概率信号

| 信号类型 | 用途 | 例子 |
|----------|------|------|
| TACO 信号 | 影响 P(reversal) | `trump_extends_deadline` |
| GARCH 时机 | 影响持仓时长 | VIX half-life 回落 |

## 预检查

```bash
python -c "from core.garch_timing import GARCHTimingModel; print('OK')"
```

## 使用方式

### 估算 VIX 回落时机

```python
from core.garch_timing import GARCHTimingModel

timer = GARCHTimingModel()

# 当前 VIX = 30，半衰期 = 17 天
timing = timer.estimate_reversion_timing(
    current_vix=30.0,
    baseline_vix=18.0,
    persistence=0.96,
)

print(f"Half-life: {timing.half_life_days} days")
print(f"Days to baseline: {timing.days_to_baseline}")

for day, vix in timing.vix_trajectory:
    print(f"  Day {day}: VIX ≈ {vix}")
```

### Phase 2 持有期建议

```python
holding = timer.phase2_holding_recommendation(
    p_taco=0.33,       # 当前后验概率
    vix_current=28.0,  # 入场时 VIX
    days_since_entry=3,
)

print(f"Recommended hold: {holding.recommended_hold_days} days")
print(f"Exit signal: {holding.exit_signal}")
print(f"VIX exit threshold: {holding.vix_exit_threshold}")
```

### VIX 退出信号判断

```python
signal = timer.vix_exit_signal(
    entry_vix=28.0,
    current_vix=19.6,  # VIX 下跌了 30%
    days_held=5,
)

print(signal)
# {'signal': 'TAKE_PROFIT', 'reason': 'VIX dropped 30% since entry...', ...}
```

## 输出示例

```
GARCH VIX Timing Report
=======================================================
  Current VIX:         28.0
  Baseline VIX:       18.0
  GARCH persistence:   α+β = 0.960
  Half-life:           17.0 trading days
  Days to baseline:    35
  Confidence:          high
-------------------------------------------------------
  VIX Trajectory:
    Day  0: VIX ≈ 28.00
    Day  1: VIX ≈ 27.60
    Day  3: VIX ≈ 26.81
    Day  5: VIX ≈ 26.03
    Day 17: VIX ≈ 23.00  (half-life)
    Day 35: VIX ≈ 19.20
    Day 60: VIX ≈ 18.34
-------------------------------------------------------
  Phase 2 Holding:
    Recommended hold:  12 days
    Exit signal:       hold
    VIX exit threshold: 21.6
=======================================================
```

## 退出信号逻辑

| 信号 | 条件 | 操作 |
|------|------|------|
| `TAKE_PROFIT` | VIX 下跌 > 30% | 止盈，Phase 2 仓位平仓 |
| `STOP_LOSS` | VIX 飙升 > 20% | 止损，限制损失 |
| `HOLD` | VIX 基本不变 | 继续持有 |

## 与概率模型的关系

```
                    P(reversal) 高 → 持有更久
                              ↕
GARCH half-life ──→ Phase 2 持有期 ←─── VIX 高 → 半衰期长
```

GARCH 决定"等多久"，Five-Factor 决定"是否等"。

## 快速诊断

```bash
# 诊断当前 VIX 水平下的建议
python -c "
from core.garch_timing import GARCHTimingModel
timer = GARCHTimingModel()
print(timer.format_timing_report(current_vix=28.0, p_taco=0.33, days_since_entry=3))
"
```
