# Generative UI & Visuals Design System (Phase 2 Blueprint)

This document defines the complete visual, architectural, and component specifications for the **Visuals & Generative Frontend (Phase 2)**.

---

## 1. Aesthetic Identity & Theme

- **Core Theme**: Modern Dark Mode with Tactile Notebook Sketch Elements.
- **Visual Personality**: High-aesthetic, warm editorial precision. Fuses clean dark-mode minimalism (`#0F172A`, `#1E293B`) with playful, hand-crafted visual study accents (neon highlighters, hand-drawn wobbly sketch borders, paper textures, taped sticky notes).
- **Typography Hierarchy**:
  - **Headings & Formulas**: `Outfit`, sans-serif (weights 600, 700) for sharp, modern legibility.
  - **Handwritten Notes & Annotations**: `Caveat` or `Patrick Hand`, cursive (weights 500, 700) for authentic study notebook margin notes.
  - **Body & Bionic Reading**: `Inter`, sans-serif (weights 400, 500, 700).
  - **Code & Syntactic Formulas**: `JetBrains Mono` or `Fira Code`.

---

## 2. Color Palette & Highlight Tokens

```css
:root {
  /* Surface & Background */
  --bg-primary: #0b0f19;
  --bg-secondary: #131b2e;
  --bg-card: rgba(30, 41, 59, 0.7);
  --bg-card-hover: rgba(51, 65, 85, 0.8);
  --border-subtle: rgba(148, 163, 184, 0.15);
  
  /* Highlighter Callout Accents */
  --highlight-yellow: #fef08a; /* Golden Rule Highlighter (Neon Yellow) */
  --highlight-yellow-text: #713f12;
  --highlight-cyan: #cffafe;   /* Sentence Pattern Formula (Cyan) */
  --highlight-cyan-text: #164e63;
  --highlight-purple: #f3e8ff; /* Colloquial Native Idiom (Soft Lilac) */
  --highlight-purple-text: #581c87;
  
  /* Feedback Badges */
  --badge-correct-bg: rgba(34, 197, 94, 0.15);
  --badge-correct-border: #22c55e;
  --badge-error-bg: rgba(239, 68, 68, 0.15);
  --badge-error-border: #ef4444;
  --badge-colloquial-bg: rgba(168, 85, 247, 0.15);
  --badge-colloquial-border: #a855f7;
  --badge-dispute-bg: rgba(245, 158, 11, 0.15);
  --badge-dispute-border: #f59e0b;
  
  /* Sketch Effects */
  --sketch-border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px;
  --sketch-border-width: 2px;
  --sketch-shadow: 4px 4px 0px rgba(0, 0, 0, 0.4);
}
```

---

## 3. CSS Sketch Styling Guidelines

### Hand-Drawn Wobbly Borders
Use CSS asymmetrical border radius with a solid accent border to create natural, hand-drawn study card edges:
```css
.sketch-card {
  border: 2px solid var(--border-subtle);
  border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px;
  box-shadow: 4px 6px 0px rgba(0, 0, 0, 0.3);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
}
.sketch-card:hover {
  transform: translateY(-2px) rotate(-0.5deg);
  box-shadow: 6px 8px 0px rgba(0, 0, 0, 0.45);
}
```

### Taped Sticky Note Accent
```css
.sticky-note {
  position: relative;
  background: #fef9c3;
  color: #1e293b;
  padding: 1.5rem;
  border-radius: 4px;
  transform: rotate(-1.5deg);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
  font-family: 'Caveat', cursive;
}
.sticky-note::before {
  content: "";
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 70px;
  height: 22px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(2px);
  border: 1px dashed rgba(0, 0, 0, 0.15);
}
```

---

## 4. Bionic Reading Engine Specification

Bionic Reading guides the reader's eye by bolding the initial 30–50% of characters in each word.

### Conversion Algorithm (JavaScript)
```javascript
function toBionic(text) {
  return text.split(/\s+/).map(word => {
    if (word.length <= 1) return word;
    const mid = word.length <= 3 ? 1 : Math.ceil(word.length * 0.45);
    const boldPart = word.slice(0, mid);
    const rest = word.slice(mid);
    return `<b class="bionic-fixation">${boldPart}</b>${rest}`;
  }).join(' ');
}
```

### Interactive Toggle
The header includes a toggle button:
```html
<button id="toggle-bionic" class="toggle-btn" onclick="toggleBionicReading()">
  <span class="icon">👁️</span> <b>Bion</b>ic Reading: <span id="bionic-status">ON</span>
</button>
```

---

## 5. Declarative Generative UI Component Catalog

When the backend emits `genui_render` over the SSE stream (`/api/stream`), the frontend dynamically mounts the corresponding component from this catalog:

### Component 1: `<QuizCard>`
```json
{
  "type": "genui_render",
  "component": "QuizCard",
  "props": {
    "question_id": "ch1_q08",
    "chapter": 1,
    "stem": "Identify the incorrect portion of this sentence:",
    "sentence": "Neither of the candidates were prepared for the debate.",
    "options": [
      {"id": "A", "text": "were -> was (Subject-Verb Agreement)"},
      {"id": "B", "text": "Neither -> None"},
      {"id": "C", "text": "prepared for -> prepared with"},
      {"id": "D", "text": "No error"}
    ],
    "rule_citation": "Oxford Guide Ch 2 / Arihant Rule 12",
    "allow_dispute": true
  }
}
```

### Component 2: `<ContentionResolver>` (Anti-Hallucination Dispute Card)
Rendered when a user claims the LLM is wrong:
```json
{
  "type": "genui_render",
  "component": "ContentionResolver",
  "props": {
    "user_claim": "'None of them were' is accepted in modern conversational English.",
    "verdict": "PARTIALLY_VALID_REGISTER_DIFFERENCE",
    "formal_rule": "In formal prescriptive grammar (Arihant Rule 9), 'none' with plural countable nouns takes singular verb 'was'.",
    "colloquial_usage": "In modern British & American spoken English (Oxford Ch 19, Cambridge Dictionary), plural verb 'were' is widely accepted.",
    "web_search_snippets": [
      {"title": "Cambridge Dictionary: None", "url": "https://dictionary.cambridge.org/grammar/british-grammar/none", "snippet": "When we use none with of and a plural noun, we can use either a singular or plural verb."}
    ],
    "recommended_recast": "Both forms valid depending on formal vs. casual context."
  }
}
```

### Component 3: `<InteractiveWorksheet>`
Interactive fill-in-the-blank cards with real-time AI checking via `POST /api/check-practice`.

### Component 4: `<BionicSketchNote>`
Visual notebook page with neon highlighter blocks, hand-drawn arrow indicators, and summary cards.

---

## 6. Execution Roadmap
- **Phase 1 (Current Focus)**: Backend core, hybrid vector RAG (`nomic-embed-text` + FTS5), 40-50 question banks, anti-hallucination grounding, story dilemmas, free DuckDuckGo search MCP tool, syllabus tracker, and LiveKit voice agent.
- **Phase 2 (Subsequent Phase)**: Full frontend implementation of the Generative UI engine, CSS sketch theme, Bionic toggle, and interactive worksheets based on this specification.
