# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# System packages for Python deps, pdf tooling, and Ollama install
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        git \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama runtime inside the image
RUN curl -fsSL https://ollama.com/install.sh | sh

# Pull the models used by the application; start the server temporarily
RUN bash -c "set -euo pipefail && ollama serve & until curl -sSf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; do sleep 1; done && ollama pull qwen2.5:1.5b && ollama pull llama3.2:3b && ollama pull mistral && ollama pull llama3.1:8b"

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    OLLAMA_HOST=0.0.0.0 \
    TAVILY_API_KEY=""

CMD ["bash", "-lc", "ollama serve & streamlit run app.py --server.address 0.0.0.0 --server.port ${STREAMLIT_SERVER_PORT}"]
