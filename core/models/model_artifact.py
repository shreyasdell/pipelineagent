from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from pathlib import Path
import json
import os


class ModelArtifact(BaseModel):
    """Represents a complete model with all its files and configurations"""
    
    # Basic identification
    model_id: str
    model_name: str
    version: str = "1.0.0"
    
    # File paths
    model_path: Path  # Path to model directory/files
    config_path: Optional[Path] = None  # Path to config file
    tokenizer_path: Optional[Path] = None  # Path to tokenizer files
    weights_path: Optional[Path] = None  # Path to weights file
    
    # Model specifications
    architecture: Optional[str] = None  # e.g., "transformer", "llama", "mistral"
    parameter_count: Optional[int] = None  # Total parameters
    model_size_gb: Optional[float] = None  # Size in GB
    
    # Format information
    weight_format: str = "safetensors"  # safetensors, gguf, onnx, pytorch, etc.
    quantization: Optional[str] = None  # FP32, FP16, INT8, etc.
    
    # Configuration data
    config_data: Optional[Dict[str, Any]] = None  # Parsed config file content
    
    # Additional metadata
    framework: Optional[str] = None  # pytorch, tensorflow, jax, etc.
    task: Optional[str] = None  # text-generation, classification, etc.
    context_length: Optional[int] = None
    embedding_dim: Optional[int] = None
    
    class Config:
        arbitrary_types_allowed = True


class ModelArtifactManager:
    """Manages model artifacts, file handling, and analysis"""
    
    def __init__(self, base_storage_path: Path = Path("./model_storage")):
        self.base_storage_path = base_storage_path
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
    
    def ingest_model(self, model_source: Path, model_id: str) -> ModelArtifact:
        """
        Ingest a model from a source directory into the managed storage
        
        Args:
            model_source: Path to source model directory
            model_id: Unique identifier for the model
            
        Returns:
            ModelArtifact with analyzed model information
        """
        # Create destination directory
        model_dest = self.base_storage_path / model_id
        model_dest.mkdir(parents=True, exist_ok=True)
        
        # Copy model files (in real implementation, you'd copy files)
        # For now, we'll just analyze the source
        
        # Analyze the model structure
        artifact = self._analyze_model(model_source, model_id)
        
        return artifact
    
    def _analyze_model(self, model_path: Path, model_id: str) -> ModelArtifact:
        """
        Analyze model files to extract specifications and configuration
        
        Args:
            model_path: Path to model directory
            model_id: Model identifier
            
        Returns:
            ModelArtifact with extracted information
        """
        artifact = ModelArtifact(
            model_id=model_id,
            model_name=model_path.name,
            model_path=model_path
        )
        
        # Look for common configuration files
        config_patterns = [
            "config.json",
            "config.yaml", 
            "model_config.json",
            "generation_config.json"
        ]
        
        for pattern in config_patterns:
            config_file = model_path / pattern
            if config_file.exists():
                artifact.config_path = config_file
                artifact.config_data = self._parse_config_file(config_file)
                break
        
        # Look for weight files
        weight_patterns = [
            "*.safetensors",
            "*.bin", 
            "*.pt",
            "*.pth",
            "*.gguf",
            "*.onnx"
        ]
        
        for pattern in weight_patterns:
            weight_files = list(model_path.glob(pattern))
            if weight_files:
                artifact.weights_path = weight_files[0]
                # Determine format from extension
                if weight_files[0].suffix == ".safetensors":
                    artifact.weight_format = "safetensors"
                elif weight_files[0].suffix == ".gguf":
                    artifact.weight_format = "gguf"
                elif weight_files[0].suffix == ".onnx":
                    artifact.weight_format = "onnx"
                else:
                    artifact.weight_format = "pytorch"
                break
        
        # Extract information from config if available
        if artifact.config_data:
            artifact = self._extract_config_info(artifact)
        
        # Calculate model size
        if artifact.weights_path:
            artifact.model_size_gb = artifact.weights_path.stat().st_size / (1024**3)
        
        return artifact
    
    def _parse_config_file(self, config_path: Path) -> Dict[str, Any]:
        """Parse configuration file based on extension"""
        if config_path.suffix == ".json":
            with open(config_path, 'r') as f:
                return json.load(f)
        elif config_path.suffix in [".yaml", ".yml"]:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _extract_config_info(self, artifact: ModelArtifact) -> ModelArtifact:
        """Extract model information from configuration data"""
        config = artifact.config_data
        
        # Common config keys (varies by framework)
        if "hidden_size" in config:
            artifact.embedding_dim = config["hidden_size"]
        if "num_hidden_layers" in config:
            # Could estimate parameter count from this
            pass
        if "max_position_embeddings" in config:
            artifact.context_length = config["max_position_embeddings"]
        if "vocab_size" in config:
            # Could estimate parameter count from this
            pass
        if "model_type" in config:
            artifact.architecture = config["model_type"]
        if "architectures" in config and isinstance(config["architectures"], list):
            artifact.architecture = config["architectures"][0]
        
        return artifact
    
    def get_model_requirements(self, artifact: ModelArtifact) -> Dict[str, Any]:
        """
        Calculate deployment requirements based on model artifact
        
        Args:
            artifact: ModelArtifact to analyze
            
        Returns:
            Dictionary with deployment requirements
        """
        requirements = {
            "model_id": artifact.model_id,
            "estimated_memory_gb": self._estimate_memory_requirements(artifact),
            "supported_formats": [artifact.weight_format],
            "architecture": artifact.architecture,
            "framework": artifact.framework,
            "parameter_count": artifact.parameter_count,
            "context_length": artifact.context_length
        }
        
        return requirements
    
    def _estimate_memory_requirements(self, artifact: ModelArtifact) -> float:
        """Estimate GPU memory requirements for the model"""
        if artifact.model_size_gb:
            # Base memory for weights
            base_memory = artifact.model_size_gb
            
            # Add overhead for activation memory, KV cache, etc.
            # This is a rough estimate - actual requirements depend on:
            # - Batch size
            # - Sequence length
            # - Framework overhead
            overhead_multiplier = 2.0  # Conservative estimate
            
            return base_memory * overhead_multiplier
        
        # Fallback estimation based on parameter count
        if artifact.parameter_count:
            # Rough estimate: 4 bytes per parameter for FP32
            return (artifact.parameter_count * 4) / (1024**3)
        
        return 0.0  # Unknown