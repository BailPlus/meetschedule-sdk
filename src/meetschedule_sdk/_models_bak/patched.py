from .origin import Adjustment as _Adjustment
from .origin import AdjustmentInput as _AdjustmentInput
from .origin import AdjustmentType as _AdjustmentType
from .origin import ApiError as _ApiError
from .origin import BaseModel as _BaseModel
from .origin import Category as _Category
from .origin import Course as _Course
from .origin import CourseInput as _CourseInput
from .origin import CoursePatch as _CoursePatch
from .origin import DayOfWeek as _DayOfWeek
from .origin import EventInput as _EventInput
from .origin import EventPatch as _EventPatch
from .origin import EventType as _EventType
from .origin import Meeting as _Meeting
from .origin import MeetingInput as _MeetingInput
from .origin import Origin as _Origin
from .origin import Reminder as _Reminder
from .origin import ReminderAnchor as _ReminderAnchor
from .origin import Schedule as _Schedule
from .origin import ScheduleBundle as _ScheduleBundle
from .origin import ScheduleInput as _ScheduleInput
from .origin import ScheduleUpdate as _ScheduleUpdate
from .origin import Source as _Source
from .origin import Task as _Task
from .origin import TaskInput as _TaskInput
from .origin import TaskPatch as _TaskPatch
from .origin import TimeMode as _TimeMode
from .origin import WeekStartDay as _WeekStartDay

Source = _Source

ReminderAnchor = _ReminderAnchor
Origin = _Origin


class Adjustment(_Adjustment):
    pass


class AdjustmentInput(_AdjustmentInput):
    pass


AdjustmentType = _AdjustmentType


class ApiError(_ApiError):
    pass


class BaseModel(_BaseModel):
    pass


Category = _Category


class Course(_Course):
    pass


class CourseInput(_CourseInput):
    pass


class CoursePatch(_CoursePatch):
    pass


DayOfWeek = _DayOfWeek


class Reminder(_Reminder):
    pass


class EventInput(_EventInput):
    pass


class Event(EventInput):
    pass


class EventPatch(_EventPatch):
    pass


EventType = _EventType


class Meeting(_Meeting):
    pass


class MeetingInput(_MeetingInput):
    pass


class Schedule(_Schedule):
    source: Source


class ScheduleBundle(_ScheduleBundle):
    pass


class ScheduleInput(_ScheduleInput):
    pass


class ScheduleUpdate(_ScheduleUpdate):
    pass


class Task(_Task):
    pass


class TaskInput(_TaskInput):
    pass


class TaskPatch(_TaskPatch):
    pass


TimeMode = _TimeMode


WeekStartDay = _WeekStartDay
