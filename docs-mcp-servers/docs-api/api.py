"""API de metadata de MCP servers para el sitio web mcp.ie/info.

Escanea dos directorios:
  /dab-configs   → data-mcp-servers/  (DAB: dab-config.json + data-source-files)
  /docs-servers  → docs-mcp-servers/  (Custom: server-meta.json)

Devuelve SOLO campos seguros: nunca connection-string, source.object ni opciones
internas. Los servidores custom describen sus tools directamente en server-meta.json.

Endpoints:
  GET /servers  -> lista unificada de todos los servers
  GET /health   -> {"ok": true}
"""

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DAB_CONFIGS_DIR  = Path(os.environ.get("DAB_CONFIGS_DIR",  "/dab-configs"))
DOCS_SERVERS_DIR = Path(os.environ.get("DOCS_SERVERS_DIR", "/docs-servers"))

app = FastAPI(title="IE MCP Docs API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_entities(entities: dict[str, Any]) -> list[dict]:
    """Extrae campos públicos de entidades DAB. Nunca source.object ni relationship.fields."""
    result = []
    for name, entity in entities.items():
        source = entity.get("source", {})
        permissions = entity.get("permissions", [])
        roles = [p.get("role", "anonymous") for p in permissions]
        result.append({
            "name": name,
            "description": entity.get("description", ""),
            "type": source.get("type", "table"),
            "permissions": roles,
        })
    return result


def _safe_dml_tools(dml_tools: dict[str, bool]) -> dict[str, bool]:
    return {
        "describe_entities":  dml_tools.get("describe-entities", True),
        "read_records":       dml_tools.get("read-records", True),
        "aggregate_records":  dml_tools.get("aggregate-records", False),
        "create_record":      dml_tools.get("create-record", False),
        "update_record":      dml_tools.get("update-record", False),
        "delete_record":      dml_tools.get("delete-record", False),
        "execute_entity":     dml_tools.get("execute-entity", False),
    }


# ---------------------------------------------------------------------------
# Parsers por tipo de server
# ---------------------------------------------------------------------------

def _parse_dab_server(server_id: str, config_dir: Path) -> dict | None:
    """Parsea un directorio con dab-config.json (Data API Builder)."""
    main_path = config_dir / "dab-config.json"
    if not main_path.exists():
        return None

    config = _load_json(main_path)
    if config is None:
        return None

    data_source = config.get("data-source", {})
    mcp = config.get("runtime", {}).get("mcp", {})
    dml_tools = mcp.get("dml-tools", {})

    readonly = not any([
        dml_tools.get("create-record", False),
        dml_tools.get("update-record", False),
        dml_tools.get("delete-record", False),
    ])

    all_entities: dict[str, Any] = dict(config.get("entities", {}))

    # Merge de configs secundarios (data-source-files)
    for secondary_file in config.get("data-source-files", []):
        secondary = _load_json(config_dir / secondary_file)
        if secondary:
            all_entities.update(secondary.get("entities", {}))

    label = server_id.replace("-", " ").replace("_", " ").title()

    return {
        "id": server_id,
        "label": label,
        "database_type": data_source.get("database-type", "mssql"),
        "description": mcp.get("description", ""),
        "readonly": readonly,
        "tools": _safe_dml_tools(dml_tools),
        "entities": _safe_entities(all_entities),
    }


def _parse_custom_server(server_id: str, meta_path: Path) -> dict | None:
    """Parsea un server-meta.json (servidores no-DAB, ej. mcp-ie-docs)."""
    meta = _load_json(meta_path)
    if meta is None:
        return None

    # Entidades custom ya vienen en formato seguro
    entities = []
    for e in meta.get("entities", []):
        entities.append({
            "name": e.get("name", ""),
            "description": e.get("description", ""),
            "type": e.get("type", "tool"),
            "permissions": e.get("permissions", ["anonymous"]),
        })

    return {
        "id": meta.get("id", server_id),
        "label": meta.get("label", server_id),
        "database_type": meta.get("type", "custom"),
        "description": meta.get("description", ""),
        "readonly": meta.get("readonly", True),
        "tools": meta.get("tools", {}),
        "entities": entities,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/servers")
def list_servers() -> dict:
    """Devuelve metadata pública de todos los MCP servers."""
    servers: list[dict] = []

    # 1. data-mcp-servers/ — DAB (dab-config.json) o custom (server-meta.json)
    if DAB_CONFIGS_DIR.exists():
        for config_dir in sorted(DAB_CONFIGS_DIR.iterdir()):
            if not config_dir.is_dir():
                continue
            # DAB tiene prioridad; si no hay dab-config.json, probar server-meta.json
            server = _parse_dab_server(config_dir.name, config_dir)
            if server is None:
                meta_path = config_dir / "server-meta.json"
                if meta_path.exists():
                    server = _parse_custom_server(config_dir.name, meta_path)
            if server is not None:
                servers.append(server)

    # 2. Custom servers (docs-mcp-servers/) — busca server-meta.json en subdirectorios
    if DOCS_SERVERS_DIR.exists():
        for server_dir in sorted(DOCS_SERVERS_DIR.iterdir()):
            if not server_dir.is_dir():
                continue
            meta_path = server_dir / "server-meta.json"
            if not meta_path.exists():
                continue
            server = _parse_custom_server(server_dir.name, meta_path)
            if server is not None:
                servers.append(server)

    return {"servers": servers, "schema_version": "1"}
