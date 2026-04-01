"""
core/garch_timing.py — GARCH VIX Timing Model for TACO System

GARCH 的正确用法：预测波动率何时回落，为交易时机提供信号。
不参与概率计算。

重构要点：
- 原 run_monte_carlo.py 中 GARCH 对概率的直接影响 → 废弃
- GARCH half-life → 用于交易时机（止损/止盈/加仓窗口）
- VIX 持续性仅影响 Phase 2 持有期，不影响 P(reversal)

Usage:
    timer = GARCHTimingModel()

    # 基于当前 VIX 和已知半衰期，估算波动率回归正常的时间
    timing = timer.estimate_reversion_timing(
        current_vix=30.0,
        baseline_vix=18.0,
        persistence=0.96,
    )

    # Phase 2 持有期建议
    holding = timer.phase2_holding_recommendation(
        p_taco=0.33,
        vix_current=28.0,
        days_since_entry=3,
    )
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Default GARCH(1,1) parameters (from pattern bible historical estimates)
# ---------------------------------------------------------------------------
DEFAULT_ALPHA = 0.09    # ARCH term: shock impact on volatility
DEFAULT_BETA = 0.87     # GARCH term: volatility persistence
DEFAULT_PERSISTENCE = DEFAULT_ALPHA + DEFAULT_BETA  # ≈ 0.96


@dataclass
class ReversionTiming:
    """Result of VIX reversion timing estimate."""
    half_life_days: float
    days_to_baseline: float
    vix_trajectory: list[tuple[int, float]]  # (day, estimated_vix)
    confidence: str  # "high", "medium", "low"
    note: str = ""


@dataclass
class HoldingRecommendation:
    """Phase 2 holding period recommendation."""
    recommended_hold_days: int
    exit_signal: str  # "reversion_confirmed" | "max_hold_reached" | "adverse_move"
    vix_exit_threshold: Optional[float]
    note: str = ""


class GARCHTimingModel:
    """
    GARCH VIX 时机模型。

    功能：
    1. 估算 VIX 从当前水平回落到基准的时间（half-life based）
    2. 为 Phase 2 交易提供持有期建议
    3. 生成波动率条件下的交易时机信号

    不做的事：
    - 不修改反转概率
    - 不参与 Five-Factor 或贝叶斯计算
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
        baseline_vix: float = 18.0,
        max_hold_days: int = 7,
    ):
        """
        Args:
            alpha: GARCH alpha (ARCH term)
            beta: GARCH beta (GARCH persistence term)
            baseline_vix: 正常市场波动率基准（历史上 ~15-18）
            max_hold_days: Phase 2 最大持有天数
        """
        self.alpha = alpha
        self.beta = beta
        self.persistence = alpha + beta
        self.baseline_vix = baseline_vix
        self.max_hold_days = max_hold_days

    def compute_half_life(self) -> float:
        """
        计算 VIX 半衰期（波动率回落一半所需天数）。

        Half-life = ln(0.5) / ln(persistence)
        典型值：~17 天（persistence=0.96）

        Returns:
            半衰期天数
        """
        if self.persistence <= 0 or self.persistence >= 1:
            return 17.0  # Default for persistence ≈ 0.96

        half_life = np.log(0.5) / np.log(self.persistence)
        return round(float(half_life), 1)

    def estimate_reversion_timing(
        self,
        current_vix: float,
        baseline_vix: Optional[float] = None,
        persistence: Optional[float] = None,
        horizon_days: int = 60,
    ) -> ReversionTiming:
        """
        估算 VIX 从当前水平回落到基准需要多长时间。

        Uses analytical GARCH mean reversion:
        VIX_t = baseline + (current - baseline) * persistence^t

        Args:
            current_vix: 当前 VIX 水平
            baseline_vix: 目标基准 VIX（默认用 self.baseline_vix）
            persistence: GARCH persistence（默认用 self.persistence）
            horizon_days: 预测最大天数

        Returns:
            ReversionTiming: 包含半衰期、回落时间和 VIX 轨迹
        """
        baseline = baseline_vix or self.baseline_vix
        pers = persistence or self.persistence

        half_life = self.compute_half_life()

        # 找到回落至 baseline 的天数
        # Solve: baseline + (current - baseline) * pers^t = baseline * 1.05
        # (5% above baseline = effectively baseline)
        excess = current_vix - baseline
        if excess <= 0:
            return ReversionTiming(
                half_life_days=half_life,
                days_to_baseline=0,
                vix_trajectory=[],
                confidence="high",
                note="VIX already at or below baseline",
            )

        # Target: 5% above baseline
        target = baseline * 1.05
        target_excess = target - baseline
        ratio = target_excess / excess

        if ratio <= 0:
            days_to_baseline = 0
        elif pers >= 1.0:
            days_to_baseline = horizon_days
        else:
            # pers^t = ratio  →  t = ln(ratio) / ln(pers)
            import math
            days_to_baseline = math.log(ratio) / math.log(pers)
            days_to_baseline = min(int(days_to_baseline), horizon_days)

        # Build trajectory (key days)
        trajectory_days = sorted(set([0, 1, 3, 5, int(half_life), int(days_to_baseline) if days_to_baseline < horizon_days else horizon_days, horizon_days]))
        trajectory_days = [d for d in trajectory_days if 0 <= d <= horizon_days]
        trajectory = []

        for day in trajectory_days:
            vix_est = baseline + excess * (pers ** day)
            trajectory.append((day, round(vix_est, 2)))

        confidence = self._confidence_label(pers)

        return ReversionTiming(
            half_life_days=half_life,
            days_to_baseline=int(days_to_baseline),
            vix_trajectory=trajectory,
            confidence=confidence,
        )

    def phase2_holding_recommendation(
        self,
        p_taco: float,
        vix_current: float,
        days_since_entry: int,
        persistence: Optional[float] = None,
    ) -> HoldingRecommendation:
        """
        Phase 2 持有期建议。

        基于：
        1. 当前 P(TACO) 越高 → 可以持有更久等待反转确认
        2. VIX 越高 → 半衰期更长，持有期相应延长
        3. 天数是硬性上限

        Args:
            p_taco: 当前后验反转概率
            vix_current: 入场时或当前的 VIX 水平
            days_since_entry: 入场后天数
            persistence: GARCH persistence（默认用 self.persistence）

        Returns:
            HoldingRecommendation: 持有建议和退出信号
        """
        pers = persistence or self.persistence
        half_life = self.compute_half_life()

        # 基础持有期 = min(半衰期 × (0.5 + p_taco), max_hold_days)
        # P(TACO) 越高，给反转确认的时间越长
        base_hold = half_life * (0.5 + p_taco)
        recommended_hold = min(int(base_hold), self.max_hold_days)

        # 硬性最大限制
        remaining = self.max_hold_days - days_since_entry
        if remaining <= 0:
            return HoldingRecommendation(
                recommended_hold_days=0,
                exit_signal="max_hold_reached",
                vix_exit_threshold=None,
                note=f"Max hold ({self.max_hold_days}d) reached",
            )

        # 退出信号判断
        if days_since_entry >= recommended_hold:
            exit_signal = "max_hold_reached"
            note = f"Recommended hold ({recommended_hold}d) reached at day {days_since_entry}"
        elif vix_current < self.baseline_vix * 1.10:
            # VIX 已接近正常，可能反转已发生（利好出尽）
            exit_signal = "reversion_confirmed"
            note = "VIX near baseline — reversal likely already priced in"
        else:
            exit_signal = "hold"
            note = f"Continue holding, check again in {remaining}d"

        # VIX 回落阈值：回落到基准的 1.2 倍时退出
        vix_exit = self.baseline_vix * 1.20

        return HoldingRecommendation(
            recommended_hold_days=recommended_hold,
            exit_signal=exit_signal,
            vix_exit_threshold=round(vix_exit, 1),
            note=note,
        )

    def vix_exit_signal(
        self,
        entry_vix: float,
        current_vix: float,
        days_held: int,
    ) -> dict:
        """
        交易持仓期间的 VIX 退出信号判断。

        Args:
            entry_vix: 入场时 VIX
            current_vix: 当前 VIX
            days_held: 持有天数

        Returns:
            dict with signal, reason, action
        """
        vix_change_pct = (current_vix - entry_vix) / entry_vix

        # 情况1：VIX 大幅下降（>30%）→ 反转可能已发生，止盈
        if vix_change_pct < -0.30:
            return {
                "signal": "TAKE_PROFIT",
                "reason": f"VIX dropped {abs(vix_change_pct)*100:.0f}% since entry — reversal likely occurred",
                "action": "Close Phase 2 position, book gains",
                "vix_exit": current_vix,
            }

        # 情况2：VIX 继续飙升（>20%）→ 局势恶化，止损
        if vix_change_pct > 0.20:
            return {
                "signal": "STOP_LOSS",
                "reason": f"VIX spiked {vix_change_pct*100:.0f}% since entry — escalation risk rising",
                "action": "Exit Phase 2, limit losses",
                "vix_exit": current_vix,
            }

        # 情况3：VIX 基本不变 → 继续持有
        return {
            "signal": "HOLD",
            "reason": f"VIX change {vix_change_pct*100:+.0f}% since entry — no clear signal",
            "action": f"Hold until next check (day {days_held + 1})",
            "vix_exit": None,
        }

    def _confidence_label(self, persistence: float) -> str:
        """基于 persistence 给出置信度标签。"""
        if persistence > 0.95:
            return "high"
        elif persistence > 0.85:
            return "medium"
        else:
            return "low"

    def format_timing_report(
        self,
        current_vix: float,
        p_taco: float,
        days_since_entry: int = 0,
    ) -> str:
        """生成完整的交易时机报告（可读字符串）。"""
        reversion = self.estimate_reversion_timing(current_vix)
        holding = self.phase2_holding_recommendation(p_taco, current_vix, days_since_entry)

        lines = []
        lines.append("GARCH VIX Timing Report")
        lines.append("=" * 55)
        lines.append(f"  Current VIX:         {current_vix}")
        lines.append(f"  Baseline VIX:       {self.baseline_vix}")
        lines.append(f"  GARCH persistence:   α+β = {self.persistence:.3f}")
        lines.append(f"  Half-life:           {reversion.half_life_days} trading days")
        lines.append(f"  Days to baseline:   {reversion.days_to_baseline}")
        lines.append(f"  Confidence:          {reversion.confidence}")
        lines.append("-" * 55)
        lines.append(f"  VIX Trajectory:")
        for day, vix in reversion.vix_trajectory:
            lines.append(f"    Day {day:>2}: VIX ≈ {vix}")
        lines.append("-" * 55)
        lines.append(f"  Phase 2 Holding:")
        lines.append(f"    Recommended hold:  {holding.recommended_hold_days} days")
        lines.append(f"    Exit signal:       {holding.exit_signal}")
        lines.append(f"    VIX exit threshold: {holding.vix_exit_threshold}")
        lines.append(f"    Note:               {holding.note}")
        lines.append("=" * 55)

        return "\n".join(lines)
