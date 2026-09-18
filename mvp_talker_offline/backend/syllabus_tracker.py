import os
import json
import sqlite3
import contextlib
from typing import Dict, Any, List, Optional
from structured_logger import system_logger

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
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
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
                INSERT OR IGNORE INTO learner_state (user_id, current_chapter_idx, current_stage)
                VALUES (?, 1, 'lecture')
            """, (self.user_id,))
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
                    "completed_chapters": []
                }
            return {
                "user_id": row["user_id"],
                "current_chapter_idx": row["current_chapter_idx"],
                "current_stage": row["current_stage"],
                "coursework_completed": bool(row["coursework_completed"]),
                "quiz_passed": bool(row["quiz_passed"]),
                "cumulative_accuracy": float(row["cumulative_accuracy"]),
                "failed_questions_queue": json.loads(row["failed_questions_queue"] or "[]"),
                "completed_chapters": json.loads(row["completed_chapters"] or "[]"),
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

    def get_learner_summary(self) -> Dict[str, Any]:
        """Returns complete authoritative state for real-time frontend synchronization."""
        state = self.get_state()
        active_info = self.get_active_chapter()
        drift = self.audit_mutation_drift()
        return {
            "user_id": self.user_id,
            "active_chapter": active_info["chapter_idx"],
            "active_chapter_title": active_info["title"],
            "stage": state["current_stage"],
            "coursework_completed": state["coursework_completed"],
            "quiz_passed": state["quiz_passed"],
            "cumulative_accuracy": state["cumulative_accuracy"],
            "failed_questions_queue": state["failed_questions_queue"],
            "completed_chapters": state["completed_chapters"],
            "roadmap": self.get_roadmap(),
            "learner_state": {
                "active_chapter": active_info["chapter_idx"],
                "coursework_completed": state["coursework_completed"],
                "milestone_quiz_passed": state["quiz_passed"],
                "chapter_scores": {str(active_info["chapter_idx"]): state["cumulative_accuracy"]},
                "total_errors": len(state["failed_questions_queue"]),
                "total_correct": max(0, 10 - len(state["failed_questions_queue"])),
                "failed_questions_queue": state["failed_questions_queue"]
            },
            "drift_audit": drift
        }

