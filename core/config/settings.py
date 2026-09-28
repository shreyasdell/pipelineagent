from pydantic_settings import BaseSettings
from typing import Optional


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

    # Podman Configuration
    podman_socket: str = "unix:///run/podman/podman.sock"

    # Argo CD Configuration
    argocd_url: Optional[str] = None
    argocd_username: Optional[str] = None
    argocd_password: Optional[str] = None

    # Application Configuration
    log_level: str = "INFO"
    environment: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()