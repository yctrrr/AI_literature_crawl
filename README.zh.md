# AI Literature Crawl

<!-- README-I18N:START -->

[English](./README.md) | **中文**

<!-- README-I18N:END -->

## 概览

AI Literature Crawl 是一个面向 Nature 平台文献的自动化工作流。它会从可配置的 feed 和搜索结果中发现候选文章，按期刊名称进行过滤，下载正文 PDF 和第一个可用补充文件，使用 DeepSeek 将论文归类到本地主题目录，并把总结追加到累计 Markdown 文件中。

默认配置面向空气质量、气候变化和能源转型相关文献。

## 功能

- 优先从 Nature feed / 文章列表发现候选文章。
- 当 feed 结果不足时，使用 Nature 搜索作为受控补充来源。
- 在应用 `--limit` 或 `download.max_articles_per_run` 之前，先按 `nature.journal_name_required_term` 过滤期刊名称。
- 只下载可访问 PDF 的文章。
- 优先使用 Nature 页面上的真实下载按钮，而不是只依赖 PDF metadata 链接。
- 当补充材料是真实可下载文件时，下载第一个 supplementary / additional 文件。
- 正文 PDF 命名为 `Journal-FirstAuthor-Year-Title.pdf`。
- 补充材料命名为 `Supp-Journal-FirstAuthor-Year-Title.<ext>`。
- 通过 OpenAI-compatible API 调用 DeepSeek V4 Pro。
- 将每篇文章归类到本地主题文件夹。
- 通过 DOI / URL 元数据避免重复下载。
- PDF 文本抽取遇到不可读页面时会跳过该页，不会中断整次运行。
- 生成 EndNote 导入文件，并把正文 PDF 与匹配的 `Supp-*` 文件挂到同一条记录下。
- 支持 Windows Task Scheduler 每周自动运行。

## 路径

- 项目目录：当前仓库根目录
- 分类目录来源：默认 `./example_taxonomy`
- 文献归档目录：默认 `./data/archive`

这些路径都可以在 `config.yaml` 中修改。

## 项目结构

```text
literature_crawl/
  config.yaml
  README.md
  prepare_endnote_import.py
  requirements.txt
  run_weekly.py
  scheduler.ps1
  src/
    archive_manager.py
    article_fetcher.py
    config.py
    llm.py
    models.py
    pdf_utils.py
    source_discovery.py
    state_manager.py
    utils.py
```

## 安装

```powershell
git clone https://github.com/yctrrr/AI_literature_crawl.git
cd AI_literature_crawl
pip install -r requirements.txt
playwright install chromium
$env:DEEPSEEK_API_KEY = "..."
```

如果需要让定时任务长期运行，建议设置持久环境变量：

```powershell
setx DEEPSEEK_API_KEY "your_key_here"
```

执行 `setx` 后需要重新打开 PowerShell。

如果需要机构登录权限，先用可见浏览器运行一次，并在弹出的 Chrome 中完成登录：

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false
```

`--limit 1` 只用于测试。正式运行默认使用 `config.yaml` 中的 `download.max_articles_per_run`，当前默认值是 `20`。

## 配置

主要配置在 `config.yaml` 中：

```yaml
keywords:
  - air pollution
  - climate change
  - energy transition

nature:
  journal_name_required_term: Nature

download:
  max_articles_per_run: 20

llm:
  provider: deepseek
  model: deepseek-v4-pro
  api_key_env: DEEPSEEK_API_KEY
  base_url: https://api.deepseek.com
```

不要把 API key 直接写入 `config.yaml`，应使用环境变量。

## 常用命令

只发现候选文章，不下载、不调用模型：

```powershell
python .\run_weekly.py --config .\config.yaml --dry-run
```

下载并总结 1 篇文章：

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false
```

下载并总结前 10 篇符合期刊过滤条件的候选文章：

```powershell
python .\run_weekly.py --config .\config.yaml --limit 10 --headless false
```

按 `download.max_articles_per_run` 正式运行：

```powershell
python .\run_weekly.py --config .\config.yaml --headless false
```

只下载和分类，不生成总结：

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false --no-summarize
```

从已下载文献生成 EndNote 导入文件：

```powershell
python .\prepare_endnote_import.py
```

生成的 `.enw` 文件会把正文 PDF 和匹配的 `Supp-*` 文件放在同一条 EndNote 记录下，并添加 `AI_crawl` 关键词，便于分组。

## 每周定时任务

注册默认每周一 09:00 运行的 Windows 定时任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler.ps1
```

定时任务执行的命令是：

```powershell
python <repo>\run_weekly.py --config <repo>\config.yaml
```

## 输出文件

- `_download\Journal-FirstAuthor-Year-Title.pdf`
- `_download\Supp-Journal-FirstAuthor-Year-Title.<ext>`，分类移动前的临时位置
- `<Category>\Journal-FirstAuthor-Year-Title.pdf`
- `<Category>\Supp-Journal-FirstAuthor-Year-Title.<ext>`
- `<Category>\Journal-FirstAuthor-Year-Title.metadata.json`
- `_state\processed_articles.jsonl`
- `_state\pending_no_pdf.jsonl`
- `_state\filtered_articles.jsonl`
- `_state\failed_downloads.jsonl`
- `_state\run_log.jsonl`
- `_summaries\summary.md`
- `_endnote_import\AI_crawl_latest.enw`

`summary.md` 中每篇文章的 Markdown 主标题使用最终 PDF 文件名去掉 `.pdf` 后的形式，方便直接定位到下载文件。

## 避免重复下载

程序通过以下信息避免重复下载：

- `_state\processed_articles.jsonl`
- `_state\filtered_articles.jsonl`
- 已存在的 `<Category>\*.metadata.json`
- 优先使用 DOI，其次使用来源 URL

只要某篇文章已经下载或被过滤过，后续正式运行就会跳过。缺失的总结可以通过后续修复流程单独补齐。

## 注意事项

- Nature 页面结构可能变化，选择器后续可能需要维护。
- `nature.journal_name_required_term` 会在应用 `--limit` / `download.max_articles_per_run` 之前过滤掉期刊名称不包含指定文本的文章。
- PDF 文本抽取会跳过不可读页面，并记录抽取失败，不会中断整次运行。
- 需要机构权限的 PDF 可能依赖已登录的 Chrome profile。
- 搜索 fallback 会受到 `delay_seconds` 限速控制。
