# Servicio de Correo IE — Guía de integración

**Última actualización:** 2026-06-04  
**Estado:** ✅ En producción — `http://correo.ie`  
**Audiencia:** desarrolladores que quieran enviar correos desde cualquier aplicación de Integral de Empaques.

> ¿Buscas la documentación del servidor de correo Exchange o la configuración SMTP raw?  
> Lee en cambio el skill `ie-correo-electronico` (configuración del relay, cuenta, puerto).

---

## ¿Qué hace este servicio?

El **ie-email-service** es el único punto centralizado de envío de correo electrónico para todas las aplicaciones de IE. Cualquier app que necesite enviar un correo lo hace llamando a esta API vía HTTP con su contraseña. El servicio:

- Se conecta internamente al relay Exchange (`intempsrv-v01.integraldeempaques.com:2525`).
- Acepta **uno o muchos destinatarios** (Para / Cc / Cco).
- Acepta **cuerpo HTML** con **sustitución opcional de variables** (`{{clave}}`).
- Acepta **adjuntos** en base64 (JSON) o binarios (multipart/form-data).
- **Registra cada envío** (éxito o fallo) en `SERVICIO_CORREOS_BD.AUDITORIA_CORREO` en `192.168.50.86`.
- Si la BD no está disponible, el envío sigue funcionando y la auditoría queda en los logs del proceso.
- Responde **de forma síncrona**: la respuesta HTTP indica si el correo fue entregado o no.

---

## Infraestructura

| Componente | Detalle |
|---|---|
| Host | `linux.ie` (`192.168.51.150`) |
| Contenedor | `ie-correo-service` (Docker) |
| Puerto interno | `5090 → 8080` |
| Nginx | `/etc/nginx/conf.d/correo.ie.conf` |
| Repositorio | `github.com/Integral-de-Empaques-ORG/ie-email-service` |
| BD auditoría | `SERVICIO_CORREOS_BD.AUDITORIA_CORREO` en `192.168.50.86` |

---

## URL base

| Entorno | URL |
|---|---|
| Producción (red interna IE) | `http://correo.ie` |
| Desarrollo local | `http://localhost:5090` |

Swagger disponible en `/swagger` (documentación interactiva de todos los endpoints).

---

## Autenticación — API Key

Toda petición (excepto `/health` y `/swagger`) debe incluir el header:

```
X-Api-Key: <contraseña>
```

**La API Key está guardada en la carpeta compartida de sistemas de TI.**  
Sin este header la respuesta es `401 Unauthorized`.

---

## Endpoints

### `POST /api/correo/enviar` — Envío con JSON (adjuntos en base64)

```json
{
  "para": ["persona@integraldeempaques.com"],
  "cc": ["supervisor@integraldeempaques.com"],
  "cco": [],
  "asunto": "Reporte de alistamiento",
  "cuerpoHtml": "<h1>Hola {{nombre}}</h1><p>Tu reporte adjunto.</p>",
  "variables": { "nombre": "Juan García" },
  "aplicacionOrigen": "Alistamiento",
  "adjuntos": [
    {
      "nombreArchivo": "reporte.xlsx",
      "contenidoBase64": "UEsDBBQA...",
      "tipoMime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
  ]
}
```

**Campos obligatorios:** al menos uno de `para`/`cc`/`cco`, `asunto`, `cuerpoHtml`.  
**Campos opcionales:** `variables`, `aplicacionOrigen` (queda en auditoría), `adjuntos`, `cc`, `cco`.

---

### `POST /api/correo/enviar-multipart` — Envío con adjuntos binarios (multipart/form-data)

Úsalo cuando los adjuntos son grandes y no quieres el overhead del base64 (+33%). Los mismos campos van como form fields; los archivos van en el campo `files`.

```
POST /api/correo/enviar-multipart
Content-Type: multipart/form-data

para=persona@integraldeempaques.com
asunto=Reporte
cuerpoHtml=<p>Adjunto</p>
aplicacionOrigen=Alistamiento
files=@reporte.xlsx
```

