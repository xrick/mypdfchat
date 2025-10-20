Streamlit Custom Components

This folder contains a custom Streamlit component that demonstrates UI customization by providing a rich‑text, multi‑line text field.

Contents
- rich_text_area: Python wrapper + frontend source
- demo_app.py: Minimal Streamlit demo app

Quick Start
1) Python deps
   - `pip install streamlit`

2) Frontend build (requires Node 16+)
   - `cd streamlit_components/rich_text_area/frontend`
   - `npm install`
   - `npm run build`  # outputs to `dist/`

3) Run demo
   - `cd` to repository root
   - `streamlit run streamlit_components/demo_app.py`

Development (optional)
- Start the Vite dev server:
  - `cd streamlit_components/rich_text_area/frontend && npm run dev`
- In another terminal, run Streamlit with dev mode for the component:
  - `ST_RICH_TEXT_DEV=1 streamlit run streamlit_components/demo_app.py`

