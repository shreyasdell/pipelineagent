from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # LLM Configuration
    openai_api_key: Optional[str] = None  # Optional for production
    llm_model: str = "qwen2.5:7b"  # Default Ollama model for development
    llm_temperature: float = 0.7
    ollama_base_url: str = "http://127.0.0.1:11434"  # Ollama endpoint for development
    vllm_base_url: str = "http://localhost:8000/v1"  # vLLM endpoint for production

    # Database Configuration
    database_url: Optional[str] = None  # Optional for initial testing
    postgres_user: str = "user"
    postgres_password: str = "password"
    postgres_db: str = "agentic_pipeline"

    # GitHub Configuration
    github_token: Optional[str] = None  # Optional for initial testing
    github_repo: Optional[str] = None  # Optional for initial testing

    # Hugging Face Configuration
    huggingface_token: Optional[str] = None  # Optional for accessing private models
    huggingface_model_id: Optional[str] = None  # Default model ID for testing

    # Podman Configuration
    podman_socket: str = "unix:///run/podman/podman.sock"
    
    # Kubernetes Configuration
    kubeconfig_path: str = "/workspaces/AgenticPipeline/.kube/config"

    # Argo CD Configuration
    argocd_url: Optional[str] = None
    argocd_username: Optional[str] = None
    argocd_password: Optional[str] = None
    
    # Kubernetes Configuration
    default_namespace: str = "model-serving"
    default_replicas: int = 1
    default_service_type: str = "LoadBalancer"
    default_service_port: int = 8000
    
    # vLLM Configuration
    default_vllm_image: str = "vllm/vllm-openai"
    vllm_image_tag: str = "latest"
    default_gpu_memory_utilization: float = 0.9
    default_max_model_len: int = 4096
    default_tensor_parallel_size: int = 1
    default_model_path_prefix: str = "/models"
    
    # Health Check Configuration
    health_check_initial_delay: int = 30
    health_check_period: int = 10
    liveness_check_initial_delay: int = 60
    liveness_check_period: int = 30
    
    # Resource Defaults
    default_cpu_request: str = "2"
    default_memory_request: str = "8Gi"
    default_cpu_limit_multiplier: int = 2
    default_memory_limit_multiplier: int = 2

    # Application Configuration
    log_level: str = "INFO"
    environment: str = "development"
    
    # Primary Agent Configuration
    default_container_registry: str = "docker.io"
    default_organization: str = "your-org"
    default_base_image: str = "nvidia/cuda:12.1.0-runtime-ubuntu22.04"
    service_endpoint_base_url: str = "https://api.example.com/inference"
    
    # Serving Framework Configuration
    serving_framework_priority_str: str = "tensorrt-llm,vllm,triton,bentoml,sglang,llama.cpp"
    
    @property
    def serving_framework_priority(self) -> List[str]:
        """Parse serving framework priority from comma-separated string"""
        return [fw.strip() for fw in self.serving_framework_priority_str.split(",") if fw.strip()]
    
    # Autoscaling Configuration
    default_min_replicas: int = 2
    default_max_replicas: int = 10
    default_target_cpu_utilization: int = 70
    default_target_memory_utilization: int = 80
    default_scale_up_threshold: int = 80
    default_scale_down_threshold: int = 30
    
    # Rollout Configuration
    default_canary_initial_traffic: int = 5
    default_canary_ramp_up_hours: int = 24
    default_canary_monitoring_hours: int = 48

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()