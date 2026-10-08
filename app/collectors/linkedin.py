import re

import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, CollectResult, JobItem, default_proxy

API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class LinkedInCollector(BaseCollector):
    """LinkedIn public guest job search (real platform source), no login required."""

    name = "linkedin"

    def collect(self) -> CollectResult:
        params = {"keywords": "software engineer", "location": "China", "start": 0}
        headers = {"User-Agent": UA}
        r = httpx.get(API, params=params, headers=headers, timeout=30, proxy=default_proxy(), trust_env=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for card in soup.select('div[data-entity-urn*="jobPosting"]'):
            urn = card.get("data-entity-urn") or ""
            m = re.search(r"jobPosting:(\d+)", urn)
            if not m:
                continue
            job_id = m.group(1)
            title_el = card.select_one(".base-search-card__title")
            sub_el = card.select_one(".base-search-card__subtitle")
            loc_el = card.select_one(".job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")
            href = (link_el.get("href") or "") if link_el else ""
            loc = (loc_el.get_text(strip=True) if loc_el else "")
            items.append(
                JobItem(
                    source_job_id=job_id,
                    title=(title_el.get_text(strip=True) if title_el else ""),
                    company=(sub_el.get_text(" ", strip=True) if sub_el else ""),
                    city=loc.split(",")[0].strip() if loc else "",
                    source_url=href.split("?")[0],
                )
            )
        return CollectResult(items=items, raw=r.text)
