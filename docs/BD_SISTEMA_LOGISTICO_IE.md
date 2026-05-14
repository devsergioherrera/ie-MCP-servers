# 📦 Base de Datos - Sistema Logístico IE

> Documentación completa de las tablas utilizadas en el sistema de alistamiento y despacho de camiones.

---

## 🗂️ Schema: `[SIE]` - Sistema de Logística

### 1. `CAMION`

**Descripción**: Almacena la información de los camiones de transporte disponibles para despachos.

**Propósito**: Catálogo maestro de vehículos con sus placas y tipología.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_CAMION` | BIGINT (PK) | Código único del camión |
| `PLACAS` | VARCHAR | Placas del vehículo (ej: ABC123) |
| `TIPOLOGIA` | TINYINT | Tipo de camión (capacidad/tamaño) |

**Ejemplos**:
```sql
-- Camión sencillo
COD_CAMION: 1, PLACAS: 'ABC123', TIPOLOGIA: 1

-- Camión doble troque
COD_CAMION: 2, PLACAS: 'XYZ789', TIPOLOGIA: 2
```

---

### 2. `CONDUCTOR`

**Descripción**: Almacena la información de los conductores autorizados para realizar despachos.

**Propósito**: Catálogo maestro de conductores con sus datos de contacto e identificación.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_CONDUCTOR` | BIGINT (PK) | Código único del conductor |
| `NOMBRES` | VARCHAR | Nombre completo del conductor |
| `TELEFONO` | VARCHAR | Número de contacto |
| `CI` | VARCHAR | Cédula de identidad |

**Ejemplos**:
```sql
-- Conductor activo
COD_CONDUCTOR: 101, NOMBRES: 'Juan Pérez', TELEFONO: '3001234567', CI: '12345678'

-- Conductor de planta
COD_CONDUCTOR: 102, NOMBRES: 'María González', TELEFONO: '3009876543', CI: '87654321'
```

---

### 3. `CAMION_X_DIA` ⭐

**Descripción**: Relaciona un camión con un conductor en una fecha específica. **Es el núcleo del sistema**, representa un "despacho programado".

**Propósito**: Programar qué camión, con qué conductor, saldrá en qué fecha. Es la tabla principal que conecta todo el flujo.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_CAMION` | BIGINT (PK) | ID único del despacho programado |
| `FECHA` | DATE | Fecha del despacho |
| `COD_EMPRESA_TRANSPORTE` | VARCHAR | NIT de la empresa transportadora |
| `ESTADO` | CHAR(1) | **C**=Por Cargar, **E**=En proceso, **D**=Despachado, **X**=Anulado |
| `COD_REGISTRO_CAMION` | BIGINT (FK) | Referencia a `CAMION.COD_CAMION` |
| `COD_CONDUCTOR` | BIGINT (FK) | Referencia a `CONDUCTOR.COD_CONDUCTOR` |

**Estados del Camión**:
- `C` = **Por Cargar**: Camión programado, esperando alistamiento
- `E` = **En proceso**: Camión siendo cargado en el software de Despachos
- `D` = **Despachado**: Camión ya salió de planta
- `X` = **Anulado**: Despacho cancelado

**Ejemplos**:
```sql
-- Camión programado para mañana (esperando alistamiento)
COD_CAMION: 1001, FECHA: '2024-12-26', ESTADO: 'C', 
COD_REGISTRO_CAMION: 1, COD_CONDUCTOR: 101

-- Camión siendo cargado ahora (no se puede alistar)
COD_CAMION: 1002, FECHA: '2024-12-25', ESTADO: 'E', 
COD_REGISTRO_CAMION: 2, COD_CONDUCTOR: 102
```

**Nota importante**: `COD_CAMION` aquí NO es el código del vehículo, es el **ID del despacho programado**. El código real del vehículo está en `COD_REGISTRO_CAMION`.

---

### 4. `DOCUMENTOS_DESPACHADOS`

**Descripción**: Almacena las remisiones/órdenes de venta asociadas a un camión específico.

**Propósito**: Vincular los documentos del ERP (remisiones, órdenes) con el camión que los transportará.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_DOCUMENTO_DESPACHADO` | BIGINT (PK) | ID único del registro |
| `SECUENCIAL` | VARCHAR | Número de remisión (ej: IE/TTS-12345) |
| `COD_CAMION` | BIGINT (FK) | Referencia a `CAMION_X_DIA.COD_CAMION` |

