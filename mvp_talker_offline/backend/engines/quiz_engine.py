import os
import json
import random
from typing import Dict, Any, List, Optional
from engines.syllabus_tracker import SyllabusTracker
from core.structured_logger import genui_logger

from core.config import DATA_DIR, BANKS_DIR
DATA_DIR = str(DATA_DIR)
BANKS_DIR = str(BANKS_DIR)

# Isomorphic sentence generation templates across all curriculum chapters
ISOMORPHIC_MUTATIONS = {
    "subject_verb_agreement_indefinite": [
        {
            "stem": "Neither of the two laptops ______ equipped with the required software.",
            "options": ["was", "were", "are", "have been"],
            "correct_answer": "was",
            "explanation": "'Neither' is an indefinite singular pronoun requiring singular verb 'was' (Oxford Ch 2 / Arihant Rule 12)."
        },
        {
            "stem": "Each of the new employees ______ assigned a mentor on day one.",
            "options": ["is", "are", "were", "have been"],
            "correct_answer": "is",
            "explanation": "'Each' is grammatically singular and requires singular verb 'is'."
        },
        {
            "stem": "One of the chief architects ______ presenting the blueprint today.",
            "options": ["is", "are", "were", "have been"],
            "correct_answer": "is",
            "explanation": "Subject is 'One', not 'architects'; requires singular verb 'is'."
        }
    ],
    "past_simple_negative": [
        {
            "stem": "The lead engineer did not ______ the server malfunction yesterday.",
            "options": ["detect", "detected", "detecting", "had detected"],
            "correct_answer": "detect",
            "explanation": "After auxiliary 'did not', always use bare infinitive 'detect' (not detected)."
        },
        {
            "stem": "She did not ______ her passport at the embassy.",
            "options": ["forget", "forgot", "forgotten", "forgetting"],
            "correct_answer": "forget",
            "explanation": "After auxiliary 'did not', use base form 'forget'."
        }
    ],
    "auxiliary_do_does": [
        {
            "stem": "Transform into question: \"The system requires regular maintenance.\"",
            "options": [
                "Does the system require regular maintenance?",
                "Do the system require regular maintenance?",
                "Is the system require maintenance?",
                "The system requires maintenance isn't it?"
            ],
            "correct_answer": "Does the system require regular maintenance?",
            "explanation": "Third-person singular takes 'Does' and main verb reverts to base form 'require'."
        },
        {
            "stem": "Transform into question: \"He manages the regional distribution center.\"",
            "options": [
                "Does he manage the regional distribution center?",
                "Do he manage the center?",
                "Is he manage the center?",
                "Did he manages the center?"
            ],
            "correct_answer": "Does he manage the regional distribution center?",
            "explanation": "Third-person singular takes 'Does' + base verb 'manage'."
        }
    ],
    "stative_continuous": [
        {
            "stem": "Spot the error: \"I am understanding the complex mathematical formula now.\"",
            "options": ["am understanding -> understand", "No error", "formula -> formulas", "now -> today"],
            "correct_answer": "am understanding -> understand",
            "explanation": "'Understand' is a stative verb of cognition; it does not take progressive tense (Oxford Ch 9 / Arihant P. 12)."
        },
        {
            "stem": "Spot the error: \"She is possessing three vintage sports cars in her collection.\"",
            "options": ["is possessing -> possesses", "No error", "three -> third", "in -> at"],
            "correct_answer": "is possessing -> possesses",
            "explanation": "'Possess' is a stative verb of ownership; use simple present 'possesses'."
        }
    ],
    "affirmative_to_negative_inversion": [
        {
            "stem": "Never ______ such breathtaking natural scenery in my entire life.",
            "options": ["have I witnessed", "I have witnessed", "did I witnessed", "had I witness"],
            "correct_answer": "have I witnessed",
            "explanation": "'Never' at clause front requires subject-auxiliary inversion: 'have I witnessed'."
        },
        {
            "stem": "Rarely ______ the company announce sudden leadership restructuring.",
            "options": ["does", "is", "has", "do"],
            "correct_answer": "does",
            "explanation": "'Rarely' with singular company triggers present tense inversion with 'does'."
        }
    ],
    "softening_commands_and_polite_requests": [
        {
            "stem": "Would you mind ______ the quarterly report before the executive briefing?",
            "options": ["reviewing", "to review", "review", "reviewed"],
            "correct_answer": "reviewing",
            "explanation": "'Would you mind' requires a gerund (-ing form)."
        },
        {
            "stem": "Could you possibly ______ me access to the project database?",
            "options": ["grant", "granting", "to grant", "granted"],
            "correct_answer": "grant",
            "explanation": "Modal 'Could you' requires bare infinitive 'grant'."
        }
    ],
    "auxiliary_inversion_questions": [
        {
            "stem": "______ either of your colleagues planning to attend the conference?",
            "options": ["Is", "Are", "Were", "Have"],
            "correct_answer": "Is",
            "explanation": "'Either' is grammatically singular and takes singular verb 'Is'."
        }
    ],
    "wh_word_syntax_and_preposition_stranding": [
        {
            "stem": "______ of these three frameworks would be best suited for our microservices?",
            "options": ["Which", "What", "Who", "Whose"],
            "correct_answer": "Which",
            "explanation": "'Which' is used for selective choice among a defined set."
        }
    ],
    "tag_polarity_and_embedded_clauses": [
        {
            "stem": "Do you know what time ______?",
            "options": ["the meeting starts", "does the meeting start", "is the meeting start", "starts the meeting"],
            "correct_answer": "the meeting starts",
            "explanation": "Indirect questions follow standard affirmative clause order (Subject + Verb)."
        }
    ],
    "there_is_are_stative_descriptions": [
        {
            "stem": "There ______ several critical bugs reported in the latest software build.",
            "options": ["are", "is", "was", "has been"],
            "correct_answer": "are",
            "explanation": "Existential 'there' agrees with the post-verbal plural subject 'several critical bugs'."
        }
    ],
    "verbs_of_perception_adjectives_vs_adverbs": [
        {
            "stem": "The freshly baked sourdough bread smells ______.",
            "options": ["wonderful", "wonderfully", "in wonder", "most wonderfully"],
            "correct_answer": "wonderful",
            "explanation": "Sensory copular verbs take predicate adjectives, not manner adverbs."
        }
    ],
    "spatial_and_temporal_prepositions": [
        {
            "stem": "The code review must be fully completed ______ Friday at 5 PM.",
            "options": ["by", "until", "for", "since"],
            "correct_answer": "by",
            "explanation": "'By' denotes a completion deadline; 'until' denotes continuous duration."
        }
    ],
    "verb_complementation_ing_vs_to": [
        {
            "stem": "Please remember ______ the server backup before logging off.",
            "options": ["to trigger", "triggering", "triggered", "trigger"],
            "correct_answer": "to trigger",
            "explanation": "'Remember to do' refers to executing a future duty or task."
        }
    ],
    "fanboys_compound_clauses": [
        {
            "stem": "The server crashed unexpectedly, ______ the backup system restored operations instantly.",
            "options": ["yet", "so", "for", "nor"],
            "correct_answer": "yet",
            "explanation": "'Yet' expresses a coordinating adversative contrast."
        }
    ],
    "adverbial_clauses_of_condition_and_time": [
        {
            "stem": "______ the deployment was delayed, the end user experience remained seamless.",
            "options": ["Although", "In spite of", "Despite of", "Because"],
            "correct_answer": "Although",
            "explanation": "'Although' introduces a finite subordinate clause with subject and verb."
        }
    ],
    "transitive_passive_and_agentless": [
        {
            "stem": "The vulnerability was ______ by the independent security auditor.",
            "options": ["discovered", "discovering", "discover", "discovers"],
            "correct_answer": "discovered",
            "explanation": "Passive voice with auxiliary 'was' takes past participle 'discovered'."
        }
    ],
    "zero_first_second_third_mixed_conditionals": [
        {
            "stem": "If we ______ automated unit testing earlier, we would have prevented these bugs.",
            "options": ["had implemented", "would have implemented", "implemented", "have implemented"],
            "correct_answer": "had implemented",
            "explanation": "Third conditional if-clause requires past perfect ('had implemented')."
        }
    ],
    "participial_phrases_and_clauses": [
        {
            "stem": "______ the system logs carefully, the engineer identified the root cause.",
            "options": ["Having examined", "Examined", "Being examined", "Having being examined"],
            "correct_answer": "Having examined",
            "explanation": "Perfect participle 'Having examined' denotes an action completed prior to the identification."
        }
    ],
    "fronted_adverbials_and_inversion": [
        {
            "stem": "Only after the thorough audit ______ the discrepancies resolved.",
            "options": ["were", "was", "did", "have"],
            "correct_answer": "were",
            "explanation": "Fronted 'Only after...' triggers auxiliary inversion with plural 'discrepancies': 'were'."
        }
    ],
    "it_clefts_and_wh_clefts": [
        {
            "stem": "It was the senior architect ______ redesigned the core database schema.",
            "options": ["who", "which", "whom", "what"],
            "correct_answer": "who",
            "explanation": "It-cleft focusing on a human subject ('the senior architect') takes relative pronoun 'who'."
        }
    ],
    "discourse_markers_and_cohesion": [
        {
            "stem": "The new architecture is scalable; ______, it significantly reduces cloud hosting expenditure.",
            "options": ["moreover", "otherwise", "nonetheless", "on the contrary"],
            "correct_answer": "moreover",
            "explanation": "'Moreover' acts as an additive formal discourse marker introducing corroborating positive value."
        }
    ]
}

