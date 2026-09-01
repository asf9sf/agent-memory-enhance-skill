# Agent Memory Enhance — MCP Server

> **Give any AI agent a long-term memory system in 3 minutes.**
>
> A Model Context Protocol (MCP) server that provides structured memory storage,
> three-layer funnel retrieval, and self-maintenance (merge + decay) for any MCP-compatible AI agent.

## Features

- **Structured Memory**: Each memory is a skill object with name, keywords, summary, triggers, importance (1-5)
- **Three-Layer Funnel Retrieval**: Semantic match (embedding/TF-IDF) → LLM relevance filter → Full content
- **Self-Maintenance**: Auto-merge similar memories (similarity >= 0.9), auto-forget low-importance stale memories (30+ days, importance < 3)
- **Zero External Dependencies**: SQLite storage, no external database required
- **Embedding Optional**: Uses OpenAI-compatible `/v1/embeddings` when configured, falls back to character bigram TF-IDF cosine similarity
- **Universal Compatibility**: Works with Claude Desktop, Cursor, TRAE, Windsurf, and any MCP client

## Quick Start

### 1. Install

```bash
pip install agent-memory-enhance
```

Or from source:

```bash
git clone https://github.com/asf9sf/agent-memory-enhance-skill.git
cd agent-memory-enhance-skill
pip install -e .
```

### 2. Configure

The server reads configuration from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_LLM_BASE_URL` | `http://localhost:1234/v1` | OpenAI-compatible API base URL |
| `MEMORY_LLM_API_KEY` | `no-key` | API key |
| `MEMORY_LLM_MODEL` | `local-model` | LLM model name |
| `MEMORY_EMBEDDING_MODEL` | `""` (empty = TF-IDF) | Embedding model name (optional) |
| `MEMORY_DB_PATH` | `./memory.db` | SQLite database path |
| `MEMORY_LLM_TIMEOUT` | `30` | LLM request timeout (seconds) |

Example:
```bash
export MEMORY_LLM_BASE_URL="http://localhost:1234/v1"
export MEMORY_LLM_MODEL="qwen2.5:7b"
export MEMORY_EMBEDDING_MODEL=""  # leave empty to use TF-IDF fallback
```

### 3. Connect to your Agent

#### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "agent_memory_enhance.server"],
      "env": {
        "MEMORY_LLM_BASE_URL": "http://localhost:1234/v1",
        "MEMORY_LLM_MODEL": "local-model"
      }
    }
  }
}
```

#### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "agent_memory_enhance.server"],
      "env": {
        "MEMORY_LLM_BASE_URL": "http://localhost:1234/v1"
      }
    }
  }
}
```

#### TRAE

Add to TRAE MCP settings:

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "agent_memory_enhance.server"]
    }
  }
}
```

#### Direct run (for testing)

```bash
python -m agent_memory_enhance.server
```

## Tools

The server exposes 9 MCP tools:

| Tool | Description |
|------|-------------|
| `memory_add` | Extract and store a memory from conversation text |
| `memory_search` | Search for relevant memories (three-layer funnel) |
| `memory_list` | List all active memories |
| `memory_get` | Get full details of a specific memory by ID |
| `memory_delete` | Soft-delete a memory |
| `memory_update_importance` | Update importance score (1-5) |
| `memory_maintenance` | Run merge + decay maintenance |
| `memory_count` | Get total active memory count |
| `memory_build_context` | Search + format memories as injectable context text |

## How It Works

### Memory Writing (`memory_add`)

```
Conversation text
  ↓
LLM Extract (structured JSON: name, keywords, summary, triggers, importance)
  ↓
Embedding (optional, for semantic search)
  ↓
SQLite INSERT
```

### Memory Retrieval (`memory_search`)

```
User query
  ↓
Layer 1: Semantic Match (embedding cosine / TF-IDF) → Top-5 candidates
  ↓
Layer 2: LLM Relevance Filter → 0-3 truly relevant
  ↓
Layer 3: Return with full raw_content + update access records
```

### Memory Maintenance (`memory_maintenance`)

```
All active memories
  ↓
Merge: similarity >= 0.9 → LLM merges into one → archive old ones
  ↓
Decay: importance < 3 AND 30+ days unaccessed → archive
```

## Architecture

```
agent-memory-enhance-skill/
├── src/agent_memory_enhance/
│   ├── __init__.py
│   ├── llm_client.py      # OpenAI-compatible LLM + embedding client
│   ├── memory_core.py     # MemorySkill + MemoryStore + MemSkillManager
│   └── server.py          # MCP server with 9 tools
├── pyproject.toml
└── README.md
```

## License

MIT
