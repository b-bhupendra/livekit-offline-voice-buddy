#!/usr/bin/env python3
"""Model Context Protocol (MCP) Server for English Conversation Memory & RAG.
Runs over standard stdio using the FastMCP framework.
Allows LiveKit Agent, external tools, or IDEs to query and update persistent learning memory.
"""

import sys
from pathlib import Path

# Ensure mvp_talker_offline is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mcp.server.fastmcp import FastMCP
import memory_store

# Initialize FastMCP server
mcp = FastMCP("english-buddy-memory")


@mcp.tool()
def get_last_conversation_state() -> str:
    """Returns the most recent conversation session summary, topic, and grammar focus so the agent knows where to begin."""
    last = memory_store.get_last_session()
    if not last or not last.get("topic"):
        return "No previous conversation recorded. This is a fresh session."
    
    return (
        f"Previous session topic: {last.get('topic')}. "
        f"Grammar focus: {last.get('grammar_focus')}. "
        f"Summary: {last.get('summary')}. "
        f"Last discussed turn: {last.get('last_utterance', 'None')}."
    )


@mcp.tool()
def search_past_topics_and_notes(query: str) -> str:
    """Performs RAG search across past dialogue turns and notes to answer questions about past conversations."""
    results = memory_store.search_conversation_history(query, limit=4)
    if not results:
        return f"No previous discussions found matching query: '{query}'."
    
    lines = []
    for r in results:
        role = "User" if r["role"] == "user" else "Buddy"
        lines.append(f"[{r['timestamp'][:16]}] {role}: {r['content']}")
    return "\n".join(lines)


@mcp.tool()
def get_grammar_progress_report() -> str:
    """Returns the user's overall English learning progress, active grammar focus areas, and goals."""
    progress = memory_store.get_learning_progress()
    focus_areas = [f"{g['grammar_point']} ({g['occurrences']}x)" for g in progress["grammar_focus_areas"]]
    focus_str = ", ".join(focus_areas) if focus_areas else "None logged yet"
    
    profile = progress["user_profile"]
    return (
        f"Student: {profile.get('user_name', 'Bhupendra')}. "
        f"Total Sessions: {progress['total_sessions']}. "
        f"Target Goal: {profile.get('proficiency_goal')}. "
        f"Top Grammar Focus Areas: {focus_str}."
    )


@mcp.tool()
def record_learning_milestone(topic: str, grammar_notes: str, summary: str = "") -> str:
    """Saves a practice milestone, scenario, or grammar rule practiced during the session."""
    session_id = f"session-{memory_store.datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    memory_store.start_session(session_id, topic=topic, grammar_focus=grammar_notes)
    if summary:
        memory_store.update_session_summary(session_id, topic=topic, grammar_focus=grammar_notes, summary=summary)
    return f"Recorded learning milestone for topic '{topic}' with grammar focus '{grammar_notes}'."


if __name__ == "__main__":
    mcp.run()
