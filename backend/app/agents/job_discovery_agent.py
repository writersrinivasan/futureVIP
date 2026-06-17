"""
JobDiscoveryAgent

Searches multiple job sources based on candidate's skills and target roles:
  - Adzuna API
  - JSearch (RapidAPI)
  - Remotive (remote jobs)
  - RemoteOK
  - USAJobs

Deduplicates, normalises to unified schema, filters by relevance,
and prioritises recently posted jobs (≤ 7 days).
Returns up to 100 discovered jobs.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_JOBS = 100
_RECENT_DAYS = 7
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
_HEADERS = {"User-Agent": "FutureVIP-JobBot/1.0"}


# --------------------------------------------------------------------------- #
# Unified job schema
# --------------------------------------------------------------------------- #

def _normalise_job(raw: dict, source: str) -> dict:
    """Normalise a raw job dict from any source into the unified schema."""
    now = datetime.now(timezone.utc)

    def _parse_date(val) -> Optional[str]:
        if not val:
            return None
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
            except Exception:
                return None
        if isinstance(val, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%Y/%m/%d"):
                try:
                    return datetime.strptime(val[:19], fmt[:len(val)]).isoformat()
                except Exception:
                    continue
        return str(val)

    title = raw.get("title") or raw.get("position") or ""
    company = (
        raw.get("company")
        or raw.get("company_name")
        or (raw.get("company_object") or {}).get("display_name", "")
        or ""
    )
    location = (
        raw.get("location")
        or (raw.get("location_object") or {}).get("display_name", "")
        or raw.get("candidate_required_location", "")
        or ""
    )
    description = raw.get("description") or raw.get("job_description") or ""
    salary_min = raw.get("salary_min") or raw.get("salary_from") or raw.get("min_salary")
    salary_max = raw.get("salary_max") or raw.get("salary_to") or raw.get("max_salary")
    url = raw.get("redirect_url") or raw.get("url") or raw.get("job_apply_link") or raw.get("job_google_link") or ""
    remote = (
        raw.get("remote") is True
        or "remote" in location.lower()
        or raw.get("job_is_remote", False)
        or raw.get("remote_ok", False)
    )
    posted_raw = (
        raw.get("created")
        or raw.get("date")
        or raw.get("posted_at")
        or raw.get("date_posted")
        or raw.get("job_posted_at_datetime_utc")
        or raw.get("pub_date")
    )
    posted_at = _parse_date(posted_raw)

    # Extract requirements from description keywords or dedicated field
    requirements: list[str] = raw.get("requirements") or raw.get("tags") or []
    if isinstance(requirements, str):
        requirements = [r.strip() for r in requirements.split(",") if r.strip()]

    raw_id = raw.get("id") or raw.get("job_id") or hashlib.md5(f"{title}{company}{location}".encode()).hexdigest()[:12]
    external_id = f"{source}_{raw_id}"

    return {
        "external_id": external_id,
        "source": source,
        "title": title.strip(),
        "company_name": company.strip(),
        "location": location.strip(),
        "description": (description or "")[:5000],
        "requirements": requirements[:30],
        "salary_min": float(salary_min) if salary_min else None,
        "salary_max": float(salary_max) if salary_max else None,
        "salary_currency": raw.get("salary_currency_iso") or raw.get("currency") or "USD",
        "job_type": raw.get("job_type") or raw.get("contract_type") or raw.get("employment_type") or "full-time",
        "experience_level": raw.get("experience_level") or raw.get("job_employment_type") or "",
        "remote": bool(remote),
        "posted_at": posted_at,
        "url": url,
        "company_logo": raw.get("company_logo") or raw.get("logo"),
        "source_raw_id": str(raw_id),
    }


def _dedup_jobs(jobs: list[dict]) -> list[dict]:
    """Deduplicate by (title + company + location) hash."""
    seen: set[str] = set()
    unique: list[dict] = []
    for job in jobs:
        key = hashlib.md5(
            f"{job['title'].lower()}{job['company_name'].lower()}{job['location'].lower()}".encode()
        ).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def _is_recent(job: dict, days: int = _RECENT_DAYS) -> bool:
    """Return True if job was posted within `days` days."""
    posted = job.get("posted_at")
    if not posted:
        return True  # unknown date — include
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        dt = datetime.fromisoformat(posted)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt >= cutoff
    except Exception:
        return True


# --------------------------------------------------------------------------- #
# Source fetchers
# --------------------------------------------------------------------------- #

async def _fetch_adzuna(
    session: aiohttp.ClientSession,
    keywords: str,
    country: str = "us",
    results_per_page: int = 25,
) -> list[dict]:
    api_id = getattr(settings, "ADZUNA_API_ID", "")
    api_key = getattr(settings, "ADZUNA_API_KEY", "")
    if not api_id or not api_key:
        logger.warning("[JobDiscovery] Adzuna credentials missing, skipping")
        return []
    url = (
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        f"?app_id={api_id}&app_key={api_key}"
        f"&results_per_page={results_per_page}&what={keywords}&content-type=application/json"
    )
    try:
        async with session.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT) as resp:
            if resp.status != 200:
                logger.warning("[JobDiscovery] Adzuna returned %s", resp.status)
                return []
            data = await resp.json()
            return [_normalise_job(j, "adzuna") for j in data.get("results", [])]
    except Exception as exc:
        logger.error("[JobDiscovery] Adzuna fetch error: %s", exc)
        return []


async def _fetch_jsearch(
    session: aiohttp.ClientSession,
    query: str,
    num_pages: int = 2,
) -> list[dict]:
    api_key = getattr(settings, "JSEARCH_API_KEY", "")
    if not api_key:
        logger.warning("[JobDiscovery] JSearch API key missing, skipping")
        return []
    headers = {
        **_HEADERS,
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    jobs: list[dict] = []
    for page in range(1, num_pages + 1):
        url = f"https://jsearch.p.rapidapi.com/search?query={query}&page={page}&num_pages=1&date_posted=week"
        try:
            async with session.get(url, headers=headers, timeout=_REQUEST_TIMEOUT) as resp:
                if resp.status != 200:
                    break
                data = await resp.json()
                for j in data.get("data", []):
                    jobs.append(_normalise_job(j, "jsearch"))
        except Exception as exc:
            logger.error("[JobDiscovery] JSearch fetch error: %s", exc)
            break
    return jobs


async def _fetch_remotive(
    session: aiohttp.ClientSession,
    search: str,
) -> list[dict]:
    url = f"https://remotive.com/api/remote-jobs?search={search}&limit=30"
    try:
        async with session.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return [_normalise_job(j, "remotive") for j in data.get("jobs", [])]
    except Exception as exc:
        logger.error("[JobDiscovery] Remotive fetch error: %s", exc)
        return []


async def _fetch_remoteok(
    session: aiohttp.ClientSession,
    tag: str = "python",
) -> list[dict]:
    url = f"https://remoteok.com/api?tag={tag}"
    try:
        async with session.get(
            url,
            headers={**_HEADERS, "Accept": "application/json"},
            timeout=_REQUEST_TIMEOUT,
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            # First item is metadata — skip it
            job_list = [j for j in data if isinstance(j, dict) and j.get("position")]
            return [_normalise_job(j, "remoteok") for j in job_list[:20]]
    except Exception as exc:
        logger.error("[JobDiscovery] RemoteOK fetch error: %s", exc)
        return []


async def _fetch_usajobs(
    session: aiohttp.ClientSession,
    keywords: str,
) -> list[dict]:
    """USAJobs public API (no key required for basic search)."""
    url = (
        f"https://data.usajobs.gov/api/search?Keyword={keywords}&ResultsPerPage=25&DatePosted=7"
    )
    headers = {
        **_HEADERS,
        "Host": "data.usajobs.gov",
        "User-Agent": "writersrinivasan@gmail.com",  # required by USAJobs
        "Authorization-Key": "",  # public endpoint
    }
    try:
        async with session.get(url, headers=headers, timeout=_REQUEST_TIMEOUT) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            items = data.get("SearchResult", {}).get("SearchResultItems", [])
            normalised = []
            for item in items:
                mv = item.get("MatchedObjectDescriptor", {})
                raw = {
                    "id": mv.get("PositionID"),
                    "title": mv.get("PositionTitle"),
                    "company": mv.get("OrganizationName"),
                    "location": ", ".join(
                        loc.get("LocationName", "") for loc in mv.get("PositionLocation", [])
                    ),
                    "description": mv.get("QualificationSummary", ""),
                    "url": mv.get("ApplyURI", [None])[0],
                    "date": mv.get("PublicationStartDate"),
                    "salary_min": (mv.get("PositionRemuneration") or [{}])[0].get("MinimumRange"),
                    "salary_max": (mv.get("PositionRemuneration") or [{}])[0].get("MaximumRange"),
                    "remote": False,
                }
                normalised.append(_normalise_job(raw, "usajobs"))
            return normalised
    except Exception as exc:
        logger.error("[JobDiscovery] USAJobs fetch error: %s", exc)
        return []


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #

class JobDiscoveryAgent(BaseAgent):
    """
    Discovers jobs from multiple sources, deduplicates, filters, and normalises.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            intelligence = state.get("resume_intelligence") or {}
            parsed = state.get("parsed_resume") or {}
            skill_graph = state.get("skill_graph") or {}

            # Build search keywords from top skills + target roles
            top_skills = self._extract_top_skills(skill_graph, parsed)
            target_roles = [
                r.get("role", "")
                for r in intelligence.get("target_role_recommendations", [])
            ][:3]

            search_query = " ".join(target_roles[:2]) or " ".join(top_skills[:3]) or "software engineer"
            remotive_tag = top_skills[0].replace(" ", "-") if top_skills else "software-engineer"
            remoteok_tag = top_skills[0].split()[0] if top_skills else "python"

            logger.info("[JobDiscovery] Searching for: %s", search_query)

            all_jobs: list[dict] = []

            async with aiohttp.ClientSession() as session:
                results = await asyncio.gather(
                    _fetch_adzuna(session, search_query),
                    _fetch_jsearch(session, search_query),
                    _fetch_remotive(session, remotive_tag),
                    _fetch_remoteok(session, remoteok_tag),
                    _fetch_usajobs(session, search_query),
                    return_exceptions=True,
                )

            for res in results:
                if isinstance(res, Exception):
                    state = self._log_error(state, f"Source fetch error: {res}")
                elif isinstance(res, list):
                    all_jobs.extend(res)

            logger.info("[JobDiscovery] Raw jobs collected: %d", len(all_jobs))

            # Dedup
            unique_jobs = _dedup_jobs(all_jobs)

            # Prioritise recent
            recent = [j for j in unique_jobs if _is_recent(j)]
            older = [j for j in unique_jobs if not _is_recent(j)]
            ordered = recent + older

            # Filter: must have title and company
            filtered = [
                j for j in ordered
                if j.get("title") and j.get("company_name")
            ]

            final_jobs = filtered[:_MAX_JOBS]

            state["discovered_jobs"] = final_jobs

            confidence = min(len(final_jobs) / 20, 1.0) * 0.95
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"JobDiscoveryAgent: discovered {len(final_jobs)} jobs "
                    f"({len(recent)} recent), confidence={confidence:.2f}"
                ),
            )
            logger.info("[JobDiscovery] Final jobs: %d", len(final_jobs))

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _extract_top_skills(self, skill_graph: dict, parsed: dict) -> list[str]:
        nodes: list[dict] = skill_graph.get("nodes", [])
        if nodes:
            sorted_nodes = sorted(nodes, key=lambda n: n.get("weight", 0), reverse=True)
            return [n["name"] for n in sorted_nodes[:10]]
        # Fallback to parsed skills
        return [s.get("name", "") for s in (parsed.get("skills") or [])[:10] if s.get("name")]
