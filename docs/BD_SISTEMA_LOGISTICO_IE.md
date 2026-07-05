# 📦 Base de Datos - Sistema Logístico IE

> Documentación completa de las tablas utilizadas en el sistema de alistamiento y despacho de camiones.

---

## 🗂️ Schema: `[SIE]` - Sistema de Logística

### 1. `CAMION`

**Descripción**: Almacena la información de los camiones de transporte disponibles para despachos.

**Propósito**: Catálogo maestro de vehículos con sus placas y tipología.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_CAMION` | BIGINT (PK) | Código único del camión (vehículo real) |
| `PLACAS` | VARCHAR | Placas del vehículo (ej: TJW570) |
| `TIPOLOGIA` | TINYINT | Tipo de camión (capacidad/tamaño) |

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

---

### 3. `CAMION_X_DIA` ⭐

**Descripción**: Relaciona un camión con un conductor en una fecha específica. **Es el núcleo del sistema**, representa un "despacho programado".

**Propósito**: Programar qué camión, con qué conductor, saldrá en qué fecha. Es la tabla principal que conecta todo el flujo.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_CAMION` | BIGINT (PK) | ID único del despacho programado |
| `FECHA` | DATETIME | Fecha de referencia de la programación (NO usar para BI) |
| `FECHA_DESPACHO` | DATETIME | Fecha real del despacho — **usar esta para BI y métricas** |
| `COD_EMPRESA_TRANSPORTE` | VARCHAR | NIT de la empresa transportadora |
| `ESTADO` | CHAR(1) | **C**=Por Cargar, **E**=En proceso, **D**=Despachado, **X**=Anulado |
| `COD_REGISTRO_CAMION` | BIGINT (FK) | Referencia a `CAMION.COD_CAMION` (vehículo real) |
| `COD_CONDUCTOR` | BIGINT (FK) | Referencia a `CONDUCTOR.COD_CONDUCTOR` |

**Estados del Camión**:
- `C` = **Por Cargar**: Camión programado, esperando alistamiento
- `E` = **En proceso**: Camión siendo cargado en el software de Despachos
- `D` = **Despachado**: Camión ya salió de planta
- `X` = **Anulado**: Despacho cancelado

**⚠️ Nota importante**: `COD_CAMION` aquí NO es el código del vehículo, es el **ID del despacho programado**. El código real del vehículo está en `COD_REGISTRO_CAMION`. Para BI y métricas siempre usar `FECHA_DESPACHO`, no `FECHA`.

---

### 4. `DOCUMENTOS_DESPACHADOS`

**Descripción**: Almacena las remisiones/órdenes de venta asociadas a un camión específico.

**Propósito**: Vincular los documentos del ERP (remisiones, órdenes) con el camión que los transportará.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_DOCUMENTO_DESPACHADO` | BIGINT (PK) | ID único del registro |
| `SECUENCIAL` | VARCHAR | Número de remisión (ej: IE/TTS-12345, IE/RMV-67890) |
| `COD_CAMION` | BIGINT (FK) | Referencia a `CAMION_X_DIA.COD_CAMION` |
| `FECHA_PROGRAMACION` | DATETIME | Fecha en que se programó el documento |
| `ESTADO` | CHAR(1) | **A**=Activo, **X**=Anulado (soft-delete) |

**Valores de ESTADO**:
- `A` = **Activo**: documento vigente en el despacho
- `X` = **Anulado**: documento removido sin eliminar físicamente (soft-delete)

---

### 5. `DETALLE_CAMION_X_DIA` 📋

**Descripción**: Desglosa los ítems (productos) que se deben despachar en el camión. **Es el "catálogo de pedido"**.

**Propósito**: Listar qué productos, en qué cantidad, y hacia dónde se envían en ese despacho.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_DETALLE_CAMION` | INT (PK) | ID único del detalle |
| `COD_CAMION` | INT (FK) | Referencia a `CAMION_X_DIA.COD_CAMION` |
| `ITEM` | VARCHAR | Código del producto del ERP |
| `ITEM_EQUIVALENTE` | VARCHAR | Código equivalente en otra compañía |
| `CANTIDAD_PLANIFICADA` | FLOAT | Cantidad pedida (unidades/kilos) |
| `CANTIDAD_DESPACHADA` | FLOAT | Cantidad efectivamente despachada |
| `JUSTIFICACION` | VARCHAR | Justificación de diferencias o ajustes |
| `ESTADO` | CHAR(1) | Estado del detalle (A=Activo, C=Creado) |
| `SECUENCIAL` | VARCHAR | Remisión/TTS de origen (ej: IE/TTS-12345) |
| `PTO_ENVIO` | VARCHAR | Destino/Ciudad del envío |
| `UN_MEDIDA` | VARCHAR | Unidad de medida (UND, KG, MT) |

