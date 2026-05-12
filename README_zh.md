# astrbot_plugin_markdown

[AstrBot](https://github.com/AstrBotDevs/AstrBot) 的 Markdown 转图片渲染插件。
当 LLM 回复包含 Markdown 语法时，自动将其渲染为高质量 PNG 截图，
使用 [Playwright](https://playwright.dev/python/) 驱动的无头 Chromium 浏览器。

渲染引擎采用与 Visual Studio Code 相同的库：
[markdown-it](https://github.com/markdown-it/markdown-it) 解析 Markdown，
[@vscode/markdown-it-katex](https://github.com/microsoft/vscode-markdown-it-katex)
渲染 LaTeX 公式，[highlight.js](https://highlightjs.org/) 进行代码语法高亮。
所有渲染后的 HTML 在注入 DOM 前均经过
[DOMPurify](https://github.com/cure53/DOMPurify) 消毒，防止 XSS 攻击。

[English](README.md)

## 功能

- 围栏代码块，支持 190+ 种语言的语法高亮
- 行内和块级 LaTeX 数学公式（`$...$`、`$$...$$`、`\(...\)` 和 `\[...\]`）
- 上标（`^text^`）、下标（`~text~`）、高亮（`==text==`）和脚注（`[^1]`）
- 完整 CommonMark 支持：标题、表格、列表、引用、链接、图片、分隔线
- 明亮 / 暗色主题，GitHub 风格样式，基于 GitHub 字体栈并补充
  Noto/CJK 回退，以兼容更多系统和语言
- 排版替换：`(tm)` → ™、`(c)` → ©、`--` → –、`---` → —
- 所有渲染引擎选项（markdown-it、KaTeX、highlight.js）均可在设置中配置，
  修改后即时生效，无需重启
- 基于 Markdown 语法评分和最小文本长度的智能触发
- 与 AstrBot 内置的文字转图片功能兼容共存
- DOMPurify HTML 消毒 — 所有渲染输出在注入前均经过消毒，
  `md_html` 和 `katex_trust` 可安全启用

## 环境要求

| 组件        | 版本      | 用途                                    |
|------------|-----------|----------------------------------------|
| AstrBot    | ≥ 4.0.0   | 宿主框架                                |
| Python     | ≥ 3.10    | 插件运行时                               |
| Playwright | ≥ 1.40.0  | 无头浏览器自动化（见 `requirements.txt`）   |
| Chromium   | —         | 由 Playwright 管理的浏览器二进制文件         |

Node.js 仅在重新构建 `dist/` 中的前端资源时需要。

## 安装

1. 在 AstrBot 管理面板中安装本插件：
   ```
   https://github.com/Li-Zheng-Rong/astrbot_plugin_markdown
   ```
2. 安装 Chromium 浏览器：
   ```bash
   playwright install chromium
   ```

如果运行时未找到 Chromium，插件会记录警告并将消息原样传递。

## 架构

```
on_decorating_result (priority 10)
│
├─ 读取插件配置
├─ 检查前置条件：启用状态、playwright 可用、llm_only 过滤
├─ 收集结果链中的前导 Plain 文本组件
├─ 评估 Markdown 评分和字符长度阈值
│
├─ renderer.py
│   ├─ 首次渲染时懒初始化 Playwright 浏览器
│   ├─ 加载 templates/render.html 及 dist/ 中的 JS/CSS 资源
│   ├─ page.evaluate("renderMarkdown(text, options)")
│   │   └─ options 包含 theme、fontSize、footer 和引擎配置
│   ├─ DOMPurify 在注入 DOM 前消毒渲染后的 HTML
│   ├─ 截图 #content 元素 → PNG 字节
│   └─ 复用浏览器页面；每 200 次渲染后重载
│
├─ 用 Image 替换前导 Plain 组件
└─ 设置 result.use_t2i_ = False 以禁止内置 t2i
```

## 配置

所有设置均通过 AstrBot 管理面板读取，Schema 定义在 `_conf_schema.json` 中。

### 插件行为

| 键                | 类型   | 默认值                  | 说明                                              |
|-------------------|--------|------------------------|-------------------------------------------------|
| `enabled`         | bool   | `true`                 | 插件总开关                                         |
| `llm_only`        | bool   | `true`                 | 仅处理 LLM 回复，跳过指令输出（如 `/help`）              |
| `char_threshold`  | int    | `100`                  | 触发渲染的最小文本长度（字符数）                          |
| `score_threshold` | int    | `2`                    | 触发渲染的最低 Markdown 语法评分                        |
| `width`           | int    | `800`                  | 视口和图片宽度（像素）                                  |
| `theme`           | string | `"light"`              | 颜色主题：`light` 或 `dark`                           |
| `font_size`       | int    | `16`                   | 基础字体大小（像素）                                    |
| `render_timeout`  | int    | `10`                   | 单次渲染最大等待时间（秒）                               |
| `footer`          | string | `"Powered by AstrBot"` | 图片底部页脚文字，留空则隐藏                              |

### 渲染引擎

以下设置控制 markdown-it、KaTeX 和 highlight.js 库。每次渲染时传递到浏览器页面，
修改后即时生效，无需重启插件。

| 键                       | 类型   | 默认值              | 说明                                                            |
|--------------------------|--------|--------------------|-----------------------------------------------------------------|
| `md_html`                | bool   | `false`            | 允许 Markdown 中的原始 HTML 标签，输出已由 DOMPurify 消毒                |
| `md_linkify`             | bool   | `true`             | 自动将纯文本 URL 转为可点击链接                                        |
| `md_typographer`         | bool   | `true`             | 排版替换：`(tm)` → ™、`(c)` → ©、`--` → –、`---` → —              |
| `md_quotes`              | string | `"\"\"''"`         | 排版引号替换字符（4字符）。默认保持 ASCII 直引号                           |
| `katex_throw_on_error`   | bool   | `false`            | LaTeX 语法错误时抛出异常而非内联显示错误                                 |
| `katex_output`           | string | `"htmlAndMathml"`  | KaTeX 输出格式：`html`、`mathml` 或 `htmlAndMathml`                |
| `katex_trust`            | bool   | `false`            | 允许 KaTeX 扩展命令（如 `\href`、`\url`），输出已由 DOMPurify 消毒       |
| `katex_escaped_delimiters` | bool | `true`             | 启用 LaTeX 数学分隔符 `\(...\)` 和 `\[...\]`                        |
| `hljs_ignore_illegals`   | bool   | `true`             | 代码含语法错误时仍继续高亮                                             |

## 命令

| 命令                       | 说明                  |
|----------------------------|-----------------------|
| `/md_theme <light\|dark>`  | 持久切换渲染主题         |
| `/md_test`                 | 渲染测试文档，覆盖所有支持的语法 |

## 安全性

所有由 markdown-it 渲染的 HTML 在注入页面 DOM 前均经过
[DOMPurify](https://github.com/cure53/DOMPurify) 消毒。DOMPurify 会剥离
`<script>` 标签、事件处理器属性（`onerror`、`onload` 等）、`javascript:` URI
及其他危险标记，同时保留安全的 HTML 格式和 MathML（KaTeX 所需）。

这意味着 `md_html` 和 `katex_trust` 可以安全启用 — 即使 LLM 输出包含恶意
HTML，也会在渲染前被消毒。

Chromium 浏览器以 `--no-sandbox` 启动以兼容 Docker 环境。DOMPurify 作为纵深
防御层，阻止任何注入内容在浏览器上下文中执行。

## 开发

### 目录结构

```
astrbot_plugin_markdown/
├── main.py                 插件入口（Star 子类）
├── renderer.py             Playwright 浏览器生命周期和截图管线
├── markdown_detect.py      基于正则的 Markdown 语法评分
├── _conf_schema.json       AstrBot 配置 Schema
├── metadata.yaml           插件元数据
├── requirements.txt        Python 依赖
├── templates/
│   └── render.html         Playwright 加载的 HTML 页面
├── src/
│   └── entry.js            JS 入口（esbuild 输入）
├── dist/                   预构建的浏览器资源（已提交）
│   ├── bundle.js           markdown-it + KaTeX + highlight.js + DOMPurify IIFE 包
│   ├── style.css           自定义 Markdown 样式
│   ├── katex.min.css       KaTeX 样式表
│   ├── fonts/              KaTeX 字体文件
│   ├── hljs-github-light.css
│   └── hljs-github-dark.css
├── package.json            JS 依赖清单
├── package-lock.json       JS 依赖锁文件（已提交）
├── build.mjs               esbuild 构建脚本
├── tests/
│   ├── test_markdown_detect.py
│   └── test_renderer.py
└── README.md
```

### 重新构建前端资源

修改 `src/entry.js` 或更新 JS 依赖后：

```bash
cd data/plugins/astrbot_plugin_markdown
npm install
npm run build
```

构建会生成 `dist/bundle.js` 并从 `node_modules/` 复制 CSS 和字体文件。
`package-lock.json` 和 `dist/` 均已提交，以确保可复现构建且运行时无需 Node.js。

### 运行测试

```bash
uv run pytest data/plugins/astrbot_plugin_markdown/tests/ -v
```

测试需要安装 Playwright 和 Chromium。检测测试为纯 Python，耗时不到一秒；
渲染集成测试会启动无头浏览器，总计约 40 秒。

## 许可证

参见 [LICENSE](LICENSE)。
