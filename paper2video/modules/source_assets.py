"""Render traceable PDF page assets; never substitute generated experiment images."""
import hashlib
import json
from pathlib import Path
import pdfplumber


def extract_pages(pdf,output):
    pdf=Path(pdf);root=Path(output);root.mkdir(parents=True,exist_ok=True)
    fingerprint=hashlib.sha256(pdf.read_bytes()).hexdigest();items=[]
    with pdfplumber.open(pdf) as document:
        for i,page in enumerate(document.pages,1):
            path=root/f'page_{i:03d}.png'
            page.to_image(resolution=130).original.convert('RGB').save(path)
            items.append({'page':i,'path':str(path.resolve()),'kind':'original_pdf_page','sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (root/'manifest.json').write_text(json.dumps({'source_sha256':fingerprint,'assets':items},ensure_ascii=False,indent=2))
    return items


def bind_assets(script,assets):
    by_page={a['page']:a for a in assets}
    for scene in script['scenes']:
        if scene['visual']=='source_page':
            asset=by_page[scene['source_page']]
            scene['source_asset']=asset['path']
            scene['source_sha256']=asset['sha256']