**Ejemplos**:
```sql
-- Remisión de transferencia entre bodegas
SECUENCIAL: 'IE/TTS-12345', COD_CAMION: 1001

-- Remisión de venta a cliente
SECUENCIAL: 'IE/RMV-67890', COD_CAMION: 1001
```

---

### 5. `DETALLE_CAMION_X_DIA` 📋

**Descripción**: Desglosa los ítems (productos) que se deben despachar en el camión. **Es el "catálogo de pedido"**.

**Propósito**: Listar qué productos, en qué cantidad, y hacia dónde se envían en ese despacho.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_DETALLE_CAMION` | INT (PK) | ID único del detalle |
| `COD_CAMION` | INT (FK) | Referencia a `CAMION_X_DIA.COD_CAMION` |
| `ITEM` | INT | Código del producto del ERP |
| `ITEM_EQUIVALENTE` | INT | Código equivalente en otra compañía |
| `CANTIDAD_PLANIFICADA` | FLOAT | Cantidad pedida (unidades/kilos) |
| `ESTADO` | CHAR(1) | Estado del detalle (C=Creado) |
| `SECUENCIAL` | VARCHAR | Remisión/TTS de origen |
| `PTO_ENVIO` | VARCHAR | Destino/Ciudad del envío |
| `UN_MEDIDA` | VARCHAR | Unidad de medida (UND, KG, MT) |

**Ejemplos**:
```sql
-- Línea de detalle: 100 unidades del ítem 12345
ITEM: '12345', CANTIDAD_PLANIFICADA: 100, UN_MEDIDA: 'UND', 
SECUENCIAL: 'IE/TTS-12345', PTO_ENVIO: 'Bogotá'

-- Línea de detalle: 500 kilos del ítem 67890
ITEM: '67890', CANTIDAD_PLANIFICADA: 500, UN_MEDIDA: 'KG', 
SECUENCIAL: 'IE/RMV-67890', PTO_ENVIO: 'Medellín'
```

**Relación con ERP**: Los datos se obtienen del ERP Siesa (UnoEE) mediante consultas SQL que acceden a las tablas de documentos contables (`t350_co_docto_contable`, `t470_cm_movto_invent`).

---

## 🏭 Schema: `[EMPAQUE(PR)]` - Sistema de Alistamiento

### 6. `ETIQUETA` (Superclase) 🏷️

**Descripción**: Almacena las etiquetas físicas de productos empacados. Tabla madre de `ETIQUETA_LINER` y `ETIQUETA_ROLLO`.

**Propósito**: Registrar cada paca/rollo/pallet que ingresa a bodega con su información de trazabilidad.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idEtiqueta` | VARCHAR (PK) | Código de barras único (ej: PACA-001) |
| `item` | INT | Código del producto |
| `cantidad` | DECIMAL | Cantidad en la etiqueta |
| `pesoNeto` | DECIMAL | Peso neto del producto |
| `pesoBruto` | DECIMAL | Peso bruto con empaque |
| `fecha` | DATE | Fecha de producción |
| `tipoEtiquetado` | VARCHAR | Tipo (PACA, ROLLO, etc) |
| `estado` | VARCHAR | ACTIVA, ELIMINADA, DESPACHADA |

**Ejemplos**:
```sql
-- Paca de producto terminado
idEtiqueta: 'PACA-20241225-001', item: 12345, cantidad: 50, 
pesoNeto: 25.5, estado: 'ACTIVA'

-- Rollo de material
idEtiqueta: 'ROLLO-20241225-100', item: 67890, cantidad: 1000, 
pesoNeto: 500, estado: 'ACTIVA'
```

---

### 7. `ETIQUETA_LINER` (Hereda de ETIQUETA)

