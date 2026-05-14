FROM python:3.12-slim

WORKDIR /app

# Instalar SDK MCP oficial
RUN pip install --no-cache-dir "mcp[cli]>=1.2.0"

COPY server.py /app/server.py

# El volumen /docs lo monta docker-compose
ENV DOCS_DIR=/docs

EXPOSE 8000

CMD ["python", "server.py"]
