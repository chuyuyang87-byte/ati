"""Configurable science director, source-bound citations and independent review."""
import json
import math
import re
from pathlib import Path
from modules.llm_client import LLMClient, require_strings
from modules.logic_decomposer import KEYS

ROOT=Path(__file__).resolve().parents[1]
VISUALS={'question','domain_shift','privacy','uncertainty','error_loop','graph','prompts','comparison','boundary','takeaway'}
CUES={'reveal','focus','link','contrast'}
SHORT_JARGON=('SPFE','DGCS','MC Dropout','Sinkhorn','最优传输','高阶结构','熵最小化','特征矩阵','反向注意力','端到端')


def load_profile(name='science_long',target_seconds=None):
    if name not in {'science_short','science_long'}:raise ValueError('未知视频风格')
    profile=json.loads((ROOT/'profiles'/f'{name}.json').read_text(encoding='utf-8'))
    if target_seconds is not None:
        if not 30<=target_seconds<=1200:raise ValueError('目标时长须在30到1200秒之间')
        profile['target_seconds']=target_seconds
    return profile


def normalize(text):return ''.join(c.casefold() for c in text if c.isalnum())


def has_number(text,value):
    number=format(value,'g')
    suffix='0*' if '.' in number else r'(?:\.0+)?'
    return re.search(r'(?<![\d.])'+re.escape(number)+suffix+r'(?![\d.])',text) is not None


def validate_storyboard(script,pages,require_all_modules=True):
    require_strings(script,('hook','promise','analogy','ending'))
    if len(script['hook'])>24:raise ValueError('开场钩子过长')
    scenes=script.get('scenes')
    if not isinstance(scenes,list) or not scenes:raise ValueError('分镜为空')
    numbers={p['number']:p['text'] for p in pages}
    for scene in scenes:
        require_strings(scene,('id','title','narration','visual','module'))
        if scene['visual'] not in VISUALS or scene['module'] not in KEYS:raise ValueError('视觉类型或模块无效')
        if len(scene['title'])>18:raise ValueError('屏幕标题超过18字')
        labels=scene.get('labels')
        if not isinstance(labels,list) or not 1<=len(labels)<=3 or any(not isinstance(x,str) or not 1<=len(x)<=10 for x in labels):raise ValueError('标签须为1到3个，每个不超过10字')
        citations=scene.get('citations')
        if not isinstance(citations,list) or not citations:raise ValueError('场景缺少原文证据')
        for citation in citations:
            if not isinstance(citation,dict) or not isinstance(citation.get('page'),int) or not isinstance(citation.get('quote'),str):raise ValueError('引文格式错误')
            quote=normalize(citation['quote'])
            if len(quote)<8 or citation['page'] not in numbers or quote not in normalize(numbers[citation['page']]):raise ValueError('引文不在指定原文页中')
        beats=scene.get('beats')
        if not isinstance(beats,list) or not 1<=len(beats)<=4:raise ValueError('每个场景须有1到4个动作')
        for beat in beats:
            if not isinstance(beat,dict) or beat.get('action') not in CUES or not isinstance(beat.get('cue'),str) or not normalize(beat['cue']) or normalize(beat['cue']) not in normalize(scene['narration']):raise ValueError(f'触发词必须是口播原文：cue={beat.get("cue")}; narration={scene["narration"]}')
        if scene['visual']=='comparison':
            metrics=scene.get('metrics')
            if not isinstance(metrics,list) or not 2<=len(metrics)<=3:raise ValueError('对比图需要2到3项数据')
            require_strings(scene,('metric_name',))
            for metric in metrics:
                require_strings(metric,('label',))
                value=metric.get('value')
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0<=value<=100:raise ValueError('指标须为0到100')
                if not any(has_number(c['quote'],value) for c in citations):raise ValueError(f'图表数值{value}没有被引用原文支持：{scene.get("evidence_ids")}')
        if scene.get('math'):
            spec=scene['math']
            if not isinstance(spec,dict) or spec.get('kind') not in {'formula','trajectory'}:raise ValueError('数学动画模板无效')
            if spec['kind']=='formula':
                if not isinstance(spec.get('formula'),str) or not spec['formula'].strip() or re.sub(r'\s+','',spec['formula']) not in re.sub(r'\s+','',' '.join(c['quote'] for c in citations)):raise ValueError('公式必须来自已引用的原文，保留运算符')
            elif spec.get('is_illustration') is not True:raise ValueError('轨迹动画须明确标为机制示意')
    texts=[normalize(s['narration']) for s in scenes]
    if len(set(texts))!=len(texts):raise ValueError('重复口播')
    first_question=normalize(scenes[0]['narration']).split('因为')[0][:12]
    if len(first_question)>=8 and sum(normalize(s['narration']).startswith(first_question) for s in scenes)>2:raise ValueError('重复使用开场问题')
    if len(normalize(scenes[0]['narration']))>50:raise ValueError('开场口播太长')
    order=[KEYS.index(s['module']) for s in scenes]
    if order!=sorted(order) or (require_all_modules and set(order)!=set(range(5))):raise ValueError('必须按五模块顺序叙述')