**Descripción**: Etiquetas específicas para productos tipo LINER (cartón corrugado).

**Propósito**: Registrar información adicional de trazabilidad para productos LINER.

| Columnas adicionales | Tipo | Descripción |
|---------------------|------|-------------|
| `ancho` | DECIMAL | Ancho del liner (cm) |
| `largo` | DECIMAL | Largo del liner (cm) |
| `gramaje` | INT | Gramaje del papel (g/m²) |
| `idLote` | VARCHAR | Lote de producción |

---

### 8. `ETIQUETA_ROLLO` (Hereda de ETIQUETA)

**Descripción**: Etiquetas específicas para productos tipo ROLLO (papel en bobina).

**Propósito**: Registrar información adicional de trazabilidad para rollos.

| Columnas adicionales | Tipo | Descripción |
|---------------------|------|-------------|
| `diametro` | DECIMAL | Diámetro del rollo (cm) |
| `espesor` | DECIMAL | Espesor del papel (micras) |
| `metrosLineales` | DECIMAL | Metros de papel en el rollo |

---

### 9. `KARDEX_BODEGA` 📊

**Descripción**: Registra TODOS los movimientos de entrada y salida de etiquetas en las bodegas. **Es el inventario del sistema**.

**Propósito**: Controlar el inventario de etiquetas en tiempo real y rastrear su ubicación.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idKardexBodega` | INT (PK) | ID único del movimiento |
| `tipoEntrada` | CHAR(1) | **M**=Manual, **B**=Banda transportadora |
| `tipoSalida` | CHAR(1) | **M**=Manual, **B**=Banda, **D**=Despacho |
| `etiqueta` | VARCHAR (FK) | Código de la etiqueta |
| `idBodega` | INT | Bodega donde está/estuvo |
| `fechaIngreso` | DATETIME | Cuándo ingresó a bodega |
| `fechaSalida` | DATETIME | Cuándo salió de bodega |
| `enBodega` | BIT | **1**=Está en bodega, **0**=Fue despachado |
| `idUsuarioEntrante` | INT | Usuario que registró entrada |
| `idUsuarioSalida` | INT | Usuario que registró salida |
| `idRemision` | VARCHAR | Remisión con la que salió |
| `area` | VARCHAR | Área/Zona de la bodega |

**Ejemplos**:
```sql
-- Etiqueta recién producida, ingresa a bodega
etiqueta: 'PACA-001', fechaIngreso: '2024-12-25 08:00', 
enBodega: 1, tipoEntrada: 'B'

-- Etiqueta despachada en camión
etiqueta: 'PACA-001', fechaSalida: '2024-12-25 14:30', 
enBodega: 0, tipoSalida: 'D', idRemision: 'IE/TTS-12345'
```

**Flujo típico**:
1. Producto termina producción → `INSERT` en KARDEX (enBodega=1)
2. Operador alista producto → Se lee etiqueta en ALISTAMIENTO_ETIQUETA
3. Despachador despacha camión → `UPDATE` en KARDEX (enBodega=0, fechaSalida, idRemision)

---

### 10. `ALISTAMIENTO` 🎯

**Descripción**: Registra el proceso intermedio entre que un producto está en bodega y es despachado. **Es el proceso de "preparación de pedido"**.

**Propósito**: Controlar qué operador, cuándo, y en qué estado está el alistamiento de un camión.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idAlistamiento` | INT (PK) | ID único del alistamiento |
| `idCamionDia` | INT (FK) | Referencia a `CAMION_X_DIA.COD_CAMION` |
| `idUsuario` | INT | Operador que realiza el alistamiento |
| `fechaInicio` | DATETIME | Cuándo empezó el alistamiento |
| `fechaFin` | DATETIME | Cuándo terminó el alistamiento |
| `observaciones` | TEXT | Notas/Comentarios del operador |
| `estado` | VARCHAR | Estado del proceso |

**Estados posibles**:
- `SIN_ALISTAR` *(virtual)*: No existe registro en BD, se muestra por lógica SQL
- `EN_PROCESO`: Operador está alistando activamente
- `ALISTADO`: Se completó todo el pedido
- `ALISTADO_INCOMPLETO`: Se completó pero faltan productos
- `ANULADO`: Se canceló el alistamiento

