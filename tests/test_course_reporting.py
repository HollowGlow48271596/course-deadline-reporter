from datetime import date
from types import SimpleNamespace

from course_reporting import CourseDelivery, generate_report


class RecordingCompletions:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def create(self, *, model: str, messages: list[dict[str, str]]) -> SimpleNamespace:
        assert model == "auto"
        self.messages = messages
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="One learner needs follow-up."))]
        )


def test_report_exposes_overdue_delivery_decision() -> None:
    course = CourseDelivery.model_validate(
        {
            "course_id": "python-101",
            "title": "Python 101",
            "learners": [
                {"learner_id": "learner-7", "due_on": "2026-08-10"},
                {
                    "learner_id": "learner-8",
                    "due_on": "2026-08-10",
                    "completed_on": "2026-08-09",
                },
            ],
        }
    )
    completions = RecordingCompletions()

    report = generate_report(course, date(2026, 8, 13), completions)

    assert [status.state for status in report.statuses] == ["overdue", "completed_on_time"]
    assert "learner-7: overdue" in completions.messages[1]["content"]
    assert report.narrative == "One learner needs follow-up."
