from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
from core.models.model_artifact import ModelArtifact


class AgentState(TypedDict):
    """Shared state for all agents in the LangGraph workflow"""
    
    # Conversation management
    messages: Annotated[list, add_messages]
    deployment_conversation_id: str
    
    # Input parameters
    model_id: str
    model_artifact: Optional[ModelArtifact] = None  # Full model artifact with files
    model_source_path: Optional[str] = None  # Path to model files
    latency_requirement: Optional[str] = None
    deployment_type: Optional[str] = None
    infrastructure_details: Optional[Dict[str, Any]] = None
    
    # Primary Agent outputs
    decomposed_sub_agent_tasks: Optional[List[Dict[str, Any]]] = None  # Tasks delegated to sub-agents
    final_deployment_report: Optional[Dict[str, Any]] = None  # Final compiled deployment report
    
    # Constraint Resolver outputs
    constraint_resolver_report: Optional[Dict[str, Any]] = None
    
    # Inference Optimization outputs (deferred for future phase)
    inference_optimization_report: Optional[Dict[str, Any]] = None
    inference_optimization_status: Optional[str] = "DEFERRED"
    
    # CI/CD outputs
    ci_pipeline: Optional[Dict[str, Any]] = None
    
    # Deployment outputs
    deployment_report: Optional[Dict[str, Any]] = None
    service_endpoint: Optional[str] = None
    
    # Kubernetes deployment outputs
    kubernetes_deployment_report: Optional[Dict[str, Any]] = None
    kubernetes_manifests: Optional[Dict[str, str]] = None
    argocd_application: Optional[Dict[str, Any]] = None
    
    # ArgoCD/GitOps specific
    argocd_status: Optional[Dict[str, Any]] = None
    gitops_repository: Optional[str] = None
    gitops_branch: Optional[str] = None
    gitops_commit_sha: Optional[str] = None
    argocd_sync_status: Optional[str] = None
    argocd_health_status: Optional[str] = None
    
    # Observability outputs (deferred for future phase)
    observability_report: Optional[Dict[str, Any]] = None
    
    # State machine tracking
    current_state: Optional[str] = None  # Current state in workflow
    state_history: Optional[List[Dict[str, Any]]] = None  # State transition history
    deployment_type_decision: Optional[str] = None  # "local" or "kubernetes"
    infrastructure_available: Optional[Dict[str, bool]] = None  # What infrastructure is available
    
    # Error handling
    errors: List[str] = []
    current_agent: Optional[str] = None
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