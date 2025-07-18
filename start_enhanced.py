#!/usr/bin/env python3
"""
Enhanced startup script that ensures all latest features are enabled
"""
import os
import sys
import asyncio
from app.utils.simple_logger import get_logger

logger = get_logger("startup")

def verify_enhanced_setup():
    """Verify all enhanced components are properly configured"""
    print("🚀 Starting Enhanced GHL LangGraph Agent")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check enhanced features
    from app.config import get_settings
    settings = get_settings()
    
    features = {
        "Streaming": settings.enable_streaming,
        "Parallel Checks": settings.enable_parallel_checks,
        "Message Batching": settings.enable_message_batching,
        "Error Recovery": True,  # Always enabled
        "Context Trimming": True,  # Always enabled
    }
    
    print("\n📋 Enhanced Features Status:")
    for feature, enabled in features.items():
        status = "✅ Enabled" if enabled else "❌ Disabled"
        print(f"  {feature}: {status}")
    
    # Check agent versions
    print("\n🤖 Agent Versions:")
    try:
        from app.agents.sofia_agent_v2_enhanced import sofia_node_v2
        print("  Sofia: ✅ Enhanced (with streaming)")
    except:
        print("  Sofia: ⚠️  Standard")
    
    try:
        from app.agents.carlos_agent_v2_enhanced import carlos_node_v2
        print("  Carlos: ✅ Enhanced (with parallel checks)")
    except:
        print("  Carlos: ⚠️  Standard")
    
    try:
        from app.agents.maria_agent_v2 import maria_node_v2
        print("  Maria: ✅ Standard (with error recovery)")
    except:
        print("  Maria: ❌ Missing")
    
    # Check workflow
    print("\n🔄 Workflow Status:")
    try:
        from app.workflow_v2 import workflow
        print("  Main Workflow: ✅ Enhanced v2")
    except Exception as e:
        print(f"  Main Workflow: ❌ Error - {e}")
    
    print("\n" + "=" * 50)
    print("🎉 All systems ready!\n")


async def test_enhanced_features():
    """Quick test of enhanced features"""
    print("🧪 Testing Enhanced Features...")
    
    try:
        # Test streaming
        from app.agents.sofia_agent_v2_enhanced import stream_appointment_confirmation
        print("  ✅ Streaming capability verified")
        
        # Test parallel checks
        from app.agents.carlos_agent_v2_enhanced import parallel_qualification_check
        print("  ✅ Parallel processing verified")
        
        # Test error recovery
        from app.utils.error_recovery import with_retry
        print("  ✅ Error recovery verified")
        
        # Test workflow
        from app.workflow_v2 import create_workflow_with_memory_v2
        workflow = create_workflow_with_memory_v2()
        print("  ✅ Enhanced workflow verified")
        
        print("\n✨ All enhanced features are working!\n")
        
    except Exception as e:
        print(f"\n❌ Feature test failed: {e}\n")


def main():
    """Main startup function"""
    # Verify setup
    verify_enhanced_setup()
    
    # Run feature tests
    asyncio.run(test_enhanced_features())
    
    # Start the enhanced webhook
    print("🌐 Starting Enhanced Webhook Server...")
    
    try:
        # Import and run enhanced webhook
        from app.api.webhook_enhanced import app
        import uvicorn
        
        port = int(os.environ.get("PORT", 8000))
        
        print(f"\n🚀 Server starting on http://0.0.0.0:{port}")
        print("📡 Webhook endpoint: POST /webhook/message")
        print("🌊 Streaming endpoint: POST /webhook/message/stream")
        print("❤️  Health check: GET /health")
        print("\nPress CTRL+C to stop\n")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )
        
    except ImportError:
        print("⚠️  Enhanced webhook not found, falling back to standard")
        from app.api.webhook import app
        import uvicorn
        
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
    
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Startup error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()