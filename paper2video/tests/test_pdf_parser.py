import tempfile
import unittest
from pathlib import Path

from PIL import Image
from modules.pdf_parser import parse_pdf


def text_pdf(path):
    stream = b'BT /F1 12 Tf 72 720 Td (Paper2Video sample paper) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    data = b'%PDF-1.4\n'
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n'
    data += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    data += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    path.write_bytes(data)


class PDFParserTests(unittest.TestCase):
    def test_real_text_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'paper.pdf'
            text_pdf(path)
            paper = parse_pdf(path)
            self.assertEqual(paper.pages[0].text, 'Paper2Video sample paper')
            self.assertIn('[第 1 页]', paper.full_text)
            self.assertEqual(paper.empty_pages, [])

    def test_scan_requires_ocr(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'scan.pdf'
            Image.new('RGB', (100, 100), 'white').save(path, 'PDF')
            with self.assertRaisesRegex(ValueError, 'OCR'):
                parse_pdf(path)

    def test_corrupt_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.pdf'
            path.write_text('not a PDF')
            with self.assertRaisesRegex(ValueError, '无法读取'):
                parse_pdf(path)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                parse_pdf(Path(folder) / 'missing.pdf')


if __name__ == '__main__':
    unittest.main()
