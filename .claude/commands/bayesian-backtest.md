# /bayesian-backtest — Bayesian Reversal Updater 回测

对历史 TACO 事件回测贝叶斯更新轨迹，验证信号处理是否改善预测精度。

## 核心指标

| 指标 | 说明 |
|------|------|
| MAE | Mean Absolute Error，越低越好 |
| Accuracy | P_t > 50% → 预测 TACO；< 50% → 预测 No-TACO |
| P₀ | Five-Factor 静态先验 |
| P_t | 贝叶斯后验（信号更新后） |

## 预检查

```bash
python scripts/backtest_bayesian.py
# 确保 core.bayesian_updater 可导入
python -c "from core.bayesian_updater import BayesianReversalUpdater; print('OK')"
```

## 使用方式

### 运行标准回测

```
/bayesian-backtest
```

### 保存结果到 JSON

```
/bayesian-backtest --output reports/backtest_bayesian.json
```

## 回测事件列表

| Event | Type | Signals | Actual |
|-------|------|---------|--------|
| TACO-001 | trade_tariff | extends_deadline → deal_imminent | TACO ✓ |
| TACO-002 | trade_tariff | hard_rejection → great_progress | TACO ✓ |
| TACO-003 | trade_tariff | symbolic_concession → extends_deadline | TACO ✓ |
| TACO-004 | trade_tariff | symbolic_concession → extends_deadline | TACO ✓ |
| TACO-005 | trade_tariff | hedges → deal_imminent | TACO ✓ |
| TACO-007 | territorial | hedges → ally_opposes → extends_deadline | TACO ✓ |
| TACO-008 | territorial | ally_opposes → hedges | TACO ✓ |
| TACO-009 | trade_tariff | mediator → great_progress → deal_imminent | TACO ✓ |
| TACO-010 | trade_tariff | no_deal → hard_rejection → mediator → great_progress | TACO ✓ |
| TACO-012 | trade_tariff | symbolic_concession → extends_deadline | TACO ✓ |
| TACO-013 | personnel | hedges → no_deal_possible | TACO ✓ |
| TACO-014 | trade_tariff | back_channel → extends_deadline | TACO ✓ |
| TACO-015 | military | mediator_enters → hedges | TACO ✓ |

**注意**: 所有历史事件都是 TACO（生存偏差），无法测试反 TACO 场景。

## 预期输出格式

```
Bayesian Reversal Updater Backtest
============================================================
Events tested: 13

Overall Accuracy (threshold=50%):
  Five-Factor P₀:  92.3%  (12/13 correct)
  Bayesian P_t:     92.3%  (12/13 correct)

Mean Absolute Error:
  Five-Factor P₀:  0.254
  Bayesian P_t:     0.132     ← MAE 改善 ~48%

By Statement Type:
------------------------------------------------------------
  military            : P₀ acc=0%, P_t acc=100%  (n=1)
  personnel           : P₀ acc=100%, P_t acc=0%  (n=1)
  territorial         : P₀ acc=100%, P_t acc=100%  (n=2)
  trade_tariff        : P₀ acc=100%, P_t acc=100%  (n=9)

Per-Event Detail:
------------------------------------------------------------
  TACO-001 (trade_tariff): P₀=82% ✓ → P_t=98% ✓  [trump_extends_deadline, trump_signals_deal_imminent]
  TACO-015 (military): P₀=38% ✗ → P_t=88% ✓  [third_party_mediator_enters, trump_hedges_language]
```

## 关键解读

### TACO-015 (military) — P₀ 低估案例

- **P₀ = 38%**: Military 基础率低，原始模型预测 No-TACO ✗
- **P_t = 88%**: 第三方调解人介入 (LR=5.0) + 软化语言 (LR=2.3) → 修正
- **结论**: 贝叶斯引擎修正了基础率过低的问题

### TACO-013 (personnel) — P_t 过度修正案例

- **P₀ = 78%**: Personnel 基础率高，预测 TACO ✓
- **P_t = 45%**: `trump_says_no_deal_possible` (LR=0.10) 主导 → 过度修正 ✗
- **实际结果**: 仍是 TACO（最终政策立场软化）
- **结论**: 反向信号组合导致 P_t 低于实际，适用于快速反转的贸易事件

## 局限性

1. **生存偏差**: 所有历史事件都是 TACO（13/13），反 TACO 案例无法测试
2. **信号序列人工重建**: 基于新闻描述，可能有噪声
3. **阈值敏感**: 50% 阈值是主观的，可调整

## 扩展回测

如需添加新事件，修改 `scripts/backtest_bayesian.py` 中的 `HISTORICAL_SIGNALS` 字典：

```python
"TACO-016": (
    StatementType.MILITARY,
    0.38,
    [
        ("Day 2", "trump_extends_deadline"),
        ("Day 5", "counterparty_hard_rejection"),
        ("Day 7", "trump_signals_deal_imminent"),
    ],
    1,  # 1=TACO occurred, 0=no TACO
),
```
