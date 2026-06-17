"""
CareerAdvisorAgent

Generates a personalised career roadmap and insights:
  - Current position assessment
  - Target role analysis
  - 30/60/90-day action plan
  - Skills to develop (with resources: courses, certifications)
  - Networking strategies
  - Milestones and KPIs
  - Timeline estimation
  - Industry trends relevant to the career
  - Job search strategy
  - Personal branding recommendations
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Function-calling schemas
# --------------------------------------------------------------------------- #

_ROADMAP_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_career_roadmap",
        "description": (
            "Generate a personalised, evidence-based career development roadmap. "
            "Ground all advice in the candidate's actual background. "
            "Be specific and actionable."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "current_assessment": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string"},
                        "primary_strengths": {"type": "array", "items": {"type": "string"}},
                        "primary_gaps": {"type": "array", "items": {"type": "string"}},
                        "market_positioning": {"type": "string"},
                        "estimated_current_market_value_usd": {
                            "type": "object",
                            "properties": {
                                "min": {"type": "number"},
                                "max": {"type": "number"},
                            },
                        },
                    },
                    "required": ["level", "primary_strengths", "primary_gaps"],
                },
                "target_roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "readiness_pct": {"type": "number"},
                            "estimated_months_to_ready": {"type": "integer"},
                        },
                        "required": ["role", "readiness_pct"],
                    },
                },
                "action_plan": {
                    "type": "object",
                    "properties": {
                        "day_30": {
                            "type": "object",
                            "properties": {
                                "theme": {"type": "string"},
                                "actions": {"type": "array", "items": {"type": "string"}},
                                "success_metric": {"type": "string"},
                            },
                            "required": ["theme", "actions"],
                        },
                        "day_60": {
                            "type": "object",
                            "properties": {
                                "theme": {"type": "string"},
                                "actions": {"type": "array", "items": {"type": "string"}},
                                "success_metric": {"type": "string"},
                            },
                            "required": ["theme", "actions"],
                        },
                        "day_90": {
                            "type": "object",
                            "properties": {
                                "theme": {"type": "string"},
                                "actions": {"type": "array", "items": {"type": "string"}},
                                "success_metric": {"type": "string"},
                            },
                            "required": ["theme", "actions"],
                        },
                    },
                    "required": ["day_30", "day_60", "day_90"],
                },
                "skills_to_develop": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "skill": {"type": "string"},
                            "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                            "estimated_weeks": {"type": "integer"},
                            "resources": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string", "enum": ["course", "certification", "book", "project", "community"]},
                                        "url": {"type": "string"},
                                        "cost": {"type": "string"},
                                    },
                                    "required": ["name", "type"],
                                },
                            },
                        },
                        "required": ["skill", "priority"],
                    },
                },
                "networking_strategy": {
                    "type": "object",
                    "properties": {
                        "target_communities": {"type": "array", "items": {"type": "string"}},
                        "events_to_attend": {"type": "array", "items": {"type": "string"}},
                        "outreach_targets": {"type": "array", "items": {"type": "string"}},
                        "content_creation_suggestions": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "milestones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "month": {"type": "integer"},
                            "milestone": {"type": "string"},
                            "kpi": {"type": "string"},
                        },
                        "required": ["month", "milestone"],
                    },
                },
                "estimated_total_months": {"type": "integer"},
                "job_search_strategy": {
                    "type": "object",
                    "properties": {
                        "ideal_company_size": {"type": "string"},
                        "target_industries": {"type": "array", "items": {"type": "string"}},
                        "application_volume_per_week": {"type": "integer"},
                        "channels": {"type": "array", "items": {"type": "string"}},
                        "expected_timeline_weeks": {"type": "integer"},
                    },
                },
                "personal_branding": {
                    "type": "object",
                    "properties": {
                        "linkedin_optimisations": {"type": "array", "items": {"type": "string"}},
                        "github_improvements": {"type": "array", "items": {"type": "string"}},
                        "portfolio_suggestions": {"type": "array", "items": {"type": "string"}},
                        "thought_leadership_topics": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "industry_trends": {
                    "type": "array",
                    "description": "Relevant industry and market trends the candidate should be aware of.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "trend": {"type": "string"},
                            "relevance": {"type": "string"},
                            "action": {"type": "string"},
                        },
                        "required": ["trend", "relevance"],
                    },
                },
            },
            "required": [
                "current_assessment", "target_roles", "action_plan",
                "skills_to_develop", "milestones", "estimated_total_months",
            ],
        },
    },
}


class CareerAdvisorAgent(BaseAgent):
    """
    Generates a comprehensive, personalised career roadmap and market insights.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            intelligence = state.get("resume_intelligence")
            parsed = state.get("parsed_resume")
            skill_gaps = state.get("skill_gaps") or []

            if not intelligence and not parsed:
                return self._log_error(
                    state,
                    "Neither resume_intelligence nor parsed_resume available — run earlier agents first",
                )

            context = self._build_context(intelligence, parsed, skill_gaps, state)

            system_prompt = (
                "You are a senior career strategist with 20+ years of experience placing "
                "tech professionals at top companies. Generate a highly personalised, "
                "actionable career roadmap. Ground ALL advice in the candidate's actual "
                "background. Do NOT give generic advice."
            )
            user_prompt = (
                "Generate a comprehensive career roadmap and strategy for the following candidate:\n\n"
                f"{context}"
            )

            result = await self._call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[_ROADMAP_TOOL],
                tool_choice={"type": "function", "function": {"name": "generate_career_roadmap"}},
                temperature=0.3,
                max_tokens=3000,
            )

            roadmap = result.get("tool_call_args") or {}

            if not roadmap:
                state = self._log_error(state, "LLM returned empty career roadmap")
                state = self._update_confidence(state, 0.1)
                return state

            state["career_roadmap"] = roadmap

            # Extract career insights as a flat list for quick consumption
            insights: list[str] = []
            for trend in roadmap.get("industry_trends", []):
                insights.append(f"Trend: {trend.get('trend')} — {trend.get('relevance')}")
            for skill in roadmap.get("skills_to_develop", [])[:5]:
                insights.append(
                    f"Develop: {skill.get('skill')} [{skill.get('priority')} priority]"
                )
            if roadmap.get("job_search_strategy"):
                jss = roadmap["job_search_strategy"]
                insights.append(
                    f"Job search: ~{jss.get('application_volume_per_week')} apps/week "
                    f"via {', '.join(jss.get('channels', [])[:3])}"
                )

            state["career_insights"] = insights[:20]

            confidence = self._compute_confidence(roadmap)
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"CareerAdvisorAgent: {len(roadmap.get('milestones', []))} milestones, "
                    f"{len(roadmap.get('skills_to_develop', []))} skills, "
                    f"confidence={confidence:.2f}"
                ),
            )
            logger.info(
                "[CareerAdvisorAgent] roadmap generated, confidence=%.2f", confidence
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _build_context(
        self,
        intelligence: Optional[dict],
        parsed: Optional[dict],
        skill_gaps: list,
        state: AgentState,
    ) -> str:
        sections: list[str] = []
        if intelligence:
            sections.append(
                "## Career Intelligence\n"
                f"Seniority: {intelligence.get('seniority_level')}\n"
                f"Years Experience: {intelligence.get('total_years_experience')}\n"
                f"Domains: {', '.join(intelligence.get('industry_domains', []))}\n"
                f"Strongest Skills: {', '.join(intelligence.get('strongest_skills', []))}\n"
                f"Value Prop: {intelligence.get('unique_value_proposition', '')}\n"
                f"Target Roles: {', '.join(r.get('role', '') for r in intelligence.get('target_role_recommendations', []))}\n"
                f"Quality Score: {intelligence.get('resume_quality_score')}/100"
            )
        if parsed:
            pinfo = parsed.get("personal_info", {})
            sections.append(
                "## Personal Info\n"
                f"Location: {pinfo.get('location', 'Not specified')}\n"
                f"Total Experiences: {len(parsed.get('experience', []))}\n"
                f"Education: {len(parsed.get('education', []))} entries\n"
                f"Skills Listed: {len(parsed.get('skills', []))}"
            )
        if skill_gaps:
            gap_summary = ", ".join(
                f"{g.get('missing_skill')} ({g.get('importance')})"
                for g in skill_gaps[:10]
            )
            sections.append(f"## Skill Gaps\n{gap_summary}")

        matched = state.get("matched_jobs") or []
        if matched:
            top_job = matched[0]
            sections.append(
                f"## Top Job Match\n"
                f"{top_job.get('title')} at {top_job.get('company_name')} "
                f"(match_score={top_job.get('match_score', 0):.0%})"
            )

        return "\n\n".join(sections)

    def _compute_confidence(self, roadmap: dict) -> float:
        checks = [
            bool(roadmap.get("current_assessment")),
            bool(roadmap.get("target_roles")),
            bool(roadmap.get("action_plan")),
            bool(roadmap.get("skills_to_develop")),
            bool(roadmap.get("milestones")),
            bool(roadmap.get("job_search_strategy")),
        ]
        return round(sum(checks) / len(checks), 4)
