"""
SemanticMatchingAgent

For each discovered job, computes a composite match score:
  - Embedding cosine similarity       (weight 40%)
  - Skill overlap score               (weight 30%)
  - Experience level alignment        (weight 20%)
  - Location / remote preference      (weight 10%)

Generates GPT-4 reasoning for each match.
Returns top-20 matched jobs with match_score and reasoning.
"""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

_TOP_N = 20
_MIN_SCORE = 0.25   # discard below this
_REASONING_BATCH = 5  # jobs per LLM call for reasoning

# Seniority level numeric map
_SENIORITY_MAP: dict[str, int] = {
    "intern": 0,
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
    "principal": 5,
    "executive": 6,
}

# Function-calling schema for batch reasoning
_MATCH_REASONING_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_match_reasoning",
        "description": "Generate match reasoning and insights for a set of job matches.",
        "parameters": {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "job_id": {"type": "string"},
                            "reasoning": {
                                "type": "string",
                                "description": "2-3 sentence explanation of why this job matches the candidate.",
                            },
                            "strengths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "maxItems": 5,
                                "description": "Candidate strengths for this role.",
                            },
                            "gaps": {
                                "type": "array",
                                "items": {"type": "string"},
                                "maxItems": 5,
                                "description": "Candidate skill or experience gaps for this role.",
                            },
                            "application_tips": {
                                "type": "array",
                                "items": {"type": "string"},
                                "maxItems": 3,
                            },
                        },
                        "required": ["job_id", "reasoning", "strengths", "gaps"],
                    },
                }
            },
            "required": ["matches"],
        },
    },
}


