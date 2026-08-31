# Meet Schedule SDK — Python

[Meet 课程表 开放 API](https://api.meetschedule.top) 的 Python SDK。

## 安装

```bash
uv add meetschedule-sdk
# 或
pip install meetschedule-sdk
```

## 快速开始

```python
from meetschedule_sdk import MeetSchedule

client = MeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx")

# 列出所有课表
for s in client.schedules.get_all():
    print(f"[{s.id}] {s.name} ({s.course_count} 门课)")

# 获取课表完整数据
bundle = client.schedules.get_full("sch_xxx")
for c in bundle.courses:
    print(f"  {c.name} — {len(c.meetings)} 条上课安排")

# 创建事件
event = client.events.create(
    EventInput(
        schedule_id="sch_xxx",
        type="exam",
        title="期中考试",
        time_mode="range",
        start_at="2025-11-10T08:00:00Z",
        end_at="2025-11-10T10:00:00Z",
    ),
)
print(f"已创建事件 {event.id}")

# 新建待办
task = client.tasks.create(TaskInput(title="完成实验报告", group="作业"))
client.tasks.update(task.id, TaskPatch(done=True))
```

## Async 用法

```python
import asyncio
from meetschedule_sdk import AsyncMeetSchedule

async def main():
    async with AsyncMeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx") as client:
        # 所有方法与 sync 版本同名，只需加 await
        schedules = await client.schedules.get_all()
        for s in schedules:
            print(f"[{s.id}] {s.name}")

        # 获取课表完整数据
        bundle = await client.schedules.get_full("sch_xxx")
        for c in bundle.courses:
            print(f"  {c.name} — {len(c.meetings)} 条上课安排")

        # 批量并行操作
        results = await asyncio.gather(
            client.tasks.get_all(),
            client.events.get_all("sch_xxx", type="exam"),
        )
        tasks, exams = results

asyncio.run(main())
```

## API 概览

| 客户端属性 | API 端点 | 所需 Scope |
|---|---|---|
| `client.schedules` | `/open/v1/schedules` | `schedule:read` / `schedule:write` |
| `client.courses` | `/open/v1/schedules/{id}/courses` | `entities:read` / `entities:write` |
| `client.events` | `/open/v1/schedules/{id}/events` | `entities:read` / `entities:write` |
| `client.adjustments` | `/open/v1/schedules/{id}/adjustments` | `entities:read` / `entities:write` |
| `client.tasks` | `/open/v1/tasks` | `entities:read` / `entities:write` |
| `client.timeslot_groups` | `/open/v1/timeslot-groups` | `entities:read` |

### Schedules

| 方法 | 说明 |
|---|---|
| `client.schedules.get_all()` | 列出所有课表 |
| `client.schedules.get(schedule_id)` | 获取单个课表信息 |
| `client.schedules.get_current()` | 获取当前正在使用的课表 |
| `client.schedules.create(ScheduleInput(...))` | 新建课表 |
| `client.schedules.update(schedule_id, ScheduleUpdate(...))` | 更新课表设置 |
| `client.schedules.delete(schedule_id)` | 删除课表（不可恢复） |
| `client.schedules.get_full(schedule_id)` | 拉取课表完整数据（含课程/事件/调停课） |

### Courses

| 方法 | 说明 |
|---|---|
| `client.courses.get_all(schedule_id)` | 列出课表下的所有课程 |
| `client.courses.create(schedule_id, CourseInput(...))` | 新建课程 |
| `client.courses.update(course_id, CoursePatch(...))` | 更新课程 |
| `client.courses.delete(course_id)` | 删除课程 |

### Events

| 方法 | 说明 |
|---|---|
| `client.events.get_all(schedule_id, type=..., from_time=..., to=..., done=...)` | 列出事件 |
| `client.events.get(event_id)` | 获取单个事件 |
| `client.events.get_by_ids([...])` | 按 id 批量获取事件 |
| `client.events.create(EventInput(...), allow_duplicate_title=...)` | 新建事件 |
| `client.events.update(event_id, EventPatch(...))` | 更新事件 |
| `client.events.delete(event_id)` | 删除事件 |
| `client.events.create_batch(schedule_id, [EventInput(...), ...], allow_duplicate_title=...)` | 批量新建事件（1–100 条，单事务） |
| `client.events.delete_batch([event_id, ...])` | 批量删除事件（返回 `EventBatchDeleteResponse`） |

### Adjustments（调停课）

| 方法 | 说明 |
|---|---|
| `client.adjustments.get_all(schedule_id)` | 列出调停课 |
| `client.adjustments.get(adjustment_id)` | 获取单个调停课 |
| `client.adjustments.create(AdjustmentInput(...))` | 新建调停课 |
| `client.adjustments.update(adjustment_id, AdjustmentPatch(...))` | 更新调停课 |
| `client.adjustments.delete(adjustment_id)` | 删除调停课 |

### Tasks（待办）

| 方法 | 说明 |
|---|---|
| `client.tasks.get_all()` | 列出所有待办 |
| `client.tasks.get(task_id)` | 获取单个待办 |
| `client.tasks.create(TaskInput(...))` | 新建待办 |
| `client.tasks.update(task_id, TaskPatch(...))` | 更新待办 |
| `client.tasks.delete(task_id)` | 删除待办 |

### Timeslot groups（作息组）

| 方法 | 说明 |
|---|---|
| `client.timeslot_groups.get_all()` | 列出当前账号的全部作息组及节次（默认组排最前） |
| `client.timeslot_groups.get(group_id)` | 获取单个作息组及节次详情 |

## 错误处理

所有 API 错误都会抛出 `ApiException` 的子类：

```python
from meetschedule_sdk import (
    MeetSchedule,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    UnprocessableEntityError,
    TooManyRequestsError,
    NetworkError,
)

client = MeetSchedule(api_key="...")

try:
    schedule = client.schedules.get("sch_xxx")
except UnauthorizedError:
    print("API Key 无效")
except ForbiddenError:
    print("API Key 缺少必要的 scope")
except NotFoundError:
    print("课表不存在")
except TooManyRequestsError:
    print("触发限流，请稍后重试")
except NetworkError:
    print("网络连接失败")
```

## 数据模型

SDK 使用 pydantic `BaseModel` 表示所有数据模型。返回的数据会自动反序列化为对应的模型实例。

```python
from meetschedule_sdk import (
    Schedule, ScheduleBundle,
    Course, CourseInput, MeetingInput,
    Event, EventInput,
    Adjustment, AdjustmentInput,
    Task, TaskInput,
    DayOfWeek, Category, EventType, TimeMode, AdjustmentType,
)
```

创建/更新时传入对应的 Input / Patch 模型实例：

```python
# 创建课程
from meetschedule_sdk import CourseInput, MeetingInput
course = client.courses.create(
    schedule_id="sch_xxx",
    input=CourseInput(
        name="高等数学（下）",
        meetings=[
            MeetingInput(day_of_week=1, start_period=3, end_period=4, weeks=[1,3,5]),
        ],
    ),
)

# 更新课表
from meetschedule_sdk import ScheduleUpdate
client.schedules.update("sch_xxx", ScheduleUpdate(name="2026 Spring"))

# 标记待办完成
from meetschedule_sdk import TaskPatch
client.tasks.update("task_xxx", TaskPatch(done=True))
```

## 许可证

GPLv3
