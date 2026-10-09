import html as html_mod
import json
import re

import httpx
import quickjs

from .base import BaseCollector, CollectResult, JobItem, default_proxy

API = "https://www.shixiseng.com/interns"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_ICON = re.compile(r"&#x[0-9a-fA-F]+;?")
_PUA = re.compile(r"[- -⁯]")
_NUXT = re.compile(r"__NUXT__\s*=")


def _clean(s) -> str:
    s = html_mod.unescape(s or "")
    s = _ICON.sub("", s)
    s = s.replace("&", "")  # drop leftover entity fragments from icon glyphs
    s = _PUA.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def _salary(o) -> str:
    lo, hi = o.get("minsalary"), o.get("maxsalary")
    if lo is not None and hi is not None:
        try:
            return f"{int(lo)}-{int(hi)}元/天"
        except (TypeError, ValueError):
            return ""
    return ""


def _job_from_dict(o) -> JobItem | None:
    uuid = (o.get("uuid") or "").strip()
    title = _clean(o.get("name"))
    if not uuid or not title:
        return None
    return JobItem(
        source_job_id=uuid,
        title=title,
        company=_clean(o.get("cname")),
        city=_clean(o.get("city")),
        source_url=f"https://www.shixiseng.com/intern/detail?uuid={uuid}",
        description=_clean(o.get("industry")),
        requirements=_clean(o.get("degree")),
        salary=_salary(o),
    )


def _extract_nuxt_payload(html: str) -> str | None:
    """Extract only the `__NUXT__ = (function(){...})(...)` assignment that
    serializes the SSR data. Never returns any other inline script or page JS."""
    m = _NUXT.search(html)
    if not m:
        return None
    start = m.start()
    end = html.find("</script>", start)
    if end < 0:
        return None
    snippet = html[start:end].strip()
    if not snippet.startswith("__NUXT__="):
        return None
    return snippet.rstrip(";").strip()


class ShixisengCollector(BaseCollector):
    """实习僧 (shixiseng.com) — real campus/intern recruitment platform, no login.

    Jobs are server-rendered into a minified Nuxt `__NUXT__` payload; we evaluate
    it with a small JS engine to recover the job list.
    """

    name = "shixiseng"

    def collect(self) -> CollectResult:
        r = httpx.get(
            API, headers={"User-Agent": UA}, timeout=30, proxy=default_proxy(), trust_env=False
        )
        r.raise_for_status()
        html = r.text
        snippet = _extract_nuxt_payload(html)
        if snippet is None:
            raise RuntimeError("shixiseng: __NUXT__ payload not found")

        # Evaluate ONLY the minimal __NUXT__ serialization assignment (never any
        # other inline script or page JavaScript), within hard resource limits.
        ctx = quickjs.Context()
        ctx.set_time_limit(10)                   # CPU seconds
        ctx.set_memory_limit(128 * 1024 * 1024)  # 128 MiB
        ctx.eval(snippet)
        jobs = json.loads(str(ctx.eval("JSON.stringify(__NUXT__.data[0].interns.data)")))

        items = [j for j in (_job_from_dict(o) for o in jobs) if j is not None]
        if not items:
            raise RuntimeError("shixiseng: no jobs parsed")
        return CollectResult(items=items, raw=r.text)
