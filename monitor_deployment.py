#!/usr/bin/env python3
"""
Monitor LangGraph deployment status and provide guidance
"""
import subprocess
import json
import time
from datetime import datetime
import webbrowser

def check_github_actions():
    """Check GitHub Actions status via CLI"""
    print("\n📊 Checking GitHub Actions Status...")
    print("=" * 60)
    
    try:
        # Try to use GitHub CLI if available
        result = subprocess.run(
            ["gh", "run", "list", "--repo", "palinopr/ghl-langgraph-agent", "--limit", "5"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("Recent workflow runs:")
            print(result.stdout)
        else:
            print("❌ GitHub CLI not available or not authenticated")
            print("📌 Please check manually at:")
            print("   https://github.com/palinopr/ghl-langgraph-agent/actions")
            
    except FileNotFoundError:
        print("❌ GitHub CLI (gh) not installed")
        print("📌 Opening GitHub Actions in browser...")
        webbrowser.open("https://github.com/palinopr/ghl-langgraph-agent/actions")


def check_langsmith_deployments():
    """Guide user to check LangSmith deployments"""
    print("\n📊 LangSmith Deployment Check")
    print("=" * 60)
    print("📌 Please check your LangSmith dashboard at:")
    print("   https://smith.langchain.com")
    print("\n👀 Look for:")
    print("   1. Your project: ghl-langgraph-agent")
    print("   2. Deployments section")
    print("   3. Recent deployment with status")
    print("   4. Deployment URL (format: https://[id].us.langgraph.app)")


def update_verify_script():
    """Guide user to update verify_deployment.py"""
    print("\n📝 Update Verification Script")
    print("=" * 60)
    
    deployment_url = input("Enter your deployment URL (or 'skip' to skip): ").strip()
    
    if deployment_url.lower() != 'skip' and deployment_url.startswith("https://"):
        try:
            # Read current content
            with open("verify_deployment.py", "r") as f:
                content = f.read()
            
            # Replace the placeholder URL
            updated_content = content.replace(
                'DEPLOYMENT_URL = "https://YOUR-DEPLOYMENT-URL"',
                f'DEPLOYMENT_URL = "{deployment_url}"'
            )
            
            # Write back
            with open("verify_deployment.py", "w") as f:
                f.write(updated_content)
            
            print(f"✅ Updated verify_deployment.py with URL: {deployment_url}")
            return deployment_url
        except Exception as e:
            print(f"❌ Error updating file: {e}")
    
    return None


def show_next_steps(deployment_url=None):
    """Show next steps for verification"""
    print("\n📋 Next Steps")
    print("=" * 60)
    
    if deployment_url:
        print("1. ✅ Deployment URL obtained")
        print(f"   URL: {deployment_url}")
        print("\n2. Run verification tests:")
        print("   python verify_deployment.py")
    else:
        print("1. ⏳ Get deployment URL from:")
        print("   - GitHub Actions logs")
        print("   - LangSmith dashboard")
        print("\n2. Update verify_deployment.py with the URL")
        print("\n3. Run verification tests:")
        print("   python verify_deployment.py")
    
    print("\n📊 Expected test results:")
    print("   - Health check: 200 OK")
    print("   - Maria test: Routes to Maria (score 0-4)")
    print("   - Carlos test: Routes to Carlos (score 5-7)")
    print("   - Sofia test: Routes to Sofia (score 8-10)")
    print("   - Command routing: Proper handoffs")


def check_deployment_readiness():
    """Check if we can detect deployment readiness"""
    print("\n🔍 Checking Deployment Readiness")
    print("=" * 60)
    
    # Check if we have a deployment URL in environment or config
    import os
    
    possible_urls = [
        os.getenv("LANGGRAPH_DEPLOYMENT_URL"),
        os.getenv("DEPLOYMENT_URL"),
    ]
    
    for url in possible_urls:
        if url:
            print(f"✅ Found deployment URL: {url}")
            return url
    
    print("⏳ No deployment URL found in environment")
    print("   Waiting for deployment to complete...")
    return None


def main():
    """Main monitoring flow"""
    print("🚀 LangGraph Deployment Monitor")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: Check GitHub Actions
    check_github_actions()
    
    # Step 2: Guide to LangSmith
    check_langsmith_deployments()
    
    # Step 3: Check if deployment is ready
    deployment_url = check_deployment_readiness()
    
    # Step 4: Update verification script if URL available
    if not deployment_url:
        print("\n⏳ Waiting for deployment to complete...")
        print("   This typically takes 5-10 minutes")
        deployment_url = update_verify_script()
    
    # Step 5: Show next steps
    show_next_steps(deployment_url)
    
    print("\n" + "=" * 60)
    print("📌 Deployment Checklist:")
    print("   [ ] GitHub Actions workflow completed")
    print("   [ ] Deployment URL obtained")
    print("   [ ] verify_deployment.py updated")
    print("   [ ] Verification tests passed")
    print("   [ ] LangSmith traces look good")
    
    print(f"\n🕐 Monitoring completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()