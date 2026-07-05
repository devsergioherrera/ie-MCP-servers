# Sistema IAM IE — Identidad y Accesos de Integral de Empaques

**Última actualización:** 2026-06-11
**Responsable:** Sergio Andrés Herrera Vallejo — Líder de TI
**URL interna:** https://iam.ie · https://identidad.ie

**Audiencia de este documento:** administradores de TI, líderes de área y personal de soporte.
Explica qué hace el sistema, cómo administrarlo y cómo opera la infraestructura.

> ¿Eres desarrollador integrando una app con el IAM? Lee en cambio:
> **[IAM-IE-Guia-Integracion.md](IAM-IE-Guia-Integracion.md)** — endpoints, JWT, código .NET/Angular y checklist de integración.

---

## ¿Qué es este sistema?

El Sistema IAM (Identity and Access Management) es la puerta de entrada a los sistemas internos de Integral de Empaques. Centraliza quién puede entrar, qué puede hacer y deja registro de todo lo que ocurrió. Antes de este sistema, cada aplicación manejaba sus propios usuarios y contraseñas de forma aislada; ahora existe un único lugar para administrar el acceso.

---

## ¿Qué puede hacer cada persona?

### Usuario regular (cualquier empleado con cuenta)

- Iniciar sesión con su usuario o correo corporativo y contraseña.
- Ver y editar su propio perfil (nombre, correo).
- Cambiar su contraseña (al hacerlo, se cierran automáticamente todas las otras sesiones activas en otros dispositivos).
- Ver qué sesiones tiene abiertas actualmente (con IP, dispositivo y fecha) y cerrarlas de forma remota.
- Solicitar el restablecimiento de su contraseña si la olvidó — recibe un enlace por correo corporativo que expira en 24 horas.

### Administrador (rol Superadmin)

Además de todo lo anterior, puede:

- **Gestionar usuarios:** crear nuevos usuarios, editarlos, activarlos, desactivarlos, bloquearlos o **eliminarlos permanentemente**. Al crear un usuario, el sistema envía un correo de activación para que el empleado cree su propia contraseña.
- **Asignar roles:** vincular o quitar roles a cualquier usuario (excepto quitarle el rol de Superadmin al último administrador activo — el sistema lo impide automáticamente para evitar que la organización quede sin acceso). Soporta asignación masiva de roles a varios usuarios a la vez.
- **Gestionar roles:** crear, editar o eliminar roles. Un rol agrupa un conjunto de permisos.
- **Gestionar permisos:** crear permisos con el formato `recurso:accion` (por ejemplo `usuarios:gestionar`, `reportes:exportar`). Los permisos se asignan a roles, no directamente a personas.
- **Forzar restablecimiento de contraseña** a cualquier usuario (por ejemplo cuando hay sospecha de compromiso de credenciales). El usuario recibe un **enlace seguro por correo** para crear una contraseña nueva; sus sesiones activas se cierran. No viaja ninguna contraseña por correo.
- **Reenviar el correo de activación** si un usuario no recibió o perdió el correo original.
- **Ver la auditoría completa** del sistema: quién hizo qué, cuándo, desde qué IP y dispositivo, y si la acción fue exitosa o fallida.

> **Eliminar usuarios — protecciones:** el sistema impide eliminar la propia cuenta y eliminar al
> último Superadmin activo. La eliminación deja registro en la auditoría (con nombre y correo del
> usuario eliminado) **antes** de borrarlo, de modo que el historial nunca se pierde.

---

## Flujo de vida de un usuario nuevo

1. El administrador crea la cuenta desde el portal (nombre, usuario, correo, rol principal).
2. El sistema envía **un único correo de activación** al empleado. El correo muestra su nombre de usuario y un botón "Activar cuenta y crear contraseña".
3. El empleado hace clic en el enlace (válido por 24 horas), elige su propia contraseña y confirma.
4. En ese mismo paso, su correo queda verificado y su cuenta activada. No necesita hacer nada más.
5. El empleado ingresa al portal con su usuario y la contraseña que acaba de crear.

