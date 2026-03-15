# StoryForge — Multi-Agent Branching Story Generator

StoryForge is an interactive AI story creation platform rooted in **expressive writing therapy** — the evidence-based practice of using narrative to process emotions, reframe lived experiences, and foster psychological healing.

A **Director Agent** guides the emotional arc of the story while multiple **Character Agents** collaborate in real time, giving voice to different inner perspectives. This mirrors therapeutic techniques where externalizing internal conflicts through fictional characters builds self-awareness and emotional distance from personal pain.

Unlike linear generators, StoryForge turns every chapter into a **branching decision point**. Three distinct paths appear after each chapter. Users can choose a direction, or backtrack through the visual **Story Tree** to explore alternate outcomes — reflecting the therapeutic belief that stories, like lives, can always be re-authored.

---

## ✨ Features

### Story Generation
- **Multi-agent collaboration** — Director Agent plans scenes and issues private instructions; Character Agents respond in their own voice; Story Composer weaves everything into literary prose
- **7-stage dramatic arc** — chapters automatically follow Setup → Inciting Incident → Rising Action → Midpoint → Dark Night → Climax → Resolution
- **Real-time SSE streaming** — watch the story unfold live with a scrolling chat log showing Director planning, character private states, public actions, and safety checks
- **AI-assisted story setup** — LLM-generated suggestions for title, theme, world settings, and keyword tags

### Branching & Decision Points
- **3 branch modes** at every decision point:
  - **Choose Mode** — pick from 3 AI-generated story directions
  - **Preview Mode** — read 250-320 word prose previews of 2 different continuations before committing
  - **Director Mode** — write your own creative direction and the Director crafts a custom continuation
- **Backtrack** — restore any previous chapter and explore alternate paths

### Characters
- **Preset characters** — 5 ready-to-use characters (Healer, Guardian, Seeker, Shadow, Innocent) with distinct voices
- **Custom characters** — create your own with name, personality, background, secrets, and role
- **Add characters mid-story** — introduce new characters at any chapter
- **AI avatar generation** — generate character portraits via DALL-E 3
- **Character profiles** — expandable profile drawer with edit mode and full action/thought history
- **Cast strip** — drag-and-drop characters into per-chapter cast assignments
- **Distinct voice system** — each character type (Soldier, Seer, Young Hero, Antagonist) has enforced speech patterns

### World Building
- **4 preset worlds** — Enchanted Forest, Future City, Timeless Town, Dream Realm
- **Custom world generation** — describe your setting and the AI builds a full world config with locations, atmosphere, time period, and therapeutic elements
- **Keyword picker** — organized by Environment, Atmosphere, Era, and Special Elements (with AI generation)

### Visualization
- **Story Tree** — interactive SVG tree showing all chapters, scenes, and branching paths; click any node to backtrack
- **World Map** — canvas-based map of story locations with visit tracking and detail panels
- **Character Relationship Network** — interactive graph with draggable nodes, long-press to connect characters, AI-detected relationships marked with ✦

### Memory Mode
- **Childhood memory exploration** — a separate therapeutic mode for revisiting nostalgic memories
- **Guided questionnaire** — hometown, best friend, favorite place, happy memory, family member, season
- **Warm second-person narrative** — AI generates sensory-rich scenes from your memories
- **Gentle branching** — 3 positive "what happens next" choices at each scene

### Safety & Quality
- **IBM watsonx.ai safety filter** — evaluates generated content for psychological safety, therapeutic value, and emotional tone
- **Three-tier safety** — watsonx.ai (primary) → LLM fallback → keyword heuristics
- **Banned phrase enforcement** — Story Composer filters atmospheric clichés; hard events must land

### Interface
- **Draggable panel layout** — resize left/right panels and the character bar freely
- **5 right-panel tabs** — Story, Story Tree, World Map, Relations, Chat Log
- **Provider flexibility** — supports OpenAI, Anthropic Claude, and Google Gemini with runtime switching
- **Export** — download your full story as a `.txt` file

---

## 🌐 Live Demo

