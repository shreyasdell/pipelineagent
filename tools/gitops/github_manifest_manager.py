from typing import Dict, Any, Optional, List
import base64
from core.config.settings import settings
from tools.github.github_client import GitHubClient
from loguru import logger


class GitHubManifestManager:
    """
    GitHub Manifest Manager - Handles GitOps operations for Kubernetes manifests
    Manages committing Kubernetes manifests to GitHub repository for ArgoCD deployment
    """
    
    def __init__(self):
        self.github_client = GitHubClient()
        self.default_branch = "main"
        self.manifests_path = "deployment/manifests"
    
    def commit_kubernetes_manifests(
        self,
        model_id: str,
        manifests: Dict[str, str],
        repository: Optional[str] = None,
        branch: Optional[str] = None,
        commit_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Commit Kubernetes manifests to GitHub repository for GitOps deployment
        
        Args:
            model_id: Model identifier
            manifests: Dictionary of Kubernetes manifests (namespace, configmap, deployment, service, argocd_application)
            repository: GitHub repository (format: owner/repo)
            branch: Git branch to commit to
            commit_message: Custom commit message
            
        Returns:
            Commit result with SHA and status
        """
        if not settings.github_token:
            logger.error("GitHub token not configured - cannot commit manifests")
            return {
                "status": "failed",
                "reason": "GitHub token not configured",
                "model_id": model_id
            }
        
        repo = repository or settings.github_repo
        if not repo:
            logger.error("GitHub repository not configured")
            return {
                "status": "failed",
                "reason": "GitHub repository not configured",
                "model_id": model_id
            }
        
        target_branch = branch or self.default_branch
        safe_model_id = model_id.replace('_', '-').replace('/', '-')
        manifest_dir = f"{self.manifests_path}/{safe_model_id}"
        
        try:
            # Step 1: Get current branch SHA
            logger.info(f"Getting current branch SHA for {repo}...")
            self.github_client.repo = repo  # Set repo for the client
            branch_info = self.github_client.get_branch(target_branch)
            if not branch_info:
                logger.error(f"Branch {target_branch} not found in repository")
                return {
                    "status": "failed",
                    "reason": f"Branch {target_branch} not found",
                    "model_id": model_id
                }
            
            base_sha = branch_info.get("commit", {}).get("sha")
            logger.info(f"Base SHA: {base_sha}")
            
            # Step 2: Create tree with manifest files
            logger.info(f"Creating Git tree with manifests for {safe_model_id}...")
            tree_items = []
            
            for manifest_type, manifest_content in manifests.items():
                file_path = f"{manifest_dir}/{manifest_type}.yaml"
                # Create blob for each manifest
                blob_result = self.github_client.create_blob(repo, manifest_content)
                if not blob_result:
                    logger.error(f"Failed to create blob for {manifest_type}")
                    continue
                
                blob_sha = blob_result.get("sha")
                tree_items.append({
                    "path": file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha
                })
                logger.info(f"Created blob for {manifest_type}: {blob_sha}")
            
            # Create tree
            tree_result = self.github_client.create_tree(repo, tree_items, base_tree=base_sha)
            if not tree_result:
                logger.error("Failed to create Git tree")
                return {
                    "status": "failed",
                    "reason": "Failed to create Git tree",
                    "model_id": model_id
                }
            
            tree_sha = tree_result.get("sha")
            logger.info(f"Created tree: {tree_sha}")
            
            # Step 3: Create commit
            logger.info("Creating commit...")
            default_message = f"Add Kubernetes manifests for model {model_id}"
            final_message = commit_message or default_message
            
            commit_result = self.github_client.create_commit(
                repo,
                message=final_message,
                tree=tree_sha,
                parents=[base_sha]
            )
            
            if not commit_result:
                logger.error("Failed to create commit")
                return {
                    "status": "failed",
                    "reason": "Failed to create commit",
                    "model_id": model_id
                }
            
            commit_sha = commit_result.get("sha")
            logger.info(f"Created commit: {commit_sha}")
            
            # Step 4: Update branch reference
            logger.info(f"Updating branch {target_branch} to new commit...")
            self.github_client.repo = repo
            update_result = self.github_client.update_reference(
                f"refs/heads/{target_branch}",
                sha=commit_sha
            )
            
            if not update_result:
                logger.error("Failed to update branch reference")
                return {
                    "status": "failed",
                    "reason": "Failed to update branch reference",
                    "model_id": model_id
                }
            
            logger.info(f"Successfully updated branch {target_branch}")
            
            return {
                "status": "success",
                "commit_sha": commit_sha,
                "branch": target_branch,
                "repository": repo,
                "manifest_directory": manifest_dir,
                "manifests_committed": list(manifests.keys()),
                "model_id": model_id,
                "message": final_message
            }
            
        except Exception as e:
            logger.error(f"Error committing Kubernetes manifests: {e}")
            return {
                "status": "error",
                "reason": f"Error during commit: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    def get_manifest_commit_status(
        self,
        model_id: str,
        repository: Optional[str] = None,
        commit_sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the status of a manifest commit
        
        Args:
            model_id: Model identifier
            repository: GitHub repository
            commit_sha: Commit SHA to check
            
        Returns:
            Commit status information
        """
        repo = repository or settings.github_repo
        if not repo:
            return {
                "status": "failed",
                "reason": "GitHub repository not configured",
                "model_id": model_id
            }
        
        try:
            if commit_sha:
                # Get specific commit info
                self.github_client.repo = repo
                commit_info = self.github_client.get_commit(commit_sha)
                return {
                    "status": "success",
                    "commit_sha": commit_sha,
                    "commit_info": commit_info,
                    "model_id": model_id
                }
            else:
                # Get latest commit
                self.github_client.repo = repo
                branch_info = self.github_client.get_branch(self.default_branch)
                return {
                    "status": "success",
                    "latest_commit": branch_info.get("commit", {}),
                    "model_id": model_id
                }
                
        except Exception as e:
            logger.error(f"Error getting commit status: {e}")
            return {
                "status": "error",
                "reason": f"Error getting commit status: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }
    
    def create_deployment_branch(
        self,
        model_id: str,
        repository: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a deployment-specific branch for the model
        
        Args:
            model_id: Model identifier
            repository: GitHub repository
            
        Returns:
            Branch creation result
        """
        repo = repository or settings.github_repo
        if not repo:
            return {
                "status": "failed",
                "reason": "GitHub repository not configured",
                "model_id": model_id
            }
        
        safe_model_id = model_id.replace('_', '-').replace('/', '')
        branch_name = f"deploy-{safe_model_id}"
        
        try:
            # Get main branch SHA
            self.github_client.repo = repo
            main_branch = self.github_client.get_branch(self.default_branch)
            if not main_branch:
                return {
                    "status": "failed",
                    "reason": f"Main branch {self.default_branch} not found",
                    "model_id": model_id
                }
            
            base_sha = main_branch.get("commit", {}).get("sha")
            
            # Create new branch
            self.github_client.repo = repo
            create_result = self.github_client.create_reference(
                f"refs/heads/{branch_name}",
                sha=base_sha
            )
            
            if create_result:
                logger.info(f"Created branch {branch_name}")
                return {
                    "status": "success",
                    "branch": branch_name,
                    "base_sha": base_sha,
                    "model_id": model_id
                }
            else:
                return {
                    "status": "failed",
                    "reason": "Failed to create branch",
                    "model_id": model_id
                }
                
        except Exception as e:
            logger.error(f"Error creating deployment branch: {e}")
            return {
                "status": "error",
                "reason": f"Error creating branch: {str(e)}",
                "model_id": model_id,
                "error": str(e)
            }