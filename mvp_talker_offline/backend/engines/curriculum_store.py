"""
curriculum_store.py — Persistent Curriculum Database & Variant Store.

Maintains data/curriculum.db across five dedicated tables:
  1. curriculum_nodes: Canonical, published content for each concept
  2. curriculum_variants: Alternate explanations keyed by (node_id, style)
  3. quiz_items: Dynamic isomorphic questions critiqued per node
  4. reconsideration_requests: Live 'explain this differently' request log & resolution
  5. critique_log: Audit trail of deterministic gate and semantic critic decisions

Kept strictly separate from memory.db so authoring pipeline checkpoint writes
never contend with live voice session learner-state writes.
"""

import os
import json
import sqlite3
import uuid
import time
from typing import Dict, Any, List, Optional, Tuple
from core.config import CURRICULUM_DB_PATH, DATA_DIR
from core.structured_logger import rag_logger, genui_logger

DB_PATH = str(CURRICULUM_DB_PATH)


def get_connection() -> sqlite3.Connection:
    """Return a configured SQLite connection in WAL mode."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_curriculum_db() -> None:
    """Initialize all 5 tables in data/curriculum.db and seed canonical topics if empty."""
    conn = get_connection()
    with conn:
        # 1. Canonical published nodes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS curriculum_nodes (
                node_id            TEXT PRIMARY KEY,
                chapter_idx        INTEGER NOT NULL,
                submodule          TEXT NOT NULL,
                title              TEXT NOT NULL,
                core_concept       TEXT NOT NULL,
                prerequisites      TEXT NOT NULL DEFAULT '[]',
                lecture_paragraphs TEXT NOT NULL DEFAULT '[]',
                canvas_type        TEXT NOT NULL,
                canvas_config      TEXT NOT NULL DEFAULT '{}',
                canvas_html        TEXT NOT NULL DEFAULT '',
                citations          TEXT NOT NULL DEFAULT '[]',
                audio_path         TEXT,
                status             TEXT NOT NULL DEFAULT 'draft',
                version            INTEGER NOT NULL DEFAULT 1,
                created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Variants (alternate explanations)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS curriculum_variants (
                variant_id          TEXT PRIMARY KEY,
                node_id             TEXT NOT NULL REFERENCES curriculum_nodes(node_id),
                style               TEXT NOT NULL,
                lecture_paragraphs  TEXT NOT NULL DEFAULT '[]',
                canvas_config       TEXT NOT NULL DEFAULT '{}',
                canvas_html         TEXT NOT NULL DEFAULT '',
                audio_path          TEXT,
                impressions_count   INTEGER NOT NULL DEFAULT 0,
                satisfaction_score  REAL NOT NULL DEFAULT 0.0,
                last_accessed_at    TIMESTAMP,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(node_id, style)
            )
        """)

        # 3. Dynamic isomorphic quiz items
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_items (
                item_id              TEXT PRIMARY KEY,
                node_id               TEXT NOT NULL REFERENCES curriculum_nodes(node_id),
                question              TEXT NOT NULL,
                options               TEXT NOT NULL DEFAULT '[]',
                correct_answer        TEXT NOT NULL,
                explanation           TEXT NOT NULL,
                citations             TEXT NOT NULL DEFAULT '[]',
                isomorphic_trap_type  TEXT NOT NULL,
                created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Reconsideration requests
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reconsideration_requests (
                request_id           TEXT PRIMARY KEY,
                node_id              TEXT NOT NULL,
                learner_id            TEXT,
                style_hint            TEXT,
                complaint             TEXT,
                status                TEXT NOT NULL DEFAULT 'pending',
                resulting_variant_id  TEXT,
                created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at           TIMESTAMP
            )
        """)

        # 5. Critique audit log
        conn.execute("""
            CREATE TABLE IF NOT EXISTS critique_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id        TEXT NOT NULL,
                job_type       TEXT NOT NULL,
                stage          TEXT NOT NULL,
                passed         BOOLEAN NOT NULL,
                detail         TEXT,
                attempt_number INTEGER NOT NULL,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)        # Auto-migrate existing tables if canvas_html column is missing
        try:
            conn.execute("ALTER TABLE curriculum_nodes ADD COLUMN canvas_html TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE curriculum_variants ADD COLUMN canvas_html TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass

        # Indexes for fast retrieval
        conn.execute("CREATE INDEX IF NOT EXISTS idx_curr_nodes_chapter ON curriculum_nodes(chapter_idx);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_curr_variants_node ON curriculum_variants(node_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reconsider_node ON reconsideration_requests(node_id);")

    conn.close()
    seed_canonical_nodes()


def seed_canonical_nodes() -> None:
    """
    Initializes foundational node outlines in curriculum_nodes if empty.
    Zero hardcoded essay paragraphs or static quiz dictionaries:
    Full lecture paragraphs, HTML5 canvas visuals, and isomorphic traps are
    dynamically authored by the Tier 2 LangGraph pipeline and RAG crawler.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM curriculum_nodes")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    canonical_topics = [
        {"node_id": "ch1_concrete_abstract", "chapter_idx": 1, "submodule": "Concrete vs Abstract Nouns", "title": "Concrete vs Abstract Nouns", "core_concept": "Sensory physical objects vs mental constructs and virtues", "canvas_type": "universal_sandbox", "citations": ["Oxford Guide to English Grammar"]},
        {"node_id": "ch1_countable_uncountable", "chapter_idx": 1, "submodule": "Countable vs Uncountable (Mass Nouns)", "title": "Countable vs Uncountable Nouns", "core_concept": "Discrete count units vs continuous mass nouns and partitives", "canvas_type": "universal_sandbox", "citations": ["Oxford Guide to English Grammar"]},
        {"node_id": "ch1_collective_concord", "chapter_idx": 1, "submodule": "Collective Nouns & Syntactic Concord", "title": "Collective Nouns & Syntactic Concord", "core_concept": "Unitary singular whole vs divided plural individuals", "canvas_type": "universal_sandbox", "citations": ["Oxford Guide to English Grammar", "Arihant English Grammar"]},
        {"node_id": "ch1_compound_nouns", "chapter_idx": 1, "submodule": "Compound Nouns & Head Noun Pluralization", "title": "Compound Nouns & Head Nouns", "core_concept": "Pluralizing only the principal semantic head noun in compound constructions", "canvas_type": "universal_sandbox", "citations": ["Oxford Guide to English Grammar"]},
        {"node_id": "ch1_possessive_genitives", "chapter_idx": 1, "submodule": "Possessive Genitives & Joint Ownership", "title": "Possessive Genitives & Joint Ownership", "core_concept": "Animate genitive 's vs inanimate 'of' relations and joint vs individual ownership", "canvas_type": "universal_sandbox", "citations": ["Oxford Guide to English Grammar", "Arihant English Grammar"]},
        {"node_id": "ch2_inversion_negative", "chapter_idx": 2, "submodule": "Sentence Transformations & Negative Inversion", "title": "Negative Adverb Inversion", "core_concept": "Fronted negative adverbs requiring auxiliary-subject inversion", "canvas_type": "universal_sandbox", "citations": ["Oxford Guide to English Grammar Ch 2"]},
        {"node_id": "ch3_workplace_softening", "chapter_idx": 3, "submodule": "Polite Requests & Softening", "title": "Workplace Register & Softening Requests", "core_concept": "Softening blunt imperatives into diplomatic workplace collaborative requests", "canvas_type": "universal_sandbox", "citations": ["Teacher Luke Workplace Course"]},
        {"node_id": "ch4_repetition_cadence", "chapter_idx": 4, "submodule": "Stress-Timed Cadence & Connected Speech", "title": "Spoken Contractions & Cadence", "core_concept": "English stress-timing cadence and connected speech contractions", "canvas_type": "universal_sandbox", "citations": ["Teacher Luke Conversational Course"]}
    ]

    with conn:
        for t in canonical_topics:
            conn.execute("""
                INSERT OR REPLACE INTO curriculum_nodes (
                    node_id, chapter_idx, submodule, title, core_concept,
                    prerequisites, lecture_paragraphs, canvas_type,
                    canvas_config, canvas_html, citations, status, version
                ) VALUES (?, ?, ?, ?, ?, '[]', '[]', ?, '{}', '', ?, 'published', 1)
            """, (
                t["node_id"],
                t["chapter_idx"],
                t["submodule"],
                t["title"],
                t["core_concept"],
                t["canvas_type"],
                json.dumps(t["citations"])
            ))

    conn.close()
    rag_logger.info(f"Initialized {len(canonical_topics)} dynamic syllabus nodes into data/curriculum.db.")


# ─────────────────────────────────────────────────────────────────────────────
# Typed CRUD Operations
# ─────────────────────────────────────────────────────────────────────────────

def save_node(node_id: str, draft: Dict[str, Any], chapter_idx: int = 1, submodule: str = "") -> str:
    """Save or update a canonical curriculum node."""
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO curriculum_nodes (
                node_id, chapter_idx, submodule, title, core_concept,
                prerequisites, lecture_paragraphs, canvas_type,
                canvas_config, citations, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published', CURRENT_TIMESTAMP)
            ON CONFLICT(node_id) DO UPDATE SET
                chapter_idx = excluded.chapter_idx,
                submodule = excluded.submodule,
                title = excluded.title,
                core_concept = excluded.core_concept,
                prerequisites = excluded.prerequisites,
                lecture_paragraphs = excluded.lecture_paragraphs,
                canvas_type = excluded.canvas_type,
                canvas_config = excluded.canvas_config,
                citations = excluded.citations,
                status = 'published',
                version = version + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (
            node_id,
            chapter_idx,
            submodule or draft.get("submodule", node_id),
            draft.get("title", submodule or node_id),
            draft.get("core_concept", ""),
            json.dumps(draft.get("prerequisites", [])),
            json.dumps(draft.get("lecture_paragraphs", [])),
            draft.get("canvas_type", "classifier"),
            json.dumps(draft.get("canvas_config", {})),
            json.dumps(draft.get("citations", []))
        ))
    conn.close()
    rag_logger.info(f"Curriculum node saved: {node_id}")
    return node_id


def get_node(node_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve canonical node by node_id or submodule fuzzy match."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM curriculum_nodes WHERE node_id = ?", (node_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT * FROM curriculum_nodes WHERE LOWER(submodule) = LOWER(?)", (node_id,))
        row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "node_id": row["node_id"],
        "chapter_idx": row["chapter_idx"],
        "submodule": row["submodule"],
        "title": row["title"],
        "core_concept": row["core_concept"],
        "prerequisites": json.loads(row["prerequisites"]),
        "lecture_paragraphs": json.loads(row["lecture_paragraphs"]),
        "canvas_type": row["canvas_type"],
        "canvas_config": json.loads(row["canvas_config"]),
        "canvas_html": row["canvas_html"] if "canvas_html" in row.keys() else "",
        "citations": json.loads(row["citations"]),
        "audio_path": row["audio_path"],
        "status": row["status"],
        "version": row["version"]
    }


def save_variant(node_id: str, style: str, draft: Dict[str, Any]) -> str:
    """Save an alternate explanation variant keyed by (node_id, style)."""
    variant_id = f"var_{node_id}_{style}_{uuid.uuid4().hex[:6]}"
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO curriculum_variants (
                variant_id, node_id, style, lecture_paragraphs,
                canvas_config, canvas_html, impressions_count, satisfaction_score, last_accessed_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 1.0, CURRENT_TIMESTAMP)
            ON CONFLICT(node_id, style) DO UPDATE SET
                lecture_paragraphs = excluded.lecture_paragraphs,
                canvas_config = excluded.canvas_config,
                canvas_html = excluded.canvas_html,
                impressions_count = impressions_count + 1,
                last_accessed_at = CURRENT_TIMESTAMP
        """, (
            variant_id,
            node_id,
            style,
            json.dumps(draft.get("lecture_paragraphs", [])),
            json.dumps(draft.get("canvas_config", {})),
            draft.get("canvas_html", "")
        ))
    conn.close()
    rag_logger.info(f"Curriculum variant saved for {node_id} (style={style})")
    return variant_id


