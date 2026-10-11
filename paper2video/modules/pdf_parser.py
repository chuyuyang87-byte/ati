"""Extract page-aware text from text-based PDFs; no OCR is performed."""
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pdfplumber
from loguru import logger


@dataclass(frozen=True)
class PaperPage:
    number: int
    text: str


@dataclass(frozen=True)
class ParsedPaper:
    source: str
    pages: list[PaperPage]

    @property
    def full_text(self) -> str:
        return "\n\n".join(
            f"[第 {page.number} 页]\n{page.text}" for page in self.pages if page.text
        )

    @property
    def empty_pages(self) -> list[int]:
        return [page.number for page in self.pages if not page.text]


def parse_pdf(path: str | Path, password: str | None = None) -> ParsedPaper:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"PDF 文件不存在：{source}")
    try:
        with pdfplumber.open(source, password=password) as document:
            pages = [
                PaperPage(number=i, text=(page.extract_text(x_tolerance=1) or "").strip())
                for i, page in enumerate(document.pages, start=1)
            ]
    except Exception as exc:
        raise ValueError("无法读取 PDF：请检查文件是否损坏、格式是否正确，或是否需要密码。") from exc
    paper = ParsedPaper(source=str(source), pages=pages)
    if not paper.full_text.strip():
        raise ValueError("PDF 没有可提取文本，可能是扫描件；请先进行 OCR 后重试。")
    if paper.empty_pages:
        logger.warning("以下页没有可提取文本，内容可能不完整：{}", paper.empty_pages)
    logger.info("提取完成：{} 页，{} 个字符", len(pages), len(paper.full_text))
    return paper


def main() -> None:
    parser = argparse.ArgumentParser(description="提取论文 PDF 的文本（不支持扫描件 OCR）")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="输出 JSON 文件路径")
    args = parser.parse_args()
    try:
        paper = parse_pdf(args.pdf)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(1, f"错误：{exc}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({**asdict(paper), "full_text": paper.full_text,
                    "empty_pages": paper.empty_pages}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已保存：{args.output}")


if __name__ == "__main__":
    main()
