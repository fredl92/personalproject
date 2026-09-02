FROM python:3.12.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src /app/src
RUN useradd --create-home --uid 1000 toolkit && mkdir -p /data/jobs /cache && chown -R toolkit:toolkit /data /cache
ENV PYTHONPATH=/app/src PERSONAL_TOOLKIT_HOME=/app JOBS_DIR=/data/jobs HF_HOME=/cache
USER toolkit
CMD ["python", "-m", "personal_toolkit", "worker"]