def _excerpts(pages):
    result={}
    for page in pages:
        for i,line in enumerate(page['text'].splitlines()):
            if len(normalize(line))>=8:result[f'p{page["number"]}l{i}']={'page':page['number'],'quote':line}
    return result


def _prepare(items,excerpts,start=0,module=None):
    prepared=[]
    for i,s in enumerate(items):
        ids=s.get('evidence_ids')
        if not isinstance(ids,list) or not 1<=len(ids)<=8 or any(not isinstance(x,str) or x not in excerpts for x in ids):raise ValueError(f'引用编号错误：{ids}')
        ids=list(ids)
        # Bind omitted numeric evidence only when a unique row on an already
        # cited page contains both the exact method label and numeric value.
        # This never changes the metric; independent review checks its meaning.
        for metric in s.get('metrics',[]):
            if not isinstance(metric,dict) or not isinstance(metric.get('value'),(int,float)):continue
            number=format(metric['value'],'g')
            if any(has_number(excerpts[x]['quote'],metric['value']) for x in ids):continue
            source_label=metric.get('source_label',metric.get('label',''))
            if any(word in source_label for word in ('无适应','不适应','不调整','不调')):
                source_label='No Adapt'
            label=normalize(source_label)
            if len(label)<3:continue
            cited_pages={excerpts[x]['page'] for x in ids}
            candidates=[x for x,c in excerpts.items() if c['page'] in cited_pages and label in normalize(c['quote']) and has_number(c['quote'],metric['value'])]
            if len(candidates)==1:ids.append(candidates[0])
        prepared.append({**s,'evidence_ids':ids,'id':f'scene_{start+i+1:03d}','module':module or s.get('module'),
                         'bullets':s.get('labels',[]),'citations':[excerpts[x] for x in ids]})
        if prepared[-1].get('metrics'):
            prepared[-1]['metrics']=sorted(prepared[-1]['metrics'],key=lambda x:x['value'])
    return prepared


SCHEMA='''只返回 scenes 数组。每项格式：{"module":"background/method/result/highlight/application之一",
"title":"18字以内短句","narration":"口播","visual":"question/domain_shift/privacy/uncertainty/error_loop/graph/prompts/comparison/boundary/takeaway之一",
"labels":["最多3个10字内标签"],"beats":[{"cue":"本段口播中原样出现的关键词","action":"reveal/focus/link/contrast之一"}],
"evidence_ids":["original_excerpts中真实存在的编号"]}。
comparison项额外提供 metric_name（准确的任务和指标名称）及 metrics:[{"label":"屏幕短方法名","source_label":"原文方法名","value":84.37}]，2到3项。
图表数字必须包含在选中编号的原文中；不混用不同任务、指标或实验设置。
每项引用1到8个支持事实的原文编号，不自写引文、不编造编号。
第一场景问句3秒内可说完，不念标题作者。口播先说人话，再解释概念。
生活类比必须说明只是帮助理解，不要把像素示意冒充真正的医学影像。
每场只说一个新信息，不重复开场；不归纳全部五模块到每一个模块。
专业术语第一次出现就用生活比喻解释，不说颠覆性、已临床可用或诊断准确率。
结尾保留实际部署尚未验证等边界，并用一句话回答开场问题。
方法镜头优先graph、prompts；结果镜头优先comparison；倒数第二镜boundary，最后一镜takeaway。
讲隐私和旧数据不可用时选privacy，讲挑选有把握区域时选uncertainty；不要把不同机制都画成双路提示。
仅当原文有数学公式或机器人轨迹解释需求，可添加math字段调用Manim固定模板：
{"kind":"formula","formula":"照抄引文中的Unicode公式"} 或
{"kind":"trajectory","points":[[0,0],[1,1]],"is_illustration":true}。
没有相关内容的论文不添加数学动画，不生成任意Python或LaTeX代码。
'''