def get_variant(node_id: str, style: str) -> Optional[Dict[str, Any]]:
    """Retrieve existing variant for (node_id, style). Increments impressions_count."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM curriculum_variants
        WHERE (node_id = ? OR node_id IN (SELECT node_id FROM curriculum_nodes WHERE LOWER(submodule) = LOWER(?)))
        AND LOWER(style) = LOWER(?)
    """, (node_id, node_id, style))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE curriculum_variants
            SET impressions_count = impressions_count + 1, last_accessed_at = CURRENT_TIMESTAMP
            WHERE variant_id = ?
        """, (row["variant_id"],))
        conn.commit()
    conn.close()

    if not row:
        return None

    keys = row.keys()
    return {
        "variant_id": row["variant_id"],
        "node_id": row["node_id"],
        "style": row["style"],
        "lecture_paragraphs": json.loads(row["lecture_paragraphs"]),
        "canvas_config": json.loads(row["canvas_config"]),
        "canvas_html": row["canvas_html"] if "canvas_html" in keys else "",
        "audio_path": row["audio_path"],
        "impressions_count": row["impressions_count"] + 1,
        "satisfaction_score": row["satisfaction_score"]
    }


def flag_node(node_id: str, job_type: str, reason: Optional[str] = None) -> None:
    """Flag a node for human review when authoring retries are exhausted."""
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE curriculum_nodes
            SET status = 'flagged', updated_at = CURRENT_TIMESTAMP
            WHERE node_id = ?
        """, (node_id,))
    conn.close()
    rag_logger.warning(f"Node {node_id} flagged for review ({job_type}): {reason}")


