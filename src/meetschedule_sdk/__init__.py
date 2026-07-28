"""Meet Schedule Open API — Python SDK.

A sync client for reading and writing your Meet 课程表 data.

Quick start::

    from meetschedule_sdk import MeetSchedule

    client = MeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx")

    # List your schedules
    for s in client.schedules.list():
        print(s.name)

    # Create an event
    event = client.events.create(
        schedule_id="sch_xxx",
        type="exam",
        title="期中考试",
        time_mode="range",
        start_at="2025-11-10T08:00:00Z",
        end_at="2025-11-10T10:00:00Z",
    )
    print(f"Created event {event.id}")
"""

from meetschedule_sdk.async_client import AsyncMeetSchedule
from meetschedule_sdk.client import MeetSchedule
from meetschedule_sdk.exceptions import (
    ApiException,
    ConfigurationError,
    ForbiddenError,
    MeetScheduleError,
    NetworkError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
    UnprocessableEntityError,
)
from meetschedule_sdk.models import (
    Adjustment,
    AdjustmentInput,
    AdjustmentType,
    ApiError,
    Category,
    Course,
    CourseInput,
    DayOfWeek,
    Event,
    EventInput,
    EventType,
    Meeting,
    MeetingInput,
    Origin,
    Reminder,
    Schedule,
    ScheduleBundle,
    ScheduleInput,
    Task,
    TaskInput,
    TimeMode,
)

__all__ = [
    # Clients
    "MeetSchedule",
    "AsyncMeetSchedule",
    # Exceptions
    "MeetScheduleError",
    "ConfigurationError",
    "NetworkError",
    "ApiException",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "UnprocessableEntityError",
    "TooManyRequestsError",
    # Enums
    "DayOfWeek",
    "Category",
    "EventType",
    "TimeMode",
    "AdjustmentType",
    "Origin",
    # Models
    "ScheduleInput",
    "Schedule",
    "ScheduleBundle",
    "MeetingInput",
    "Meeting",
    "CourseInput",
    "Course",
    "EventInput",
    "Event",
    "AdjustmentInput",
    "Adjustment",
    "TaskInput",
    "Task",
    "Reminder",
    "ApiError",
]
