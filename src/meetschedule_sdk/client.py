"""Sync HTTP client for the Meet Schedule Open API.

Usage::

    from meetschedule_sdk import MeetSchedule

    client = MeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx")

    # List schedules
    schedules = client.schedules.get_all()

    # Create a course
    course = client.courses.create(
        schedule_id="sch_xxx",
        input=CourseInput(
            name="高等数学（下）",
            meetings=[
                MeetingInput(
                    day_of_week=1,
                    start_period=3,
                    end_period=4,
                    weeks=[1, 3, 5, 7, 9, 11, 13, 15],
                ),
            ],
        ),
    )
"""

from __future__ import annotations

from typing import Any, Self

import httpx

from meetschedule_sdk.exceptions import (
    ConfigurationError,
    NetworkError,
    map_status_code,
)
from meetschedule_sdk.models import (
    Adjustment,
    AdjustmentInput,
    AdjustmentPatch,
    ApiError,
    Course,
    CourseInput,
    CoursePatch,
    Event,
    EventBatchCreateRequest,
    EventBatchDeleteRequest,
    EventBatchDeleteResponse,
    EventInput,
    EventPatch,
    Schedule,
    ScheduleBundle,
    ScheduleInput,
    ScheduleUpdate,
    Task,
    TaskInput,
    TaskPatch,
    TimeSlotGroup,
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
    """Recursively convert a pydantic model / enum / dict to a JSON-safe dict.

    Handles:
    - pydantic ``BaseModel`` → dict (via ``model_dump``)
    - ``dict`` → recursively converted dict
    - ``list`` / ``tuple`` → list of converted items
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
    if hasattr(obj, "model_dump"):
        return _to_dict(obj.model_dump(exclude_none=True))
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
        self, path: str, *, body: Any = None, params: dict[str, str] | None = None
    ) -> Any:
        """POST and return parsed JSON (expects 201)."""
        resp = self._request("POST", path, params=params, json_body=body)
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
        return [Schedule.model_validate(item) for item in data]

    def get(self, schedule_id: str) -> Schedule:
        """Get a single schedule by ID.

        Requires scope ``schedule:read``.
        """
        data = self._get(f"/open/v1/schedules/{schedule_id}")
        return Schedule.model_validate(data)

    def get_current(self) -> Schedule:
        """Get the schedule currently in use (the one shown on open).

        Requires scope ``schedule:read``.

        Raises
        ------
        NotFoundError:
            If the account has no schedules yet.
        """
        data = self._get("/open/v1/schedules/current")
        return Schedule.model_validate(data)

    def create(self, input: ScheduleInput) -> Schedule:
        """Create a new schedule.

        Requires scope ``schedule:write``.

        Parameters
        ----------
        input:
            The schedule fields to create.
        """
        data = self._post("/open/v1/schedules", body=input)
        return Schedule.model_validate(data)

    def update(self, schedule_id: str, input: ScheduleUpdate) -> Schedule:
        """Update a schedule's settings (partial).

        Requires scope ``schedule:write``.
        Only the fields passed are changed; omitted fields keep their values.

        Parameters
        ----------
        schedule_id:
            The schedule to update.
        input:
            The fields to update (all optional).
        """
        body = input.model_dump(exclude_unset=True)
        data = self._patch(f"/open/v1/schedules/{schedule_id}", body=body)
        return Schedule.model_validate(data)

    def delete(self, schedule_id: str) -> None:
        """Delete a schedule and all its courses, events, and adjustments.

        Requires scope ``schedule:write``. **This cannot be undone.**
        """
        self._delete(f"/open/v1/schedules/{schedule_id}")

    def get_full(self, schedule_id: str) -> ScheduleBundle:
        """Get a full schedule snapshot — schedule + courses + events
        + adjustments + the account's timeslot groups.

        Requires scope ``schedule:read``.
        """
        data = self._get(f"/open/v1/schedules/{schedule_id}/full")
        return ScheduleBundle(
            schedule=Schedule.model_validate(data["schedule"]),
            courses=[Course.model_validate(c) for c in data["courses"]],
            events=[Event.model_validate(e) for e in data["events"]],
            adjustments=[Adjustment.model_validate(a) for a in data["adjustments"]],
            timeslot_groups=[
                TimeSlotGroup.model_validate(g) for g in data["timeslot_groups"]
            ],
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
    """``/open/v1/schedules/{scheduleId}/courses``
    and ``/open/v1/courses/{courseId}`` endpoints."""

    def get_all(self, schedule_id: str) -> list[Course]:
        """Get all courses (with their meetings) in a schedule.

        Requires scope ``entities:read``.
        """
        data = self._get(f"/open/v1/schedules/{schedule_id}/courses")
        return [Course.model_validate(item) for item in data]

    def create(self, schedule_id: str, input: CourseInput) -> Course:
        """Create a new course in a schedule.

        Requires scope ``entities:write``.

        Parameters
        ----------
        schedule_id:
            The schedule to add the course to.
        input:
            The course fields to create.
        """
        data = self._post(
            f"/open/v1/schedules/{schedule_id}/courses",
            body=input,
        )
        return Course.model_validate(data)

    def update(self, course_id: str, input: CoursePatch) -> Course:
        """Update a course (partial).

        Requires scope ``entities:write``.
        Only the fields passed are changed; omitted fields keep their values.
        ``meetings`` is special: when set, it replaces all existing meetings.

        Parameters
        ----------
        course_id:
            The course to update.
        input:
            The fields to update (all optional).
        """
        body = input.model_dump(exclude_unset=True)
        data = self._patch(f"/open/v1/courses/{course_id}", body=body)
        return Course.model_validate(data)

    def delete(self, course_id: str) -> None:
        """Delete a course.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        self._delete(f"/open/v1/courses/{course_id}")


# ── Events ───────────────────────────────────────────────────────────────────


class _EventsResource(_BaseResource):
    """``/open/v1/schedules/{scheduleId}/events``
    and ``/open/v1/events/{eventId}`` endpoints."""

    def get_all(
        self,
        schedule_id: str,
        *,
        type: str | None = None,
        from_time: str | None = None,
        to: str | None = None,
        done: bool | None = None,
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
        done:
            Optional. Filter by completion status: ``True`` only returns
            completed events, ``False`` only uncompleted ones.
        """
        params: dict[str, str] = {}
        if type is not None:
            params["type"] = str(type)
        if from_time is not None:
            params["from"] = from_time
        if to is not None:
            params["to"] = to
        if done is not None:
            params["done"] = "true" if done else "false"

        data = self._get(
            f"/open/v1/schedules/{schedule_id}/events",
            params=params,
        )
        return [Event.model_validate(item) for item in data]

    def get(self, event_id: str) -> Event:
        """Get a single event by ID.

        Requires scope ``entities:read``.
        """
        data = self._get(f"/open/v1/events/{event_id}")
        return Event.model_validate(data)

    def get_by_ids(self, ids: list[str]) -> list[Event]:
        """Batch-fetch events by their IDs.

        Requires scope ``entities:read``.

        Parameters
        ----------
        ids:
            The event IDs to fetch. The request repeats the ``ids`` query
            parameter once per ID (``?ids=a&ids=b``).
        """
        data = self._get("/open/v1/events", params={"ids": ids})
        return [Event.model_validate(item) for item in data]

    def create(
        self,
        input: EventInput,
        *,
        allow_duplicate_title: bool = False,
    ) -> Event:
        """Create a new event in a schedule.

        Requires scope ``entities:write``.

        By default, events with the same title as an existing non-deleted
        event in the same schedule will be rejected (409). Pass
        ``allow_duplicate_title=True`` to skip this check.

        Parameters
        ----------
        input:
            The event fields to create. Must include ``schedule_id``.
        allow_duplicate_title:
            Allow creating an event with a title that already exists
            in the schedule.
        """
        data = self._post(
            f"/open/v1/schedules/{input.schedule_id}/events",
            body=input,
            params={"allow_duplicate_title": "true"} if allow_duplicate_title else None,
        )
        return Event.model_validate(data)

    def update(self, event_id: str, input: EventPatch) -> Event:
        """Update an event (partial).

        Requires scope ``entities:write``.
        Only the fields passed are changed; omitted fields keep their values.

        Parameters
        ----------
        event_id:
            The event to update.
        input:
            The fields to update (all optional).
        """
        body = input.model_dump(exclude_unset=True)
        data = self._patch(f"/open/v1/events/{event_id}", body=body)
        return Event.model_validate(data)

    def delete(self, event_id: str) -> None:
        """Delete an event.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        self._delete(f"/open/v1/events/{event_id}")

    def create_batch(
        self,
        schedule_id: str,
        events: list[EventInput],
        *,
        allow_duplicate_title: bool = False,
    ) -> list[Event]:
        """Batch-create events in a schedule.

        Requires scope ``entities:write``.

        Accepts 1–100 events; all events are validated and written in a single
        transaction, so if any one fails the whole batch is rejected. By default
        events with a title already present in the schedule (or in this batch)
        are rejected with a ``409``; pass ``allow_duplicate_title=True`` to
        permit duplicates.

        The returned list follows the order of *events*.

        Parameters
        ----------
        schedule_id:
            The schedule to add the events to.
        events:
            The event fields to create (each must carry this ``schedule_id``).
        allow_duplicate_title:
            Allow creating events with titles that already exist.
        """
        body = EventBatchCreateRequest(events=events)
        params = {"allow_duplicate_title": "true"} if allow_duplicate_title else None
        resp = self._request(
            "POST",
            f"/open/v1/schedules/{schedule_id}/events/batch",
            params=params,
            json_body=body,
        )
        return [Event.model_validate(item) for item in resp.json()]

    def delete_batch(self, ids: list[str]) -> EventBatchDeleteResponse:
        """Batch-delete events by ID.

        Requires scope ``entities:write``. **This cannot be undone.**

        Accepts 1–100 IDs (counting duplicates); each ID is processed once.
        IDs that don't exist, are already deleted, or don't belong to this
        account do not fail the batch — they are listed in ``not_found_ids``.

        Parameters
        ----------
        ids:
            The event IDs to delete.
        """
        body = EventBatchDeleteRequest(ids=ids)
        resp = self._request("DELETE", "/open/v1/events/batch", json_body=body)
        return EventBatchDeleteResponse.model_validate(resp.json())


# ── Adjustments ──────────────────────────────────────────────────────────────


class _AdjustmentsResource(_BaseResource):
    """``/open/v1/schedules/{scheduleId}/adjustments``
    and ``/open/v1/adjustments/{adjustmentId}`` endpoints."""

    def get_all(self, schedule_id: str) -> list[Adjustment]:
        """Get all adjustments in a schedule.

        Requires scope ``entities:read``.
        """
        data = self._get(f"/open/v1/schedules/{schedule_id}/adjustments")
        return [Adjustment.model_validate(item) for item in data]

    def create(self, input: AdjustmentInput) -> Adjustment:
        """Create a new adjustment (cancel / makeup / reschedule).

        Requires scope ``entities:write``.

        Parameters
        ----------
        input:
            The adjustment fields to create. Must include ``schedule_id``.
        """
        data = self._post(
            f"/open/v1/schedules/{input.schedule_id}/adjustments",
            body=input,
        )
        return Adjustment.model_validate(data)

    def get(self, adjustment_id: str) -> Adjustment:
        """Get a single adjustment by ID.

        Requires scope ``entities:read``.
        """
        data = self._get(f"/open/v1/adjustments/{adjustment_id}")
        return Adjustment.model_validate(data)

    def update(self, adjustment_id: str, input: AdjustmentPatch) -> Adjustment:
        """Update an adjustment (partial).

        Requires scope ``entities:write``.
        Only the fields passed are changed; omitted fields keep their values.

        Parameters
        ----------
        adjustment_id:
            The adjustment to update.
        input:
            The fields to update (all optional).
        """
        body = input.model_dump(exclude_unset=True)
        data = self._patch(f"/open/v1/adjustments/{adjustment_id}", body=body)
        return Adjustment.model_validate(data)

    def delete(self, adjustment_id: str) -> None:
        """Delete an adjustment.

        Requires scope ``entities:write``. **This cannot be undone.**
        The original course schedule is unaffected.
        """
        self._delete(f"/open/v1/adjustments/{adjustment_id}")


# ── Timeslot groups ──────────────────────────────────────────────────────────


class _TimeslotGroupsResource(_BaseResource):
    """``/open/v1/timeslot-groups`` endpoints (account-level resources)."""

    def get_all(self) -> list[TimeSlotGroup]:
        """Get all timeslot (作息) groups and their periods for this account.

        Requires scope ``entities:read``.
        The default group is listed first.
        """
        data = self._get("/open/v1/timeslot-groups")
        return [TimeSlotGroup.model_validate(item) for item in data]

    def get(self, group_id: str) -> TimeSlotGroup:
        """Get a single timeslot group by ID.

        Requires scope ``entities:read``.
        """
        data = self._get(f"/open/v1/timeslot-groups/{group_id}")
        return TimeSlotGroup.model_validate(data)


# ── Tasks ────────────────────────────────────────────────────────────────────


class _TasksResource(_BaseResource):
    """``/open/v1/tasks`` endpoints."""

    def get_all(self) -> list[Task]:
        """Get all tasks for this account.

        Requires scope ``entities:read``.
        Tasks are not scoped to a schedule.
        """
        data = self._get("/open/v1/tasks")
        return [Task.model_validate(item) for item in data]

    def get(self, task_id: str) -> Task:
        """Get a single task by ID.

        Requires scope ``entities:read``.
        """
        data = self._get(f"/open/v1/tasks/{task_id}")
        return Task.model_validate(data)

    def create(self, input: TaskInput) -> Task:
        """Create a new task.

        Requires scope ``entities:write``.

        Parameters
        ----------
        input:
            The task fields to create.
        """
        data = self._post("/open/v1/tasks", body=input)
        return Task.model_validate(data)

    def update(self, task_id: str, input: TaskPatch) -> Task:
        """Update a task (partial).

        Requires scope ``entities:write``.
        Only the fields passed are changed; omitted fields keep their values.

        Parameters
        ----------
        task_id:
            The task to update.
        input:
            The fields to update (all optional).
        """
        body = input.model_dump(exclude_unset=True)
        data = self._patch(f"/open/v1/tasks/{task_id}", body=body)
        return Task.model_validate(data)

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
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ConfigurationError("api_key must not be empty")

        if client is None:
            client = httpx.Client()
        client.base_url = base_url
        client.headers["X-API-Key"] = api_key
        self._client = client

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
        self.timeslot_groups = _TimeslotGroupsResource(self._client)
        """Access timeslot (作息) group endpoints."""

    def close(self) -> None:
        """Close the underlying HTTP client (releases connections)."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
