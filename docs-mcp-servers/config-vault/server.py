"""MCP Server 'ie-config-vault' — importar/exportar archivos de configuracion
sensibles (`.env`, `public.pem`, certificados, llaves, `*.conf`) desde un
almacen central en el servidor, con autenticacion contra el IAM de IE.

Motivacion: tras un `git clone` limpio, el codigo no trae los secretos (viven
solo en `.env`/keys, fuera de git). Este server permite a un agente autenticado
bajar (import) esos archivos al proyecto local y subir (export) versiones nuevas
al almacen central, sin copiarlos a mano ni exponerlos en el repo.

SEGURIDAD (esto sirve secretos — el gating es lo mas importante):
  - **Toda** tool excepto `login` exige un access token JWT del IAM
    (`https://iam.ie`) con rol **Superadmin**. El token se valida LOCALMENTE
    con la llave publica RSA del IAM (RS256): firma, `iss`, `aud`, `exp`. No se
    consulta al IAM en cada request (mismo patron que las apps cliente del IAM).
  - **Path traversal guard**: toda ruta se resuelve bajo VAULT_DIR y se rechaza
    si escapa (`..`, rutas absolutas, symlinks fuera del vault).
  - **Auditoria**: cada import/export se registra en un JSONL (quien, que, sha256,
    cuando, resultado). Nunca se loguea el contenido, solo su hash.
  - El almacen (VAULT_DIR) vive fuera de git y se respalda con el backup mensual.

Tools:
  - login(username_or_email, password): obtiene un access token del IAM.
  - list_configs(token, subdir=""): lista archivos del vault (ruta, tamano,
    mtime, sha256) — NO su contenido.
  - import_config(token, path): devuelve el contenido de un archivo (texto utf-8
    o base64 si es binario).
  - export_config(token, path, content, encoding): escribe/actualiza un archivo
    en el vault (respalda la version previa como .bak).
"""

import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import jwt
from mcp.server.fastmcp import FastMCP

# --- Config por entorno -----------------------------------------------------
VAULT_DIR = Path(os.environ.get("VAULT_DIR", "/vault")).resolve()
IAM_PUBLIC_KEY_PATH = os.environ.get("IAM_PUBLIC_KEY_PATH", "/keys/public.pem")
IAM_BASE_URL = os.environ.get("IAM_BASE_URL", "https://iam.ie").rstrip("/")
IAM_ISSUER = os.environ.get("IAM_ISSUER", "autenticacion.intempaques.com")
IAM_AUDIENCE = os.environ.get("IAM_AUDIENCE", "apps.intempaques.com")
IAM_CA_BUNDLE = os.environ.get("IAM_CA_BUNDLE")  # ruta a root-ca.pem; None = CAs del sistema
REQUIRED_ROLE = os.environ.get("REQUIRED_ROLE", "Superadmin")
AUDIT_LOG = Path(os.environ.get("AUDIT_LOG", "/logs/config-vault.jsonl"))
MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_BYTES", str(5 * 1024 * 1024)))  # 5 MB
HTTP_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "10"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("config-vault")

_PUBLIC_KEY = Path(IAM_PUBLIC_KEY_PATH).read_text(encoding="utf-8")


