"""One-command PDF-to-story-to-motion workflow with source-checked reuse."""
import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from loguru import logger
from config import load_settings
from modules.pdf_parser import parse_pdf
from modules.term_extractor import extract_terms
from modules.logic_decomposer import decompose_logic
from modules.story_director import load_profile,validate_storyboard
from modules.script_writer import write_script
from modules.tts_engine import synthesize
from modules.video_maker import make_video
from modules.animated_renderer import save_story_card,save_summary_card
from modules.article_writer import write_article
from modules.quality_report import validate_output


def main():
    parser=argparse.ArgumentParser(description='论文转动态科普视频；大模型调用会产生费用')
    parser.add_argument('pdf',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--profile',choices=['science_short','science_long','research_bridge','research_long'],default='research_long')
    parser.add_argument('--duration',type=int)
    parser.add_argument('--analysis-dir',type=Path,help='复用另一目录中同一PDF的已验证分析')
    parser.add_argument('--reuse-analysis',action='store_true')
    parser.add_argument('--reuse-story',action='store_true',help='复用同一PDF、同一风格的已审查分镜')
    parser.add_argument('--prepare-only',action='store_true',help='仅脚本、分镜图和推文')
    args=parser.parse_args();settings=load_settings();root=args.output
    duration=args.duration if args.duration is not None else (settings.target_duration_seconds if args.profile=='science_long' else None)
    profile=load_profile(args.profile,duration)
    fingerprint=hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    root.mkdir(parents=True,exist_ok=True);marker=root/'source.sha256'
    if marker.exists() and marker.read_text()!=fingerprint:raise ValueError('输出目录属于另一份PDF')
    if not marker.exists() and not (root/'paper.json').exists() and ((args.reuse_story and (root/'script.json').exists()) or (args.reuse_analysis and (root/'terms.json').exists())):
        raise ValueError('无法确证旧缓存属于当前PDF，请使用新目录或先保存对应paper.json')
    paper=parse_pdf(args.pdf)
    if (args.reuse_analysis or args.reuse_story) and not marker.exists() and (root/'paper.json').exists():
        if json.loads((root/'paper.json').read_text())['full_text']!=paper.full_text:raise ValueError('已有分析与当前PDF不匹配')
    marker.write_text(fingerprint)
    def save(name,value):
        (root/f'{name}.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');return value
    save('paper',{**asdict(paper),'full_text':paper.full_text})
    analysis_dir=args.analysis_dir or root
    if args.analysis_dir:
        reference=json.loads((analysis_dir/'paper.json').read_text())
        if reference['full_text']!=paper.full_text:raise ValueError('analysis-dir与输入PDF不一致')
    def analysis(name,fn):
        path=analysis_dir/f'{name}.json'
        return save(name,json.loads(path.read_text()) if (args.reuse_analysis or args.analysis_dir) and path.exists() else fn())
    terms=analysis('terms',lambda:extract_terms(paper.full_text))
    logic=analysis('logic',lambda:decompose_logic(paper.full_text))
    script_path=root/'script.json'
    if args.reuse_story and script_path.exists():
        script=json.loads(script_path.read_text())
        if script.get('profile')!=profile:raise ValueError('分镜风格已变化，请移除--reuse-story重新编导')
        validate_storyboard(script,[asdict(p) for p in paper.pages])
        if not script.get('reviews') or script['reviews'][-1].get('approved') is not True:raise ValueError('分镜未经独立审查')
    else:
        script=save('script',write_script(logic,terms,[asdict(p) for p in paper.pages],profile['target_seconds'],args.profile))
    if profile.get('research_depth'):
        from modules.research_contract import validate_research
        from modules.source_assets import extract_pages,bind_assets
        validate_research(script)
        if not script.get('teaching_review',{}).get('approved'):raise ValueError('研究版缺少教学审查')
        bind_assets(script,extract_pages(args.pdf,root/'source_assets'))
        save('script',script)
    for scene in script['scenes']:save_story_card(scene,profile,root/'cards'/f'{scene["id"]}.png')
    save_summary_card(script['summary_card'],profile,root/'summary.png')
    write_article(script,root/'article.md')
    if args.prepare_only:return
    timeline=asyncio.run(synthesize(script,root/'audio'))
    # The last scene holds the shareable summary without duplicating narration.
    timeline['scenes'][-1]['summary_card']=script['summary_card']
    save('timeline',timeline)
    make_video(timeline,root/'video.mp4')
    validate_output(root)
    logger.info('完成：实际 {:.1f}秒，目标 {}秒，分镜 {}个',timeline['duration'],profile['target_seconds'],len(script['scenes']))


if __name__=='__main__':main()