**Ejemplos**:
```sql
-- Alistamiento en curso
idAlistamiento: 5001, idCamionDia: 1001, idUsuario: 25, 
estado: 'EN_PROCESO', fechaInicio: '2024-12-25 09:00'

-- Alistamiento completo
idAlistamiento: 5002, idCamionDia: 1002, idUsuario: 26, 
estado: 'ALISTADO', fechaInicio: '2024-12-25 08:00', 
fechaFin: '2024-12-25 11:30'
```

**Relación**: `ALISTAMIENTO` ↔ `CAMION_X_DIA` es **1:1** (un camión tiene un solo alistamiento activo a la vez).

---

### 11. `ALISTAMIENTO_ETIQUETA` 📝

**Descripción**: Registra las etiquetas físicas que fueron leídas durante el alistamiento de un camión. Tabla de relación **1:N**.

**Propósito**: Rastrear qué etiquetas específicas se incluyeron en cada alistamiento.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idAlistamiento` | INT (PK, FK) | Referencia a `ALISTAMIENTO.idAlistamiento` |
| `etiqueta` | VARCHAR (PK, FK) | Código de la etiqueta leída |
| `fecha` | DATETIME | Cuándo se leyó la etiqueta |
| `estado` | VARCHAR | ACTIVA, ELIMINADA |
| `areaInicial` | VARCHAR | De dónde se tomó |
| `areaFinal` | VARCHAR | Hacia dónde se movió |
| `idBodegaInicial` | INT | Bodega de origen |
| `idBodegaFinal` | INT | Bodega de destino |
| `idUsuario` | INT | Quién la leyó |

**Ejemplos**:
```sql
-- Etiqueta alistada correctamente
idAlistamiento: 5001, etiqueta: 'PACA-001', 
fecha: '2024-12-25 09:15', estado: 'ACTIVA'

-- Etiqueta eliminada por error
idAlistamiento: 5001, etiqueta: 'PACA-002', 
fecha: '2024-12-25 09:20', estado: 'ELIMINADA'
```

**Relación**: Un `ALISTAMIENTO` puede tener **muchas** `ALISTAMIENTO_ETIQUETA` (1:N).

---

### 12. `FormatoAreaBodega` ⭐

**Descripción**: Tabla maestra de formatos de área. Cada registro define un **patrón de nomenclatura** que describe cómo deben verse las áreas dentro de una bodega del Kardex (ej: `A-01`, `PRIN-B-3`, `REV140`).

**Propósito**: Reemplazar las reglas hardcodeadas de `AreaValidator`. Permite crear, editar y desactivar formatos sin tocar código.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idFormatoAreaBodega` | BIGINT (PK) | ID único del formato |
| `nombreFormato` | VARCHAR(100) | Nombre descriptivo del formato (ej: "Bodega Principal") |
| `descripcionFormato` | VARCHAR(250) | Descripción opcional del patrón |
| `activo` | BIT | 1 = activo, 0 = desactivado |
| `creadoPor` | INT (FK) | Usuario que creó el formato |
| `fechaCreacion` | DATETIME | Fecha de creación (default: GETDATE()) |
| `modificadoPor` | INT (FK, NULL) | Último usuario que lo modificó |
| `fechaModificacion` | DATETIME (NULL) | Fecha de última modificación |

**Ejemplos**:
```sql
-- Formato para bodega principal (ej: patrón A-01 a Z-99)
idFormatoAreaBodega: 1, nombreFormato: 'Bodega Principal', activo: 1,
creadoPor: 1, fechaCreacion: '2025-05-11'

-- Formato desactivado (fue reemplazado)
idFormatoAreaBodega: 2, nombreFormato: 'Formato Antiguo Revisión', activo: 0,
creadoPor: 1, fechaCreacion: '2025-01-01', modificadoPor: 3
```

**Relación**: Un `FormatoAreaBodega` puede estar asignado a **muchas** bodegas vía `BodegaFormato`.

---

