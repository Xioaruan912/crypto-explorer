# Crypto Explorer

[![CI](https://github.com/Xioaruan912/crypto-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/Xioaruan912/crypto-explorer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

面向密码学学习与论文研究的可视化研究工作台。它把文献检索、引用关系、时间线、阅读清单、收藏和 Markdown 阅读笔记放在一个可持久化的工作流里。

## 功能

- **文献图谱**：从种子论文展开引用关系，支持分类筛选和节点详情。
- **研究时间线**：按年份观察研究演化，并支持自定义年份范围。
- **早期基础论文探索**：提供“经典基础 / 基础论文优先”策略，可回溯早期高相关论文。
- **引文网络**：查看当前研究子图的直接关系、入度/出度和关键节点。
- **论文检索**：关键词、作者、会议/期刊、年份、Open Access 与排序筛选。
- **作者检索**：作者、机构、学术影响力和代表论文。
- **会议 / 期刊检索**：支持 CRYPTO、ASIACRYPT、IEEE S&P、CCS、USENIX Security 等常用缩写。
- **阅读清单**：待读 / 在读 / 已读、优先级和备注。
- **收藏 / 历史 / 仪表盘**：研究行为统一持久化并可回溯。
- **Markdown 笔记**：网页编辑、本地 `.md` 导入、论文关联和 `.md` 导出。
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
```

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_PORT` | `3000` | 前端公开端口 |
| `LOG_LEVEL` | `INFO` | 后端日志级别 |
| `ENABLE_EPRINT_LOOKUP` | `false` | 是否额外匹配 IACR ePrint |
| `SEMANTIC_SCHOLAR_API_KEY` | 空 | 可选；未配置时仍可通过 OpenAlex 容错 |

## 数据持久化

Compose 使用命名卷 `crypto_explorer_data`，数据库位于容器内：

```text
/app/data/research.db
```

数据库当前用于保存：

- 阅读清单与阅读状态
- 收藏
- 搜索历史
- 用户资料
- Markdown 论文笔记

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

## CI

GitHub Actions 会在 `main` push 和 Pull Request 上执行：

1. Frontend `npm ci` / lint / production build
2. Backend dependency install / Python compile / FastAPI import smoke test
3. Docker Compose config / image build

## 安全

- 不要提交真实 `.env`。
- 不要提交 SQLite 数据库和阅读笔记备份。
- 不要在 Issue 中公开 Token、密码或 API key。
- Semantic Scholar API key 应只通过运行环境注入。

安全问题请参阅 [SECURITY.md](SECURITY.md)。

## License

[MIT](LICENSE)

