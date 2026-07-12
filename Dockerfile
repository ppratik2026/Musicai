FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# For GPU model backends, build with:  docker build --build-arg MODELS=1 .
ARG MODELS=0
COPY requirements-models.txt .
RUN if [ "$MODELS" = "1" ]; then pip install --no-cache-dir -r requirements-models.txt; fi

COPY app ./app
COPY frontend ./frontend

EXPOSE 8000
VOLUME ["/app/data", "/app/checkpoints"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
