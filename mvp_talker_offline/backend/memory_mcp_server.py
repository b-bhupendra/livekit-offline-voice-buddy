import os
import json
import sqlite3
import asyncio
import threading
import urllib.request
from typing import Dict, Any, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server.mcpserver import MCPServer as FastMCP

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

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen-buddy")

memory_mcp = FastMCP("BuddyMemoryAndGrammarServer")
rag_store = RAGStore(db_path=DB_PATH)
syllabus_tracker = SyllabusTracker(db_path=DB_PATH)
simulation_engine = SimulationEngine(rag_store=rag_store)

def _ollama_stream(prompt: str, system: str = "", model: str = None):
    """
    Synchronous generator that streams tokens from Ollama.
    Yields token strings one at a time.
    """
    model = model or OLLAMA_MODEL
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": True,
        "options": {"temperature": 0.4, "num_predict": 800}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        yield f"[Ollama error: {e}]"

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
def save_conversation_turn(user_message: str, assistant_response: str) -> str:
    """Saves a conversation turn to SQLite memory store."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_history (user_message, assistant_response) VALUES (?, ?)",
            (user_message, assistant_response)
        )
        conn.commit()
    return "Saved turn successfully."

@memory_mcp.tool()
def query_conversation_history(limit: int = 5) -> str:
    """Retrieves recent conversation history from SQLite memory store."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_message, assistant_response FROM conversation_history ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        if not rows:
            return "No previous history found."
        history = []
        for r in reversed(rows):
            history.append(f"User: {r['user_message']}\nAssistant: {r['assistant_response']}")
        return "\n\n".join(history)

@memory_mcp.tool()
def query_grammar_rag(query: str, top_k: int = 3) -> str:
    """
    Search the local RAG knowledge base for authoritative grammar rules from:
    - Oxford Guide to English Grammar (John Eastwood)
    - Arihant General English (P.K. Thorne & S.C. Gupta)
    """
    results = rag_store.hybrid_search(query, top_k=top_k)
    if not results:
        return "No direct matches found in local grammar references."
    formatted = []
    for idx, r in enumerate(results, 1):
        source = r.get("source_title", "Reference")
        section = r.get("section_title", "")
        text = r.get("text", "")
        formatted.append(f"[{idx}] Source: {source} | Section: {section}\n{text}")
    return "\n\n---\n\n".join(formatted)

@memory_mcp.tool()
def get_learner_progress() -> str:
    """Returns the current learner state, active chapter, and syllabus progress."""
    state = syllabus_tracker.get_state()
    return json.dumps(state, indent=2)

@memory_mcp.tool()
def advance_chapter() -> str:
    """Attempts to advance the learner to the next chapter if requirements are met."""
    if not syllabus_tracker.can_advance():
        return "Cannot advance: both coursework and milestone quiz must be completed."
    new_ch = syllabus_tracker.advance_to_next_chapter()
    return f"Successfully advanced to Chapter {new_ch}."

@memory_mcp.tool()
def search_web_grammar(query: str) -> str:
    """Free web search fallback using DuckDuckGo for language disputes."""
    if DDGS is None:
        return "DuckDuckGo search unavailable: ddgs package not installed."
    try:
        search_query = f"grammar rule English {query[:80]}"
        results = list(DDGS().text(search_query, max_results=3))
        if not results:
            return f"No authoritative web results found for: {query}"
        snippets = []
        for r in results:
            snippets.append(f"- {r.get('title')}: {r.get('body')[:200]} ({r.get('href')})")
        return "\n".join(snippets)
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

@memory_mcp.tool()
def generate_quiz(chapter: int, mode: str = "milestone") -> str:
    """
    Generates grammar quiz questions for the given chapter using RAG context.
    Returns structured JSON with verified rules and citations.
    """
    active_ch = syllabus_tracker.get_active_chapter()
    ch_title = active_ch.get("title", f"Chapter {chapter}") if isinstance(active_ch, dict) else f"Chapter {chapter}"
    rag_results = rag_store.hybrid_search(
        f"chapter {chapter} grammar rules", top_k=4, chapter_filter=chapter
    )
    rag_context = "\n\n".join([r["text"] for r in rag_results]) if rag_results else ""

    system_prompt = (
        "You are an expert English grammar quiz designer. "
        "Generate exactly 5 multiple-choice quiz questions based on the provided grammar rules. "
        "Each question MUST cite Oxford Guide or Arihant Grammar as source. "
        "Return ONLY valid JSON in this exact format:\n"
        '{"questions": [{"id": "q1", "stem": "...", "sentence": "...", '
        '"options": [{"id": "A", "text": "..."}, ...], '
        '"correct_answer": "A", "explanation": "...", '
        '"rule_citation": "Oxford Ch X / Arihant Rule Y"}]}'
    )
    user_prompt = (
        f"Chapter {chapter}: {ch_title}\n\n"
        f"Grammar reference:\n{rag_context[:1500]}\n\n"
        f"Generate {5 if mode == 'milestone' else 3} multiple-choice questions. "
        f"Make them progressively harder. Return only JSON."
    )

    full_text = ""
    for token in _ollama_stream(user_prompt, system=system_prompt):
        full_text += token

    questions = []
    try:
        start = full_text.find("{")
        end = full_text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(full_text[start:end])
            questions = parsed.get("questions", [])
    except Exception:
        pass

    return json.dumps({
        "success": bool(questions),
        "chapter": chapter,
        "mode": mode,
        "questions": questions
    }, indent=2)

@memory_mcp.tool()
def generate_revision_notes(chapter: int) -> str:
    """
    Generates revision notes for the given chapter.
    Returns structured JSON with overview, rules, and mistakes.
    """
    active_ch = syllabus_tracker.get_active_chapter()
    ch_title = active_ch.get("title", f"Chapter {chapter}") if isinstance(active_ch, dict) else f"Chapter {chapter}"
    rag_results = rag_store.hybrid_search(
        f"chapter {chapter} rules summary", top_k=5, chapter_filter=chapter
    )
    rag_context = "\n\n".join([r["text"] for r in rag_results]) if rag_results else ""

    system_prompt = (
        "You are a concise, expert English grammar teacher creating revision notes. "
        "Return JSON: {\"title\": \"...\", \"overview\": \"...\", "
        "\"rules\": [{\"title\": \"...\", \"body\": \"...\", \"type\": \"rule|formula|colloquial\", \"citation\": \"...\"}], "
        "\"mistakes\": [\"...\"], \"colloquialisms\": [\"...\"]}"
    )
    user_prompt = f"Chapter {chapter}: {ch_title}\n\nGrammar reference:\n{rag_context[:2000]}"

    full_text = ""
    for token in _ollama_stream(user_prompt, system=system_prompt):
        full_text += token

    notes_data = {}
    try:
        start = full_text.find("{")
        end = full_text.rfind("}") + 1
        if start >= 0 and end > start:
            notes_data = json.loads(full_text[start:end])
    except Exception:
        notes_data = {
            "title": ch_title,
            "overview": full_text[:200] if full_text else "Revision notes generated.",
            "rules": [],
            "mistakes": [],
            "colloquialisms": []
        }

    return json.dumps(notes_data, indent=2)

if __name__ == "__main__":
    memory_mcp.run()
