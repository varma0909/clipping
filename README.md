# ClipForge

ClipForge turns a public YouTube video or a video file you upload into scored, captioned vertical clips. It uses Next.js 14 for the UI and FastAPI for a local background-processing API.

> ClipForge processes videos you are authorized to use. YouTube access, download restrictions, and API provider terms still apply.

## Prerequisites

- Python 3.11
- Node.js 20+
- FFmpeg with `ffmpeg` and `ffprobe` on `PATH`
- Ollama for local, key-free scoring, or an OpenAI/Anthropic API key
- MediaPipe/OpenCV supported Python environment (see troubleshooting)

Install Python 3.11, Node.js 20+, and FFmpeg:

- **Windows:** `winget install Python.Python.3.11`, `winget install OpenJS.NodeJS.LTS`, and `winget install Gyan.FFmpeg`. Restart the terminal after installation.
- **macOS (Homebrew):** `brew install python@3.11 node ffmpeg`
- **Ubuntu/Debian:** `sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip nodejs npm ffmpeg`. Confirm Node is version 20 or newer; use the [Node.js installer](https://nodejs.org/) if the distribution package is older.

Verify the tools are available: `py -3.11 --version` (Windows) or `python3.11 --version`, `node --version`, and `ffmpeg -version`.

For key-free local scoring, install Ollama:

- **Windows:** `winget install Ollama.Ollama`, then restart the terminal.
- **macOS:** `brew install ollama`
- **Linux:** follow the installer at <https://ollama.com/download/linux>.

## Setup

From the project root:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

The default `backend\.env` settings use local Ollama (`LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2.5:3b`) and need no API key. Download the model once:

```powershell
ollama pull qwen2.5:3b
```

Ollama normally starts its local service after installation. If it is not running, start it with `ollama serve`. The model download is a few gigabytes; inference speed depends on your hardware. Alternatively, set `LLM_PROVIDER` to `openai` or `anthropic` and provide the matching API key. Keep provider keys in the backend `.env`, never in the frontend.

`WHISPER_MODEL` defaults to `small`; `LLM_MODEL` and `OLLAMA_BASE_URL` can be overridden.

Install the frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

The requested Next.js 14 line is used here. Current npm advisories include issues with Next 14 that have no fix within that major version; the frontend scripts bind to loopback for local development. Do not expose this version to an untrusted network without upgrading Next.js and revalidating the app.

## Run both servers

Terminal 1 (project root):

```powershell
backend\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm run dev
```

Open <http://localhost:3000>. Jobs are stored in SQLite at `backend/storage/clipforge.db`; job assets live under `backend/storage/{job_id}/` and are removed after `RETENTION_HOURS` (default 24).

## Verification commands

From the project root:

```powershell
backend\.venv\Scripts\Activate.ps1
python -m pytest backend\tests -q
```

Then:

```powershell
cd frontend
npm run build
```

For an end-to-end test, run both servers and submit a short, public video for which you have permission to make clips. The first transcription may take several minutes while faster-whisper downloads its model. Exact model performance depends on your hardware.

## Troubleshooting

- **`ffmpeg`/`ffprobe` not found:** install FFmpeg and restart the terminal after changing `PATH`.
- **Python install failures on Windows:** use Python 3.11 x64 and create a fresh virtual environment. MediaPipe wheels can lag behind newer Python releases.
- **MediaPipe unavailable:** ClipForge logs a warning and uses the blurred-background vertical layout instead of face tracking.
- **Ollama connection/model error:** make sure Ollama is running and `ollama pull qwen2.5:3b` completed. Check `OLLAMA_BASE_URL` if the server is on another address.
- **Hosted LLM configuration error:** check `LLM_PROVIDER`, the corresponding API key, and available provider quota.
- **YouTube download error:** the video may be private, age-restricted, region-blocked, unavailable, or outside your account's permissions. Update `yt-dlp` with `pip install -U yt-dlp`.
- **Slow or out-of-memory transcription:** lower `WHISPER_MODEL` (for example `base`) or use a machine with more memory.
- **Browser API errors:** make sure the backend is listening on port 8000 and `NEXT_PUBLIC_API_URL` in `frontend/.env.local` matches it. CORS allows localhost ports 3000 and 3001 by default.

## API

- `POST /api/jobs` — enqueue a YouTube video URL
- `POST /api/jobs/upload` — upload a video file and enqueue it
- `GET /api/jobs/{job_id}` — status and progress
- `GET /api/jobs/{job_id}/clips` — scored clips
- `GET /api/clips/{clip_id}/download` and `/download/srt`
- `GET /api/jobs/{job_id}/download-all` — ZIP archive

The backend exposes interactive API documentation at <http://127.0.0.1:8000/docs>.
