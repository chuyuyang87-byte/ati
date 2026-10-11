# 研究入门版配置 v3

受众：有基础、希望读懂方法并开始研究的学生。旧零基础短版仍保留。
默认research_long目标600秒；research_bridge目标180秒，用于先验证方法与实验讲解。

## 内容合同

正式术语→全称→直观含义→本论文作用→类比边界。至少两个核心术语进入旁白，不能只在JSON里写说明。
方法讲清输入、输出、中间步骤和改进动机。实验讲清指标、任务/数据集、基线与比较条件；有消融必须解释，没有则明确未报告。
局限与复现至少各一镜：原文报告的代码、算力、参数才可当事实，缺项明确未说明；研究建议标为我们建议。
每镜learning_goal、teaching_role、visual_steps与真实口播触发beats共同约束生成。

## 素材与视觉

source_assets自动渲染PDF原页，记录原文件及图片SHA256、物理页码。方法和结果各至少一镜用对应原页。
默认整页，模型不能猜图框坐标。明确知道位置时才用source_crop归一化坐标裁剪。
原页显示配合按实际口播逐步展开的注释；不能把生成图片当实验影像。
术语镜左侧显示全称、含义与论文作用；长说明仍在旁白与推文中。
保留原页是素材追溯的起点，不等于已经完成专业重绘。高清图框自动识别、区域级高亮、复杂结构图逐层重绘仍需后续迭代。
不自动抓取外部视频、图库或音乐，避免来源及授权不明。

## 审查与运行

先源文引用/数值校验，再独立事实审查，再研究教学审查。教学审查失败自动修订至多两轮，重新事实审查；仍失败停止，不输出已通过视频。
术语、原图、局限或复现缺失不能靠提示语绕过。

```bash
python main.py paper.pdf --profile research_bridge --output output/research-preview --prepare-only
python main.py paper.pdf --profile research_long --output output/research-long
python -m unittest discover -s tests -v
```

prepare-only会产生脚本、原页、分镜、总结图和推文，不产生MP4。真实配音时长以成片检查为准。
无需新API；DeepSeek写稿与独立审查沿用现有密钥，增加的审核会增加调用费用。
