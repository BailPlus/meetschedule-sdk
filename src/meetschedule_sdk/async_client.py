"""Async HTTP client for the Meet Schedule Open API.

Usage::

    from meetschedule_sdk import AsyncMeetSchedule

    async with AsyncMeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx") as client:
        schedules = await client.schedules.get_all()
        for s in schedules:
            print(s.name)
"""

from __future__ import annotations

from typing import Any, Self

import httpx

from meetschedule_sdk.client import _raise_on_error, _to_dict
from meetschedule_sdk.exceptions import ConfigurationError, NetworkError
from meetschedule_sdk.models import (
    Adjustment,
    AdjustmentInput,
    Course,
    CourseInput,
    CoursePatch,
    Event,
    EventInput,
    EventPatch,
    Schedule,
    ScheduleBundle,
    ScheduleInput,
    ScheduleUpdate,
    Task,
    TaskInput,
    TaskPatch,
)

# ── Base async resource ─────────────────────────────────────────────────────


class _AsyncBaseResource:
    """Base class for async resource sub-clients."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> httpx.Response:
        json_data = _to_dict(json_body) if json_body is not None else None

        try:
            response = await self._client.request(
                method,
                path,
                params=params,
                json=json_data,
            )
        except httpx.RequestError as exc:
            raise NetworkError(str(exc)) from exc

        _raise_on_error(response)
        return response

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        resp = await self._request("GET", path, params=params)
        if resp.status_code == 204:
            return None
        return resp.json()

    async def _post(
        self, path: str, *, body: Any = None, params: dict[str, str] | None = None
    ) -> Any:
        resp = await self._request("POST", path, params=params, json_body=body)
        return resp.json()

    async def _patch(self, path: str, *, body: Any = None) -> Any:
        resp = await self._request("PATCH", path, json_body=body)
        return resp.json()

    async def _delete(self, path: str) -> None:
        await self._request("DELETE", path)


# ── Schedules ────────────────────────────────────────────────────────────────


class _AsyncSchedulesResource(_AsyncBaseResource):
    """Async ``/open/v1/schedules`` endpoints."""

    async def get_all(self) -> list[Schedule]:
        """Get all schedules.

        Requires scope ``schedule:read``.
        """
        data = await self._get("/open/v1/schedules")
        return [Schedule.model_validate(item) for item in data]

    async def get(self, schedule_id: str) -> Schedule:
        """Get a single schedule by ID.

        Requires scope ``schedule:read``.
        """
        data = await self._get(f"/open/v1/schedules/{schedule_id}")
        return Schedule.model_validate(data)

    async def create(self, input: ScheduleInput) -> Schedule:
        """Create a new schedule.

        Requires scope ``schedule:write``.

        Parameters
        ----------
        input:
            The schedule fields to create.
        """
        data = await self._post("/open/v1/schedules", body=input)
        return Schedule.model_validate(data)

    async def update(self, schedule_id: str, input: ScheduleUpdate) -> Schedule:
        """Update a schedule (partial).

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
        data = await self._patch(f"/open/v1/schedules/{schedule_id}", body=body)
        return Schedule.model_validate(data)

    async def delete(self, schedule_id: str) -> None:
        """Delete a schedule and all its contents.

        Requires scope ``schedule:write``. **This cannot be undone.**
        """
        await self._delete(f"/open/v1/schedules/{schedule_id}")

    async def get_full(self, schedule_id: str) -> ScheduleBundle:
        """Get a full schedule snapshot — schedule + courses + events + adjustments.

        Requires scope ``schedule:read``.
        """
        data = await self._get(f"/open/v1/schedules/{schedule_id}/full")
        return ScheduleBundle(
            schedule=Schedule.model_validate(data["schedule"]),
            courses=[Course.model_validate(c) for c in data["courses"]],
            events=[Event.model_validate(e) for e in data["events"]],
            adjustments=[Adjustment.model_validate(a) for a in data["adjustments"]],
        )

    @property
    def courses(self) -> _AsyncCoursesResource:
        return _AsyncCoursesResource(self._client)

    @property
    def events(self) -> _AsyncEventsResource:
        return _AsyncEventsResource(self._client)

    @property
    def adjustments(self) -> _AsyncAdjustmentsResource:
        return _AsyncAdjustmentsResource(self._client)


# ── Courses ──────────────────────────────────────────────────────────────────


