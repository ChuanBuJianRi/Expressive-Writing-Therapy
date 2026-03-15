# StoryForge — Multi-Agent Branching Story Generator

> An expressive writing therapy tool powered by multi-agent AI collaboration.

StoryForge is an interactive AI story creation platform rooted in **expressive writing therapy** — the evidence-based practice of using narrative to process emotions, reframe lived experiences, and foster psychological healing.

A **Director Agent** guides the emotional arc of the story while multiple **Character Agents** collaborate in real time, giving voice to different inner perspectives. This mirrors therapeutic techniques where externalizing internal conflicts through fictional characters builds self-awareness and emotional distance from personal pain.

Unlike linear generators, StoryForge turns every chapter into a **branching decision point**. Three distinct paths appear after each chapter. Users can choose a direction, or backtrack through the visual **Story Tree** to explore alternate outcomes — reflecting the therapeutic belief that stories, like lives, can always be re-authored.

---

## ✨ Features

- **AI-assisted story setup** — title, theme, and world-setting generation with a keyword picker
- **Multi-agent collaboration** — Director + Character Agents negotiate plot in real time
- **Branching choices** — 3 AI-generated options after every chapter
- **Story Tree visualization** — interactive SVG tree showing all paths taken; click any node to backtrack
- **Expressive keyword prompts** — world-building keywords organized by Environment, Atmosphere, Era, and Special Elements
- **Draggable panel layout** — resize left/right panels and the character bar freely
- **Provider flexibility** — supports OpenAI, Anthropic Claude, and Google Gemini
- **Export** — download your full story as a `.txt` file

---

## 🗂 Project Structure

```
Expressive-Writing-Therapy/
├── index.html          # Frontend (single-file, no build step)
└── backend/
    ├── run.py          # Flask entry point  (port 5001)
    ├── requirements.txt
    └── app/
        ├── api/
        │   ├── story.py    # Story generation + SSE streaming
        │   └── config.py   # Dynamic LLM configuration
        ├── models/         # Story, Chapter, Character data models
        ├── services/       # Director / Character agent logic
        └── utils/
            └── llm_client.py
```

---

## 🌐 Live Demo

- **Frontend**: [https://s3.ca-tor.cloud-object-storage.appdomain.cloud/expressive-writing-frontend/index.html](https://s3.ca-tor.cloud-object-storage.appdomain.cloud/expressive-writing-frontend/index.html)
- **Backend API**: [https://story-forge.27hq7x0nnc07.ca-tor.codeengine.appdomain.cloud](https://story-forge.27hq7x0nnc07.ca-tor.codeengine.appdomain.cloud)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A modern browser (Chrome / Safari / Firefox)
- An API key from one of: [OpenAI](https://platform.openai.com/api-keys), [Anthropic](https://console.anthropic.com/keys), or [Google AI Studio](https://aistudio.google.com/app/apikey)

---

### Option A: Use the live deployment

Visit the [live demo](https://s3.ca-tor.cloud-object-storage.appdomain.cloud/expressive-writing-frontend/index.html) — no installation required. Configure your API key on first launch and start creating.

---

### Option B: Run locally

#### 1. Clone the repository

```bash
git clone https://github.com/ChuanBuJianRi/Expressive-Writing-Therapy.git
cd Expressive-Writing-Therapy
```

---

#### 2. Start the backend

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

The backend runs at **http://localhost:5001**. Keep this terminal open while using the app.

> **Note:** When running locally, update `API_BASE` in `index.html` to `http://localhost:5001`.

> **Every time you restart your machine**, run this to start the backend again:
> ```bash
> cd backend && source venv/bin/activate && python run.py
> ```

---

#### 3. Open the frontend

Open `index.html` directly in your browser — no build step or local server required:

```bash
# macOS
open index.html

# Or drag index.html into any browser window
```

---

#### 4. Configure your AI provider

On first launch, a setup modal will appear automatically:

1. Select your AI provider (OpenAI / Anthropic / Google)
2. Paste your API key
3. Choose a model
4. Click **Start Creating**

Your settings are saved locally in `localStorage` and synced to the backend on each session start.

---

## 🖥 Usage

1. **Fill in the Director panel** — enter a story title, theme, and world setting (use the keyword picker or AI suggestions)
2. **Configure characters** — edit names, roles, and personalities in the bottom Character Agents bar
3. **Choose options** — select model, chapter length (Brief / Medium / Detailed), and creativity level
4. **Click Start Story** — the agents collaborate to generate Chapter 1
5. **Pick a branch** — three choices appear after each chapter; select one to continue
6. **Explore the Story Tree** — switch to the Story Tree tab to see all branches; click any node to restore that chapter
7. **Export** — click Export in the header to download the full story

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/story/start` | Initialize a new story session |
| `POST` | `/api/story/generate-chapter` | Stream chapter generation (SSE) |
| `POST` | `/api/story/generate-choices` | Generate 3 branch options for next chapter |
| `POST` | `/api/story/suggest` | AI suggestions for title / theme / keywords |
| `GET`  | `/api/story/status/<id>` | Get session status |
| `GET`  | `/api/story/export/<id>` | Export full story text |
| `POST` | `/api/config/llm` | Update LLM provider / key / model |
| `GET`  | `/api/config/llm` | Get current LLM configuration |
| `GET`  | `/health` | Health check |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML / CSS / JS (no framework) |
| Backend | Python · Flask · Flask-CORS · Gunicorn |
| Streaming | Server-Sent Events (SSE) |
| LLM | OpenAI SDK (compatible with Anthropic & Google via base_url) |
| Hosting | IBM Cloud Object Storage (frontend) · IBM Code Engine (backend) |
| State | In-memory session store + localStorage |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
