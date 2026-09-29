from typing import Dict, Any, Optional, List
import requests
from core.config.settings import settings
from loguru import logger


class ArgoCDClient:
    """
    ArgoCD API client for deployment management
    Handles application synchronization, health checks, and deployment status monitoring
    """
    
    def __init__(self, url: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize ArgoCD client
        
        Args:
            url: ArgoCD server URL (defaults to settings.argocd_url)
            username: ArgoCD username (defaults to settings.argocd_username)
            password: ArgoCD password (defaults to settings.argocd_password)
        """
        self.url = url or settings.argocd_url
        self.username = username or settings.argocd_username
        self.password = password or settings.argocd_password
        self.session = requests.Session()
        self.auth_token = None
        
        if self.url and self.username and self.password:
            self._authenticate()
        else:
            logger.warning("ArgoCD credentials not fully configured - API calls will be limited")
    
    def _authenticate(self):
        """Authenticate with ArgoCD and get session token"""
        try:
            auth_url = f"{self.url}/api/v1/session"
            response = self.session.post(
                auth_url,
                json={"username": self.username, "password": self.password},
                verify=False  # Disable SSL verification for development
            )
            response.raise_for_status()
            
            self.auth_token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            logger.info("Successfully authenticated with ArgoCD")
            
        except Exception as e:
            logger.error(f"ArgoCD authentication failed: {e}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to ArgoCD API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            Response JSON data
        """
        if not self.url:
            raise ValueError("ArgoCD URL not configured")
        
        url = f"{self.url}/api/v1{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url, json=data, verify=False)
            elif method == "POST":
                response = self.session.post(url, json=data, verify=False)
            elif method == "PUT":
                response = self.session.put(url, json=data, verify=False)
            elif method == "DELETE":
                response = self.session.delete(url, verify=False)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ArgoCD API request failed: {e}")
            if hasattr(e.response, 'status_code'):
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            raise
    
    def get_application(self, app_name: str) -> Dict[str, Any]:
        """
        Get application details from ArgoCD
        
        Args:
            app_name: Name of the application
            
        Returns:
            Application details
        """
        endpoint = f"/applications/{app_name}"
        return self._make_request("GET", endpoint)
    
    def get_application_status(self, app_name: str) -> Dict[str, Any]:
        """
        Get application status including sync and health status
        
        Args:
            app_name: Name of the application
            
        Returns:
            Application status information
        """
        try:
            app = self.get_application(app_name)
            
            return {
                "application_name": app_name,
                "sync_status": app.get("status", {}).get("sync", {}).get("status"),
                "sync_revision": app.get("status", {}).get("sync", {}).get("revision"),
                "health_status": app.get("status", {}).get("health", {}).get("status"),
                "operation_state": app.get("operation", {}).get("state"),
                "operation_message": app.get("operation", {}).get("message"),
                "url": app.get("url"),
                "project": app.get("spec", {}).get("project"),
                "namespace": app.get("spec", {}).get("destination", {}).get("namespace"),
                "server": app.get("spec", {}).get("destination", {}).get("server"),
                "created_at": app.get("status", {}).get("operationState", {}).get("startedAt"),
                "updated_at": app.get("status", {}).get("operationState", {}).get("finishedAt")
            }
            
        except Exception as e:
            logger.error(f"Error getting application status: {e}")
            return {
                "application_name": app_name,
                "sync_status": "unknown",
                "health_status": "unknown",
                "error": str(e)
            }
    
    def sync_application(self, app_name: str, revision: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Trigger application synchronization
        
        Args:
            app_name: Name of the application
            revision: Git revision to sync (optional)
            dry_run: Perform dry run without actual sync
            
        Returns:
            Sync operation response
        """
        endpoint = f"/applications/{app_name}/sync"
        
        data = {
            "dryRun": dry_run,
            "prune": True,
            "strategy": {
                "hook": {
                    "force": False
                }
            }
        }
        
        if revision:
            data["revision"] = revision
        
        response = self._make_request("POST", endpoint, data)
        logger.info(f"Application {app_name} sync triggered")
        
        return response
    
    def create_application(self, app_name: str, repo_url: str, path: str, 
                          destination_server: str, destination_namespace: str,
                          project: str = "default") -> Dict[str, Any]:
        """
        Create a new application in ArgoCD
        
        Args:
            app_name: Name of the application
            repo_url: Git repository URL
            path: Path to manifests in repository
            destination_server: Destination cluster server
            destination_namespace: Destination namespace
            project: ArgoCD project name
            
        Returns:
            Created application details
        """
        endpoint = "/applications"
        
        data = {
            "metadata": {
                "name": app_name
            },
            "spec": {
                "project": project,
                "source": {
                    "repoURL": repo_url,
                    "targetRevision": "HEAD",
                    "path": path
                },
                "destination": {
                    "server": destination_server,
                    "namespace": destination_namespace
                },
                "syncPolicy": {
                    "automated": {
                        "prune": True,
                        "selfHeal": True
                    },
                    "syncOptions": [
                        "CreateNamespace=true"
                    ]
                }
            }
        }
        
        response = self._make_request("POST", endpoint, data)
        logger.info(f"Application {app_name} created successfully")
        
        return response
    
    def list_applications(self, label_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all applications in ArgoCD
        
        Args:
            label_selector: Optional label selector to filter applications
            
        Returns:
            List of applications
        """
        endpoint = "/applications"
        params = {}
        
        if label_selector:
            params["labelSelector"] = label_selector
        
        response = self._make_request("GET", endpoint, params)
        return response.get("items", [])
    
    def get_application_resources(self, app_name: str) -> List[Dict[str, Any]]:
        """
        Get resources managed by an application
        
        Args:
            app_name: Name of the application
            
        Returns:
            List of application resources
        """
        endpoint = f"/applications/{app_name}/resources"
        response = self._make_request("GET", endpoint)
        return response.get("items", [])
    
    def verify_deployment(self, model_id: str) -> Dict[str, Any]:
        """
        Verify deployment status for a specific model
        
        Args:
            model_id: Model identifier to search for
            
        Returns:
            Deployment verification result
        """
        try:
            # Search for application by model_id (assuming app name includes model_id)
            applications = self.list_applications()
            
            matching_apps = [
                app for app in applications 
                if model_id.replace("_", "-").lower() in app.get("metadata", {}).get("name", "").lower()
            ]
            
            if not matching_apps:
                return {
                    "verified": False,
                    "status": "not_found",
                    "message": f"No ArgoCD application found for model {model_id}",
                    "model_id": model_id
                }
            
            # Get status of the first matching application
            app_name = matching_apps[0]["metadata"]["name"]
            app_status = self.get_application_status(app_name)
            
            # Check if all indicators are positive
            sync_status = app_status.get("sync_status")
            health_status = app_status.get("health_status")
            
            all_positive = (
                sync_status == "Synced" and 
                health_status in ["Healthy", "Progressing"]
            )
            
            return {
                "verified": all_positive,
                "status": "success" if all_positive else "partial",
                "message": f"Deployment verification for {model_id}: {'All indicators positive' if all_positive else 'Some indicators not positive'}",
                "model_id": model_id,
                "application_name": app_name,
                "sync_status": sync_status,
                "health_status": health_status,
                "operation_state": app_status.get("operation_state"),
                "all_indicators_positive": all_positive,
                "details": app_status
            }
            
        except Exception as e:
            logger.error(f"Error verifying deployment: {e}")
            return {
                "verified": False,
                "status": "error",
                "message": f"Error during deployment verification: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    def get_deployment_metrics(self, app_name: str) -> Dict[str, Any]:
        """
        Get deployment metrics for an application
        
        Args:
            app_name: Name of the application
            
        Returns:
            Deployment metrics
        """
        try:
            resources = self.get_application_resources(app_name)
            
            metrics = {
                "application_name": app_name,
                "total_resources": len(resources),
                "resources_by_kind": {},
                "healthy_resources": 0,
                "unhealthy_resources": 0
            }
            
            for resource in resources:
                kind = resource.get("kind", "Unknown")
                metrics["resources_by_kind"][kind] = metrics["resources_by_kind"].get(kind, 0) + 1
                
                health_status = resource.get("health", {}).get("status")
                if health_status == "Healthy":
                    metrics["healthy_resources"] += 1
                else:
                    metrics["unhealthy_resources"] += 1
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting deployment metrics: {e}")
            return {
                "application_name": app_name,
                "error": str(e)
            }