# --- Auth -------------------------------------------------------------------
def _as_list(v: Any) -> list[str]:
    """El claim role/permiso del IAM puede ser string o array."""
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _verify(token: str) -> dict:
    """Valida el JWT del IAM (RS256) y exige el rol requerido. Devuelve los claims."""
    if not token or not token.strip():
        raise PermissionError("Falta el access token. Autentica primero con login().")
    try:
        claims = jwt.decode(
            token.strip(),
            _PUBLIC_KEY,
            algorithms=["RS256"],
            audience=IAM_AUDIENCE,
            issuer=IAM_ISSUER,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise PermissionError("Token expirado (los access token duran 15 min). Vuelve a login().")
    except jwt.InvalidTokenError as e:
        raise PermissionError(f"Token invalido: {e}")

    if REQUIRED_ROLE not in _as_list(claims.get("role")):
        raise PermissionError(
            f"Acceso denegado: se requiere el rol '{REQUIRED_ROLE}'. "
            f"El usuario '{claims.get('unique_name')}' no lo tiene."
        )
    return claims


def _actor(claims: dict) -> str:
    return f"{claims.get('unique_name', '?')}(sub={claims.get('sub', '?')})"


# --- Vault path safety ------------------------------------------------------
def _safe_path(rel: str) -> Path:
    """Resuelve `rel` bajo VAULT_DIR; rechaza cualquier escape del vault."""
    if not rel or not rel.strip():
        raise ValueError("La ruta no puede estar vacia.")
    rel = rel.strip().lstrip("/\\")
    p = (VAULT_DIR / rel).resolve()
    if p != VAULT_DIR and not p.is_relative_to(VAULT_DIR):
        raise ValueError(f"Ruta fuera del vault rechazada: {rel}")
    return p


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _audit(action: str, actor: str, path: str, ok: bool, detail: str = "", sha: str = "") -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor,
        "path": path,
        "ok": ok,
        "sha256": sha,
        "detail": detail,
    }
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:  # la auditoria nunca debe tumbar la operacion
        logger.warning("No se pudo escribir auditoria: %s", e)
    logger.info("%s ok=%s actor=%s path=%s %s", action, ok, actor, path, detail)


# --- MCP server -------------------------------------------------------------
mcp = FastMCP(
    "ie-config-vault",
    instructions=(
        "Importa/exporta archivos de configuracion sensibles (.env, public.pem, "
        "certificados, llaves, *.conf) desde un almacen central de IE. REQUIERE "
        "autenticacion: primero llama login(usuario, password) para obtener un "
        "access token del IAM, luego pasa ese token a list_configs/import_config/"
        "export_config. Solo usuarios con rol Superadmin. Usa import_config para "
        "bootstrapear un proyecto tras git clone; export_config para publicar un "
        "cert/.env nuevo. Toda operacion queda auditada."
    ),
    host="0.0.0.0",
    port=8000,
    streamable_http_path="/mcp",
)


@mcp.tool()
def login(username_or_email: str, password: str) -> dict:
    """Autentica contra el IAM de IE y devuelve un access token (dura 15 min) mas
    los datos del usuario (roles, permisos). Usa el token devuelto en las demas
    tools. Requiere rol Superadmin para operar sobre el vault."""
    try:
        resp = httpx.post(
            f"{IAM_BASE_URL}/api/auth/login",
            json={"usernameOrEmail": username_or_email, "password": password},
            timeout=HTTP_TIMEOUT,
            verify=IAM_CA_BUNDLE if IAM_CA_BUNDLE else True,
        )
    except Exception as e:
        raise RuntimeError(f"No se pudo contactar al IAM ({IAM_BASE_URL}): {e}")

    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if not resp.is_success or not body.get("exitoso"):
        msg = body.get("mensaje") or f"HTTP {resp.status_code}"
        raise PermissionError(f"Login fallido: {msg}")

    data = body.get("data", {})
    usuario = data.get("usuario", {})
    roles = _as_list(usuario.get("roles"))
    if REQUIRED_ROLE not in roles:
        logger.info("login de %s sin rol %s (roles=%s)", username_or_email, REQUIRED_ROLE, roles)
    return {
        "access_token": data.get("accessToken"),
        "expiracion": data.get("expiracion"),
        "usuario": {
            "username": usuario.get("username"),
            "nombre": usuario.get("nombre"),
            "roles": roles,
        },
        "puede_operar_vault": REQUIRED_ROLE in roles,
    }


