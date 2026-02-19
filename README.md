# Multi-Agent Coding Assistant

A powerful AI-powered coding assistant that understands your codebase using RAG (Retrieval-Augmented Generation) and deploys specialized agents for different tasks.

## Features

- **RAG-Powered Code Understanding**: Indexes your codebase for semantic search
- **Multi-Agent Architecture**: Specialized agents for research, implementation, testing, and code review
- **Multi-Provider Support**: Works with Claude, GPT-4, or local models via Ollama
- **LangGraph Orchestration**: Intelligent task routing and agent coordination
- **Interactive CLI**: Easy-to-use command-line interface

## Quick Start

### Option 1: pip install

```bash
# Clone the repository
git clone https://github.com/yourusername/coding-assistant.git
cd coding-assistant

# Install with your preferred provider
pip install -e ".[anthropic]"   # For Claude
pip install -e ".[openai]"      # For GPT-4
pip install -e ".[ollama]"      # For local models
pip install -e ".[all]"         # For all providers

# Configure
cp .env.example .env
# Edit .env with your API key

# Index your codebase
assistant index /path/to/your/codebase

# Start chatting!
assistant chat
```

### Option 2: Docker

```bash
# Clone and configure
git clone https://github.com/yourusername/coding-assistant.git
cd coding-assistant
cp .env.example .env
# Edit .env with your API key

# Build and run
docker-compose up -d

# Index a codebase
docker exec -it coding-assistant assistant index /app/codebase

# Interactive chat
docker exec -it coding-assistant assistant chat
```

## Configuration

### LLM Providers

| Provider | Models | Setup |
|----------|--------|-------|
| **Anthropic** | claude-sonnet-4, claude-opus-4 | Set `ANTHROPIC_API_KEY` |
| **OpenAI** | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | Set `OPENAI_API_KEY` |
| **Ollama** | llama3, mistral, codellama | Run Ollama locally |

### Embedding Providers

| Provider | Models | Notes |
|----------|--------|-------|
| **HuggingFace** | all-MiniLM-L6-v2 | Free, runs locally (default) |
| **OpenAI** | text-embedding-3-small | Requires API key |
| **Ollama** | nomic-embed-text | Local, requires Ollama |

### Environment Variables

```bash
# Provider selection
LLM_PROVIDER=anthropic          # anthropic, openai, ollama
MODEL_NAME=claude-sonnet-4-20250514

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

# Embeddings
EMBEDDING_PROVIDER=huggingface  # huggingface, openai, ollama
EMBEDDING_MODEL=                # Leave empty for default

# Performance tuning
CHUNK_SIZE=1500
CHUNK_OVERLAP=200
MAX_TOKENS=4096

# Permissions
PERMISSION_MODE=ask             # full, readonly, ask
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `assistant index <path>` | Index a codebase for semantic search |
| `assistant ask <question>` | Ask questions about the codebase |
| `assistant implement <desc>` | Implement features (`--tests`, `--review`) |
| `assistant test <target>` | Generate or run tests |
| `assistant review <target>` | Code review (`--security`, `--performance`) |
| `assistant chat` | Interactive chat session |
| `assistant status` | Show configuration status |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                    │
│            (Routes tasks to specialized agents)          │
└─────────────────┬───────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    ▼             ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐
│Research│  │Implement │  │ Testing │  │  Review  │
│ Agent  │  │  Agent   │  │  Agent  │  │  Agent   │
└────────┘  └──────────┘  └─────────┘  └──────────┘
    │             │             │             │
    └─────────────┴─────────────┴─────────────┘
                        │
              ┌─────────▼─────────┐
              │   Codebase RAG    │
              │     (ChromaDB)    │
              └───────────────────┘
```

### Agents

| Agent | Trigger Keywords | Capabilities |
|-------|------------------|--------------|
| **Research** | "find", "where", "how does", "explain" | Semantic search, code tracing, pattern analysis |
| **Implementation** | "implement", "add", "fix", "create" | Write code, edit files, refactor |
| **Testing** | "test", "verify", "coverage" | Generate tests, run tests, coverage analysis |
| **Review** | "review", "check", "security" | Code review, security audit, performance analysis |

## Examples

```bash
# Ask about your codebase
assistant ask "Where is the authentication logic?"
assistant ask "How does the database connection work?"

# Implement features
assistant implement "Add input validation to the user form"
assistant implement "Create a REST endpoint for user profiles" --tests

# Generate tests
assistant test "src/services/auth.py"
assistant test --generate "the login function"

# Code review
assistant review "src/api/handlers.py"
assistant review "src/" --security

# Interactive session
assistant chat
```

## Using with Ollama (Local Models)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3
ollama pull nomic-embed-text

# Configure
export LLM_PROVIDER=ollama
export EMBEDDING_PROVIDER=ollama
export MODEL_NAME=llama3

# Run
assistant chat
```

## Performance Tuning

| Setting | Description | Default | Recommendation |
|---------|-------------|---------|----------------|
| `CHUNK_SIZE` | Characters per code chunk | 1500 | Increase for more context |
| `CHUNK_OVERLAP` | Overlap between chunks | 200 | Increase for better continuity |
| `MAX_TOKENS` | Max response tokens | 4096 | Increase for longer responses |
| `MAX_RESULTS` | Search results per query | 5 | Increase for more context |

## Development

```bash
# Install dev dependencies
poetry install --with dev

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/
```

## License

MIT License - See [LICENSE](LICENSE) for details.
