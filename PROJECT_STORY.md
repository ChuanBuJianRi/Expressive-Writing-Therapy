# Project Story: StoryForge

## What Inspired Us

StoryForge **has real psychological healing value**: putting difficult or joyful experiences into narrative form can reduce rumination, improve emotional regulation, and support re-authoring of pivotal moments. It is also **a tool that helps ordinary people express** — to give people who are not professional writers a **deeper expression window**, a stage where they can steer a story and say what matters to them.

We drew on **expressive writing therapy** and **narrative re-authoring**: the practice of turning experience into story has strong evidence behind it. We wanted to scale that *kind* of process — not as a chatbot, but as a **collaborative stage** where multiple AI “agents” act out a story *with* the user, so that the act of *choosing* what happens next becomes part of the work. We were inspired by the idea that your life story is not fixed: you can revisit pivotal moments and imagine different outcomes. StoryForge makes that literal: every chapter ends at a **branching point**. You pick one of three AI-generated continuations, or use the **Story Tree** to go back and try another path. The product is not just text; it’s the experience of *steering* a story that reflects your themes, your world, and your choices.

We added **Memory Mode** as a gentle variant where the “world” is built from a short childhood questionnaire (hometown, best friend, favourite place, a joyful moment, etc.). The same pipeline then runs on that nostalgic setup — same Director, same Character Agents, same branching — so users can relive and re-author positive memories when they choose.

Above all, we care about **helping ordinary people express big ideas in vivid, story form**. Not everyone is a novelist — but everyone can steer a world. StoryForge can be used to tell stories that *show* what abstract issues feel like: **protecting the environment** or **safeguarding endangered species**; a tale set in a dying forest to make climate and environmental loss tangible; a narrative from the ground level of conflict to convey the horror and futility of war; or an allegorical world (like *Animal Farm*) that **reflects social issues** — power, inequality, injustice — through characters and choices. The tool doesn’t preach; it gives users a stage, characters, and branches so they can *discover* and express their own stance. We think of it as a **citizen’s storytelling kit**: a deeper expression window for the issues that matter.

---

## What We Learned

- **Multi-agent systems are coordination problems.** The Director must “see” private states (fears, secrets, desires) that the characters don’t share with each other, then issue *per-scene* instructions. We learned to separate **Phase 1** (Director gathers private states) from **Phase 2** (Director directs the scene). Without that, characters felt generic.

- **Tension as a dial.** We introduced a **tension score** per scene (e.g. τ ∈ [0, 1]). When τ crosses a threshold (e.g. τ ≥ 0.72), the chapter stops and becomes a decision point. This gave us controllable pacing: calm stretches vs. moments where the user *must* choose.

- **Streaming changes UX.** Sending chapter prose via **Server-Sent Events (SSE)** — scene by scene, with optional “Director says…” and “Character acts…” events — made the app feel alive. We learned to design the backend for **incremental events** and the frontend for **append-only** updates.

- **One pipeline, two entry points.** Memory Mode taught us to avoid a second backend. We kept a single story pipeline; Memory Mode only changes the *input* (questionnaire → theme + world + AI-generated characters) and then calls the same `startStory()` and chapter-generation flow. Less code, same behaviour.

---

## How We Built It

**Architecture**

- **Frontend:** Single-page app in one `index.html` (vanilla HTML/CSS/JS, no build). The UI has a resizable left panel (Director + options), a right panel (Stage / Story / Story Tree / Log / Map / Relations), and a draggable bottom bar (Character Agents + Chapter Cast).
- **Backend:** Flask (Python 3.10+), one main blueprint for story APIs. Sessions and story state live in memory (with optional persistence). LLM calls go through a thin `llm_client` that supports OpenAI and compatible APIs (Anthropic, Google) via `base_url` and API key.

**Pipeline (simplified)**