- Web Page: [https://s3.ca-tor.cloud-object-storage.appdomain.cloud/expressive-writing-frontend/index.html](https://s3.ca-tor.cloud-object-storage.appdomain.cloud/expressive-writing-frontend/index.html)


No installation or API key required — the backend is pre-configured, so you can start creating immediately.

---

## 🗂 Project Structure

```
Expressive-Writing-Therapy/
├── index.html              # Frontend (single-file, no build step)
├── Dockerfile              # Container image for IBM Code Engine
├── .env.example            # Environment variable template
└── backend/
    ├── run.py              # Flask entry point (port 5001)
    ├── requirements.txt
    └── app/
        ├── __init__.py     # App factory, CORS setup
        ├── config.py       # Environment-based configuration
        ├── api/
        │   ├── story.py    # Story generation, branching, SSE streaming
        │   ├── config.py   # Dynamic LLM configuration
        │   ├── character.py  # Character presets and creation
        │   ├── world.py      # World presets and generation
        │   └── session.py    # Session management
        ├── models/         # Story, Chapter, Scene, Character data models
        ├── services/
        │   ├── director_agent.py   # Director: scene planning, private queries, orchestration
        │   ├── character_agent.py  # Per-character action and dialogue generation
        │   ├── story_composer.py   # Weaves actions into literary prose
        │   ├── safety_filter.py    # watsonx.ai content safety evaluation
        │   ├── world_builder.py    # World configuration generation
        │   ├── chapter_planner.py  # Multi-chapter arc planning
        │   ├── memory_builder.py   # Memory Mode scene generation
        │   └── preset_manager.py   # Preset worlds and characters
        └── utils/
            ├── llm_client.py       # OpenAI-compatible LLM client
            └── watsonx_client.py   # IBM watsonx.ai client
```

---

## 🚀 Getting Started

### Option A: Use the live deployment

Visit the [live demo](https://s3.ca-tor.cloud-object-storage.appdomain.cloud/expressive-writing-frontend/index.html) — no installation or API key required. The backend is pre-configured with a shared LLM key, so you can start creating immediately.

---

### Option B: Run locally

#### Prerequisites

- Python 3.10+
- A modern browser (Chrome / Safari / Firefox)

#### 1. Clone the repository

```bash
git clone https://github.com/ChuanBuJianRi/Expressive-Writing-Therapy.git
cd Expressive-Writing-Therapy
```

#### 2. Configure environment variables

Copy the template and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o

# Optional: IBM watsonx.ai for safety filter
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_URL=https://ca-tor.ml.cloud.ibm.com
```

> If `.env` is configured, the setup modal is skipped automatically on launch.

#### 3. Start the backend

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Start the Flask server
python run.py
```

The backend runs at **http://localhost:5001**.

> **Note:** When running locally, update `API_BASE` in `index.html` to `http://localhost:5001`.

> **Every time you restart your machine**, run this to start the backend again:
> ```bash
> cd backend && source venv/bin/activate && python run.py
> ```

#### 4. Open the frontend

Open `index.html` directly in your browser — no build step or local server required:

```bash
# macOS
open index.html

# Or drag index.html into any browser window
```

If you did not configure `.env`, a setup modal will appear on first launch where you can enter your API key.

---

## 🖥 Usage

### Story Mode

1. **Fill in the Director panel** — enter a story title, theme, and world setting (use the keyword picker or AI suggestions)
2. **Configure characters** — use presets or create custom characters; drag them into the cast strip to assign per chapter
3. **Choose options** — select model, chapter length (Brief / Medium / Detailed), and creativity level
4. **Click Start Story** — the agents collaborate to generate Chapter 1 with real-time streaming
5. **Pick a branch** — at each decision point, choose from three modes:
   - **Choose** — select from 3 AI-generated directions
   - **Preview** — read prose previews of 2 continuations before committing
   - **Director** — write your own creative direction
6. **Explore tabs** — Story (prose), Story Tree (branch visualization), World Map (locations), Relations (character network), Chat Log (agent messages)
7. **Export** — click Export in the header to download the full story

### Memory Mode

1. **Switch to Memory Mode** in the left panel
2. **Fill in the questionnaire** — hometown, best friend, favorite place, happy memory, etc.
3. **Start** — the AI generates warm, nostalgic second-person scenes from your memories
4. **Choose gently** — pick from 3 positive directions at each scene

---

## 🔌 API Endpoints

### Story (`/api/story/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/start` | Initialize a new story session |
| `POST` | `/generate-chapter` | Stream chapter generation via SSE |
| `POST` | `/generate-choices` | Generate 3 branch options after decision point |
| `POST` | `/generate-branch-previews` | Generate 2 prose preview continuations |
| `POST` | `/director-chat` | User-directed custom continuation |
| `POST` | `/suggest` | AI suggestions for title / theme / keywords / characters |
| `POST` | `/add-character` | Introduce a new character mid-story |
| `POST` | `/backtrack` | Truncate story to chapter N for re-branching |
| `POST` | `/generate-avatar` | Generate character portrait via DALL-E 3 |
| `POST` | `/user-input` | Record user input for analysis |
| `GET`  | `/relationships/<id>` | Extract character relationships from story |
| `GET`  | `/status/<id>` | Get session status |
| `GET`  | `/export/<id>` | Export full story text |

### Configuration (`/api/config/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/llm` | Update LLM provider / key / model at runtime |
| `GET`  | `/llm` | Get current LLM configuration |

### Characters (`/api/character/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/presets` | List preset characters |
| `POST` | `/create` | Create a custom character |

### Worlds (`/api/world/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/presets` | List preset worlds |
| `POST` | `/generate` | Generate custom world from theme/tags |

### Sessions (`/api/session/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/<id>` | Get session details |
| `GET`  | `/list` | List all sessions |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Health check |

---

## 🧠 Architecture

### Multi-Agent Pipeline

Each chapter is generated through a collaborative pipeline:

1. **Chapter Planner** — plans the dramatic arc across all chapters (7-stage structure)
2. **Director Agent Phase 1** — privately queries each character for emotional state, desires, fears, and secrets
3. **Director Agent Phase 2** — plans 3-4 scenes with hard events, then issues per-character instructions exploiting private intel
4. **Character Agents** — each character generates their public action, dialogue, private thought, and growth moment
5. **Story Composer** — weaves all character actions into literary prose (enforcing hard events, distinct voices, and no atmospheric clichés)
6. **Safety Filter** — evaluates content for psychological safety and therapeutic value via IBM watsonx.ai

### Safety Filter (Three-Tier)

1. **IBM watsonx.ai** (Granite 3-8B) — primary evaluator when configured
2. **Primary LLM fallback** — uses the story generation LLM if watsonx unavailable
3. **Keyword heuristics** — basic danger keyword scanning as last resort

Returns: safety score, therapeutic score, emotional tone, flags, and approval status.

---

## ☁️ Deployment (IBM Cloud)

The app is deployed as two components:

| Component | Service | URL |
|-----------|---------|-----|
| Frontend | IBM Cloud Object Storage | `s3.ca-tor.cloud-object-storage.appdomain.cloud/expressive-writing-frontend/` |
| Backend | IBM Code Engine | `story-forge.27hq7x0nnc07.ca-tor.codeengine.appdomain.cloud` |

### Redeploy the backend

```bash
# Log in to IBM Cloud
ibmcloud login --sso -r ca-tor
ibmcloud target -g Default
ibmcloud cr login

# Build and push the container image
docker build -t ca.icr.io/expressive-writing/backend:latest .
docker push ca.icr.io/expressive-writing/backend:latest

# Update Code Engine app
ibmcloud ce project select --name expressive-writing
ibmcloud ce app update --name story-forge --image ca.icr.io/expressive-writing/backend:latest --wait
```

### Redeploy the frontend

```bash
ibmcloud cos object-put \
  --bucket expressive-writing-frontend \
  --key index.html \
  --body index.html \
  --content-type "text/html; charset=utf-8"
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML / CSS / JS (no framework) |
| Backend | Python · Flask · Flask-CORS · Gunicorn |
| Streaming | Server-Sent Events (SSE) |
| LLM | OpenAI SDK (compatible with Anthropic & Google via base_url) |
| Safety | IBM watsonx.ai (Granite 3-8B) |
| Hosting | IBM Cloud Object Storage (frontend) · IBM Code Engine (backend) |
| Container | Docker · IBM Container Registry |
| State | In-memory session store + localStorage |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