**Relación con ERP**: Los datos se obtienen del ERP Siesa (UnoEE) mediante consultas SQL que acceden a las tablas de documentos contables (`t350_co_docto_contable`, `t470_cm_movto_invent`) vía linked server `[erp.ie].[UnoEE_Doron]`.

---

## 🏭 Schema: `[EMPAQUE(PR)]` - Sistema de Alistamiento

### 6. `ETIQUETA` 🏷️

**Descripción**: Etiquetas físicas de producto terminado tipo paca/saco. Tabla independiente (sin herencia) junto a `ETIQUETA_LINER` y `ETIQUETA_ROLLO`.

**Propósito**: Registrar cada paca que ingresa a bodega con su información de trazabilidad.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_ETIQUETA` | VARCHAR (PK) | Código de barras único (ej: 01020A0001) |
| `COD_ITEM` | INT | Código del producto ERP |
| `CANTIDAD` | DECIMAL | Cantidad en unidades |
| `PESO` | DECIMAL | Peso neto del producto |
| `PESO_TEORICO` | DECIMAL | Peso teórico esperado |
| `COD_CLIENTE` | VARCHAR | Código del cliente |
| `COD_EMPACADOR` | INT | Operador que empacó |
| `COD_CORTADOR` | INT | Operador cortador |
| `COD_TURNO` | VARCHAR | Turno de producción (A/B/C) |
| `ESTADO` | VARCHAR | Estado de la etiqueta (R=Regular/Activa, etc.) |
| `FECHA` | DATETIME | Fecha de producción |
| `LOTE` | VARCHAR | Lote de producción |
| `ORDEN_PRODUCCION` | INT | Orden de producción asociada |
| `COD_TIPO_ETIQUETADO` | VARCHAR | Tipo de etiquetado (puede ser null) |
| `CONSUMIDA_EN` | VARCHAR | Referencia de consumo (null si no consumida) |
| `DESPACHADA_EN` | VARCHAR | Referencia de despacho (null si no despachada) |

**⚠️ Nota**: Las tres tablas de etiquetas (`ETIQUETA`, `ETIQUETA_LINER`, `ETIQUETA_ROLLO`) son independientes — NO tienen herencia entre sí. La vista `vw_EtiquetasBI` las unifica.

---

### 7. `ETIQUETA_LINER`

**Descripción**: Etiquetas específicas para productos tipo LINER (cartón corrugado/laminado). Tabla independiente, sin herencia de `ETIQUETA`.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_ETIQUETA_LINER` | VARCHAR (PK) | Código de barras único del liner |
| `COD_BARRAS` | VARCHAR | Código de barras completo |
| `FECHA` | DATETIME | Fecha de producción |
| `ITEM` | INT | Código del producto ERP |
| `EXTRUSORA` | INT | Número de extrusora que lo produjo |
| `OPERADOR` | INT | Operador que registró |
| `PESO_BRUTO` | DECIMAL | Peso bruto (kg) |
| `PESO_NETO` | DECIMAL | Peso neto (kg) |
| `ESTADO` | INT | Estado numérico interno |
| `ESTADO_PA_IPT` | VARCHAR | Estado proceso (R=Regular) |
| `COD_TIPO_ETIQUETADO` | VARCHAR | Tipo de etiquetado (PR, etc.) |
| `SELLADORA` | INT | Número de selladora |
| `TURNO` | VARCHAR | Turno de producción |
| `COD_AREA_x_TIPO_DS` | INT | Área por tipo de despacho |
| `EXT2` | VARCHAR | Extrusora secundaria (puede ser null) |
| `CANTIDAD` | DECIMAL | Cantidad (puede ser null) |
| `CONSUMIDAEN` | VARCHAR | Referencia de consumo (null si no consumida) |
| `DESPACHADAEN` | VARCHAR | Referencia de despacho (null si no despachada) |

---

### 8. `ETIQUETA_ROLLO`

