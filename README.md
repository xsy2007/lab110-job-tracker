# lab110-job-tracker

110 实验室招新考核项目：一个真实数据驱动的岗位追踪应用。

## 技术栈

Python 3.12 · FastAPI · Jinja2 · SQLAlchemy · SQLite · httpx · BeautifulSoup · pytest · Docker

## 快速开始

```bash
uv sync --extra dev        # 安装依赖（含测试）
uv run python -m app.cli   # 采集所有来源（写入 data/lab110.db）
uv run python -m uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000 。预置账号（密码与用户名相同）：

| 账号 | 角色 |
|---|---|
| user1 / user2 | 普通用户 |
| maintainer | 维护（可采集，/maintenance） |

## 数据来源

| 来源 | 类型 | 说明 |
|---|---|---|
| 腾讯招聘 careers.tencent.com | 大厂官方 | JSON API，无需登录 |
| LinkedIn linkedin.com/jobs | 招聘平台 | guest 岗位接口，无需登录 |

## 代理说明（重要）

LinkedIn 的 guest 岗位接口在中国大陆网络下直连会返回 302（被重定向 / 机器人检测），
需经 HTTP 代理才能取到数据。代理是**完全可选**的：

- 通过环境变量 `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY` 配置（或写入 `.env`，参考 `.env.example`）。
- 代码中不硬编码任何代理地址。
- 没有代理时，LinkedIn 来源采集会记录 `FAILED` 并保留旧数据，**不影响腾讯来源**。

```bash
# 示例（.env.example 只有示例，不写真实秘密）
export HTTPS_PROXY=http://127.0.0.1:7890
```

## 目录

- `data/` — SQLite 数据库（Docker 用 volume 持久化）
- `evidence/` — 真实采集的原始响应（JSON/HTML）
- `snapshots/` — 回放数据（确定性验收变化逻辑，独立于真实岗位）

## 测试

```bash
uv run pytest
```