def review_story(script,pages,reviewer):
    checks=[]
    for scene in script['scenes']:
        if scene['visual']=='comparison':
            metrics=scene['metrics']
            checks.append({'scene_id':scene['id'],'values':metrics,
                           'arithmetic_difference_percentage_points':metrics[-1]['value']-metrics[0]['value']})
    return reviewer.ask_json(
        '你是独立事实审查模型。只审核事实错误、证据不足、数据任务错配、夸大医疗效果，'
        '以及明显重复或开场结尾答非所问。通俗简化不等于错误，不要求短片覆盖全部技术细节。'
        '日常类比可以是作者未使用的，只要不冒充实验事实且说明类比边界。'
        '两个以百分数表达的DSC数值相减，得到百分点差；以表格数值直接算出的差是有效结论。'
        '论文把差写成%不代表它必然是相对提升，不将正确的百分点算术判为错误。'
        '必须检查每项引用是否支持对应主张，不能仅因数字出现在原文就通过。'
        '返回 {"approved":true/false,"issues":["阻断性问题"],"suggestions":["非阻断改进"],"summary":"说明"}。',
        json.dumps({'script':script,'computed_checks':checks,
                    'original_pages':[p for p in pages if p['number'] in {c['page'] for s in script['scenes'] for c in s['citations']}]},ensure_ascii=False))


def fit_narration_budget(script,client):
    profile=script['profile']
    minimum=profile.get('script_min_chars');maximum=profile.get('script_max_chars')
    if minimum is None or maximum is None:return
    for attempt in range(3):
        total=sum(len(normalize(s['narration'])) for s in script['scenes'])
        if minimum<=total<=maximum:return
        if attempt==2:raise ValueError(f'长版口播{total}字，未达到{minimum}～{maximum}字预算')
        count=len(script['scenes'])
        result=client.ask_json(
            f'调整长版口播预算，保持{count}个场景的id、顺序和内容主题。总计{minimum}到{maximum}个汉字。'
            f'每镜约{math.ceil(minimum/count)}到{maximum//count}字。只返回 scenes数组，每项仅id、narration和beats。'
            '根据既有证据压缩或扩展解释，不添加实验数字或编造事实。第一镜仍用短问句开场。'
            'beats的cue必须逐字出现在对应口播中，action保持合法。',json.dumps(script['scenes'],ensure_ascii=False))
        items=result.get('scenes')
        if not isinstance(items,list) or len(items)!=count:raise ValueError('预算修订改变场景数')
        by_id={item.get('id'):item for item in items}
        if set(by_id)!={s['id'] for s in script['scenes']}:raise ValueError('预算修订场景id不匹配')
        for scene in script['scenes']:
            item=by_id[scene['id']];require_strings(item,('narration',))
            scene.update(narration=item['narration'],beats=item.get('beats'))


