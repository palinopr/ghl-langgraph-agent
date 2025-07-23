# GoHighLevel LangGraph Messaging Agent

A production-ready multi-agent system built with LangGraph v0.5.3+ for intelligent WhatsApp/SMS conversation handling in GoHighLevel. Features deterministic lead scoring, Spanish language support, and appointment booking capabilities.

## 🚀 Key Features

- **Multi-Agent Architecture**: Three specialized agents (Maria, Carlos, Sofia) handle different lead stages
- **Intelligent Lead Scoring**: Deterministic 1-10 scoring based on extracted information
- **Spanish Language Support**: Native Spanish conversation handling with typo tolerance
- **Appointment Booking**: Integrated calendar management with GHL
- **Human-Like Responses**: Natural typing delays and message batching
- **Production Ready**: Comprehensive error handling, monitoring, and validation
- **Performance Optimized**: Python 3.13 with GIL-free mode and JIT compilation
- **Advanced Debugging**: Built-in tools for trace analysis and message deduplication

## 🏗️ Architecture Overview

```
WhatsApp/SMS → GHL → Webhook → Intelligence → Supervisor → Agent → Response
```

- **Intelligence Layer**: Extracts Spanish patterns and scores leads (1-10)
- **Supervisor**: Routes based on score using deterministic rules
- **Agents**: 
  - Maria (0-4): Initial contact and qualification
  - Carlos (5-7): Value proposition and budget confirmation
  - Sofia (8-10): Appointment booking and closing

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## 🚀 Quick Start

### Prerequisites

- Python 3.13.5 (required for performance features)
- GoHighLevel API credentials
- OpenAI API key

### Installation

```bash
# Clone repository
git clone <repository-url>
cd langgraph-ghl-agent

# Setup Python environment
python3.13 -m venv venv_langgraph
source venv_langgraph/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Validate setup
make validate
```

### Quick Test

```bash
# Start development server
make run

# Test webhook
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{"contactId": "test123", "message": "Hola, tengo un restaurante"}'
```

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment instructions
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and components
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Local development and debugging
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and fixes

## 🔧 Key Commands

```bash
make validate   # Pre-deployment validation (5 seconds)
make test      # Run test suite
make run       # Start development server
make deploy    # Deploy to production
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run validation (`make validate`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🔍 Debugging & Monitoring

### Debug Tools

The system includes built-in debugging tools to quickly identify and fix issues:

```bash
# Analyze a specific trace
python analyze_trace.py 1f067756-c282-640a-85ed-56c1478cd894 --verbose

# Monitor traces in real-time
python monitor_traces.py

# Debug message duplication
python debug_message_duplication.py
```

### Common Issues

1. **Message Duplication**: Use `MessageManager.set_messages()` in all nodes
2. **Dict vs BaseMessage**: MessageManager handles format normalization
3. **Error Accumulation**: Error messages are deduplicated automatically

### Debug Helpers

```python
from app.utils.debug_helpers import log_state_transition, validate_state

# In your node:
log_state_transition(state, "node_name", "input")
validation = validate_state(state, "node_name")
```

See [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md) for comprehensive debugging practices.

## 🙏 Acknowledgments

- Built with [LangGraph](https://langchain-ai.github.io/langgraph/)
- Powered by [OpenAI](https://openai.com/)
- Integrated with [GoHighLevel](https://www.gohighlevel.com/)