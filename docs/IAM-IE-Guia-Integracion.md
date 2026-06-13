# IAM IE — Guía de integración para aplicaciones cliente

**Última actualización:** 2026-06-11
**Audiencia:** desarrolladores (o agentes de IA) que construyen una nueva app interna y quieren
usar el IAM de Integral de Empaques como proveedor de autenticación.

> ⚠️ **Contrato verificado contra el código** (`AuthController`, `JwtService`, `AuthDtos`). Si algo
> en otra fuente (skills, notas) contradice este documento, **manda el código**, no la nota. Las
> versiones viejas de esta guía tenían errores (claim `nombre`/`username`/`sesionId`, `iss=iam.ie`)
> que ya están corregidos aquí.

> ¿Buscas cómo administrar el sistema (usuarios, roles, infraestructura)?
> Lee en cambio: **[Sistema-IAM-IE.md](Sistema-IAM-IE.md)**

---

## ¿Qué ofrece el IAM a una app cliente?

- **Autenticación centralizada** — login único para todos los sistemas IE.
- **JWT RS256** — el IAM firma con su llave privada RSA; la app cliente verifica con la pública
  (sin consultar al IAM en cada request).
- **RBAC** — el token trae roles y permisos. La app hace enforcement local.
- **Refresh con rotación** — el access token dura 15 min; el refresh token (7 días, cookie httpOnly)
  lo renueva. Cada refresh emite un refresh token nuevo y revoca el anterior.

---

## URLs base

| Entorno | URL |
|---|---|
| Producción (red interna IE) | `https://iam.ie` |
| Producción (alias) | `https://identidad.ie` |
| Desarrollo local | `http://localhost:5055` |

La API vive bajo `/api/`. Swagger en `/swagger`.

---

## ⭐ Contrato real (LO MÁS IMPORTANTE — léelo antes de codear)

Todas las respuestas van envueltas en el **sobre uniforme `ApiResponse`**:

```json
{ "exitoso": true, "mensaje": "...", "data": { ... }, "errores": [] }
```

Los datos útiles están SIEMPRE dentro de `data`. Nunca asumas campos en la raíz.

### `POST /api/auth/login`

**Body** (ojo: el campo es `usernameOrEmail`, NO `username`):
```json
{ "usernameOrEmail": "jgarcia", "password": "..." }
```

**Respuesta** — `data` trae el access token **y** el objeto `usuario` completo:
```json
{
  "exitoso": true,
  "mensaje": "Sesión iniciada correctamente.",
  "data": {
    "accessToken": "eyJ...",
    "expiracion": "2026-06-11T18:15:00Z",
    "usuario": {
      "id": 42,
      "nombre": "Juan García",
      "email": "jgarcia@intempaques.com",
      "username": "jgarcia",
      "roles": ["Operador"],
      "permisos": ["despachos:leer", "despachos:crear"],
      "debeResetearPassword": false
    }
  },
  "errores": []
}
```
Además, `Set-Cookie: refresh_token=...` (httpOnly, Secure, SameSite=Strict). El refresh token
**nunca** viaja en el body.

### `POST /api/auth/refresh`

Se llama sin body (usa la cookie). **Respuesta — solo el token, SIN el objeto `usuario`:**
```json
{
  "exitoso": true,
  "mensaje": null,
  "data": { "accessToken": "eyJ...", "expiracion": "2026-06-11T18:30:00Z" },
  "errores": []
}
```

> 🔑 **Esta es la causa #1 de bugs al integrar.** El `refresh` **no** devuelve `usuario`. Si tu app
> necesita el nombre/roles/permisos tras un refresh (p. ej. al recargar la página con
> APP_INITIALIZER), **debes reconstruirlos decodificando el JWT** — ver la sección siguiente. No
> esperes `data.usuario` en el refresh; no existe.

---

## Estructura del JWT (access token) — claims REALES

Decodificando el payload del `accessToken` (p. ej. en jwt.io) se obtiene **exactamente** esto:

```json
{
  "sub": "42",
  "unique_name": "jgarcia",
  "email": "jgarcia@intempaques.com",
  "role": ["Operador"],
  "permiso": ["despachos:leer", "despachos:crear"],
  "jti": "a1b2c3...",
  "iat": 1717350000,
  "nbf": 1717350000,
  "exp": 1717350900,
  "iss": "autenticacion.intempaques.com",
  "aud": "apps.intempaques.com"
}
```

