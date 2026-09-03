# Contributing

感谢你对 Crypto Explorer 的关注。

## 开发环境

- Node.js 20+
- Python 3.11+
- Docker + Docker Compose（推荐）

最简单的完整启动方式：

```bash
docker compose up -d --build --wait
```

前端单独开发：

```bash
cd frontend
npm ci
npm run dev
```

后端单独开发：

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

## 提交前检查

```bash
cd frontend
npm run lint
npm run build

cd ../backend
python -m compileall -q .
```

也建议确认：

```bash
docker compose config
```

## Pull Request

1. 保持 PR 聚焦于一个明确问题。
2. 描述用户可见的行为变化和测试方式。
3. 不要提交 `.env`、数据库、日志、备份或密钥。
4. 数据模型变化应说明迁移/兼容策略。

