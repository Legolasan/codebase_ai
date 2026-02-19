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
| `assistant chat --persona <name>` | Chat with a specific persona (mentor, senior, junior, pair) |
| `assistant status` | Show configuration status |

### Plugin Commands

| Command | Description |
|---------|-------------|
| `assistant plugins list` | Show all available plugins |
| `assistant plugins enable <name>` | Enable a plugin |
| `assistant plugins disable <name>` | Disable a plugin |
| `assistant plugins status` | Show enabled plugins |

### Git Workflow Commands (requires `git_workflow` plugin)

| Command | Description |
|---------|-------------|
| `assistant git status` | Show git workflow status |
| `assistant git branch <desc>` | Create a feature branch from description |
| `assistant git branch <desc> --type <type>` | Create branch with specific type (feature, fix, refactor, docs) |
| `assistant git prepare <task>` | Prepare git environment for implementation |

### Security Commands (requires `security_scanner` plugin)

| Command | Description |
|---------|-------------|
| `assistant security scan [path]` | Scan for security issues |
| `assistant security scan --secrets-only` | Scan for secrets only |
| `assistant security scan --malware-only` | Scan for malware only |
| `assistant security scan --vulns-only` | Scan for vulnerabilities only |
| `assistant security report [-o file]` | Generate detailed report |
| `assistant security status` | Show scanner configuration |
| `assistant security auto-scan --enable/--disable` | Toggle auto-scan on index |

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

#### 5. Persona (`persona`)

Role-based personas for customizing assistant behavior and communication style.

```bash
# Enable the plugin
assistant plugins enable persona

# Start chat with a persona
assistant chat --persona mentor    # Teaching-focused
assistant chat --persona senior    # Expert, efficient
assistant chat --persona junior    # Curious, cautious
assistant chat --persona pair      # Collaborative pair programmer

# Default behavior (no persona)
assistant chat
```

**Available Personas:**

| Persona | Emoji | Description | Communication Style |
|---------|-------|-------------|---------------------|
| **mentor** | 🎓 | Teaching-focused | Breaks down problems, explains "why", encourages learning |
| **senior** | 👨‍💻 | Expert developer | Direct, efficient, shares best practices and patterns |
| **junior** | 🌱 | Learning alongside | Asks clarifying questions, cautious, confirms understanding |
| **pair** | 👥 | Pair programmer | Thinks aloud, collaborative, suggests refactors together |

**Features:**
- Modifies assistant's communication style
- Persists for the entire chat session
- Shown in the welcome panel header
- No external dependencies

#### 6. Security Scanner (`security_scanner`)

Proactively detect security threats in your codebase including secrets, malware, and vulnerabilities.

```bash
# Enable the plugin
assistant plugins enable security_scanner

# Scan current directory
assistant security scan

# Scan specific path
assistant security scan /path/to/code

# Scan for specific issues only
assistant security scan --secrets-only
assistant security scan --malware-only
assistant security scan --vulns-only

# Generate detailed report
assistant security report
assistant security report --output security-report.md

# Configure auto-scan on index
assistant security auto-scan --enable
assistant security auto-scan --disable

# Show scanner status
assistant security status
```

**Detection Capabilities:**

| Category | Patterns | Examples |
|----------|----------|----------|
| **Secrets** | 14 patterns | AWS keys, GitHub tokens, API keys, private keys, passwords, JWT secrets, database URLs, Slack/Stripe/Google tokens |
| **Malware** | 8 patterns | Reverse shells, crypto miners, data exfiltration, keyloggers, obfuscated code, backdoors |
| **Vulnerabilities** | 15 patterns | SQL injection, command injection, XSS, path traversal, insecure deserialization, weak crypto, debug mode |

**Features:**
- Automatic scanning after `assistant index` (configurable)
- Agent tool for security reviews
- Severity levels: CRITICAL, HIGH, MEDIUM, LOW, INFO
- Markdown report generation
- Skip test files for certain patterns

#### 7. Git Workflow (`git_workflow`)

Enforces proper git branching workflow for code changes. Automatically creates feature branches before any implementation.

```bash
# Enable the plugin
assistant plugins enable git_workflow

# Check workflow status
assistant git status

# Manually create a feature branch
assistant git branch "add user authentication"
assistant git branch "fix login bug" --type fix
assistant git branch "improve performance" --type refactor

# Prepare for implementation (creates branch if needed)
assistant git prepare "add new API endpoint"
```

**Automatic Branching:**

When enabled, the implementation agent automatically creates feature branches before making any code changes:

```bash
# This automatically creates feature/add-login-page branch
assistant implement "add login page"

# This automatically creates fix/broken-validation branch
assistant implement "fix broken validation"
```

**Branch Naming Convention:**

| Prefix | Usage | Example |
|--------|-------|---------|
| `feature/` | New features | `feature/add-user-auth` |
| `fix/` | Bug fixes | `fix/login-validation` |
| `refactor/` | Code refactoring | `refactor/auth-module` |
| `docs/` | Documentation | `docs/update-readme` |

**Features:**
- Auto-detects branch type from task description
- Slugifies descriptions into valid branch names
- Checks if already on a feature branch (skips creation)
- Provides git workflow tools to agents
- No external dependencies

### Plugin Configuration

Plugin settings are stored in `~/.assistant/plugins.json`:

```json
{
  "enabled": ["multi_dir", "rag_guardrails", "persona", "security_scanner", "git_workflow"],
  "multi_dir": {
    "unified_collection": "multi_codebase"
  },
  "rag_guardrails": {
    "strict_mode": false,
    "show_verification": true
  },
  "security_scanner": {
    "auto_scan_on_index": true,
    "scan_secrets": true,
    "scan_malware": true,
    "scan_vulnerabilities": true
  },
  "git_workflow": {
    "auto_branch": true,
    "require_feature_branch": true
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

# Chat with different personas (with persona plugin enabled)
assistant chat --persona mentor   # Great for learning new concepts
assistant chat --persona senior   # Quick, expert answers
assistant chat --persona pair     # Collaborative coding

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
