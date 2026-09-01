#!/usr/bin/env python3
"""
Agent Memory Enhance — MCP Server

A long-term memory system for AI agents, exposed via Model Context Protocol (MCP).
Compatible with Claude Desktop, Cursor, TRAE, Windsurf, and any MCP-compatible client.

Tools exposed:
  1. memory_add           — Extract and store a memory from conversation text
  2. memory_search        — Search for memories relevant to a query (three-layer funnel)
  3. memory_list          — List all active memories
  4. memory_get           — Get a specific memory by ID
  5. memory_delete        — Delete a memory
  6. memory_update_importance — Update the importance score of a memory
  7. memory_maintenance   — Run merge + decay maintenance
  8. memory_count         — Get the total count of active memories
  9. memory_build_context — Search + format memories as injectable context text

Configuration (environment variables):
  MEMORY_LLM_BASE_URL     (default: http://localhost:1234/v1)
  MEMORY_LLM_API_KEY      (default: "no-key")
  MEMORY_LLM_MODEL        (default: "local-model")
  MEMORY_EMBEDDING_MODEL  (default: "" → TF-IDF fallback)
  MEMORY_DB_PATH          (default: ./memory.db)
"""

import os
import sys
import json

# Ensure src/ is on the path when running directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from agent_memory_enhance.llm_client import LLMClient
from agent_memory_enhance.memory_core import MemSkillManager

# ---------- Initialize ----------
mcp = FastMCP("agent-memory-enhance")

_llm = LLMClient()
_db_path = os.getenv("MEMORY_DB_PATH", os.path.join(os.getcwd(), "memory.db"))
_manager = MemSkillManager(llm=_llm, db_path=_db_path)


# ---------- Tools ----------

@mcp.tool()
def memory_add(conversation_text: str, session_id: str = "") -> str:
    """Extract key facts from a conversation and store them as a long-term memory.

    The LLM analyzes the conversation and extracts structured memory: name, keywords,
    summary, triggers, and importance (1-5). If nothing is worth remembering, returns "skipped".

    Args:
        conversation_text: The conversation text to extract memories from (min 10 chars).
        session_id: Optional session identifier for traceability.

    Returns:
        JSON string with the stored memory's metadata, or {"skip": true} if nothing worth saving.
    """
    skill = _manager.add_memory(conversation_text, session_id)
    if skill is None:
        return json.dumps({"skip": True, "message": "Nothing worth remembering in this conversation."})
    return json.dumps({
        "skill_id": skill.skill_id,
        "name": skill.name,
        "keywords": skill.keywords,
        "summary": skill.summary,
        "triggers": skill.triggers,
        "importance": skill.importance,
    }, ensure_ascii=False)


@mcp.tool()
def memory_search(query: str) -> str:
    """Search for memories relevant to the user's current message using three-layer funnel retrieval.

    Layer 1: Semantic matching (embedding cosine similarity or TF-IDF fallback) — Top-5 candidates.
    Layer 2: LLM-based fine-grained relevance filtering (0-3 selected).
    Layer 3: Returns selected memories with full raw_content, updates access records.

    Args:
        query: The user's current message or question.

    Returns:
        JSON array of matching memories with full details (skill_id, name, summary, raw_content, importance, etc.).
    """
    memories = _manager.retrieve_relevant_memories(query)
    return json.dumps([m.to_dict() for m in memories], ensure_ascii=False)


@mcp.tool()
def memory_list(limit: int = 50) -> str:
    """List all active memories, ordered by importance (desc) then creation time (desc).

    Args:
        limit: Maximum number of memories to return (default 50, max 1000).

    Returns:
        JSON array of memory objects (without raw_content for brevity).
    """
    limit = max(1, min(1000, int(limit)))
    memories = _manager.list_all()[:limit]
    result = []
    for m in memories:
        result.append({
            "skill_id": m.skill_id,
            "name": m.name,
            "keywords": m.keywords,
            "summary": m.summary,
            "importance": m.importance,
            "created_at": m.created_at,
            "last_accessed_at": m.last_accessed_at,
            "access_count": m.access_count,
        })
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def memory_get(skill_id: str) -> str:
    """Get the full details of a specific memory by its ID.

    Args:
        skill_id: The unique identifier of the memory (e.g., "mem_20260823_143022_a1b2c3").

    Returns:
        JSON object with all fields including raw_content, or {"error": "not found"}.
    """
    mem = _manager.store.get(skill_id)
    if mem is None:
        return json.dumps({"error": "Memory not found", "skill_id": skill_id})
    return json.dumps(mem.to_dict(), ensure_ascii=False)


@mcp.tool()
def memory_delete(skill_id: str) -> str:
    """Delete a memory by setting its status to 'deleted' (soft delete, recoverable).

    Args:
        skill_id: The unique identifier of the memory to delete.

    Returns:
        JSON object with success status.
    """
    _manager.delete_memory(skill_id)
    return json.dumps({"success": True, "deleted": skill_id})


@mcp.tool()
def memory_update_importance(skill_id: str, importance: int) -> str:
    """Update the importance score of a memory (1-5 scale).

    Importance levels: 1=trivial, 2=minor, 3=normal, 4=important, 5=critical.

    Args:
        skill_id: The unique identifier of the memory.
        importance: New importance level (1-5, will be clamped to range).

    Returns:
        JSON object with the updated importance value.
    """
    importance = max(1, min(5, int(importance)))
    _manager.update_importance(skill_id, importance)
    return json.dumps({"success": True, "skill_id": skill_id, "importance": importance})


@mcp.tool()
def memory_maintenance() -> str:
    """Run memory maintenance: merge similar memories and forget low-importance stale ones.

    - Merge: Memories with similarity >= 0.9 are merged into one comprehensive memory using LLM.
    - Forget: Memories with importance < 3 that haven't been accessed in 30+ days are archived.

    Returns:
        JSON object with merge and forget counts, e.g., {"merged": 3, "forgotten": 2}.
    """
    stats = _manager.schedule_maintenance()
    return json.dumps(stats)


@mcp.tool()
def memory_count() -> str:
    """Get the total count of active memories in the system.

    Returns:
        JSON object with the count, e.g., {"count": 42}.
    """
    n = _manager.count()
    return json.dumps({"count": n})


@mcp.tool()
def memory_build_context(query: str) -> str:
    """Search for relevant memories and format them as context text for LLM injection.

    This is a convenience tool that combines memory_search + build_context_text.
    The returned text can be directly prepended to the agent's system prompt.

    Args:
        query: The user's current message or question.

    Returns:
        Formatted context text string, or empty string if no relevant memories found.
    """
    memories = _manager.retrieve_relevant_memories(query)
    return _manager.build_context_text(memories)


# ---------- Entry Point ----------

if __name__ == "__main__":
    mcp.run(transport="stdio")