| Claim | Tipo | Descripción |
|---|---|---|
| `sub` | string | ID del usuario en `AutenticacionDB` |
| `unique_name` | string | **El username.** No existe un claim `nombre` ni `username` |
| `email` | string | Correo del usuario |
| `role` | string **o** string[] | Roles. **Con un solo rol es un string**, con varios un array |
| `permiso` | string **o** string[] | Permisos `recurso:accion` (mismo: string si es uno) |
| `iat` / `nbf` / `exp` | Unix timestamp | Emisión / no-antes-de / expiración (15 min) |
| `iss` | string | `"autenticacion.intempaques.com"` |
| `aud` | string | `"apps.intempaques.com"` |

**Lo que NO está en el JWT** (errores comunes heredados de docs viejas):
- ❌ **No hay claim `nombre`** — el nombre completo solo viene en `data.usuario.nombre` del *login*,
  no en el token. Tras un refresh no lo tienes desde el JWT; si lo necesitas, cachéalo del login.
- ❌ **No hay claim `username`** — usa `unique_name`.
- ❌ **No hay claim `sesionId`**.

### Reconstruir la identidad desde el JWT (para el refresh)

```typescript
// Decodifica el payload del JWT (sin verificar firma — eso lo hace el backend)
function identidadDesdeJwt(accessToken: string) {
  const payload = JSON.parse(atob(accessToken.split('.')[1]));
  const aArreglo = (v: string | string[] | undefined): string[] =>
    v == null ? [] : Array.isArray(v) ? v : [v];   // ← clave: role/permiso puede ser string
  return {
    id: Number(payload.sub ?? 0),
    username: payload.unique_name ?? '',
    nombre: payload.unique_name ?? '',   // el token no trae nombre completo; cae al username
    email: payload.email ?? '',
    roles: aArreglo(payload.role),
    permisos: aArreglo(payload.permiso),
  };
}
```

> El detalle `role`/`permiso` puede ser **string o array** rompe a quien asume siempre array.
> Normaliza con un helper como `aArreglo`.

---

## Otros endpoints

| Método | Ruta | Body / Notas |
|---|---|---|
| `POST` | `/api/auth/logout` | Revoca el refresh token (requiere estar autenticado) |
| `POST` | `/api/auth/recuperar-password` | `{ email }` — envía enlace de reset |
| `POST` | `/api/auth/resetear-password` | `{ token, nuevaPassword }` |
| `POST` | `/api/auth/activar-cuenta` | `{ token, nuevaPassword }` — alta de usuario nuevo |
| `GET`  | `/api/auth/activacion-info?token=...` | Datos del usuario a activar |
| `GET`  | `/api/perfil` | Datos del usuario actual |
| `PUT`  | `/api/perfil` | Editar nombre/email propio |
| `POST` | `/api/perfil/cambiar-password` | Cambiar contraseña propia |
| `GET`/`DELETE` | `/api/perfil/sesiones[/{id}]` | Sesiones propias |

Administración bajo `/api/admin/` (requiere rol `Superadmin`). Ver Swagger.

---

## Cómo verificar el token en una app backend (.NET)

```csharp
using System.Security.Cryptography;
using Microsoft.IdentityModel.Tokens;

string pem = File.ReadAllText("/ruta/a/public.pem");   // llave pública del IAM
using RSA rsa = RSA.Create();
rsa.ImportFromPem(pem);
RsaSecurityKey llavePublica = new(rsa);

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.MapInboundClaims = false;  // mantiene "sub"/"role"/"unique_name" sin remapear
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = llavePublica,
            ValidateIssuer = true,
            ValidIssuer = "autenticacion.intempaques.com",
            ValidateAudience = true,
            ValidAudience = "apps.intempaques.com",
            ValidateLifetime = true,
            ClockSkew = TimeSpan.FromSeconds(30),
            RoleClaimType = "role",          // [Authorize(Roles=...)] lee el claim "role"
            NameClaimType = "unique_name"
        };
    });
```

