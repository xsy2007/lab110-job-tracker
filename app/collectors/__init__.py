from .base import BaseCollector, CollectResult, JobItem
from .linkedin import LinkedInCollector
from .tencent import TencentCollector

REGISTRY = {
    "tencent": TencentCollector,
    "linkedin": LinkedInCollector,
}


def get_collector(key: str) -> BaseCollector:
    cls = REGISTRY.get(key)
    if cls is None:
        raise ValueError(f"Unknown collector: {key}")
    return cls()


__all__ = ["BaseCollector", "CollectResult", "JobItem", "get_collector"]
