"""
LangGraph Multi-Agent State Graph for LiveKit English Buddy & Master Tutor.
Maintains state machine across:
 - 'buddy': Casual conversational peer, soft grammar corrections, remembers student phase
 - 'tutor_lecture': Uninterrupted paragraph lecture with HTML5 Canvas visual generation
 - 'tutor_qa': Post-lecture Q&A, counter-question handling, and re-narration
 - 'tutor_quiz': Interactive pattern testing and shadowing repetition
Stores all grammar reference books and course transcripts in a local LangGraph Store.
"""

import os
import json
import sqlite3
import uuid
import time
from typing import Dict, Any, List, Optional, TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore
from core.structured_logger import system_logger, rag_logger
from core.config import DB_PATH, CHECKPOINT_DB_PATH, CURRICULUM_FILE

DB_PATH = str(DB_PATH)
CHECKPOINT_DB_PATH = str(CHECKPOINT_DB_PATH)
CURRICULUM_FILE = str(CURRICULUM_FILE)

class TutorState(TypedDict):
    user_id: str
    active_mode: Literal["buddy", "tutor_lecture", "tutor_qa", "tutor_quiz", "tutor_repetition"]
    current_topic: str
    submodule: str
    phase_index: int
    session_type: str
    lecture_data: Optional[Dict[str, Any]]
    is_delivering_lecture: bool
    mastered_patterns: List[str]
    observed_errors: List[Dict[str, Any]]
    pending_homework: Optional[str]
    last_user_query: str
    last_assistant_reply: str
    conversation_history: List[Dict[str, str]]

