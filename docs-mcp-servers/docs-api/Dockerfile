FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn[standard]==0.32.1

COPY api.py .

ENV DAB_CONFIGS_DIR=/dab-configs

EXPOSE 8001

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001"]
