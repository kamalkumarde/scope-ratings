# --- Stage 1: Build & Dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install Debian compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .

# Package all wheels together
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# --- Stage 2: Final Runtime Environment ---
FROM python:3.11-slim

WORKDIR /app

# Install runtime system library dependencies for postgresql
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy everything built over from Stage 1
COPY --from=builder /app/wheels /app/wheels
COPY --from=builder /app/requirements.txt .

# Install packaged extensions from local wheels
RUN pip install --no-cache-dir --no-index --find-links=/app/wheels -r requirements.txt \
    && rm -rf /app/wheels

# Copy code modules
COPY config/ /app/config/
COPY data/ /app/data/
COPY src/ /app/src/
COPY main.py /app/main.py

ENV PYTHONUNBUFFERED=1

# Expose FastAPI's target interface port
EXPOSE 8000

# Keep your batch pipeline process as the default image entrypoint
CMD ["python", "main.py"]