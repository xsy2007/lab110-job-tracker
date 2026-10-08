import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def default_proxy() -> Optional[str]:
    """Read the proxy from env (like curl) so httpx routes through it while
    ignoring the possibly-malformed NO_PROXY list that breaks httpx's parser."""
    return (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("ALL_PROXY")
        or None
    )


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


@dataclass
class CollectResult:
    """Parsed jobs plus the raw response text for evidence."""

    items: list[JobItem] = field(default_factory=list)
    raw: str = ""


class BaseCollector:
    """Interface every source collector implements."""

    name: str = "base"

    def collect(self) -> CollectResult:
        raise NotImplementedError
