"""
Test ArgoCD connection
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.argocd.argocd_client import ArgoCDClient
from core.config.settings import settings
from loguru import logger


async def test_argocd_connection():
    """Test ArgoCD connection"""
    logger.info("Testing ArgoCD connection...")
    
    try:
        client = ArgoCDClient()
        
        # Test application list
        logger.info(f"ArgoCD URL: {settings.argocd_url}")
        logger.info(f"ArgoCD Username: {settings.argocd_username}")
        
        apps = client.list_applications()
        
        logger.info(f"✅ ArgoCD connection successful")
        
        if apps:
            logger.info(f"   Applications: {len(apps.get('items', []))}")
            
            for app in apps.get('items', []):
                logger.info(f"   - {app.get('metadata', {}).get('name')}: {app.get('status', {}).get('health', {}).get('status')}")
        else:
            logger.info("   No applications found (empty ArgoCD)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ArgoCD connection failed: {e}")
        return False


async def main():
    """Run test"""
    logger.info("=" * 60)
    logger.info("ArgoCD Connection Test")
    logger.info("=" * 60)
    
    success = await test_argocd_connection()
    
    logger.info("=" * 60)
    logger.info(f"Test: {'PASSED' if success else 'FAILED'}")
    logger.info("=" * 60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)