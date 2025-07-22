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

## 🙏 Acknowledgments

- Built with [LangGraph](https://langchain-ai.github.io/langgraph/)
- Powered by [OpenAI](https://openai.com/)
- Integrated with [GoHighLevel](https://www.gohighlevel.com/)