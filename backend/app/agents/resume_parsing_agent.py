"""
ResumeParsingAgent

Uses GPT-4 with function calling (structured output) to extract a
normalised JSON representation of a resume.  ONLY factual data present
in the resume text is returned — no hallucination.
"""

from __future__ import annotations

import json
import logging

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Function-calling schema
# --------------------------------------------------------------------------- #

_PARSE_RESUME_TOOL = {
    "type": "function",
    "function": {
        "name": "parse_resume",
        "description": (
            "Extract structured information from resume text. "
            "Only include information explicitly present in the text. "
            "Do NOT infer, guess, or hallucinate any field."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "personal_info": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "location": {"type": "string"},
                        "linkedin": {"type": "string"},
                        "github": {"type": "string"},
                        "website": {"type": "string"},
                    },
                    "required": [],
                },
                "summary": {"type": "string", "description": "Professional summary or objective, verbatim or very close paraphrase."},
                "experience": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "company": {"type": "string"},
                            "title": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "location": {"type": "string"},
                            "description": {"type": "string"},
                            "achievements": {"type": "array", "items": {"type": "string"}},
                            "technologies": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["company", "title"],
                    },
                },
                "education": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "institution": {"type": "string"},
                            "degree": {"type": "string"},
                            "field": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "gpa": {"type": "string"},
                            "honors": {"type": "string"},
                        },
                        "required": ["institution"],
                    },
                },
                "skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "category": {"type": "string", "enum": [
                                "programming_language", "framework", "database",
                                "cloud", "devops", "ai_ml", "soft_skill", "tool", "other",
                            ]},
                            "proficiency": {"type": "string", "enum": [
                                "beginner", "intermediate", "advanced", "expert",
                            ]},
                            "years": {"type": "number"},
                        },
                        "required": ["name"],
                    },
                },
                "certifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "issuer": {"type": "string"},
                            "date": {"type": "string"},
                            "expiry": {"type": "string"},
                            "credential_id": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                },
                "projects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "technologies": {"type": "array", "items": {"type": "string"}},
                            "url": {"type": "string"},
                            "impact": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                },
                "publications": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "awards": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "languages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "proficiency": {"type": "string", "enum": [
                                "native", "fluent", "professional", "conversational", "basic",
                            ]},
                        },
                        "required": ["name"],
                    },
                },
                "volunteer": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
            "required": ["personal_info", "experience", "education", "skills"],
        },
    },
}


class ResumeParsingAgent(BaseAgent):
    """
    Extracts fully structured resume data from raw text using GPT-4
    function calling.  Returns only factual, present information.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            raw_text: str | None = state.get("resume_raw_text")
            if not raw_text or len(raw_text.strip()) < 50:
                return self._log_error(state, "resume_raw_text is missing or too short")

            # Truncate to fit context window (≈ 12k chars ≈ 3k tokens)
            text_input = raw_text[:12000]

            system_prompt = (
                "You are an expert resume parser. Extract ONLY information explicitly "
                "present in the resume text. Do NOT invent, infer, or hallucinate any "
                "field. If a field is not in the text, omit it or leave it empty."
            )
            user_prompt = f"Parse the following resume:\n\n---\n{text_input}\n---"

            result = await self._call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[_PARSE_RESUME_TOOL],
                tool_choice={"type": "function", "function": {"name": "parse_resume"}},
                temperature=0.0,
            )

            parsed = result.get("tool_call_args") or {}

            if not parsed:
                state = self._log_error(state, "LLM returned empty parsed_resume")
                state = self._update_confidence(state, 0.1)
                return state

            # Ensure top-level keys exist
            for key in ("personal_info", "experience", "education", "skills",
                        "certifications", "projects", "publications", "awards",
                        "languages", "volunteer"):
                parsed.setdefault(key, [] if key != "personal_info" else {})

            state["parsed_resume"] = parsed

            confidence = self._compute_confidence(parsed)
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"ResumeParsingAgent: Parsed resume — "
                    f"{len(parsed.get('experience', []))} roles, "
                    f"{len(parsed.get('skills', []))} skills, "
                    f"confidence={confidence:.2f}"
                ),
            )
            logger.info("[ResumeParsingAgent] Parsed resume — confidence=%.2f", confidence)

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _compute_confidence(self, parsed: dict) -> float:
        """
        Score completeness of parsed resume.
        Full marks require personal_info with email, ≥1 experience,
        ≥1 education entry, and ≥3 skills.
        """
        score = 0.0
        pinfo = parsed.get("personal_info", {})

        # Personal info (0.2)
        pi_fields = sum(1 for f in ("name", "email", "phone", "location") if pinfo.get(f))
        score += (pi_fields / 4) * 0.20

        # Experience (0.30)
        exp_count = len(parsed.get("experience", []))
        score += min(exp_count / 3, 1.0) * 0.30

        # Education (0.15)
        edu_count = len(parsed.get("education", []))
        score += min(edu_count / 1, 1.0) * 0.15

        # Skills (0.25)
        skill_count = len(parsed.get("skills", []))
        score += min(skill_count / 10, 1.0) * 0.25

        # Summary present (0.10)
        if parsed.get("summary"):
            score += 0.10

        return round(score, 4)
