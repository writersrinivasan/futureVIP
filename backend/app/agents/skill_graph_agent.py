"""
SkillKnowledgeGraphAgent

Builds a skill knowledge graph from the parsed resume:
  - Nodes: skills, technologies, domains, roles
  - Edges: relationships (requires, complements, leads_to)
  - Weights: proficiency score × market demand
  - Identifies skill clusters (Frontend, Backend, Data, Cloud, etc.)
  - Computes skill gaps vs target roles (from resume intelligence)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.state import AgentState
from app.agents.tools import get_skill_market_data

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Static skill relationship graph (seed)
# --------------------------------------------------------------------------- #

# Maps each skill to complementary skills (undirected) and leads_to skills
_SKILL_RELATIONS: dict[str, dict[str, list[str]]] = {
    "python": {
        "complements": ["fastapi", "django", "flask", "pandas", "sqlalchemy"],
        "leads_to": ["machine learning", "data engineering", "backend engineering"],
        "requires": [],
    },
    "react": {
        "complements": ["typescript", "redux", "graphql", "nextjs", "css"],
        "leads_to": ["frontend engineering", "full stack development"],
        "requires": ["javascript"],
    },
    "kubernetes": {
        "complements": ["docker", "helm", "terraform", "prometheus"],
        "leads_to": ["platform engineering", "sre", "devops"],
        "requires": ["docker", "linux"],
    },
    "machine learning": {
        "complements": ["python", "tensorflow", "pytorch", "scikit-learn", "pandas"],
        "leads_to": ["ml engineering", "data science", "ai research"],
        "requires": ["python", "statistics"],
    },
    "aws": {
        "complements": ["terraform", "kubernetes", "lambda", "s3", "rds"],
        "leads_to": ["cloud architecture", "devops"],
        "requires": ["linux", "networking"],
    },
}

# Cluster definitions
_CLUSTERS: dict[str, set[str]] = {
    "frontend": {"react", "vue", "angular", "svelte", "javascript", "typescript", "html", "css", "nextjs", "nuxt"},
    "backend": {"python", "java", "golang", "nodejs", "fastapi", "django", "flask", "spring", "express", "rust"},
    "data": {"pandas", "spark", "kafka", "dbt", "airflow", "sql", "postgresql", "snowflake", "bigquery"},
    "ai_ml": {"machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "scikit-learn", "llm", "langchain", "transformers"},
    "cloud": {"aws", "gcp", "azure", "lambda", "s3", "ecs", "eks", "cloud functions"},
    "devops": {"docker", "kubernetes", "terraform", "ansible", "jenkins", "github actions", "prometheus", "grafana"},
    "database": {"postgresql", "mysql", "mongodb", "redis", "cassandra", "elasticsearch", "dynamodb"},
    "mobile": {"react native", "flutter", "swift", "kotlin", "android", "ios"},
}

# Proficiency weight mapping
_PROFICIENCY_WEIGHT: dict[str, float] = {
    "expert": 1.0,
    "advanced": 0.8,
    "intermediate": 0.6,
    "beginner": 0.3,
    "": 0.5,  # unknown
}

# Demand weight mapping
_DEMAND_WEIGHT: dict[str, float] = {
    "very_high": 1.0,
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
    "unknown": 0.4,
}

# --------------------------------------------------------------------------- #
# Function-calling schema for gap analysis
# --------------------------------------------------------------------------- #

_GAP_ANALYSIS_TOOL = {
    "type": "function",
    "function": {
        "name": "identify_skill_gaps",
        "description": (
            "Identify skill gaps between the candidate's current skills and their "
            "target roles. Be specific and actionable. Only reference real skills."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "gaps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "target_role": {"type": "string"},
                            "missing_skill": {"type": "string"},
                            "importance": {
                                "type": "string",
                                "enum": ["critical", "important", "nice_to_have"],
                            },
                            "learning_path": {"type": "string"},
                            "estimated_weeks": {"type": "integer"},
                        },
                        "required": ["target_role", "missing_skill", "importance"],
                    },
                }
            },
            "required": ["gaps"],
        },
    },
}


class SkillKnowledgeGraphAgent(BaseAgent):
    """
    Builds a skill graph from parsed resume and identifies skill gaps
    against recommended target roles.
    """

    async def run(self, state: AgentState) -> AgentState:
        try:
            parsed = state.get("parsed_resume")
            intelligence = state.get("resume_intelligence")

            if not parsed:
                return self._log_error(state, "parsed_resume required — run ResumeParsingAgent first")

            raw_skills: list[dict] = parsed.get("skills", [])

            # ---------------------------------------------------------------- #
            # 1. Build skill nodes
            # ---------------------------------------------------------------- #
            nodes: dict[str, dict] = {}
            for skill_entry in raw_skills:
                name = skill_entry.get("name", "").lower().strip()
                if not name:
                    continue
                proficiency = skill_entry.get("proficiency", "").lower()
                market = get_skill_market_data.invoke({"skill_name": name})
                demand = market.get("demand", "unknown")
                weight = _PROFICIENCY_WEIGHT.get(proficiency, 0.5) * _DEMAND_WEIGHT.get(demand, 0.4)
                cluster = self._assign_cluster(name)

                nodes[name] = {
                    "name": name,
                    "category": skill_entry.get("category", "other"),
                    "proficiency": proficiency or "unknown",
                    "years": skill_entry.get("years"),
                    "cluster": cluster,
                    "weight": round(weight, 4),
                    "market_demand": demand,
                    "avg_salary_usd": market.get("avg_salary_usd"),
                }

            # Also add technologies from experience
            for exp in parsed.get("experience", []):
                for tech in exp.get("technologies", []):
                    tech_lower = tech.lower().strip()
                    if tech_lower and tech_lower not in nodes:
                        market = get_skill_market_data.invoke({"skill_name": tech_lower})
                        nodes[tech_lower] = {
                            "name": tech_lower,
                            "category": "tool",
                            "proficiency": "intermediate",
                            "cluster": self._assign_cluster(tech_lower),
                            "weight": 0.5,
                            "market_demand": market.get("demand", "unknown"),
                            "avg_salary_usd": market.get("avg_salary_usd"),
                            "source": "experience",
                        }

            # ---------------------------------------------------------------- #
            # 2. Build edges
            # ---------------------------------------------------------------- #
            edges: list[dict] = []
            for skill_name in nodes:
                relations = _SKILL_RELATIONS.get(skill_name, {})
                for rel_type, related_list in relations.items():
                    for related in related_list:
                        edges.append({
                            "source": skill_name,
                            "target": related,
                            "relationship": rel_type,
                            "weight": 1.0 if related in nodes else 0.5,
                        })

            # ---------------------------------------------------------------- #
            # 3. Cluster summary
            # ---------------------------------------------------------------- #
            cluster_summary: dict[str, dict] = {}
            for node_name, node_data in nodes.items():
                cl = node_data.get("cluster", "other")
                if cl not in cluster_summary:
                    cluster_summary[cl] = {"skills": [], "avg_weight": 0.0}
                cluster_summary[cl]["skills"].append(node_name)

            for cl, data in cluster_summary.items():
                weights = [nodes[s]["weight"] for s in data["skills"] if s in nodes]
                data["avg_weight"] = round(sum(weights) / max(len(weights), 1), 4)
                data["depth"] = "deep" if data["avg_weight"] > 0.6 else "moderate" if data["avg_weight"] > 0.3 else "surface"

            skill_graph = {
                "nodes": list(nodes.values()),
                "edges": edges,
                "clusters": cluster_summary,
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            }
            state["skill_graph"] = skill_graph

            # ---------------------------------------------------------------- #
            # 4. Skill gap analysis via GPT-4
            # ---------------------------------------------------------------- #
            target_roles = []
            if intelligence:
                for rec in intelligence.get("target_role_recommendations", []):
                    target_roles.append(rec.get("role", ""))

            if target_roles:
                state = await self._compute_skill_gaps(state, list(nodes.keys()), target_roles)

            confidence = self._compute_confidence(skill_graph)
            state = self._update_confidence(state, confidence)
            state = self._append_message(
                state,
                role="system",
                content=(
                    f"SkillKnowledgeGraphAgent: {len(nodes)} nodes, "
                    f"{len(edges)} edges, {len(cluster_summary)} clusters, "
                    f"confidence={confidence:.2f}"
                ),
            )
            logger.info(
                "[SkillGraphAgent] %d nodes, %d edges, %d clusters",
                len(nodes), len(edges), len(cluster_summary),
            )

        except Exception as exc:
            state = self._log_error(state, f"Unexpected error: {exc}")
            state = self._update_confidence(state, 0.0)

        return state

    # ---------------------------------------------------------------------- #
    # Private helpers
    # ---------------------------------------------------------------------- #

    def _assign_cluster(self, skill_name: str) -> str:
        for cluster, skills in _CLUSTERS.items():
            if skill_name in skills:
                return cluster
            # Partial match for compound names
            for s in skills:
                if s in skill_name or skill_name in s:
                    return cluster
        return "other"

    async def _compute_skill_gaps(
        self,
        state: AgentState,
        current_skills: list[str],
        target_roles: list[str],
    ) -> AgentState:
        """Call GPT-4 to identify skill gaps for each target role."""
        roles_str = ", ".join(target_roles[:5])
        skills_str = ", ".join(current_skills[:60])

        system_prompt = (
            "You are a technical career advisor. Identify REAL, SPECIFIC skill gaps "
            "between a candidate's skills and their target roles. "
            "Only list genuinely missing skills, not ones the candidate already has."
        )
        user_prompt = (
            f"Candidate current skills: {skills_str}\n\n"
            f"Target roles: {roles_str}\n\n"
            "Identify the most important skill gaps."
        )

        result = await self._call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[_GAP_ANALYSIS_TOOL],
            tool_choice={"type": "function", "function": {"name": "identify_skill_gaps"}},
            temperature=0.1,
            max_tokens=1024,
        )

        gaps = (result.get("tool_call_args") or {}).get("gaps", [])
        state["skill_gaps"] = gaps
        return state

    def _compute_confidence(self, graph: dict) -> float:
        n_nodes = graph.get("total_nodes", 0)
        n_edges = graph.get("total_edges", 0)
        n_clusters = len(graph.get("clusters", {}))

        node_score = min(n_nodes / 10, 1.0)
        edge_score = min(n_edges / 20, 1.0)
        cluster_score = min(n_clusters / 4, 1.0)

        return round((node_score * 0.5) + (edge_score * 0.3) + (cluster_score * 0.2), 4)