**Descripción**: Etiquetas específicas para productos tipo ROLLO (tela tejida en bobina). Tabla independiente, sin herencia de `ETIQUETA`.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `COD_ETIQUETA_ROLLO` | VARCHAR (PK) | Código de barras único del rollo |
| `COD_BARRAS` | VARCHAR | Código de barras completo |
| `FECHA` | DATETIME | Fecha de producción |
| `ITEM` | INT | Código del producto ERP |
| `TELAR` | INT | Número de telar que lo produjo |
| `TEJEDOR` | INT | Operador tejedor |
| `PESO_BRUTO` | DECIMAL | Peso bruto (kg) |
| `PESO_NETO` | DECIMAL | Peso neto (kg) |
| `METROS` | DECIMAL | Metros lineales del rollo |
| `ESTADO` | INT | Estado numérico interno |
| `ESTADO_PA_IPT` | VARCHAR | Estado proceso (R=Regular) |
| `COD_TIPO_ETIQUETADO` | VARCHAR | Tipo de etiquetado (PR, etc.) |
| `CI_OPERADOR` | VARCHAR | Cédula del operador |
| `TURNO` | VARCHAR | Turno de producción |
| `CONSUMIDA_EN` | VARCHAR | Referencia de consumo (null si no consumida) |
| `DESPACHADA_EN` | VARCHAR | Referencia de despacho (null si no despachada) |

---

### 9. `KARDEX_BODEGA` 📊

**Descripción**: Registra TODOS los movimientos de entrada y salida de etiquetas en las bodegas. **Es el inventario del sistema**.

**Propósito**: Controlar el inventario de etiquetas en tiempo real y rastrear su ubicación.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idKardexBodega` | INT (PK) | ID único del movimiento |
| `tipoEntrada` | VARCHAR | Tipo de entrada: **B**=Banda transportadora, **M**=Manual |
| `tipoSalida` | VARCHAR | Tipo de salida: **DESPACHO**, **BORRADO**, **M**=Manual, **B**=Banda |
| `etiqueta` | VARCHAR (FK) | Código de la etiqueta |
| `idBodega` | VARCHAR | Bodega donde está/estuvo |
| `fechaIngreso` | DATETIME | Cuándo ingresó a bodega |
| `fechaSalida` | DATETIME | Cuándo salió de bodega |
| `enBodega` | BIT | **1**=Está en bodega, **0**=Fue despachado/removido |
| `idUsuarioEntrante` | INT | Usuario que registró entrada |
| `idUsuarioSalida` | INT | Usuario que registró salida |
| `idRemision` | VARCHAR | Remisión con la que salió |
| `area` | VARCHAR | Área/Zona de la bodega (ej: BANDA, A-01) |

**⚠️ Nota**: Usar `LEFT JOIN` al cruzar con tablas de usuarios — `idUsuarioSalida` puede ser null en registros sin salida aún.

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

**Relación**: `ALISTAMIENTO` ↔ `CAMION_X_DIA` es **1:1** (un camión tiene un solo alistamiento activo a la vez).

---

### 11. `ALISTAMIENTO_ETIQUETA` 📝

**Descripción**: Registra las etiquetas físicas que fueron leídas durante el alistamiento de un camión.

**Propósito**: Rastrear qué etiquetas específicas se incluyeron en cada alistamiento.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idAlistamientoEtiqueta` | INT (PK) | ID surrogate único del registro |
| `idAlistamiento` | INT (FK) | Referencia a `ALISTAMIENTO.idAlistamiento` |
| `etiqueta` | VARCHAR (FK) | Código de la etiqueta leída |
| `fecha` | DATETIME | Cuándo se leyó la etiqueta |
| `estado` | VARCHAR | **ACTIVA** o **ELIMINADA** |
| `areaInicial` | VARCHAR | De dónde se tomó (ej: ALISTAMIENTO) |
| `areaFinal` | VARCHAR | Hacia dónde se movió (ej: ALISTAMIENTO-SPJ707) |
| `idBodegaInicial` | INT | Bodega de origen |
| `idBodegaFinal` | INT | Bodega de destino |
| `idUsuario` | INT | Quién la leyó |

**Relación**: Un `ALISTAMIENTO` puede tener **muchas** `ALISTAMIENTO_ETIQUETA` (1:N). El par (`idAlistamiento`, `etiqueta`) es lógicamente único para etiquetas activas.

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

**Restricción**: El par (`idFormatoAreaBodega`, `orden`) es único — no puede haber dos componentes en la misma posición.

---

### 14. `BodegaFormato` 🔗

**Descripción**: Tabla de relación N:M entre bodegas y formatos. Indica **qué formato(s) usa cada bodega** y cuál es el predeterminado.

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

**Restricción**: Solo puede haber **un** registro con `esPredeterminado = 1` y `activo = 1` por bodega (índice único filtrado `UX_BodegaFormato_UnicoPredeterminadoActivo`).

