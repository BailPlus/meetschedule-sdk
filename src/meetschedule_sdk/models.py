"""Pydantic models for the Meet Schedule Open API.

All models are ``pydantic.BaseModel`` subclasses that mirror the OpenAPI
schemas in api-1.yaml.

Input variants (``*Input``) contain only user-settable fields; full models
add server-generated fields (``id``, ``updated_at``, etc.).
"""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, Field

# ── Enums ──────────────────────────────────────────────────────────────────


class DayOfWeek(IntEnum):
    """Day of week (ISO-8601 order)."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class Category(StrEnum):
    """Course category."""

    REQUIRED = "required"
    ELECTIVE = "elective"
    PUBLIC_ELECTIVE = "public_elective"
    OTHER = "other"


class EventType(StrEnum):
    """Event type."""

    HOMEWORK = "homework"
    EXAM = "exam"
    ACTIVITY = "activity"
    ANNIVERSARY = "anniversary"


class TimeMode(StrEnum):
    """How an event expresses its time."""

    RANGE = "range"  # start_at + end_at
    START_ONLY = "start_only"  # start_at only
    DUE_ONLY = "due_only"  # end_at only
    ALL_DAY = "all_day"  # all_day_date


class AdjustmentType(StrEnum):
    """Adjustment type."""

    CANCEL = "cancel"
    MAKEUP = "makeup"
    RESCHEDULE = "reschedule"


class Origin(StrEnum):
    """Data origin."""

    IMPORT = "import"  # imported from school教务 system
    USER = "user"  # created by user / API


class ReminderAnchor(StrEnum):
    """Anchor point for reminders."""

    START = "START"
    END = "END"


class WeekStartDay(IntEnum):
    """First day of the week view."""

    MONDAY = 1
    SUNDAY = 7


class Source(StrEnum):
    """Data source for schedules and adjustments."""

    MANUAL = "manual"
    AI = "ai"
    ADAPTER = "adapter"
    CLOUD = "cloud"  # Adjustment的source特有
    SCHOOL_IMPORT = "school_import"  # Schedule的source特有


# ── Shared models ──────────────────────────────────────────────────────────


class Reminder(BaseModel):
    """A reminder rule attached to a course or event."""

    offset_minutes: int = Field(ge=0)
    """How many minutes before the anchor point to remind."""

    anchor: ReminderAnchor = ReminderAnchor.START
    """Anchor point: start time or end/due time."""


# ── Schedule models ────────────────────────────────────────────────────────


class ScheduleInput(BaseModel):
    """Fields a user can set when creating or updating a schedule."""

    name: str
    """Schedule name, e.g. '2025 Fall Semester'."""

    start_date: str
    """ISO date of the Monday of week 1, e.g. '2025-09-01'."""

    term: str | None = None
    """Raw term string, display-only, e.g. '2025-2026学年1学期'."""

    total_weeks: int = Field(20, ge=1, le=520)
    """Total weeks in the semester (1-520)."""

    week_start_day: WeekStartDay = WeekStartDay.MONDAY
    """First day of the week view: 1=Monday, 7=Sunday."""


class ScheduleUpdate(BaseModel):
    """Fields a user can set when updating a schedule (PATCH).

    All fields are optional; only explicitly set fields are sent to the API.
    Unset fields keep their current server-side values.
    """

    name: str | None = None
    """Schedule name, e.g. '2025 Fall Semester'."""

    start_date: str | None = None
    """ISO date of the Monday of week 1, e.g. '2025-09-01'."""

    term: str | None = None
    """Raw term string, display-only, e.g. '2025-2026学年1学期'."""

    total_weeks: int | None = None
    """Total weeks in the semester (1-520)."""

    week_start_day: WeekStartDay | None = None
    """First day of the week view: 1=Monday, 7=Sunday."""


class Schedule(ScheduleInput):
    """A full schedule object returned by the API."""

    id: str
    """Schedule ID (opaque string)."""

    source: Source
    """How the schedule was created."""

    sort_order: int
    """Sort weight; lower values appear first in lists."""

    is_current: bool
    """Whether this is the schedule currently in use (the one with the
    smallest ``sort_order``)."""

    course_count: int
    """Number of courses (excluding deleted)."""

    event_count: int
    """Number of events (excluding deleted)."""

    updated_at: str
    """Last modification time (UTC, ISO 8601)."""


# ── Meeting models ─────────────────────────────────────────────────────────


class MeetingInput(BaseModel):
    """A single weekly meeting pattern for a course."""

    day_of_week: DayOfWeek
    """Day of week (1=Monday … 7=Sunday)."""

    start_period: int = Field(ge=1)
    """Starting period number (1-based)."""

    end_period: int = Field(ge=1)
    """Ending period number (inclusive)."""

    weeks: list[Annotated[int, Field(ge=1, le=63)]]
    """List of weeks this meeting occurs (1-based)."""

    location: str | None = None
    """Classroom, e.g. 'Building A-301'."""

    teacher: str | None = None
    """Instructor name."""

    note: str | None = None
    """Extra notes."""


class Meeting(MeetingInput):
    """A meeting pattern as returned by the API."""

    id: str
    """Meeting ID (opaque string)."""

    weeks_mask: int
    """Bitmask representation of `weeks` (server-computed, read-only)."""


# ── Course models ──────────────────────────────────────────────────────────


class CourseInput(BaseModel):
    """Fields a user can set when creating or updating a course."""

    name: str
    """Course name, e.g. '高等数学（下）'."""

    meetings: list[MeetingInput]
    """Weekly meeting patterns for this course."""

    course_code: str | None = None
    """教务 course code, e.g. 'A2150341'."""

    class_code: str | None = None
    """教务 class code, e.g. 'A15252A2150341002'."""

    credits: float | None = None
    """Credit hours."""

    category: Category | None = None
    """Normalised course category."""

    category_raw: str | None = None
    """Raw category text from 教务 system."""

    display_teacher: str | None = None
    """Display teacher name (summary for list views)."""

    color_hue: float | None = None
    """Fixed hue value (0-360) for the course colour block."""

    note: str | None = None
    """Plain-text note."""

    reminders: list[Reminder] | None = None
    """Reminder rules."""


class CoursePatch(BaseModel):
    """Fields a user can set when updating a course (PATCH).

    All fields are optional; only explicitly set fields are sent to the API.
    Unset fields keep their current server-side values.
    ``meetings`` is special: if set, it **replaces** all existing meetings.
    """

    name: str | None = None
    """Course name, e.g. '高等数学（下）'."""

    meetings: list[MeetingInput] | None = None
    """Weekly meeting patterns; replaced entirely when set."""

    course_code: str | None = None
    """教务 course code, e.g. 'A2150341'."""

    class_code: str | None = None
    """教务 class code, e.g. 'A15252A2150341002'."""

    credits: float | None = None
    """Credit hours."""

    category: Category | None = None
    """Normalised course category."""

    category_raw: str | None = None
    """Raw category text from 教务 system."""

    display_teacher: str | None = None
    """Display teacher name (summary for list views)."""

    color_hue: float | None = None
    """Fixed hue value (0-360) for the course colour block."""

    note: str | None = None
    """Plain-text note."""

    reminders: list[Reminder] | None = None
    """Reminder rules."""


class Course(CourseInput):
    """A full course object returned by the API."""

    id: str
    """Course ID (opaque string)."""

    schedule_id: str
    """ID of the schedule this course belongs to."""

    origin: Origin
    """How this course was created."""

    external_id: str | None = None
    """Original identifier from 教务 system (for import dedup)."""

    user_overridden: bool = False
    """Whether the course has been modified after import."""

    updated_at: str
    """Last modification time (UTC, ISO 8601)."""


# ── Event models ───────────────────────────────────────────────────────────


class EventInput(BaseModel):
    """Fields a user can set when creating or updating an event."""

    schedule_id: str
    """ID of the schedule this event belongs to."""

    type: EventType
    """Event type."""

    title: str
    """Event title."""

    time_mode: TimeMode
    """How the event expresses its time."""

    start_at: str | None = None
    """Start time (ISO 8601); required when time_mode is 'range' or 'start_only'."""

    end_at: str | None = None
    """End / due time (ISO 8601); required when time_mode is 'range' or 'due_only'."""

    all_day_date: str | None = None
    """Date for all-day events (ISO date); required when time_mode is 'all_day'."""

    linked_course_id: str | None = None
    """Optional linked course ID."""

    timeslot_group_id: str | None = None
    """Optional timeslot group ID for grid rendering."""

    location: str | None = None
    """Location."""

    color_hue: float | None = None
    """Fixed hue value (0-360) for the colour block."""

    note: str | None = None
    """Plain-text note."""

    reminders: list[Reminder] | None = None
    """Reminder rules."""

    done: bool = False
    """Completion status (events can be marked done too)."""


class EventPatch(BaseModel):
    """Fields a user can set when updating an event (PATCH).

    All fields are optional; only explicitly set fields are sent to the API.
    Unset fields keep their current server-side values.
    """

    schedule_id: str | None = None
    """ID of the schedule this event belongs to; moves the event if changed."""

    type: EventType | None = None
    """Event type."""

    title: str | None = None
    """Event title."""

    time_mode: TimeMode | None = None
    """How the event expresses its time."""

    start_at: str | None = None
    """Start time (ISO 8601)."""

    end_at: str | None = None
    """End / due time (ISO 8601)."""

    all_day_date: str | None = None
    """Date for all-day events (ISO date)."""

    linked_course_id: str | None = None
    """Optional linked course ID."""

    timeslot_group_id: str | None = None
    """Optional timeslot group ID for grid rendering."""

    location: str | None = None
    """Location."""

    color_hue: float | None = None
    """Fixed hue value (0-360) for the colour block."""

    note: str | None = None
    """Plain-text note."""

    reminders: list[Reminder] | None = None
    """Reminder rules."""

    done: bool | None = None
    """Completion status (events can be marked done too)."""


class Event(EventInput):
    """A full event object returned by the API."""

    id: str
    """Event ID (opaque string)."""

    origin: Origin
    """How this event was created."""

    updated_at: str
    """Last modification time (UTC, ISO 8601)."""


# ── Adjustment models ──────────────────────────────────────────────────────


class AdjustmentInput(BaseModel):
    """Fields a user can set when creating an adjustment."""

    schedule_id: str
    """ID of the schedule this adjustment belongs to."""

    type: AdjustmentType
    """Adjustment type: cancel, makeup, or reschedule."""

    course_id: str | None = None
    """Linked course ID; can be None for custom holiday adjustments."""

    origin_week: int | None = None
    """Original week (required for cancel / reschedule)."""

    origin_day: DayOfWeek | None = None
    """Original day of week."""

    origin_start_period: int | None = None
    """Original starting period."""

    origin_end_period: int | None = None
    """Original ending period (inclusive)."""

    target_week: int | None = None
    """Target week (required for makeup / reschedule)."""

    target_day: DayOfWeek | None = None
    """Target day of week."""

    target_start_period: int | None = None
    """Target starting period."""

    target_end_period: int | None = None
    """Target ending period (inclusive)."""

    target_location: str | None = None
    """New location for makeup / reschedule."""

    substitute_teacher: str | None = None
    """Substitute teacher; leave empty if unchanged."""


class Adjustment(AdjustmentInput):
    """A full adjustment object returned by the API."""

    id: str
    """Adjustment ID (opaque string)."""

    source: Source
    """Data source."""

    updated_at: str
    """Last modification time (UTC, ISO 8601)."""


# ── Task models ────────────────────────────────────────────────────────────


class TaskInput(BaseModel):
    """Fields a user can set when creating or updating a task."""

    title: str
    """Task title."""

    group: str | None = None
    """Group name, e.g. '毕业设计', '生活'."""

    done: bool = False
    """Completion status."""

    due_at: str | None = None
    """Due time (ISO 8601); no due date if None."""

    sort_order: int | None = None
    """Sort weight; lower values appear first."""


class TaskPatch(BaseModel):
    """Fields a user can set when updating a task (PATCH).

    All fields are optional; only explicitly set fields are sent to the API.
    Unset fields keep their current server-side values.
    """

    group: str | None = None
    """Group name, e.g. '毕业设计', '生活'; pass empty string to clear."""

    title: str | None = None
    """Task title."""

    done: bool | None = None
    """Completion status; unset keeps the current value."""

    due_at: str | None = None
    """Due time (ISO 8601); no due date if None."""

    sort_order: int | None = None
    """Sort weight; lower values appear first."""


class Task(TaskInput):
    """A full task object returned by the API."""

    id: str
    """Task ID (opaque string)."""

    updated_at: str
    """Last modification time (UTC, ISO 8601)."""


# ── Bundle models ──────────────────────────────────────────────────────────


class ScheduleBundle(BaseModel):
    """Full schedule snapshot: schedule + courses + events + adjustments."""

    schedule: Schedule
    """The schedule itself."""

    courses: list[Course]
    """All courses (with meetings)."""

    events: list[Event]
    """All events."""

    adjustments: list[Adjustment]
    """All adjustments."""


# ── Error model ────────────────────────────────────────────────────────────


class ApiError(BaseModel):
    """Error response body."""

    code: str
    """Stable error code for programmatic handling, e.g. 'credits.insufficient'."""

    message: str
    """Human-readable error description in Chinese."""

    details: dict[str, Any] | None = None
    """Optional extra info (schema varies by error type)."""