class _AsyncCoursesResource(_AsyncBaseResource):
    """Async ``/open/v1/schedules/{scheduleId}/courses`` endpoints."""

    async def get_all(self, schedule_id: str) -> list[Course]:
        """Get all courses (with meetings) in a schedule.

        Requires scope ``entities:read``.
        """
        data = await self._get(f"/open/v1/schedules/{schedule_id}/courses")
        return [Course.model_validate(item) for item in data]

    async def create(self, schedule_id: str, input: CourseInput) -> Course:
        """Create a new course.

        Requires scope ``entities:write``.

        Parameters
        ----------
        schedule_id:
            The schedule to add the course to.
        input:
            The course fields to create.
        """
        data = await self._post(
            f"/open/v1/schedules/{schedule_id}/courses",
            body=input,
        )
        return Course.model_validate(data)

    async def update(self, course_id: str, input: CoursePatch) -> Course:
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
        data = await self._patch(f"/open/v1/courses/{course_id}", body=body)
        return Course.model_validate(data)

    async def delete(self, course_id: str) -> None:
        """Delete a course.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        await self._delete(f"/open/v1/courses/{course_id}")


# ── Events ───────────────────────────────────────────────────────────────────


class _AsyncEventsResource(_AsyncBaseResource):
    """Async ``/open/v1/schedules/{scheduleId}/events`` endpoints."""

    async def get_all(
        self,
        schedule_id: str,
        *,
        type: str | None = None,
        from_time: str | None = None,
        to: str | None = None,
    ) -> list[Event]:
        """Get events with optional filters.

        Requires scope ``entities:read``.
        """
        params: dict[str, str] = {}
        if type is not None:
            params["type"] = str(type)
        if from_time is not None:
            params["from"] = from_time
        if to is not None:
            params["to"] = to

        data = await self._get(
            f"/open/v1/schedules/{schedule_id}/events",
            params=params,
        )
        return [Event.model_validate(item) for item in data]

    async def create(
        self,
        input: EventInput,
        *,
        allow_duplicate_title: bool = False,
    ) -> Event:
        """Create a new event.

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
        data = await self._post(
            f"/open/v1/schedules/{input.schedule_id}/events",
            body=input,
            params={"allow_duplicate_title": "true"} if allow_duplicate_title else None,
        )
        return Event.model_validate(data)

    async def update(self, event_id: str, input: EventPatch) -> Event:
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
        data = await self._patch(f"/open/v1/events/{event_id}", body=body)
        return Event.model_validate(data)

    async def delete(self, event_id: str) -> None:
        """Delete an event.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        await self._delete(f"/open/v1/events/{event_id}")


# ── Adjustments ──────────────────────────────────────────────────────────────


class _AsyncAdjustmentsResource(_AsyncBaseResource):
    """Async ``/open/v1/schedules/{scheduleId}/adjustments`` endpoints."""

    async def get_all(self, schedule_id: str) -> list[Adjustment]:
        """Get all adjustments in a schedule.

        Requires scope ``entities:read``.
        """
        data = await self._get(f"/open/v1/schedules/{schedule_id}/adjustments")
        return [Adjustment.model_validate(item) for item in data]

    async def create(self, input: AdjustmentInput) -> Adjustment:
        """Create a new adjustment (cancel / makeup / reschedule).

        Requires scope ``entities:write``.

        Parameters
        ----------
        input:
            The adjustment fields to create. Must include ``schedule_id``.
        """
        data = await self._post(
            f"/open/v1/schedules/{input.schedule_id}/adjustments",
            body=input,
        )
        return Adjustment.model_validate(data)

    async def delete(self, adjustment_id: str) -> None:
        """Delete an adjustment.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        await self._delete(f"/open/v1/adjustments/{adjustment_id}")


# ── Tasks ────────────────────────────────────────────────────────────────────


class _AsyncTasksResource(_AsyncBaseResource):
    """Async ``/open/v1/tasks`` endpoints."""

    async def get_all(self) -> list[Task]:
        """Get all tasks for this account.

        Requires scope ``entities:read``.
        """
        data = await self._get("/open/v1/tasks")
        return [Task.model_validate(item) for item in data]

    async def create(self, input: TaskInput) -> Task:
        """Create a new task.

        Requires scope ``entities:write``.

        Parameters
        ----------
        input:
            The task fields to create.
        """
        data = await self._post("/open/v1/tasks", body=input)
        return Task.model_validate(data)

    async def update(self, task_id: str, input: TaskPatch) -> Task:
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
        data = await self._patch(f"/open/v1/tasks/{task_id}", body=body)
        return Task.model_validate(data)

    async def delete(self, task_id: str) -> None:
        """Delete a task.

        Requires scope ``entities:write``. **This cannot be undone.**
        """
        await self._delete(f"/open/v1/tasks/{task_id}")


# ── Main async client ────────────────────────────────────────────────────────


class AsyncMeetSchedule:
    """Async client for the **Meet Schedule Open API**.

    Usage::

        async with AsyncMeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx") as client:
            schedules = await client.schedules.get_all()
            bundle = await client.schedules.get_full("sch_xxx")
            print(bundle.courses)

        # Or manage the lifecycle manually:
        client = AsyncMeetSchedule(api_key="msk_live_xxxxxxxxxxxxxxxxxxxx")
        try:
            schedules = await client.schedules.get_all()
        finally:
            await client.close()

    Parameters
    ----------
    api_key:
        Your API key (``msk_live_...``).
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

        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-API-Key": api_key},
            timeout=httpx.Timeout(timeout),
        )

        self.schedules = _AsyncSchedulesResource(self._client)
        """Access schedule endpoints."""
        self.courses = _AsyncCoursesResource(self._client)
        """Access course endpoints."""
        self.events = _AsyncEventsResource(self._client)
        """Access event endpoints."""
        self.adjustments = _AsyncAdjustmentsResource(self._client)
        """Access adjustment endpoints."""
        self.tasks = _AsyncTasksResource(self._client)
        """Access task endpoints."""

    async def close(self) -> None:
        """Close the underlying async HTTP client (releases connections)."""
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
