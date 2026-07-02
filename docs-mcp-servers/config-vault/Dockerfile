FROM python:3.12-slim

WORKDIR /app

# pyjwt[crypto] trae cryptography (RS256); httpx para hablar con el IAM.
RUN pip install --no-cache-dir \
        "mcp[cli]>=1.2.0" \
        "pyjwt[crypto]>=2.8.0" \
        "httpx>=0.27.0"

COPY server.py /app/server.py

# Los volumenes los monta docker-compose:
#   /vault  (rw)  -> almacen central de configs (fuera de git)
#   /keys   (ro)  -> llave publica del IAM (public.pem) y opcional root-ca.pem
#   /logs   (rw)  -> auditoria JSONL
ENV VAULT_DIR=/vault \
    IAM_PUBLIC_KEY_PATH=/keys/public.pem \
    IAM_BASE_URL=https://iam.ie \
    AUDIT_LOG=/logs/config-vault.jsonl

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import socket,sys; s=socket.socket(); s.settimeout(3); \
        s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

CMD ["python", "server.py"]