### 13. `FormatoAreaBodegaDetalle` 📋

**Descripción**: Desglosa un formato en sus componentes posicionales uno por uno. **Es el "ADN" del patrón de área**: cada fila describe una pieza del código de área en orden.

**Propósito**: Permitir validar y construir áreas posición a posición. El orden de los detalles define la secuencia exacta del código.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idFormatoAreaDetalle` | BIGINT (PK) | ID único del componente |
| `idFormatoAreaBodega` | BIGINT (FK) | Formato al que pertenece |
| `orden` | INT | Posición del componente (1, 2, 3…) |
| `tipoComponente` | TINYINT | Tipo del componente (ver tabla de tipos) |
| `valorLiteral` | VARCHAR(100) | Texto fijo (solo para tipos Literal y Separador) |
| `minimoNumero` | INT (NULL) | Dígito mínimo (0–9) para tipo Dígito |
| `maximoNumero` | INT (NULL) | Dígito máximo (0–9) para tipo Dígito |
| `rangoLetraDesde` | CHAR(1) (NULL) | Letra inicial del rango (ej: 'A') |
| `rangoLetraHasta` | CHAR(1) (NULL) | Letra final del rango (ej: 'Z') |
| `minimoValor` | INT (NULL) | Valor mínimo del rango entero (tipo NumeroLibre) |
| `maximoValor` | INT (NULL) | Valor máximo del rango entero (tipo NumeroLibre) |
| `obligatorio` | BIT | 1 = el componente es obligatorio en el área |

**Tipos de componente** (`tipoComponente`):

| Valor | Nombre | Descripción | Ejemplo en área |
|-------|--------|-------------|-----------------|
| 1 | Literal | Texto fijo exacto | `"PRIN"`, `"REV"` |
| 2 | Letra | Una letra en rango A–Z | `"A"`, `"B"` |
| 3 | Dígito | Un dígito en rango 0–9 | `"0"`, `"9"` |
| 4 | Separador | Guion (`-`) o espacio | `"-"` |
| 5 | NumeroLibre | Número entero en rango libre | `"140"`, `"1"` |

**Ejemplos**:
```sql
-- Formato "A-01": Letra(A-Z) + Separador(-) + Dígito(0-9) + Dígito(0-9)
orden: 1, tipoComponente: 2, rangoLetraDesde: 'A', rangoLetraHasta: 'Z'
orden: 2, tipoComponente: 4, valorLiteral: '-'
orden: 3, tipoComponente: 3, minimoNumero: 0, maximoNumero: 9
orden: 4, tipoComponente: 3, minimoNumero: 0, maximoNumero: 9

-- Formato "INALIP-140": Literal(INALIP) + Separador(-) + NumeroLibre(1-140)
orden: 1, tipoComponente: 1, valorLiteral: 'INALIP'
orden: 2, tipoComponente: 4, valorLiteral: '-'
orden: 3, tipoComponente: 5, minimoValor: 1, maximoValor: 140
```

**Restricción**: El par (`idFormatoAreaBodega`, `orden`) es único — no puede haber dos componentes en la misma posición.

---

### 14. `BodegaFormato` 🔗

**Descripción**: Tabla de relación N:M entre bodegas y formatos. Indica **qué formato(s) usa cada bodega** y cuál es el predeterminado.

**Propósito**: Permitir que una bodega tenga varios formatos (ej: en transición) y que el sistema siempre sepa cuál aplicar por defecto.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idBodegaFormato` | BIGINT (PK) | ID único de la asignación |
| `idBodega` | BIGINT | ID de la bodega (referencia lógica a `UBICACIONES_BODEGA.COD_UBICACION`) |
| `idFormatoAreaBodega` | BIGINT (FK) | Formato asignado a esa bodega |
| `activo` | BIT | 1 = asignación vigente, 0 = desactivada |
| `esPredeterminado` | BIT | 1 = es el formato que aplica por defecto |
| `asignadoPor` | INT (FK) | Usuario que hizo la asignación |
| `fechaAsignacion` | DATETIME | Fecha de la asignación (default: GETDATE()) |
| `modificadoPor` | INT (FK, NULL) | Último usuario que modificó la asignación |
| `fechaModificacion` | DATETIME (NULL) | Fecha de última modificación |