---

### `GET /api/correo/logs` — Consulta del historial de envíos

Devuelve el historial de `AUDITORIA_CORREO` con filtros y paginado.

**Query params:** `aplicacionOrigen`, `fechaDesde` (ISO 8601), `fechaHasta`, `exitoso` (true/false), `pagina` (default 1), `tamanoPagina` (default 50).

```
GET /api/correo/logs?aplicacionOrigen=Alistamiento&exitoso=false&pagina=1&tamanoPagina=20
```

---

### `GET /health` — Liveness

Devuelve `200 Healthy` si el proceso está corriendo. No verifica dependencias externas.

### `GET /health/ready` — Readiness

Verifica conectividad con BD (`SERVICIO_CORREOS_BD`) y relay SMTP. Devuelve `200` si ambos están disponibles, `503` si alguno falla.

---

## Contrato de respuesta

Todas las respuestas siguen el mismo envelope:

```json
{
  "exitoso": true,
  "mensaje": "Correo enviado exitosamente.",
  "data": {
    "idLog": 42,
    "enviado": true,
    "fecha": "2026-06-04T14:30:00Z"
  },
  "errores": []
}
```

| HTTP | `exitoso` | Significado |
|---|---|---|
| `200` | `true` | Correo entregado al relay Exchange. |
| `400` | `false` | Request inválido (email mal formado, sin destinatarios, adjunto excede límite). |
| `401` | `false` | API key ausente o inválida. |
| `502` | `false` | El relay Exchange rechazó o no respondió. |
| `500` | `false` | Error interno inesperado. |

> **Importante:** ante cualquier respuesta con `exitoso: false`, el correo **no fue enviado**. La app debe capturar el error y reaccionar (mostrar mensaje, reintentar, registrar, etc.).

---

## Sustitución de variables

El campo `cuerpoHtml` puede contener placeholders con la sintaxis `{{clave}}`. Si se envía el campo `variables` con un diccionario de clave-valor, el servicio los sustituye antes de enviar:

```json
"cuerpoHtml": "<p>Hola {{nombre}}, tu pedido {{numeroPedido}} está listo.</p>",
"variables": { "nombre": "Ana", "numeroPedido": "PE-2026-001" }
```

---

## Principio de integración para las apps

**El servicio es una API HTTP. Ninguna app debe tener lógica SMTP directa.**

Cada aplicación debe:
1. Definir su propio contrato de correo (una interfaz tipo `IEmailService` en su lenguaje/framework).
2. Implementar esa interfaz como un cliente HTTP que llame a este servicio con el header `X-Api-Key`.
3. Manejar los errores de la respuesta (capturar `exitoso: false` o excepciones HTTP) según la lógica propia de la app.

El **qué** enviar (HTML, destinatarios, asunto) lo construye cada app. El **cómo** entregarlo al Exchange es responsabilidad exclusiva de este servicio.

---

## Ejemplos de consumo

### .NET (HttpClient)

```csharp
var request = new
{
    para = new[] { "persona@integraldeempaques.com" },
    asunto = "Notificación",
    cuerpoHtml = "<p>Hola {{nombre}}</p>",
    variables = new { nombre = "Juan" },
    aplicacionOrigen = "MiApp"
};

var response = await _httpClient.PostAsJsonAsync("/api/correo/enviar", request);

if (!response.IsSuccessStatusCode)
{
    var error = await response.Content.ReadFromJsonAsync<ApiResponse>();
    throw new Exception($"Correo no enviado: {error?.Mensaje}");
}
```

Configurar en `Program.cs` / DI:
```csharp
builder.Services.AddHttpClient("correo", c =>
{
    c.BaseAddress = new Uri("http://correo.ie");
    c.DefaultRequestHeaders.Add("X-Api-Key", configuration["Correo:ApiKey"]);
});
```

