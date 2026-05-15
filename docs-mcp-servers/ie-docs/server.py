"""MCP Server para documentacion viva de Integral de Empaques.

Expone los markdowns de /docs como Resources MCP y ofrece tools de lectura,
busqueda y edicion. Sin RAG, sin embeddings: acceso directo al filesystem.

Logs estructurados JSON: cada llamada a tool se persiste en /logs/ie-docs.jsonl
con tool, params (sanitizados), duration_ms, status. Rotacion automatica.
"""

import json
import logging
import os
import re
import shutil
import time
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DOCS_DIR = Path(os.environ.get("DOCS_DIR", "/docs")).resolve()
LOG_DIR = Path(os.environ.get("LOG_DIR", "/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Logging estructurado JSON (linea por evento) -> /logs/ie-docs.jsonl
# ---------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        for key in ("tool", "params", "duration_ms", "status", "error",
                    "result_summary"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        return json.dumps(payload, ensure_ascii=False)


_file_handler = RotatingFileHandler(
    LOG_DIR / "ie-docs.jsonl",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(JsonFormatter())
_stdout_handler = logging.StreamHandler()
_stdout_handler.setFormatter(JsonFormatter())

logger = logging.getLogger("ie-docs")
logger.setLevel(logging.INFO)
logger.addHandler(_file_handler)
logger.addHandler(_stdout_handler)
logger.propagate = False


def _sanitize_params(kwargs: dict) -> dict:
    """Trunca content/largo y no loggea nombres que parezcan secretos."""
    safe = {}
    for k, v in kwargs.items():
        if isinstance(v, str) and len(v) > 200:
            safe[k] = v[:200] + f"...<truncated {len(v) - 200} chars>"
        else:
            safe[k] = v
    return safe


def traced(fn):
    """Decora una tool para emitir un evento JSON por invocacion."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            summary = None
            if isinstance(result, list):
                summary = {"count": len(result)}
            elif isinstance(result, dict):
                summary = {k: result[k] for k in list(result)[:5]}
            logger.info(
                "tool_ok",
                extra={
                    "tool": fn.__name__,
                    "params": _sanitize_params(kwargs),
                    "duration_ms": elapsed_ms,
                    "status": "ok",
                    "result_summary": summary,
                },
            )
            return result
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "tool_err",
                extra={
                    "tool": fn.__name__,
                    "params": _sanitize_params(kwargs),
                    "duration_ms": elapsed_ms,
                    "status": "error",
                    "error": f"{type(e).__name__}: {e}",
                },
            )
            raise
    return wrapper


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "ie-docs",
    instructions=(
        "Documentacion viva de sistemas, BDs y procesos de Integral de Empaques. "
        "Usa list_docs para descubrir archivos, read_doc para leer uno completo, "
        "search_docs para buscar substrings, y write_doc/append_doc para editar."
    ),
    host="0.0.0.0",
    port=8000,
    streamable_http_path="/mcp",
)


def _safe_path(name: str) -> Path:
    """Resuelve `name` dentro de DOCS_DIR. Bloquea path traversal y extensiones no .md."""
    if not name.endswith(".md"):
        raise ValueError("Solo se permiten archivos con extension .md")
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError("El nombre no puede contener separadores ni '..'")
    p = (DOCS_DIR / name).resolve()
    if not (p == DOCS_DIR / name or DOCS_DIR in p.parents):
        raise ValueError("Path traversal detectado")
    return p


@mcp.tool()
@traced
def list_docs() -> list[str]:
    """Lista todos los archivos .md disponibles en el directorio de docs."""
    return sorted(p.name for p in DOCS_DIR.glob("*.md"))


@mcp.tool()
@traced
def read_doc(name: str) -> str:
    """Devuelve el contenido completo de un archivo .md."""
    return _safe_path(name).read_text(encoding="utf-8")


@mcp.tool()
@traced
def search_docs(query: str, max_results: int = 50) -> list[dict]:
    """Busca `query` (case-insensitive) en todos los .md. Devuelve [{file, line, snippet}]."""
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[dict] = []
    for p in sorted(DOCS_DIR.glob("*.md")):
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                hits.append({"file": p.name, "line": i, "snippet": line.strip()[:200]})
                if len(hits) >= max_results:
                    return hits
    return hits


@mcp.tool()
@traced
def write_doc(name: str, content: str) -> dict:
    """Sobrescribe (o crea) un archivo .md. Crea backup .md.bak si ya existia."""
    p = _safe_path(name)
    backup_created = False
    if p.exists():
        shutil.copy2(p, p.with_suffix(".md.bak"))
        backup_created = True
    p.write_text(content, encoding="utf-8")
    return {
        "file": p.name,
        "bytes_written": len(content.encode("utf-8")),
        "backup_created": backup_created,
    }


@mcp.tool()
@traced
def append_doc(name: str, content: str) -> dict:
    """Anexa contenido al final de un archivo .md existente."""
    p = _safe_path(name)
    if not p.exists():
        raise ValueError(f"El archivo {name} no existe; usa write_doc para crearlo")
    with p.open("a", encoding="utf-8") as f:
        bytes_written = f.write(content)
    return {"file": p.name, "bytes_appended": bytes_written}


@mcp.resource("doc://{name}")
def get_doc_resource(name: str) -> str:
    """Resource MCP: lee un .md por nombre."""
    return read_doc(name)


if __name__ == "__main__":
    logger.info("ie-docs server starting", extra={"tool": "_startup", "status": "ok"})
    mcp.run(transport="streamable-http")
