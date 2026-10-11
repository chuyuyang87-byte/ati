# Paper2Video：从论文到动态科普视频

纯 Python 流水线：PDF → 术语与五模块分析 → 编导与分镜 → 独立事实审查 →
词级配音与动作时间戳 → 动态示意图、数据图、字幕、配乐 → MP4与图文推文。

## 安装与配置

Python3.10+，FFmpeg由imageio-ffmpeg提供，中文字体自动查找Noto/微软雅黑/苹方。

```bash
cd /workspace/ati/paper2video
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

首次使用将 `.env.example` 复制为 `.env`（勿覆盖已有文件），或在云环境安全注入
`LLM_API_KEY`。不要把真实密钥发到聊天或提交Git。
默认 `LLM_MODEL=deepseek-chat` 写稿，`REVIEW_MODEL=deepseek-reasoner` 独立审查，
两者共用DeepSeek密钥，无需注册新服务；审查调用会增加API费用。
`python config.py` 仅显示密钥是否配置。

## 运行

十分钟长版（16:9），600秒为目标，实际时长须以真实配音测量：

```bash
python main.py /path/to/paper.pdf --output output/my-paper
```

竖屏短版（9:16，默认约90秒）：

```bash
python main.py /path/to/paper.pdf --profile science_short --output output/my-short
```

已有同一PDF的分析可用 `--analysis-dir output/my-paper`，程序核验正文再复用。
同一目录中分析和已审查分镜可用 `--reuse-analysis --reuse-story`；风格变动会拒绝
旧分镜。语音以正文、声音和语速的哈希缓存，重试不会混用旧配音。
`--prepare-only` 仅生成脚本、图示、总结和推文。
`--duration 120` 可调整内容目标。长版初始预算1500～2000汉字，仍需听感和真实时长校准。

## agent配置在哪里

- `AGENTS.md`：未来任务的操作规则。
- `docs/EDITORIAL_GUIDE.md`：叙事骨架、视听标准、心理目标与参考访问记录。
- `profiles/science_short.json` / `science_long.json`：尺寸、节奏、目标时长、语速、配乐等。
- `modules/story_director.py`：Hook、五模块分镜、生活比喻、引用编号、内容审核及修订。
- `modules/animated_renderer.py`：医院场景、错误反馈环、聚类移动、双路提示、数据增长、边界及总结。
- `modules/tts_engine.py`：整镜配音、词级时间戳、字幕分组及动画关键词事件。

每次审核结果保存进 `script.json`。字幕使用真实WordBoundary时间，句尾静音保持
无字幕，不按字数杜撰时间。音效和轻量电子配乐为Python原创，配音时自动ducking。
画面是简约机制示意，非真实医学图像；数字条形图使用0～100统一零基线并标来源页。

## Manim数学动画

Manim仅用于原文有公式或轨迹解释需求的镜头，使用固定Python模板，不执行模型生成
的Python或LaTeX。公式用Unicode文本动态书写，复杂TeX排版尚未实现；轨迹为明确标注的
示意点线运动。本次医学短片不强行加入无关机器人运动。

Debian13云环境，无root安装Cairo/Pango开发头文件到忽略目录 `.system/`：

```bash
python scripts/install_manim.py
```

此安装器保留APT签名、包校验和TLS验证。其他系统先按Manim官方文档准备Cairo/Pango，
再 `pip install -r requirements-manim.txt`。本实例已实际渲染公式与轨迹测试。

## 输出与单独测试

输出：`video.mp4`、`article.md`、`summary.png`、`subtitles.srt`、`script.json`、
`timeline.json`、`cards/`、`audio/`、`segments/`、`music.wav`。

```bash
python -m modules.pdf_parser /path/to/paper.pdf --output output/paper.json
python -m modules.term_extractor /path/to/paper.pdf --output output/my-paper/terms.json
python -m modules.logic_decomposer /path/to/paper.pdf --output output/my-paper/logic.json
python -m modules.script_writer output/my-paper --profile science_short
python -m modules.tts_engine output/my-paper
python -m modules.video_maker output/my-paper
python -m modules.article_writer output/my-paper
python -m unittest discover -s tests -v
```

单独编导需要该目录中有PDF解析得到的 `paper.json`，用于引文验证。
扫描件需先OCR；公式、表格、双栏PDF仍可能提取失真；自动审查不代替专业人工核验。
网络需允许 `api.deepseek.com` 和 `speech.platform.bing.com`（HTTPS/WebSocket）。
TTS会加载平台 `SSL_CERT_FILE` CA，保持TLS验证开启。

## 参考与实际效果

用户参考：全全探索局《为什么深海巨兽，偏偏就是找不到？》。只能核实用户分享的
标题，云代理拒绝正文；尚未观看视频或验证互动量。因此编导标准是创作假设，
不是已验证的爆款公式。真实发布后的留存、完播、收藏数据才用于效果迭代。

旧样片 `demo/paper2video-spegc.mp4` 为6分24秒文字卡片版，保留用于对比。
新版 [demo/v2/video.mp4](../demo/v2/video.mp4) 实测86.87秒，12个动态分镜，另附推文、总结图、字幕与验证记录；不把短版或旧样片称为已完成十分钟动画长版。

## v3 研究入门版（当前默认）

默认 `research_long`，目标十分钟；三分钟验证配置为 `research_bridge`。
旧 `science_short` / `science_long` 仍可显式选择。

```bash
python main.py /path/to/paper.pdf --profile research_bridge --output output/research --prepare-only
```

新增原PDF页面提取与哈希追溯、术语首次解释卡、输入输出和步骤要求、实验条件、局限与复现行动，以及独立教学审查。配置见 [研究版说明](docs/RESEARCH_EDITION.md)。
原页展示已接入渲染，但自动识别图框和高质量逐层重绘尚未完成；不要把配置更新称为新版视频已制作。
