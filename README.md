# AI Literature Crawl / AI 文献自动抓取

## English

AI Literature Crawl is an automated literature workflow for Nature articles. It discovers articles by configurable keywords, downloads article PDFs plus the first available supplementary file, classifies papers into a local topic taxonomy with DeepSeek, and appends summaries to one cumulative Markdown document.

The current workflow is tuned for air quality, climate change, and energy transition literature.

### Features

- Discovers Nature candidates from feeds/article lists first.
- Uses Nature search as an optional fallback when feed results are insufficient.
- Downloads only articles with accessible PDFs.
- Downloads the first supplementary/additional file when it is a real downloadable file.
- Names PDFs as `Journal-FirstAuthor-Year-Title.pdf`.
- Names supplements as `Supp-Journal-FirstAuthor-Year-Title.<ext>`.
- Uses DeepSeek V4 Pro through an OpenAI-compatible API.
- Classifies each paper into folders.
- Avoids duplicate downloads using DOI/URL metadata.
- Updates one cumulative summary file.
- Supports Windows Task Scheduler for weekly runs.

### Paths

- Project: this repository root
- Category source: `./example_taxonomy` by default
- Archive root: `./data/archive` by default

These paths are configurable in `config.yaml`.

### Project Structure

```text
literature_crawl/
  config.yaml
  README.md
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

### Setup

```powershell
git clone https://github.com/yctrrr/AI_literature_crawl.git
cd AI_literature_crawl
pip install -r requirements.txt
playwright install chromium
$env:DEEPSEEK_API_KEY = "..."
```

For persistent scheduled runs:

```powershell
setx DEEPSEEK_API_KEY "your_key_here"
```

Restart PowerShell after using `setx`.

For institutional access, run once with a visible browser and complete login if needed:

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false
```

`--limit 1` is only for testing. Formal runs use `download.max_articles_per_run` from `config.yaml`; the current default is `20`.

### Configuration

Key settings live in `config.yaml`:

```yaml
keywords:
  - air pollution
  - climate change
  - energy transition

download:
  max_articles_per_run: 20

llm:
  provider: deepseek
  model: deepseek-v4-pro
  api_key_env: DEEPSEEK_API_KEY
  base_url: https://api.deepseek.com
```

Do not put API keys directly in `config.yaml`; use environment variables.

### Commands

Discovery only:

```powershell
python .\run_weekly.py --config .\config.yaml --dry-run
```

Download and summarize one paper:

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false
```

Download and summarize the top 10 relevant candidates:

```powershell
python .\run_weekly.py --config .\config.yaml --limit 10 --headless false
```

Formal run using `download.max_articles_per_run`:

```powershell
python .\run_weekly.py --config .\config.yaml --headless false
```

Download/classify without summary:

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false --no-summarize
```

### Weekly Scheduler

Register the default Monday 09:00 task:

```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler.ps1
```

The task runs:

```powershell
python <repo>\run_weekly.py --config <repo>\config.yaml
```

### Outputs

- `_download\Journal-FirstAuthor-Year-Title.pdf`
- `_download\Supp-Journal-FirstAuthor-Year-Title.<ext>` before classification/move
- `<Category>\Journal-FirstAuthor-Year-Title.pdf`
- `<Category>\Supp-Journal-FirstAuthor-Year-Title.<ext>`
- `<Category>\Journal-FirstAuthor-Year-Title.metadata.json`
- `_state\processed_articles.jsonl`
- `_state\pending_no_pdf.jsonl`
- `_state\failed_downloads.jsonl`
- `_state\run_log.jsonl`
- `_summaries\summary.md`

Each paper entry in `summary.md` uses the final PDF filename without `.pdf` as its Markdown title, so it can be matched directly to the downloaded file.

### Duplicate Handling

The crawler avoids repeat downloads using:

- `_state\processed_articles.jsonl`
- existing `<Category>\*.metadata.json`
- DOI first, source URL second

If a previous run downloaded a paper, later formal runs skip downloading it again. Missing summaries can be filled later with a separate repair workflow if needed.

### Notes

