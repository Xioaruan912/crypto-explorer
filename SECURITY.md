# Security Policy

## Supported version

当前维护分支为 `main`。

## Reporting a vulnerability

请不要把真实凭据、服务器密码、API key 或包含私人研究数据的 SQLite 数据库提交到公开 Issue。

如果发现安全问题，优先通过仓库所有者的 GitHub 联系方式私下报告，并提供：

- 受影响的组件或接口
- 复现步骤
- 影响范围
- 建议修复方式（如有）

项目默认不会把 `.env`、SQLite 数据库、日志和备份文件纳入版本控制。

## Security controls

- 默认管理员账号仅用于首次初始化，首次登录后强制修改密码。
- 密码使用带随机盐的 `scrypt` 哈希保存，不保存明文密码。
- 会话 token 使用高熵随机值，数据库只保存 token 的 SHA-256 摘要。
- 会话 Cookie 为 `HttpOnly`、`SameSite=Strict`；HTTPS 部署应启用 `COOKIE_SECURE=true`。
- 所有研究 API 需要登录；所有写接口需要会话绑定的 CSRF token。
- 连续 5 次登录失败会锁定账号 15 分钟。
- FastAPI 文档生产环境默认关闭。
- 备份导入限制大小、格式和数据行数，并在 SQLite 事务中执行；失败整体回滚。
- 备份导出不包含密码哈希、会话 token 或 CSRF token。
- OpenAlex 路径 ID 使用固定格式校验，外部 URL 只允许 `http` / `https`。
- 响应启用 `nosniff`、`DENY` frame policy、严格 referrer policy、permissions policy 和 CSP。

## Transport security

应用支持直接通过 HTTP 自托管，但 HTTP 无法保护网络传输中的登录凭据和会话 Cookie。公开互联网部署应放在 HTTPS 反向代理后，并设置 `COOKIE_SECURE=true`。

