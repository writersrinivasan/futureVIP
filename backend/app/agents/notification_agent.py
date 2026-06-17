"""
NotificationAgent

Triggers and stores notifications based on workflow events:
  - New high-match jobs (match_score > 0.80)
  - Resume analysis complete
  - ATS score improved / computed
  - Application status changed
  - Career milestone achieved
  - Weekly opportunity digest

Formats message, stores in DB, and returns notification metadata.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState
from app.agents.tools import send_notification

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Notification templates
# --------------------------------------------------------------------------- #

_TEMPLATES: dict[str, dict] = {
    "resume_analyzed": {
        "title": "Resume Analysis Complete",
        "message_tpl": (
            "Your resume has been analysed. Quality score: {quality_score}/100. "
            "Seniority level detected: {seniority_level}."
        ),
    },
    "job_match": {
        "title": "High-Match Jobs Found",
        "message_tpl": (
            "We found {count} job(s) with ≥80% match score for your profile! "
            "Top match: {top_job_title} at {top_company} ({top_score:.0%} match)."
        ),
    },
    "ats_optimized": {
        "title": "ATS Score Computed",
        "message_tpl": (
            "Your ATS compatibility score for {job_title} is {ats_score}/100. "
            "{suggestions_count} improvement suggestions generated."
        ),
    },
    "career_roadmap": {
        "title": "Career Roadmap Generated",
        "message_tpl": (
            "Your personalised career roadmap is ready. "
            "{milestone_count} milestones across {total_months} months. "
            "Top focus: {top_skill}."
        ),
    },
    "interview_ready": {
        "title": "Interview Prep Ready",
        "message_tpl": (
            "{question_count} interview questions generated for {job_title}. "
            "Start practising to boost your chances!"
        ),
    },
    "interview_feedback": {
        "title": "Interview Answer Feedback",
        "message_tpl": (
            "Your answer scored {score}/10. "
            "Strength: {top_strength}. "
            "Improve: {top_improvement}."
        ),
    },
    "weekly_digest": {
        "title": "Weekly Opportunity Digest",
        "message_tpl": (
            "This week: {new_jobs_count} new job matches discovered. "
            "Best match: {best_match_title} ({best_match_score:.0%}). "
            "Keep applying!"
        ),
    },
}


class NotificationAgent(BaseAgent):
    """
    Analyses workflow state and fires appropriate notifications.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            user_id: str = state.get("user_id", "unknown")
            task_type: str = state.get("task_type", "")
            notifications_sent: list[dict] = []

            # ---------------------------------------------------------------- #
            # Decide which notifications to send based on state content
            # ---------------------------------------------------------------- #

            # Resume analysis complete
            if state.get("resume_intelligence"):
                notif = await self._send_resume_analyzed(user_id, state)
                if notif:
                    notifications_sent.append(notif)

            # High-match jobs
            if state.get("matched_jobs"):
                notif = await self._send_job_matches(user_id, state)
                if notif:
                    notifications_sent.append(notif)

            # ATS score
            if state.get("ats_score") is not None:
                notif = await self._send_ats_score(user_id, state)
                if notif:
                    notifications_sent.append(notif)

            # Career roadmap
            if state.get("career_roadmap"):
                notif = await self._send_career_roadmap(user_id, state)
                if notif:
                    notifications_sent.append(notif)

            # Interview questions generated
            if state.get("interview_questions") and not state.get("interview_feedback"):
                notif = await self._send_interview_ready(user_id, state)
                if notif:
                    notifications_sent.append(notif)

            # Interview feedback
            if state.get("interview_feedback"):
                notif = await self._send_interview_feedback(user_id, state)
                if notif:
                    notifications_sent.append(notif)

            confidence = 0.9 if notifications_sent else 0.5
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=f"NotificationAgent: {len(notifications_sent)} notifications sent",
            )
            logger.info(
                "[NotificationAgent] Sent %d notifications for user %s",
                len(notifications_sent), user_id,
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Notification builders
    # ---------------------------------------------------------------------- #

    async def _send_resume_analyzed(self, user_id: str, state: AgentState) -> Optional[dict]:
        intel = state.get("resume_intelligence") or {}
        quality = intel.get("resume_quality_score", "N/A")
        seniority = intel.get("seniority_level", "Unknown")
        tmpl = _TEMPLATES["resume_analyzed"]
        message = tmpl["message_tpl"].format(
            quality_score=quality, seniority_level=seniority
        )
        return await send_notification.ainvoke({
            "user_id": user_id,
            "notification_type": "resume_analyzed",
            "title": tmpl["title"],
            "message": message,
            "metadata": {
                "quality_score": quality,
                "seniority_level": seniority,
                "session_id": state.get("session_id"),
            },
        })

    async def _send_job_matches(self, user_id: str, state: AgentState) -> Optional[dict]:
        matched = state.get("matched_jobs") or []
        high_match = [j for j in matched if j.get("match_score", 0) >= 0.80]
        if not high_match:
            return None
        top = high_match[0]
        tmpl = _TEMPLATES["job_match"]
        message = tmpl["message_tpl"].format(
            count=len(high_match),
            top_job_title=top.get("title", ""),
            top_company=top.get("company_name", ""),
            top_score=top.get("match_score", 0),
        )
        return await send_notification.ainvoke({
            "user_id": user_id,
            "notification_type": "job_match",
            "title": tmpl["title"],
            "message": message,
            "metadata": {
                "high_match_count": len(high_match),
                "top_job_id": top.get("external_id"),
                "session_id": state.get("session_id"),
            },
        })

    async def _send_ats_score(self, user_id: str, state: AgentState) -> Optional[dict]:
        ats_score = state.get("ats_score", 0)
        suggestions = state.get("ats_suggestions") or []
        target_job = state.get("target_job") or {}
        tmpl = _TEMPLATES["ats_optimized"]
        message = tmpl["message_tpl"].format(
            job_title=target_job.get("title", "target role"),
            ats_score=ats_score,
            suggestions_count=len(suggestions),
        )
        return await send_notification.ainvoke({
            "user_id": user_id,
            "notification_type": "ats_improved",
            "title": tmpl["title"],
            "message": message,
            "metadata": {
                "ats_score": ats_score,
                "job_id": target_job.get("external_id"),
                "session_id": state.get("session_id"),
            },
        })

    async def _send_career_roadmap(self, user_id: str, state: AgentState) -> Optional[dict]:
        roadmap = state.get("career_roadmap") or {}
        milestones = roadmap.get("milestones", [])
        total_months = roadmap.get("estimated_total_months", "?")
        skills = roadmap.get("skills_to_develop", [])
        top_skill = skills[0].get("skill", "") if skills else "N/A"
        tmpl = _TEMPLATES["career_roadmap"]
        message = tmpl["message_tpl"].format(
            milestone_count=len(milestones),
            total_months=total_months,
            top_skill=top_skill,
        )
        return await send_notification.ainvoke({
            "user_id": user_id,
            "notification_type": "career_milestone",
            "title": tmpl["title"],
            "message": message,
            "metadata": {
                "total_months": total_months,
                "session_id": state.get("session_id"),
            },
        })

    async def _send_interview_ready(self, user_id: str, state: AgentState) -> Optional[dict]:
        questions = state.get("interview_questions") or []
        real_questions = [q for q in questions if q.get("question")]
        target_job = state.get("target_job") or {}
        tmpl = _TEMPLATES["interview_ready"]
        message = tmpl["message_tpl"].format(
            question_count=len(real_questions),
            job_title=target_job.get("title", "your target role"),
        )
        return await send_notification.ainvoke({
            "user_id": user_id,
            "notification_type": "application_status",
            "title": tmpl["title"],
            "message": message,
            "metadata": {
                "question_count": len(real_questions),
                "session_id": state.get("session_id"),
            },
        })

    async def _send_interview_feedback(self, user_id: str, state: AgentState) -> Optional[dict]:
        feedback = state.get("interview_feedback") or {}
        score = feedback.get("overall_score", "?")
        strengths = feedback.get("strengths", [])
        improvements = feedback.get("improvements", [])
        top_strength = strengths[0] if strengths else "Good effort"
        top_improvement = (
            improvements[0].get("issue", "Review answer structure")
            if improvements
            else "Review answer structure"
        )
        tmpl = _TEMPLATES["interview_feedback"]
        message = tmpl["message_tpl"].format(
            score=score,
            top_strength=top_strength,
            top_improvement=top_improvement,
        )
        return await send_notification.ainvoke({
            "user_id": user_id,
            "notification_type": "application_status",
            "title": tmpl["title"],
            "message": message,
            "metadata": {
                "score": score,
                "session_id": state.get("session_id"),
            },
        })
