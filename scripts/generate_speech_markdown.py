"""
scripts/generate_speech_markdown.py — Generate Markdown Report from JSON Analysis

将 JSON 分析结果转换为人类可读的 Markdown 报告。
适配 run_congress_speech_analysis.py 输出的 JSON 结构。
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def load_json(json_path: Path) -> Dict[str, Any]:
    """加载 JSON 分析结果"""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def format_probability(p: float) -> str:
    """格式化概率为百分比"""
    if isinstance(p, dict):
        p = p.get("probability", p.get("weight", 0))
    return f"{p * 100:.0f}%"


def generate_executive_summary(data: Dict[str, Any]) -> str:
    """生成执行摘要"""
    md = []
    agent_f = data.get("agent_outputs", {}).get("F", {})
    exec_sum = agent_f.get("executive_summary", {})

    md.append("本次国会演讲分析核心判断：")
    md.append("")

    # 从 executive_summary 提取
    core_judgment = exec_sum.get("core_judgment", "N/A")
    md.append(f"- **核心判断**: {core_judgment}")
    md.append("")

    # 情景概率简述
    sp = agent_f.get("scenario_probabilities_final", {})
    if sp:
        a = sp.get("A_fast_resolution", 0)
        b = sp.get("B_stalemate", 0)
        c = sp.get("C_escalation", 0)
        md.append(f"- **情景概率**: A={a*100:.0f}% B={b*100:.0f}% C={c*100:.0f}%")

    # TACO 判断 (从投资建议推断)
    trades = agent_f.get("final_trade_recommendations", [])
    taco_event = "✅ 可能" if trades else "❌ 不是"
    md.append(f"- **TACO 事件**: {taco_event}")
    md.append("")

    return "\n".join(md)


def generate_scenario_table(data: Dict[str, Any]) -> str:
    """生成情景概率表格"""
    md = []
    md.append("## 情景概率")
    md.append("")
    md.append("| 情景 | 概率 | 说明 |")
    md.append("|------|------|------|")

    agent_f = data.get("agent_outputs", {}).get("F", {})
    sp = agent_f.get("scenario_probabilities_final", {})

    descriptions = {
        "A_fast_resolution": "2周内停火撤离",
        "B_stalemate": "无重大升级，谈判持续",
        "C_escalation": "基础设施打击，战事蔓延",
    }

    for key, prob in sp.items():
        desc = descriptions.get(key, "")
        if isinstance(prob, dict):
            prob = prob.get("probability", prob.get("weight", 0))
        md.append(f"| {key} | {prob*100:.0f}% | {desc} |")

    md.append("")
    return "\n".join(md)


def generate_agent_summary(data: Dict[str, Any]) -> str:
    """生成 Agent 分析摘要"""
    md = []
    md.append("## Agent 分析摘要")
    md.append("")

    agents = data.get("agent_outputs", {})

    agent_names = {
        "A": "Agent A: 语言分析",
        "B": "Agent B: 事实核查",
        "C": "Agent C: 情景预测",
        "D": "Agent D: 投资策略",
        "E": "Agent E: 魔鬼代言",
        "F": "Agent F: 仲裁者",
    }

    for key in ["A", "B", "C", "D", "E", "F"]:
        output = agents.get(key, {})
        name = agent_names.get(key, key)
        md.append(f"### {name}")

        # 特殊字段
        if key == "A":
            vocab = output.get("vocabulary_analysis", {})
            if vocab:
                md.append(f"- Escalation Ratio: {vocab.get('escalation_ratio', 'N/A')}")
            tone = output.get("tone_delta", {})
            if tone:
                md.append(f"- Tone: {tone.get('vs_last_speech', 'N/A')}")
                md.append(f"- Key Change: {tone.get('key_change', 'N/A')}")

        elif key == "B":
            stats = output.get("summary_stats", {})
            if stats:
                md.append(f"- 平均可信度: {stats.get('average_credibility', 'N/A')}")
                md.append(f"- 高可信度声明: {stats.get('high_credibility', 0)}")

        elif key == "C":
            priors = output.get("prior_probabilities", {})
            if priors:
                md.append(f"- 先验概率: A={priors.get('A_fast_resolution', 0)*100:.0f}% "
                          f"B={priors.get('B_stalemate', 0)*100:.0f}% "
                          f"C={priors.get('C_escalation', 0)*100:.0f}%")

        elif key == "D":
            portfolio = output.get("portfolio_recommendation", {})
            if portfolio:
                md.append(f"- 现金储备: {portfolio.get('cash_reserve', 0)*100:.0f}%")
                md.append(f"- 合规通过: {'是' if portfolio.get('passes_compliance') else '否'}")

        elif key == "E":
            critique = output.get("overall_critique", {})
            if critique:
                md.append(f"- 最弱结论: {critique.get('weakest_conclusion', 'N/A')}")
                md.append(f"- 最强结论: {critique.get('strongest_conclusion', 'N/A')}")

        elif key == "F":
            exec_sum = output.get("executive_summary", {})
            if exec_sum:
                md.append(f"- 置信度: {exec_sum.get('confidence_score', 'N/A')}/100")
                md.append(f"- 核心判断: {exec_sum.get('core_judgment', 'N/A')}")
            delphi = output.get("delphi_iterations", [])
            if delphi:
                md.append(f"- Delphi 迭代: {len(delphi)} 次")

        md.append("")

    return "\n".join(md)


def generate_trade_recommendations(data: Dict[str, Any]) -> str:
    """生成交易建议"""
    md = []
    md.append("## 最终交易建议")
    md.append("")
    md.append("| 资产 | 方向 | 仓位 | 理由 |")
    md.append("|------|------|------|------|")

    agent_f = data.get("agent_outputs", {}).get("F", {})
    trades = agent_f.get("final_trade_recommendations", [])

    direction_symbols = {"LONG": "🟢", "SHORT": "🔴", "HOLD": "🟡", "AVOID": "⚫"}

    for trade in trades:
        direction = trade.get("direction", "")
        symbol = direction_symbols.get(direction, "")
        size = trade.get("size", 0)
        rationale = trade.get("rationale", "")
        asset = trade.get("asset", "")
        md.append(f"| {asset} | {symbol} {direction} | {size*100:.0f}% | {rationale} |")

    # compliance
    compliance = agent_f.get("positioning_compliance", {})
    if compliance:
        md.append("")
        md.append(f"**合规状态**: {'通过 ✅' if compliance.get('passes_rules') else '未通过 ❌'}")
        md.append(f"**总仓位**: {compliance.get('total_exposure', 0)*100:.0f}%")
        md.append(f"**现金储备**: {compliance.get('cash_reserve', 0)*100:.0f}%")

    md.append("")
    return "\n".join(md)


def generate_markdown_report(data: Dict[str, Any]) -> str:
    """从 JSON 数据生成完整的 Markdown 报告"""

    md = []
    md.append("# 国会演讲分析 — 最终备忘录")
    md.append("")
    md.append(f"**speech_id**: {data.get('speech_id', 'N/A')}")
    md.append(f"**日期**: {data.get('speech_date', data.get('date', 'N/A'))}")
    md.append(f"**演讲者**: {data.get('speaker', 'N/A')}")
    md.append("")

    agent_f = data.get("agent_outputs", {}).get("F", {})
    exec_sum = agent_f.get("executive_summary", {})
    if exec_sum:
        md.append(f"**置信度**: {exec_sum.get('confidence_score', 0)}/100")
    else:
        md.append("**置信度**: N/A")

    md.append("")
    md.append("---")
    md.append("")

    # 执行摘要
    md.append("## 执行摘要")
    md.append("")
    md.append(generate_executive_summary(data))
    md.append("---")
    md.append("")

    # 情景概率
    md.append(generate_scenario_table(data))
    md.append("---")
    md.append("")

    # 交易建议
    md.append(generate_trade_recommendations(data))
    md.append("---")
    md.append("")

    # Agent 摘要
    md.append(generate_agent_summary(data))
    md.append("---")
    md.append("")

    # 页脚
    md.append(f"*Generated by TACO Congressional Speech Analysis System*")
    md.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(md)


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("Usage: python generate_speech_markdown.py <json_path> [output_path]")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"Error: File not found: {json_path}")
        sys.exit(1)

    # 确定输出路径
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = json_path.with_suffix(".md")

    # 生成报告
    data = load_json(json_path)
    md_content = generate_markdown_report(data)

    # 写入文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