**Nota**: La FK hacia `UBICACIONES_BODEGA` fue omitida intencionalmente porque `COD_UBICACION` no es PK de esa tabla. La relación se mantiene por consistencia lógica.

---

### 15. `FormatoAreaBodegaHistorial` 📜

**Descripción**: Registro de auditoría de todos los cambios sobre los formatos. Cada creación, modificación o desactivación queda grabada aquí con el estado anterior y el nuevo.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idHistorialFormato` | BIGINT (PK) | ID único del registro de auditoría |
| `idFormatoAreaBodega` | BIGINT (FK) | Formato que fue modificado |
| `accion` | VARCHAR(30) | Tipo de cambio: `CREAR`, `ACTUALIZAR`, `ACTIVAR`, `DESACTIVAR` |
| `antesJson` | NVARCHAR(MAX) | Estado del formato **antes** del cambio (JSON) |
| `despuesJson` | NVARCHAR(MAX) | Estado del formato **después** del cambio (JSON) |
| `ejecutadoPor` | INT (FK) | Usuario que realizó la acción |
| `fechaEjecucion` | DATETIME | Fecha y hora del cambio (default: GETDATE()) |

---

### 16. `ConfiguracionAreasKardex` ⚙️

**Descripción**: Tabla de control de versión del caché de reglas de validación de áreas. Tiene **un solo registro activo** que se incrementa cada vez que se modifica cualquier formato.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `idConfiguracion` | INT (PK) | ID del registro (siempre es 1) |
| `versionReglas` | BIGINT | Contador que aumenta con cada cambio de formato |
| `fechaActualizacion` | DATETIME | Última vez que se actualizó (default: GETDATE()) |
| `actualizadoPor` | INT (FK, NULL) | Usuario que disparó la actualización |

---

## 🗃️ Tablas de Caché Local

### 17. `ITEMS_CACHE` (BD `EMPAQUE(PR)`)

**Descripción**: Tabla local que cachea los datos de ítems del ERP (`t120_mc_items`) para evitar JOINs costosos al linked server en cada consulta operativa.

**Propósito**: Fuente local de datos de ítems para todas las queries del flujo diario (alistamiento, kardex, planificación). Se refresca automáticamente cada 10 minutos con el SP `sp_RefrescarItemsCache` (SQL Server Agent: Job "Refrescar ITEMS_CACHE").

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `Item` | INT (PK) | Código del ítem ERP (`f120_id`) |
| `Descripcion` | NVARCHAR(200) | Nombre completo del ítem (`f120_descripcion`) |
| `DescripcionCorta` | NVARCHAR(100) | Nombre corto (`f120_descripcion_corta`) |
| `UnidadInventario` | VARCHAR(10) | Unidad de inventario ERP: `UND`, `KLS`, `MTS` (`f120_id_unidad_inventario`) |
| `UnidadEmpaque` | VARCHAR(20) | Unidad de empaque: ej. `P012`, `K500` (`f120_id_unidad_empaque`) |
| `Linea` | NVARCHAR(200) | Línea de producto (criterio LINEA del ERP, via t125→t106→t105) |
| `RowId` | INT | `f120_rowid` del ERP |

**Datos**:
- ~30k filas, ~5MB
- Pre-filtrada a `f120_id_cia = 2` — no hay que agregar ese filtro en las queries que la consumen
- Refresco: TRUNCATE + INSERT (~5 segundos de ventana vacía)
- Fuente: `[erp.ie].[UnoEE_Doron].dbo.t120_mc_items` + criterios de línea

---

## 🔄 Flujo Completo del Sistema

### Fase 1: Programación (Software de Cargue Masivo)

```
1. Usuario carga Excel con remisiones
2. Sistema valida datos del ERP (Siesa UnoEE vía linked server [erp.ie].[UnoEE_Doron])
3. Se crea registro en CAMION_X_DIA (Estado='C'), se registra FECHA_DESPACHO
4. Se insertan remisiones en DOCUMENTOS_DESPACHADOS (ESTADO='A')
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
    - tipoSalida = 'DESPACHO'
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
Una **etiqueta** es un código de barras físico impreso que identifica de manera única una paca, rollo o pieza de liner de producto. Contiene información de trazabilidad (fecha, lote, cantidad, peso). Las tres tablas (`ETIQUETA`, `ETIQUETA_LINER`, `ETIQUETA_ROLLO`) son independientes — sin herencia entre sí.

