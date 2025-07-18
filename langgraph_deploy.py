#!/usr/bin/env python3
"""
LangGraph Platform Deployment Helper

This script provides utilities for deploying and managing LangGraph applications
using the LangGraph CLI and API.
"""

import os
import subprocess
import json
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path
import time
from datetime import datetime


class LangGraphDeployment:
    """Manage LangGraph Platform deployments"""
    
    def __init__(self, project_dir: Optional[str] = None):
        """
        Initialize deployment manager
        
        Args:
            project_dir: Project directory (defaults to current directory)
        """
        self.project_dir = Path(project_dir or os.getcwd())
        self.config_file = self.project_dir / "langgraph.json"
        
        # Check if langgraph.json exists
        if not self.config_file.exists():
            raise FileNotFoundError(f"langgraph.json not found in {self.project_dir}")
        
        # Load configuration
        with open(self.config_file) as f:
            self.config = json.load(f)
        
        self.project_name = self.config.get("name", "unnamed-project")
        print(f"Loaded project: {self.project_name}")
    
    def check_cli_installed(self) -> bool:
        """Check if langchain-cli is installed"""
        try:
            result = subprocess.run(
                ["pip", "show", "langchain-cli"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def install_cli(self):
        """Install langchain-cli if not present"""
        if not self.check_cli_installed():
            print("Installing langchain-cli...")
            subprocess.run([sys.executable, "-m", "pip", "install", "langchain-cli"])
        else:
            print("langchain-cli is already installed")
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate langgraph.json configuration"""
        required_fields = ["name", "version", "entry_point", "graphs"]
        missing_fields = []
        
        for field in required_fields:
            if field not in self.config:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "valid": False,
                "errors": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        # Check if entry point exists
        entry_point = self.project_dir / self.config["entry_point"]
        if not entry_point.exists():
            return {
                "valid": False,
                "errors": f"Entry point not found: {self.config['entry_point']}"
            }
        
        return {"valid": True, "config": self.config}
    
    def run_local_server(self, port: int = 8000, verbose: bool = True):
        """
        Run LangGraph server locally for testing
        
        Args:
            port: Port to run server on
            verbose: Show verbose output
        """
        print(f"Starting local LangGraph server on port {port}...")
        
        # Set required environment variables
        env = os.environ.copy()
        if not env.get("LANGCHAIN_API_KEY"):
            print("Warning: LANGCHAIN_API_KEY not set. Server may not start properly.")
        
        cmd = ["langgraph", "up", "--port", str(port)]
        if verbose:
            cmd.append("--verbose")
        
        try:
            # Run server
            process = subprocess.Popen(
                cmd,
                cwd=self.project_dir,
                env=env
            )
            
            print(f"\nServer running at http://localhost:{port}")
            print("Press Ctrl+C to stop\n")
            
            # Wait for interrupt
            process.wait()
            
        except KeyboardInterrupt:
            print("\nStopping server...")
            process.terminate()
            process.wait()
        except Exception as e:
            print(f"Error running server: {e}")
    
    def build_docker_image(self, tag: Optional[str] = None) -> bool:
        """
        Build Docker image for deployment
        
        Args:
            tag: Docker image tag (defaults to project name)
        """
        tag = tag or f"{self.project_name}:latest"
        
        print(f"Building Docker image: {tag}")
        
        # Create Dockerfile if it doesn't exist
        dockerfile_path = self.project_dir / "Dockerfile"
        if not dockerfile_path.exists():
            self._create_dockerfile()
        
        # Build image
        cmd = ["docker", "build", "-t", tag, "."]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"Successfully built image: {tag}")
                return True
            else:
                print(f"Build failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error building image: {e}")
            return False
    
    def _create_dockerfile(self):
        """Create a Dockerfile for LangGraph deployment"""
        dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install langchain-cli
RUN pip install langchain-cli

# Expose port
EXPOSE 8000

# Run LangGraph server
CMD ["langgraph", "up", "--host", "0.0.0.0", "--port", "8000"]
"""
        
        with open(self.project_dir / "Dockerfile", "w") as f:
            f.write(dockerfile_content)
        
        print("Created Dockerfile for LangGraph deployment")
    
    def deploy_to_platform(self, environment: str = "production") -> Dict[str, Any]:
        """
        Deploy to LangGraph Platform
        
        Args:
            environment: Deployment environment
        """
        print(f"Deploying to LangGraph Platform ({environment})...")
        
        # This would typically use the LangGraph Platform API
        # For now, we'll simulate the deployment process
        
        deployment_info = {
            "project": self.project_name,
            "version": self.config.get("version", "1.0.0"),
            "environment": environment,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # In a real deployment, this would:
        # 1. Package the application
        # 2. Upload to LangGraph Platform
        # 3. Trigger deployment
        # 4. Monitor deployment status
        
        print("Deployment initiated. Use 'langsmith_monitor.py' to track progress.")
        
        return deployment_info
    
    def test_deployment(self, url: str) -> bool:
        """
        Test a deployed LangGraph application
        
        Args:
            url: Deployment URL to test
        """
        import requests
        
        print(f"Testing deployment at {url}...")
        
        try:
            # Test health endpoint
            response = requests.get(f"{url}/health", timeout=10)
            
            if response.status_code == 200:
                print("✓ Health check passed")
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False
            
            # Test API info endpoint
            response = requests.get(f"{url}/info", timeout=10)
            
            if response.status_code == 200:
                info = response.json()
                print(f"✓ API info: {json.dumps(info, indent=2)}")
            else:
                print(f"✗ API info failed: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            return False
    
    def generate_deployment_script(self, output_file: str = "deploy.sh"):
        """Generate a deployment script"""
        script_content = f"""#!/bin/bash
# Auto-generated deployment script for {self.project_name}

set -e

echo "Deploying {self.project_name}..."

# Validate configuration
echo "Validating langgraph.json..."
python -c "import json; json.load(open('langgraph.json'))"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install langchain-cli

# Run tests (if they exist)
if [ -f "test_deployment.py" ]; then
    echo "Running deployment tests..."
    python test_deployment.py
fi

# Build Docker image
echo "Building Docker image..."
docker build -t {self.project_name}:latest .

# Deploy to platform
echo "Deploying to LangGraph Platform..."
# Add your deployment commands here

echo "Deployment complete!"
"""
        
        script_path = self.project_dir / output_file
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        print(f"Generated deployment script: {output_file}")


def main():
    """CLI interface for LangGraph deployment"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LangGraph Platform Deployment Helper")
    parser.add_argument("--project-dir", help="Project directory (defaults to current)")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Validate command
    subparsers.add_parser("validate", help="Validate langgraph.json configuration")
    
    # Install CLI command
    subparsers.add_parser("install-cli", help="Install langchain-cli")
    
    # Local server command
    local_parser = subparsers.add_parser("local", help="Run local development server")
    local_parser.add_argument("--port", type=int, default=8000, help="Port to run on")
    local_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build Docker image")
    build_parser.add_argument("--tag", help="Docker image tag")
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy to LangGraph Platform")
    deploy_parser.add_argument("--env", default="production", help="Deployment environment")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test deployment")
    test_parser.add_argument("url", help="Deployment URL to test")
    
    # Generate script command
    script_parser = subparsers.add_parser("generate-script", help="Generate deployment script")
    script_parser.add_argument("--output", default="deploy.sh", help="Output filename")
    
    args = parser.parse_args()
    
    # Initialize deployment manager
    try:
        deployment = LangGraphDeployment(project_dir=args.project_dir)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Execute command
    if args.command == "validate":
        result = deployment.validate_config()
        if result["valid"]:
            print("✓ Configuration is valid")
            print(json.dumps(result["config"], indent=2))
        else:
            print(f"✗ Configuration invalid: {result['errors']}")
            sys.exit(1)
    
    elif args.command == "install-cli":
        deployment.install_cli()
    
    elif args.command == "local":
        deployment.run_local_server(port=args.port, verbose=args.verbose)
    
    elif args.command == "build":
        success = deployment.build_docker_image(tag=args.tag)
        sys.exit(0 if success else 1)
    
    elif args.command == "deploy":
        info = deployment.deploy_to_platform(environment=args.env)
        print(json.dumps(info, indent=2))
    
    elif args.command == "test":
        success = deployment.test_deployment(args.url)
        sys.exit(0 if success else 1)
    
    elif args.command == "generate-script":
        deployment.generate_deployment_script(output_file=args.output)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()