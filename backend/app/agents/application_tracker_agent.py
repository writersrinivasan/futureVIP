"""
ApplicationTrackerAgent

Tracks job application lifecycle and provides analytics:

Status transitions:
  saved → applied → screening → phone_screen → technical → interview
  → offer → negotiation → accepted | rejected | withdrawn

Features:
  - Follow-up reminders
  - Response-rate analytics
  - Interview scheduling suggestions
  - Rejection pattern analysis
  - Success probability scoring
  - Recommendations for next actions
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState
from app.agents.tools import save_to_database

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Status transition graph
# --------------------------------------------------------------------------- #

_STATUS_FLOW: dict[str, list[str]] = {
    "saved":       ["applied", "withdrawn"],
    "applied":     ["screening", "rejected", "withdrawn"],
    "screening":   ["phone_screen", "rejected", "withdrawn"],
    "phone_screen": ["technical", "rejected", "withdrawn"],
    "technical":   ["interview", "rejected", "withdrawn"],
    "interview":   ["offer", "rejected", "withdrawn"],
    "offer":       ["negotiation", "accepted", "rejected", "withdrawn"],
    "negotiation": ["accepted", "rejected", "withdrawn"],
    "accepted":    [],
    "rejected":    [],
    "withdrawn":   [],
}

_TERMINAL_STATUSES = {"accepted", "rejected", "withdrawn"}

# Days before a follow-up reminder is triggered
_FOLLOW_UP_DAYS: dict[str, int] = {
    "applied":     5,
    "screening":   3,
    "phone_screen": 7,
    "technical":   7,
    "interview":   5,
    "offer":       2,
}

# --------------------------------------------------------------------------- #
# Function-calling schema
# --------------------------------------------------------------------------- #

_TRACKER_ANALYSIS_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_application_pipeline",
        "description": (
            "Analyse the candidate's job application pipeline and provide "
            "actionable recommendations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pipeline_health": {
                    "type": "object",
                    "properties": {
                        "total_applications": {"type": "integer"},
                        "active_applications": {"type": "integer"},
                        "response_rate_pct": {"type": "number"},
                        "interview_conversion_pct": {"type": "number"},
                        "offer_rate_pct": {"type": "number"},
                        "health_score": {"type": "number", "minimum": 0, "maximum": 100},
                        "assessment": {"type": "string"},
                    },
                    "required": ["total_applications", "response_rate_pct", "health_score"],
                },
                "rejection_patterns": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "frequency": {"type": "string"},
                            "likely_cause": {"type": "string"},
                            "mitigation": {"type": "string"},
                        },
                        "required": ["pattern", "likely_cause"],
                    },
                },
                "applications_needing_followup": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "job_id": {"type": "string"},
                            "job_title": {"type": "string"},
                            "company": {"type": "string"},
                            "status": {"type": "string"},
                            "days_since_update": {"type": "integer"},
                            "recommended_action": {"type": "string"},
                            "message_template": {"type": "string"},
                        },
                        "required": ["job_id", "status", "recommended_action"],
                    },
                },
                "success_probabilities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "job_id": {"type": "string"},
                            "probability_pct": {"type": "number"},
                            "key_factors": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["job_id", "probability_pct"],
                    },
                },
                "prioritised_next_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low"]},
                            "deadline": {"type": "string"},
                            "rationale": {"type": "string"},
                        },
                        "required": ["action", "priority"],
                    },
                    "maxItems": 10,
                },
                "weekly_targets": {
                    "type": "object",
                    "properties": {
                        "applications_to_submit": {"type": "integer"},
                        "follow_ups_to_send": {"type": "integer"},
                        "networking_outreach": {"type": "integer"},
                        "skills_to_practice": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "required": ["pipeline_health", "prioritised_next_actions"],
        },
    },
}


class ApplicationTrackerAgent(BaseAgent):
    """
    Analyses and manages the job application pipeline.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            user_id: str = state.get("user_id", "unknown")
            matched_jobs: list[dict] = state.get("matched_jobs") or []

            # Build a synthetic application pipeline from matched jobs
            # In production this would be loaded from DB
            applications = self._build_applications_from_state(state, matched_jobs)

            if not applications:
                logger.info("[ApplicationTrackerAgent] No applications to track yet")
                state = self._update_confidence(state, 0.5)
                return state

            # Rule-based: find applications needing follow-up
            follow_ups = self._compute_follow_ups(applications)

            # Rule-based: basic metrics
            basic_metrics = self._compute_metrics(applications)

            # GPT-4 deep analysis
            analysis = await self._call_gpt_analysis(
                applications=applications,
                follow_ups=follow_ups,
                metrics=basic_metrics,
                state=state,
            )

            # Persist snapshot to DB
            await self._persist_snapshot(user_id, applications, analysis, state)

            # Write back to state messages for downstream consumers
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"ApplicationTrackerAgent: tracking {len(applications)} applications, "
                    f"{len(follow_ups)} need follow-up, "
                    f"health_score={analysis.get('pipeline_health', {}).get('health_score', 'N/A')}"
                ),
                metadata={"analysis": analysis},
            )

            confidence = 0.85 if analysis else 0.5
            state = self._update_confidence(state, confidence)
            logger.info(
                "[ApplicationTrackerAgent] %d applications tracked, %d follow-ups",
                len(applications), len(follow_ups),
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _build_applications_from_state(
        self, state: AgentState, matched_jobs: list[dict]
    ) -> list[dict]:
        """
        Build a list of application records from matched jobs in state.
        In production these would be loaded from the database.
        """
        now = datetime.now(timezone.utc)
        applications: list[dict] = []
        for i, job in enumerate(matched_jobs[:20]):
            # Assign realistic-looking statuses for simulation
            # In production: load real status from DB
            if i == 0:
                status = "interview"
                days_ago = 3
            elif i < 3:
                status = "phone_screen"
                days_ago = 7
            elif i < 8:
                status = "applied"
                days_ago = 5
            else:
                status = "saved"
                days_ago = 1

            applications.append({
                "job_id": job.get("external_id", f"job_{i}"),
                "job_title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "match_score": job.get("match_score", 0),
                "status": status,
                "applied_at": (now - timedelta(days=days_ago + 2)).isoformat() if status != "saved" else None,
                "last_updated": (now - timedelta(days=days_ago)).isoformat(),
                "url": job.get("url", ""),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
            })
        return applications

    def _compute_follow_ups(self, applications: list[dict]) -> list[dict]:
        """Identify applications that need a follow-up message."""
        now = datetime.now(timezone.utc)
        follow_ups: list[dict] = []
        for app in applications:
            status = app.get("status", "")
            if status in _TERMINAL_STATUSES or status == "saved":
                continue
            threshold_days = _FOLLOW_UP_DAYS.get(status, 7)
            last_updated_str = app.get("last_updated")
            if not last_updated_str:
                continue
            try:
                last_updated = datetime.fromisoformat(last_updated_str)
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                days_since = (now - last_updated).days
                if days_since >= threshold_days:
                    follow_ups.append({
                        **app,
                        "days_since_update": days_since,
                        "follow_up_due": True,
                    })
            except Exception:
                pass
        return follow_ups

    def _compute_metrics(self, applications: list[dict]) -> dict:
        """Compute basic pipeline metrics."""
        total = len(applications)
        if total == 0:
            return {}

        status_counts: dict[str, int] = {}
        for app in applications:
            s = app.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        responded = sum(
            status_counts.get(s, 0)
            for s in ("screening", "phone_screen", "technical", "interview", "offer", "negotiation", "accepted")
        )
        interviews = sum(
            status_counts.get(s, 0)
            for s in ("technical", "interview", "offer", "negotiation", "accepted")
        )
        offers = sum(
            status_counts.get(s, 0)
            for s in ("offer", "negotiation", "accepted")
        )
        applied = total - status_counts.get("saved", 0)

        return {
            "total": total,
            "applied": applied,
            "status_counts": status_counts,
            "response_rate_pct": round(responded / max(applied, 1) * 100, 1),
            "interview_conversion_pct": round(interviews / max(applied, 1) * 100, 1),
            "offer_rate_pct": round(offers / max(applied, 1) * 100, 1),
        }

    async def _call_gpt_analysis(
        self,
        applications: list[dict],
        follow_ups: list[dict],
        metrics: dict,
        state: AgentState,
    ) -> dict:
        """Use GPT-4 to generate deep pipeline analysis and recommendations."""
        intel = state.get("resume_intelligence") or {}
        apps_summary = "\n".join(
            f"- {a.get('job_title')} @ {a.get('company')} | status={a.get('status')} | match={a.get('match_score', 0):.0%}"
            for a in applications[:15]
        )
        follow_up_summary = "\n".join(
            f"- {f.get('job_title')} @ {f.get('company')} | {f.get('days_since_update')} days since update"
            for f in follow_ups[:10]
        )

        system_prompt = (
            "You are a job search strategist. Analyse the candidate's application pipeline "
            "and provide specific, actionable recommendations. Be direct and tactical."
        )
        user_prompt = (
            f"## Candidate\nSeniority: {intel.get('seniority_level', 'Unknown')}\n\n"
            f"## Pipeline Metrics\n"
            f"Total: {metrics.get('total', 0)} | Applied: {metrics.get('applied', 0)} | "
            f"Response rate: {metrics.get('response_rate_pct', 0)}%\n\n"
            f"## Applications\n{apps_summary}\n\n"
            f"## Needs Follow-up ({len(follow_ups)})\n{follow_up_summary or 'None'}\n\n"
            "Analyse the pipeline and provide recommendations."
        )

        result = await self._call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_TRACKER_ANALYSIS_TOOL],
            tool_choice={"type": "function", "function": {"name": "analyze_application_pipeline"}},
            temperature=0.2,
            max_tokens=2000,
        )

        analysis = result.get("tool_call_args") or {}

        # Inject rule-based follow-ups if LLM missed them
        if follow_ups and not analysis.get("applications_needing_followup"):
            analysis["applications_needing_followup"] = [
                {
                    "job_id": f.get("job_id", ""),
                    "job_title": f.get("job_title", ""),
                    "company": f.get("company", ""),
                    "status": f.get("status", ""),
                    "days_since_update": f.get("days_since_update", 0),
                    "recommended_action": f"Send follow-up for {f.get('status')} stage",
                    "message_template": (
                        f"Hi [Name], I wanted to follow up on my application for the "
                        f"{f.get('job_title')} position at {f.get('company')}. "
                        "I remain very interested and would love to discuss next steps. "
                        "Please let me know if you need any additional information."
                    ),
                }
                for f in follow_ups[:5]
            ]

        return analysis

    async def _persist_snapshot(
        self,
        user_id: str,
        applications: list[dict],
        analysis: dict,
        state: AgentState,
    ) -> None:
        """Persist a pipeline snapshot to the database."""
        import json
        import uuid

        snapshot_id = str(uuid.uuid4())
        await save_to_database.ainvoke({
            "table": "application_snapshots",
            "data": {
                "id": snapshot_id,
                "user_id": user_id,
                "session_id": state.get("session_id", ""),
                "application_count": len(applications),
                "analysis": json.dumps(analysis),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        })