@mcp.tool()
def list_configs(token: str, subdir: str = "") -> dict:
    """Lista los archivos disponibles en el vault (ruta relativa, tamano, fecha de
    modificacion y sha256). NO devuelve el contenido. Opcionalmente filtra por un
    subdirectorio (ej. un proyecto). Requiere token Superadmin."""
    claims = _verify(token)
    base = _safe_path(subdir) if subdir else VAULT_DIR
    if not base.exists():
        return {"vault_subdir": subdir, "count": 0, "files": []}

    files = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        try:
            data = p.read_bytes()
        except Exception:
            continue
        st = p.stat()
        files.append({
            "path": str(p.relative_to(VAULT_DIR)).replace("\\", "/"),
            "size": st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            "sha256": _sha256(data),
        })
    _audit("list", _actor(claims), subdir or "/", True, detail=f"{len(files)} archivos")
    return {"vault_subdir": subdir, "count": len(files), "files": files}


@mcp.tool()
def import_config(token: str, path: str) -> dict:
    """Devuelve el contenido de un archivo del vault para bootstrapear un proyecto
    local. Texto plano se devuelve como utf-8 (encoding='text'); binarios (certs,
    llaves .pem/.pfx) como base64 (encoding='base64'). Requiere token Superadmin."""
    claims = _verify(token)
    p = _safe_path(path)
    if not p.exists() or not p.is_file():
        _audit("import", _actor(claims), path, False, detail="no existe")
        raise FileNotFoundError(f"No existe en el vault: {path}")

    data = p.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        _audit("import", _actor(claims), path, False, detail="excede tamano")
        raise ValueError(f"Archivo demasiado grande ({len(data)} B > {MAX_FILE_BYTES} B).")

    try:
        content, encoding = data.decode("utf-8"), "text"
    except UnicodeDecodeError:
        content, encoding = base64.b64encode(data).decode("ascii"), "base64"

    sha = _sha256(data)
    _audit("import", _actor(claims), path, True, sha=sha)
    return {
        "path": str(p.relative_to(VAULT_DIR)).replace("\\", "/"),
        "encoding": encoding,
        "content": content,
        "size": len(data),
        "sha256": sha,
    }


@mcp.tool()
def export_config(token: str, path: str, content: str, encoding: str = "text") -> dict:
    """Escribe/actualiza un archivo en el vault central. `encoding` = 'text'
    (content es utf-8) o 'base64' (content es base64 de un binario). Si el archivo
    ya existe, respalda la version previa como <archivo>.bak antes de sobrescribir.
    Requiere token Superadmin. Queda auditado."""
    claims = _verify(token)
    if encoding not in ("text", "base64"):
        raise ValueError("encoding debe ser 'text' o 'base64'.")
    p = _safe_path(path)

    if encoding == "base64":
        try:
            data = base64.b64decode(content, validate=True)
        except Exception as e:
            raise ValueError(f"content no es base64 valido: {e}")
    else:
        data = content.encode("utf-8")

    if len(data) > MAX_FILE_BYTES:
        _audit("export", _actor(claims), path, False, detail="excede tamano")
        raise ValueError(f"Contenido demasiado grande ({len(data)} B > {MAX_FILE_BYTES} B).")

    p.parent.mkdir(parents=True, exist_ok=True)
    backed_up = False
    if p.exists():
        p.with_suffix(p.suffix + ".bak").write_bytes(p.read_bytes())
        backed_up = True
    p.write_bytes(data)

    sha = _sha256(data)
    _audit("export", _actor(claims), path, True, sha=sha,
           detail=f"{len(data)}B backup={backed_up}")
    return {
        "path": str(p.relative_to(VAULT_DIR)).replace("\\", "/"),
        "bytes_written": len(data),
        "sha256": sha,
        "previous_backed_up": backed_up,
    }


if __name__ == "__main__":
    logger.info("ie-config-vault starting — vault=%s iam=%s role=%s",
                VAULT_DIR, IAM_BASE_URL, REQUIRED_ROLE)
    mcp.run(transport="streamable-http")
