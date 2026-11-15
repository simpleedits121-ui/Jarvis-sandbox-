from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    name: str
    role: str
    objective: str
    capabilities: tuple[str, ...]
    tools: tuple[str, ...] = ()


AGENTS: tuple[AgentDefinition, ...] = (
    AgentDefinition("orchestrator", "JARVIS Orchestrator", "orchestrator", "Decompose goals, delegate work and coordinate agents.", ("task_decomposition", "delegation", "coordination")),
    AgentDefinition("vision", "Vision Agent", "vision", "Extract visible design evidence and uncertainty from reference images.", ("reference_analysis", "visual_checklist")),
    AgentDefinition("design", "Design Agent", "design", "Define character art direction, proportions and design constraints.", ("art_direction", "proportion_specification")),
    AgentDefinition("geometry", "Geometry Agent", "geometry", "Plan coherent mesh structure, topology and geometry corrections.", ("mesh_planning", "topology_checklist")),
    AgentDefinition("appearance", "Appearance Agent", "appearance", "Plan materials, textures, hair, clothing and surface details.", ("material_planning", "texture_checklist")),
    AgentDefinition("rigging", "Rigging Agent", "rigging", "Plan skeletons, weights and deformation validation.", ("rig_planning", "deformation_checklist")),
    AgentDefinition("supervisor", "3D Supervisor", "supervisor", "Review deliverables, identify gaps and assign corrective work.", ("review", "defect_tracking", "reinspection")),
    AgentDefinition("quality", "Quality Agent", "quality", "Check deliverables against acceptance criteria and report limitations.", ("acceptance_review", "risk_reporting")),
)


def public_agents() -> list[dict[str, object]]:
    return [asdict(agent) for agent in AGENTS]


def get_agent(agent_id: str) -> AgentDefinition | None:
    return next((agent for agent in AGENTS if agent.agent_id == agent_id), None)