### ¿Qué es el "Kardex"?
El **kardex** es el registro histórico de todos los movimientos de inventario. Muestra dónde está cada etiqueta en cada momento, y permite hacer auditorías de inventario. `tipoSalida` puede ser: `DESPACHO`, `BORRADO`, `M` (manual) o `B` (banda).

### ¿Qué es un "Formato de Área"?
Un **formato de área** es una plantilla que describe cómo deben ser los códigos de ubicación dentro de una bodega. Se compone de piezas ordenadas: letras, dígitos, textos fijos, separadores y números libres. Por ejemplo, el formato `Letra(A-Z) + "-" + Dígito + Dígito` valida áreas como `A-01`, `B-99`, `Z-10`.

---

## 🔎 Vistas BI

### `vw_EtiquetasBI` (BD `EMPAQUE(PR)`)

**Descripción**: Vista que **unifica las tres tablas separadas de etiquetas** (`ETIQUETA`, `ETIQUETA_LINER`, `ETIQUETA_ROLLO` — que NO tienen herencia entre sí) en una sola superficie consultable, con unidades ya normalizadas por unidad ERP.

**Propósito**: Es la **fuente oficial para BI y métricas** de efectividad de alistamiento y despacho. Cualquier consulta analítica sobre etiquetas debe leer de aquí, no de las tres tablas crudas.

| Columna             | Tipo       | Descripción                                                         |
|---------------------|------------|---------------------------------------------------------------------|
| `Etiqueta`          | NCHAR (PK) | Código de barras único de la etiqueta (paca / rollo / liner)        |
| `Item`              | INT        | Código ERP del producto                                             |
| `Descripcion`       | NVARCHAR   | Nombre del producto                                                 |
| `UnidadInventario`  | VARCHAR    | Unidad de inventario en el ERP (KG, UN, ML, etc.)                   |
| `Linea`             | NVARCHAR   | Línea de producción que generó la etiqueta                          |
| `Cantidad`          | DECIMAL    | Cantidad en unidades del producto                                   |
| `PesoNeto`          | DECIMAL    | Peso neto en kg                                                     |
| `PesoBruto`         | DECIMAL    | Peso bruto en kg                                                    |
| `Metros`            | DECIMAL    | Longitud en metros (aplica a rollos / liners)                       |
| `EstadoEtiqueta`    | VARCHAR    | Estado actual de la etiqueta                                        |
| `TipoEtiquetado`    | VARCHAR    | Origen: `ETIQUETA` / `ETIQUETA_LINER` / `ETIQUETA_ROLLO`             |
| `Desde`             | VARCHAR    | Sistema o módulo que generó el registro                              |
| `Valor`             | DECIMAL    | **Cantidad normalizada para BI** según la `UnidadInventario` del ERP |

**Reglas clave**:
- La columna `Valor` es la única que debe usarse para sumar/agregar en BI — ya está normalizada por unidad ERP.
- `Etiqueta` es única en toda la vista (PK lógica), aunque internamente provenga de tres tablas distintas.
- Cuando `Desde='ETIQUETA_LINER'` la columna `Etiqueta` puede venir como cadena de espacios (placeholder).
- La vista está expuesta vía MCP (servidor `mcp-mssql`, entidad `veb`).

---

## 📌 Notas Importantes

- Todas las tablas de `SIE` usan el prefijo `COD_` para claves primarias
- Todas las tablas de `EMPAQUE(PR)` usan el prefijo `id` para claves primarias (camelCase)
- El sistema opera en dos bases de datos diferentes (`SIE` y `EMPAQUE(PR)`)
- El ERP externo (Siesa UnoEE) se accede vía linked server `[erp.ie].[UnoEE_Doron]` — solo lectura, nunca INSERT/UPDATE/DELETE
- La tabla `KARDEX_BODEGA` es crítica para auditorías de inventario — nunca modificar directamente
- El Kardex de bodegas está en la aplicación **LECTURA DE BANDA** (`Frm_Kardex`)
- La gestión de formatos de área (tablas §12–§16) es administrada desde esa misma aplicación por usuarios con perfil administrador
- Para BI y métricas: siempre usar `FECHA_DESPACHO` de `CAMION_X_DIA`, nunca `FECHA`

---

**Autor**: Sistema IE  
**Fecha**: Diciembre 2024 — Actualizado Junio 2026  
**Versión**: 1.3 (agregada ITEMS_CACHE con UnidadEmpaque; correcciones de columnas reales en tablas operativas; linked server corregido a erp.ie)  
**Propósito**: Documentación para LLMs y desarrolladores
