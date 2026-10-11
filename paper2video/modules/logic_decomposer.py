"""Summarize all chunks before a bounded hierarchical synthesis."""
import argparse
import json
from pathlib import Path
from modules.llm_client import LLMClient, require_strings, split_text
from modules.pdf_parser import parse_pdf

KEYS = ("background", "method", "result", "highlight", "application")
INSTRUCTION = (
    '返回五个非空字符串字段：background（背景痛点）、method（方法）、'
    'result（实验结果及限制）、highlight（创新）、application（应用价值）。'
    '每项保留可用的原文页码。区分实验支持、作者推测和未说明；不推断因果。'
)


def decompose_logic(text: str, client=None) -> dict:
    client = client or LLMClient()
    summaries = []
    for chunk in split_text(text):
        summary = client.ask_json(INSTRUCTION, chunk)
        require_strings(summary, KEYS)
        summaries.append({key: summary[key] for key in KEYS})
    for _ in range(8):
        if len(summaries) == 1:
            return summaries[0]
        groups, current, size = [], [], 0
        for summary in summaries:
            serialized = json.dumps(summary, ensure_ascii=False)
            if len(serialized) > 28000:
                raise ValueError("单段摘要过长，无法安全合并；请调整模型输出。")
            if current and size + len(serialized) > 28000:
                groups.append(current)
                current, size = [], 0
            current.append(summary)
            size += len(serialized)
        if current:
            groups.append(current)
        if len(groups) >= len(summaries):
            raise ValueError("摘要无法压缩合并，停止处理以避免丢失内容。")
        merged = []
        for group in groups:
            result = client.ask_json(INSTRUCTION + '合并这些分段摘要，去重压缩，每个字段不超过800字。',
                                     json.dumps(group, ensure_ascii=False))
            require_strings(result, KEYS)
            merged.append({key: result[key] for key in KEYS})
        summaries = merged
    raise ValueError("论文过长，摘要合并超过最大轮数。")


def main():
    parser = argparse.ArgumentParser(description="使用大模型拆解论文；会产生 API 费用")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = decompose_logic(parse_pdf(args.pdf).full_text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存：{args.output}")


if __name__ == "__main__":
    main()
