import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from rag_store import RAGStore
from syllabus_tracker import SyllabusTracker
from simulation_engine import SimulationEngine

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORKSPACE_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "memory.db")

memory_mcp = FastMCP("BuddyMemoryAndGrammarServer")
rag_store = RAGStore(db_path=DB_PATH)
syllabus_tracker = SyllabusTracker(db_path=DB_PATH)
simulation_engine = SimulationEngine(rag_store=rag_store)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT,
                assistant_response TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learner_recasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                original_utterance TEXT,
                polished_recast TEXT,
                grammar_rule TEXT
            )
        """)
    return conn

@memory_mcp.tool()
def log_conversation_turn(user_message: str, assistant_response: str) -> str:
    """Logs an interaction turn to the persistent database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_history (user_message, assistant_response) VALUES (?, ?)",
            (user_message, assistant_response)
        )
        conn.commit()
    return "Turn logged successfully."

@memory_mcp.tool()
def get_learner_summary() -> str:
    """Retrieves learner profile, active chapter, and grammar mastery statistics."""
    state = syllabus_tracker.get_state()
    active_ch = syllabus_tracker.get_active_chapter()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM learner_recasts")
        recast_cnt = cursor.fetchone()["cnt"]

    summary = (
        f"Learner Profile:\n"
        f"- Active Chapter: Chapter {state['current_chapter_idx']} ({active_ch['title']})\n"
        f"- Current Stage: {state['current_stage']}\n"
        f"- Coursework Completed: {state['coursework_completed']}\n"
        f"- Quiz Passed: {state['quiz_passed']}\n"
        f"- Cumulative Accuracy: {state['cumulative_accuracy']:.1f}%\n"
        f"- Total Grammatical Recasts Logged: {recast_cnt}\n"
        f"- Failed Questions Awaiting Review: {len(state['failed_questions_queue'])}\n"
        f"- Completed Chapters: {state['completed_chapters']}"
    )
    return summary

@memory_mcp.tool()
def query_grammar_rag(query: str, chapter: Optional[int] = None) -> str:
    """
    Search indexed Oxford Guide, Arihant Grammar, Udemy lectures, and story books
    using hybrid dense vector and SQLite FTS5 search.
    """
    results = rag_store.hybrid_search(query, top_k=3, chapter_filter=chapter)
    if not results:
        return f"No direct matches found in local knowledge base for: '{query}'."

    output = []
    for r in results:
        output.append(
            f"[{r['source_title']} | Section: {r['section_title']}]\n{r['text']}"
        )
    return "\n\n---\n\n".join(output)

@memory_mcp.tool()
def search_web_grammar(query: str) -> str:
    """
    Free web search tool via DuckDuckGo (no API keys required).
    Use this to fact-check disputed grammar rules, Cambridge/Oxford definitions,
    or contemporary usage when a user challenges a correction.
    """
    if DDGS is None:
        return "DuckDuckGo search module (ddgs) is not installed."

    try:
        results = list(DDGS().text(f"grammar English {query}", max_results=3))
        if not results:
            return f"No web search results found for: {query}"
        
        snippets = []
        for r in results:
            snippets.append(f"• {r.get('title')}: {r.get('body')}\n  URL: {r.get('href')}")
        return "\n\n".join(snippets)
    except Exception as e:
        return f"Web search error: {e}"

@memory_mcp.tool()
def dispute_answer(user_claim: str) -> str:
    """
    Impartial linguistic dispute resolver. Invoked when user contends:
    'My answer is right / LLM is wrong!'
    Combines local RAG and live web search to deliver an evidence-backed ruling.
    """
    verdict_data = simulation_engine.handle_answer_contention(user_claim)
    return json.dumps(verdict_data, indent=2)

@memory_mcp.tool()
def log_learner_recast(original_utterance: str, polished_recast: str, grammar_rule: str) -> str:
    """Logs a grammatical correction or colloquial refinement for study notes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO learner_recasts (original_utterance, polished_recast, grammar_rule) VALUES (?, ?, ?)",
            (original_utterance, polished_recast, grammar_rule)
        )
        conn.commit()
    return f"Logged recast: '{original_utterance}' -> '{polished_recast}' ({grammar_rule})"

if __name__ == "__main__":
    memory_mcp.run()
