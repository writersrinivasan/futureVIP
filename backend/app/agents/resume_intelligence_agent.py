"""
ResumeIntelligenceAgent

Deep analysis of a parsed resume using GPT-4 function calling.
Produces a structured intelligence report covering:
  - Career trajectory, seniority, years of experience
  - Strongest skills and competencies
  - Industry domains, leadership indicators, impact metrics
  - Red flags (gaps, short tenures)
  - Unique value proposition
  - Target role recommendations and salary estimates
  - Overall resume quality score (0-100)
"""

from __future__ import annotations

import logging

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Function-calling schema
# --------------------------------------------------------------------------- #

_INTELLIGENCE_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_resume_intelligence",
        "description": (
            "Perform deep career intelligence analysis on a parsed resume. "
            "Base ALL findings strictly on the parsed data — do not fabricate."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "career_trajectory": {
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["upward", "lateral", "pivot", "unclear"],
                        },
                        "narrative": {"type": "string"},
                    },
                    "required": ["direction", "narrative"],
                },
                "total_years_experience": {"type": "number"},
                "seniority_level": {
                    "type": "string",
                    "enum": ["Intern", "Junior", "Mid", "Senior", "Lead", "Principal", "Executive"],
                },
                "strongest_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 10,
                },
                "core_competencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8,
                },
                "industry_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "leadership_indicators": {
                    "type": "array",
                    "description": "Evidence of leadership (team size, mentoring, project ownership, etc.)",
                    "items": {"type": "string"},
                },
                "impact_metrics": {
                    "type": "array",
                    "description": "Quantified achievements found in the resume",
                    "items": {"type": "string"},
                },
                "red_flags": {
                    "type": "array",
                    "description": "Potential concerns: employment gaps > 6 months, tenures < 9 months, etc.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        },
                    },
                },
                "unique_value_proposition": {
                    "type": "string",
                    "description": "One-paragraph summary of what makes this candidate distinctive.",
                },
                "target_role_recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "fit_score": {"type": "number", "minimum": 0, "maximum": 100},
                            "rationale": {"type": "string"},
                        },
                    },
                    "maxItems": 5,
                },
                "salary_range_estimate": {
                    "type": "object",
                    "properties": {
                        "currency": {"type": "string"},
                        "min": {"type": "number"},
                        "max": {"type": "number"},
                        "basis": {"type": "string", "description": "Basis for estimate"},
                    },
                },
                "resume_quality_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Overall resume quality: structure, clarity, impact, completeness.",
                },
                "resume_quality_breakdown": {
                    "type": "object",
                    "properties": {
                        "structure": {"type": "number"},
                        "clarity": {"type": "number"},
                        "impact": {"type": "number"},
                        "completeness": {"type": "number"},
                        "keyword_richness": {"type": "number"},
                    },
                },
                "improvement_priorities": {
                    "type": "array",
                    "description": "Top 3-5 things the candidate should do to improve their resume.",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "career_trajectory",
                "total_years_experience",
                "seniority_level",
                "strongest_skills",
                "industry_domains",
                "unique_value_proposition",
                "target_role_recommendations",
                "resume_quality_score",
            ],
        },
    },
}


class ResumeIntelligenceAgent(BaseAgent):
    """
    Produces a structured intelligence report from a parsed resume.
    Strictly grounded — no hallucination.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            parsed = state.get("parsed_resume")
            raw_text = state.get("resume_raw_text", "")

            if not parsed:
                return self._log_error(state, "parsed_resume not available — run ResumeParsingAgent first")

            # Build a concise context for the LLM
            context = self._build_context(parsed, raw_text)

            system_prompt = (
                "You are a senior career intelligence analyst specialising in tech talent. "
                "Analyse the candidate profile provided and produce a precise, evidence-based "
                "intelligence report. Ground every finding in the resume data. "
                "Do NOT invent information. Flag uncertainties explicitly."
            )
            user_prompt = (
                "Analyse the following candidate profile and produce the intelligence report:\n\n"
                f"{context}"
            )

            result = await self._call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[_INTELLIGENCE_TOOL],
                tool_choice={
                    "type": "function",
                    "function": {"name": "analyze_resume_intelligence"},
                },
                temperature=0.1,
                max_tokens=2048,
            )

            intelligence = result.get("tool_call_args") or {}

            if not intelligence:
                state = self._log_error(state, "LLM returned empty intelligence report")
                state = self._update_confidence(state, 0.1)
                return state

            state["resume_intelligence"] = intelligence

            confidence = self._compute_confidence(intelligence)
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"ResumeIntelligenceAgent: seniority={intelligence.get('seniority_level')}, "
                    f"quality_score={intelligence.get('resume_quality_score')}, "
                    f"confidence={confidence:.2f}"
                ),
            )
            logger.info(
                "[ResumeIntelligenceAgent] seniority=%s quality=%s confidence=%.2f",
                intelligence.get("seniority_level"),
                intelligence.get("resume_quality_score"),
                confidence,
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _build_context(self, parsed: dict, raw_text: str) -> str:
        """Build a compact LLM-readable summary of the parsed resume."""
        import json

        # Include the full parsed structure (truncated if huge)
        parsed_str = json.dumps(parsed, indent=2)[:8000]
        raw_sample = raw_text[:2000] if raw_text else ""

        return (
            "## Parsed Resume (JSON)\n"
            f"```json\n{parsed_str}\n```\n\n"
            "## Raw Text Sample (first 2000 chars)\n"
            f"{raw_sample}"
        )

    def _compute_confidence(self, intel: dict) -> float:
        """Score completeness of the intelligence report."""
        score = 0.0
        required_present = [
            "career_trajectory", "total_years_experience", "seniority_level",
            "strongest_skills", "unique_value_proposition",
            "target_role_recommendations", "resume_quality_score",
        ]
        for field in required_present:
            if intel.get(field):
                score += 1 / len(required_present)

        # Bonus for rich optional fields
        if intel.get("impact_metrics"):
            score += 0.05
        if intel.get("red_flags") is not None:
            score += 0.05
        if intel.get("salary_range_estimate"):
            score += 0.05

        return round(min(score, 1.0), 4)
