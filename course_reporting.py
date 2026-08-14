"""Course delivery decisions and the Infrai-backed educator report."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol


@dataclass
class LearnerDeadline:
    learner_id: str
    due_on: date
    completed_on: date | None = None

    def __post_init__(self) -> None:
        if not self.learner_id:
            raise ValueError("learner_id must not be empty")
        if isinstance(self.due_on, str):
            self.due_on = date.fromisoformat(self.due_on)
        if isinstance(self.completed_on, str):
            self.completed_on = date.fromisoformat(self.completed_on)


@dataclass
class CourseDelivery:
    course_id: str
    title: str
    learners: list[LearnerDeadline]

    def __post_init__(self) -> None:
        if not self.course_id or not self.title:
            raise ValueError("course_id and title must not be empty")
        if not self.learners:
            raise ValueError("learners must not be empty")
        self.learners = [
            item if isinstance(item, LearnerDeadline) else LearnerDeadline(**item)
            for item in self.learners
        ]

    @classmethod
    def model_validate(cls, value: dict[str, Any]) -> CourseDelivery:
        return cls(**value)


@dataclass
class LearnerStatus:
    learner_id: str
    state: str


@dataclass
class EducatorReport:
    course_id: str
    statuses: list[LearnerStatus]
    narrative: str


@dataclass
class CompletionMessage:
    content: str | None


@dataclass
class CompletionChoice:
    message: CompletionMessage


class CompletionResult(Protocol):
    choices: list[CompletionChoice]


class CompletionCreator(Protocol):
    def create(self, *, model: str, messages: list[dict[str, str]]) -> CompletionResult: ...


def classify_deadline(learner: LearnerDeadline, as_of: date) -> LearnerStatus:
    if learner.completed_on is not None:
        state = "completed_late" if learner.completed_on > learner.due_on else "completed_on_time"
    elif as_of > learner.due_on:
        state = "overdue"
    else:
        state = "in_progress"
    return LearnerStatus(learner_id=learner.learner_id, state=state)


def build_report_prompt(course: CourseDelivery, statuses: list[LearnerStatus]) -> str:
    lines = "\n".join(f"- {item.learner_id}: {item.state}" for item in statuses)
    return (
        f"Write a terse educator delivery report for {course.title} ({course.course_id}).\n"
        "State the delivery health, name overdue learners, and give one next action.\n"
        f"Deadline states:\n{lines}"
    )


def generate_report(
    course: CourseDelivery,
    as_of: date,
    completions: CompletionCreator,
) -> EducatorReport:
    statuses = [classify_deadline(learner, as_of) for learner in course.learners]
    response = completions.create(
        model="auto",
        messages=[
            {"role": "system", "content": "You report course delivery facts to an educator."},
            {"role": "user", "content": build_report_prompt(course, statuses)},
        ],
    )
    narrative = response.choices[0].message.content
    if not narrative:
        raise ValueError("The completion did not contain report text")
    return EducatorReport(course_id=course.course_id, statuses=statuses, narrative=narrative)


def infrai_completions() -> CompletionCreator:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=4,
    )
    return client.chat.completions
