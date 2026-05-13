# OCW Canvas — frontend

React + Vite + TypeScript SPA. Canvas-like UI; talks to the FastAPI backend.

## Run locally

```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm run dev                   # http://localhost:5173
```

Start the backend first, and make sure `FRONTEND_ORIGINS` in the backend `.env`
includes `http://localhost:5173`.

## Build / checks

```bash
npm run typecheck
npm run lint
npm run build                 # outputs dist/ (base path /ocw-canvas/ for GitHub Pages)
```
