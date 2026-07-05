# ie-config-vault

MCP server para **importar/exportar archivos de configuración sensibles**
(`.env`, `public.pem`, certificados, llaves, `*.conf`) desde un almacén central
en el servidor, autenticado contra el **IAM de IE**.

## Por qué

Tras un `git clone` limpio, el código **no** trae los secretos (viven solo en
`deploy/.env` y en las carpetas de llaves, todo fuera de git). Este server deja
que un agente autenticado:

- **`import_config`** → bajar un `.env`/cert al proyecto local para bootstrapear.
- **`export_config`** → publicar una versión nueva al almacén central.

Sin copiar archivos a mano ni exponerlos en el repo público.

> **`import_config` es de un solo tiro, no un enlace vivo.** Lee el archivo del
> vault **una vez**, el agente lo escribe en una ruta **local gitignoreada** del
> proyecto (nunca al repo — es público), y desde ese momento la app usa su copia
> local. **En runtime la app nunca vuelve a llamar al vault.** El único momento que
> depende del servidor es el bootstrap tras un clone limpio; los checkouts ya
> configurados siguen funcionando aunque `linux.ie` esté caído. La resiliencia del
> secreto viene del **backup mensual del vault**, no de un acoplamiento permanente.

## Seguridad

Esto **sirve secretos**, así que el gating es lo más importante. `mcp.ie` no
tiene auth de transporte → el token Superadmin es la **única** barrera.

- Todas las tools excepto `login` exigen un **access token JWT del IAM** con rol
  **`Superadmin`**. El token se valida **localmente** con la llave pública RSA
  del IAM (RS256): firma, `iss`, `aud`, `exp`. No se consulta al IAM por request.
- **Path traversal guard**: toda ruta se resuelve bajo `VAULT_DIR` y se rechaza
  si escapa (`..`, rutas absolutas, symlinks fuera del vault).
- **Cap de tamaño** (5 MB por defecto) en import y export.
- **Backup `.bak`** de la versión previa antes de sobrescribir en `export`.
- **Auditoría JSONL** (`logs/config-vault.jsonl`): quién, qué, sha256, cuándo,
  resultado. Nunca se loguea el contenido, solo su hash.

## Tools

| Tool | Auth | Descripción |
|------|------|-------------|
| `login(username_or_email, password)` | — | Autentica contra el IAM, devuelve access token (15 min) + roles. |
| `list_configs(token, subdir="")` | Superadmin | Lista archivos del vault (ruta, tamaño, mtime, sha256). No devuelve contenido. |
| `import_config(token, path)` | Superadmin | Devuelve el contenido (utf-8 o base64 si es binario). |
| `export_config(token, path, content, encoding="text")` | Superadmin | Escribe/actualiza un archivo (respalda `.bak`). |

## Config por entorno

| Var | Default | Descripción |
|-----|---------|-------------|
| `VAULT_DIR` | `/vault` | Raíz del almacén (montado desde `VAULT_HOST_DIR`). |
| `IAM_PUBLIC_KEY_PATH` | `/keys/public.pem` | Llave pública del IAM para validar el JWT. |
| `IAM_BASE_URL` | `https://iam.ie` | Base del IAM para `login()`. |
| `IAM_ISSUER` | `autenticacion.intempaques.com` | Claim `iss` esperado. |
| `IAM_AUDIENCE` | `apps.intempaques.com` | Claim `aud` esperado. |
| `IAM_CA_BUNDLE` | (CAs del sistema) | Ruta a `root-ca.pem` si `login()` valida TLS contra la CA interna. |
| `REQUIRED_ROLE` | `Superadmin` | Rol exigido para operar el vault. |
| `AUDIT_LOG` | `/logs/config-vault.jsonl` | Ruta del log de auditoría. |
| `MAX_FILE_BYTES` | `5242880` | Tamaño máximo por archivo. |

## Deploy (servidor linux.ie)

Requiere admin — el agente **no** lo ejecuta sin que se le pida.

1. **Crear el almacén** (fuera de git):
   ```bash
   mkdir -p /proyectos/_vault
   ```
2. **Verificar `deploy/.env`** tiene (o dejar los defaults):
   ```
   VAULT_HOST_DIR=/proyectos/_vault
   IAM_KEYS_DIR=/proyectos/ie-IAM/backend/keys   # debe contener public.pem
   IAM_BASE_URL=https://iam.ie
   ```
3. **Levantar el contenedor**:
   ```bash
   cd deploy && docker compose up -d --build mcp-config-vault
   ```
4. **Proxy `ie-proxy`** — agregar el location block en
   `/proyectos/ie-proxy/config/conf.d/mcp.ie.conf` (patrón igual a los otros MCP):
   ```nginx
   location /vault/ {
       proxy_pass http://mcp-config-vault:8000/;
       proxy_http_version 1.1;
       proxy_set_header Host $host;
       proxy_set_header Connection "";
       proxy_buffering off;
   }
   ```
   Recargar: `docker exec ie-proxy nginx -t && docker exec ie-proxy nginx -s reload`
5. **Backup mensual** — registrar `/proyectos/_vault` en el backup (skill
   `ie-add-to-linux-backup`). El vault es la fuente de verdad de los secretos.

Queda accesible en `http://mcp.ie/vault/mcp` (ya declarado en `.mcp.json`).

## Uso

```
login("sergio", "****")            → { access_token, puede_operar_vault: true, ... }
list_configs(token)                → { files: [{ path, size, sha256 }, ...] }
import_config(token, "ie-IAM/.env")→ { encoding: "text", content: "..." }
export_config(token, "ie-IAM/backend/keys/public.pem", "<b64>", "base64")
```
