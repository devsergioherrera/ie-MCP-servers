-- =====================================================================
-- GRANTs para el usuario mcp_reader (servidor SQL Server de IE)
-- Ejecutar como `sa` o un admin con permisos en ambas BDs.
-- Ejecutar CADA bloque por separado o asegurar que los GO procesen.
-- =====================================================================

-- ---------------------------------------------------------------------
-- BD SIE — logistica (programacion de despachos)
-- ---------------------------------------------------------------------
USE SIE;
GO

-- Asegurar que el USER existe (idempotente)
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mcp_reader')
    CREATE USER mcp_reader FOR LOGIN mcp_reader;
GO

GRANT SELECT ON dbo.CAMION                  TO mcp_reader;
GRANT SELECT ON dbo.CONDUCTOR               TO mcp_reader;
GRANT SELECT ON dbo.CAMION_X_DIA            TO mcp_reader;
GRANT SELECT ON dbo.DOCUMENTOS_DESPACHADOS  TO mcp_reader;
GRANT SELECT ON dbo.DETALLE_CAMION_X_DIA    TO mcp_reader;
GO


-- ---------------------------------------------------------------------
-- BD EMPAQUE(PR) — operacion (etiquetas, alistamiento, kardex)
-- ---------------------------------------------------------------------
USE [EMPAQUE(PR)];
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mcp_reader')
    CREATE USER mcp_reader FOR LOGIN mcp_reader;
GO

-- Vista BI (ya estaba, idempotente)
GRANT SELECT ON dbo.vw_EtiquetasBI                TO mcp_reader;

-- Etiquetas (tablas separadas)
GRANT SELECT ON dbo.ETIQUETA                      TO mcp_reader;
GRANT SELECT ON dbo.ETIQUETA_LINER                TO mcp_reader;
GRANT SELECT ON dbo.ETIQUETA_ROLLO                TO mcp_reader;

-- Inventario / movimientos
GRANT SELECT ON dbo.KARDEX_BODEGA                 TO mcp_reader;

-- Alistamiento
GRANT SELECT ON dbo.ALISTAMIENTO                  TO mcp_reader;
GRANT SELECT ON dbo.ALISTAMIENTO_ETIQUETA         TO mcp_reader;

-- Formatos de area
GRANT SELECT ON dbo.FormatoAreaBodega             TO mcp_reader;
GRANT SELECT ON dbo.FormatoAreaBodegaDetalle      TO mcp_reader;
GRANT SELECT ON dbo.BodegaFormato                 TO mcp_reader;
GRANT SELECT ON dbo.FormatoAreaBodegaHistorial    TO mcp_reader;
GRANT SELECT ON dbo.ConfiguracionAreasKardex      TO mcp_reader;
GO


-- ---------------------------------------------------------------------
-- Verificacion (opcional): listar permisos efectivos de mcp_reader
-- ---------------------------------------------------------------------
USE SIE;
SELECT
    DB_NAME()        AS database_name,
    pr.name          AS user_name,
    o.name           AS object_name,
    p.permission_name,
    p.state_desc
FROM sys.database_permissions p
JOIN sys.database_principals pr ON p.grantee_principal_id = pr.principal_id
JOIN sys.objects o ON p.major_id = o.object_id
WHERE pr.name = 'mcp_reader'
ORDER BY o.name;

USE [EMPAQUE(PR)];
SELECT
    DB_NAME()        AS database_name,
    pr.name          AS user_name,
    o.name           AS object_name,
    p.permission_name,
    p.state_desc
FROM sys.database_permissions p
JOIN sys.database_principals pr ON p.grantee_principal_id = pr.principal_id
JOIN sys.objects o ON p.major_id = o.object_id
WHERE pr.name = 'mcp_reader'
ORDER BY o.name;
