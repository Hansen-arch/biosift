# BioSift Standalone — production image
FROM python:3.12-slim

WORKDIR /app

# install deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code
COPY utils/ ./utils/
COPY standalone/ ./standalone/
COPY app.py ./app.py
COPY views/ ./views/

EXPOSE 8080
# 2 workers; timeout accommodates slow multi-request GBIF bundles
CMD ["uvicorn", "standalone.server:app", "--host", "0.0.0.0", \
     "--port", "8080", "--workers", "2", "--timeout-keep-alive", "120"]
