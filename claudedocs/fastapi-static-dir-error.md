Fix: RuntimeError "Directory 'static' does not exist" when running via Streamlit

Summary
- You ran `streamlit run app_fastapi_ollama.py` and saw: `RuntimeError: Directory 'static' does not exist`.
- Root cause: `app_fastapi_ollama.py` is a FastAPI app that mounts Starlette static files and Jinja templates. It expected `static/` and `templates/` to exist and also should be run with Uvicorn, not Streamlit.

What changed in this repo
- Added the required folders and minimal assets:
  - `static/style.css`
  - `templates/index.html`
- Made the FastAPI static/template paths robust (file‑relative) in `app_fastapi_ollama.py` so they work regardless of current working directory.
- Clarified how to run each entry point in `how_to_run.txt`.

How to run correctly
1) FastAPI backend (for `app_fastapi_ollama.py`)
   - Install deps (example): `pip install fastapi uvicorn jinja2 python-multipart PyPDF2`
   - Start server: `uvicorn app_fastapi_ollama:app --reload`
   - Open: `http://localhost:8000/`

2) Streamlit apps
   - Original app: `streamlit run app_original.py`
   - Custom component demo: `streamlit run streamlit_components/demo_app.py`

Why `streamlit run app_fastapi_ollama.py` failed
- `app_fastapi_ollama.py` is not a Streamlit script. It uses FastAPI + Starlette `StaticFiles` and `Jinja2Templates`. When Streamlit executed the file, Starlette attempted to mount a relative `static/` directory that didn’t exist at the time, raising the runtime error.

File‑relative path fix (already applied)
- In `app_fastapi_ollama.py`, static/template directories now derive from the file location:
  - `BASE_DIR = Path(__file__).resolve().parent`
  - `STATIC_DIR = BASE_DIR / "static"`
  - `TEMPLATE_DIR = BASE_DIR / "templates"`
  - `app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")`
  - `templates = Jinja2Templates(directory=str(TEMPLATE_DIR))`

Verification checklist
- `static/` and `templates/` exist in the repo root.
- `uvicorn app_fastapi_ollama:app --reload` starts without errors.
- Visiting `http://localhost:8000/` renders the HTML page.
- PDF upload to `/upload-pdf/` returns a JSON success payload.
- `/chat/` responds with an answer and updated `history`.

Troubleshooting
- 404 on static assets: ensure the server is running at `http://localhost:8000/` and `static/style.css` exists.
- Port already in use: stop other processes or use `--port 8001`.
- Missing dependencies: install `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `PyPDF2` and your LangChain/FAISS/HF stack.