def make_story(logic,terms,pages,profile,client=None,reviewer=None,draft=None):
    client=client or LLMClient()
    if reviewer is None:
        from config import load_settings
        reviewer=LLMClient(model=load_settings().review_model)
    outline=client.ask_json('为论文生成科普创意，只返回 hook(18字内具体问题)、promise(观众收获)、analogy(生活比喻及边界)、ending(回答开场并给观众一个实用启发)。创新不推断录用原因，应用不编造就业或临床成效。',json.dumps({'logic':logic,'style':profile['style']},ensure_ascii=False))
    require_strings(outline,('hook','promise','analogy','ending'))
    total=max(10,math.ceil(profile['target_seconds']/profile['scene_seconds']))
    counts={k:max(1,int(total*profile['stage_weights'][k])) for k in KEYS};counts['method']+=total-sum(counts.values())
    if total<=16 and counts['application']<2:
        counts['application']+=1;counts['method']-=1
    budget=max(25,round(profile['target_seconds']*profile['words_per_second']/total))
    selected=[p for p in pages if p['number'] in {1,2,3,4,5,6,7,8,16}]
    excerpts=_excerpts(selected)
    payload={'outline':outline,'logic':logic,'original_excerpts':excerpts,'scene_counts':counts}
    if total<=16:
        batches=[(None,total)]
    else:
        batches=[(module,count) for module,count in counts.items()]
    scenes=[]
    for module,count in batches:
        instruction=SCHEMA+f'本次必须生成{count}镜，每镜口播约{budget}个中文字符。'
        instruction+='语言示范：坏例子“可微图聚类提炼高阶结构”；好例子“先把相似的区域拉到一组，再让这组区域互相校对，别只相信自己的猜测”。至少一镜用“就像”讲具体生活类比并解释它与论文的联系。'
        if total<=16:
            instruction+='这是给完全不懂机器学习的人看的短片，禁止在口播和标题使用以下词，改用日常动作解释：'+','.join(SHORT_JARGON)+'。方法只解释有把握的区域、相似区域组、旧经验和新差异，不堆算法名。结果只用两项主实验平均DSC，不使用长期实验的另一套指标来挤占时间。'
        if module:instruction+=f'只写当前模块{module}，不可重复已经覆盖的内容；不要再次抛开场问题。'
        else:instruction+='一次写完完整短片，严格遵守scene_counts的五模块数量与顺序。'
        last_error=None
        previous=None
        for attempt in range(3):
            if draft is not None and attempt==0 and not scenes:
                response=draft
            elif previous is not None and last_error and ('术语' in last_error or '触发词' in last_error):
                response=client.ask_json('只修正草稿的文字与动作cue。保持场景数、模块、evidence_ids、metrics不变；可以调整标题、口播、标签、beats。cue必须原样出现在修正后的口播中。返回完整scenes。'+last_error,
                    json.dumps({'draft':previous,'style_example':'先把相似的区域拉到一组，再让它们互相校对。','forbidden_short_terms':SHORT_JARGON},ensure_ascii=False))
            else:
                response=client.ask_json(instruction+(f'上次校验失败：{last_error}；在previous_invalid_response基础上修正，尽量保留已有正确内容。' if last_error else ''),json.dumps({**payload,'already_covered':[s['narration'] for s in scenes],'previous_invalid_response':previous},ensure_ascii=False))
            try:
                items=response.get('scenes')
                if not isinstance(items,list) or len(items)!=count:raise ValueError('场景数量不符')
                prepared=_prepare(items,excerpts,len(scenes),module)
                if total<=16:
                    jargon=[x for s in prepared for x in SHORT_JARGON if x.casefold() in (s['narration']+s['title']).casefold()]
                    if jargon:raise ValueError('短版仍有生硬术语，须人话改写：'+','.join(sorted(set(jargon))))
                    if not any('就像' in s['narration'] for s in prepared):raise ValueError('缺少具体生活类比')
                candidate={**outline,'scenes':[*scenes,*prepared]}
                validate_storyboard(candidate,pages,require_all_modules=module is None)
                scenes.extend(prepared);break
            except (ValueError,TypeError,KeyError) as exc:
                last_error=str(exc)
                previous=response
                if attempt==2:
                    (ROOT/'output'/'director_debug.json').write_text(json.dumps(response,ensure_ascii=False,indent=2))
                    raise ValueError(f'分镜校验失败：{last_error}') from exc
        print(f'编导完成：{module or "完整短片"}，{count}镜',flush=True)
    script={**outline,'version':2,'profile':profile,'target_seconds':profile['target_seconds'],
            'estimated_seconds':sum(len(normalize(s['narration'])) for s in scenes)/profile['words_per_second'],'scenes':scenes}
    validate_storyboard(script,pages)
    fit_narration_budget(script,client)
    validate_storyboard(script,pages)
    (ROOT/'output'/'candidate_story.json').write_text(json.dumps(script,ensure_ascii=False,indent=2),encoding='utf-8')
    reviews=[]
    for iteration in range(3):
        fit_narration_budget(script,client)
        validate_storyboard(script,pages)
        review=review_story(script,pages,reviewer);reviews.append(review)
        if review.get('approved') is True and review.get('issues')==[]:break
        if iteration==2:
            path=ROOT/'output'/'rejected_story.json';path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({'script':script,'reviews':reviews},ensure_ascii=False,indent=2))
            raise ValueError('独立审查仍未通过，脚本已保存供诊断')
        fixed=client.ask_json(SCHEMA+'修正审核发现的阻断问题，保持全部场景数和五模块顺序，不删除正确证据。只返回修正后的scenes。',json.dumps({'script':script,'issues':review.get('issues'),'original_excerpts':excerpts},ensure_ascii=False))
        items=fixed.get('scenes')
        if not isinstance(items,list) or len(items)!=len(scenes):raise ValueError('修订场景数量变化')
        script['scenes']=_prepare(items,excerpts)
        validate_storyboard(script,pages)
    script['reviews']=reviews;script['review_model']=getattr(reviewer,'model','test-reviewer')
    script['estimated_seconds']=sum(len(normalize(s['narration'])) for s in script['scenes'])/profile['words_per_second']
    (ROOT/'output'/'reviewed_story.json').write_text(json.dumps(script,ensure_ascii=False,indent=2),encoding='utf-8')
    # Summary generation is also reviewed against the source.
    summary=client.ask_json('根据已审核分镜生成一页总结。返回 title(18字内)、points(3条，每条20字内)、takeaway(面向学生的一个实际学习启发，30字内)。只陈述已有内容，不添加事实。',json.dumps(script,ensure_ascii=False))
    require_strings(summary,('title','takeaway'))
    if not isinstance(summary.get('points'),list) or len(summary['points'])!=3 or any(not isinstance(x,str) or not 1<=len(x)<=20 for x in summary['points']):raise ValueError('总结卡片格式无效')
    script['summary_card']=summary
    return finish_summary(script,client,reviewer,summary)