1. **World Builder** — From theme + tags + optional custom setting, one LLM call produces a structured world (name, description, key locations, atmosphere, therapeutic elements).
2. **Chapter Planner** — From world + character list, another call produces a high-level plan for N chapters (we often start with N = 1 and extend).
3. **Director Agent (two phases)**  
   - **Gather private states:** For each character, the Director (via LLM) asks for inner state — desires, fears, secrets — “visible only to the Director.”  
   - **Direct scene:** Given those states + the chapter plan, the Director outputs per-character *stage directions* (emotional beat, physical action, subtext).
4. **Character Agent** — For each character, an LLM generates public action, private thought, dialogue, emotional state, and optional growth moment, conditioned on the Director’s instructions.
5. **Story Composer** — One more LLM call turns (scene plan + Director directions + all character outputs) into **literary prose** (we target a “Denis Johnson / Ishiguro” style: concrete events, distinct voices, minimal filler).
6. **Safety Filter** — Optional pass (e.g. IBM watsonx or keyword fallback) to downrank harmful or anti-therapeutic content.
7. **Decision point** — If scene tension ≥ threshold, we stop the chapter, call **generate-choices** (3 options), and let the user choose. The next chapter can use **extend_story** to plan from the chosen branch.

**Memory Mode**

- User fills a short form (hometown, best friend, favourite place, happy memory, favourite activity, family member, season).
- We build `theme` and `custom_setting` from these answers, call `/api/story/suggest` with `type: initial_characters` to get 3 characters, auto-fill the cast for Chapter 1, then call the same **start** and **generate-chapter** APIs. No separate “memory” backend.

**Data flow**

- Story, chapters, scenes, and character actions are in-memory Python objects; the frontend keeps session id, tree state, and cast per chapter. Export is a simple walk over chapters → scenes → prose to produce a `.txt` file.

---

## Challenges We Faced

1. **Keeping character voices distinct.** Early on, every character sounded like the same “helpful narrator.” We had to tighten prompts (e.g. “Warrior: short, direct sentences. Prophet: poetic, concrete images”) and feed the Director’s *per-character* instructions explicitly into each Character Agent call.

2. **Tension without breaking the mood.** If the threshold was too low, we got a decision point every few paragraphs; too high, and the story felt flat. We tuned the threshold (and the way we compute τ from scene content) so that decision points land at natural “what happens next?” moments.

3. **Streaming and UI state.** The frontend had to handle out-of-order or partial SSE events (e.g. “progress” before “scene”), and avoid clearing the story panel when a new chunk arrived. We standardized event types (`progress`, `log`, `scene`, `chapter`, `decision_point`) and made the UI append-only for story content.

4. **Scope creep on Memory Mode.** We first built a separate “memory” backend (custom world + scene + choices). It duplicated logic and didn’t use the Director/Character pipeline. We scrapped it and made Memory Mode a **different input UI** that feeds the same pipeline — much simpler and consistent.

5. **Cross-browser and CORS.** Serving the frontend as a static file and the backend on another port meant we had to enable CORS and ensure the frontend used the correct `API_BASE` (e.g. `http://localhost:5001`). We also had to test SSE in different browsers to avoid buffering issues.

---

## Summary

StoryForge is a **citizen expression tool** with **psychological healing value**: it helps **ordinary people** say what matters through story — a **deeper expression window** — while expressive writing and narrative re-authoring support emotional regulation and re-authoring of memories. It uses **multi-agent AI** (Director + Character Agents + World Builder + Story Composer) to generate **branching, user-steered stories**. Themes can be **protecting the environment**, **safeguarding endangered species**, or (like *Animal Farm*) **reflecting social issues** — power, inequality, injustice — so users can express their stance through allegory and choice; **Memory Mode** adds a gentle path for reliving and re-authoring positive memories. A **tension-based** decision mechanism controls when the user must choose among three continuations; a **Story Tree** lets them backtrack and re-author. We built it to show that citizen storytelling can be collaborative, interactive, and grounded in one clear pipeline — and that “tell your story” can be a real window for deeper expression.
