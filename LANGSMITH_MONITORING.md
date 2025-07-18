# LangSmith Monitoring and Deployment Guide

This guide provides comprehensive information about using LangSmith CLI and API for monitoring LangGraph Platform deployments.

## Overview

LangSmith provides powerful monitoring and debugging capabilities for LangGraph applications. This includes:
- Real-time deployment metrics
- Log aggregation and analysis
- Trace visualization
- Performance monitoring
- Error tracking

## Prerequisites

1. **LangSmith Account**: You need a LangSmith account with API access
2. **API Key**: Set up your `LANGCHAIN_API_KEY` environment variable
3. **Python SDK**: Install with `pip install langsmith`

## Configuration

Your project already has LangSmith configured in `src/config.py`:

```python
# LangSmith configuration
langchain_tracing_v2: bool = True
langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
langchain_project: str = Field(default="ghl-langgraph-migration", env="LANGCHAIN_PROJECT")
```

## Using the LangSmith Monitor Script

The `langsmith_monitor.py` script provides programmatic access to deployment monitoring:

### Installation

```bash
# Ensure langsmith is installed
pip install langsmith
```

### Available Commands

1. **List Projects**
   ```bash
   python langsmith_monitor.py list-projects
   ```

2. **View Deployment Metrics**
   ```bash
   python langsmith_monitor.py metrics --hours 24
   ```

3. **Live Monitoring**
   ```bash
   python langsmith_monitor.py monitor --interval 60
   ```

4. **Export Logs**
   ```bash
   python langsmith_monitor.py export --hours 24 --output logs.json
   ```

5. **View Recent Runs**
   ```bash
   python langsmith_monitor.py runs --hours 1 --limit 20
   ```

### Programmatic Usage

```python
from langsmith_monitor import LangSmithMonitor

# Initialize monitor
monitor = LangSmithMonitor()

# Get deployment metrics
metrics = monitor.get_deployment_metrics(hours=24)
print(f"Success rate: {metrics['success_rate']}%")
print(f"Average latency: {metrics['average_latency_seconds']}s")

# Get recent runs
runs = monitor.get_recent_runs(hours=1)
for run in runs:
    print(f"{run.name} - Status: {run.status}")

# Export logs
monitor.export_logs(hours=24, output_file="deployment_logs.json")
```

## Using the LangGraph Deployment Script

The `langgraph_deploy.py` script helps manage LangGraph deployments:

### Available Commands

1. **Validate Configuration**
   ```bash
   python langgraph_deploy.py validate
   ```

2. **Install LangChain CLI**
   ```bash
   python langgraph_deploy.py install-cli
   ```

3. **Run Local Server**
   ```bash
   python langgraph_deploy.py local --port 8000 --verbose
   ```

4. **Build Docker Image**
   ```bash
   python langgraph_deploy.py build --tag my-langgraph-app:latest
   ```

5. **Deploy to Platform**
   ```bash
   python langgraph_deploy.py deploy --env production
   ```

6. **Test Deployment**
   ```bash
   python langgraph_deploy.py test https://my-deployment.langgraph.com
   ```

7. **Generate Deployment Script**
   ```bash
   python langgraph_deploy.py generate-script
   ```

## LangSmith Web UI Features

Access the LangSmith web UI at https://smith.langchain.com to:

1. **View Deployment Metrics**
   - Navigate to LangGraph Platform → Select deployment → Monitoring tab
   - View CPU & memory usage
   - Monitor API request latency
   - Track pending/active run counts

2. **Trace Analysis**
   - Full visibility into input/output of each step
   - Execution path visualization
   - State transition tracking
   - Performance profiling

3. **Error Debugging**
   - Detailed error logs
   - Stack traces
   - Input data that caused errors
   - Reproduction capabilities

## LangGraph CLI Commands

The LangGraph CLI (installed via `pip install langchain-cli`) provides:

### Development Server
```bash
# Start development server with hot reloading
langgraph dev

# Run with verbose logging
langgraph up --verbose --port 8000
```

### Building and Deployment
```bash
# Build Docker image
langgraph build

# Deploy to LangGraph Platform
langgraph deploy --env production
```

## API Integration

### Using LangSmith SDK

```python
from langsmith import Client

client = Client()

# List runs
runs = client.list_runs(
    project_name="ghl-langgraph-migration",
    start_time=datetime.now() - timedelta(hours=24)
)

# Get run details
run = client.read_run(run_id)
print(f"Status: {run.status}")
print(f"Latency: {(run.end_time - run.start_time).total_seconds()}s")
```

### REST API Access

```python
import requests

headers = {
    "x-api-key": os.getenv("LANGCHAIN_API_KEY")
}

# Get project runs
response = requests.get(
    "https://api.smith.langchain.com/runs",
    headers=headers,
    params={"project_name": "ghl-langgraph-migration"}
)
```

## Monitoring Best Practices

1. **Set Up Alerts**
   - Configure alerts for high error rates
   - Monitor latency thresholds
   - Track resource usage

2. **Regular Log Reviews**
   - Export logs daily for analysis
   - Look for patterns in errors
   - Monitor performance trends

3. **Use Tracing**
   - Enable tracing for all production runs
   - Use trace data for debugging
   - Analyze execution paths

4. **Performance Optimization**
   - Monitor average latencies
   - Identify slow operations
   - Optimize based on trace data

## Troubleshooting

### Common Issues

1. **No traces appearing**
   - Ensure `LANGCHAIN_TRACING_V2=true`
   - Verify `LANGCHAIN_API_KEY` is set
   - Check `LANGCHAIN_PROJECT` matches

2. **CLI not found**
   - Install with `pip install langchain-cli`
   - Ensure it's in your PATH

3. **Authentication errors**
   - Verify API key is valid
   - Check key has proper permissions
   - Ensure correct workspace selected

## Additional Resources

- [LangSmith Documentation](https://docs.smith.langchain.com)
- [LangGraph Platform Guide](https://langchain-ai.github.io/langgraph/concepts/langgraph_platform/)
- [LangGraph CLI Reference](https://langchain-ai.github.io/langgraph/cloud/reference/cli/)
- [LangSmith Python SDK](https://docs.smith.langchain.com/reference/python/reference)