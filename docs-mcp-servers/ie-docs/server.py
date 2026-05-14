"""MCP Server para documentacion viva de Integral de Empaques.

Expone los markdowns de /docs como Resources MCP y ofrece tools de lectura,
busqueda y edicion. Sin RAG, sin embeddings: acceso directo al filesystem.
"""

import os
import re
import shutil
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DOCS_DIR = Path(os.environ.get("DOCS_DIR", "/docs")).resolve()

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
def list_docs() -> list[str]:
    """Lista todos los archivos .md disponibles en el directorio de docs."""
    return sorted(p.name for p in DOCS_DIR.glob("*.md"))


@mcp.tool()
def read_doc(name: str) -> str:
    """Devuelve el contenido completo de un archivo .md."""
    return _safe_path(name).read_text(encoding="utf-8")


@mcp.tool()
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
    mcp.run(
        transport="streamable-http",
    )