class SemanticMatchingAgent(BaseAgent):
    """
    Ranks discovered jobs against the candidate's profile using a weighted
    multi-factor scoring model, then generates LLM reasoning for top matches.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            discovered_jobs: list[dict] = state.get("discovered_jobs") or []
            if not discovered_jobs:
                return self._log_error(state, "No discovered_jobs in state")

            resume_embedding: Optional[list] = state.get("resume_embedding")
            skill_graph: dict = state.get("skill_graph") or {}
            intelligence: dict = state.get("resume_intelligence") or {}
            parsed: dict = state.get("parsed_resume") or {}

            candidate_skills = self._extract_candidate_skills(skill_graph, parsed)
            candidate_seniority = intelligence.get("seniority_level", "Mid").lower()
            candidate_location = (parsed.get("personal_info") or {}).get("location", "").lower()

            # ---------------------------------------------------------------- #
            # 1. Score each job
            # ---------------------------------------------------------------- #
            scored: list[dict] = []
            for job in discovered_jobs:
                score, breakdown = self._compute_match_score(
                    job=job,
                    resume_embedding=resume_embedding,
                    candidate_skills=candidate_skills,
                    candidate_seniority=candidate_seniority,
                    candidate_location=candidate_location,
                )
                if score >= _MIN_SCORE:
                    scored.append({
                        **job,
                        "match_score": round(score, 4),
                        "match_breakdown": breakdown,
                        "reasoning": None,
                        "match_strengths": [],
                        "match_gaps": [],
                        "application_tips": [],
                    })

            # Sort descending by match score
            scored.sort(key=lambda j: j["match_score"], reverse=True)
            top_matches = scored[:_TOP_N]

            # ---------------------------------------------------------------- #
            # 2. Generate LLM reasoning for top matches
            # ---------------------------------------------------------------- #
            if top_matches:
                top_matches = await self._generate_reasoning(
                    state=state,
                    matches=top_matches,
                    candidate_skills=candidate_skills,
                    intelligence=intelligence,
                )

            state["matched_jobs"] = top_matches

            avg_score = sum(j["match_score"] for j in top_matches) / max(len(top_matches), 1)
            confidence = min(len(top_matches) / _TOP_N, 1.0) * 0.95
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"SemanticMatchingAgent: {len(top_matches)} matches "
                    f"(avg_score={avg_score:.2f}), confidence={confidence:.2f}"
                ),
            )
            logger.info(
                "[SemanticMatchingAgent] %d matches, avg_score=%.2f",
                len(top_matches), avg_score,
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Scoring
    # ---------------------------------------------------------------------- #

    def _compute_match_score(
        self,
        job: dict,
        resume_embedding: Optional[list],
        candidate_skills: set[str],
        candidate_seniority: str,
        candidate_location: str,
    ) -> tuple[float, dict]:
        """
        Returns (composite_score, breakdown_dict).
        """
        breakdown: dict[str, float] = {}

        # -- Embedding cosine similarity (40%) --
        job_embedding = job.get("embedding")
        if resume_embedding and job_embedding:
            cos_sim = self._cosine_similarity(resume_embedding, job_embedding)
            embedding_score = (cos_sim + 1) / 2  # normalise to [0, 1]
        else:
            embedding_score = 0.5  # neutral when no embedding
        breakdown["embedding_similarity"] = round(embedding_score, 4)

        # -- Skill overlap (30%) --
        job_reqs = {r.lower().strip() for r in job.get("requirements", []) if r}
        if job_reqs:
            overlap = candidate_skills & job_reqs
            # Partial matches (substring)
            partial_count = sum(
                1 for r in job_reqs
                if any(r in s or s in r for s in candidate_skills) and r not in overlap
            )
            skill_score = (len(overlap) + partial_count * 0.5) / max(len(job_reqs), 1)
            skill_score = min(skill_score, 1.0)
        else:
            skill_score = 0.5
        breakdown["skill_overlap"] = round(skill_score, 4)

        # -- Experience level alignment (20%) --
        job_level_raw = (job.get("experience_level") or "").lower()
        job_seniority = self._infer_seniority_from_text(
            job_level_raw + " " + job.get("title", "").lower()
        )
        candidate_level_num = _SENIORITY_MAP.get(candidate_seniority, 2)
        job_level_num = _SENIORITY_MAP.get(job_seniority, 2)
        level_diff = abs(candidate_level_num - job_level_num)
        level_score = max(0.0, 1.0 - level_diff * 0.33)
        breakdown["level_alignment"] = round(level_score, 4)

        # -- Location / remote preference (10%) --
        if job.get("remote"):
            location_score = 1.0
        elif candidate_location and job.get("location"):
            loc_match = (
                candidate_location in job["location"].lower()
                or any(
                    city in job["location"].lower()
                    for city in candidate_location.split(",")
                )
            )
            location_score = 0.9 if loc_match else 0.3
        else:
            location_score = 0.5
        breakdown["location_match"] = round(location_score, 4)

        # -- Composite --
        composite = (
            embedding_score * 0.40
            + skill_score * 0.30
            + level_score * 0.20
            + location_score * 0.10
        )
        breakdown["composite"] = round(composite, 4)
        return composite, breakdown

    def _cosine_similarity(self, a: list, b: list) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(y * y for y in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def _infer_seniority_from_text(self, text: str) -> str:
        for key in reversed(list(_SENIORITY_MAP.keys())):
            if key in text:
                return key
        return "mid"

    def _extract_candidate_skills(self, skill_graph: dict, parsed: dict) -> set[str]:
        nodes: list[dict] = skill_graph.get("nodes", [])
        if nodes:
            return {n["name"].lower() for n in nodes}
        return {s.get("name", "").lower() for s in (parsed.get("skills") or []) if s.get("name")}

    # ---------------------------------------------------------------------- #
    # LLM reasoning
    # ---------------------------------------------------------------------- #

    async def _generate_reasoning(
        self,
        state: AgentState,
        matches: list[dict],
        candidate_skills: set[str],
        intelligence: dict,
    ) -> list[dict]:
        """
        Generate reasoning for matches in batches of _REASONING_BATCH.
        """
        batches = [
            matches[i: i + _REASONING_BATCH]
            for i in range(0, len(matches), _REASONING_BATCH)
        ]
        tasks = [
            self._reason_batch(batch, candidate_skills, intelligence)
            for batch in batches
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        reasoning_map: dict[str, dict] = {}
        for res in batch_results:
            if isinstance(res, Exception):
                state = self._log_error(state, f"Reasoning batch error: {res}")
            elif isinstance(res, dict):
                reasoning_map.update(res)

        for match in matches:
            jid = match.get("external_id", "")
            if jid in reasoning_map:
                r = reasoning_map[jid]
                match["reasoning"] = r.get("reasoning", "")
                match["match_strengths"] = r.get("strengths", [])
                match["match_gaps"] = r.get("gaps", [])
                match["application_tips"] = r.get("application_tips", [])

        return matches

    async def _reason_batch(
        self,
        batch: list[dict],
        candidate_skills: set[str],
        intelligence: dict,
    ) -> dict[str, dict]:
        """
        Call GPT-4 to generate reasoning for a batch of job matches.
        Returns dict mapping job external_id → reasoning dict.
        """
        jobs_summary = "\n\n".join(
            f"Job ID: {j.get('external_id')}\n"
            f"Title: {j.get('title')}\n"
            f"Company: {j.get('company_name')}\n"
            f"Requirements: {', '.join(j.get('requirements', [])[:15])}\n"
            f"Match Score: {j.get('match_score')}"
            for j in batch
        )
        candidate_summary = (
            f"Seniority: {intelligence.get('seniority_level', 'Unknown')}\n"
            f"Top skills: {', '.join(list(candidate_skills)[:20])}\n"
            f"Domains: {', '.join(intelligence.get('industry_domains', []))}\n"
            f"Value prop: {intelligence.get('unique_value_proposition', '')}"
        )

        result = await self._call_llm(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a career coach generating match reasoning for job recommendations. "
                        "Be specific, honest, and concise."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"## Candidate Profile\n{candidate_summary}\n\n"
                        f"## Job Matches\n{jobs_summary}\n\n"
                        "Generate match reasoning for each job."
                    ),
                },
            ],
            tools=[_MATCH_REASONING_TOOL],
            tool_choice={"type": "function", "function": {"name": "generate_match_reasoning"}},
            temperature=0.2,
            max_tokens=2000,
        )

        reasoning_list = (result.get("tool_call_args") or {}).get("matches", [])
        return {r["job_id"]: r for r in reasoning_list if r.get("job_id")}
