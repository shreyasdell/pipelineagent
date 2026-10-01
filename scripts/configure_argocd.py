"""
Configure ArgoCD to watch the GitOps repository
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.argocd.argocd_client import ArgoCDClient
from core.config.settings import settings
from loguru import logger


async def configure_argocd():
    """Configure ArgoCD to watch the GitOps repository"""
    logger.info("Configuring ArgoCD for GitOps...")
    
    try:
        client = ArgoCDClient()
        
        # Repository configuration
        # Use HTTPS with insecure SSL (for development)
        repo_url = "https://github.com/shreyasdell/pipelineagent.git"
        
        # ArgoCD application configuration
        app_name = "agentic-pipeline-gitops"
        path = "deployment/manifests"
        destination_server = "https://kubernetes.default.svc"  # Internal cluster URL
        destination_namespace = "model-serving"
        
        logger.info(f"Creating ArgoCD application: {app_name}")
        logger.info(f"Repository: {repo_url}")
        logger.info(f"Path: {path}")
        logger.info(f"Destination: {destination_namespace}")
        
        result = client.create_application(
            app_name=app_name,
            repo_url=repo_url,
            path=path,
            destination_server=destination_server,
            destination_namespace=destination_namespace
        )
        
        logger.info(f"✅ ArgoCD application created successfully")
        logger.info(f"   Application: {app_name}")
        logger.info(f"   Repository: {repo_url}")
        logger.info(f"   Path: {path}")
        logger.info(f"   Destination: {destination_namespace}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ArgoCD configuration failed: {e}")
        return False


async def main():
    """Run configuration"""
    logger.info("=" * 60)
    logger.info("ArgoCD GitOps Configuration")
    logger.info("=" * 60)
    
    success = await configure_argocd()
    
    logger.info("=" * 60)
    logger.info(f"Configuration: {'SUCCESS' if success else 'FAILED'}")
    logger.info("=" * 60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)