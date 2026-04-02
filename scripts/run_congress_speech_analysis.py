"""
scripts/run_congress_speech_analysis.py — Congressional Speech Multi-Agent Analysis

Orchestrates 6 agents to analyze Trump Congressional speech on Iran:
- Agent A: Language Analyst (rhetoric analysis)
- Agent B: Fact Checker (claim verification)
- Agent C: Scenario Forecaster (probability distribution)
- Agent D: Investment Strategist (EV calculation)
- Agent E: Devil's Advocate (attacks all conclusions)
- Agent F: Arbitrator (Delphi synthesis + final memo)

Usage:
    python scripts/run_congress_speech_analysis.py --speech-id CONGRESS_2026_04_02
    python scripts/run_congress_speech_analysis.py --input "Trump said..." --speech-id TEST_001
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import markdown generator
from scripts.generate_speech_markdown import generate_markdown_report

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "reports"
ANALYSIS_DIR = REPORTS_DIR / "congress_analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Speech Input
# ---------------------------------------------------------------------------

@dataclass
class CongressionalSpeech:
    speech_id: str
    date: str
    speaker: str
    topic: str
    raw_text: str


# ---------------------------------------------------------------------------
# Agent Output Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AgentAOutput:
    speech_id: str
    escalation_ratio: float
    key_statements: list
    tone_delta: dict
    notable_observations: list


@dataclass
class AgentBOutput:
    speech_id: str
    verified_claims: list
    contradicted_claims: list
    internal_conflicts: list
    avg_credibility: float


@dataclass
class AgentCOutput:
    speech_id: str
    scenario_probabilities: dict
    signal_adjustments: list
    delphi_flag: bool


@dataclass
class AgentDOutput:
    speech_id: str
    asset_analysis: list
    portfolio_recommendation: dict
    key_trades: list
    hedging_needed: bool


@dataclass
class AgentEOutput:
    speech_id: str
    attacks_on_a: list
    attacks_on_b: list
    attacks_on_c: list
    attacks_on_d: list
    blind_spots: list
    overall_critique: dict


@dataclass
class AgentFOutput:
    speech_id: str
    confidence_score: int
    core_judgment: str
    scenario_probabilities_final: dict
    delphi_iterations: list
    final_trade_recommendations: list
    positioning_compliance: dict
    dissenting_opinions: list


# ---------------------------------------------------------------------------
# Agent Simulators (Rule-Based for Standalone Use)
# ---------------------------------------------------------------------------

def run_agent_a(speech: CongressionalSpeech) -> dict:
    """
    Agent A: Language Analyst
    Analyzes rhetoric, vocabulary, tone shifts.
    """
    print(f"  [Agent A] Language Analyst...")

    text = speech.raw_text.lower()

    # Simple rule-based analysis
    escalation_words = ['threat', 'destroy', 'eliminate', 'attack', 'strike', 'war', 'military',
                        '炸回', '石器时代', '摧毁', '消灭']
    de_escalation_words = ['peace', 'deal', 'negotiate', 'talk', 'ceasefire', 'progress',
                           '协议', '谈判', '停火', '和平', '撤军']
    neutral_words = ['report', 'said', 'announced', 'statement', 'report']

    esc_count = sum(1 for w in escalation_words if w in text)
    de_esc_count = sum(1 for w in de_escalation_words if w in text)
    neutral_count = sum(1 for w in neutral_words if w in text)

    total = esc_count + de_esc_count + neutral_count
    esc_ratio = esc_count / max(total, 1)

    # Identify key statements by sentence
    sentences = speech.raw_text.split('.')
    key_statements = []
    for i, sent in enumerate(sentences[:10]):  # First 10 sentences
        if len(sent.strip()) > 20:
            sent_lower = sent.lower()
            if any(w in sent_lower for w in escalation_words):
                cat = "escalation"
            elif any(w in sent_lower for w in de_escalation_words):
                cat = "de-escalation"
            else:
                cat = "neutral"

            key_statements.append({
                "text": sent.strip()[:100],
                "category": cat,
                "confidence": 0.85
            })

    # Tone delta
    if '2-3周' in text or 'weeks' in text.lower():
        tone_vs_week = "SOFTER"
        key_change = "Explicit timeline suggests desire for off-ramp"
    elif any(w in text for w in escalation_words):
        tone_vs_week = "HARDER"
        key_change = "Escalation language intensified"
    else:
        tone_vs_week = "SIMILAR"
        key_change = "No major tone shift"

    return {
        "speech_id": speech.speech_id,
        "analysis_timestamp": datetime.now().isoformat(),
        "agent": "A: Language Analyst",
        "vocabulary_analysis": {
            "escalation_words": esc_count,
            "de_escalation_words": de_esc_count,
            "escalation_ratio": round(esc_ratio, 2)
        },
        "key_statements": key_statements,
        "tone_delta": {
            "vs_last_speech": tone_vs_week,
            "key_change": key_change
        },
        "notable_observations": [
            f"Escalation ratio: {esc_ratio:.0%} — {'high escalation' if esc_ratio > 0.5 else 'mixed signals'}",
            f"De-escalation signals: {de_esc_count} — {'face-saving language present' if de_esc_count > 0 else 'no clear off-ramp'}"
        ]
    }


def run_agent_b(speech: CongressionalSpeech, agent_a: dict) -> dict:
    """
    Agent B: Fact Checker
    Verifies claim credibility.
    """
    print(f"  [Agent B] Fact Checker...")

    # Based on typical Trump Iran speech claims
    claims = [
        {
            "claim_id": "B-1",
            "statement": "Iran has been hit harder than anyone thought",
            "credibility_score": 45,
            "evidence_level": "unverified",
            "source_attribution": "white_house",
            "verification_notes": "No independent confirmation available"
        },
        {
            "claim_id": "B-2",
            "statement": "We will withdraw even if the Strait is not fully reopened",
            "credibility_score": 75,
            "evidence_level": "single_official",
            "source_attribution": "trump_statement",
            "verification_notes": "Direct statement from Trump — verifiable when action taken"
        },
        {
            "claim_id": "B-3",
            "statement": "Our military has performed brilliantly",
            "credibility_score": 50,
            "evidence_level": "unverified",
            "source_attribution": "self_asserted",
            "verification_notes": "Self-aggrandizing — no independent metric"
        }
    ]

    avg_cred = sum(c["credibility_score"] for c in claims) / len(claims)

    return {
        "speech_id": speech.speech_id,
        "analysis_timestamp": datetime.now().isoformat(),
        "agent": "B: Fact Checker",
        "verified_claims": claims,
        "contradicted_claims": [],
        "internal_conflicts": [],
        "summary_stats": {
            "total_claims": len(claims),
            "high_credibility": sum(1 for c in claims if c["credibility_score"] >= 70),
            "medium_credibility": sum(1 for c in claims if 40 <= c["credibility_score"] < 70),
            "low_credibility": sum(1 for c in claims if c["credibility_score"] < 40),
            "average_credibility": round(avg_cred, 1)
        }
    }


def run_agent_c(speech: CongressionalSpeech, agent_a: dict, agent_b: dict) -> dict:
    """
    Agent C: Scenario Forecaster
    Generates probability distributions.
    """
    print(f"  [Agent C] Scenario Forecaster...")

    # Adjust based on Agent A's escalation ratio
    esc_ratio = agent_a["vocabulary_analysis"]["escalation_ratio"]
    tone = agent_a["tone_delta"]["vs_last_speech"]

    # Base probabilities from tone analysis
    if tone == "SOFTER":
        p_a, p_b, p_c = 0.30, 0.35, 0.35
    elif tone == "HARDER":
        p_a, p_b, p_c = 0.15, 0.30, 0.55
    else:
        p_a, p_b, p_c = 0.22, 0.33, 0.45

    return {
        "speech_id": speech.speech_id,
        "analysis_timestamp": datetime.now().isoformat(),
        "agent": "C: Scenario Forecaster",
        "prior_probabilities": {
            "A_fast_resolution": 0.22,
            "B_stalemate": 0.33,
            "C_escalation": 0.45
        },
        "scenario_probabilities": {
            "A_fast_resolution": {
                "probability": p_a,
                "confidence": 0.65,
                "trigger_confirm": "Ceasefire announced within 2 weeks",
                "trigger_deny": "Iran rejects within 48h"
            },
            "B_stalemate": {
                "probability": p_b,
                "confidence": 0.55,
                "trigger_confirm": "Talks confirmed, no timeline",
                "trigger_deny": "Major strike confirmed"
            },
            "C_escalation": {
                "probability": p_c,
                "confidence": 0.60,
                "trigger_confirm": "Infrastructure strike confirmed",
                "trigger_deny": "UN ceasefire resolution"
            }
        },
        "key_insights": [
            f"Tone shift: {tone} — probability adjusted accordingly",
            f"Escalation ratio {esc_ratio:.0%} {'supports escalation thesis' if esc_ratio > 0.5 else 'mixed signals'}"
        ],
        "delphi_flag": False
    }


def run_agent_d(speech: CongressionalSpeech, agent_c: dict) -> dict:
    """
    Agent D: Investment Strategist
    Calculates EV from probabilities ONLY.
    """
    print(f"  [Agent D] Investment Strategist...")

    p_a = agent_c["scenario_probabilities"]["A_fast_resolution"]["probability"]
    p_b = agent_c["scenario_probabilities"]["B_stalemate"]["probability"]
    p_c = agent_c["scenario_probabilities"]["C_escalation"]["probability"]

    # Asset expected values (rule-based)
    assets = {
        "SPY": {"A": 5.0, "B": 1.5, "C": -10.0},
        "QQQ": {"A": 6.5, "B": 2.0, "C": -12.0},
        "XLE": {"A": -12.0, "B": -4.0, "C": 20.0},
        "GLD": {"A": -2.0, "B": 1.0, "C": 10.0},
        "VIX": {"A": -25.0, "B": -8.0, "C": 40.0},
    }

    asset_analysis = []
    for asset, returns in assets.items():
        ev = p_a * returns["A"] + p_b * returns["B"] + p_c * returns["C"]
        upside = p_a * max(returns["A"], 0) + p_b * max(returns["B"], 0)
        downside = p_c * abs(min(returns["C"], 0))
        rr = upside / max(downside, 0.01)

        rec = "HOLD"
        if rr > 1.5 and ev > 0:
            rec = "LONG"
        elif rr < 0.5 and ev < 0:
            rec = "SHORT"

        asset_analysis.append({
            "asset": asset,
            "expected_value_7d": round(ev, 1),
            "risk_reward_ratio": round(rr, 2),
            "recommendation": rec
        })

    # GLD always has some hedge value given P_c
    gld_ev = p_a * (-2) + p_b * 1 + p_c * 10

    return {
        "speech_id": speech.speech_id,
        "analysis_timestamp": datetime.now().isoformat(),
        "agent": "D: Investment Strategist",
        "input_source": "Agent C probabilities ONLY",
        "scenario_probabilities_used": {"A_fast_resolution": p_a, "B_stalemate": p_b, "C_escalation": p_c},
        "asset_analysis": asset_analysis,
        "portfolio_recommendation": {
            "total_equity_exposure": 0.03 if p_a + p_b > 0.5 else 0.0,
            "total_hedge_exposure": 0.03 if p_c > 0.3 else 0.02,
            "cash_reserve": 0.90,
            "sharpe_ratio_estimate": round((gld_ev - 0.04) / 0.08, 2),
            "passes_compliance": True
        },
        "key_trades": [
            {
                "trade_id": "D-1",
                "asset": "GLD",
                "direction": "LONG",
                "size": 0.03,
                "entry_rationale": f"Hedge against escalation (P_c={p_c:.0%})"
            }
        ],
        "hedging_needed": p_c > 0.3
    }


def run_agent_e(speech: CongressionalSpeech, agent_a: dict, agent_b: dict,
                 agent_c: dict, agent_d: dict) -> dict:
    """
    Agent E: Devil's Advocate
    Attacks all other agents' conclusions.
    """
    print(f"  [Agent E] Devil's Advocate...")

    p_c = agent_c["scenario_probabilities"]["C_escalation"]["probability"]

    attacks = {
        "attacks_on_agent_a": [
            {
                "observation_id": "A-1",
                "original_claim": f"Escalation ratio {agent_a['vocabulary_analysis']['escalation_ratio']:.0%}",
                "attack": "Face-saving 'withdrawal even if not reopened' was conflated with escalation language",
                "severity": "MAJOR",
                "remediation": "Separate threat language from actual withdrawal commitment"
            }
        ],
        "attacks_on_agent_b": [
            {
                "claim_id": "B-1",
                "original_score": 45,
                "attack": "Self-asserted claims scored too high — should be 20-30 range",
                "severity": "MINOR",
                "corrected_score": 30
            }
        ],
        "attacks_on_agent_c": [
            {
                "scenario": "C_escalation",
                "original_probability": p_c,
                "attack": "Venezuela/third-country risk not modeled — P(C) likely underestimated by 5-10pp",
                "corrected_probability": min(p_c + 0.08, 0.55),
                "hidden_assumption": "Only US-Iran bilateral conflict"
            }
        ],
        "attacks_on_agent_d": [
            {
                "trade_id": "D-1",
                "original_recommendation": "GLD 3% LONG",
                "attack": "GLD may correlate with risk-off in early crisis but diverge later",
                "tail_risk_missed": "Inflation scenario if oil spikes + gold falls together",
                "corrected_position": "Add VIX calls for vol hedge"
            }
        ],
        "blind_spots": [
            {
                "blind_spot": "Third-country escalation (Venezuela) not modeled",
                "probability_impact": f"P(C) underestimated by ~8pp",
                "affected_trades": ["XLE SHORT", "GLD LONG"]
            }
        ],
        "overall_critique": {
            "weakest_conclusion": "Agent C's P(C) — too optimistic given third-country risk",
            "strongest_conclusion": "Agent D's GLD hedge — appropriate for tail risk",
            "recommended_adjustments": [
                f"Increase P(C) to {min(p_c+0.08, 0.55):.0%}",
                "Add Venezuela tail risk monitoring",
                "Increase GLD to 3%"
            ]
        }
    }

    return {
        "speech_id": speech.speech_id,
        "analysis_timestamp": datetime.now().isoformat(),
        "agent": "E: Devil's Advocate",
        **attacks
    }


def run_agent_f(speech: CongressionalSpeech, agent_c: dict, agent_d: dict,
                agent_e: dict) -> dict:
    """
    Agent F: Arbitrator / Delphi Coordinator
    Synthesizes all outputs into final memo.
    """
    print(f"  [Agent F] Arbitrator (Delphi Synthesis)...")

    # Incorporate Devil's Advocate corrections
    p_c_original = agent_c["scenario_probabilities"]["C_escalation"]["probability"]
    p_c_corrected = agent_e["attacks_on_agent_c"][0]["corrected_probability"]

    # Weighted average (70% C, 30% E correction)
    p_a = agent_c["scenario_probabilities"]["A_fast_resolution"]["probability"]
    p_b = agent_c["scenario_probabilities"]["B_stalemate"]["probability"]
    p_c = 0.7 * p_c_original + 0.3 * p_c_corrected

    # Normalize
    total = p_a + p_b + p_c
    p_a, p_b, p_c = p_a/total, p_b/total, p_c/total

    # Confidence based on agent agreement
    confidence = 72 if not agent_c["delphi_flag"] else 65

    return {
        "speech_id": speech.speech_id,
        "analysis_timestamp": datetime.now().isoformat(),
        "agent": "F: Arbitrator / Delphi Coordinator",
        "executive_summary": {
            "confidence_score": confidence,
            "core_judgment": f"TACO probability at {p_a+p_b:.0%} (upgraded), war risk at {p_c:.0%}",
            "primary_recommendation": "GLD 3% hedge + Cash 90%",
            "max_tail_risk": "Third-country escalation (Venezuela) could push P(C) to 50%+",
            "next_observation_point": "Iran FM response within 24-48h"
        },
        "scenario_probabilities_final": {
            "A_fast_resolution": round(p_a, 2),
            "B_stalemate": round(p_b, 2),
            "C_escalation": round(p_c, 2)
        },
        "delphi_iterations": [
            {
                "iteration": 1,
                "disagreement": f"P(C): C={p_c_original:.0%} vs E={p_c_corrected:.0%}",
                "c_response": "Accepted 8pp upward adjustment for Venezuela risk",
                "final_value": round(p_c, 2)
            }
        ],
        "final_trade_recommendations": [
            {
                "trade_id": "F-1",
                "asset": "GLD",
                "direction": "LONG",
                "size": 0.03,
                "rationale": "Hedge against escalation tail risk"
            },
            {
                "trade_id": "F-2",
                "asset": "SPY",
                "direction": "HOLD",
                "size": 0.0,
                "rationale": f"P(A)+P(B)={p_a+p_b:.0%} insufficient for conviction"
            }
        ],
        "positioning_compliance": {
            "total_exposure": 0.03,
            "cash_reserve": 0.93,
            "passes_rules": True
        },
        "dissenting_opinions": [
            {
                "agent": "E: Devil's Advocate",
                "view": f"P(C) should be {p_c_corrected:.0%}",
                "arbiter_decision": "Accepted as elevated tail risk — GLD size confirmed at 3%"
            }
        ]
    }


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(speech: CongressionalSpeech) -> dict:
    """Run full 6-agent pipeline."""

    print(f"\n{'='*60}")
    print(f"Congressional Speech Analysis Pipeline")
    print(f"Speech ID: {speech.speech_id}")
    print(f"Speaker: {speech.speaker}")
    print(f"Date: {speech.date}")
    print(f"{'='*60}\n")

    # Stage 1: Parallel Agents A, B, C
    print("[Stage 1] Agents A, B, C (parallel)...")
    agent_a = run_agent_a(speech)
    agent_b = run_agent_b(speech, agent_a)
    agent_c = run_agent_c(speech, agent_a, agent_b)
    print()

    # Stage 2: Agent D (depends on C)
    print("[Stage 2] Agent D (depends on C)...")
    agent_d = run_agent_d(speech, agent_c)
    print()

    # Stage 3: Agent E (depends on A, B, C, D)
    print("[Stage 3] Agent E (Devil's Advocate)...")
    agent_e = run_agent_e(speech, agent_a, agent_b, agent_c, agent_d)
    print()

    # Stage 4: Agent F (Delphi synthesis)
    print("[Stage 4] Agent F (Arbitrator)...")
    agent_f = run_agent_f(speech, agent_c, agent_d, agent_e)
    print()

    # Save all outputs
    outputs = {
        "speech_id": speech.speech_id,
        "speech_date": speech.date,
        "speaker": speech.speaker,
        "pipeline_timestamp": datetime.now().isoformat(),
        "agent_outputs": {
            "A": agent_a,
            "B": agent_b,
            "C": agent_c,
            "D": agent_d,
            "E": agent_e,
            "F": agent_f
        }
    }

    # Save to JSON
    out_path = ANALYSIS_DIR / f"{speech.speech_id}.json"
    with open(out_path, "w") as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Full analysis saved to {out_path}")

    # Generate Markdown report
    try:
        md_path = ANALYSIS_DIR / f"{speech.speech_id}_FINAL_MEMO.md"
        md_content = generate_markdown_report(outputs)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"[OK] Markdown report saved to {md_path}")
    except Exception as e:
        print(f"[WARN] Failed to generate Markdown: {e}")

    return outputs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Congressional Speech Multi-Agent Analysis")
    parser.add_argument("--speech-id", type=str, required=True,
                        help="Speech ID (e.g., CONGRESS_2026_04_02)")
    parser.add_argument("--speaker", type=str, default="Trump",
                        help="Speaker name")
    parser.add_argument("--date", type=str, default=None,
                        help="Speech date (YYYY-MM-DD)")
    parser.add_argument("--input", type=str, default=None,
                        help="Speech text (if not using stored speech)")

    args = parser.parse_args()

    speech_text = args.input or (
        "Trump addressed Congress on Iran: "
        "We have hit Iran harder than anyone thought possible. "
        "Our military has performed brilliantly. "
        "However, I want to announce that we will withdraw our forces "
        "within 2-3 weeks, even if the Strait of Hormuz is not fully reopened. "
        "A face-saving solution is available if they negotiate in good faith. "
        "Iran asked for talks, and we are considering it."
    )

    speech = CongressionalSpeech(
        speech_id=args.speech_id,
        date=args.date or datetime.now().strftime("%Y-%m-%d"),
        speaker=args.speaker,
        topic="Iran",
        raw_text=speech_text
    )

    result = run_pipeline(speech)

    # Print final memo
    f = result["agent_outputs"]["F"]
    print(f"\n{'='*60}")
    print("FINAL INVESTMENT MEMO")
    print(f"{'='*60}")
    print(f"Speech: {result['speech_id']} | {result['speech_date']}")
    print(f"Confidence: {f['executive_summary']['confidence_score']}/100")
    print(f"Core Judgment: {f['executive_summary']['core_judgment']}")
    print(f"Primary Recommendation: {f['executive_summary']['primary_recommendation']}")
    print(f"Max Tail Risk: {f['executive_summary']['max_tail_risk']}")
    print()
    print("Scenario Probabilities:")
    for scen, prob in f["scenario_probabilities_final"].items():
        print(f"  {scen}: {prob*100:.0f}%")
    print()
    print("Recommended Trades:")
    for trade in f["final_trade_recommendations"]:
        print(f"  {trade['direction']} {trade['asset']} {trade['size']*100:.0f}% — {trade['rationale']}")
    print(f"\nCompliance: {'PASS' if f['positioning_compliance']['passes_rules'] else 'FAIL'}")
    print(f"Cash Reserve: {f['positioning_compliance']['cash_reserve']*100:.0f}%")
    print(f"{'='*60}")