class QuizEngine:
    def __init__(self, syllabus_tracker: Optional[SyllabusTracker] = None):
        self.tracker = syllabus_tracker or SyllabusTracker()

    def load_quiz_bank(self, chapter_idx: int) -> List[Dict[str, Any]]:
        """Load the 40-50 question bank for the specified chapter."""
        bank_path = os.path.join(BANKS_DIR, f"chapter_{chapter_idx:02d}_bank.json")
        if not os.path.exists(bank_path):
            return []
        try:
            with open(bank_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            genui_logger.error(f"Error reading quiz bank for chapter {chapter_idx}: {e}")
            return []

    def get_milestone_quiz(self, chapter_idx: int, count: int = 10) -> List[Dict[str, Any]]:
        """Retrieve a balanced 10-15 question milestone exam from the 40-50 bank."""
        bank = self.load_quiz_bank(chapter_idx)
        if not bank:
            return []
        # Return a diverse sample covering spot-error, transformation, and fill-in
        count = min(count, len(bank))
        selected = random.sample(bank, count)
        return selected

    def get_checkpoint_quiz(self, chapter_idx: int, count: int = 3) -> List[Dict[str, Any]]:
        """Quick 3-question pulse check during lesson."""
        bank = self.load_quiz_bank(chapter_idx)
        if not bank:
            return []
        return random.sample(bank, min(count, len(bank)))

    def get_on_demand_quiz(self, chapter_idx: int, count: int = 5) -> List[Dict[str, Any]]:
        """Instant quiz triggered when user says 'Quiz me' or 'Test me'."""
        bank = self.load_quiz_bank(chapter_idx)
        if not bank:
            return []
        return random.sample(bank, min(count, len(bank)))

    def mutate_isomorphic(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Isomorphic Question Mutation Algorithm:
        When a question is failed, generate a fresh question with the EXACT SAME
        grammatical obstacle, but completely new nouns, verbs, and scenario context.
        """
        iso_template = question.get("isomorphic_template", {})
        trap_type = iso_template.get("trap_type", "subject_verb_agreement_indefinite")

        candidates = ISOMORPHIC_MUTATIONS.get(trap_type)
        if candidates:
            chosen = random.choice(candidates)
            mutated = dict(question)
            mutated["id"] = f"{question['id']}_iso_{random.randint(100, 999)}"
            mutated["question"] = f"[Isomorphic Practice] {chosen['stem']}"
            mutated["sentence"] = chosen["stem"]
            mutated["options"] = chosen["options"]
            mutated["correct_answer"] = chosen["correct_answer"]
            mutated["explanation"] = f"Isomorphic remediation: {chosen['explanation']}"
            mutated["is_isomorphic"] = True
            return mutated

        # Fallback mutation: mutate the subject/objects of the original question using lexical slot substitution
        import re
        mutated = dict(question)
        mutated["id"] = f"{question['id']}_iso_{random.randint(100, 999)}"
        orig_q = question.get("question", "")
        replacements = [
            ("the manager", "the director"), ("the engineer", "the architect"),
            ("the candidates", "the applicants"), ("the team", "the committee"),
            ("the software", "the system"), ("yesterday", "last week"),
            ("the report", "the proposal"), ("the book", "the manuscript"),
            ("the client", "the stakeholder"), ("the students", "the researchers")
        ]
        new_q = orig_q
        for old_w, new_w in replacements:
            if old_w in new_q.lower():
                new_q = re.sub(re.escape(old_w), new_w, new_q, flags=re.IGNORECASE)
                break
        if new_q == orig_q:
            new_q = f"Fresh practice variant: {orig_q}"
        mutated["question"] = f"[Isomorphic Practice] {new_q}"
        mutated["sentence"] = new_q
        mutated["is_isomorphic"] = True
        return mutated

    def evaluate_answer(
        self,
        question: Dict[str, Any],
        user_answer: str
    ) -> Dict[str, Any]:
        """
        Verify the user's answer against pre-verified ground truth.
        If failed, immediately generates an isomorphic question!
        """
        expected = str(question.get("correct_answer", "")).strip().lower()
        actual = str(user_answer).strip().lower()

        # Check direct match or option letter match (e.g. user said "A" or "Option A")
        is_correct = False
        if actual == expected:
            is_correct = True
        elif actual in expected or expected in actual:
            is_correct = True
        else:
            # Check options letter
            options = question.get("options", [])
            for idx, opt in enumerate(options):
                letter = chr(65 + idx).lower() # a, b, c, d
                if actual in [letter, f"option {letter}", f"({letter})"]:
                    if opt.strip().lower() == expected or expected in opt.strip().lower():
                        is_correct = True
                        break

        if is_correct:
            self.tracker.resolve_failed_question(question["id"])
            if question.get("is_isomorphic"):
                self.tracker.log_isomorphic_mutation(
                    original_q_id=question.get("id", "").split("_iso")[0],
                    mutated_q_id=question.get("id", ""),
                    original_text=question.get("question", ""),
                    mutated_text=question.get("question", ""),
                    rule_citation=question.get("rule_citation", ""),
                    student_pass=True
                )
            return {
                "is_correct": True,
                "feedback": "Correct! Excellent grasp of this grammatical structure.",
                "explanation": question.get("explanation", ""),
                "rule_citation": question.get("rule_citation", "")
            }
        else:
            self.tracker.log_failed_question(question["id"])
            if question.get("is_isomorphic"):
                self.tracker.log_isomorphic_mutation(
                    original_q_id=question.get("id", "").split("_iso")[0],
                    mutated_q_id=question.get("id", ""),
                    original_text=question.get("question", ""),
                    mutated_text=question.get("question", ""),
                    rule_citation=question.get("rule_citation", ""),
                    student_pass=False
                )
            # Generate isomorphic question for instant reinforcement
            iso_q = self.mutate_isomorphic(question)
            self.tracker.log_isomorphic_mutation(
                original_q_id=question.get("id", ""),
                mutated_q_id=iso_q.get("id", ""),
                original_text=question.get("question", question.get("sentence", "")),
                mutated_text=iso_q.get("question", iso_q.get("sentence", "")),
                rule_citation=question.get("rule_citation", ""),
                student_pass=False
            )
            return {
                "is_correct": False,
                "feedback": f"Not quite. The correct answer is: {question.get('correct_answer')}.",
                "explanation": question.get("explanation", ""),
                "rule_citation": question.get("rule_citation", ""),
                "isomorphic_question": iso_q
            }
