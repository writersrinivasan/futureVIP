"""
InterviewCoachAgent

Generates role-specific interview questions AND evaluates user answers:

Question generation:
  - Technical questions from job requirements
  - Behavioral (STAR-format) questions
  - Situational questions
  - Company culture fit questions
  - Salary negotiation questions

Answer evaluation:
  - Clarity and structure
  - Relevance to the question
  - Specific examples used
  - Confidence indicators
  - Areas for improvement
  - Ideal answer example
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

_QUESTIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_interview_questions",
        "description": (
            "Generate a comprehensive, role-specific set of interview questions "
            "tailored to the candidate's background and target job. "
            "Base technical questions on actual job requirements."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "category": {
                                "type": "string",
                                "enum": [
                                    "technical", "behavioral", "situational",
                                    "culture_fit", "salary_negotiation", "competency",
                                ],
                            },
                            "difficulty": {
                                "type": "string",
                                "enum": ["easy", "medium", "hard"],
                            },
                            "question": {"type": "string"},
                            "what_they_assess": {
                                "type": "string",
                                "description": "What competency or trait this question evaluates.",
                            },
                            "answer_framework": {
                                "type": "string",
                                "description": "Recommended answer framework (e.g. STAR, SOAR, direct explanation).",
                            },
                            "red_flags_in_answer": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Common mistakes candidates make answering this question.",
                            },
                            "ideal_answer_outline": {
                                "type": "string",
                                "description": "Brief outline of an ideal answer.",
                            },
                        },
                        "required": ["id", "category", "difficulty", "question", "what_they_assess"],
                    },
                    "minItems": 10,
                    "maxItems": 30,
                },
                "preparation_guide": {
                    "type": "object",
                    "properties": {
                        "company_research_tips": {"type": "array", "items": {"type": "string"}},
                        "technical_prep_areas": {"type": "array", "items": {"type": "string"}},
                        "stories_to_prepare": {
                            "type": "array",
                            "description": "Types of stories to prepare (achievements, failures, conflicts, etc.)",
                            "items": {"type": "string"},
                        },
                        "day_before_checklist": {"type": "array", "items": {"type": "string"}},
                        "questions_to_ask_them": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Smart questions for the candidate to ask the interviewer.",
                        },
                    },
                },
            },
            "required": ["questions"],
        },
    },
}

_FEEDBACK_TOOL = {
    "type": "function",
    "function": {
        "name": "evaluate_interview_answer",
        "description": (
            "Evaluate a candidate's interview answer and provide detailed, "
            "constructive feedback. Be honest and specific."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "overall_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 10,
                    "description": "Overall answer quality 0-10.",
                },
                "dimension_scores": {
                    "type": "object",
                    "properties": {
                        "clarity": {"type": "number", "minimum": 0, "maximum": 10},
                        "structure": {"type": "number", "minimum": 0, "maximum": 10},
                        "relevance": {"type": "number", "minimum": 0, "maximum": 10},
                        "specificity": {"type": "number", "minimum": 0, "maximum": 10},
                        "impact_demonstration": {"type": "number", "minimum": 0, "maximum": 10},
                        "conciseness": {"type": "number", "minimum": 0, "maximum": 10},
                    },
                },
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific things the candidate did well.",
                },
                "improvements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                        "required": ["issue", "suggestion"],
                    },
                },
                "missing_elements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key elements that should have been included but were not.",
                },
                "ideal_answer_example": {
                    "type": "string",
                    "description": "A model answer demonstrating best practices.",
                },
                "follow_up_questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Likely follow-up questions an interviewer would ask.",
                },
                "confidence_signals": {
                    "type": "object",
                    "properties": {
                        "positive": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Language patterns suggesting confidence.",
                        },
                        "negative": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Language patterns undermining confidence.",
                        },
                    },
                },
            },
            "required": ["overall_score", "strengths", "improvements", "ideal_answer_example"],
        },
    },
}


class InterviewCoachAgent(BaseAgent):
    """
    Generates interview questions and evaluates user answers with GPT-4.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            target_job: Optional[dict] = state.get("target_job")
            interview_answer: Optional[str] = state.get("interview_answer")

            # ---------------------------------------------------------------- #
            # Mode A: Generate questions (default)
            # ---------------------------------------------------------------- #
            if not interview_answer or not state.get("interview_questions"):
                state = await self._generate_questions(state, target_job)

            # ---------------------------------------------------------------- #
            # Mode B: Evaluate an answer
            # ---------------------------------------------------------------- #
            if interview_answer and state.get("interview_questions"):
                state = await self._evaluate_answer(state, interview_answer, target_job)

            # ---------------------------------------------------------------- #
            # Fallback: no target job
            # ---------------------------------------------------------------- #
            if not target_job and not state.get("interview_questions"):
                state = self._log_error(state, "No target_job set for interview coaching")
                state = self._update_confidence(state, 0.0)
                return state

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Question generation
    # ---------------------------------------------------------------------- #

    async def _generate_questions(
        self, state: AgentState, target_job: Optional[dict]
    ) -> AgentState:
        intelligence = state.get("resume_intelligence") or {}
        parsed = state.get("parsed_resume") or {}

        candidate_context = self._build_candidate_context(intelligence, parsed)
        job_context = self._build_job_context(target_job)

        system_prompt = (
            "You are an expert interview coach with deep experience at FAANG and top-tier startups. "
            "Generate highly specific, role-relevant interview questions tailored to both the "
            "candidate's background and the target job. Mix technical depth with behavioral insight."
        )
        user_prompt = (
            f"## Candidate Profile\n{candidate_context}\n\n"
            f"## Target Job\n{job_context}\n\n"
            "Generate a comprehensive interview question set with preparation guidance."
        )

        result = await self._call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_QUESTIONS_TOOL],
            tool_choice={"type": "function", "function": {"name": "generate_interview_questions"}},
            temperature=0.4,
            max_tokens=3000,
        )

        args = result.get("tool_call_args") or {}
        questions = args.get("questions", [])
        prep_guide = args.get("preparation_guide", {})

        if not questions:
            state = self._log_error(state, "LLM returned no interview questions")
            state = self._update_confidence(state, 0.1)
            return state

        state["interview_questions"] = questions

        confidence = min(len(questions) / 15, 1.0) * 0.9
        state = self._update_confidence(state, confidence)
        state = self._append_message(
            state,
            role="system",
            content=(
                f"InterviewCoachAgent: Generated {len(questions)} questions, "
                f"confidence={confidence:.2f}"
            ),
        )

        # Store prep guide inside first question's parent or as a meta entry
        if questions and prep_guide:
            state["interview_questions"] = [
                {"_preparation_guide": prep_guide},
                *questions,
            ]

        logger.info("[InterviewCoachAgent] Generated %d questions", len(questions))
        return state

    # ---------------------------------------------------------------------- #
    # Answer evaluation
    # ---------------------------------------------------------------------- #

    async def _evaluate_answer(
        self,
        state: AgentState,
        answer: str,
        target_job: Optional[dict],
    ) -> AgentState:
        # Find the question being answered (use first non-meta question)
        questions = state.get("interview_questions") or []
        current_question: Optional[dict] = None
        for q in questions:
            if q.get("question"):
                current_question = q
                break

        question_text = current_question.get("question", "General interview question") if current_question else "General interview question"

        system_prompt = (
            "You are a tough-but-fair interview coach. Evaluate the candidate's answer honestly. "
            "Give specific, actionable feedback that will help them improve."
        )
        user_prompt = (
            f"## Question\n{question_text}\n\n"
            f"## Candidate's Answer\n{answer}\n\n"
            f"## Job Context\n{self._build_job_context(target_job)[:1000]}\n\n"
            "Evaluate this answer comprehensively."
        )

        result = await self._call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_FEEDBACK_TOOL],
            tool_choice={"type": "function", "function": {"name": "evaluate_interview_answer"}},
            temperature=0.2,
            max_tokens=2000,
        )

        feedback = result.get("tool_call_args") or {}
        if not feedback:
            state = self._log_error(state, "LLM returned empty interview feedback")
            return state

        state["interview_feedback"] = {
            "question": question_text,
            "answer": answer,
            **feedback,
        }

        confidence = 0.9 if feedback.get("ideal_answer_example") else 0.6
        state = self._update_confidence(state, confidence)
        state = self._append_message(
            state,
            role="system",
            content=(
                f"InterviewCoachAgent: Answer score={feedback.get('overall_score')}/10, "
                f"confidence={confidence:.2f}"
            ),
        )
        logger.info(
            "[InterviewCoachAgent] Answer evaluated — score=%s/10",
            feedback.get("overall_score"),
        )
        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _build_candidate_context(self, intel: dict, parsed: dict) -> str:
        skills = ", ".join(intel.get("strongest_skills", [])[:15])
        pinfo = parsed.get("personal_info", {})
        return (
            f"Name: {pinfo.get('name', 'Candidate')}\n"
            f"Seniority: {intel.get('seniority_level', 'Unknown')}\n"
            f"Years: {intel.get('total_years_experience', '?')}\n"
            f"Skills: {skills}\n"
            f"Domains: {', '.join(intel.get('industry_domains', []))}\n"
            f"Value Prop: {intel.get('unique_value_proposition', '')}"
        )

    def _build_job_context(self, job: Optional[dict]) -> str:
        if not job:
            return "No specific job provided — use general software engineering context."
        reqs = ", ".join(job.get("requirements", [])[:20])
        return (
            f"Title: {job.get('title')}\n"
            f"Company: {job.get('company_name')}\n"
            f"Location: {job.get('location')}\n"
            f"Requirements: {reqs}\n"
            f"Description: {(job.get('description', ''))[:1500]}"
        )
