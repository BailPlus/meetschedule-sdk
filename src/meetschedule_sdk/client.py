"""Sync HTTP client for the Meet Schedule Open API.

Usage::

    from meetschedule_sdk import MeetSchedule

    client = MeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx")

    # List schedules
    schedules = client.schedules.get_all()

    # Create a course
    course = client.courses.create(
        schedule_id="sch_xxx",
        name="高等数学（下）",
        meetings=[{
            "day_of_week": 1,
            "start_period": 3,
            "end_period": 4,
            "weeks": [1, 3, 5, 7, 9, 11, 13, 15],
        }],
    )
"""

from __future__ import annotations

from typing import Any, Literal

import httpx

from meetschedule_sdk.exceptions import (
    ConfigurationError,
    NetworkError,
    map_status_code,
)
from meetschedule_sdk.models import (
    Adjustment,
    AdjustmentInput,
    ApiError,
    Course,
    CourseInput,
    Event,
    EventInput,
    Schedule,
    ScheduleBundle,
    ScheduleInput,
    Task,
    TaskInput,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _parse_error_body(response: httpx.Response) -> ApiError | None:
    """Try to parse an error response body into an ``ApiError``."""
    try:
        data = response.json()
        return ApiError(
            code=data["code"],
            message=data["message"],
            details=data.get("details"),
        )
    except Exception:  # noqa: BLE001
        return None


def _raise_on_error(response: httpx.Response) -> None:
    """Raise an ``ApiException`` subclass if *response* indicates an error."""
    if response.is_success or response.status_code == 204:
        return
    body = _parse_error_body(response)
    exc = map_status_code(
        response.status_code,
        body=body,
        response_text=response.text,
    )
    raise exc


def _to_dict(obj: Any) -> Any:
    """Recursively convert a dataclass (with enums, etc.) to a JSON-safe dict.

    Handles:
    - dataclasses → dict
    - dict → recursively converted dict
    - lists → list of converted items
    - ``IntEnum`` / ``StrEnum`` → value
    - ``None`` → ``None``
    - other → passthrough
    """
    if obj is None:
        return None
    if isinstance(obj, (int, float, str, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_dict(i) for i in obj]
    if hasattr(obj, "__dataclass_fields__"):
        result: dict[str, Any] = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            if value is not None:
                result[field_name] = _to_dict(value)
        return result
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


# ── Base resource ────────────────────────────────────────────────────────────


class _BaseResource:
    """Base class for resource sub-clients."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> httpx.Response:
        """Send an HTTP request and handle errors."""
        json_data = _to_dict(json_body) if json_body is not None else None

        try:
            response = self._client.request(
                method,
                path,
                params=params,
                json=json_data,
            )
        except httpx.RequestError as exc:
            raise NetworkError(str(exc)) from exc

        _raise_on_error(response)
        return response

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        """GET and return parsed JSON."""
        resp = self._request("GET", path, params=params)
        if resp.status_code == 204:
            return None
        return resp.json()

    def _post(
        self, path: str, *, body: Any = None
    ) -> Any:
        """POST and return parsed JSON (expects 201)."""
        resp = self._request("POST", path, json_body=body)
        return resp.json()

    def _patch(self, path: str, *, body: Any = None) -> Any:
        """PATCH and return parsed JSON."""
        resp = self._request("PATCH", path, json_body=body)
        return resp.json()

    def _delete(self, path: str) -> None:
        """DELETE (expects 204)."""
        self._request("DELETE", path)


# ── Schedules ────────────────────────────────────────────────────────────────


class _SchedulesResource(_BaseResource):
    """``/open/v1/schedules`` endpoints."""

    def get_all(self) -> list[Schedule]:
        """Get all schedules belonging to this API key's account.

        Requires scope ``schedule:read``.
        """
        data = self._get("/open/v1/schedules")
        return [Schedule(**item) for item in data]

    def get(self, schedule_id: str) -> Schedule:
        """Get a single schedule by ID.

        Requires scope ``schedule:read``.
        """
        data = self._get(f"/open/v1/schedules/{schedule_id}")
        return Schedule(**data)

    def create(self, **kwargs: Any) -> Schedule:
        """Create a new schedule.

        Requires scope ``schedule:write``.

        Parameters
        ----------
        **kwargs
            Fields matching :class:`~meetschedule_sdk.models.ScheduleInput`.
        """
        body = ScheduleInput(**kwargs)
        data = self._post("/open/v1/schedules", body=body)
        return Schedule(**data)

    def update(self, schedule_id: str, **kwargs: Any) -> Schedule:
        """Update a schedule's settings (partial).

        Requires scope ``schedule:write``.
        Only the fields passed are changed; omitted fields keep their values.
        """
        data = self._patch(f"/open/v1/schedules/{schedule_id}", body=kwargs)
        return Schedule(**data)

    def delete(self, schedule_id: str) -> None:
        """Delete a schedule and all its courses, events, and adjustments.

        Requires scope ``schedule:write``. **This cannot be undone.**
        """
        self._delete(f"/open/v1/schedules/{schedule_id}")

    def get_full(self, schedule_id: str) -> ScheduleBundle:
        """Get a full schedule snapshot — schedule + courses + events + adjustments.

        Requires scope ``schedule:read``.
        """
        data = self._get(f"/open/v1/schedules/{schedule_id}/full")
        return ScheduleBundle(
            schedule=Schedule(**data["schedule"]),
            courses=[Course(**c) for c in data["courses"]],
            events=[Event(**e) for e in data["events"]],
            adjustments=[Adjustment(**a) for a in data["adjustments"]],
        )

    # ── Nested resources ────────────────────────────────────────────────

    @property
    def courses(self) -> _CoursesResource:
        """Access courses nested under a schedule."""
        return _CoursesResource(self._client)

    @property
    def events(self) -> _EventsResource:
        """Access events nested under a schedule."""
        return _EventsResource(self._client)

    @property
    def adjustments(self) -> _AdjustmentsResource:
        """Access adjustments nested under a schedule."""
        return _AdjustmentsResource(self._client)


# ── Courses ──────────────────────────────────────────────────────────────────


class _CoursesResource(_BaseResource):
    """``/open/v1/schedules/{scheduleId}/courses`` and ``/open/v1/courses/{courseId}`` endpoints."""

    def get_all(self, schedule_id: str) -> list[Course]:
        """Get all courses (with their meetings) in a schedule.

        Requires scope ``entities:read``.
        """
        data = self._get(f"/open/v1/schedules/{schedule_id}/courses")
        return [Course(**item) for item in data]

    def create(self, schedule_id: str, **kwargs: Any) -> Course:
        """Create a new course in a schedule.

        Requires scope ``entities:write``.

        Parameters
        ----------
        schedule_id:
            The schedule to add the course to.
        **kwargs:
            Fields matching :class:`~meetschedule_sdk.models.CourseInput`.
            ``name`` and ``meetings`` are required.
        """
        body = CourseInput(**kwargs)
        data = self._post(
            f"/open/v1/schedules/{schedule_id}/courses",
            body=body,
        )
        return Course(**data)

    def update(self, course_id: str, **kwargs: Any) -> Course:
        """Update a course (partial).

        Requires scope ``entities:write``.
        """
        data = self._patch(f"/open/v1/courses/{course_id}", body=kwargs)
        return Course(**data)

    def delete(self, course_id: str) -> None:
        """Delete a course.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        self._delete(f"/open/v1/courses/{course_id}")


# ── Events ───────────────────────────────────────────────────────────────────


class _EventsResource(_BaseResource):
    """``/open/v1/schedules/{scheduleId}/events`` and ``/open/v1/events/{eventId}`` endpoints."""

    def get_all(
        self,
        schedule_id: str,
        *,
        type: str | None = None,  # noqa: A002
        from_time: str | None = None,
        to: str | None = None,
    ) -> list[Event]:
        """Get events in a schedule, with optional filters.

        Requires scope ``entities:read``.

        Parameters
        ----------
        schedule_id:
            The schedule to list events from.
        type:
            Optional. Filter by event type.
        from_time:
            Optional. Only return events whose time range starts at or after
            this ISO 8601 timestamp.
        to:
            Optional. Only return events whose time range ends at or before
            this ISO 8601 timestamp.
        """
        params: dict[str, str] = {}
        if type is not None:
            params["type"] = str(type)
        if from_time is not None:
            params["from"] = from_time
        if to is not None:
            params["to"] = to

        data = self._get(
            f"/open/v1/schedules/{schedule_id}/events",
            params=params,
        )
        return [Event(**item) for item in data]

    def create(self, schedule_id: str, **kwargs: Any) -> Event:
        """Create a new event in a schedule.

        Requires scope ``entities:write``.

        Parameters
        ----------
        schedule_id:
            The schedule to add the event to.
        **kwargs:
            Fields matching :class:`~meetschedule_sdk.models.EventInput`.
        """
        body = EventInput(schedule_id=schedule_id, **kwargs)
        data = self._post(
            f"/open/v1/schedules/{schedule_id}/events",
            body=body,
        )
        return Event(**data)

    def update(self, event_id: str, **kwargs: Any) -> Event:
        """Update an event (partial).

        Requires scope ``entities:write``.
        """
        data = self._patch(f"/open/v1/events/{event_id}", body=kwargs)
        return Event(**data)

    def delete(self, event_id: str) -> None:
        """Delete an event.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        self._delete(f"/open/v1/events/{event_id}")


# ── Adjustments ──────────────────────────────────────────────────────────────


class _AdjustmentsResource(_BaseResource):
    """``/open/v1/schedules/{scheduleId}/adjustments`` and ``/open/v1/adjustments/{adjustmentId}`` endpoints."""

    def get_all(self, schedule_id: str) -> list[Adjustment]:
        """Get all adjustments in a schedule.

        Requires scope ``entities:read``.
        """
        data = self._get(f"/open/v1/schedules/{schedule_id}/adjustments")
        return [Adjustment(**item) for item in data]

    def create(self, schedule_id: str, **kwargs: Any) -> Adjustment:
        """Create a new adjustment (cancel / makeup / reschedule).

        Requires scope ``entities:write``.

        Parameters
        ----------
        schedule_id:
            The schedule to add the adjustment to.
        **kwargs:
            Fields matching :class:`~meetschedule_sdk.models.AdjustmentInput`.
        """
        body = AdjustmentInput(schedule_id=schedule_id, **kwargs)
        data = self._post(
            f"/open/v1/schedules/{schedule_id}/adjustments",
            body=body,
        )
        return Adjustment(**data)

    def delete(self, adjustment_id: str) -> None:
        """Delete an adjustment.

        Requires scope ``entities:write``. **This cannot be undone.**
        The original course schedule is unaffected.
        """
        self._delete(f"/open/v1/adjustments/{adjustment_id}")


# ── Tasks ────────────────────────────────────────────────────────────────────


class _TasksResource(_BaseResource):
    """``/open/v1/tasks`` endpoints."""

    def get_all(self) -> list[Task]:
        """Get all tasks for this account.

        Requires scope ``entities:read``.
        Tasks are not scoped to a schedule.
        """
        data = self._get("/open/v1/tasks")
        return [Task(**item) for item in data]

    def create(self, **kwargs: Any) -> Task:
        """Create a new task.

        Requires scope ``entities:write``.

        Parameters
        ----------
        **kwargs:
            Fields matching :class:`~meetschedule_sdk.models.TaskInput`.
            ``title`` is required.
        """
        body = TaskInput(**kwargs)
        data = self._post("/open/v1/tasks", body=body)
        return Task(**data)

    def update(self, task_id: str, **kwargs: Any) -> Task:
        """Update a task (partial).

        Requires scope ``entities:write``.
        """
        data = self._patch(f"/open/v1/tasks/{task_id}", body=kwargs)
        return Task(**data)

    def delete(self, task_id: str) -> None:
        """Delete a task.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        self._delete(f"/open/v1/tasks/{task_id}")


# ── Main client ──────────────────────────────────────────────────────────────


class MeetSchedule:
    """Sync client for the **Meet Schedule Open API**.

    Usage::

        client = MeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx")

        # Schedules
        for s in client.schedules.get_all():
            print(s.name)

        # Full bundle
        bundle = client.schedules.get_full("sch_xxx")
        print(bundle.courses)

    Parameters
    ----------
    api_key:
        Your API key (``msk_live_...``), created on the Meet Schedule
        "开放平台" page.
    base_url:
        Base URL of the API. Defaults to the production endpoint.
    timeout:
        Request timeout in seconds. Defaults to 30.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.meetschedule.top",
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ConfigurationError("api_key must not be empty")

        self._client = httpx.Client(
            base_url=base_url,
            headers={"X-API-Key": api_key},
            timeout=httpx.Timeout(timeout),
        )

        self.schedules = _SchedulesResource(self._client)
        """Access schedule endpoints."""
        self.courses = _CoursesResource(self._client)
        """Access course endpoints."""
        self.events = _EventsResource(self._client)
        """Access event endpoints."""
        self.adjustments = _AdjustmentsResource(self._client)
        """Access adjustment endpoints."""
        self.tasks = _TasksResource(self._client)
        """Access task endpoints."""

    def close(self) -> None:
        """Close the underlying HTTP client (releases connections)."""
        self._client.close()

    def __enter__(self) -> MeetSchedule:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