> El enlace de activación expira en 24 horas. Si el empleado no lo usa a tiempo, el administrador puede reenviar la activación desde la vista de Usuarios.

Si el empleado olvida su contraseña más adelante, usa el flujo "Olvidé mi contraseña" desde la pantalla de ingreso: recibe un enlace seguro por correo que le permite establecer una nueva contraseña sin intervención del administrador.

---

## Política de contraseñas

Toda contraseña en el sistema debe cumplir:
- Mínimo 8 caracteres
- Al menos una letra mayúscula
- Al menos una letra minúscula
- Al menos un número
- Al menos un carácter especial (!, @, #, $, etc.)

El portal muestra los requisitos en tiempo real mientras el usuario escribe, marcando en verde cada condición que se cumple. La misma política se valida en la API, así que no puede ser evadida.

---

## Seguridad — qué hay detrás

### Sesiones y tokens

- Cuando un usuario inicia sesión, el sistema emite un **token de acceso** que dura **15 minutos**. Vencido ese tiempo, el sistema lo renueva automáticamente usando una **cookie de sesión** almacenada en el navegador, sin que el usuario note nada.
- La cookie de sesión dura **7 días** y es `HttpOnly` (el código JavaScript no puede leerla), `Secure` (solo viaja por HTTPS) y `SameSite=Strict` (solo viaja al mismo sitio, no a terceros). El token de acceso se guarda en memoria del navegador, no en disco.
- Si el usuario cierra el navegador completamente y vuelve dentro de los 7 días, su sesión se restablece automáticamente al cargar el portal. Pasados los 7 días, debe volver a ingresar.
- Cada sesión queda registrada en la base de datos. El administrador puede ver todas las sesiones activas de cualquier usuario y cerrarlas remotamente.

### Protección de contraseñas

- Las contraseñas **nunca se guardan en texto plano**. Se almacena únicamente un hash criptográfico (BCrypt); ni el administrador ni el sistema puede ver la contraseña real de un usuario.
- Los intentos fallidos de inicio de sesión se cuentan. Tras **5 intentos fallidos consecutivos**, la cuenta se bloquea automáticamente para protegerla de ataques de fuerza bruta. El administrador debe desbloquearla manualmente.

### Auditoría

Cada acción relevante queda registrada permanentemente:
- Inicios de sesión exitosos y fallidos
- Cambios de contraseña y activaciones de cuenta
- Creación, modificación, desactivación o eliminación de usuarios
- Asignación o revocación de roles y permisos
- Cierres de sesión

El registro incluye quién lo hizo, cuándo, desde qué dirección IP y dispositivo.

---

## Correo electrónico

El sistema envía correos automáticos en estas situaciones:

| Evento | Qué recibe el usuario |
|---|---|
| Cuenta nueva creada por admin | Correo de activación con su usuario y un enlace para crear su contraseña (válido 24 h) |
| Restablecimiento forzado por admin | Enlace seguro para crear una contraseña nueva (válido 24 h) |
| Olvidé mi contraseña | Enlace para establecer nueva contraseña (válido 24 h) |
| Cuenta bloqueada por intentos fallidos | Aviso de bloqueo con instrucciones para contactar al admin |

El IAM **no envía correo directamente**. Delega el envío al **servicio de correo centralizado de IE**
(`ie-email-service`, accesible en `http://correo.ie`), que se encarga del relay con Exchange, la
auditoría de envíos y los reintentos. El IAM solo construye el contenido del correo (HTML con la
imagen institucional) y lo entrega a ese servicio por HTTP con una clave de API.

> El envío es **best-effort** en las acciones de administración: si el servicio de correo está caído,
> la creación o el reset del usuario **no se revierte** — la cuenta queda creada y el administrador
> puede reenviar la activación cuando el correo vuelva. Ver la doc **Servicio-Correo-IE.md**.

---

## Infraestructura y dónde vive el sistema

### Servidor

El sistema corre en el servidor Linux de IE (`linux.ie`, Ubuntu 24.04 LTS), dentro de contenedores Docker.

| Componente | Contenedor | Puerto interno |
|---|---|---|
| API (lógica del negocio) | `iam_ie_api` | 8082 |
| Portal web (interfaz) | `iam_ie_web` | 8083 |
| Proxy externo (nginx del host) | — | 443 (HTTPS, termina TLS) · 80 (redirige a HTTPS) |

El portal se accede en la red interna por `https://iam.ie` o `https://identidad.ie`.

### HTTPS

El portal se sirve por **HTTPS real** con un certificado emitido por la **CA interna de la empresa**
(`INTEMP-ROOT-CA`, en `intempserv2`). El nginx del host termina el TLS en el puerto 443 y redirige
todo el tráfico de HTTP (80) a HTTPS. Como la CA interna ya es de confianza en los equipos del
dominio, los navegadores corporativos no muestran advertencias.

> Si un equipo **fuera del dominio** muestra advertencia de certificado, hay que instalar el
> certificado raíz de la CA interna (`root-ca.pem`) en su almacén de "Entidades de certificación
> raíz de confianza".

### Base de datos

Los datos del IAM (usuarios, roles, permisos, sesiones, auditoría) viven en la base de datos **`AutenticacionDB`** del SQL Server corporativo (`sqlcorp.ie`). Esta base es independiente de las demás bases del ERP.

### Acceso al servidor para administradores de TI

El servidor Linux **no acepta contraseñas** por SSH — solo llaves criptográficas registradas previamente. Para conectarse:

1. Generar una llave SSH en el equipo del administrador (se hace una sola vez).
2. Enviar la llave pública a TI para que la registren en el servidor.
3. Conectarse con `ssh claude-agent@linux.ie` (o con el usuario asignado).

Desde fuera de la red de la empresa se necesita VPN activa para alcanzar `linux.ie` y el SQL Server.

### Puertos relevantes para el firewall / UTM

| Servicio | IP | Puerto | Protocolo |
|---|---|---|---|
| Portal IAM (HTTPS) | linux.ie | 443 | TCP |
| Portal IAM (HTTP → redirige) | linux.ie | 80 | TCP |
| API interna | linux.ie | 8082 | TCP (solo LAN) |
| SQL Server IAM | sqlcorp.ie | 1433 | TCP (solo LAN) |

> El IAM ya no habla SMTP directo: el envío de correo pasa por el servicio centralizado `correo.ie`
> (mismo servidor Linux). La conectividad con Exchange es responsabilidad de ese servicio, no del IAM.

---

## Backup

Los archivos sensibles del IAM que **no están en el repositorio git** están incluidos en el script de backup mensual del servidor Linux (`/opt/scripts/backup-machine.sh`):

| Archivo | Qué contiene |
|---|---|
| `/proyectos/ie-IAM/backend/.env` | Credenciales de BD, clave del servicio de correo, parámetros JWT |
| `/proyectos/ie-IAM/backend/keys/private.pem` | Llave privada RSA (firma los tokens de sesión) |
| `/proyectos/ie-IAM/backend/keys/public.pem` | Llave pública RSA (valida los tokens) |
| `/etc/nginx/` (directorio completo) | Config del proxy inverso **y** el certificado TLS + llave + cadena raíz (`ssl/`) |

El backup respalda `/etc/nginx` entero como un `.tar.gz`, así que la config de nginx **y** el
certificado TLS (`iam.ie.crt.pem`, `iam.ie.key`, `root-ca.pem`) quedan cubiertos automáticamente.

Los backups se guardan mensualmente en un share de backup corporativo (`\\backup-nas\Backups\LinuxVM`).

> **Crítico:** si se pierden las llaves RSA y no hay backup, todas las sesiones activas quedan invalidadas y hay que regenerar las llaves. Los usuarios podrán volver a ingresar, pero sus sesiones actuales se cierran.

---

## Qué pasa si el sistema falla

| Síntoma | Causa probable | Acción |
|---|---|---|
| No se puede entrar al portal | Contenedor caído o nginx down | `ssh linux.ie` → `cd /proyectos/ie-IAM && docker compose up -d` |
| Los correos no llegan | Servicio `correo.ie` caído o sin conectividad a Exchange | Verificar `http://correo.ie/health`; revisar el contenedor `ie-correo-service` (ver Servicio-Correo-IE.md) |
| "Error de base de datos" al ingresar | SQL Server no alcanzable (VPN, red) | Verificar conectividad a `sqlcorp.ie`; verificar VPN si aplica |
| Advertencia de certificado en el navegador | Equipo fuera del dominio sin la CA interna | Instalar `root-ca.pem` en las entidades de certificación raíz de confianza del equipo |
| Un usuario quedó bloqueado | 5 intentos fallidos | El Superadmin lo desbloquea desde Usuarios → Activar |
| El sistema no tiene administrador | Eliminación accidental del último Superadmin | No puede pasar — el sistema lo impide. Si ocurre por corrupción de BD, TI debe insertar el rol directamente en `AutenticacionDB` |

---

## Repositorio y código fuente

El código fuente está en GitHub bajo la organización de IE:
`github.com/Integral-de-Empaques-ORG/ie-IAM`

El repositorio es **privado**. Solo el equipo de TI tiene acceso.

Para actualizar el sistema en producción:
```
1. Hacer los cambios en el PC de desarrollo y subirlos a GitHub (git push)
2. En el servidor: cd /proyectos/ie-IAM && git pull && docker compose up -d --build
```

---

## Migración a otro servidor (otra IP, otro sistema operativo)

El sistema está diseñado para ser **portable**: corre dentro de contenedores Docker, así que el sistema operativo de abajo no importa mientras tenga Docker instalado. La clave es entender **qué está atado a la máquina y qué no**.

### Lo que NO cambia (se copia tal cual al nuevo servidor)

- **El certificado TLS y su llave privada.** Están atados al **nombre de dominio** (`iam.ie`), no a la IP ni al sistema operativo. El mismo certificado sirve en cualquier servidor mientras el sitio se siga llamando `iam.ie`. **No se reemite** al cambiar de máquina.
- **Los contenedores** (API + portal) — se levantan igual con `docker compose`.
- **Las llaves RSA del JWT** (`backend/keys/*.pem`).
- **El `backend/.env`** y la **configuración de nginx**.

### Lo que SÍ hay que actualizar al cambiar de IP

- **DNS interno:** los registros A de `iam.ie` e `identidad.ie` deben apuntar a la **nueva IP** (se cambia en el DNS del controlador de dominio).
- **Correo:** el IAM solo necesita que `http://correo.ie` resuelva y que su clave de API siga siendo válida. La conectividad del servicio de correo con Exchange es responsabilidad de ese servicio, no del IAM.
- **Firewall / UTM:** cualquier regla que referencie la IP vieja.

### Runbook de migración

1. Instalar **Docker** en el nuevo servidor.
2. `git clone` del repo en `/proyectos/ie-IAM`.
3. Restaurar desde el backup los archivos que **no están en git**: `backend/.env`, `backend/keys/`, el **certificado TLS + su llave** (`/etc/nginx/ssl/`) y `/etc/nginx/conf.d/iam.ie.conf`.
4. Actualizar el **DNS** (`iam.ie` / `identidad.ie` → nueva IP).
5. `docker compose up -d --build`.

> Regla de oro: el certificado se reemite **solo si cambias el dominio**, no si cambias de máquina. Cambiar servidor/IP/SO no invalida el certificado.

### Si lo llevas a la nube (a futuro)

Cambia una sola pieza: el **origen del certificado**. En la nube usarías un **dominio público real** (ej. `identidad.tuempresa.com`) y un certificado de **Let's Encrypt** (gratis, se renueva solo con `certbot`), en lugar de la CA interna `INTEMP-ROOT-CA`. El resto del sistema (Docker, contenedores, llaves JWT, base de datos) es idéntico. La CA interna solo aplica mientras el dominio sea interno.
