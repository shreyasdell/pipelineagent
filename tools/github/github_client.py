from typing import Dict, Any, Optional, List
import requests
import base64
from core.config.settings import settings
from loguru import logger


class GitHubClient:
    """
    GitHub API client for repository operations
    Handles workflow file creation, updates, and CI pipeline verification
    """
    
    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        """
        Initialize GitHub client
        
        Args:
            token: GitHub personal access token (defaults to settings.github_token)
            repo: GitHub repository in format "owner/repo" (defaults to settings.github_repo)
        """
        self.token = token or settings.github_token
        self.repo = repo or settings.github_repo
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        } if self.token else {}
        
        if not self.token:
            logger.warning("GitHub token not provided - API calls will be unauthenticated (limited)")
        
        if not self.repo:
            logger.warning("GitHub repository not configured - repository operations will be limited")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated request to GitHub API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            Response JSON data
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=data)
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
            logger.error(f"GitHub API request failed: {e}")
            if hasattr(e.response, 'status_code'):
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            raise
    
    def create_workflow_file(self, workflow_name: str, workflow_content: str, branch: str = "main") -> Dict[str, Any]:
        """
        Create or update a GitHub Actions workflow file in the repository
        
        Args:
            workflow_name: Name of the workflow file (without .yaml extension)
            workflow_content: YAML content of the workflow
            branch: Branch to create the file on
            
        Returns:
            Response from GitHub API
        """
        if not self.repo:
            raise ValueError("GitHub repository not configured")
        
        # Encode content to base64
        encoded_content = base64.b64encode(workflow_content.encode()).decode()
        
        # File path for GitHub Actions workflow
        file_path = f".github/workflows/{workflow_name}.yaml"
        
        # First, check if file exists to get SHA
        endpoint = f"/repos/{self.repo}/contents/{file_path}"
        try:
            existing_file = self._make_request("GET", endpoint, {"ref": branch})
            sha = existing_file.get("sha")
            logger.info(f"Updating existing workflow file: {file_path}")
        except:
            sha = None
            logger.info(f"Creating new workflow file: {file_path}")
        
        # Create or update file
        data = {
            "message": f"Add/update CI workflow: {workflow_name}",
            "content": encoded_content,
            "branch": branch
        }
        
        if sha:
            data["sha"] = sha
        
        endpoint = f"/repos/{self.repo}/contents/{file_path}"
        response = self._make_request("PUT", endpoint, data)
        
        logger.info(f"Workflow file {workflow_name}.yaml created/updated successfully")
        return response
    
    def get_workflow_runs(self, workflow_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get workflow runs from the repository
        
        Args:
            workflow_name: Optional filter by workflow name
            
        Returns:
            List of workflow runs
        """
        if not self.repo:
            raise ValueError("GitHub repository not configured")
        
        endpoint = f"/repos/{self.repo}/actions/runs"
        params = {}
        
        if workflow_name:
            params["workflow"] = f".github/workflows/{workflow_name}.yaml"
        
        response = self._make_request("GET", endpoint, params)
        return response.get("workflow_runs", [])
    
    def get_workflow_status(self, workflow_name: str) -> Dict[str, Any]:
        """
        Get the status of the latest workflow run for a specific workflow
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow status information
        """
        runs = self.get_workflow_runs(workflow_name)
        
        if not runs:
            return {
                "status": "no_runs",
                "message": f"No workflow runs found for {workflow_name}"
            }
        
        latest_run = runs[0]
        return {
            "status": latest_run.get("status"),
            "conclusion": latest_run.get("conclusion"),
            "run_id": latest_run.get("id"),
            "run_number": latest_run.get("run_number"),
            "created_at": latest_run.get("created_at"),
            "updated_at": latest_run.get("updated_at"),
            "url": latest_run.get("html_url"),
            "head_branch": latest_run.get("head_branch"),
            "head_commit": latest_run.get("head_sha")
        }
    
    def trigger_workflow(self, workflow_name: str, branch: str = "main", inputs: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Manually trigger a workflow run
        
        Args:
            workflow_name: Name of the workflow
            branch: Branch to run the workflow on
            inputs: Optional workflow inputs
            
        Returns:
            Response from GitHub API
        """
        if not self.repo:
            raise ValueError("GitHub repository not configured")
        
        # Get workflow ID first
        endpoint = f"/repos/{self.repo}/actions/workflows"
        response = self._make_request("GET", endpoint)
        
        workflow_id = None
        for workflow in response.get("workflows", []):
            if workflow["name"] == workflow_name or workflow["path"] == f".github/workflows/{workflow_name}.yaml":
                workflow_id = workflow["id"]
                break
        
        if not workflow_id:
            raise ValueError(f"Workflow {workflow_name} not found")
        
        # Trigger workflow
        endpoint = f"/repos/{self.repo}/actions/workflows/{workflow_id}/dispatches"
        data = {
            "ref": branch
        }
        
        if inputs:
            data["inputs"] = inputs
        
        response = self._make_request("POST", endpoint, data)
        logger.info(f"Workflow {workflow_name} triggered on branch {branch}")
        
        return response
    
    def create_branch(self, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """
        Create a new branch in the repository
        
        Args:
            branch_name: Name of the new branch
            base_branch: Base branch to create from
            
        Returns:
            Response from GitHub API
        """
        if not self.repo:
            raise ValueError("GitHub repository not configured")
        
        # Get SHA of base branch
        endpoint = f"/repos/{self.repo}/git/refs/heads/{base_branch}"
        response = self._make_request("GET", endpoint)
        sha = response["object"]["sha"]
        
        # Create new branch
        endpoint = f"/repos/{self.repo}/git/refs"
        data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        
        response = self._make_request("POST", endpoint, data)
        logger.info(f"Branch {branch_name} created from {base_branch}")
        
        return response
    
    def create_pull_request(self, title: str, head: str, base: str = "main", body: str = "") -> Dict[str, Any]:
        """
        Create a pull request
        
        Args:
            title: PR title
            head: Head branch (your branch)
            base: Base branch (target branch)
            body: PR description
            
        Returns:
            Response from GitHub API
        """
        if not self.repo:
            raise ValueError("GitHub repository not configured")
        
        endpoint = f"/repos/{self.repo}/pulls"
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body
        }
        
        response = self._make_request("POST", endpoint, data)
        logger.info(f"Pull request created: {title}")
        
        return response
    
    def verify_ci_pipeline(self, workflow_name: str) -> Dict[str, Any]:
        """
        Verify CI pipeline status and health
        
        Args:
            workflow_name: Name of the workflow to verify
            
        Returns:
            Verification result with status and details
        """
        try:
            status = self.get_workflow_status(workflow_name)
            
            if status["status"] == "no_runs":
                return {
                    "verified": False,
                    "status": "no_runs",
                    "message": f"Workflow {workflow_name} exists but has no runs",
                    "recommendation": "Trigger the workflow manually or push to trigger branch"
                }
            
            # Check if latest run was successful
            if status["conclusion"] == "success":
                return {
                    "verified": True,
                    "status": "success",
                    "message": f"Workflow {workflow_name} latest run completed successfully",
                    "details": status
                }
            elif status["conclusion"] == "failure":
                return {
                    "verified": False,
                    "status": "failure",
                    "message": f"Workflow {workflow_name} latest run failed",
                    "details": status,
                    "recommendation": "Check workflow logs for errors"
                }
            else:
                return {
                    "verified": False,
                    "status": status["conclusion"] or status["status"],
                    "message": f"Workflow {workflow_name} status: {status['status']}",
                    "details": status
                }
                
        except Exception as e:
            logger.error(f"Error verifying CI pipeline: {e}")
            return {
                "verified": False,
                "status": "error",
                "message": f"Error verifying CI pipeline: {str(e)}",
                "error": str(e)
            }
