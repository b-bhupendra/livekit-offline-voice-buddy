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
        """)

        # Indexes for fast retrieval
        conn.execute("CREATE INDEX IF NOT EXISTS idx_curr_nodes_chapter ON curriculum_nodes(chapter_idx);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_curr_variants_node ON curriculum_variants(node_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reconsider_node ON reconsideration_requests(node_id);")

    conn.close()
    seed_canonical_nodes()


def seed_canonical_nodes() -> None:
    """Seeds the 8 foundational topics from syllabus_tracker into curriculum_nodes if empty."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM curriculum_nodes")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    seeds = [
        {
            "node_id": "ch1_concrete_abstract",
            "chapter_idx": 1,
            "submodule": "Concrete vs Abstract Nouns",
            "title": "Concrete vs Abstract Nouns",
            "core_concept": "Sensory physical objects vs mental constructs and emotion virtues",
            "prerequisites": [],
            "lecture_paragraphs": [
                "Concrete nouns designate tangible entities existing in physical space that can be directly observed through at least one of your five senses: sight, touch, sound, smell, or taste. Everyday instances include items like 'laptop', 'coffee', 'desk', and 'thunder'. Because these items possess physical boundaries, they can be measured, photographed, and easily grouped into units.",
                "Abstract nouns, by contrast, denote non-physical concepts, emotional states, intellectual philosophies, ethical virtues, and qualitative relationships. Notable examples include 'curiosity', 'freedom', 'dignity', and 'elegance'. You cannot hold 'curiosity' in a bag or weigh 'integrity' on a scale; they function as mental, cognitive, or experiential realities.",
                "A core grammatical trap occurs when learners attempt to pluralize abstract nouns as if they were physical objects. For example, standard grammar rejects 'many courages' or 'an honesty'; instead, you employ partitive or qualitative phrases such as 'acts of courage' or simply the uncountable 'great honesty'."
            ],
            "canvas_type": "classifier",
            "canvas_config": {
                "title": "Sensory vs Conceptual Classifier",
                "categories": ["Concrete (Sensory)", "Abstract (Mind/Idea)"],
                "items": [
                    {"name": "Laptop", "category": "Concrete (Sensory)", "type": "concrete"},
                    {"name": "Courage", "category": "Abstract (Mind/Idea)", "type": "abstract"},
                    {"name": "Coffee", "category": "Concrete (Sensory)", "type": "concrete"},
                    {"name": "Freedom", "category": "Abstract (Mind/Idea)", "type": "abstract"},
                    {"name": "Thunder", "category": "Concrete (Sensory)", "type": "concrete"},
                    {"name": "Integrity", "category": "Abstract (Mind/Idea)", "type": "abstract"}
                ]
            },
            "citations": ["Oxford Guide to English Grammar", "Arihant English Grammar"],
            "status": "published"
        },
        {
            "node_id": "ch1_countable_uncountable",
            "chapter_idx": 1,
            "submodule": "Countable vs Uncountable (Mass Nouns)",
            "title": "Countable vs Uncountable Nouns",
            "core_concept": "Discrete count units vs continuous mass nouns and partitives",
            "prerequisites": ["ch1_concrete_abstract"],
            "lecture_paragraphs": [
                "Countable nouns represent discrete, individual entities that can be numbered directly (e.g., 'one project', 'two questions', 'three books'). They possess both distinct singular and plural forms (typically ending in '-s' or '-es') and comfortably accept the indefinite articles 'a' or 'an' in their singular representation.",
                "Uncountable nouns (mass nouns) refer to substances, liquids, abstract concepts, or collective aggregates that cannot be divided into discrete numbered units without a partitive counter. Crucial examples tested in competitive examinations include 'information', 'advice', 'equipment', 'furniture', 'luggage', and 'research'. These nouns are strictly singular in concord: they take singular verbs ('The equipment is ready') and cannot take 'a/an' or a plural '-s'.",
                "To quantify uncountable nouns, English uses partitive structures: 'a piece of advice', 'three items of furniture', or 'a bottle of water'. Crucially, match your quantifiers: use 'fewer' and 'many' for countable items, but 'less' and 'much' for uncountable masses (e.g., 'less traffic', 'fewer cars')."
            ],
            "canvas_type": "classifier",
            "canvas_config": {
                "title": "Countable vs Uncountable Particle Funnel",
                "categories": ["Countable (Many / Few)", "Uncountable (Much / Little)"],
                "items": [
                    {"name": "Apples", "category": "Countable (Many / Few)", "type": "countable"},
                    {"name": "Water", "category": "Uncountable (Much / Little)", "type": "uncountable"},
                    {"name": "Advice", "category": "Uncountable (Much / Little)", "type": "uncountable"},
                    {"name": "Laptops", "category": "Countable (Many / Few)", "type": "countable"},
                    {"name": "Information", "category": "Uncountable (Much / Little)", "type": "uncountable"},
                    {"name": "Furniture", "category": "Uncountable (Much / Little)", "type": "uncountable"}
                ]
            },
            "citations": ["Oxford Guide to English Grammar"],
            "status": "published"
        },
        {
            "node_id": "ch1_collective_concord",
            "chapter_idx": 1,
            "submodule": "Collective Nouns & Syntactic Concord",
            "title": "Collective Nouns & Syntactic Concord",
            "core_concept": "Unitary vs divided concord in collective noun assemblies",
            "prerequisites": ["ch1_countable_uncountable"],
            "lecture_paragraphs": [
                "Collective nouns designate a singular lexical entity that refers to an assembly of individual people or items, such as 'team', 'committee', 'jury', 'faculty', and 'government'. Syntactically, collective nouns possess dynamic concord: they trigger either singular or plural grammatical agreement depending on speaker focus.",
                "When the group behaves as an integrated, unified whole with a singular focus or decision, formal syntax requires singular agreement: 'The committee has approved the proposal.' Here, the collective noun functions as a solitary unit, matching singular auxiliary 'has' and pronoun 'its'.",
                "Conversely, when individual members within the collective are acting independently or experiencing conflict, plural concord is employed: 'The jury are still debating among themselves.' Inserting 'members of...' easily resolves ambiguity."
            ],
            "canvas_type": "matrix",
            "canvas_config": {
                "title": "Collective Concord Scale",
                "noun": "The Committee",
                "singular_sentence": "The committee IS unanimous in its decision.",
                "plural_sentence": "The committee ARE divided in their opinions.",
                "active_mode": "unitary"
            },
            "citations": ["Arihant English Grammar"],
            "status": "published"
        },
        {
            "node_id": "ch1_compound_nouns",
            "chapter_idx": 1,
            "submodule": "Compound Nouns & Head Noun Pluralization",
            "title": "Compound Nouns & Head Nouns",
            "core_concept": "Pluralizing the core head noun rather than prepositions or modifiers",
            "prerequisites": ["ch1_countable_uncountable"],
            "lecture_paragraphs": [
                "Compound nouns are formed when two or more independent words combine into a single grammatical entity. They appear in solid form (blackboard), hyphenated form (runner-up, mother-in-law), and open form (software engineer).",
                "The core syntactical principle of compound morphology is identifying the head noun—the lexical anchor that denotes the essential nature of the person or object. In 'passer-by', the head noun is 'passer'. In 'mother-in-law', the head noun is 'mother'.",
                "Avoid placing '-s' on prepositions. The grammatically sanctioned plurals are passersby (not passerbys), mothers-in-law (not mother-in-laws), and runners-up (not runner-ups)."
            ],
            "canvas_type": "tree",
            "canvas_config": {
                "title": "Compound Head-Noun Inspector",
                "compounds": [
                    {"full": "Mother-in-law", "head": "Mother", "modifier": "-in-law", "correct_plural": "Mothers-in-law", "wrong_plural": "Mother-in-laws"},
                    {"full": "Passer-by", "head": "Passer", "modifier": "-by", "correct_plural": "Passersby", "wrong_plural": "Passer-bys"}
                ]
            },
            "citations": ["Oxford Guide to English Grammar"],
            "status": "published"
        },
        {
            "node_id": "ch1_possessive_genitives",
            "chapter_idx": 1,
            "submodule": "Possessive Genitives & Joint Ownership",
            "title": "Possessive Genitives & Joint Ownership",
            "core_concept": "Joint vs separate genitive apostrophes and of-constructions",
            "prerequisites": ["ch1_compound_nouns"],
            "lecture_paragraphs": [
                "The genitive case expresses possession, origin, or relational connection. For singular nouns and irregular plurals not ending in 's', add apostrophe-s ('the student's laptop', 'the children's room'). For regular plurals ending in 's', append only the apostrophe ('the students' laptops').",
                "Joint versus separate ownership is a crucial syntax distinction. When two entities jointly own a single asset, place the apostrophe-s only on the final noun: 'Ravi and Neha's startup.' When each entity owns distinct assets, both take the genitive: 'Ravi's and Neha's laptops.'",
                "Inanimate objects typically resist apostrophe-s in formal prose: prefer 'the leg of the table' over 'the table's leg'."
            ],
            "canvas_type": "matrix",
            "canvas_config": {
                "title": "Genitive Ownership Switchboard",
                "scenarios": [
                    {"type": "Joint Ownership", "text": "Ravi and Neha's company (1 shared company)"},
                    {"type": "Separate Ownership", "text": "Ravi's and Neha's laptops (2 distinct laptops)"}
                ]
            },
            "citations": ["Arihant English Grammar"],
            "status": "published"
        },
        {
            "node_id": "ch1_workplace_register",
            "chapter_idx": 1,
            "submodule": "Polite Requests & Softening",
            "title": "Workplace Register & Softening Requests",
            "core_concept": "Modal auxiliary softening and professional workplace pragmatic tone",
            "prerequisites": ["ch1_concrete_abstract"],
            "lecture_paragraphs": [
                "In professional office environments, direct imperatives like 'Send me the report now' sound abrupt and confrontational. English achieves politeness through modal past-tense softening and hedging expressions.",
                "Using 'Could you possibly...', 'Would you mind...', or 'I was wondering if...' transforms commands into collaborative, courteous requests without losing authority.",
                "When addressing senior leadership or cross-functional partners, softening signals emotional intelligence and corporate composure."
            ],
            "canvas_type": "matrix",
            "canvas_config": {
                "title": "Workplace Register Matrix",
                "items": [
                    {"blunt": "Fix this code.", "polished": "Could you take a quick look at this merge request when you have a moment?"},
                    {"blunt": "Give me the file.", "polished": "Would you mind sharing the updated spreadsheet?"}
                ]
            },
            "citations": ["Udemy Complete Grammar Course"],
            "status": "published"
        },
        {
            "node_id": "ch1_spoken_contractions",
            "chapter_idx": 1,
            "submodule": "Everyday Spoken Contractions",
            "title": "Spoken Contractions & Cadence",
            "core_concept": "Connected speech rhythm and natural phonetic reductions",
            "prerequisites": ["ch1_concrete_abstract"],
            "lecture_paragraphs": [
                "Native English speech relies on connected rhythm where function words contract naturally. Non-native speakers who pronounce every syllable uncontracted often sound robotic or excessively formal.",
                "Common spoken reductions like 'I'll', 'they've', 'we're', and 'didn't' keep the conversational rhythm moving fluidly.",
                "Practicing phrase-level shadowing builds muscle memory for unstressed vowel reductions (schwa sound)."
            ],
            "canvas_type": "flow",
            "canvas_config": {
                "title": "Rhythm Cadence Flow",
                "steps": [
                    {"step": 1, "text": "I will go to the office.", "reduction": "I'll go to the office."},
                    {"step": 2, "text": "They have finished the sprint.", "reduction": "They've finished the sprint."}
                ]
            },
            "citations": ["Udemy Complete Grammar Course"],
            "status": "published"
        },
        {
            "node_id": "ch1_course_foundations",
            "chapter_idx": 1,
            "submodule": "Course Foundations & Fluency",
            "title": "Grammar Foundations & Fluency Overview",
            "core_concept": "The architecture of English sentences: subjects, predicates, and modifiers",
            "prerequisites": [],
            "lecture_paragraphs": [
                "Every complete English sentence consists of a subject and a predicate. The subject identifies who or what performs the action, while the predicate reveals the action, state, or complement.",
                "Mastery of foundational syntax allows you to express complex technical and interpersonal thoughts with clarity and confidence.",
                "As we advance through the course, each chapter builds upon these foundational grammatical patterns."
            ],
            "canvas_type": "flow",
            "canvas_config": {
                "title": "Sentence Foundation Flow",
                "steps": [
                    {"step": 1, "text": "Subject (Noun / Pronoun)"},
                    {"step": 2, "text": "Verb / Predicate (Action / State)"},
                    {"step": 3, "text": "Complement / Object (Details)"}
                ]
            },
            "citations": ["Oxford Guide to English Grammar"],
            "status": "published"
        }
    ]

    with conn:
        for s in seeds:
            conn.execute("""
                INSERT OR REPLACE INTO curriculum_nodes (
                    node_id, chapter_idx, submodule, title, core_concept,
                    prerequisites, lecture_paragraphs, canvas_type,
                    canvas_config, citations, status, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                s["node_id"],
                s["chapter_idx"],
                s["submodule"],
                s["title"],
                s["core_concept"],
                json.dumps(s["prerequisites"]),
                json.dumps(s["lecture_paragraphs"]),
                s["canvas_type"],
                json.dumps(s["canvas_config"]),
                json.dumps(s["citations"]),
                s["status"]
            ))

    conn.close()
    rag_logger.info(f"Seeded {len(seeds)} canonical curriculum nodes into data/curriculum.db.")


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
                canvas_config, impressions_count, satisfaction_score, last_accessed_at
            ) VALUES (?, ?, ?, ?, ?, 1, 1.0, CURRENT_TIMESTAMP)
            ON CONFLICT(node_id, style) DO UPDATE SET
                lecture_paragraphs = excluded.lecture_paragraphs,
                canvas_config = excluded.canvas_config,
                impressions_count = impressions_count + 1,
                last_accessed_at = CURRENT_TIMESTAMP
        """, (
            variant_id,
            node_id,
            style,
            json.dumps(draft.get("lecture_paragraphs", [])),
            json.dumps(draft.get("canvas_config", {}))
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

    return {
        "variant_id": row["variant_id"],
        "node_id": row["node_id"],
        "style": row["style"],
        "lecture_paragraphs": json.loads(row["lecture_paragraphs"]),
        "canvas_config": json.loads(row["canvas_config"]),
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
