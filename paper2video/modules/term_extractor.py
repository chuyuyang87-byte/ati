"""Extract terms from every text chunk, then merge duplicates."""
import argparse
import json
from pathlib import Path
from modules.llm_client import LLMClient, require_strings, split_text
from modules.pdf_parser import parse_pdf


def extract_terms(text: str, client=None) -> list[dict]:
    client = client or LLMClient()
    terms = {}
    for chunk in split_text(text):
        result = client.ask_json(
            '提取本段专有名词、缩写及关键公式。返回 {"terms": ['
            '{"term":"术语或公式","full_name":"全称，未给出则写未说明",'
            '"plain_explain":"面向小白的解释，类比须说明局限",'
            '"evidence":"正文中的简短原文及可用页码"}]}。没有则返回空列表。', chunk)
        items = result.get("terms")
        if not isinstance(items, list):
            raise ValueError("terms 必须为列表")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("术语条目必须为对象")
            require_strings(item, ("term", "full_name", "plain_explain", "evidence"))
            key = item["term"].strip().casefold()
            if key not in terms:
                terms[key] = item
    return list(terms.values())


def main():
    parser = argparse.ArgumentParser(description="使用大模型提取论文术语；会产生 API 费用")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    terms = extract_terms(parse_pdf(args.pdf).full_text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(terms, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"提取 {len(terms)} 个术语，保存到 {args.output}")


if __name__ == "__main__":
    main()
