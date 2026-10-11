"""Create an illustrated companion with a summary and source references."""
from pathlib import Path


def write_article(script,output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    parts=['# '+script.get('hook','Paper2Video：论文图文解读'),script.get('promise','')]
    if script.get('summary_card'):
        summary=script['summary_card']
        parts.extend(['## 一页读懂','![一页总结](summary.png)',*['- '+x for x in summary['points']],
                      '学习建议：'+summary['takeaway']])
    for scene in script['scenes']:
        pages=sorted({c['page'] for c in scene.get('citations',[])})
        parts.extend([f'## {scene["title"]}',f'![{scene["title"]}](cards/{scene["id"]}.png)',scene['narration']])
        if scene.get('term_card'):
            card=scene['term_card']
            parts.extend(['**'+card['name']+'（'+card['full_name']+'）**',card['definition'],'论文作用：'+card['paper_role'],'类比边界：'+card['analogy_limit']])
        if scene.get('source_asset'):
            parts.append('![论文原页](source_assets/page_'+str(scene['source_page']).zfill(3)+'.png)')
        if pages:parts.append('原文依据：第'+ '、'.join(map(str,pages))+'页。')
    parts.append('示意动画用于解释机制，不能当作真实实验影像；研究结果不等于临床验证。')
    output.write_text('\n\n'.join(parts)+'\n',encoding='utf-8');return output


if __name__=='__main__':
    import argparse,json
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    write_article(json.loads((a.folder/'script.json').read_text()),a.folder/'article.md')