### Python (httpx / requests)

```python
import httpx

response = httpx.post(
    "http://correo.ie/api/correo/enviar",
    headers={"X-Api-Key": API_KEY},
    json={
        "para": ["persona@integraldeempaques.com"],
        "asunto": "Reporte",
        "cuerpoHtml": "<p>Hola {{nombre}}</p>",
        "variables": {"nombre": "Ana"},
        "aplicacionOrigen": "PipelineBI"
    }
)

data = response.json()
if not data["exitoso"]:
    raise Exception(f"Correo no enviado: {data['mensaje']}")
```

### Python con adjunto CSV (base64)

```python
import base64

with open("reporte.csv", "rb") as f:
    contenido_b64 = base64.b64encode(f.read()).decode()

httpx.post(
    "http://correo.ie/api/correo/enviar",
    headers={"X-Api-Key": API_KEY},
    json={
        "para": ["gerencia@integraldeempaques.com"],
        "asunto": "Reporte BI diario",
        "cuerpoHtml": "<p>Reporte adjunto.</p>",
        "adjuntos": [{
            "nombreArchivo": "reporte.csv",
            "contenidoBase64": contenido_b64,
            "tipoMime": "text/csv"
        }]
    }
)
```

### WinForms (.NET — HttpClient asíncrono)

```csharp
var payload = new
{
    para = destinatarios,
    asunto = asunto,
    cuerpoHtml = cuerpoHtml,
    aplicacionOrigen = "AlistamientoIE"
};

try
{
    var response = await _httpClient.PostAsJsonAsync("/api/correo/enviar", payload);
    if (!response.IsSuccessStatusCode)
        MessageBox.Show("No se pudo enviar el correo.", "Advertencia",
            MessageBoxButtons.OK, MessageBoxIcon.Warning);
}
catch (Exception ex)
{
    MessageBox.Show($"Error al enviar correo: {ex.Message}", "Error",
        MessageBoxButtons.OK, MessageBoxIcon.Error);
}
```

### Adjunto binario grande — multipart (.NET)

```csharp
using var form = new MultipartFormDataContent();
form.Add(new StringContent("persona@integraldeempaques.com"), "para");
form.Add(new StringContent("Reporte grande"), "asunto");
form.Add(new StringContent("<p>Adjunto.</p>"), "cuerpoHtml");

byte[] archivo = File.ReadAllBytes("reporte.xlsx");
form.Add(new ByteArrayContent(archivo), "files", "reporte.xlsx");

await _httpClient.PostAsync("/api/correo/enviar-multipart", form);
```

---

## Consulta de logs

Para auditar envíos o diagnosticar problemas:

```
GET /api/correo/logs?aplicacionOrigen=Alistamiento&fechaDesde=2026-06-01&exitoso=false
```

También disponible en Swagger (`http://correo.ie/swagger`) para consulta manual.

---

## Operación y mantenimiento

### Despliegue de nuevas versiones
```bash
# En el servidor linux.ie
cd /proyectos/ie-email-service && git pull && docker compose up -d --build
```

### Ver logs en tiempo real
```bash
ssh ie-linux "docker logs -f ie-correo-service"
```

### Reiniciar el servicio
```bash
ssh ie-linux "cd /proyectos/ie-email-service && docker compose restart"
```

---

## Checklist de integración

- [ ] Obtener la `ApiKey` de la carpeta compartida de sistemas de TI.
- [ ] Definir en la app el contrato de correo (interfaz) separado de la lógica de negocio.
- [ ] Implementar la interfaz como cliente HTTP con el header `X-Api-Key`.
- [ ] Manejar respuestas con `exitoso: false` — el correo NO fue entregado.
- [ ] Incluir `aplicacionOrigen` en las peticiones para facilitar la auditoría.
- [ ] Verificar la conectividad al servicio con `GET /health` antes de reportar un problema.
