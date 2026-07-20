# DemoVideoBot — Project Overview (Plain Language)

## What is this?

DemoVideoBot is a tool that **automatically creates demo videos** for AI agents.

Instead of someone sitting down, screen-recording themselves using an AI agent, narrating what's happening, and editing the footage — this tool does all of that automatically. You just tell it which agent to demo, and it produces two ready-to-use videos.

---

## What problem does it solve?

Every AI agent on the AgenticQEAHub platform (or any local agent) needs a demo video to show stakeholders, clients, or new users how it works. Making these videos manually is:

- **Time-consuming** — recording, scripting, recording voice-over, editing takes hours
- **Inconsistent** — different people make videos with different quality and style
- **Hard to update** — when the agent changes, the video needs to be re-made from scratch

DemoVideoBot automates the whole process in one click and produces consistent, professional-quality output every time.

---

## What does it produce?

Two video files per agent:

| Video | Description |
|-------|-------------|
| **Narrated video** | Full walkthrough of the agent run with a voice-over explaining each step. Best for presentations and client demos. |
| **Silent video** | A condensed cut with on-screen text captions. No audio — good for embedding in docs or dashboards. |

---

## How does it work? (Step by step)

Think of it as an assembly line with 8 stations:

```
1. Find the agent         — looks up the agent's description and purpose
2. Record the run         — logs in, runs the agent, records the screen
3. Write the script       — AI reads the recording and writes a narration
4. You review the script  — you can edit lines before any video is made
5. Generate voice-over    — text-to-speech turns the script into audio
6. Build narrated video   — combines the recording + audio into one file
7. Build silent video     — makes a caption-only version of the same run
8. Deliver outputs        — validates both files and saves them to a folder
```

The whole thing runs in the background. You submit the job, wait ~10–15 minutes, review the script when prompted, and collect the finished videos.

---

## Who uses it and how?

**The person making the demo video:**

1. Opens the web interface in their browser
2. Chooses the source:
   - **Platform (Hub)** — types the project name and agent name exactly as shown in AgenticQEAHub
   - **Standalone Folder** — pastes the path to a local agent folder (which has a `demo_config.yaml` file)
3. Optionally adds custom instructions ("focus on the Neo4j lookup step", "use formal tone")
4. Clicks **Start Pipeline** and waits
5. When the script is ready, reviews and edits the narration lines if needed
6. Clicks **Approve** — videos are assembled automatically
7. Collects the two `.mp4` files from the `output/` folder

---

## What technology does it use?

You do not need to understand these to use the tool — this is just for context:

| What | Technology | Why |
|------|-----------|-----|
| Web UI | React | Lets you submit jobs, review scripts, and see results in a browser |
| Backend server | Python (FastAPI) | Handles requests and runs the pipeline |
| Pipeline engine | LangGraph | Manages the 8-step workflow and the human review pause |
| Browser automation | Playwright | Logs into the platform, runs the agent, records the screen |
| Script writing | Google Gemini | AI that reads the run transcript and writes the narration |
| Voice-over | Edge TTS | Converts the script text to speech (free, no API limits) |
| Video editing | FFmpeg | Merges recordings, audio, and captions into the final videos |

---

## What does it NOT do?

- It does not publish videos anywhere — it just saves them to a folder
- It does not record audio from the actual agent — it generates a narration from scratch
- It does not edit the agent or change how it works
- The visual quality of the recording depends on what the agent's UI looks like

---

## Two types of agents

### Platform agents (Hub mode)
Agents that live on the AgenticQEAHub platform. The tool logs in using your credentials, navigates to the agent, runs it with the pre-configured test inputs, and records everything automatically.

### Standalone agents (Standalone mode)
Agents that run locally on your machine — Python scripts, Gradio apps, CLI tools, etc. You point the tool at the folder, and it launches the agent and records the screen.

For standalone agents you create a `demo_config.yaml` file in the agent folder that tells DemoVideoBot how to run it, what inputs to provide, and when it's done. See [STANDALONE_AGENT_MODE.md](STANDALONE_AGENT_MODE.md) for the full spec.

---

## Where do the files go?

```
output/
├── narrated_<agent_name>.mp4   ← full video with voice-over
└── silent_<agent_name>.mp4     ← condensed video with captions
```

Intermediate files (raw recordings, audio clips) are automatically cleaned up after the final videos are assembled.

---

## Setting it up

See [INSTALL.md](INSTALL.md) for the full step-by-step setup guide.

The short version:
1. Install Python 3.11+, Node.js, and FFmpeg
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your credentials and API key
4. Start the backend: `uvicorn app.api.routes:app --reload`
5. Start the frontend: `cd frontend && npm run dev`
6. Open `http://localhost:5173`
