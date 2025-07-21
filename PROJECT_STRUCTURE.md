# Project Structure - LangGraph GHL Agent

## Core Files (Root Directory)
- `app.py` - Main FastAPI application
- `Makefile` - Build and deployment commands
- `requirements.txt` - Python dependencies
- `langgraph.json` - LangGraph deployment configuration
- `.env` - Environment variables (not in git)
- `.gitignore` - Git ignore rules
- `validate_workflow.py` - Pre-deployment validation

## Core Directories
```
app/
├── agents/           # Agent implementations (Maria, Carlos, Sofia, Supervisor)
├── api/             # API endpoints and webhook handlers
├── debug/           # Debug utilities and trace collection
├── intelligence/    # Lead scoring and analysis
├── prompts/         # Agent prompt templates
├── state/           # State management and schemas
├── tools/           # Agent tools and integrations
├── utils/           # Utility functions
└── workflow*.py     # Workflow implementations

tests/               # Test suite
templates/           # HTML templates
static/             # Static assets
backup_analysis_scripts_20250721/  # Archived debug/analysis scripts
```

## Key Documentation
- `README.md` - Project overview and setup
- `CLAUDE.md` - Context for Claude AI assistant
- `DEPLOYMENT_READY.md` - Deployment checklist
- `LANGGRAPH_BEST_PRACTICES_IMPLEMENTATION.md` - Best practices guide
- `PROJECT_STRUCTURE.md` - This file

## What Was Cleaned Up
Over 130 analysis, debug, and test scripts were moved to `backup_analysis_scripts_20250721/` including:
- Analysis scripts (`analyze_*.py`)
- Debug utilities (`debug_*.py`) 
- Trace fetchers (`fetch_*.py`)
- Test scripts (`test_*.py`)
- Old documentation (`*_FIX.md`, `*_ANALYSIS.md`)
- Trace JSON files
- Test results

The project is now clean and production-ready with only essential files remaining.