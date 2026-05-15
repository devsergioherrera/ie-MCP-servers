FROM python:3.12-slim

WORKDIR /app

# Instalar SDK MCP oficial
RUN pip install --no-cache-dir "mcp[cli]>=1.2.0"

COPY server.py /app/server.py

# Los volumenes /docs y /logs los monta docker-compose
ENV DOCS_DIR=/docs
ENV LOG_DIR=/logs

EXPOSE 8000

# Healthcheck: verifica que el puerto 8000 acepte conexiones TCP
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket,sys; s=socket.socket(); s.settimeout(3); \
        s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

CMD ["python", "server.py"]
