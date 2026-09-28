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
    
    # Inference Optimization outputs
    inference_optimization_report: Optional[Dict[str, Any]] = None
    
    # CI/CD outputs
    ci_pipeline: Optional[Dict[str, Any]] = None
    
    # Deployment outputs
    deployment_report: Optional[Dict[str, Any]] = None
    service_endpoint: Optional[str] = None
    
    # Observability outputs
    observability_report: Optional[Dict[str, Any]] = None
    
    # Final outputs
    final_deployment_report: Optional[Dict[str, Any]] = None
    
    # Error handling
    errors: List[str] = []
    current_agent: Optional[str] = None


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