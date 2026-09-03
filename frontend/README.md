# Crypto Explorer Frontend

Next.js 16 + React 19 frontend for [Crypto Explorer](../README.md).

## Development

```bash
npm ci
npm run dev
```

The production application normally runs through the repository-level Docker Compose setup, where `/api/*` requests are rewritten to the internal FastAPI service.

## Checks

```bash
npm run lint
npm run build
```

For full setup, persistence and deployment documentation, see the [root README](../README.md).