Leer claims en un controller:
```csharp
bool esSuperadmin = User.IsInRole("Superadmin");
int usuarioId = int.Parse(User.FindFirstValue("sub")!);   // con MapInboundClaims=false
IEnumerable<string> permisos = User.Claims.Where(c => c.Type == "permiso").Select(c => c.Value);
```

Proteger endpoints: `[Authorize]`, `[Authorize(Roles = "Superadmin")]`.

---

## Cómo consumir el IAM desde un frontend Angular

1. **Token en memoria** — nunca en `localStorage`/`sessionStorage`. Un signal privado.
2. **`withCredentials: true`** en TODAS las llamadas al IAM (para que viaje la cookie de refresh).
3. **APP_INITIALIZER** — al arrancar, llamar `POST /api/auth/refresh`. Como el refresh **no trae
   `usuario`**, reconstruye la identidad decodificando el JWT (ver arriba).
4. **Interceptor HTTP** — agrega `Authorization: Bearer <token>`; en `401` llama refresh y reintenta.
   Serializa el refresh (un solo refresh en vuelo) — con la rotación de tokens, dos refresh
   simultáneos se pisan.

---

## Reglas de implicación de permisos

| Permiso en el token | Implica |
|---|---|
| `recurso:gestionar` | Cualquier acción CRUD de ese recurso |
| `recurso:*` | Cualquier acción de ese recurso |

```typescript
function tienePermiso(permisos: string[], requerido: string): boolean {
  if (permisos.includes(requerido)) return true;
  const [recurso] = requerido.split(':');
  return permisos.includes(`${recurso}:gestionar`) || permisos.includes(`${recurso}:*`);
}
```

---

## CORS

El origen del frontend debe estar en la lista blanca del IAM. En producción, pedir a TI que lo
agregue al `.env` del servidor (formato .NET, doble guion bajo):
```
CORS__ORIGENESPERMITIDOS__0=https://mi-nueva-app.ie
```

---

## Checklist de integración

- [ ] La llave pública RSA del IAM está disponible en la app.
- [ ] El backend valida `iss = "autenticacion.intempaques.com"` y `aud = "apps.intempaques.com"`.
- [ ] El backend usa `MapInboundClaims = false` + `RoleClaimType = "role"`.
- [ ] El origen del frontend está en `Cors:OrigenesPermitidos` del IAM.
- [ ] Todas las llamadas usan `withCredentials: true`.
- [ ] El access token se guarda **en memoria**, nunca en disco.
- [ ] El login lee `data.usuario`; el refresh reconstruye identidad desde el **JWT** (no espera `data.usuario`).
- [ ] El parser trata `role`/`permiso` como **string O array**.
- [ ] La lógica de implicación de permisos (`gestionar`, `*`) está implementada.

---

## 🟢 Fuente de verdad viva (no dependas de esta guía a ciegas)

Esta guía explica el **por qué** y los patrones. Para el **contrato exacto byte a byte**, usa
siempre la fuente que se genera del código y por tanto **no puede contradecirlo**:

| Qué necesitas | Fuente autoritativa |
|---|---|
| Contrato HTTP (campos de request/response, tipos, endpoints) | **`https://iam.ie/swagger/v1/swagger.json`** — OpenAPI autogenerado del código en cada build |
| Claims internos del JWT (`sub`, `unique_name`, `role`, …) | **Decodifica un access token real** (jwt.io). Swagger no ve dentro del token. |

**Contrato verificado contra Swagger de producción (2026-06-11):**
```
LoginRequestDto:    { usernameOrEmail, password }
LoginResponseDto:   { accessToken, expiracion, usuario }            ← login SÍ trae usuario
UsuarioInfoDto:     { id, nombre, email, username, roles, permisos, debeResetearPassword }
RefreshResponseDto: { accessToken, expiracion }                     ← refresh NO trae usuario
```
(Todo dentro del sobre `ApiResponse`: `{ exitoso, mensaje, data: <lo de arriba>, errores }`.)

**Regla para devs y agentes de IA:** si una skill, nota o versión vieja de un .md contradice el
`swagger.json` o un token decodificado, **gana la fuente generada del código**. No parchees a ciegas
contra suposiciones de la documentación.
