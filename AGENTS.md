# AGENTS.md — 项目速览与跨会话记忆

给后续任何会话的 agent 使用。改动代码前先读本文件，改完若有重要进展可更新它。

## 项目是什么

`meetschedule-sdk` 是一个手写的 Python SDK（非代码生成），封装 [Meet 课程表 开放 API](https://api.meetschedule.top)（`/open/v1/`）。服务端 OpenAPI 描述以快照形式放在仓库根目录，SDK 代码是**手工同步**这些 schema 的产物——没有 codegen。

- `src/meetschedule_sdk/` 为包源码（`uv_build` / hatchling 布局）。
- `tests/test.ipynb` 是唯一的"测试"（交互式 notebook，无 pytest 套件）。
- 环境：Python >= 3.12，依赖 `httpx` + `pydantic`；venv 在 `.venv`。
- 版本当前见 `pyproject.toml`（`version` 独立于 api json 的 spec version）。

## API 快照文件（根目录，勿删）

| 文件 | 说明 |
|---|---|
| `api-1.json` | 最早一版 API |
| `api-2.json` | SDK 上一次同步所对应的版本（当前代码 ≈ api-2） |
| `api-3.json` | 最新 API 版本（较新） |
| `api-json.diff` | 新 API 相对当前 SDK 的改动（用户会提供/更新） |

**变更工作流**：用户通常给一个新版 `api-N.json`（或一份 `api-json.diff`），要求"同步到代码"。做法：先读 diff 或自己 `diff api-2.json api-3.json` 定位**功能性 schema/端点变更**（路径、schema、字段、枚举、端点），忽略纯描述文字/版本号噪音，再把改动落到手写代码。

## 代码结构与约定

每新增一个资源/端点都要改动 4 处，保持同步：

1. `src/meetschedule_sdk/models.py`
   - pydantic 模型。顶部 import `Annotated`/`Field` 已就绪。
   - 字符串枚举用 `StrEnum`、整数枚举用 `IntEnum`。
   - **响应侧枚举惯用法**：`Annotated[SomeEnum | str, Field(union_mode="left_to_right")]` —— 已知值解析为枚举、未知字符串保留，避免历史数据解析失败（参考 `Schedule.source`）。
   - 输入侧用 `*Input`（只含用户可设字段），`*Patch` 是 PATCH 全可选模型；完整模型（含服务端 `id`/`updated_at` 等）继承对应 Input。
   - 以 `# ── Xxx models ──` 分区注释组织。
2. `src/meetschedule_sdk/client.py`（同步）
   - 资源子客户端类命名为 `_XxxResource(_BaseResource)`，使用 `self._get/_post/_patch/_delete`；在 `MeetSchedule.__init__` 里用 `self.xxx = _XxxResource(self._client)` 注册并带 docstring。
3. `src/meetschedule_sdk/async_client.py`（异步）
   - 对应类 `_AsyncXxxResource(_AsyncBaseResource)`（注意初始化方式可能与 sync 略不同，以现状为准），注册到 `AsyncMeetSchedule`。方法同名，加 `await`。
4. `src/meetschedule_sdk/__init__.py`
   - 把新增模型加进 `from ...models import (...)` 与 `__all__` 两处。

`README.md` 也要补：API 概览表（`client.xxx` 行）以及对应资源小节的方法表。模块 docstring 里的 usage 示例不必逐字跟。

方法命名习惯：资源上通常有 `get_all` / `get` / `create` / `update` / `delete`；`get_current`（schedule）、`get_full`、`create_batch`/`delete_batch`、`get_by_ids` 等按需。

## 最近一次同步（记住本次进度）

本次（api-2 → api-3）新增了「当前 API Key 权限」端点，已同步到代码：

- 新增 `GET /open/v1/key`，返回 `ApiKeyScopes`（必填 `scopes: list[str]`）。
- 新增模型 `ApiKeyScopes`，已导出。
- `MeetSchedule.key.get()` 与 `AsyncMeetSchedule.key.get()` 返回 `ApiKeyScopes`（请求 `/open/v1/key`，无需任何业务 scope，只要 Key 有效）。
- README 已加 `client.key` 行与「API Key」小节。

此改动代码侧未提交；工作区里 `pyproject.toml` 有一处 uv_build 版本改动**是本会话前就存在的**，与同步无关。

## 待办 / 其他提醒

- 若要发布，记得自己版本号（pyproject `version`）——它不等同于 api spec 的 version。
- pyproject 同时带 `[tool.ruff.lint] select = ["E","F","I","N","W"]`，同步后跑 `ruff check src/meetschedule_sdk/` 保持通过；ruff 不在 `.venv`，用 `~/.local/bin/ruff`。
- LICENSE 实为 MIT（虽早期描述说 GPLv3，pyproject 标注 MIT）。