- Nature page structure can change, so selectors may need maintenance.
- Institution-protected PDFs may require a logged-in Chrome profile.
- Search fallback is intentionally rate-limited by `delay_seconds`.
- Keep `.browser_profile/` local; it is ignored by git and should not be uploaded.

## 中文

AI Literature Crawl 是一套面向 Nature 文章的自动化文献抓取流程。它可以根据自定义关键词发现文章，下载正文 PDF 和第一个可用附件，调用 DeepSeek 将文章归类到本地主题目录，并把文章总结追加到一个统一的 Markdown 文档中。

当前默认关键词面向空气质量、气候变化和能源转型相关文献。

### 功能

- 优先从 Nature feed / 文章列表发现候选文章。
- 当 feed 结果不足时，可启用 Nature 搜索页作为补充来源。
- 只下载可以获取 PDF 的文章。
- 只下载第一个真实可下载的 supplementary / additional 附件。
- 正文 PDF 命名为 `期刊-第一作者-年份-标题.pdf`。
- 附件命名为 `Supp-期刊-第一作者-年份-标题.<扩展名>`。
- 通过 OpenAI-compatible API 调用 DeepSeek V4 Pro。
- 根据目录结构将文章归类到对应主题文件夹。
- 通过 DOI / URL 元数据避免重复下载。
- 统一更新一个累计总结文档。
- 支持 Windows Task Scheduler 每周定时运行。

### 路径

- 项目目录：当前仓库根目录
- 分类目录来源：默认 `./example_taxonomy`
- 文献归档目录：默认 `./data/archive`

这些路径都可以在 `config.yaml` 中修改。

### 项目结构

```text
literature_crawl/
  config.yaml
  README.md
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

### 安装与配置

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

`--limit 1` 只用于测试。正式运行时默认使用 `config.yaml` 中的 `download.max_articles_per_run`，当前默认值是 `20`。

### 配置

主要配置在 `config.yaml` 中：

```yaml
keywords:
  - air pollution
  - climate change
  - energy transition

download:
  max_articles_per_run: 20

llm:
  provider: deepseek
  model: deepseek-v4-pro
  api_key_env: DEEPSEEK_API_KEY
  base_url: https://api.deepseek.com
```

不要把 API key 直接写进 `config.yaml`，应使用环境变量。

### 常用命令

只发现候选文章，不下载、不调用模型：

```powershell
python .\run_weekly.py --config .\config.yaml --dry-run
```

下载并总结 1 篇文章：

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false
```

下载并总结当前发现顺序下相关性较高的前 10 篇：

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

### 每周定时任务

注册默认每周一 09:00 运行的 Windows 定时任务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler.ps1
```

定时任务执行的命令是：

```powershell
python <repo>\run_weekly.py --config <repo>\config.yaml
```

### 输出文件

- `_download\期刊-第一作者-年份-标题.pdf`
- `_download\Supp-期刊-第一作者-年份-标题.<扩展名>`，分类移动前的临时位置
- `<分类>\期刊-第一作者-年份-标题.pdf`
- `<分类>\Supp-期刊-第一作者-年份-标题.<扩展名>`
- `<分类>\期刊-第一作者-年份-标题.metadata.json`
- `_state\processed_articles.jsonl`
- `_state\pending_no_pdf.jsonl`
- `_state\failed_downloads.jsonl`
- `_state\run_log.jsonl`
- `_summaries\summary.md`

`summary.md` 中每篇文章的 Markdown 主标题使用最终 PDF 文件名去掉 `.pdf` 的形式，方便直接定位到下载文件。

### 避免重复下载

程序通过以下信息避免重复下载：

- `_state\processed_articles.jsonl`
- 已存在的 `<分类>\*.metadata.json`
- 优先使用 DOI，其次使用来源 URL

只要某篇文章已经下载过，后续正式运行就会跳过。缺失的总结可通过后续修复流程单独补齐。

### 注意事项

- Nature 页面结构可能变化，选择器后续可能需要维护。
- 需要机构权限的 PDF 可能依赖已登录的 Chrome profile。
- 搜索 fallback 会受到 `delay_seconds` 限速控制。
- `.browser_profile/` 只应保存在本地，已经被 `.gitignore` 忽略，不应上传到 GitHub。
