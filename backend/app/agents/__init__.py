"""
FUTURE VIP — Multi-Agent System Package

Exports the CareerSupervisor orchestrator and all individual agent classes.

Quick start:
    from app.agents import CareerSupervisor
    supervisor = CareerSupervisor()
    result = await supervisor.run(
        task_type="resume_analysis",
        user_id="u123",
        resume_file_path="/uploads/resume.pdf",
    )
"""

from app.agents.state import AgentState

from app.agents.base_agent import BaseAgent

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

from app.agents.supervisor import CareerSupervisor, get_supervisor

__all__ = [
    # State
    "AgentState",
    # Base
    "BaseAgent",
    # Agents — in pipeline order
    "ResumeUploadAgent",
    "ResumeParsingAgent",
    "ResumeIntelligenceAgent",
    "EmbeddingVectorizationAgent",
    "SkillKnowledgeGraphAgent",
    "JobDiscoveryAgent",
    "CompanyIntelligenceAgent",
    "SemanticMatchingAgent",
    "ATSOptimizationAgent",
    "CareerAdvisorAgent",
    "InterviewCoachAgent",
    "NotificationAgent",
    "ApplicationTrackerAgent",
    # Orchestrator
    "CareerSupervisor",
    "get_supervisor",
]
