"""
Shared LangGraph state TypedDict for the FUTURE VIP multi-agent system.
All agents read from and write to this canonical state object.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # ------------------------------------------------------------------ #
    # Input / session context
    # ------------------------------------------------------------------ #
    user_id: str
    session_id: str
    task_type: str  # resume_analysis | job_discovery | job_matching |
    #                  ats_optimization | career_advice | interview_prep

    # ------------------------------------------------------------------ #
    # Resume source
    # ------------------------------------------------------------------ #
    resume_id: Optional[str]
    resume_raw_text: Optional[str]
    resume_file_path: Optional[str]

    # ------------------------------------------------------------------ #
    # Parsed / analysed resume
    # ------------------------------------------------------------------ #
    parsed_resume: Optional[dict]       # structured extraction (GPT-4 function call)
    resume_intelligence: Optional[dict] # deep analysis report
    resume_embedding: Optional[list]    # list[float] — text-embedding-3-large
    resume_chunks: Optional[list]       # list[str] — overlapping 512-token windows

    # ------------------------------------------------------------------ #
    # Skill graph
    # ------------------------------------------------------------------ #
    skill_graph: Optional[dict]         # nodes + edges + clusters
    skill_gaps: Optional[list]          # list[dict] — per-target-role gaps

    # ------------------------------------------------------------------ #
    # Jobs
    # ------------------------------------------------------------------ #
    discovered_jobs: Optional[list]     # list[dict] — normalised job schema
    matched_jobs: Optional[list]        # list[dict] — with match_score + reasoning
    target_job: Optional[dict]          # single job for ATS / interview prep

    # ------------------------------------------------------------------ #
    # Company intelligence
    # ------------------------------------------------------------------ #
    company_intelligence: Optional[dict]

    # ------------------------------------------------------------------ #
    # ATS optimisation
    # ------------------------------------------------------------------ #
    ats_optimized_resume: Optional[dict]
    ats_score: Optional[float]
    ats_suggestions: Optional[list]     # list[str]

    # ------------------------------------------------------------------ #
    # Career planning
    # ------------------------------------------------------------------ #
    career_roadmap: Optional[dict]
    career_insights: Optional[list]     # list[str]

    # ------------------------------------------------------------------ #
    # Interview coaching
    # ------------------------------------------------------------------ #
    interview_questions: Optional[list] # list[dict]
    interview_answer: Optional[str]     # user's answer for feedback
    interview_feedback: Optional[dict]

    # ------------------------------------------------------------------ #
    # Workflow meta
    # ------------------------------------------------------------------ #
    confidence_scores: dict             # dict[str, float]  agent → score
    errors: list                        # list[str]
    messages: list                      # list[dict]  conversation history
    next_agent: Optional[str]
    workflow_complete: bool
