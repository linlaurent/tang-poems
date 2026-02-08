# 唐诗三百首学习应用

一个使用 Streamlit 构建的交互式学习应用，用于学习《唐诗三百首》。

## 功能特性

- **📖 浏览模式**：浏览和搜索唐诗，支持按标题、作者或内容搜索
- **🎯 测验模式**：通过选择题和填空题测试对唐诗的掌握程度
- **🃏 闪卡模式**：使用闪卡方式记忆诗歌，可标记已掌握或需练习的诗歌
- **📊 数据分析**：查看学习进度时间线、连续学习天数、个性化学习建议
- **✍️ 笔顺查询**：查询汉字的笔画顺序（需要 cnchar-data 数据集，可选功能）
- **🔤 简繁切换**：支持简体中文和繁體中文显示，可在侧边栏设置中切换（默认简体）

## 技术栈

- **Streamlit**：Web 应用框架
- **Python 3.9+**：编程语言
- **uv**：快速 Python 包管理器
- **requests**：HTTP 请求库
- **beautifulsoup4**：HTML 解析库（用于数据抓取）

## 安装与运行

### 前置要求

- Python 3.9 或更高版本
- [uv](https://github.com/astral-sh/uv) 包管理器

### 安装步骤

1. 克隆或下载项目到本地

2. 使用 uv 安装依赖：

```bash
uv sync
```

或者如果 uv 未安装，先安装 uv：

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

3. （可选）获取笔顺数据：如需使用笔顺查询功能，请克隆 cnchar-data 数据集：

```bash
git clone --depth 1 https://github.com/cn-char/cnchar-data.git data/cnchar-data
```

4. 运行应用：

```bash
uv run streamlit run app.py
```

或者激活虚拟环境后运行：

```bash
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

streamlit run app.py
```

应用将在浏览器中自动打开，默认地址为 `http://localhost:8501`

## 项目结构

```
poems/
├── pyproject.toml          # uv 项目配置和依赖
├── uv.lock                 # uv 锁定文件（自动生成）
├── app.py                  # 主 Streamlit 应用
├── src/
│   ├── __init__.py
│   ├── analytics.py        # 数据分析模块
│   ├── data_loader.py      # 诗歌数据加载模块（支持简繁切换）
│   ├── quiz.py             # 测验模式逻辑
│   ├── flashcards.py       # 闪卡模式逻辑
│   ├── stroke_order.py     # 笔顺查询模块（使用 cnchar-data）
│   └── stroke_widget.py    # 笔顺交互组件
├── scripts/
│   ├── convert_to_simplified.py  # 繁体转简体转换脚本
│   ├── gather_poems.py     # 诗歌数据采集脚本
│   └── remove_duplicates.py # 去重脚本
├── data/
│   ├── 唐诗三百首.json      # 简体中文诗歌数据（默认）
│   ├── 唐诗三百首_繁体.json  # 繁體中文诗歌数据
│   └── cnchar-data/        # 笔顺数据集（可选）
└── README.md               # 项目文档
```

## 使用说明

### 浏览模式

- 在搜索框中输入关键词（标题、作者或内容）来过滤诗歌
- 使用分页按钮浏览不同页面的诗歌
- 每首诗显示标题、作者、朝代和完整内容

### 测验模式

- 选择测验类型：选择题或填空题
- 回答题目后查看正确答案
- 系统会跟踪你的得分和准确率
- 点击"下一题"继续练习

### 闪卡模式

- 查看诗歌的标题和作者
- 点击"显示内容"查看完整诗歌
- 标记诗歌为"已掌握"或"需练习"
- 使用导航按钮浏览不同的诗歌
- 查看学习进度统计

## 数据来源

诗歌数据存储在 `data/` 目录下，包含简体和繁体两个版本：

- `唐诗三百首.json`：简体中文版（默认）
- `唐诗三百首_繁体.json`：繁體中文版

可在侧边栏「设置」中切换简繁体。如果本地数据不可用，应用将尝试从公共 API 加载数据，或使用内置的示例数据作为后备方案。

## 开发

### 添加新功能

- 修改 `app.py` 添加新的页面或功能
- 在 `src/` 目录下添加新的模块
- 更新 `pyproject.toml` 添加新的依赖

### 运行测试

```bash
uv run pytest  # 如果添加了测试
```

## 许可证

本项目仅供学习和教育用途。

## 贡献

欢迎提交 Issue 和 Pull Request！

