from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class JobItem:
    """A single job as collected from a source, before persistence."""

    source_job_id: str
    title: str
    company: str = ""
    city: str = ""
    source_url: str = ""
    description: str = ""
    requirements: str = ""
    salary: str = ""
    status: str = "OPEN"
    deadline: Optional[datetime] = None


class BaseCollector:
    """Interface every source collector implements."""

    name: str = "base"

    def collect(self) -> list[JobItem]:
        raise NotImplementedError