class LangGraphTutorEngine:
    def __init__(self, db_path: str = DB_PATH, checkpoint_path: str = CHECKPOINT_DB_PATH):
        self.db_path = db_path
        self.checkpoint_path = checkpoint_path
        db_dir = os.path.dirname(self.checkpoint_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self.store = InMemoryStore()
        self._init_knowledge_store()
        self._conn = sqlite3.connect(self.checkpoint_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(self._conn)
        self.checkpointer.setup()
        self.graph = self._build_graph()

    def _init_knowledge_store(self):
        """Indexes local grammar books (Oxford Guide, Arihant) and Luke curriculum into LangGraph Store."""
        rag_logger.info("Initializing LangGraph Local Knowledge Store from ChromaDB and curriculum.json...")
        count_chunks = 0
        try:
            from engines.rag_store import RAGStore
            rag = RAGStore()
            col_data = rag._col.get(include=["documents", "metadatas"])
            docs = col_data.get("documents") or []
            metas = col_data.get("metadatas") or []
            ids = col_data.get("ids") or []
            for item_id, doc, meta in zip(ids, docs, metas):
                meta = meta or {}
                source = (meta.get("source_title") or "general_grammar").lower().replace(" ", "_")
                section = (meta.get("section_title") or "general").lower().replace(" ", "_")
                data = {
                    "text": doc,
                    "source_title": meta.get("source_title", ""),
                    "section_title": meta.get("section_title", ""),
                    "chapter_idx": meta.get("chapter_idx", 0)
                }
                self.store.put(
                    namespace=("grammar", source, section),
                    key=str(item_id),
                    value=data
                )
                count_chunks += 1
        except Exception as e:
            rag_logger.warning(f"Could not load RAG chunks into LangGraph Store: {e}")

        count_chapters = 0
        try:
            if os.path.exists(CURRICULUM_FILE):
                with open(CURRICULUM_FILE, "r", encoding="utf-8") as f:
                    curr_data = json.load(f)
                for ch_str, info in curr_data.items():
                    ch_idx = info.get("chapter_idx", int(ch_str))
                    self.store.put(
                        namespace=("curriculum", "luke_course"),
                        key=f"ch_{ch_idx}",
                        value=info
                    )
                    count_chapters += 1
        except Exception as e:
            rag_logger.warning(f"Could not load curriculum.json into LangGraph Store: {e}")

        rag_logger.info(f"LangGraph Knowledge Store loaded {count_chunks} reference chunks and {count_chapters} curriculum chapters.")

    def search_knowledge(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Searches LangGraph local store using keyword and token matching."""
        results = []
        q_tokens = [w.lower() for w in query.split() if len(w) > 2]
        if not q_tokens:
            q_tokens = [query.lower()]

        items = self.store.search(("grammar",), limit=200)
        scored = []
        for it in items:
            text = it.value.get("text", "").lower()
            section = it.value.get("section_title", "").lower()
            score = sum(text.count(token) * 2 + section.count(token) * 5 for token in q_tokens)
            if score > 0:
                scored.append((score, it.value))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored[:limit]]
        return results

    def _build_graph(self):
        builder = StateGraph(TutorState)

        builder.add_node("buddy_node", self._buddy_node)
        builder.add_node("tutor_lecture_node", self._tutor_lecture_node)
        builder.add_node("tutor_qa_node", self._tutor_qa_node)
        builder.add_node("tutor_quiz_node", self._tutor_quiz_node)

        def route_from_buddy(state: TutorState) -> str:
            if state.get("active_mode") in ["tutor_lecture", "tutor_qa", "tutor_quiz", "tutor_repetition"]:
                return "tutor_lecture_node"
            return END

        def route_from_lecture(state: TutorState) -> str:
            return "tutor_qa_node"

        def route_from_qa(state: TutorState) -> str:
            mode = state.get("active_mode", "tutor_qa")
            if mode == "buddy":
                return "buddy_node"
            elif mode in ["tutor_quiz", "tutor_repetition"]:
                return "tutor_quiz_node"
            elif mode == "tutor_lecture":
                return "tutor_lecture_node"
            return END

        def route_from_quiz(state: TutorState) -> str:
            mode = state.get("active_mode", "tutor_quiz")
            if mode == "buddy":
                return "buddy_node"
            elif mode == "tutor_qa":
                return "tutor_qa_node"
            return END

        builder.set_entry_point("buddy_node")
        builder.add_conditional_edges("buddy_node", route_from_buddy, {
            "tutor_lecture_node": "tutor_lecture_node",
            END: END
        })
        builder.add_edge("tutor_lecture_node", "tutor_qa_node")
        builder.add_conditional_edges("tutor_qa_node", route_from_qa, {
            "buddy_node": "buddy_node",
            "tutor_quiz_node": "tutor_quiz_node",
            "tutor_lecture_node": "tutor_lecture_node",
            END: END
        })
        builder.add_conditional_edges("tutor_quiz_node", route_from_quiz, {
            "buddy_node": "buddy_node",
            "tutor_qa_node": "tutor_qa_node",
            END: END
        })

        return builder.compile(checkpointer=self.checkpointer)

    def _buddy_node(self, state: TutorState) -> Dict[str, Any]:
        """Buddy Mode: Casual, friendly peer. Softly points out grammar mistakes without breaking conversational immersion."""
        last_user = state.get("last_user_query", "")
        errors = state.get("observed_errors", [])

        l_user = last_user.lower()
        if "an advice" in l_user or "many advices" in l_user:
            errors.append({"error": "an advice", "correction": "some advice", "timestamp": time.time()})
        elif "much people" in l_user:
            errors.append({"error": "much people", "correction": "many people", "timestamp": time.time()})
        elif "informations" in l_user:
            errors.append({"error": "informations", "correction": "information", "timestamp": time.time()})

        return {
            "observed_errors": errors,
            "is_delivering_lecture": False,
            "active_mode": state.get("active_mode", "buddy")
        }

    def _tutor_lecture_node(self, state: TutorState) -> Dict[str, Any]:
        """Tutor Lecture Mode: Uninterrupted educational delivery with dynamic paragraphs and Canvas generation."""
        return {
            "is_delivering_lecture": True,
            "active_mode": "tutor_qa"
        }

    def _tutor_qa_node(self, state: TutorState) -> Dict[str, Any]:
        """Tutor Q&A: Uninterrupted mode finished. Handles counter-questions, re-narrations, and debates."""
        return {
            "is_delivering_lecture": False,
            "active_mode": state.get("active_mode", "tutor_qa")
        }

    def _tutor_quiz_node(self, state: TutorState) -> Dict[str, Any]:
        """Tutor Quiz: Tests patterns until student demonstrates mastery."""
        return {
            "is_delivering_lecture": False,
            "active_mode": state.get("active_mode", "tutor_quiz")
        }

    def get_state(self, user_id: str = "default_learner") -> TutorState:
        """Retrieves checkpointed state for user."""
        config = {"configurable": {"thread_id": user_id}}
        try:
            snapshot = self.graph.get_state(config)
            if snapshot and snapshot.values:
                return snapshot.values
        except Exception:
            pass

        return {
            "user_id": user_id,
            "active_mode": "buddy",
            "current_topic": "Nouns & Determiners",
            "submodule": "Concrete vs Abstract Nouns",
            "phase_index": 1,
            "session_type": "grammar_mastery",
            "lecture_data": None,
            "is_delivering_lecture": False,
            "mastered_patterns": [],
            "observed_errors": [],
            "pending_homework": None,
            "last_user_query": "",
            "last_assistant_reply": "",
            "conversation_history": []
        }

    def update_state(self, updates: Dict[str, Any], user_id: str = "default_learner"):
        """Updates checkpointed state for user in SQLite."""
        config = {"configurable": {"thread_id": user_id}}
        try:
            self.graph.update_state(config, updates)
        except Exception as e:
            rag_logger.warning(f"Failed to update LangGraph state: {e}")

# Global singleton
langgraph_engine = LangGraphTutorEngine()
graph = langgraph_engine.graph
