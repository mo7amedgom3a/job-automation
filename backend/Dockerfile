# =========================
# Builder Stage
# =========================
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    --prefix=/install \
    -r requirements.txt

# =========================
# Playwright Stage
# =========================
FROM python:3.12-slim AS playwright

RUN apt-get update && apt-get install -y \
    libnss3 \
    libgbm1 \
    libasound2 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgtk-3-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir playwright

# =========================
# Runtime Stage
# =========================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Chromium runtime libraries
RUN apt-get update && apt-get install -y \
    libnss3 \
    libgbm1 \
    libasound2 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgtk-3-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Python packages
COPY --from=builder /install /usr/local

# Chromium browser
COPY --from=playwright /root/.cache/ms-playwright /ms-playwright

# Application
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]