"""CLI entry for the configurable director, replacing the PPT-style writer."""
import argparse
import json
from pathlib import Path
from modules.story_director import make_story,load_profile


def write_script(logic,terms,pages,target_seconds=None,profile='science_long',client=None,reviewer=None):
    return make_story(logic,terms,pages,load_profile(profile,target_seconds),client,reviewer)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='生成有原文证据、独立审查和动作指令的口播分镜')
    parser.add_argument('folder',type=Path)
    parser.add_argument('--profile',choices=['science_short','science_long'],default='science_long')
    parser.add_argument('--duration',type=int)
    args=parser.parse_args()
    paper=json.loads((args.folder/'paper.json').read_text(encoding='utf-8'))
    script=write_script(json.loads((args.folder/'logic.json').read_text(encoding='utf-8')),
                        json.loads((args.folder/'terms.json').read_text(encoding='utf-8')),
                        paper['pages'],args.duration,args.profile)
    (args.folder/'script.json').write_text(json.dumps(script,ensure_ascii=False,indent=2),encoding='utf-8')
