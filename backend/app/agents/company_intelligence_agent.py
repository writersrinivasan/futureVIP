"""
CompanyIntelligenceAgent

For a target job's company, gathers:
  - Company size, industry, founded year
  - Culture signals (from job description language)
  - Growth indicators
  - Tech stack (from job requirements)
  - Remote/hybrid/onsite policy
  - Estimated salary ranges
  - Red flags (high-turnover signals, vague descriptions)
  - Interview process hints
  - Overall fit score for the candidate
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Culture signal lexicons
# --------------------------------------------------------------------------- #

_POSITIVE_CULTURE_SIGNALS = {
    "work_life_balance": [
        "flexible hours", "flexible schedule", "work-life balance",
        "unlimited pto", "unlimited vacation", "remote-friendly",
    ],
    "growth": [
        "career growth", "learning opportunities", "mentorship",
        "professional development", "growth opportunities",
    ],
    "diversity": [
        "diverse team", "inclusive", "equity", "diversity and inclusion",
        "belonging", "eeo",
    ],
    "innovation": [
        "cutting-edge", "innovative", "startup", "fast-paced",
        "move fast", "build the future",
    ],
    "compensation": [
        "competitive salary", "equity", "stock options", "401k match",
        "health insurance", "comprehensive benefits",
    ],
}

_RED_FLAG_SIGNALS = {
    "high_turnover": [
        "join our rapidly growing team",  # overused / often hollow
        "we work hard and play hard",
        "fast-paced environment",         # can mean chaotic
        "wear many hats",                 # resource-constrained
        "self-starter",
        "hit the ground running",
    ],
    "vague_description": [
        "various duties",
        "other duties as assigned",
        "must be flexible",
        "competitive compensation",        # vague pay
    ],
    "overdemanding": [
        "10+ years experience",
        "must have 15 years",
        "we need a unicorn",
        "expected to work nights and weekends",
        "unlimited responsibilities",
    ],
}

# --------------------------------------------------------------------------- #
# Function-calling schema
# --------------------------------------------------------------------------- #

_COMPANY_INTEL_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_company",
        "description": (
            "Extract structured company intelligence from a job posting. "
            "Only state facts present in or clearly inferable from the posting text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "company_size_estimate": {
                    "type": "string",
                    "enum": ["startup_1_10", "small_11_50", "medium_51_200",
                             "large_201_1000", "enterprise_1000+", "unknown"],
                },
                "industry": {"type": "string"},
                "founded_year": {"type": "integer"},
                "growth_stage": {
                    "type": "string",
                    "enum": ["pre_seed", "seed", "series_a", "series_b",
                             "series_c_plus", "public", "unknown"],
                },
                "work_model": {
                    "type": "string",
                    "enum": ["remote", "hybrid", "onsite", "unknown"],
                },
                "tech_stack": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "salary_range_estimate": {
                    "type": "object",
                    "properties": {
                        "currency": {"type": "string"},
                        "min": {"type": "number"},
                        "max": {"type": "number"},
                        "confidence": {"type": "string", "enum": ["explicit", "inferred", "low"]},
                    },
                },
                "interview_process_hints": {
                    "type": "array",
                    "description": "Hints about interview stages from the posting",
                    "items": {"type": "string"},
                },
                "growth_indicators": {
                    "type": "array",
                    "description": "Signals of company growth (funding, headcount, product launches)",
                    "items": {"type": "string"},
                },
                "culture_signals": {
                    "type": "object",
                    "description": "Positive and negative culture signals found in the posting",
                    "properties": {
                        "positive": {"type": "array", "items": {"type": "string"}},
                        "negative": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "red_flags": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "flag": {"type": "string"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        },
                    },
                },
                "fit_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Overall fit score for the candidate given their profile.",
                },
                "fit_rationale": {"type": "string"},
            },
            "required": [
                "company_size_estimate", "work_model", "tech_stack",
                "culture_signals", "red_flags", "fit_score",
            ],
        },
    },
}


class CompanyIntelligenceAgent(BaseAgent):
    """
    Analyses the company behind a target job and produces a structured
    intelligence report including fit score.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            target_job: Optional[dict] = state.get("target_job")
            if not target_job:
                # Fall back to first matched job if available
                matched = state.get("matched_jobs") or []
                if matched:
                    target_job = matched[0]
                    state["target_job"] = target_job

            if not target_job:
                return self._log_error(state, "No target_job or matched_jobs in state")

            job_text = self._build_job_context(target_job)
            candidate_context = self._build_candidate_context(state)

            # Rule-based pre-analysis (fast, no LLM)
            rule_culture = self._rule_based_culture_signals(job_text)
            rule_red_flags = self._rule_based_red_flags(job_text)

            system_prompt = (
                "You are a company intelligence analyst specialising in tech job markets. "
                "Analyse the job posting and candidate profile provided. "
                "Ground all findings in the text — do not hallucinate company data."
            )
            user_prompt = (
                "## Job Posting\n"
                f"{job_text}\n\n"
                "## Candidate Profile Summary\n"
                f"{candidate_context}\n\n"
                "Produce structured company intelligence."
            )

            result = await self._call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[_COMPANY_INTEL_TOOL],
                tool_choice={"type": "function", "function": {"name": "analyze_company"}},
                temperature=0.1,
                max_tokens=1500,
            )

            intel = result.get("tool_call_args") or {}

            # Merge rule-based signals in
            if intel:
                existing_culture = intel.get("culture_signals", {})
                existing_culture.setdefault("positive", [])
                existing_culture.setdefault("negative", [])
                for sig in rule_culture["positive"]:
                    if sig not in existing_culture["positive"]:
                        existing_culture["positive"].append(sig)
                for sig in rule_culture["negative"]:
                    if sig not in existing_culture["negative"]:
                        existing_culture["negative"].append(sig)
                intel["culture_signals"] = existing_culture

                existing_flags = intel.get("red_flags", [])
                flag_descriptions = {f["flag"] for f in existing_flags if "flag" in f}
                for rf in rule_red_flags:
                    if rf["flag"] not in flag_descriptions:
                        existing_flags.append(rf)
                intel["red_flags"] = existing_flags
                intel["source_job_id"] = target_job.get("external_id")

            if not intel:
                state = self._log_error(state, "LLM returned empty company intelligence")
                state = self._update_confidence(state, 0.1)
                return state

            state["company_intelligence"] = intel

            confidence = self._compute_confidence(intel)
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"CompanyIntelligenceAgent: fit_score={intel.get('fit_score')}, "
                    f"work_model={intel.get('work_model')}, "
                    f"confidence={confidence:.2f}"
                ),
            )
            logger.info(
                "[CompanyIntelligenceAgent] fit_score=%s confidence=%.2f",
                intel.get("fit_score"),
                confidence,
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _build_job_context(self, job: dict) -> str:
        parts = [
            f"Title: {job.get('title', '')}",
            f"Company: {job.get('company_name', '')}",
            f"Location: {job.get('location', '')}",
            f"Remote: {job.get('remote', False)}",
            f"Salary: {job.get('salary_min', 'N/A')} - {job.get('salary_max', 'N/A')} {job.get('salary_currency', 'USD')}",
            f"Description:\n{job.get('description', '')[:3000]}",
            f"Requirements: {', '.join(job.get('requirements', [])[:30])}",
        ]
        return "\n".join(parts)

    def _build_candidate_context(self, state: AgentState) -> str:
        intel = state.get("resume_intelligence") or {}
        parsed = state.get("parsed_resume") or {}
        pinfo = parsed.get("personal_info", {})
        skills_list = [s.get("name", "") for s in parsed.get("skills", [])[:20]]

        return (
            f"Seniority: {intel.get('seniority_level', 'Unknown')}\n"
            f"Years of experience: {intel.get('total_years_experience', '?')}\n"
            f"Top skills: {', '.join(intel.get('strongest_skills', skills_list)[:15])}\n"
            f"Location: {pinfo.get('location', 'Unknown')}\n"
            f"Domains: {', '.join(intel.get('industry_domains', []))}"
        )

    def _rule_based_culture_signals(self, text: str) -> dict:
        text_lower = text.lower()
        positive: list[str] = []
        negative: list[str] = []

        for category, phrases in _POSITIVE_CULTURE_SIGNALS.items():
            for phrase in phrases:
                if phrase in text_lower:
                    positive.append(f"{category}: {phrase}")
                    break

        for category, phrases in _RED_FLAG_SIGNALS.items():
            for phrase in phrases:
                if phrase in text_lower:
                    negative.append(f"{category}: {phrase}")

        return {"positive": positive, "negative": negative}

    def _rule_based_red_flags(self, text: str) -> list[dict]:
        text_lower = text.lower()
        flags: list[dict] = []
        for category, phrases in _RED_FLAG_SIGNALS.items():
            for phrase in phrases:
                if phrase in text_lower:
                    severity = "medium" if category == "vague_description" else "high" if category == "overdemanding" else "low"
                    flags.append({"flag": f"{category}: {phrase}", "severity": severity})
        return flags

    def _compute_confidence(self, intel: dict) -> float:
        fields = [
            "company_size_estimate", "work_model", "tech_stack",
            "culture_signals", "red_flags", "fit_score",
        ]
        present = sum(1 for f in fields if intel.get(f))
        return round(present / len(fields) * 0.95, 4)