**Ejemplos**:
```sql
-- Bodega 5 usa el formato 1 como predeterminado
idBodega: 5, idFormatoAreaBodega: 1, activo: 1, esPredeterminado: 1,
asignadoPor: 1, fechaAsignacion: '2025-05-11'

-- Bodega 5 también tiene el formato 3 (inactivo, antes era el predeterminado)
idBodega: 5, idFormatoAreaBodega: 3, activo: 0, esPredeterminado: 0
```

**Restricción**: Solo puede haber **un** registro con `esPredeterminado = 1` y `activo = 1` por bodega (índice único filtrado `UX_BodegaFormato_UnicoPredeterminadoActivo`).

**Nota**: La FK hacia `UBICACIONES_BODEGA` fue omitida intencionalmente porque `COD_UBICACION` no es PK de esa tabla. La relación se mantiene por consistencia lógica.

---

### 15. `FormatoAreaBodegaHistorial` 📜

**Descripción**: Registro de auditoría de todos los cambios sobre los formatos. Cada creación, modificación o desactivación queda grabada aquí con el estado anterior y el nuevo.

**Propósito**: Cumplir con trazabilidad de cambios sobre configuraciones críticas que afectan la validación del inventario en Kardex.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idHistorialFormato` | BIGINT (PK) | ID único del registro de auditoría |
| `idFormatoAreaBodega` | BIGINT (FK) | Formato que fue modificado |
| `accion` | VARCHAR(30) | Tipo de cambio: `CREAR`, `ACTUALIZAR`, `ACTIVAR`, `DESACTIVAR` |
| `antesJson` | NVARCHAR(MAX) | Estado del formato **antes** del cambio (JSON) |
| `despuesJson` | NVARCHAR(MAX) | Estado del formato **después** del cambio (JSON) |
| `ejecutadoPor` | INT (FK) | Usuario que realizó la acción |
| `fechaEjecucion` | DATETIME | Fecha y hora del cambio (default: GETDATE()) |

**Ejemplos**:
```sql
-- Creación de un formato nuevo (antes vacío)
idFormatoAreaBodega: 1, accion: 'CREAR',
antesJson: NULL,
despuesJson: '{"nombre":"Bodega Principal","activo":true,"componentes":[...]}',
ejecutadoPor: 3, fechaEjecucion: '2025-05-11 10:22:00'

-- Desactivación de un formato
idFormatoAreaBodega: 2, accion: 'DESACTIVAR',
antesJson: '{"nombre":"Formato Antiguo","activo":true}',
despuesJson: '{"nombre":"Formato Antiguo","activo":false}',
ejecutadoPor: 1, fechaEjecucion: '2025-05-13 14:05:00'
```

---

### 16. `ConfiguracionAreasKardex` ⚙️

**Descripción**: Tabla de control de versión del caché de reglas de validación de áreas. Tiene **un solo registro activo** que se incrementa cada vez que se modifica cualquier formato.

**Propósito**: Permitir que el servicio `AreaBodegaKardexService` sepa cuándo su caché en memoria está desactualizado, sin consultar todas las tablas en cada lectura de etiqueta.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idConfiguracion` | INT (PK) | ID del registro (siempre es 1) |
| `versionReglas` | BIGINT | Contador que aumenta con cada cambio de formato |
| `fechaActualizacion` | DATETIME | Última vez que se actualizó (default: GETDATE()) |
| `actualizadoPor` | INT (FK, NULL) | Usuario que disparó la actualización |

**Ejemplos**:
```sql
-- Estado inicial (ningún cambio aún)
idConfiguracion: 1, versionReglas: 1, fechaActualizacion: '2025-05-11 10:00:00'

-- Después de crear un nuevo formato
idConfiguracion: 1, versionReglas: 4, fechaActualizacion: '2025-05-13 14:05:00'
```

---

## 🔄 Flujo Completo del Sistema

### Fase 1: Programación (Software de Cargue Masivo)

