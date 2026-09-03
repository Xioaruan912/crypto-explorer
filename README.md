# Crypto Explorer

[![CI](https://github.com/Xioaruan912/crypto-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/Xioaruan912/crypto-explorer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向密码学学习与论文研究的可视化研究工作台。它把文献检索、引用关系、时间线、阅读清单、收藏和 Markdown 阅读笔记放在一个可持久化的工作流里。界面采用统一的橙色研究工作台视觉体系，成功、警告与错误状态仍保留必要的语义色。

## 功能

- **文献图谱**：从种子论文展开引用关系，支持分类筛选和节点详情。
- **研究时间线**：按年份观察研究演化，并支持自定义年份范围。
- **早期基础论文探索**：提供“经典基础 / 基础论文优先”策略，可回溯早期高相关论文。
- **自学习学术术语解析**：中文查询优先使用本地 SQLite 已确认映射；未知术语可通过中文 Wikipedia / Wikidata、CSO、NIST 与 OpenAlex 交叉验证后学习并缓存。用户可在“学术术语库”中修正英文术语、增加别名和人工确认。
- **概念谱系 / 开山论文**：先从现代锚点沿 references 向过去寻找概念源头；确定开山论文后切换到 cited-by 向未来展开。
- **从开山开始学**：默认主线为“开山论文 → 早期奠基 → 关键演进 → 现代代表”，时间只向前；开山之前的理论依赖改成可选背景，不再混入默认主线。
- **规范文献元数据**：学习路径中的关键论文会使用 DBLP / Crossref 等来源校正文献重印年份、会议与 DOI，并保留原数据源年份用于透明比对。
- **基础论文抽取**：先构建密码学基础论文候选池，再均匀随机抽取；不设置稀有度或概率等级，并尽量避开最近 10 次重复论文。
- **引文网络**：查看当前研究子图的直接关系、入度/出度和关键节点。
- **论文检索**：关键词、作者、会议/期刊、年份、Open Access 与排序筛选。
- **作者检索**：作者、机构、学术影响力和代表论文。
- **会议 / 期刊检索**：支持 CRYPTO、ASIACRYPT、IEEE S&P、CCS、USENIX Security 等常用缩写。
- **阅读清单 / 每周 TODO**：把论文排到周一至周日，支持阅读、笔记、复习、复现、自定义任务与独立完成状态。
- **收藏 / 历史 / 仪表盘**：研究行为统一持久化并可回溯；默认进入仪表盘并直接展示本周阅读计划。
- **Markdown 笔记**：网页编辑、本地 `.md` 导入、论文关联和 `.md` 导出。
- **账户与安全**：内置单管理员登录、强制修改默认密码、HttpOnly 会话、CSRF 防护和登录锁定。
- **备份 / 恢复**：账户界面可导出、导入完整研究数据备份；登录凭据与会话不会进入备份。
- **SQLite 持久化**：阅读清单、收藏、搜索历史、个人资料和笔记都保存在本地数据库。

## 技术栈

| 层 | 技术 |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, React Flow, Recharts |
| Backend | FastAPI, Python 3.11 |
| Research data | Semantic Scholar + OpenAlex fallback/discovery |
| Persistence | SQLite (WAL mode) |
| Deployment | Docker Compose |

## 架构

```text
Browser
  |
  v
Next.js :3000
  |  /api/* rewrite
  v
FastAPI :8000 (internal)
  |-- Semantic Scholar
  |-- OpenAlex
  `-- SQLite /app/data/research.db
```

浏览器只访问 Next.js；FastAPI 默认不直接暴露宿主机端口。

## 快速开始

### Docker Compose（推荐）

```bash
cp .env.example .env
docker compose up -d --build --wait
```

默认访问：

```text
http://localhost:3000
```

首次初始化登录：

```text
用户名：admin
密码：123456
```

首次登录后系统会强制修改默认密码（新密码至少 10 个字符）；在完成改密前，其他研究 API 不可用。

查看状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f --tail=200
```

停止：

```bash
docker compose down
```

> 不要使用 `docker compose down -v`，除非你明确希望删除 SQLite 持久化卷。

## 配置

`.env.example`：

```dotenv
APP_PORT=3000
LOG_LEVEL=INFO
ENABLE_EPRINT_LOOKUP=false
SEMANTIC_SCHOLAR_API_KEY=
OPENALEX_API_KEY=
OPENALEX_MAILTO=
CROSSREF_MAILTO=
SESSION_TTL_HOURS=720
SESSION_RENEW_BEFORE_HOURS=168
COOKIE_SECURE=false
ENABLE_API_DOCS=false
MAX_REQUEST_BYTES=6291456
```

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_PORT` | `3000` | 前端公开端口 |
| `LOG_LEVEL` | `INFO` | 后端日志级别 |
| `ENABLE_EPRINT_LOOKUP` | `false` | 是否额外匹配 IACR ePrint |
| `SEMANTIC_SCHOLAR_API_KEY` | 空 | 可选；未配置时仍可通过 OpenAlex 容错 |
| `OPENALEX_API_KEY` | 空 | 可选；频繁使用概念谱系时建议配置以提升 OpenAlex 配额 |
| `OPENALEX_MAILTO` | 空 | 可选；OpenAlex polite pool 联系邮箱 |
| `CROSSREF_MAILTO` | 空 | 可选；Crossref 文献元数据查询联系邮箱，未设置时也可工作 |
| `SESSION_TTL_HOURS` | `720` | 登录会话有效时长，默认 30 天 |
| `SESSION_RENEW_BEFORE_HOURS` | `168` | 会话剩余不足该时长时自动续期，默认剩余 7 天时续回 30 天 |
| `COOKIE_SECURE` | `false` | HTTPS 部署时应设置为 `true` |
| `ENABLE_API_DOCS` | `false` | 是否开放 FastAPI `/docs` 和 OpenAPI 文档 |
| `MAX_REQUEST_BYTES` | `6291456` | 单次请求体最大字节数 |

## 数据持久化

Compose 默认把持久化数据直接映射到项目根目录的 `./data`，容器内仍然使用 `/app/data`：

```text
宿主机：./data/research.db
容器内：/app/data/research.db
```

可以通过 `CRYPTO_EXPLORER_DATA_DIR` 把宿主机数据目录改到其他位置。例如：

```dotenv
CRYPTO_EXPLORER_DATA_DIR=/srv/crypto-explorer/data
```

如果使用默认配置，并且项目部署在 `/root/crypto-explorer`，服务器备份脚本只需要备份：

```text
/root/crypto-explorer/data/
```

该目录包含 SQLite 主数据库以及 SQLite 运行时可能出现的 `-wal` / `-shm` 文件。代码已经保存在 GitHub，`node_modules`、`.next`、Docker 镜像、日志和概念谱系缓存均不需要单独作为代码备份对象。

数据库当前用于保存：

- 阅读清单与阅读状态
- 每周阅读 TODO 与任务完成状态
- 收藏
- 搜索历史
- 搜索时的原始中文词、实际学术检索词、语言模式和规范化术语
- 自学习的中文 / 英文学术术语映射、别名、来源证据和人工确认结果
- 论文随机抽取历史
- 用户资料
- Markdown 论文笔记
- 登录账号、密码哈希和会话（不会被备份导出）

账户页支持导出 / 导入研究备份。备份格式包含阅读清单、每周 TODO、收藏、搜索历史、论文抽取历史、个人资料、Markdown 笔记和已经学习/确认的学术术语映射，不包含密码哈希、Cookie 或服务器会话。概念谱系与规范元数据缓存属于可再生成的派生数据，不进入备份。

数据库、`.env`、日志和备份文件默认被 `.gitignore` 排除，不应提交到 GitHub。

## 本地开发

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

检查：

```bash
npm run lint
npm run build
```

### Backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

检查：

```bash
python -m compileall -q .
```

## 项目结构

```text
crypto-explorer/
├── backend/                 # FastAPI、研究数据源、SQLite、图谱分析
├── frontend/                # Next.js UI
├── .github/                 # CI、Issue/PR 模板
├── docker-compose.yml       # 生产/自托管编排
├── .env.example             # 环境变量模板
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

## 数据源与容错

研究图谱优先使用 Semantic Scholar。匿名请求遇到限流或上游异常时，系统可使用本地缓存或 OpenAlex 继续构建研究数据。

论文 / 作者 / 会议期刊检索主要由 OpenAlex 提供实时数据。

中文术语解析会组合本地 SQLite、中文 Wikipedia / Wikidata 跨语言实体、Computer Science Ontology (CSO 3.5)、NIST CSRC 与 OpenAlex 学术语料证据；高置信度结果会写入本地术语库。CSO 数据遵循其发布的 CC BY 4.0 许可，Wikidata 结构化数据为 CC0。

学习路径中的关键文献会使用 DBLP 与 Crossref 进行规范元数据校验，以优先显示论文的原始发表年份而不是后续 reprint / 电子版年份。

## CI

GitHub Actions 会在 `main` push 和 Pull Request 上执行：

1. Frontend `npm ci` / lint / production build
2. Backend dependency audit / Bandit static scan / Python compile / FastAPI import smoke test
3. Backend authentication / CSRF / session / backup security regression smoke test
4. Concept Genealogy、开山后前向演化与中文学术查询回归测试
5. 自学习术语解析与规范文献元数据回归测试
6. Docker Compose config / image build

## 安全

- 不要提交真实 `.env`。
- 不要提交 SQLite 数据库和阅读笔记备份。
- 不要在 Issue 中公开 Token、密码或 API key。
- Semantic Scholar API key 应只通过运行环境注入。
- 默认账号只用于首次初始化。首次登录后必须立即更换密码。
- 生产环境若通过 HTTPS 访问，请把 `COOKIE_SECURE=true`。
- 生产环境默认关闭 FastAPI API 文档。
- 所有研究 API 都要求登录；POST / PUT / PATCH / DELETE 还要求会话绑定 CSRF token。
- 连续 5 次错误登录后会对错误尝试节流 15 分钟；正确凭据仍可恢复登录。
- 修改用户名或密码后会轮换会话并撤销旧会话。
- CI 持续运行 `npm audit`、`pip-audit`、Bandit 和认证/备份安全回归测试。
- 外部论文 / 作者 / 会议链接在前端只允许 `http` / `https` 协议。

安全问题请参阅 [SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE)

