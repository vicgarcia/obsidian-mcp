FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY obsidian_mcp.py .

RUN pip install --no-cache-dir .

ENV OBSIDIAN_VAULT_PATH=/vault

CMD ["obsidian-mcp"]