```
1. Usuario carga Excel con remisiones
2. Sistema valida datos del ERP (Siesa)
3. Se crea registro en CAMION_X_DIA (Estado='C')
4. Se insertan remisiones en DOCUMENTOS_DESPACHADOS
5. Se consulta ERP para obtener ítems
6. Se insertan ítems en DETALLE_CAMION_X_DIA
```

### Fase 2: Alistamiento (Software de Alistamiento)

```
7. Operador hace doble click en camión programado
8. Si no existe ALISTAMIENTO → muestra "SIN_ALISTAR"
9. Operador da click en "Alistar"
10. Se crea registro en ALISTAMIENTO (Estado='EN_PROCESO')
11. Operador lee etiquetas con pistola de código de barras
12. Cada etiqueta se registra en ALISTAMIENTO_ETIQUETA
13. Sistema valida contra DETALLE_CAMION_X_DIA
14. Al terminar: ALISTAMIENTO.Estado='ALISTADO'
```

### Fase 3: Despacho (Software de Despachos)

```
15. Despachador da click en "Cargar Camión"
16. CAMION_X_DIA.Estado cambia a 'E' (En proceso)
17. Ya no se puede alistar en el software de Alistamiento
18. Despachador da click en "Despachar"
19. Se actualiza KARDEX_BODEGA:
    - enBodega = 0
    - fechaSalida = NOW()
    - idRemision = número de remisión
20. CAMION_X_DIA.Estado cambia a 'D' (Despachado)
21. Fin del ciclo
```

---

## 🎓 Conceptos Clave

### ¿Qué es un "Despacho"?
Un **despacho** es el proceso completo de preparar y enviar un camión con productos hacia un cliente o bodega externa. Comienza cuando se programa el camión (`CAMION_X_DIA`) y termina cuando sale de planta (`Estado='D'`).

### ¿Qué es el "Alistamiento"?
El **alistamiento** es el proceso de "picking" (recolección de productos) de bodega para cumplir con el pedido del camión. El operador lee físicamente cada etiqueta para confirmar que está incluyendo los productos correctos.

### ¿Qué es una "Etiqueta"?
Una **etiqueta** es un código de barras físico impreso que identifica de manera única una paca, rollo o pallet de producto. Contiene información de trazabilidad (fecha, lote, cantidad, peso).

### ¿Qué es el "Kardex"?
El **kardex** es el registro histórico de todos los movimientos de inventario. Muestra dónde está cada etiqueta en cada momento, y permite hacer auditorías de inventario.

### ¿Qué es un "Formato de Área"?
Un **formato de área** es una plantilla que describe cómo deben ser los códigos de ubicación dentro de una bodega. Se compone de piezas ordenadas: letras, dígitos, textos fijos, separadores y números libres. Por ejemplo, el formato `Letra(A-Z) + "-" + Dígito + Dígito` valida áreas como `A-01`, `B-99`, `Z-10`. Sin formato configurado, ningún área puede ser registrada en esa bodega.

---

## 📌 Notas Importantes

- Todas las tablas de `SIE` usan el prefijo `COD_` para claves primarias
- Todas las tablas de `EMPAQUE(PR)` usan el prefijo `id` para claves primarias (camelCase); las tablas de formatos de área siguen esta misma convención
- El sistema opera en dos bases de datos diferentes (`SIE` y `EMPAQUE(PR)`)
- El ERP externo (Siesa UnoEE) también está involucrado en consultas cross-database
- La tabla `KARDEX_BODEGA` es crítica para auditorías de inventario
- El Kardex de bodegas está en la aplicación **LECTURA DE BANDA** (`Frm_Kardex`)
- La gestión de formatos de área (tablas §12–§16) es administrada desde esa misma aplicación por usuarios con perfil administrador

---

**Autor**: Sistema IE  
**Fecha**: Diciembre 2024 — Actualizado Mayo 2026  
**Versión**: 1.1 (agregadas tablas FormatoAreaBodega, Detalle, BodegaFormato, Historial, ConfiguracionAreasKardex)  
**Propósito**: Documentación para LLMs y desarrolladores
