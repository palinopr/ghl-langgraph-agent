"""
Deployment verification utilities
"""
import os
import hashlib
from datetime import datetime
from app.utils.simple_logger import get_logger

logger = get_logger("deployment_check")

# Version and deployment info
__version__ = "1.2.0"  # Increment this with each deployment
__deployment_date__ = "2025-07-19"
__features__ = [
    "Enhanced business extraction for single words",
    "Debug logging with full visibility", 
    "Appointment booking with real GHL slots",
    "Budget extraction fix for time patterns"
]

def log_deployment_info():
    """Log deployment information at startup"""
    logger.info("="*60)
    logger.info("🚀 DEPLOYMENT INFO")
    logger.info(f"  - Version: {__version__}")
    logger.info(f"  - Deployment Date: {__deployment_date__}")
    logger.info(f"  - Python Version: {os.sys.version}")
    logger.info(f"  - Current Time: {datetime.now().isoformat()}")
    
    # Log features
    logger.info("  - Features:")
    for feature in __features__:
        logger.info(f"    ✓ {feature}")
    
    # Log environment
    logger.info("  - Environment:")
    logger.info(f"    • LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT', 'Not set')}")
    logger.info(f"    • GHL_LOCATION_ID: {os.getenv('GHL_LOCATION_ID', 'Not set')}")
    logger.info(f"    • LOG_LEVEL: {os.getenv('LOG_LEVEL', 'INFO')}")
    
    # Check for specific code changes
    logger.info("  - Code Checks:")
    
    # Check if business extraction enhancement exists
    try:
        from app.agents.supervisor_brain_simple import supervisor_brain_simple_node
        import inspect
        source = inspect.getsource(supervisor_brain_simple_node)
        
        if "direct_business_words" in source:
            logger.info("    ✓ Enhanced business extraction present")
        else:
            logger.info("    ❌ Enhanced business extraction NOT found")
            
        if "@debug_async" in source:
            logger.info("    ✓ Debug logging decorator present")
        else:
            logger.info("    ❌ Debug logging decorator NOT found")
            
    except Exception as e:
        logger.error(f"    ❌ Could not check code: {str(e)}")
    
    logger.info("="*60)

def get_code_signature():
    """Get a signature of the current code for verification"""
    signatures = {}
    
    files_to_check = [
        "app/agents/supervisor_brain_simple.py",
        "app/tools/ghl_client.py",
        "app/agents/receptionist_simple.py"
    ]
    
    for file_path in files_to_check:
        try:
            full_path = os.path.join(os.path.dirname(__file__), "..", "..", file_path)
            with open(full_path, 'rb') as f:
                content = f.read()
                signatures[file_path] = hashlib.md5(content).hexdigest()[:8]
        except Exception as e:
            signatures[file_path] = f"Error: {str(e)}"
    
    return signatures

def verify_deployment():
    """Verify the deployment has the latest code"""
    log_deployment_info()
    
    signatures = get_code_signature()
    logger.info("\n📝 Code Signatures:")
    for file, sig in signatures.items():
        logger.info(f"  - {file}: {sig}")
    
    return {
        "version": __version__,
        "deployment_date": __deployment_date__,
        "signatures": signatures,
        "features": __features__
    }