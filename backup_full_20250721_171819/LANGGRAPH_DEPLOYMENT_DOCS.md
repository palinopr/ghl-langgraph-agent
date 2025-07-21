# Complete LangGraph Deployment Documentation

## Table of Contents
1. [Configuration File Structure](#configuration-file-structure)
2. [Reserved Names and Common Errors](#reserved-names-and-common-errors)
3. [Dependencies and Requirements](#dependencies-and-requirements)
4. [Deployment Types](#deployment-types)
5. [Environment Variables](#environment-variables)
6. [Troubleshooting Guide](#troubleshooting-guide)

---

## Configuration File Structure

### Basic langgraph.json Structure

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./app/workflow.py:workflow"
  },
  "env": ".env",
  "python_version": "3.11"
}
```

### Complete Configuration Options

```json
{
  // REQUIRED: Dependencies array
  "dependencies": [
    ".",                        // Local packages
    "./my_package",            // Directory with pyproject.toml/setup.py
    "langchain>=0.3.8"         // Python packages
  ],
  
  // REQUIRED: Graph definitions
  "graphs": {
    "agent": "./app/workflow.py:workflow",     // Path to compiled graph
    "dynamic": "./app/graph.py:make_graph"     // Function that returns graph
  },
  
  // Optional: Environment variables
  "env": ".env",                              // Path to .env file
  // OR inline:
  "env": {
    "OPENAI_API_KEY": "sk-...",
    "CUSTOM_VAR": "value"
  },
  
  // Python configuration
  "python_version": "3.11",                   // 3.11, 3.12, or 3.13
  "pip_config_file": "./pip.conf",            // Custom pip config
  "pip_installer": "auto",                    // "auto", "pip", or "uv"
  "keep_pkg_tools": false,                    // Keep pip/setuptools/wheel
  
  // Docker configuration
  "dockerfile_lines": [
    "RUN apt-get update && apt-get install -y libmagic1",
    "RUN pip install custom-package"
  ],
  "base_image": "langchain/langgraph-api",    // Custom base image
  "image_distro": "wolfi",                    // "debian" or "wolfi"
  
  // Checkpointer configuration
  "checkpointer": {
    "ttl": {
      "strategy": "delete",
      "sweep_interval_minutes": 10,
      "default_ttl": 43200                    // 30 days in minutes
    }
  },
  
  // Store configuration (semantic search)
  "store": {
    "index": {
      "embed": "openai:text-embedding-3-small",
      "dims": 1536,
      "fields": ["$"]                         // Fields to index
    },
    "ttl": {
      "refresh_on_read": true,
      "default_ttl": 1440,                    // 24 hours
      "sweep_interval_minutes": 60
    }
  },
  
  // HTTP server configuration
  "http": {
    "app": "./app/webapp.py:app",             // Custom FastAPI app
    "cors": {
      "allow_origins": ["*"],
      "allow_methods": ["*"],
      "allow_headers": ["*"]
    },
    "configurable_headers": {
      "include": ["x-user-id", "x-org-*"],
      "exclude": ["authorization"]
    },
    "disable_assistants": false,
    "disable_mcp": false,
    "disable_meta": false,
    "disable_runs": false,
    "disable_store": false,
    "disable_threads": false,
    "disable_ui": false,
    "disable_webhooks": false,
    "mount_prefix": "/api"
  },
  
  // Authentication configuration
  "auth": {
    "path": "./auth.py:auth",
    "openapi": {
      "securitySchemes": {
        "apiKeyAuth": {
          "type": "apiKey",
          "in": "header",
          "name": "X-API-Key"
        }
      },
      "security": [{ "apiKeyAuth": [] }]
    },
    "disable_studio_auth": false
  },
  
  // UI components (JavaScript only)
  "ui": {
    "agent": "./app/ui.tsx"
  },
  
  // Node.js configuration (JavaScript only)
  "node_version": "20"
}
```

---

## Reserved Names and Common Errors

### Reserved Package Names
The following names are **RESERVED** and cannot be used as directory names:
- `src` - Will cause: `ValueError: Package name 'src' used in local dep '.' is reserved`
- `lib`
- `bin`
- `dist`
- `build`
- `test`
- `tests`
- `docs`
- `scripts`
- `tools`
- `utils` (sometimes)

### Solution
Use alternative names like:
- `app` (recommended)
- `agent`
- `core`
- `backend`
- `service`
- `my_agent`
- Your project name

### Common Configuration Errors

1. **Wrong Graph Path Format**
   ```json
   // WRONG - Object notation
   "graphs": {
     "agent": {
       "path": "./app/workflow.py",
       "variable": "workflow"
     }
   }
   
   // CORRECT - String notation
   "graphs": {
     "agent": "./app/workflow.py:workflow"
   }
   ```

2. **Missing Workflow Export**
   ```python
   # app/workflow.py
   
   # WRONG - No export
   def create_workflow():
       graph = StateGraph(State)
       # ... build graph
       return graph.compile()
   
   # CORRECT - Export for LangGraph Platform
   def create_workflow():
       graph = StateGraph(State)
       # ... build graph
       return graph.compile()
   
   workflow = create_workflow()  # REQUIRED!
   ```

3. **Wrong Python Version**
   ```json
   // WRONG - Too old
   "python_version": "3.9"
   
   // CORRECT - Minimum 3.11
   "python_version": "3.11"
   ```

---

## Dependencies and Requirements

### Minimum Required Dependencies

```txt
# Core LangGraph (REQUIRED)
langgraph>=0.3.27
langchain>=0.3.8
langchain-core>=0.2.38

# For LangGraph Platform deployment
langgraph-sdk>=0.1.66
langgraph-checkpoint>=2.0.23
langsmith>=0.1.63

# Essential utilities
orjson>=3.9.7,<3.10.17
httpx>=0.25.0
tenacity>=8.0.0
cloudpickle>=3.0.0

# For production
uvicorn>=0.26.0
sse-starlette>=2.1.0,<2.2.0
uvloop>=0.18.0
httptools>=0.5.0
structlog>=24.1.0
```

### Version Compatibility Matrix

| Component | Minimum Version | Recommended Version |
|-----------|----------------|---------------------|
| Python | 3.11 | 3.11 |
| LangGraph | 0.3.27 | Latest 0.3.x |
| LangChain | 0.3.8 | Latest 0.3.x |
| Node.js | 20 | 20 |

### Common Missing Dependencies

```txt
# Often forgotten but required
pydantic-settings>=2.0.0  # For BaseSettings
python-dotenv>=1.0.0       # For .env loading
jsonschema-rs>=0.20.0      # For validation
```

---

## Deployment Types

### Development Deployment
- **Resources**: 1 CPU, 1 GB RAM
- **Scaling**: Up to 1 container
- **Database**: 10 GB disk, no backups
- **Use Case**: Testing and development
- **Limitations**: Preemptible compute, may be terminated

### Production Deployment
- **Resources**: 2 CPU, 2 GB RAM (can be increased)
- **Scaling**: Up to 10 containers
- **Database**: Autoscaling disk, automatic backups, multi-zone
- **Use Case**: Customer-facing production workloads
- **Note**: Deployment type is immutable after creation

---

## Environment Variables

### Required for LangGraph Platform

```bash
# Authentication
LANGCHAIN_API_KEY=lsv2_...           # From LangSmith
LANGSMITH_API_KEY=lsv2_...           # Same as above
LANGCHAIN_PROJECT=my-project         # Project name

# LLM Keys (as needed)
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Self-Hosted Deployments

```bash
# Database connections
POSTGRES_URI_CUSTOM=postgres://user:pass@host/db
REDIS_URI_CUSTOM=redis://host:6379/0

# Custom configuration
REDIS_KEY_PREFIX=myapp_
REDIS_CLUSTER=false
MOUNT_PREFIX=/api
LOG_JSON=true

# Authentication
LANGGRAPH_AUTH_TYPE=noop  # or langsmith
```

### Custom Application Variables

```bash
# Your app-specific variables
GHL_API_TOKEN=pit-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
WEBHOOK_SECRET=your-secret
```

---

## Troubleshooting Guide

### Build Errors

1. **"Package name 'src' is reserved"**
   - Solution: Rename `src/` to `app/` or another non-reserved name
   - Update all imports and langgraph.json paths

2. **"Python version 3.9 is not supported"**
   - Solution: Update to `"python_version": "3.11"` in langgraph.json

3. **"AttributeError: 'NoneType' object has no attribute 'split'"**
   - Problem: Wrong graph path format in langgraph.json
   - Solution: Use string format `"./app/workflow.py:workflow"`

4. **"ModuleNotFoundError: No module named 'pydantic_settings'"**
   - Solution: Add `pydantic-settings>=2.0.0` to requirements.txt

5. **"Cannot find workflow export"**
   - Solution: Add `workflow = create_workflow()` at end of workflow.py

### Runtime Errors

1. **Environment variables not loading**
   ```python
   # app/config.py
   from pathlib import Path
   from dotenv import load_dotenv
   
   # Fix: Only load .env if it exists
   env_file = Path(__file__).parent.parent / ".env"
   if env_file.exists():
       load_dotenv(env_file)
   ```

2. **Import errors in production**
   - Check relative imports use correct paths
   - Ensure all dependencies are in requirements.txt
   - Verify PYTHONPATH includes project root

3. **Webhook 404 errors**
   - Verify correct app is deployed (not test app)
   - Check graph name matches deployment
   - Confirm route paths are correct

### Deployment Issues

1. **Build fails on LangGraph Platform**
   - Check langgraph.json syntax
   - Verify all file paths exist
   - Ensure Python version is 3.11+
   - Confirm no reserved directory names

2. **Deployment stuck in BUILDING**
   - Check build logs for errors
   - Verify GitHub integration has access
   - Ensure secrets are properly set

3. **"Failed to pull image"**
   - Check base_image exists
   - Verify image_distro is valid
   - Ensure Docker registry access

### Best Practices

1. **Always test locally first**
   ```bash
   langgraph dev
   ```

2. **Validate configuration**
   ```bash
   langgraph dockerfile . --config langgraph.json
   ```

3. **Use version pinning**
   ```txt
   langgraph==0.3.27  # Pin to specific version
   ```

4. **Monitor deployments**
   - Check revision status regularly
   - Review build logs for warnings
   - Set up proper error tracking

5. **Handle secrets properly**
   - Never commit .env files
   - Use deployment platform's secret management
   - Rotate keys regularly

---

## Quick Reference

### File Structure
```
my-app/
├── app/                    # Main application code (NOT src!)
│   ├── __init__.py
│   ├── workflow.py         # Must export 'workflow'
│   ├── agents/
│   ├── tools/
│   └── config.py
├── langgraph.json          # Deployment configuration
├── requirements.txt        # Python dependencies
├── .env                    # Local environment variables
└── README.md
```

### Minimal langgraph.json
```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./app/workflow.py:workflow"
  },
  "python_version": "3.11"
}
```

### Deployment Command
```bash
# Local development
langgraph dev

# Build Docker image
langgraph dockerfile . --config langgraph.json

# Deploy (via platform UI or API)
git push origin main
```

---

## Additional Resources

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangSmith Platform](https://smith.langchain.com)
- [LangGraph Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)

## Support

For deployment issues:
- Email: support@langchain.dev
- GitHub Issues: https://github.com/langchain-ai/langgraph/issues