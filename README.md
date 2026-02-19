# Multi-Agent Coding Assistant

A powerful AI-powered coding assistant that understands your codebase using RAG (Retrieval-Augmented Generation) and deploys specialized agents for different tasks.

## Features

- **RAG-Powered Code Understanding**: Indexes your codebase for semantic search
- **Multi-Agent Architecture**: Specialized agents for research, implementation, testing, code review, and PRD generation
- **Multi-Provider Support**: Works with Claude, GPT-4, or local models via Ollama
- **LangGraph Orchestration**: Intelligent task routing and agent coordination
- **Plugin System**: Extend functionality with optional plugins
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

### Core Commands

| Command | Description |
|---------|-------------|
| `assistant index <path>` | Index a codebase for semantic search |
| `assistant ask <question>` | Ask questions about the codebase |
| `assistant implement <desc>` | Implement features (`--tests`, `--review`) |
| `assistant test <target>` | Generate or run tests |
| `assistant review <target>` | Code review (`--security`, `--performance`) |
| `assistant prd <description>` | Generate a Product Requirements Document |
| `assistant chat` | Interactive chat session |
| `assistant status` | Show configuration status |

### Plugin Commands

| Command | Description |
|---------|-------------|
| `assistant plugins list` | Show all available plugins |
| `assistant plugins enable <name>` | Enable a plugin |
| `assistant plugins disable <name>` | Disable a plugin |
| `assistant plugins status` | Show enabled plugins |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                    │
│            (Routes tasks to specialized agents)          │
└─────────────────┬───────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┬───────────┐
    ▼             ▼             ▼             ▼           ▼
┌────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌─────┐
│Research│  │Implement │  │ Testing │  │  Review  │  │ PRD │
│ Agent  │  │  Agent   │  │  Agent  │  │  Agent   │  │Agent│
└────────┘  └──────────┘  └─────────┘  └──────────┘  └─────┘
    │             │             │             │           │
    └─────────────┴─────────────┴─────────────┴───────────┘
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
| **PRD** | "prd", "requirements", "spec" | Generate comprehensive Product Requirements Documents |

## Plugin System

The assistant supports an extensible plugin architecture. Plugins are stored in `~/.assistant/` and persist across sessions.

### Available Plugins

#### 1. Multi-Directory Support (`multi_dir`)

Index and search across multiple codebases with unified search.

```bash
# Enable the plugin
assistant plugins enable multi_dir

# Add directories
assistant add-dir /path/to/frontend --alias "frontend"
assistant add-dir /path/to/backend --alias "backend"

# List configured directories
assistant list-dirs

# Remove a directory
assistant remove-dir "frontend"

# Re-index all directories
assistant reindex
```

**Features:**
- Unified indexing with source metadata
- Filter searches by source directory
- Persistent configuration in `~/.assistant/directories.json`

#### 2. GitHub Authentication (`github_auth`)

Secure GitHub authentication with multiple strategies.

```bash
# Enable the plugin
assistant plugins enable github_auth

# Store token securely (uses system keyring)
assistant auth github --set

# Check authentication status
assistant auth github --status

# Test authentication
assistant auth github --test

# Remove stored token
assistant auth github --remove
```

**Auth Strategies (tried in order):**
1. `GITHUB_TOKEN` environment variable
2. System keyring (encrypted by OS)
3. GitHub CLI (`gh auth token`)

**Additional Git Tools:**
- `git_clone` - Clone repositories (including private)
- `git_push` - Push to remote
- `git_pull` - Pull from remote
- `gh_create_pr` - Create pull requests
- `gh_create_issue` - Create issues

#### 3. RAG Guardrails (`rag_guardrails`)

Anti-hallucination protection that grounds responses in the indexed codebase.

```bash
# Enable the plugin
assistant plugins enable rag_guardrails

# Enable strict mode (blocks unverified claims)
assistant guardrails --strict

# Disable strict mode (shows warnings only)
assistant guardrails --no-strict

# Show/hide verification in output
assistant guardrails --show
assistant guardrails --hide

# Check current configuration
assistant guardrails --status
```

**Features:**
- Extracts verifiable claims (file paths, function names, code snippets)
- Verifies claims against indexed codebase
- Warning mode: Shows warnings for unverified claims
- Strict mode: Blocks responses with unverified claims
- System prompt injection for grounding

#### 4. Context7 MCP Integration (`context7`)

Deep library research via Context7's Model Context Protocol.

```bash
# Enable the plugin
assistant plugins enable context7

# Set API key
export CONTEXT7_API_KEY=your-key

# Check status
assistant context7 --status

# Look up library documentation
assistant context7 --lookup react --topic hooks
```

**Features:**
- Up-to-date library documentation lookup
- Competitor research for PRD generation
- Library comparison across features
- Integrates with PRD agent for competitive analysis

**Requirements:**
- `CONTEXT7_API_KEY` environment variable
- Optional: `langchain-mcp-adapters` for full MCP support

### Plugin Configuration

Plugin settings are stored in `~/.assistant/plugins.json`:

```json
{
  "enabled": ["multi_dir", "rag_guardrails"],
  "multi_dir": {
    "unified_collection": "multi_codebase"
  },
  "rag_guardrails": {
    "strict_mode": false,
    "show_verification": true
  }
}
```

## PRD Generation

Generate comprehensive Product Requirements Documents with competitor research.

```bash
# Generate a PRD
assistant prd "Add OAuth authentication to the app"

# Generate PRD without web research
assistant prd "Add dark mode support" --no-research

# Implement from a PRD
assistant implement --from-prd docs/prd/oauth-authentication-2025-02-19.md
```

**PRD Sections:**
1. Problem Statement
2. Scope (In/Out of scope)
3. User Personas
4. Competitor Research
5. Parity Check
6. Functional Requirements
7. Non-Functional Requirements
8. Acceptance Criteria
9. Success Metrics

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

# Generate PRD
assistant prd "Add user notifications feature"

# Interactive session
assistant chat

# Multi-directory search (with plugin enabled)
assistant ask "How does auth work?" --all-dirs
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

## Optional Dependencies

```bash
# For GitHub auth plugin (secure token storage)
pip install keyring

# For Context7 MCP plugin (full MCP support)
pip install langchain-mcp-adapters
```

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
