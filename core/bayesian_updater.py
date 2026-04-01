"""
core/bayesian_updater.py — Bayesian Reversal Updater for TACO System

不再是"一次性计算器"，而是持续运行的信号处理引擎。
每次收到新信号时，通过贝叶斯更新调整反转概率。

Usage:
    updater = BayesianReversalUpdater()
    prior = 0.38  # 五因子模型输出的 MILITARY 初始先验
    posterior, delta = updater.update(prior, "trump_extends_deadline")

    # 批量更新
    history = updater.update_sequence(prior, [
        ("Day 2", "trump_extends_deadline"),
        ("Day 3", "counterparty_hard_rejection"),
    ])
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Likelihood Ratio Table
# ---------------------------------------------------------------------------
# P(observe signal | reversal happens) / P(observe signal | reversal does NOT happen)
# LR > 1: signal supports reversal
# LR < 1: signal supports NO reversal
# LR ≈ 1: neutral signal

LIKELIHOOD_RATIOS: dict[str, float] = {

    # ── 强反转信号 (LR >> 1) ─────────────────────────────────────────────
    "trump_says_great_progress":      8.5,   # 特朗普称"进展顺利"
    "trump_says_they_called_me":     12.0,   # 特朗普称"他们给我打了电话"
    "trump_signals_deal_imminent":    7.2,   # 特朗普暗示即将达成协议
    "third_party_mediator_enters":    5.0,   # 第三方调解人介入
    "vix_drops_10pct_no_news":        4.2,   # VIX 下跌 10%+ 但无明显消息
    "counterparty_symbolic_concession": 6.5, # 对手做出象征性让步
    "trump_extends_deadline":         3.8,   # 特朗普延长最后期限
    "trump_praises_counterparty":     5.5,   # 特朗普公开称赞对手
    "both_sides_frame_deal":          6.0,   # 双方都开始用"协议"框架

    # ── 弱反转信号 (LR 1.5–3) ────────────────────────────────────────────
    "market_rally_without_catalyst":   2.1,   # 市场上涨但无明确催化剂
    "back_channel_rumor":              1.8,   # 幕后渠道传言
    "trump_hedges_language":           2.3,   # 特朗普措辞软化
    "trump_repeats_deadline_change":   2.5,   # 特朗普重复提及期限变更
    "press_hints_negotiation":         1.9,   # 媒体报道谈判暗示

    # ── 反 TACO 信号 (LR << 1) ───────────────────────────────────────────
    "new_harder_statement":           0.15,   # 特朗普发表更强硬声明
    "military_action_confirmed":      0.05,   # 军事行动确认
    "counterparty_hard_rejection":     0.20,  # 对手强硬拒绝
    "trump_says_no_deal_possible":    0.10,  # 特朗普称"不可能达成协议"
    "ally_publicly_opposes_retreat":  0.35,   # 盟友公开反对退缩
    "military_forces_repositioned":   0.12,  # 军事力量重新部署
    "trump_sets_hard_deadline":       0.25,  # 特朗普设定硬性最后期限
    "counterparty_breaks_off_talks":  0.18,  # 对手中断谈判

    # ── 中性信号 (LR ≈ 1) ───────────────────────────────────────────────
    "routine_press_briefing":         1.1,   # 例行新闻发布会
    "market_flat":                    0.95,  # 市场基本持平
    "trump_repeats_threat":           1.0,   # 特朗普重复原有威胁（无新信息）
    "mixed_signals":                  1.0,   # 混合信号
}

# ── 油价上下文修正器 ────────────────────────────────────────────────────
# 当油价 > 85时，TACO 的国内政治成本更高，"软化信号"的可信度下降
CONTEXT_MODIFIERS: dict[str, dict[str, float]] = {
    "oil_above_85": {
        "trump_extends_deadline":        0.55,  # LR × 0.55
        "trump_says_great_progress":     0.70,
        "trump_signals_deal_imminent":   0.60,
        "counterparty_symbolic_concession": 0.75,
    },
    "oil_above_100": {
        "trump_extends_deadline":        0.35,
        "trump_says_great_progress":     0.50,
        "trump_signals_deal_imminent":    0.40,
        "counterparty_symbolic_concession": 0.55,
    },
    "gas_above_4": {
        "trump_extends_deadline":        0.60,
        "trump_says_great_progress":     0.75,
    },
}


@dataclass
class UpdateResult:
    """Single Bayesian update result."""
    time: str
    signal: str
    prior: float
    posterior: float
    delta: float
    lr_applied: float
    context_adjusted: bool = False
    modifier_note: str = ""


class BayesianReversalUpdater:
    """
    持续运行的贝叶斯反转概率更新引擎。

    不再是一次性计算，而是每次收到新信号时更新概率。
    五因子模型的输出作为初始先验 P₀，贝叶斯引擎在其基础上
    通过似然比更新得到实时后验 P_t。

    Usage:
        updater = BayesianReversalUpdater()

        # 单一更新
        posterior, delta = updater.update(0.38, "trump_extends_deadline")

        # 序列更新（含轨迹）
        history = updater.update_sequence(0.38, [
            ("Day 2", "trump_extends_deadline"),
            ("Day 3", "counterparty_hard_rejection"),
        ])
    """

    def __init__(
        self,
        min_prob: float = 0.02,
        max_prob: float = 0.98,
    ):
        """
        Args:
            min_prob: 概率下界（防止极端更新）
            max_prob: 概率上界
        """
        self.min_prob = min_prob
        self.max_prob = max_prob
        self.lr_table = LIKELIHOOD_RATIOS.copy()
        self.context_modifiers = CONTEXT_MODIFIERS

    def update(
        self,
        prior: float,
        signal: str,
        context: Optional[dict] = None,
    ) -> tuple[float, float]:
        """
        标准贝叶斯更新。

        Args:
            prior: 先验概率 P(reversal)
            signal: 信号名称（必须在 LIKELIHOOD_RATIOS 中）
            context: 可选上下文 {"oil_price": float, "gas_price": float}

        Returns:
            (后验概率, 更新幅度 delta = posterior - prior)
        """
        if signal not in self.lr_table:
            return prior, 0.0

        lr = self.lr_table[signal]

        # 应用上下文修正
        if context:
            lr = self._apply_context_modifier(lr, signal, context)

        # 贝叶斯公式: posterior = lr × prior / (lr × prior + (1 - prior))
        numerator = lr * prior
        denominator = lr * prior + (1 - prior)

        if denominator <= 0:
            return prior, 0.0

        posterior = numerator / denominator
        posterior = float(np.clip(posterior, self.min_prob, self.max_prob))

        return posterior, posterior - prior

    def update_sequence(
        self,
        initial_prior: float,
        signals: list[tuple[str, str]],
        context: Optional[dict] = None,
    ) -> list[UpdateResult]:
        """
        处理一系列信号，返回完整更新轨迹。

        Args:
            initial_prior: 五因子模型输出的初始先验 P₀
            signals: [(timestamp, signal_name), ...]
            context: 油价/气价等上下文

        Returns:
            更新轨迹列表，每步包含 prior, posterior, delta, lr
        """
        history: list[UpdateResult] = []
        current_prior = initial_prior

        # t0: 初始先验
        history.append(UpdateResult(
            time="t0",
            signal="initial_estimate",
            prior=initial_prior,
            posterior=initial_prior,
            delta=0.0,
            lr_applied=1.0,
        ))

        for time, signal in signals:
            prior = current_prior
            lr = self.lr_table.get(signal, 1.0)
            adjusted_lr = self._apply_context_modifier(lr, signal, context) if context else lr
            adjusted_note = ""

            if context and adjusted_lr != lr:
                adjusted_note = f"ctx_mod: {lr:.2f}→{adjusted_lr:.2f}"

            posterior, delta = self.update(prior, signal, context)

            history.append(UpdateResult(
                time=time,
                signal=signal,
                prior=round(prior, 4),
                posterior=round(posterior, 4),
                delta=round(delta, 4),
                lr_applied=round(adjusted_lr, 3),
                context_adjusted=(adjusted_lr != lr),
                modifier_note=adjusted_note,
            ))

            current_prior = posterior

        return history

    def _apply_context_modifier(
        self,
        lr: float,
        signal: str,
        context: dict,
    ) -> float:
        """根据上下文调整似然比（油价/气价修正）。"""
        adjusted = lr

        oil_price = context.get("oil_price", 0)
        gas_price = context.get("gas_price", 0)

        if oil_price >= 100 and "oil_above_100" in self.context_modifiers:
            mod = self.context_modifiers["oil_above_100"].get(signal, 1.0)
            adjusted *= mod
        elif oil_price >= 85 and "oil_above_85" in self.context_modifiers:
            mod = self.context_modifiers["oil_above_85"].get(signal, 1.0)
            adjusted *= mod

        if gas_price >= 4.0 and "gas_above_4" in self.context_modifiers:
            mod = self.context_modifiers["gas_above_4"].get(signal, 1.0)
            adjusted *= mod

        return adjusted

    def check_polymarket_calibration(
        self,
        model_prob: float,
        polymarket_prob: float,
    ) -> Optional[tuple[str, float]]:
        """
        Polymarket 校准检查。

        Polymarket 从"30%权重直接参与计算"变为
        "以独立信号身份用 LR 注入贝叶斯引擎"。

        当 model_prob 与 polymarket_prob 存在显著分歧时，
        生成一个伪信号反馈到 update()。

        Args:
            model_prob: 五因子模型输出的 P₀
            polymarket_prob: Polymarket 市场的反转概率

        Returns:
            (signal_name, lr) 如果产生信号，否则 None
        """
        divergence = abs(model_prob - polymarket_prob)

        if divergence > 0.30:
            # 巨大分歧
            if polymarket_prob < model_prob:
                return ("market_strongly_disagrees_with_reversal", 0.25)
            else:
                return ("market_strongly_expects_reversal", 4.0)
        elif divergence > 0.15:
            # 中等分歧
            if polymarket_prob < model_prob:
                return ("market_skeptical_of_reversal", 0.60)
            else:
                return ("market_leans_reversal", 1.80)
        else:
            # 基本一致，无额外信号
            return None

    def format_trajectory(
        self,
        history: list[UpdateResult],
        initial_statement_type: str = "",
    ) -> str:
        """格式化输出更新轨迹为可读字符串。"""
        lines = []
        header = "Bayesian Reversal Probability Trajectory"
        if initial_statement_type:
            header += f" ({initial_statement_type})"
        lines.append(header)
        lines.append("=" * 65)

        for r in history:
            if r.signal == "initial_estimate":
                lines.append(
                    f"  {r.time:<8} {r.signal:<35} → {r.posterior*100:6.1f}%"
                )
            else:
                arrow = "↑" if r.delta >= 0 else "↓"
                ctx_note = f" [{r.modifier_note}]" if r.modifier_note else ""
                lines.append(
                    f"  {r.time:<8} {r.signal:<35} → {r.posterior*100:6.1f}%"
                    f"  ({arrow}{abs(r.delta)*100:5.1f}pp, LR={r.lr_applied:.2f}){ctx_note}"
                )

        lines.append("=" * 65)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Statement Type → Initial Prior P₀
# ---------------------------------------------------------------------------
# 从 Five-Factor 的 Factor1 (type base rate) 映射
# 这是先验，不是经过五因子全链计算的结果

STATEMENT_TYPE_PRIORS: dict[str, float] = {
    "trade_tariff":   0.82,
    "personnel":      0.78,
    "territorial":    0.58,
    "military":       0.38,   # 38% = Five-Factor MILITARY base rate
    "policy":         0.15,
    "sanctions":      0.55,
    "diplomatic":     0.60,
}


def get_initial_prior(statement_type: str) -> float:
    """根据语句类型返回初始先验 P₀（来自五因子 Factor1）。"""
    return STATEMENT_TYPE_PRIORS.get(statement_type.lower(), 0.38)
