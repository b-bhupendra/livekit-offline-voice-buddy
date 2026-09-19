import os
import json
import sqlite3
import contextlib
import uuid
import time
from typing import Dict, Any, List, Optional
from core.structured_logger import system_logger

try:
    from tutor.langgraph_tutor_graph import langgraph_engine
except Exception:
    langgraph_engine = None

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(WORKSPACE_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "memory.db")
CURRICULUM_FILE = os.path.join(DATA_DIR, "curriculum.json")

CHAPTER_NAMES = {
    1: "Course Foundations & Sentence Transformations",
    2: "Sentence Transformations (Affirmative to Negative & Question)",
    3: "Commands and Requests (Direct, Softening & Polite Inquiries)",
    4: "Closed Questions & Auxiliary Verb Inversion",
    5: "Open Questions (Wh- Words: Why, How, Who, Where, When, What)",
    6: "Special & Indirect Questions (Embedded Clauses & Question Tags)",
    7: "Existential Sentences (There is/are & Stative Action)",
    8: "Sensory Descriptions & Reference Points (Look, Sound, Feel, Smell)",
    9: "Descriptions of Objects, People & Places",
    10: "Gerunds vs Infinitives (Verbs + -ing vs to-Infinitive)",
    11: "Coordinating Conjunctions (FANBOYS) & Compound Sentences",
    12: "Subordinating Conjunctions & Adverbial Clauses",
    13: "Active vs Passive Voice & Agentless Constructions",
    14: "Conditionals & Hypotheticals (Zero, 1st, 2nd, 3rd, Mixed)",
    15: "Sentence Building & Clause Synthesis",
    16: "Sentence Beginnings & Fronting for Emphasis",
    17: "Cleft Sentences & Inversions",
    18: "Advanced Discourse Fluency & Synthesis"
}

