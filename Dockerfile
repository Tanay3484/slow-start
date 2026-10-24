# One image: the built app and the Python backend (TabPFN v2 on CPU), served by one process.

# ---- stage 1: build the pixel-art app ----
FROM node:20-slim AS app
WORKDIR /app
COPY app/package.json app/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/ ./
RUN npm run build

# ---- stage 2: the backend ----
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TABPFN_MODEL_CACHE_DIR=/opt/tabpfn \
    TABPFN_ALLOW_CPU_LARGE_DATASET=1
WORKDIR /srv

# CPU-only torch first (the default wheel pulls in gigabytes of CUDA libraries).
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/slowstart backend/slowstart
RUN pip install -e "backend[model]"

# Bake the TabPFN v2 weights (Apache 2.0) into the image so a restart never downloads them, and so the
# licence-gated 2.5+ weights are never fetched. This line must stay above the ENV lines below so
# Render reuses the cached layer.
COPY scripts/bake_tabpfn.py /tmp/bake_tabpfn.py
RUN python /tmp/bake_tabpfn.py

COPY --from=app /app/dist /srv/app/dist

ENV SS_STATIC_DIR=/srv/app/dist \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8000')+'/api/health')"
CMD ["sh", "-c", "exec uvicorn --factory slowstart.api:app_factory --host 0.0.0.0 --port ${PORT:-8000}"]