def attach_audio(job_type: str, target_id: str, audio_path: str) -> None:
    """Link synthesized studio audio clip to a node or variant."""
    conn = get_connection()
    with conn:
        if job_type in ("build", "refine"):
            conn.execute("UPDATE curriculum_nodes SET audio_path = ? WHERE node_id = ?", (audio_path, target_id))
        else:
            conn.execute("UPDATE curriculum_variants SET audio_path = ? WHERE variant_id = ?", (audio_path, target_id))
    conn.close()


def log_reconsideration_request(node_id: str, style_hint: str = "", complaint: str = "", learner_id: str = "default_learner") -> str:
    """Log an in-flight 'explain this differently' request from Buddy."""
    request_id = f"recons_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO reconsideration_requests (
                request_id, node_id, learner_id, style_hint, complaint, status
            ) VALUES (?, ?, ?, ?, ?, 'pending')
        """, (request_id, node_id, learner_id, style_hint, complaint))
    conn.close()
    return request_id


def resolve_reconsideration_request(request_id: str, resulting_variant_id: Optional[str] = None) -> None:
    """Mark a reconsideration request as resolved."""
    conn = get_connection()
    with conn:
        conn.execute("""
            UPDATE reconsideration_requests
            SET status = 'done', resulting_variant_id = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE request_id = ?
        """, (resulting_variant_id, request_id))
    conn.close()


def log_critique(node_id: str, job_type: str, stage: str, passed: bool, detail: Optional[str] = None, attempt_number: int = 1) -> None:
    """Log deterministic gate or semantic critic decisions for runtime audits."""
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO critique_log (
                node_id, job_type, stage, passed, detail, attempt_number
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (node_id, job_type, stage, passed, detail, attempt_number))
    conn.close()


def get_clustered_reconsideration_nodes(min_count: int = 3) -> List[Tuple[str, int]]:
    """Return nodes that received >= min_count reconsideration requests (signals need for canonical rewrite)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT node_id, COUNT(*) as req_count
        FROM reconsideration_requests
        GROUP BY node_id
        HAVING COUNT(*) >= ?
    """, (min_count,))
    rows = cursor.fetchall()
    conn.close()
    return [(r["node_id"], r["req_count"]) for r in rows]

# Auto-initialize on import
init_curriculum_db()
