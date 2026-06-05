FROM python:3.12-slim

# ---- Microsoft ODBC Driver 18 para SQL Server (necesario para pyodbc) ----
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        curl gnupg ca-certificates unixodbc unixodbc-dev \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
 && apt-get purge -y curl gnupg \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir "mcp[cli]>=1.2.0" "pyodbc==5.2.0"

COPY server.py /app/server.py

# El volumen /dab-configs (read-only) lo monta docker-compose.
ENV DAB_CONFIG_DIR=/dab-configs
ENV ODBC_DRIVER="ODBC Driver 18 for SQL Server"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import socket,sys; s=socket.socket(); s.settimeout(3); \
        s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

CMD ["python", "server.py"]
