from typing import Dict, Any, Optional, List
import requests
from core.config.settings import settings
from loguru import logger


class HuggingFaceClient:
    """
    Hugging Face API client for model repository operations
    Handles model metadata retrieval, model info, and artifact discovery
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Hugging Face client
        
        Args:
            token: Hugging Face API token (defaults to settings.huggingface_token)
        """
        self.token = token or settings.huggingface_token
        self.base_url = "https://huggingface.co/api"
        self.headers = {}
        
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
        else:
            logger.warning("Hugging Face token not provided - API calls will be unauthenticated (limited access)")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Hugging Face API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: URL parameters
            
        Returns:
            Response JSON data
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Hugging Face API request failed: {e}")
            if hasattr(e.response, 'status_code'):
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            raise
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a model from Hugging Face
        
        Args:
            model_id: Model identifier (e.g., "Qwen/Qwen2.5-7B")
            
        Returns:
            Model information including metadata, config, etc.
        """
        endpoint = f"/models/{model_id}"
        
        try:
            model_info = self._make_request("GET", endpoint)
            logger.info(f"Retrieved model info for {model_id}")
            return model_info
        except Exception as e:
            logger.error(f"Failed to get model info for {model_id}: {e}")
            raise
    
    def get_model_config(self, model_id: str) -> Dict[str, Any]:
        """
        Get model configuration from Hugging Face
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model configuration
        """
        endpoint = f"/models/{model_id}/config"
        
        try:
            config = self._make_request("GET", endpoint)
            logger.info(f"Retrieved model config for {model_id}")
            return config
        except Exception as e:
            logger.error(f"Failed to get model config for {model_id}: {e}")
            raise
    
    def get_model_files(self, model_id: str) -> List[Dict[str, Any]]:
        """
        Get list of files in the model repository
        
        Args:
            model_id: Model identifier
            
        Returns:
            List of file information
        """
        endpoint = f"/models/{model_id}"
        
        try:
            model_info = self._make_request("GET", endpoint)
            siblings = model_info.get("siblings", [])
            
            files = []
            for sibling in siblings:
                if sibling.get("rfilename"):
                    files.append({
                        "filename": sibling.get("rfilename"),
                        "size": sibling.get("size"),
                        "type": self._determine_file_type(sibling.get("rfilename"))
                    })
            
            logger.info(f"Retrieved {len(files)} files for {model_id}")
            return files
        except Exception as e:
            logger.error(f"Failed to get model files for {model_id}: {e}")
            raise
    
    def _determine_file_type(self, filename: str) -> str:
        """Determine the type of model file based on filename"""
        if filename.endswith(".safetensors"):
            return "model_weights"
        elif filename.endswith(".bin"):
            return "model_weights"
        elif filename.endswith(".json"):
            if "config" in filename:
                return "config"
            elif "tokenizer" in filename:
                return "tokenizer"
            else:
                return "metadata"
        elif filename.endswith(".txt"):
            return "text"
        else:
            return "unknown"
    
    def get_model_requirements(self, model_id: str) -> Dict[str, Any]:
        """
        Get model requirements and dependencies
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model requirements including framework, dependencies, etc.
        """
        try:
            model_info = self.get_model_info(model_id)
            config = self.get_model_config(model_id)
            
            requirements = {
                "model_id": model_id,
                "framework": model_info.get("library_name", "unknown"),
                "architecture": config.get("architectures", ["unknown"])[0] if config.get("architectures") else "unknown",
                "parameter_count": self._estimate_parameters(config),
                "context_length": config.get("max_position_embeddings", "unknown"),
                "vocab_size": config.get("vocab_size", "unknown"),
                "hidden_size": config.get("hidden_size", "unknown"),
                "num_attention_heads": config.get("num_attention_heads", "unknown"),
                "num_layers": config.get("num_hidden_layers", "unknown"),
                "supported_formats": self._get_supported_formats(model_id),
                "dependencies": self._get_dependencies(model_info),
                "tags": model_info.get("tags", []),
                "pipeline_tag": model_info.get("pipeline_tag", "unknown")
            }
            
            logger.info(f"Retrieved requirements for {model_id}")
            return requirements
            
        except Exception as e:
            logger.error(f"Failed to get model requirements for {model_id}: {e}")
            raise
    
    def _estimate_parameters(self, config: Dict[str, Any]) -> str:
        """Estimate parameter count from config"""
        # Try to get from config if available
        if "num_parameters" in config:
            return str(config["num_parameters"])
        
        # Rough estimation based on architecture
        hidden_size = config.get("hidden_size", 0)
        num_layers = config.get("num_hidden_layers", 0)
        vocab_size = config.get("vocab_size", 0)
        
        if hidden_size and num_layers and vocab_size:
            # Very rough estimation for transformer models
            params = 12 * hidden_size * num_layers * vocab_size // 1000000000  # in billions
            return f"{params}B"
        
        return "unknown"
    
    def _get_supported_formats(self, model_id: str) -> List[str]:
        """Get supported weight formats for the model"""
        try:
            files = self.get_model_files(model_id)
            formats = set()
            
            for file_info in files:
                filename = file_info["filename"]
                if filename.endswith(".safetensors"):
                    formats.add("safetensors")
                elif filename.endswith(".bin"):
                    formats.add("pytorch")
                elif filename.endswith(".gguf"):
                    formats.add("gguf")
                elif filename.endswith(".onnx"):
                    formats.add("onnx")
            
            return list(formats) if formats else ["unknown"]
        except:
            return ["unknown"]
    
    def _get_dependencies(self, model_info: Dict[str, Any]) -> List[str]:
        """Get model dependencies from model info"""
        # This would typically come from requirements.txt or similar
        # For now, infer from framework
        framework = model_info.get("library_name", "unknown")
        
        if framework == "transformers":
            return ["transformers>=4.0.0", "torch>=2.0.0", "tokenizers>=0.13.0"]
        elif framework == "sentence-transformers":
            return ["sentence-transformers>=2.0.0", "torch>=2.0.0"]
        else:
            return [f"{framework}"]
    
    def search_models(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for models on Hugging Face
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching models
        """
        endpoint = "/models"
        params = {
            "search": query,
            "limit": limit
        }
        
        try:
            results = self._make_request("GET", endpoint, params=params)
            logger.info(f"Found {len(results)} models for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Failed to search models: {e}")
            raise
    
    def download_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Get comprehensive model information for deployment planning
        
        Args:
            model_id: Model identifier
            
        Returns:
            Comprehensive model information
        """
        try:
            model_info = self.get_model_info(model_id)
            model_config = self.get_model_config(model_id)
            model_files = self.get_model_files(model_id)
            requirements = self.get_model_requirements(model_id)
            
            comprehensive_info = {
                "model_id": model_id,
                "basic_info": {
                    "model_name": model_info.get("modelId"),
                    "author": model_info.get("author"),
                    "created_at": model_info.get("createdAt"),
                    "last_modified": model_info.get("lastModified"),
                    "downloads": model_info.get("downloads"),
                    "likes": model_info.get("likes"),
                    "tags": model_info.get("tags", []),
                    "pipeline_tag": model_info.get("pipeline_tag")
                },
                "configuration": model_config,
                "files": model_files,
                "requirements": requirements,
                "total_size_gb": self._calculate_total_size(model_files),
                "weight_formats": self._get_supported_formats(model_id)
            }
            
            logger.info(f"Retrieved comprehensive info for {model_id}")
            return comprehensive_info
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive model info for {model_id}: {e}")
            raise
    
    def _calculate_total_size(self, files: List[Dict[str, Any]]) -> float:
        """Calculate total size of model files in GB"""
        total_bytes = sum(f.get("size", 0) for f in files)
        return round(total_bytes / (1024**3), 2)  # Convert to GB