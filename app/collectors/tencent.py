import time

import httpx

from .base import BaseCollector, CollectResult, JobItem, default_proxy

API = "https://careers.tencent.com/tencentcareer/api/post/Query"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class TencentCollector(BaseCollector):
    """Tencent official careers site (real big-company source), no login required."""

    name = "tencent"

    def collect(self) -> CollectResult:
        params = {
            "timestamp": int(time.time() * 1000),
            "countryId": "",
            "cityId": "",
            "bgIds": "",
            "productId": "",
            "categoryId": "",
            "parentCategoryId": "",
            "attrId": "",
            "keyword": "",
            "pageIndex": 1,
            "pageSize": 15,
            "language": "zh-cn",
            "area": "cn",
        }
        headers = {
            "User-Agent": UA,
            "Referer": "https://careers.tencent.com/",
            "Accept": "application/json",
        }
        r = httpx.get(API, params=params, headers=headers, timeout=30, proxy=default_proxy(), trust_env=False)
        r.raise_for_status()
        data = r.json()
        posts = (data.get("Data") or {}).get("Posts") or []
        items = []
        for p in posts:
            is_valid = bool(p.get("IsValid", True))
            items.append(
                JobItem(
                    source_job_id=str(p.get("PostId") or ""),
                    title=(p.get("RecruitPostName") or "").strip(),
                    company=(p.get("ComName") or "").strip() or "腾讯",
                    city=(p.get("LocationName") or "").strip(),
                    source_url=(p.get("PostURL") or "").strip().replace("http://", "https://", 1),
                    description=(p.get("Responsibility") or "").strip(),
                    requirements=(p.get("RequireWorkYearsName") or "").strip(),
                    status="OPEN" if is_valid else "CLOSED",
                )
            )
        if not items:
            raise RuntimeError("Tencent API returned no jobs")
        return CollectResult(items=items, raw=r.text)
