"""
ATSOptimizationAgent

Analyses a resume against a target job description and:
  - Computes keyword match score, bigram score, formatting score
  - Identifies missing critical keywords
  - Flags ATS-hostile formatting issues
  - Quantification / action verb analysis
  - Generates optimised resume version (JSON + guidance)
  - Returns ats_score (0–100), ats_suggestions, ats_optimized_resume
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState
from app.agents.tools import calculate_ats_score

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# ATS formatting red flags
# --------------------------------------------------------------------------- #

_FORMATTING_CHECKS = [
    {
        "id": "tables",
        "pattern": r"\|.*\|",
        "message": "Tables detected — most ATS systems cannot parse table content correctly.",
        "severity": "high",
        "deduction": 10,
    },
    {
        "id": "no_bullet_action_verbs",
        "pattern": None,   # checked via word list
        "message": "Bullet points lack strong action verbs (Led, Built, Delivered, Optimised, etc.)",
        "severity": "medium",
        "deduction": 5,
    },
    {
        "id": "generic_objective",
        "pattern": r"to obtain a position|seeking a challenging role|looking for an opportunity",
        "message": "Generic objective statement detected — replace with a targeted summary.",
        "severity": "low",
        "deduction": 5,
    },
    {
        "id": "no_quantification",
        "pattern": None,  # checked programmatically
        "message": "Few or no quantified achievements — add numbers, %, $, timelines.",
        "severity": "medium",
        "deduction": 8,
    },
]

_STRONG_ACTION_VERBS = {
    "led", "built", "delivered", "optimised", "optimized", "achieved", "reduced", "increased",
    "launched", "designed", "architected", "implemented", "developed", "managed", "deployed",
    "automated", "improved", "created", "transformed", "scaled", "drove", "executed", "spearheaded",
}

# --------------------------------------------------------------------------- #
# Function-calling schemas
# --------------------------------------------------------------------------- #

_OPTIMIZE_TOOL = {
    "type": "function",
    "function": {
        "name": "optimize_resume_for_ats",
        "description": (
            "Generate an ATS-optimised resume version tailored to a specific job description. "
            "Integrate missing keywords naturally — never keyword-stuff. "
            "Rewrite weak bullets for impact. Provide a tailored summary. "
            "Base every change on actual resume content — do NOT hallucinate experience."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tailored_summary": {
                    "type": "string",
                    "description": "Rewritten professional summary targeting this specific job.",
                },
                "keyword_insertions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"},
                            "suggested_placement": {"type": "string"},
                            "example_sentence": {"type": "string"},
                        },
                        "required": ["keyword", "suggested_placement"],
                    },
                },
                "rewritten_bullets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original": {"type": "string"},
                            "rewritten": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["original", "rewritten"],
                    },
                },
                "format_recommendations": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "section_order_recommendation": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Recommended section order for this job type.",
                },
                "skills_to_add": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Legitimate skills to add based on job requirements and candidate background.",
                },
            },
            "required": ["tailored_summary", "keyword_insertions", "rewritten_bullets", "format_recommendations"],
        },
    },
}


class ATSOptimizationAgent(BaseAgent):
    """
    Full ATS analysis and optimisation against a target job description.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            raw_text: Optional[str] = state.get("resume_raw_text")
            target_job: Optional[dict] = state.get("target_job")

            if not raw_text:
                return self._log_error(state, "No resume_raw_text in state")
            if not target_job:
                # Try first matched job
                matched = state.get("matched_jobs") or []
                if matched:
                    target_job = matched[0]
                    state["target_job"] = target_job

            job_description = self._build_jd_text(target_job) if target_job else ""

            # ---------------------------------------------------------------- #
            # 1. Rule-based ATS scoring
            # ---------------------------------------------------------------- #
            rule_result = calculate_ats_score.invoke(
                {"resume_text": raw_text, "job_description": job_description}
            )

            format_issues = self._check_formatting(raw_text)
            format_deduction = sum(issue["deduction"] for issue in format_issues)

            base_score = rule_result.get("overall_score", 50)
            adjusted_score = max(0.0, base_score - format_deduction)

            # ---------------------------------------------------------------- #
            # 2. GPT-4 optimisation
            # ---------------------------------------------------------------- #
            parsed = state.get("parsed_resume") or {}
            optimized_dict: dict = {}

            if target_job and job_description:
                optimized_dict = await self._call_optimizer(
                    raw_text=raw_text,
                    job_description=job_description,
                    parsed=parsed,
                    missing_keywords=rule_result.get("missing_keywords", [])[:20],
                )

            # ---------------------------------------------------------------- #
            # 3. Build suggestions list
            # ---------------------------------------------------------------- #
            suggestions: list[str] = []
            for issue in format_issues:
                suggestions.append(f"[{issue['severity'].upper()}] {issue['message']}")
            for kw in rule_result.get("missing_keywords", [])[:15]:
                suggestions.append(f"Add keyword: '{kw}' — present in job description but not in resume")
            for rec in (optimized_dict.get("format_recommendations") or []):
                if rec not in suggestions:
                    suggestions.append(rec)

            # ---------------------------------------------------------------- #
            # 4. Write to state
            # ---------------------------------------------------------------- #
            state["ats_score"] = round(adjusted_score, 1)
            state["ats_suggestions"] = suggestions[:30]
            state["ats_optimized_resume"] = {
                "score_breakdown": {
                    "keyword_score": rule_result.get("keyword_score"),
                    "bigram_score": rule_result.get("bigram_score"),
                    "formatting_score": rule_result.get("formatting_score"),
                    "format_deduction": format_deduction,
                    "final_score": round(adjusted_score, 1),
                },
                "matched_keywords": rule_result.get("matched_keywords", []),
                "missing_keywords": rule_result.get("missing_keywords", [])[:30],
                "format_issues": [
                    {"message": i["message"], "severity": i["severity"]}
                    for i in format_issues
                ],
                "optimization": optimized_dict,
            }

            confidence = self._compute_confidence(adjusted_score, optimized_dict)
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"ATSOptimizationAgent: ats_score={adjusted_score:.1f}, "
                    f"{len(suggestions)} suggestions, confidence={confidence:.2f}"
                ),
            )
            logger.info(
                "[ATSOptimizationAgent] ats_score=%.1f, %d suggestions",
                adjusted_score, len(suggestions),
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _build_jd_text(self, job: Optional[dict]) -> str:
        if not job:
            return ""
        return (
            f"{job.get('title', '')} {job.get('company_name', '')} "
            f"{job.get('description', '')} "
            f"{' '.join(job.get('requirements', []))}"
        )[:8000]

    def _check_formatting(self, resume_text: str) -> list[dict]:
        issues: list[dict] = []
        text_lower = resume_text.lower()
        lines = resume_text.split("\n")

        for check in _FORMATTING_CHECKS:
            if check["id"] == "no_bullet_action_verbs":
                bullet_lines = [l.lstrip("•-*·").strip().lower() for l in lines if l.strip().startswith(("•", "-", "*", "·"))]
                action_verb_count = sum(
                    1 for bl in bullet_lines
                    if bl.split()[0] in _STRONG_ACTION_VERBS if bl.split()
                )
                if bullet_lines and action_verb_count / max(len(bullet_lines), 1) < 0.3:
                    issues.append(check)
            elif check["id"] == "no_quantification":
                has_numbers = bool(re.search(r"\d+%|\$\d+|\d+x|\d+ team|\d+ engineers|saved \$|\d+ million", text_lower))
                if not has_numbers:
                    issues.append(check)
            elif check.get("pattern"):
                if re.search(check["pattern"], resume_text, re.IGNORECASE):
                    issues.append(check)

        return issues

    async def _call_optimizer(
        self,
        raw_text: str,
        job_description: str,
        parsed: dict,
        missing_keywords: list[str],
    ) -> dict:
        system_prompt = (
            "You are an expert ATS resume optimisation specialist. "
            "Improve the candidate's resume for a specific job. "
            "Natural keyword integration only — no stuffing. "
            "Never add experience or skills the candidate doesn't have."
        )
        user_prompt = (
            f"## Current Resume Text (first 4000 chars)\n{raw_text[:4000]}\n\n"
            f"## Target Job Description\n{job_description[:3000]}\n\n"
            f"## Missing Keywords to Integrate (if legitimate)\n{', '.join(missing_keywords)}\n\n"
            "Generate the ATS-optimised version."
        )

        result = await self._call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_OPTIMIZE_TOOL],
            tool_choice={"type": "function", "function": {"name": "optimize_resume_for_ats"}},
            temperature=0.2,
            max_tokens=2500,
        )

        return result.get("tool_call_args") or {}

    def _compute_confidence(self, ats_score: float, optimized: dict) -> float:
        score_conf = min(ats_score / 100, 1.0) * 0.5
        opt_conf = 0.4 if optimized.get("keyword_insertions") else 0.0
        tip_conf = 0.1 if optimized.get("rewritten_bullets") else 0.0
        return round(score_conf + opt_conf + tip_conf, 4)