def finish_summary(script,client,reviewer,summary=None):
    prompt='生成一页总结，title不超过12字、points恰好3条每条不超过16字、takeaway标为学习建议且不超过20字。不能新增实验数据或许诺就业、临床效果。'
    if summary is None:
        summary=client.ask_json(prompt,json.dumps(script,ensure_ascii=False))
    for attempt in range(3):
        try:
            require_strings(summary,('title','takeaway'))
            if len(summary['title'])>18 or len(summary['takeaway'])>30:raise ValueError('总结标题或建议太长')
            if not isinstance(summary.get('points'),list) or len(summary['points'])!=3 or any(not isinstance(x,str) or not 1<=len(x)<=20 for x in summary['points']):raise ValueError('总结须恰好3条短句')
            summary_review=reviewer.ask_json('审核总结是否忠实于已审核脚本，是否新增实验事实或夸大效果。takeaway是作者学习建议，可据理解提出，但不能许诺就业或临床效果。只列阻断性事实问题，不因省略技术细节判错。返回 approved布尔、issues数组。',json.dumps({'summary':summary,'scenes':script['scenes']},ensure_ascii=False))
            if summary_review.get('approved') is True and summary_review.get('issues')==[]:
                script['summary_card']=summary;script['summary_review']=summary_review;return script
            error=json.dumps(summary_review.get('issues'),ensure_ascii=False)
        except (ValueError,TypeError) as exc:
            error=str(exc)
        if attempt==2:
            (ROOT/'output'/'rejected_summary.json').write_text(json.dumps({'summary':summary,'error':error},ensure_ascii=False,indent=2))
            raise ValueError('总结卡片审核未通过：'+error)
        summary=client.ask_json(prompt+'修正问题：'+error,json.dumps({'script':script,'previous':summary},ensure_ascii=False))
