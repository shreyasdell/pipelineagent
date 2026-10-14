from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from core.models.model_artifact import ModelArtifact
import operator


def merge_dicts(left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge two dictionaries, with right taking precedence over left"""
    merged = left.copy() if left else {}
    if right:
        merged.update(right)
    return merged


class AgentState(TypedDict):
    """Shared state for all agents in the LangGraph workflow"""
    
    # Conversation management
    messages: Annotated[list, add_messages]
    deployment_conversation_id: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    
    # Input parameters
    model_id: Annotated[str, lambda a, b: b or a]  # Last writer wins
    model_artifact: Optional[ModelArtifact] = None  # Full model artifact with files
    model_source_path: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    latency_requirement: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    deployment_type: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    infrastructure_details: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts
    
    # Primary Agent outputs
    decomposed_sub_agent_tasks: Optional[List[Dict[str, Any]]] = None  # Tasks delegated to sub-agents
    final_deployment_report: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts

    # Constraint Resolver outputs
    constraint_resolver_report: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts

    # Inference Optimization outputs (deferred for future phase)
    inference_optimization_report: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts
    inference_optimization_status: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins

    # CI/CD outputs
    ci_pipeline: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts

    # Deployment outputs
    deployment_report: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts
    service_endpoint: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins

    # Kubernetes deployment outputs
    kubernetes_deployment_report: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts
    kubernetes_manifests: Annotated[Optional[Dict[str, str]], merge_dicts]  # Merge dicts
    argocd_application: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts
    
    # ArgoCD/GitOps specific
    argocd_status: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts
    gitops_repository: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    gitops_branch: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    gitops_commit_sha: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    argocd_sync_status: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    argocd_health_status: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins

    # Observability outputs (deferred for future phase)
    observability_report: Annotated[Optional[Dict[str, Any]], merge_dicts]  # Merge dicts

    # State machine tracking
    current_state: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    state_history: Annotated[Optional[List[Dict[str, Any]]], lambda a, b: (a or []) + (b or [])]  # Append lists
    deployment_type_decision: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    infrastructure_available: Annotated[Optional[Dict[str, bool]], merge_dicts]  # Merge dicts
    
    # Error handling
    errors: Annotated[List[str], operator.add]  # Accumulate errors
    current_agent: Annotated[Optional[str], lambda a, b: b or a]  # Last writer wins
    retry_count: int = 0
    max_retries: int = 3


class ConstraintResolverReport(TypedDict):
    """Output structure for Constraint Resolver Agent"""
    
    model_id: str
    overall_confidence_score: float
    quantization_levels_possible: List[Dict[str, Any]]
    parallelization_possible: Dict[str, bool]
    weight_format: str
    engine_type: str
    deployment_feasible: bool
    recommendations: List[str]


class InferenceOptimizationReport(TypedDict):
    """Output structure for Inference Optimization Agent"""
    
    model_id: str
    quantization_applied: str
    batching_strategy: str
    serving_framework: str
    ttft_ms: float
    tokens_per_second: float
    end_to_end_latency_ms: float
    benchmark_results: Dict[str, Any]


class DeploymentReport(TypedDict):
    """Output structure for Deployment Pipeline Agent"""
    
    model_id: str
    container_image: str
    deployment_status: str
    argocd_sync_status: str
    argocd_health_status: str
    deployment_timestamp: str