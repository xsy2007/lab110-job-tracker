# lab110-job-tracker

110 实验室招新考核项目：一个真实数据驱动的岗位追踪应用。

## 1. 项目目标

采集两个真实招聘来源的岗位（腾讯招聘官方 + LinkedIn 招聘平台），提供岗位搜索、筛选条件管理、岗位关注与变化动态；维护人员可手动触发采集；通过 playback 快照对变化检测逻辑做确定性验收。

## 2. 架构与目录结构

技术栈：Python 3.12 · FastAPI · Jinja2 · SQLAlchemy · SQLite · httpx · BeautifulSoup · pytest · Docker

```
app/
  main.py           应用入口（中间件、路由、启动时自动建库 + seed）
  config.py         路径 / DB URL / .env 加载
  db.py             engine / SessionLocal / Base / init_db
  models.py         9 张表（users/sources/jobs/job_versions/saved_filters/
                    follows/job_changes/user_activities/collection_runs）
  security.py       PBKDF2 密码散列
  seed.py           预置 user1/user2/maintainer + 两个来源
  deps.py           登录依赖（未登录重定向 /login）
  routers/          auth / jobs / filters / follows / activity / maintenance
  services/         collection.py（采集+变更+动态）  playback.py（快照回放）
  collectors/       base + tencent + linkedin
  templates/        Jinja2 页面
data/              SQLite 数据库（volume 持久化，不入库）
evidence/          真实采集原始响应 + 元数据（来源/时间/结果）
snapshots/         4 个 playback 快照（独立于真实数据）
tests/             pytest 验收测试
```

## 3. 两个真实来源及说明

| 来源 | 类型 | 采集器 | 说明 |
|---|---|---|---|
| 腾讯招聘 careers.tencent.com | 大厂官方 | tencent | JSON API，无需登录 |
| LinkedIn linkedin.com/jobs | 招聘平台 | linkedin | guest 岗位接口，无需登录 |

字段映射：腾讯 `PostId→source_job_id`、`RecruitPostName→title`、`LocationName→city`、`PostURL→source_url`（转 https）、`IsValid→status`；LinkedIn 由卡片解析 `jobPosting ID→source_job_id`、标题/公司/城市/URL。

## 4. 本地启动（需要 Python 3.12）

```bash
uv sync --extra dev
uv run python -m uvicorn app.main:app --reload
```

## 5. Docker 启动（宿主机无需 Python）

```bash
docker compose up --build
```

## 6. 访问地址

http://localhost:8000

## 7. 三个测试账号（密码 = 用户名）

| 账号 | 角色 |
|---|---|
| user1 | 普通用户 |
| user2 | 普通用户 |
| maintainer | 维护（可采集） |

## 8. 首次真实采集步骤

1. 用 maintainer 登录，进入「维护」页。
2. 点「全部采集」，或对每个来源点「立即采集」。
3. 结果（状态、created/updated/unchanged/failed、error）显示在「最近采集运行」表。

命令行等价：`uv run python -m app.cli`

## 9. 岗位搜索步骤

登录后进入「岗位」页，输入关键词 + 城市，点「搜索」。

## 10. 保存 / 修改 / 删除筛选步骤

进入「筛选」页：新建（名称 + 关键词 + 城市）保存；每个筛选可「更新」「删除」「使用」。「使用」用保存的条件**重新搜索当前岗位**，不保存结果快照。

## 11. 关注 / 取消关注步骤

岗位列表或详情页点「关注」/「取消关注」。

## 12. 查看动态步骤

进入「动态」页查看关注岗位的变化动态。

## 13. playback 四场景运行方法

快照在 `snapshots/`：`baseline.json`、`requirements_changed.json`、`explicit_closed.json`、`source_timeout.json`。在临时独立数据库上运行（不碰真实岗位）：

```bash
uv run pytest -k playback -v
```

## 14. pytest 运行方法

```bash
uv run pytest -v
```

## 15. Docker 数据持久化验证方法

```bash
docker compose up --build
# user1 登录：创建一个筛选、关注一个岗位
docker compose down
docker compose up -d
# 重新登录：筛选、关注、历史动态仍在（data/ 挂到 volume）
```

## 16. evidence 目录说明

- `evidence/<collector>/run_<id>.{json,html}` = 采集时的原始响应（逐字节）。
- `evidence/<collector>/run_<id>.meta.json` = 来源 / 开始时间 / 结束时间 / 状态 / 计数。
- `evidence/linkedin_probe.html` = 来源探测时的原始 HTML（非采集成功证据）。

## 17. 真实采集与 playback 数据严格区分

- 真实采集：来自 careers.tencent.com 与 linkedin.com，写入 `jobs` 表，原始响应存 `evidence/`。
- playback：`snapshots/` 下的 4 个 JSON 快照，只在临时独立数据库运行，验证变化逻辑，不计入真实岗位。

## 18. 已知限制

- **LinkedIn 网络/代理限制**：guest 接口在大陆网络下直连返回 302（被重定向/机器人检测），需合法可用的 HTTP/HTTPS 代理。代理完全可选，通过 `HTTPS_PROXY`/`HTTP_PROXY`/`ALL_PROXY` 环境变量或 `.env` 配置（见 `.env.example`），代码不硬编码代理地址。无代理时 LinkedIn 采集记 `FAILED`、保留旧数据、不影响腾讯来源。
- 已提交的 `evidence/` 是历史采集记录；在无代理环境重新采集 LinkedIn 会 `FAILED`，不会冒充新采集成功。
- `deadline` 在所选两个来源中均不可得，页面显示「未提供」，不做推测。

## 19. 关键验收场景及实际结果

1. **真实采集**：腾讯 15 岗位、LinkedIn 10 岗位；首次采集 0 条 job_change。
2. **采集幂等**：相同数据重复采集 unchanged=15/10，job_change 总数保持 0。
3. **关注动态时序**（pytest）：关注前变化不补发；关注期间变化生成 activity；取关后不再生成、历史保留。
4. **数据隔离**（pytest + HTTP 实测）：user1 的筛选/关注/动态，user2 不可见。
5. **playback 四场景**（pytest）：baseline 0 change；requirements_changed 有 before/after；explicit_closed 仅显式关闭；source_timeout 不关闭任何岗位。
6. **Docker 持久化**：见第 15 节步骤（本机以 `docker compose up --build` 实际验证）。

## 20. 声明

上述「实际结果」均为本机实际执行得到（pytest 9/9 通过、真实采集 15+10、重复采集 0 change、隔离与 playback 均实测）。未验证的内容不写入「实际结果」。
