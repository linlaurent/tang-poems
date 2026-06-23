# 诗词学习应用

一个使用 Streamlit 构建的中文诗词学习应用，支持《唐诗三百首》与可扩展诗词库的闪卡记忆、测验练习、学习分析、拼音与笔顺查询。

## 功能特性

- **🃏 闪卡模式**：逐首学习诗词，标记「已掌握」或「需练习」，并支持按状态、作者、标题和关键词快速定位。
- **🎯 测验模式**：通过选择题和填空题练习，可选择从已掌握、需练习或全部诗词中出题。
- **🔎 查拼音与字形**：输入字词、诗句或整段文本，查看拼音、笔画数、Unicode 信息和交互式笔顺。
- **📊 数据分析**：查看学习进度、连续学习天数、时间线、作者维度统计和个性化复习建议。
- **📚 多诗词库**：侧边栏可切换《唐诗三百首》和宋词语料；本地扩展库会自动并入当前语料。
- **🔤 简繁切换**：侧边栏可切换简体中文和繁體中文显示。
- **🤖 智谱 GLM 集成（可选）**：联网检索诗词、补充扩展库，并为诗词抓取或刷新释义。

## 技术栈

- **Python 3.9+**
- **Streamlit**：Web 应用框架
- **uv**：依赖和虚拟环境管理
- **pandas**：学习数据展示和分析
- **pypinyin**：标题排序、拼音查询
- **openai**：以 OpenAI-compatible SDK 调用智谱 GLM
- **requests / beautifulsoup4 / lxml**：数据抓取和解析脚本

## 安装与运行

### 前置要求

- Python 3.9 或更高版本
- [uv](https://github.com/astral-sh/uv) 包管理器

如果尚未安装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 安装依赖

```bash
uv sync
```

开发依赖（ruff、pre-commit）：

```bash
uv sync --extra dev
```

### 运行应用

```bash
uv run streamlit run app.py
```

应用会在浏览器中打开，默认地址为 `http://localhost:8501`。

### 可选配置

如需在访客模式之外自动设置默认用户：

```bash
export DEFAULT_POEM_USER="your-name"
```

如需使用联网检索和释义功能：

```bash
export ZHIPU_API_KEY="your-api-key"
```

如需完整笔顺数据，请克隆 `cnchar-data` 数据集：

```bash
git clone --depth 1 https://github.com/cn-char/cnchar-data.git data/cnchar-data
```

## 使用说明

### 闪卡模式

- 在侧边栏选择诗词库和简繁体显示。
- 输入用户名后，学习进度会按用户保存；访客模式不会持久保存进度。
- 可用筛选、作者下拉、标题下拉或关键词搜索跳转到指定诗词。
- 点击「联网搜诗」可从本地库或智谱 GLM 检索诗词，并保存到当前语料的扩展库。
- 支持导出和导入学习进度 JSON。

### 测验模式

- 选择出题范围和题型后开始练习。
- 选择题和填空题都会在提交后显示反馈。
- 测验题库会跟随当前诗词库和学习状态变化。

### 查拼音与字形

- 输入任意中文文本，应用会逐字显示拼音、笔画数和 Unicode。
- 下方交互区域支持悬停查看注音，双击单字查看笔顺。

### 数据分析

- 需要使用非访客用户并产生闪卡学习记录。
- 可查看整体进度、时间线、连续学习天数、作者统计和推荐复习列表。
- 支持导出分析数据 JSON。

## 数据与扩展库

本地数据位于 `data/`：

- `唐诗三百首.json`：简体《唐诗三百首》（默认）
- `唐诗三百首_繁体.json`：繁體《唐诗三百首》
- `poems_supplement.json`：唐诗扩展库
- `song_ci_supplement.json`：宋词扩展库
- `poem_explanations.json`：本地释义缓存
- `cnchar-data/`：笔顺数据集（可选）

加载数据时，应用优先读取本地语料，再合并对应扩展库。《唐诗三百首》在本地数据不可用时会尝试公共 API，失败后使用内置示例数据；宋词语料依赖本地文件或扩展库。

## 智谱释义与批量抓取

设置 `ZHIPU_API_KEY` 后，应用内可以联网检索诗词和查询释义。检索到的新诗词可写入当前诗词库对应的扩展 JSON。

命令行可对本地合并后的诗库批量写入 `data/poem_explanations.json`：

```bash
uv run python scripts/gather_poem_explanations.py --quiet-timing
uv run python scripts/gather_poem_explanations.py --all --skip-existing --sleep 0.5
```

代码中也可调用 `gather_explanations_for_poems`（定义于 `src/poem_web_supplement.py`）批量获取释义；入参为诗词字典列表，返回值为 `dict[诗词 id, 释义正文]`。

## 项目结构

```text
poems/
├── app.py                         # 主 Streamlit 应用
├── pyproject.toml                 # 项目配置、依赖和 ruff 设置
├── uv.lock                        # uv 锁定文件
├── src/
│   ├── analytics.py               # 学习分析
│   ├── data_loader.py             # 诗词库加载、简繁切换和扩展库合并
│   ├── flashcards.py              # 闪卡状态、进度持久化、导入导出
│   ├── poem_corpus_lookup.py      # 本地诗库检索辅助
│   ├── poem_explanations_store.py # 本地释义缓存读写
│   ├── poem_web_supplement.py     # 智谱联网搜诗和扩展库写入
│   ├── quiz.py                    # 测验逻辑
│   ├── stroke_order.py            # 笔画和笔顺数据读取
│   ├── stroke_widget.py           # 交互式笔顺组件
│   └── zhipu_glm.py               # 智谱 GLM 客户端封装
├── scripts/
│   ├── build_song_ci_database.py
│   ├── convert_to_simplified.py
│   ├── gather_poem_explanations.py
│   ├── gather_poems.py
│   └── remove_duplicates.py
├── data/
└── README.md
```

## 开发

格式化 Python 代码：

```bash
uv run ruff format
```

检查 lint：

```bash
uv run ruff check
```

当前仓库没有专门的测试目录；添加测试后可使用：

```bash
uv run pytest
```

## 许可证

本项目仅供学习和教育用途。

