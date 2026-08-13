"""HTTP entry point for course delivery reporting."""

from datetime import date

from fastapi import Depends, FastAPI

from course_reporting import (
    CompletionCreator,
    CourseDelivery,
    EducatorReport,
    generate_report,
    infrai_completions,
)


service = FastAPI(title="Course delivery reporter")


@service.post("/educator/reports", response_model=EducatorReport)
def create_educator_report(
    course: CourseDelivery,
    as_of: date,
    completions: CompletionCreator = Depends(infrai_completions),
) -> EducatorReport:
    return generate_report(course, as_of, completions)
