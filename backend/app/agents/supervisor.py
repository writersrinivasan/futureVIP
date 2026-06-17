"""
CareerSupervisor — LangGraph orchestrator for FUTURE VIP

Builds a StateGraph with conditional routing across all agents.
Supports parallel execution where agents are independent.

Workflow routes by task_type:

  resume_analysis:
    upload → parse → intelligence → (embed || skill_graph) → notify

  job_discovery:
    skill_graph → job_discovery → (company_intel || embed_jobs) → match → notify

  job_matching:
    embed → match → notify

  ats_optimization:
    parse → ats_optimize → notify

  career_advice:
    career_advisor → notify

  interview_prep:
    interview_coach → notify

  full_pipeline (default):
    upload → parse → intelligence → (embed || skill_graph)
    → job_discovery → (embed_jobs || company_intel) → match
    → ats_optimize → career_advisor → interview_coach → notify

  track_applications:
    application_tracker → notify
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Optional

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.resume_upload_agent import ResumeUploadAgent
from app.agents.resume_parsing_agent import ResumeParsingAgent
from app.agents.resume_intelligence_agent import ResumeIntelligenceAgent
from app.agents.embedding_agent import EmbeddingVectorizationAgent
from app.agents.skill_graph_agent import SkillKnowledgeGraphAgent
from app.agents.job_discovery_agent import JobDiscoveryAgent
from app.agents.company_intelligence_agent import CompanyIntelligenceAgent
from app.agents.semantic_matching_agent import SemanticMatchingAgent
from app.agents.ats_optimization_agent import ATSOptimizationAgent
from app.agents.career_advisor_agent import CareerAdvisorAgent
from app.agents.interview_coach_agent import InterviewCoachAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.application_tracker_agent import ApplicationTrackerAgent

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Node name constants
# --------------------------------------------------------------------------- #

N_START = "start_router"
N_UPLOAD = "resume_upload"
N_PARSE = "resume_parse"
N_INTELLIGENCE = "resume_intelligence"
N_EMBED = "embedding"
N_SKILL = "skill_graph"
N_DISCOVER = "job_discovery"
N_COMPANY = "company_intelligence"
N_MATCH = "semantic_match"
N_ATS = "ats_optimize"
N_ADVISOR = "career_advisor"
N_INTERVIEW = "interview_coach"
N_NOTIFY = "notification"
N_TRACKER = "application_tracker"
N_EMBED_SKILL = "embed_and_skill"       # parallel fan-out node
N_EMBED_COMPANY = "embed_and_company"   # parallel fan-out node


class CareerSupervisor:
    """
    LangGraph-based multi-agent orchestrator.

    Usage
    -----
    supervisor = CareerSupervisor()
    result = await supervisor.run(
        task_type="resume_analysis",
        user_id="u123",
        resume_file_path="/uploads/resume.pdf",
    )
    """

    def __init__(self) -> None:
        # Instantiate all agents once; they are stateless
        self._upload = ResumeUploadAgent()
        self._parse = ResumeParsingAgent()
        self._intel = ResumeIntelligenceAgent()
        self._embed = EmbeddingVectorizationAgent()
        self._skill = SkillKnowledgeGraphAgent()
        self._discover = JobDiscoveryAgent()
        self._company = CompanyIntelligenceAgent()
        self._match = SemanticMatchingAgent()
        self._ats = ATSOptimizationAgent()
        self._advisor = CareerAdvisorAgent()
        self._interview = InterviewCoachAgent()
        self._notify = NotificationAgent()
        self._tracker = ApplicationTrackerAgent()

        # Compile the graph
        self.graph = self._build_graph()

    # ---------------------------------------------------------------------- #
    # Public entry point
    # ---------------------------------------------------------------------- #

    async def run(
        self,
        task_type: str,
        user_id: str,
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentState:
        """
        Execute the workflow for the given task_type.

        Parameters
        ----------
        task_type  : one of the supported task types (see module docstring)
        user_id    : authenticated user identifier
        session_id : optional session UUID; auto-generated if omitted
        **kwargs   : additional state fields (resume_file_path, target_job, etc.)
        """
        initial_state: AgentState = {
            "user_id": user_id,
            "session_id": session_id or str(uuid.uuid4()),
            "task_type": task_type,
            # Resume source
            "resume_id": kwargs.get("resume_id"),
            "resume_raw_text": kwargs.get("resume_raw_text"),
            "resume_file_path": kwargs.get("resume_file_path"),
            "resume_chunks": None,
            # Parsed
            "parsed_resume": kwargs.get("parsed_resume"),
            "resume_intelligence": None,
            "resume_embedding": None,
            # Skills
            "skill_graph": None,
            "skill_gaps": None,
            # Jobs
            "discovered_jobs": kwargs.get("discovered_jobs"),
            "matched_jobs": None,
            "target_job": kwargs.get("target_job"),
            # Company
            "company_intelligence": None,
            # ATS
            "ats_optimized_resume": None,
            "ats_score": None,
            "ats_suggestions": None,
            # Career
            "career_roadmap": None,
            "career_insights": None,
            # Interview
            "interview_questions": None,
            "interview_answer": kwargs.get("interview_answer"),
            "interview_feedback": None,
            # Meta
            "confidence_scores": {},
            "errors": [],
            "messages": [],
            "next_agent": None,
            "workflow_complete": False,
        }

        logger.info(
            "[CareerSupervisor] task_type=%s user=%s session=%s",
            task_type, user_id, initial_state["session_id"],
        )

        try:
            final_state = await self.graph.ainvoke(initial_state)
            final_state["workflow_complete"] = True
        except Exception as exc:
            logger.exception("[CareerSupervisor] Graph execution failed: %s", exc)
            initial_state["errors"].append(f"[CareerSupervisor] Graph failure: {exc}")
            initial_state["workflow_complete"] = False
            return initial_state

        logger.info(
            "[CareerSupervisor] Complete. errors=%d confidence_keys=%s",
            len(final_state.get("errors", [])),
            list(final_state.get("confidence_scores", {}).keys()),
        )
        return final_state

    # ---------------------------------------------------------------------- #
    # Graph construction
    # ---------------------------------------------------------------------- #

    def _build_graph(self) -> Any:
        """Build and compile the LangGraph StateGraph."""
        graph: StateGraph = StateGraph(AgentState)

        # ------------------------------------------------------------------ #
        # Register nodes
        # ------------------------------------------------------------------ #
        graph.add_node(N_START, self._start_router)
        graph.add_node(N_UPLOAD, self._upload.run)
        graph.add_node(N_PARSE, self._parse.run)
        graph.add_node(N_INTELLIGENCE, self._intel.run)
        graph.add_node(N_EMBED, self._embed.run)
        graph.add_node(N_SKILL, self._skill.run)
        graph.add_node(N_DISCOVER, self._discover.run)
        graph.add_node(N_COMPANY, self._company.run)
        graph.add_node(N_MATCH, self._match.run)
        graph.add_node(N_ATS, self._ats.run)
        graph.add_node(N_ADVISOR, self._advisor.run)
        graph.add_node(N_INTERVIEW, self._interview.run)
        graph.add_node(N_NOTIFY, self._notify.run)
        graph.add_node(N_TRACKER, self._tracker.run)
        # Parallel compound nodes
        graph.add_node(N_EMBED_SKILL, self._parallel_embed_skill)
        graph.add_node(N_EMBED_COMPANY, self._parallel_embed_company)

        # ------------------------------------------------------------------ #
        # Entry point
        # ------------------------------------------------------------------ #
        graph.set_entry_point(N_START)

        # ------------------------------------------------------------------ #
        # Routing from start_router
        # ------------------------------------------------------------------ #
        graph.add_conditional_edges(
            N_START,
            self._route_by_task,
            {
                "resume_analysis":    N_UPLOAD,
                "job_discovery":      N_SKILL,
                "job_matching":       N_EMBED,
                "ats_optimization":   N_PARSE,
                "career_advice":      N_ADVISOR,
                "interview_prep":     N_INTERVIEW,
                "full_pipeline":      N_UPLOAD,
                "track_applications": N_TRACKER,
                "__default__":        N_UPLOAD,
            },
        )

        # ------------------------------------------------------------------ #
        # resume_analysis / full_pipeline: upload → parse
        # parse routes to intelligence or ats_optimize
        # ------------------------------------------------------------------ #
        graph.add_edge(N_UPLOAD, N_PARSE)

        graph.add_conditional_edges(
            N_PARSE,
            self._route_after_parse,
            {
                "ats_optimization": N_ATS,
                # resume_analysis and full_pipeline continue to intelligence
                "__default__": N_INTELLIGENCE,
            },
        )

        # ------------------------------------------------------------------ #
        # intelligence → embed_and_skill (parallel)
        # ------------------------------------------------------------------ #
        graph.add_edge(N_INTELLIGENCE, N_EMBED_SKILL)

        # embed_and_skill → job_discovery (full) or notify (resume_analysis)
        graph.add_conditional_edges(
            N_EMBED_SKILL,
            self._route_after_embed_skill,
            {
                "full_pipeline": N_DISCOVER,
                "__default__":   N_NOTIFY,
            },
        )

        # ------------------------------------------------------------------ #
        # job_discovery path
        # skill_graph → discover (if started from job_discovery task)
        # ------------------------------------------------------------------ #
        graph.add_conditional_edges(
            N_SKILL,
            self._route_after_skill_standalone,
            {
                "job_discovery": N_DISCOVER,
                "__default__":   N_NOTIFY,
            },
        )

        # discover → embed_and_company (parallel)
        graph.add_edge(N_DISCOVER, N_EMBED_COMPANY)

        # embed_and_company → match
        graph.add_edge(N_EMBED_COMPANY, N_MATCH)

        # ------------------------------------------------------------------ #
        # job_matching path (standalone): embed → match
        # ------------------------------------------------------------------ #
        graph.add_conditional_edges(
            N_EMBED,
            self._route_after_embed_standalone,
            {
                "job_matching": N_MATCH,
                "__default__":  N_NOTIFY,
            },
        )

        # ------------------------------------------------------------------ #
        # After matching → ats (full) or notify
        # ------------------------------------------------------------------ #
        graph.add_conditional_edges(
            N_MATCH,
            self._route_after_match,
            {
                "full_pipeline": N_ATS,
                "__default__":   N_NOTIFY,
            },
        )

        # ------------------------------------------------------------------ #
        # ats_optimize → advisor (full) or notify
        # ------------------------------------------------------------------ #
        graph.add_conditional_edges(
            N_ATS,
            self._route_after_ats,
            {
                "full_pipeline": N_ADVISOR,
                "__default__":   N_NOTIFY,
            },
        )

        # ------------------------------------------------------------------ #
        # career_advisor → interview_coach (full) or notify
        # ------------------------------------------------------------------ #
        graph.add_conditional_edges(
            N_ADVISOR,
            self._route_after_advisor,
            {
                "full_pipeline": N_INTERVIEW,
                "__default__":   N_NOTIFY,
            },
        )

        # ------------------------------------------------------------------ #
        # Terminal edges → END
        # ------------------------------------------------------------------ #
        graph.add_edge(N_INTERVIEW, N_NOTIFY)
        graph.add_edge(N_TRACKER, N_NOTIFY)
        graph.add_edge(N_NOTIFY, END)

        return graph.compile()

    # ---------------------------------------------------------------------- #
    # Parallel compound node implementations
    # ---------------------------------------------------------------------- #

    async def _parallel_embed_skill(self, state: AgentState) -> AgentState:
        """Run EmbeddingAgent and SkillGraphAgent concurrently."""
        s1, s2 = await asyncio.gather(
            self._embed.run(dict(state)),  # type: ignore[arg-type]
            self._skill.run(dict(state)),  # type: ignore[arg-type]
        )
        merged = dict(state)
        # Embedding outputs
        merged["resume_embedding"] = s1.get("resume_embedding")
        merged["resume_chunks"] = s1.get("resume_chunks") or merged.get("resume_chunks")
        _merge_confidence(merged, s1)
        _merge_errors(merged, s1)
        _merge_messages(merged, s1)
        # Skill graph outputs
        merged["skill_graph"] = s2.get("skill_graph")
        merged["skill_gaps"] = s2.get("skill_gaps")
        _merge_confidence(merged, s2)
        _merge_errors(merged, s2)
        _merge_messages(merged, s2)
        return merged  # type: ignore[return-value]

    async def _parallel_embed_company(self, state: AgentState) -> AgentState:
        """Run EmbeddingAgent (job vectors) and CompanyIntelligenceAgent concurrently."""
        s1, s2 = await asyncio.gather(
            self._embed.run(dict(state)),   # type: ignore[arg-type]
            self._company.run(dict(state)), # type: ignore[arg-type]
        )
        merged = dict(state)
        # Embedding outputs (jobs get their embeddings, resume embedding refreshed)
        merged["discovered_jobs"] = s1.get("discovered_jobs") or merged.get("discovered_jobs")
        merged["resume_embedding"] = s1.get("resume_embedding") or merged.get("resume_embedding")
        _merge_confidence(merged, s1)
        _merge_errors(merged, s1)
        _merge_messages(merged, s1)
        # Company intel
        merged["company_intelligence"] = s2.get("company_intelligence")
        _merge_confidence(merged, s2)
        _merge_errors(merged, s2)
        _merge_messages(merged, s2)
        return merged  # type: ignore[return-value]

    # ---------------------------------------------------------------------- #
    # Start router node
    # ---------------------------------------------------------------------- #

    async def _start_router(self, state: AgentState) -> AgentState:
        """Validate and normalise the task_type before routing."""
        valid_tasks = {
            "resume_analysis", "job_discovery", "job_matching",
            "ats_optimization", "career_advice", "interview_prep",
            "full_pipeline", "track_applications",
        }
        task = state.get("task_type", "")
        if task not in valid_tasks:
            logger.warning(
                "[Supervisor] Unknown task_type '%s' → defaulting to full_pipeline", task
            )
            state["task_type"] = "full_pipeline"
        state["next_agent"] = state["task_type"]
        return state

    # ---------------------------------------------------------------------- #
    # Conditional routing functions
    # ---------------------------------------------------------------------- #

    def _route_by_task(self, state: AgentState) -> str:
        task = state.get("task_type", "")
        valid = {
            "resume_analysis", "job_discovery", "job_matching",
            "ats_optimization", "career_advice", "interview_prep",
            "full_pipeline", "track_applications",
        }
        return task if task in valid else "__default__"

    def _route_after_parse(self, state: AgentState) -> str:
        task = state.get("task_type", "")
        if task == "ats_optimization":
            return "ats_optimization"
        return "__default__"

    def _route_after_embed_skill(self, state: AgentState) -> str:
        task = state.get("task_type", "")
        return "full_pipeline" if task == "full_pipeline" else "__default__"

    def _route_after_skill_standalone(self, state: AgentState) -> str:
        task = state.get("task_type", "")
        return "job_discovery" if task == "job_discovery" else "__default__"

    def _route_after_embed_standalone(self, state: AgentState) -> str:
        task = state.get("task_type", "")
        return "job_matching" if task == "job_matching" else "__default__"

    def _route_after_match(self, state: AgentState) -> str:
        task = state.get("task_type", "")
        return "full_pipeline" if task == "full_pipeline" else "__default__"

    def _route_after_ats(self, state: AgentState) -> str:
        task = state.get("task_type", "")
        return "full_pipeline" if task == "full_pipeline" else "__default__"

    def _route_after_advisor(self, state: AgentState) -> str:
        task = state.get("task_type", "")
        return "full_pipeline" if task == "full_pipeline" else "__default__"


# --------------------------------------------------------------------------- #
# State merge utilities
# --------------------------------------------------------------------------- #

def _merge_confidence(target: dict, source: dict) -> None:
    existing = dict(target.get("confidence_scores") or {})
    existing.update(source.get("confidence_scores") or {})
    target["confidence_scores"] = existing


def _merge_errors(target: dict, source: dict) -> None:
    existing = list(target.get("errors") or [])
    for err in source.get("errors") or []:
        if err not in existing:
            existing.append(err)
    target["errors"] = existing


def _merge_messages(target: dict, source: dict) -> None:
    existing = list(target.get("messages") or [])
    seen = {m.get("content") for m in existing}
    for msg in source.get("messages") or []:
        if msg.get("content") not in seen:
            existing.append(msg)
            seen.add(msg.get("content"))
    target["messages"] = existing


# --------------------------------------------------------------------------- #
# Module-level singleton (for backward-compat with existing imports)
# --------------------------------------------------------------------------- #

# Lazy-initialised to avoid import-time overhead
_supervisor_instance: Optional[CareerSupervisor] = None


def get_supervisor() -> CareerSupervisor:
    """Return the shared CareerSupervisor singleton."""
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = CareerSupervisor()
    return _supervisor_instance
