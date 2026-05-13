# OCW Canvas backend — Python 3.12 + Node (for the Claude Code CLI the Agent SDK drives).
FROM python:3.12-slim

# System deps: curl/ca-certs (uv installer, nodesource), then Node 20.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# uv (Astral) — fast Python package manager.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Claude Code CLI — the Agent SDK shells out to it when CLAUDE_CODE_OAUTH_TOKEN is set.
# Harmless when the Anthropic-API fallback (ANTHROPIC_API_KEY) is used instead.
# Verify the binary lands on PATH at build time so a silent install failure can't reach prod.
RUN npm install -g @anthropic-ai/claude-code \
 && which claude \
 && claude --version

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .

ENV PORT=8000
# Apply migrations, then serve. (On Render, set the env vars in the dashboard.)
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
