"""Generate paginated Chinese slides without clipping long text."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from config import load_settings

TITLES = {"background": "背景痛点", "method": "核心方法", "result": "实验结果",
          "highlight": "创新亮点", "application": "应用价值"}


def find_font() -> Path:
    configured = load_settings().font_path
    candidates = [configured] if configured else [
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        Path('C:/Windows/Fonts/msyh.ttc'),
        Path('/System/Library/Fonts/PingFang.ttc'),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError('未找到中文字体，请在 FONT_PATH 配置可用中文字体的路径。')


def wrap_text(text: str, font, width: int) -> list[str]:
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for character in paragraph:
            if line and font.getlength(line + character) > width:
                lines.append(line)
                line = character
            else:
                line += character
        lines.append(line)
    return lines


def generate_cards(logic: dict, output_dir: str | Path) -> list[dict]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    font_path = find_font()
    body = ImageFont.truetype(str(font_path), 34)
    title_font = ImageFont.truetype(str(font_path), 58)
    small = ImageFont.truetype(str(font_path), 24)
    cards = []
    for module, title in TITLES.items():
        text = logic.get(module)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f'缺少模块正文：{module}')
        lines = wrap_text(text, body, 1120)
        pages = [lines[i:i + 8] for i in range(0, len(lines), 8)]
        for page_number, page_lines in enumerate(pages, 1):
            picture = Image.new('RGB', (1280, 720), '#111b30')
            draw = ImageDraw.Draw(picture)
            draw.rectangle((0, 0, 18, 720), fill='#43d9bd')
            draw.text((72, 48), title, font=title_font, fill='#ffffff')
            draw.line((72, 138, 1208, 138), fill='#43d9bd', width=3)
            for index, line in enumerate(page_lines):
                draw.text((72, 176 + index * 54), line, font=body, fill='#e0e8f4')
            draw.text((72, 664), 'Paper2Video · 论文科普', font=small, fill='#a2b4ce')
            draw.text((1040, 664), f'{page_number} / {len(pages)}', font=small, fill='#a2b4ce')
            path = output_dir / f'{module}_{page_number:02d}.png'
            picture.save(path)
            cards.append({'id': f'{module}_{page_number:02d}', 'module': module,
                          'title': title, 'text': '\n'.join(page_lines),
                          'image': str(path.resolve())})
    return cards


def main():
    parser = argparse.ArgumentParser(description='将论文五模块 JSON 排版为中文卡片')
    parser.add_argument('logic', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cards = generate_cards(json.loads(args.logic.read_text(encoding='utf-8')), args.output)
    manifest = args.output / 'cards.json'
    manifest.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'已生成 {len(cards)} 张卡片：{manifest}')


if __name__ == '__main__':
    main()
