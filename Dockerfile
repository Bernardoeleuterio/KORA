FROM python:3.13-slim

# git e necessario em tempo de execucao: obsidian_tool.py usa GitPython para
# clonar/sincronizar o Vault do Obsidian (pull --rebase, commit, push).
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