class SyllabusTracker:
    def __init__(self, db_path: str = DB_PATH, user_id: str = "default_learner"):
        self.db_path = db_path
        self.user_id = user_id
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    @contextlib.contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learner_state (
                    user_id TEXT PRIMARY KEY,
                    current_chapter_idx INTEGER DEFAULT 1,
                    current_stage TEXT DEFAULT 'lecture',
                    coursework_completed INTEGER DEFAULT 0,
                    quiz_passed INTEGER DEFAULT 0,
                    cumulative_accuracy REAL DEFAULT 100.0,
                    failed_questions_queue TEXT DEFAULT '[]',
                    completed_chapters TEXT DEFAULT '[]',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS isomorphic_mutation_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    original_question_id TEXT,
                    mutated_question_id TEXT,
                    original_text TEXT,
                    mutated_text TEXT,
                    rule_citation TEXT,
                    student_pass INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lecture_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    topic TEXT,
                    submodule TEXT,
                    phase_index INTEGER DEFAULT 1,
                    session_type TEXT DEFAULT 'grammar_mastery',
                    spoken_summary TEXT,
                    paragraphs TEXT,
                    canvas_type TEXT DEFAULT 'particle_classifier',
                    canvas_config TEXT DEFAULT '{}',
                    repetition_items TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("PRAGMA table_info(lecture_sessions)")
            lec_cols = [r["name"] for r in cursor.fetchall()]
            if "session_type" not in lec_cols:
                cursor.execute("ALTER TABLE lecture_sessions ADD COLUMN session_type TEXT DEFAULT 'grammar_mastery'")
            if "repetition_items" not in lec_cols:
                cursor.execute("ALTER TABLE lecture_sessions ADD COLUMN repetition_items TEXT DEFAULT '[]'")

            cursor.execute("""
                INSERT OR IGNORE INTO learner_state (user_id, current_chapter_idx, current_stage)
                VALUES (?, 1, 'lecture')
            """, (self.user_id,))

            # Ensure columns for Tutor Mode, Homework Tracking and Preferences exist
            cursor.execute("PRAGMA table_info(learner_state)")
            cols = [r["name"] for r in cursor.fetchall()]
            if "active_mode" not in cols:
                cursor.execute("ALTER TABLE learner_state ADD COLUMN active_mode TEXT DEFAULT 'buddy'")
            if "current_topic" not in cols:
                cursor.execute("ALTER TABLE learner_state ADD COLUMN current_topic TEXT DEFAULT 'Nouns: Concrete, Abstract & Countable'")
            if "pending_homework" not in cols:
                cursor.execute("ALTER TABLE learner_state ADD COLUMN pending_homework TEXT DEFAULT NULL")
            if "homework_status" not in cols:
                cursor.execute("ALTER TABLE learner_state ADD COLUMN homework_status TEXT DEFAULT 'none'")
            if "mastered_patterns" not in cols:
                cursor.execute("ALTER TABLE learner_state ADD COLUMN mastered_patterns TEXT DEFAULT '[]'")
            if "learner_preferences" not in cols:
                cursor.execute("ALTER TABLE learner_state ADD COLUMN learner_preferences TEXT DEFAULT '{\"analogy_style\": \"everyday\", \"pacing\": \"steady\"}'")

            conn.commit()

    def get_state(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM learner_state WHERE user_id = ?", (self.user_id,))
            row = cursor.fetchone()
            if not row:
                return {
                    "user_id": self.user_id,
                    "current_chapter_idx": 1,
                    "current_stage": "lecture",
                    "coursework_completed": 0,
                    "quiz_passed": 0,
                    "cumulative_accuracy": 100.0,
                    "failed_questions_queue": [],
                    "completed_chapters": [],
                    "active_mode": "buddy",
                    "current_topic": "Nouns: Concrete, Abstract & Countable",
                    "pending_homework": None,
                    "homework_status": "none",
                    "mastered_patterns": []
                }
            keys = row.keys()
            return {
                "user_id": row["user_id"],
                "current_chapter_idx": row["current_chapter_idx"],
                "current_stage": row["current_stage"],
                "coursework_completed": bool(row["coursework_completed"]),
                "quiz_passed": bool(row["quiz_passed"]),
                "cumulative_accuracy": float(row["cumulative_accuracy"]),
                "failed_questions_queue": json.loads(row["failed_questions_queue"] or "[]"),
                "completed_chapters": json.loads(row["completed_chapters"] or "[]"),
                "active_mode": row["active_mode"] if "active_mode" in keys else "buddy",
                "current_topic": row["current_topic"] if "current_topic" in keys else "Nouns: Concrete, Abstract & Countable",
                "pending_homework": row["pending_homework"] if "pending_homework" in keys else None,
                "homework_status": row["homework_status"] if "homework_status" in keys else "none",
                "mastered_patterns": json.loads(row["mastered_patterns"] or "[]") if "mastered_patterns" in keys else [],
                "updated_at": row["updated_at"]
            }

    def get_active_chapter(self) -> Dict[str, Any]:
        state = self.get_state()
        c_idx = state["current_chapter_idx"]
        title = CHAPTER_NAMES.get(c_idx, f"Chapter {c_idx}")
        
        summary = ""
        if os.path.exists(CURRICULUM_FILE):
            try:
                with open(CURRICULUM_FILE, "r", encoding="utf-8") as f:
                    curr = json.load(f)
                    summary = curr.get(str(c_idx), {}).get("summary", "")
            except Exception:
                pass

        return {
            "chapter_idx": c_idx,
            "title": title,
            "stage": state["current_stage"],
            "summary": summary,
            "coursework_completed": state["coursework_completed"],
            "quiz_passed": state["quiz_passed"]
        }

    def update_stage(self, new_stage: str) -> bool:
        valid_stages = ["lecture", "dilemma_practice", "coursework_worksheet", "milestone_quiz"]
        if new_stage not in valid_stages:
            return False
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET current_stage = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (new_stage, self.user_id))
            conn.commit()
        return True

    def mark_coursework_completed(self) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET coursework_completed = 1, current_stage = 'milestone_quiz', updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (self.user_id,))
            conn.commit()
        return True

    def mark_quiz_passed(self, accuracy: float = 100.0) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET quiz_passed = 1, cumulative_accuracy = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (accuracy, self.user_id))
            conn.commit()
        return True

    def can_advance(self) -> bool:
        state = self.get_state()
        return state["coursework_completed"] and state["quiz_passed"]

    def advance_to_next_chapter(self) -> bool:
        state = self.get_state()
        if not self.can_advance():
            return False

        current_idx = state["current_chapter_idx"]
        next_idx = min(18, current_idx + 1)
        completed = list(state["completed_chapters"])
        if current_idx not in completed:
            completed.append(current_idx)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET current_chapter_idx = ?,
                    current_stage = 'lecture',
                    coursework_completed = 0,
                    quiz_passed = 0,
                    completed_chapters = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (next_idx, json.dumps(completed), self.user_id))
            conn.commit()
        return True

    def log_failed_question(self, question_id: str):
        state = self.get_state()
        queue = state["failed_questions_queue"]
        if question_id not in queue:
            queue.append(question_id)
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE learner_state
                    SET failed_questions_queue = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (json.dumps(queue), self.user_id))
                conn.commit()

    def resolve_failed_question(self, question_id: str):
        state = self.get_state()
        queue = state["failed_questions_queue"]
        if question_id in queue:
            queue.remove(question_id)
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE learner_state
                    SET failed_questions_queue = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (json.dumps(queue), self.user_id))
                conn.commit()

    def get_startup_greeting(self) -> str:
        state = self.get_state()
        c_idx = state["current_chapter_idx"]
        title = CHAPTER_NAMES.get(c_idx, f"Chapter {c_idx}")
        stage = state["current_stage"]
        stage_desc = {
            "lecture": "exploring the core grammatical concept and syntactic formula",
            "dilemma_practice": "navigating our story-driven communicative dilemma",
            "coursework_worksheet": "completing our interactive practice worksheet",
            "milestone_quiz": "tackling our chapter milestone quiz"
        }.get(stage, "our lesson")

        return (
            f"Hello Bhupendra! Buddy here. We're on Chapter {c_idx} of your English Grammar course: "
            f"{title}. Right now we are {stage_desc}. "
            f"Ready to master this pattern?"
        )

    def get_roadmap(self) -> List[Dict[str, Any]]:
        state = self.get_state()
        curr_idx = state["current_chapter_idx"]
        completed = set(state["completed_chapters"])

        roadmap = []
        for i in range(1, 19):
            if i in completed:
                status = "completed"
            elif i == curr_idx:
                status = "active"
            else:
                status = "locked"

            roadmap.append({
                "chapter_idx": i,
                "title": CHAPTER_NAMES.get(i, f"Chapter {i}"),
                "status": status,
                "is_current": (i == curr_idx)
            })
        return roadmap

    def log_isomorphic_mutation(
        self,
        original_q_id: str,
        mutated_q_id: str,
        original_text: str,
        mutated_text: str,
        rule_citation: str,
        student_pass: bool = False
    ):
        """Audit log isomorphic question generation and learner outcome."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO isomorphic_mutation_audit (
                        user_id, original_question_id, mutated_question_id, original_text, mutated_text, rule_citation, student_pass
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (self.user_id, original_q_id, mutated_q_id, original_text, mutated_text, rule_citation, int(student_pass)))
                conn.commit()
        except Exception as e:
            system_logger.warning(f"Failed to log isomorphic audit: {e}")

    def get_isomorphic_audits(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve logged (original_question, mutated_question, student_pass/fail) triples from SQLite."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, original_question_id, mutated_question_id, original_text, mutated_text, rule_citation, student_pass, created_at
                    FROM isomorphic_mutation_audit
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (self.user_id, limit))
                rows = cursor.fetchall()
                return [
                    {
                        "id": r["id"],
                        "user_id": r["user_id"],
                        "original_question_id": r["original_question_id"],
                        "mutated_question_id": r["mutated_question_id"],
                        "original_text": r["original_text"],
                        "mutated_text": r["mutated_text"],
                        "rule_citation": r["rule_citation"],
                        "student_pass": bool(r["student_pass"]),
                        "created_at": r["created_at"]
                    }
                    for r in rows
                ]
        except Exception as e:
            system_logger.error(f"Error retrieving isomorphic audits: {e}")
            return []

    def audit_mutation_drift(self) -> Dict[str, Any]:
        """Calculate drift and performance metrics across mutated questions."""
        audits = self.get_isomorphic_audits(limit=500)
        total = len(audits)
        if total == 0:
            return {"total_mutations": 0, "pass_count": 0, "fail_count": 0, "pass_rate": 0.0, "status": "no_audits"}
        passes = sum(1 for a in audits if a["student_pass"])
        fails = total - passes
        return {
            "total_mutations": total,
            "pass_count": passes,
            "fail_count": fails,
            "pass_rate": round((passes / total) * 100.0, 2),
            "status": "active_monitoring"
        }

    def get_tutor_state(self) -> Dict[str, Any]:
        state = self.get_state()
        active_info = self.get_active_chapter()
        return {
            "active_mode": state.get("active_mode", "buddy"),
            "current_topic": state.get("current_topic", "Nouns: Concrete, Abstract & Countable"),
            "pending_homework": state.get("pending_homework"),
            "homework_status": state.get("homework_status", "none"),
            "mastered_patterns": state.get("mastered_patterns", []),
            "current_chapter_idx": active_info["chapter_idx"],
            "current_chapter_title": active_info["title"],
            "stage": state.get("current_stage", "lecture")
        }

    def activate_tutor_mode(self, topic: Optional[str] = None) -> Dict[str, Any]:
        state = self.get_state()
        new_topic = topic or state.get("current_topic") or "Nouns: Concrete, Abstract & Countable"
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET active_mode = 'tutor',
                    current_topic = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (new_topic, self.user_id))
            conn.commit()
        return self.get_tutor_state()

    def exit_tutor_mode(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET active_mode = 'buddy',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (self.user_id,))
            conn.commit()
        return self.get_tutor_state()

    def assign_homework(self, task: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET pending_homework = ?,
                    homework_status = 'pending',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (task, self.user_id))
            conn.commit()
        return True

    def complete_homework(self, evaluation: str = "completed") -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET pending_homework = NULL,
                    homework_status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (self.user_id,))
            conn.commit()
        return True

    def record_pattern_mastery(self, pattern: str, passed: bool) -> List[str]:
        state = self.get_state()
        mastered = list(state.get("mastered_patterns", []))
        if passed and pattern not in mastered:
            mastered.append(pattern)
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE learner_state
                    SET mastered_patterns = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (json.dumps(mastered), self.user_id))
                conn.commit()
        return mastered

    def save_lecture_session(
        self,
        topic: str,
        submodule: str,
        phase_index: int,
        spoken_summary: str,
        paragraphs: List[str],
        canvas_type: str = "particle_classifier",
        canvas_config: Optional[Dict[str, Any]] = None,
        session_type: str = "grammar_mastery",
        repetition_items: Optional[List[Dict[str, Any]]] = None,
        key_takeaways: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Persists a generated dynamic lecture session into SQLite."""
        lecture_id = f"lec_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        cfg = canvas_config or {}
        if key_takeaways:
            cfg["key_takeaways"] = key_takeaways
        reps = repetition_items or []
            
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lecture_sessions (
                    id, user_id, topic, submodule, phase_index, session_type, spoken_summary, paragraphs, canvas_type, canvas_config, repetition_items
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lecture_id,
                self.user_id,
                topic,
                submodule,
                phase_index,
                session_type,
                spoken_summary,
                json.dumps(paragraphs),
                canvas_type,
                json.dumps(cfg),
                json.dumps(reps)
            ))
            conn.commit()

        return {
            "id": lecture_id,
            "topic": topic,
            "submodule": submodule,
            "phase_index": phase_index,
            "session_type": session_type,
            "spoken_summary": spoken_summary,
            "paragraphs": paragraphs,
            "key_takeaways": key_takeaways or [],
            "canvas_type": canvas_type,
            "canvas_config": cfg,
            "repetition_items": reps,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_lecture_history(self, limit: int = 30, session_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves past generated lecture sessions for student revision and review."""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                if session_type:
                    cursor.execute("""
                        SELECT id, topic, submodule, phase_index, session_type, spoken_summary, paragraphs, canvas_type, canvas_config, repetition_items, created_at
                        FROM lecture_sessions
                        WHERE user_id = ? AND session_type = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (self.user_id, session_type, limit))
                else:
                    cursor.execute("""
                        SELECT id, topic, submodule, phase_index, session_type, spoken_summary, paragraphs, canvas_type, canvas_config, repetition_items, created_at
                        FROM lecture_sessions
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (self.user_id, limit))
                rows = cursor.fetchall()
                
                lectures = []
                for r in rows:
                    try:
                        paras = json.loads(r["paragraphs"])
                    except Exception:
                        paras = [r["paragraphs"]]
                    try:
                        cfg = json.loads(r["canvas_config"])
                    except Exception:
                        cfg = {}
                    try:
                        reps = json.loads(r["repetition_items"]) if "repetition_items" in r.keys() and r["repetition_items"] else []
                    except Exception:
                        reps = []
                    st = r["session_type"] if "session_type" in r.keys() and r["session_type"] else "grammar_mastery"
                    lectures.append({
                        "id": r["id"],
                        "topic": r["topic"],
                        "submodule": r["submodule"],
                        "phase_index": r["phase_index"],
                        "session_type": st,
                        "spoken_summary": r["spoken_summary"],
                        "paragraphs": paras,
                        "key_takeaways": cfg.get("key_takeaways", []),
                        "canvas_type": r["canvas_type"],
                        "canvas_config": cfg,
                        "repetition_items": reps,
                        "timestamp": r["created_at"]
                    })
                return lectures
        except Exception as e:
            system_logger.error(f"Error fetching lecture history: {e}")
            return []

    def get_learner_preferences(self) -> Dict[str, Any]:
        """Retrieves learner preferences (analogy styles, pacing, interests)."""
        state = self.get_state()
        raw = state.get("learner_preferences")
        if raw:
            try:
                return json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                pass
        return {"analogy_style": "everyday", "pacing": "steady", "interest": "general"}

    def update_learner_preferences(self, prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Updates learner preferences in SQLite."""
        curr = self.get_learner_preferences()
        curr.update(prefs)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE learner_state
                SET learner_preferences = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (json.dumps(curr), self.user_id))
            conn.commit()
        return curr

    def get_curriculum_catalog(self) -> Dict[str, Any]:
        """Returns comprehensive modular course structure across all 4 practice domains."""
        return {
            "domains": {
                "grammar_mastery": {
                    "title": "Grammar Mastery",
                    "icon": "GraduationCap",
                    "description": "Deep-dive syntactic rules, concord, morphology, and competitive exam accuracy.",
                    "modules": [
                        {
                            "id": "nouns_5_phase",
                            "topic": "Nouns & Determiners",
                            "phases": [
                                {"phase": 1, "submodule": "Concrete vs Abstract Nouns", "canvas_type": "particle_classifier", "focus": "Sensory perception vs Cognitive concepts"},
                                {"phase": 2, "submodule": "Countable vs Uncountable (Mass Nouns)", "canvas_type": "particle_classifier", "focus": "Discrete units vs Continuous masses (much/many, fewer/less)"},
                                {"phase": 3, "submodule": "Collective Nouns & Syntactic Concord", "canvas_type": "concord_balance", "focus": "Unitary singular vs Individual plural concord"},
                                {"phase": 4, "submodule": "Compound Nouns & Head Noun Pluralization", "canvas_type": "compound_builder", "focus": "Identifying head nouns (mothers-in-law, passersby)"},
                                {"phase": 5, "submodule": "Possessive Genitives & Joint Ownership", "canvas_type": "noun_hierarchy", "focus": "Joint (Tom and Mary's) vs Separate (Tom's and Mary's) ownership"}
                            ]
                        },
                        {
                            "id": "verbs_and_statives",
                            "topic": "Verbs & Aspect",
                            "phases": [
                                {"phase": 1, "submodule": "Action vs Stative Verbs", "canvas_type": "particle_classifier", "focus": "Progressive aspect restrictions with perception verbs"},
                                {"phase": 2, "submodule": "Gerunds vs Infinitives", "canvas_type": "concord_balance", "focus": "Verbs followed by -ing vs to-infinitive"}
                            ]
                        },
                        {
                            "id": "sentence_inversions",
                            "topic": "Sentence Transformations",
                            "phases": [
                                {"phase": 1, "submodule": "Auxiliary Verb Inversions", "canvas_type": "concord_balance", "focus": "Negative adverbial fronting (Hardly had I, Seldom do we)"},
                                {"phase": 2, "submodule": "Cleft Sentences for Emphasis", "canvas_type": "compound_builder", "focus": "It-clefts and Wh-cleft structures"}
                            ]
                        }
                    ]
                },
                "sentence_repetition": {
                    "title": "Daily Sentence Repetition & Shadowing",
                    "icon": "Repeat",
                    "description": "Natural spoken cadence, connected speech, contractions, and voice shadowing.",
                    "modules": [
                        {
                            "id": "spoken_contractions",
                            "topic": "Conversational Fluency",
                            "phases": [
                                {"phase": 1, "submodule": "Everyday Spoken Contractions", "canvas_type": "repetition_flow", "focus": "Natural rhythm of wanna, gonna, could've, what're you"},
                                {"phase": 2, "submodule": "Connected Speech & Linking", "canvas_type": "repetition_flow", "focus": "Consonant-to-vowel linking and intrusive glides"}
                            ]
                        }
                    ]
                },
                "workplace_office": {
                    "title": "Workplace & Office English",
                    "icon": "Briefcase",
                    "description": "Professional polite softening, executive presence, indirect inquiries, and feedback.",
                    "modules": [
                        {
                            "id": "polite_softening",
                            "topic": "Workplace Communication",
                            "phases": [
                                {"phase": 1, "submodule": "Polite Requests & Softening", "canvas_type": "workplace_matrix", "focus": "Transforming blunt imperatives into diplomatic inquiries"},
                                {"phase": 2, "submodule": "Meeting Interjections & Disagreement", "canvas_type": "workplace_matrix", "focus": "Professional interruptions and diplomatic disagreement"}
                            ]
                        }
                    ]
                },
                "conversational_banter": {
                    "title": "Conversational Banter & Daily Talk",
                    "icon": "MessageCircle",
                    "description": "Natural social dialogue, storytelling, humor, and reactive expressions.",
                    "modules": [
                        {
                            "id": "social_banter",
                            "topic": "Everyday Conversation",
                            "phases": [
                                {"phase": 1, "submodule": "Casual Small Talk & Banter", "canvas_type": "repetition_flow", "focus": "Icebreakers, empathy sounds, and natural conversation flow"},
                                {"phase": 2, "submodule": "Storytelling Connectors", "canvas_type": "compound_builder", "focus": "Anecdote pacing and punchy discourse markers"}
                            ]
                        }
                    ]
                }
            },
            "chapters": CHAPTER_NAMES
        }

    def get_dynamic_course_session(
        self,
        topic: str = "Nouns",
        submodule: Optional[str] = None,
        session_type: str = "grammar_mastery",
        phase_index: int = 1
    ) -> Dict[str, Any]:
        """Dynamically synthesizes structured educational lecture paragraphs, spoken summaries,
        canvas configurations, and repetition drills grounded in local reference materials.
        """
        # Determine submodule if not provided
        if not submodule:
            if topic.lower().startswith("noun"):
                noun_phases = [
                    "Concrete vs Abstract Nouns",
                    "Countable vs Uncountable (Mass Nouns)",
                    "Collective Nouns & Syntactic Concord",
                    "Compound Nouns & Head Noun Pluralization",
                    "Possessive Genitives & Joint Ownership"
                ]
                submodule = noun_phases[min(max(phase_index - 1, 0), len(noun_phases) - 1)]
            elif session_type == "workplace_office":
                submodule = "Polite Requests & Softening"
            elif session_type == "sentence_repetition":
                submodule = "Everyday Spoken Contractions"
            else:
                submodule = "Course Foundations & Fluency"

        # Search local store / RAG for verified reference citations
        citations = []
        if langgraph_engine:
            try:
                results = langgraph_engine.search_knowledge(f"{topic} {submodule}", limit=3)
                for r in results:
                    src = r.get("source_title")
                    if src and src not in citations:
                        citations.append(src)
            except Exception:
                pass

        citation_str = f" [Cited: {', '.join(citations)}]" if citations else ""
        prefs = self.get_learner_preferences()
        analogy_style = prefs.get("analogy_style", "everyday")

        # Query curriculum_store for canonical node or style variant
        from engines import curriculum_store
        node_slug = f"ch{phase_index}_{submodule.lower().replace(' ', '_').replace('&', 'and')}"
        
        variant = None
        if analogy_style != "everyday":
            variant = curriculum_store.get_variant(node_slug, analogy_style) or curriculum_store.get_variant(submodule, analogy_style)

        node = curriculum_store.get_node(node_slug) or curriculum_store.get_node(submodule)

        if node:
            spoken = node.get("core_concept") or node.get("title", submodule)
            paras = node.get("lecture_paragraphs", [])
            canvas_type = node.get("canvas_type", "classifier")
            canvas_cfg = node.get("canvas_config", {})
            takeaways = [
                f"Core Concept: {node.get('core_concept', '')}",
                f"Topic: {node.get('title', submodule)}",
                f"Citations: {', '.join(node.get('citations', [])) or 'Standard Grammar'}"
            ]
            reps = [
                {"prompt": "Repeat target pattern:", "target": f"Key practice for {submodule}.", "drill_type": "Daily Talk", "audio_cue": "Smooth natural cadence", "notes": "Grammar practice."}
            ]

            if variant:
                paras = variant.get("lecture_paragraphs") or paras
                canvas_cfg = variant.get("canvas_config") or canvas_cfg

            return {
                "topic": topic,
                "submodule": submodule,
                "phase_index": phase_index,
                "session_type": session_type,
                "spoken_summary": spoken,
                "paragraphs": paras,
                "key_takeaways": takeaways,
                "canvas_type": canvas_type,
                "canvas_config": canvas_cfg,
                "repetition_items": reps
            }

        # Fallback for unseeded/new submodules
            takeaways = [
                "Concrete = sensory perception (sight, touch, smell, hearing, taste).",
                "Abstract = cognitive constructs, emotional states, concepts, and virtues.",
                "Abstract nouns resist direct pluralization (*honesty, not honesties)."
            ]
            reps = [
                {"prompt": "Say this sentence:", "target": "She showed tremendous courage during the project.", "drill_type": "Daily Talk", "audio_cue": "Stress 'courage' smoothly without pluralizing", "notes": "Abstract noun stays singular."}
            ]

        elif "countable" in submodule.lower() or "uncountable" in submodule.lower() or "mass" in submodule.lower():
            spoken = "Countable nouns are distinct units you can number like three apples or five laptops, while uncountable nouns are continuous masses like water, advice, and information. Remember, uncountable nouns never take an 's' ending or the article 'a'."
            paras = [
                f"Countable nouns represent discrete, individual entities that can be numbered directly (e.g., 'one project', 'two questions', 'three books'){citation_str}. They possess both distinct singular and plural forms (typically ending in '-s' or '-es') and comfortably accept the indefinite articles 'a' or 'an' in their singular representation.",
                "Uncountable nouns (mass nouns) refer to substances, liquids, abstract concepts, or collective aggregates that cannot be divided into discrete numbered units without a partitive counter. Crucial examples tested in competitive examinations include 'information', 'advice', 'equipment', 'furniture', 'luggage', and 'research'. These nouns are strictly singular in concord: they take singular verbs ('The equipment is ready') and cannot take 'a/an' or a plural '-s'.",
                "To quantify uncountable nouns, English uses partitive structures: 'a piece of advice', 'three items of furniture', or 'a bottle of water'. Crucially, match your quantifiers: use 'fewer' and 'many' for countable items, but 'less' and 'much' for uncountable masses (e.g., 'less traffic', 'fewer cars')."
            ]
            canvas_type = "particle_classifier"
            canvas_cfg = {
                "title": "Countable vs Uncountable Particle Funnel",
                "categories": ["Countable (Many / Few)", "Uncountable (Much / Little)"],
                "items": [
                    {"name": "Apples", "category": "Countable (Many / Few)", "type": "countable"},
                    {"name": "Water", "category": "Uncountable (Much / Little)", "type": "uncountable"},
                    {"name": "Advice", "category": "Uncountable (Much / Little)", "type": "uncountable"},
                    {"name": "Laptops", "category": "Countable (Many / Few)", "type": "countable"},
                    {"name": "Information", "category": "Uncountable (Much / Little)", "type": "uncountable"},
                    {"name": "Furniture", "category": "Uncountable (Much / Little)", "type": "uncountable"},
                    {"name": "Coins", "category": "Countable (Many / Few)", "type": "countable"},
                    {"name": "Money", "category": "Uncountable (Much / Little)", "type": "uncountable"}
                ]
            }
            takeaways = [
                "Countable: accept numbers, plural -s, and 'a/an' (e.g., a chair, 5 chairs).",
                "Uncountable: no -s, no 'a/an', singular verbs (e.g., advice, information, furniture).",
                "Quantifiers: Many/Fewer for countable vs Much/Less for uncountable."
            ]
            reps = [
                {"prompt": "Repeat with correct quantifier:", "target": "Could you give me some advice on this?", "drill_type": "Shadowing", "audio_cue": "Never say 'an advice'", "notes": "Use 'some advice' or 'a piece of advice'."},
                {"prompt": "Quantifier practice:", "target": "There are fewer cars on the road today, so there is less traffic.", "drill_type": "Shadowing", "audio_cue": "Link 'fewer cars' and 'less traffic'", "notes": "Fewer for countable, Less for mass."}
            ]

        elif "collective" in submodule.lower() or "concord" in submodule.lower():
            spoken = "Collective nouns represent a group acting as a single unit, like a team or a committee. When acting together in unison, use a singular verb like 'The team is winning', but if members are acting individually, use a plural verb like 'The team are arguing'."
            paras = [
                f"Collective nouns designate a singular lexical entity that refers to an assembly of individual people or items, such as 'team', 'committee', 'jury', 'faculty', and 'government'{citation_str}. Syntactically, collective nouns possess dynamic concord: they trigger either singular or plural grammatical agreement depending on speaker focus.",
                "When the group behaves as an integrated, unified whole with a singular focus or decision, formal syntax requires singular agreement: 'The committee has approved the proposal.' Here, the collective noun functions as a solitary unit, matching singular auxiliary 'has' and pronoun 'its'.",
                "Conversely, when individual members within the collective are acting independently or experiencing conflict, plural concord is employed: 'The jury are still debating among themselves.' Inserting 'members of...' easily resolves ambiguity."
            ]
            canvas_type = "concord_balance"
            canvas_cfg = {
                "title": "Collective Concord Scale",
                "noun": "The Committee",
                "singular_sentence": "The committee IS unanimous in its decision.",
                "plural_sentence": "The committee ARE divided in their opinions.",
                "active_mode": "unitary"
            }
            takeaways = [
                "Unitary Action: Singular verb + singular pronoun (The team is ready for its match).",
                "Divided Action: Plural verb + plural pronoun (The team are putting on their coats).",
                "Clarity: Insert 'members of the...' to avoid ambiguity."
            ]
            reps = [
                {"prompt": "Say unitary agreement:", "target": "The committee has announced its final verdict.", "drill_type": "Daily Talk", "audio_cue": "Keep 'has' and 'its' singular", "notes": "One decision = singular."},
                {"prompt": "Say divided agreement:", "target": "The jury are currently divided on the verdict.", "drill_type": "Shadowing", "audio_cue": "Stress 'are divided'", "notes": "Disagreement = plural concord."}
            ]

        elif "compound" in submodule.lower() or "head" in submodule.lower():
            spoken = "Compound nouns join words together, like passerby, mother-in-law, or software engineer. When making them plural, always add the 's' to the main head noun, giving you passersby and mothers-in-law."
            paras = [
                f"Compound nouns are formed when two or more independent words combine into a single grammatical entity{citation_str}. They appear in solid form (blackboard), hyphenated form (runner-up, mother-in-law), and open form (software engineer).",
                "The core syntactical principle of compound morphology is identifying the head noun—the lexical anchor that denotes the essential nature of the person or object. In 'passer-by', the head noun is 'passer'. In 'mother-in-law', the head noun is 'mother'.",
                "Avoid placing '-s' on prepositions. The grammatically sanctioned plurals are passersby (not passerbys), mothers-in-law (not mother-in-laws), and runners-up (not runner-ups)."
            ]
            canvas_type = "compound_builder"
            canvas_cfg = {
                "title": "Compound Head-Noun Inspector",
                "compounds": [
                    {"full": "Mother-in-law", "head": "Mother", "modifier": "-in-law", "correct_plural": "Mothers-in-law", "wrong_plural": "Mother-in-laws"},
                    {"full": "Passer-by", "head": "Passer", "modifier": "-by", "correct_plural": "Passers-by", "wrong_plural": "Passer-bys"},
                    {"full": "Runner-up", "head": "Runner", "modifier": "-up", "correct_plural": "Runners-up", "wrong_plural": "Runner-ups"},
                    {"full": "Attorney General", "head": "Attorney", "modifier": "General", "correct_plural": "Attorneys General", "wrong_plural": "Attorney Generals"}
                ]
            }
            takeaways = [
                "Identify the Head Noun before pluralizing.",
                "Pluralize the Head Noun: Passersby, Mothers-in-law, Runners-up.",
                "Never place the '-s' on prepositions (*passerbys is incorrect)."
            ]
            reps = [
                {"prompt": "Repeat correctly:", "target": "Several passersby stopped to help after the accident.", "drill_type": "Daily Talk", "audio_cue": "Pronounce 'passers-by' with plural on passers", "notes": "Head noun 'passer' takes the 's'."}
            ]

        elif "possessive" in submodule.lower() or "genitive" in submodule.lower():
            spoken = "Possessive nouns show ownership with an apostrophe. If two people share ownership of one thing, put the apostrophe-s only on the last person, like Tom and Mary's house. If they each own separate houses, put it on both, like Tom's and Mary's houses."
            paras = [
                f"The English genitive case indicates ownership, association, or relational connection{citation_str}. For singular nouns, append apostrophe-s (the student's laptop). For regular plurals ending in -s, append only the apostrophe (the students' laptops).",
                "Irregular plurals that do not end in -s (children, women, people) follow the singular pattern: children's rights, women's soccer, people's choice.",
                "Joint ownership vs separate ownership: When two entities share one joint asset, only the final noun takes the genitive marker: 'Tom and Mary's startup'. If they hold independent startups, both names require apostrophes: 'Tom's and Mary's startups'."
            ]
            canvas_type = "noun_hierarchy"
            canvas_cfg = {
                "title": "Possessive Genitive Matrix",
                "examples": [
                    {"type": "Joint Ownership", "text": "Tom and Mary's house", "meaning": "1 shared house owned together"},
                    {"type": "Separate Ownership", "text": "Tom's and Mary's houses", "meaning": "2 separate houses, 1 each"},
                    {"type": "Plural Possession", "text": "The dogs' collars", "meaning": "Multiple dogs, multiple collars"},
                    {"type": "Irregular Plural", "text": "The children's playground", "meaning": "Irregular plural takes 's"}
                ]
            }
            takeaways = [
                "Regular Plurals: Add only apostrophe (teachers' lounge).",
                "Irregular Plurals: Add 's (children's playground).",
                "Joint Ownership: Apostrophe on final name only (Ben and Jerry's).",
                "Separate Ownership: Apostrophe on each name (Ben's and Jerry's cars)."
            ]
            reps = [
                {"prompt": "Repeat joint ownership:", "target": "We visited Sarah and David's new apartment.", "drill_type": "Shadowing", "audio_cue": "Single 's on David", "notes": "Shared apartment = joint possession."}
            ]

        elif session_type == "workplace_office":
            spoken = "In workplace English, softening direct commands creates a respectful, collaborative tone. Instead of saying 'Send me the report', say 'Could you possibly share the report when you have a moment?'"
            paras = [
                f"Professional workplace communication relies on syntactical softening (hedging) to maintain collaborative rapport without sounding demanding{citation_str}. Direct imperatives ('Finish this by 5') can be perceived as abrupt or confrontational in multinational office environments.",
                "To soften inquiries, speakers use modal past-tenses ('Could you...', 'Would it be possible to...'), continuous progressive aspects ('I was wondering if...'), and minimizing adverbs ('just', 'possibly', 'quick feedback').",
                "Executive presence balances politeness with clarity: never apologize excessively, but structure requests so the colleague feels respected and invited into the workflow rather than commanded."
            ]
            canvas_type = "workplace_matrix"
            canvas_cfg = {
                "title": "Direct vs Softened Workplace Phrasing",
                "pairs": [
                    {"direct": "Send me the deck right now.", "softened": "Could you possibly send over the deck when you get a chance?", "tone": "Collaborative"},
                    {"direct": "You made a mistake here.", "softened": "I noticed a slight discrepancy here; could we take a second look?", "tone": "Constructive"},
                    {"direct": "I don't agree with this plan.", "softened": "I see your perspective, though I have a small reservation regarding the timeline.", "tone": "Diplomatic"}
                ]
            }
            takeaways = [
                "Use modal verbs ('Would you mind...', 'Could you possibly...').",
                "Employ progressive frames ('I was wondering if we could...').",
                "Use constructive minimizing adverbs ('a slight discrepancy', 'a quick check')."
            ]
            reps = [
                {"prompt": "Practice softening:", "target": "Would you mind reviewing this draft when you have a free moment?", "drill_type": "Softening", "audio_cue": "Warm, professional rising cadence", "notes": "Transform blunt command into polite request."},
                {"prompt": "Diplomatic disagreement:", "target": "I see where you're coming from, but could we explore an alternative option?", "drill_type": "Softening", "audio_cue": "Gentle contrast on 'alternative option'", "notes": "Softened dissent."}
            ]

        elif session_type == "sentence_repetition":
            spoken = "Spoken English has a natural music and rhythm where function words contract. Native speakers naturally say 'What are you gonna do?' with linked rhythm, not robotic word-by-word separation."
            paras = [
                f"Natural conversational fluency in English is stress-timed rather than syllable-timed{citation_str}. Content words (nouns, main verbs) are emphasized with length and pitch, while grammatical function words (auxiliaries, prepositions, pronouns) undergo natural phonological reduction.",
                "Common spoken reductions include 'going to' -> 'gonna', 'want to' -> 'wanna', 'could have' -> 'could've' /kʊdəv/, and 'what are you' -> 'what're you' /wʌtʃə/. Practicing sentence repetition and shadowing trains your vocal apparatus to flow naturally without hesitation.",
                "Shadowing—repeating immediately after hearing the cadence—develops automatic muscle memory for English sentence melodies, eliminating mental translation delays."
            ]
            canvas_type = "repetition_flow"
            canvas_cfg = {
                "title": "Spoken Rhythm & Cadence Visualizer",
                "sentences": [
                    {"text": "What're you gonna do after work?", "stressed": ["What", "gonna", "work"], "reduced": ["are", "you", "to", "do"]},
                    {"text": "I could've told you that earlier.", "stressed": ["could've", "told", "earlier"], "reduced": ["I", "you", "that"]},
                    {"text": "Do you wanna grab a quick coffee?", "stressed": ["wanna", "quick", "coffee"], "reduced": ["Do", "you", "grab", "a"]}
                ]
            }
            takeaways = [
                "Stress content words (nouns, main verbs); reduce function words.",
                "Natural spoken contractions: gonna, wanna, could've, what're you.",
                "Sentence repetition builds automatic muscle memory."
            ]
            reps = [
                {"prompt": "Shadow this phrase:", "target": "What're you gonna do after work tonight?", "drill_type": "Shadowing", "audio_cue": "Flow 'what're you gonna' as one fluid beat", "notes": "Stress 'what', 'gonna', 'tonight'."},
                {"prompt": "Shadow contraction:", "target": "I should've known that was coming!", "drill_type": "Shadowing", "audio_cue": "Pronounce 'should've' quickly as 'should-uv'", "notes": "Fast modal reduction."}
            ]

        else: # conversational_banter or general
            spoken = "Good conversational English uses smooth discourse markers and active reactions to keep conversations engaging and natural."
            paras = [
                f"Conversational banter relies on collaborative dialogue signals: acknowledging the other speaker, reflecting their emotion, and linking anecdotes with discourse markers like 'by the way', 'as a matter of fact', or 'speaking of which'{citation_str}.",
                "Unlike textbook grammar drills, natural dialogue tolerates conversational ellipsis (omitting understood words) and expressive intonation. Practicing varied reactions ('No way!', 'That makes total sense', 'Tell me about it') makes you a vibrant conversationalist.",
                "When sharing stories, chronological transition words keep your listener captivated while you organize your thoughts."
            ]
            canvas_type = "repetition_flow"
            canvas_cfg = {
                "title": "Conversational Dialogue Flow",
                "markers": ["By the way...", "Speaking of which...", "To be honest...", "That makes total sense!"]
            }
            takeaways = [
                "Use active listening reactions ('No way!', 'That makes sense!').",
                "Link topics with discourse markers ('Speaking of which...').",
                "Focus on rhythm and warmth rather than rigid syntax."
            ]
            reps = [
                {"prompt": "React casually:", "target": "That makes total sense! Tell me more about how it went.", "drill_type": "Daily Talk", "audio_cue": "Enthusiastic friendly cadence", "notes": "Conversational reaction."}
            ]

        return {
            "topic": topic,
            "submodule": submodule,
            "phase_index": phase_index,
            "session_type": session_type,
            "spoken_summary": spoken,
            "paragraphs": paras,
            "key_takeaways": takeaways,
            "canvas_type": canvas_type,
            "canvas_config": canvas_cfg,
            "repetition_items": reps
        }

    def get_noun_phase_template(self, phase_index: int = 1) -> Dict[str, Any]:
        """Returns dynamically synthesized lesson for a given noun phase without hardcoded dictionaries."""
        return self.get_dynamic_course_session(topic="Nouns", phase_index=phase_index, session_type="grammar_mastery")

    def get_learner_summary(self) -> Dict[str, Any]:
        """Returns complete authoritative state for real-time frontend synchronization."""
        state = self.get_state()
        active_info = self.get_active_chapter()
        drift = self.audit_mutation_drift()
        tutor_state = self.get_tutor_state()
        recent_lectures = self.get_lecture_history(limit=5)
        prefs = self.get_learner_preferences()

        # Check LangGraph active state if available
        lg_mode = state.get("active_mode", "buddy")
        if langgraph_engine:
            try:
                lg_s = langgraph_engine.get_state(self.user_id)
                if lg_s and "active_mode" in lg_s:
                    lg_mode = lg_s["active_mode"]
            except Exception:
                pass
        
        return {
            "user_id": self.user_id,
            "active_chapter": active_info["chapter_idx"],
            "active_chapter_title": active_info["title"],
            "stage": state["current_stage"],
            "active_mode": lg_mode,
            "current_topic": state.get("current_topic", "Nouns: Concrete, Abstract & Countable"),
            "pending_homework": state.get("pending_homework"),
            "homework_status": state.get("homework_status", "none"),
            "mastered_patterns": state.get("mastered_patterns", []),
            "tutor_state": tutor_state,
            "learner_preferences": prefs,
            "recent_lectures": recent_lectures,
            "coursework_completed": state["coursework_completed"],
            "quiz_passed": state["quiz_passed"],
            "cumulative_accuracy": state["cumulative_accuracy"],
            "failed_questions_queue": state["failed_questions_queue"],
            "completed_chapters": state["completed_chapters"],
            "roadmap": self.get_roadmap(),
            "learner_state": {
                "active_chapter": active_info["chapter_idx"],
                "active_mode": lg_mode,
                "current_topic": state.get("current_topic", "Nouns: Concrete, Abstract & Countable"),
                "pending_homework": state.get("pending_homework"),
                "homework_status": state.get("homework_status", "none"),
                "mastered_patterns": state.get("mastered_patterns", []),
                "learner_preferences": prefs,
                "coursework_completed": state["coursework_completed"],
                "milestone_quiz_passed": state["quiz_passed"],
                "chapter_scores": {str(active_info["chapter_idx"]): state["cumulative_accuracy"]},
                "total_errors": len(state["failed_questions_queue"]),
                "total_correct": max(0, 10 - len(state["failed_questions_queue"])),
                "failed_questions_queue": state["failed_questions_queue"]
            },
            "drift_audit": drift
        }


