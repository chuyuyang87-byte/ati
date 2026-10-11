"""Teaching requirements are a gate separate from factual approval."""
import json
from modules.llm_client import require_strings

RESEARCH_PROMPT='''
本段规则覆盖之前的短版视觉选择示例。这是研究入门版，不能删掉核心专业术语来换取通俗。保留正式术语，首次出现解释含义和本论文作用。
每镜额外提供 teaching_role（setup/term/mechanism/evidence/limitation/reproduction之一），
learning_goal（学生看完能回答什么），visual_steps（2到4条有因果顺序的视觉步骤）。
术语镜提供 term_card:{name,full_name,definition,paper_role,analogy_limit}，这些内容必须进入旁白，不能仅写隐藏字段。
全片至少两镜解释不同核心术语，全片至少两镜用原文素材，至少一镜method模块和一镜result模块的visual必须是source_page，而不是graph/comparison；source_page可保留metrics字段和正确数值。
原文素材用visual="source_page",source_page为PDF物理页码，source_crop=[左,上,右,下]为0到1坐标。
不能猜裁剪位置，默认[0,0,1,1]显示整页；labels是简短注释，beats是实际口播触发的重点。
方法必须说清输入、输出、关键步骤及改进动机；每一阶段对应原图或示意，禁止无意义圆点漂移。
实验必须解释指标含义、数据集或任务、基线及比较条件；有消融就解释组件贡献，没有则明确未说明。
全片至少一镜limitation，至少一镜reproduction：给出可执行的学习或复现动作；原文未报告的代码、算力、训练参数必须说未说明。
研究建议标为“我们建议”，不冒充作者结论；不把开源代码、显著性、会议录用或临床验证当已知事实。
短句用于屏幕，旁白可以严谨解释算法名；生活类比只作为辅助，必须说明失效边界。
'''


def validate_research(script):
    scenes=script['scenes'];roles=set();terms=set();source_modules=set();missing_terms=[]
    for s in scenes:
        require_strings(s,('teaching_role','learning_goal'))
        if s['teaching_role'] not in {'setup','term','mechanism','evidence','limitation','reproduction'}:raise ValueError('教学角色无效')
        roles.add(s['teaching_role'])
        steps=s.get('visual_steps')
        if not isinstance(steps,list) or not 2<=len(steps)<=4 or any(not isinstance(x,str) or not x.strip() for x in steps):raise ValueError('须提供2到4步视觉解释')
        if s['teaching_role']=='term':
            card=s.get('term_card')
            if not isinstance(card,dict):raise ValueError('术语镜缺少术语卡')
            require_strings(card,('name','full_name','definition','paper_role','analogy_limit'))
            if card['name'].casefold() not in s['narration'].casefold():missing_terms.append(card['name']+'@'+s.get('id',''))
            terms.add(card['name'].casefold())
        if s['visual']=='source_page':source_modules.add(s['module'])
    if missing_terms:raise ValueError('术语名称须进入口播：'+','.join(missing_terms))
    if len(terms)<2:raise ValueError('研究版至少解释两个不同核心术语')
    if not {'mechanism','evidence','limitation','reproduction'}<=roles:raise ValueError('研究版缺少机制、证据、局限或复现')
    if not {'method','result'}<=source_modules:raise ValueError('方法和实验均须绑定原文素材')


def audit_research(script,pages,reviewer):
    validate_research(script)
    result=reviewer.ask_json('你是研究入门教学审查员。检查旁白而非仅元数据：术语首次出现是否解释正式名称、含义、论文作用及类比边界；机制是否明确输入输出和关键因果；指标、基线、比较条件和消融是否讲清；局限与复现行动是否有用且有证据。原图页是否包含对应方法或结果。教学缺失应阻断。不能因为有标签就认为讲过。论文未报告项允许明确未说明。返回approved布尔和issues字符串数组。',json.dumps({'script':script,'original_pages':pages},ensure_ascii=False))
    if result.get('approved') is not True or result.get('issues')!=[]:raise ValueError('研究教学审查未通过：'+json.dumps(result,ensure_ascii=False))
    return result
