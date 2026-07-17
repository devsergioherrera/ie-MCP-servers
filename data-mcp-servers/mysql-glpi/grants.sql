-- =====================================================================
-- GRANTs para el usuario mcp_reader (MySQL de GLPI, host intempserv8)
-- Ejecutar como root/admin de MySQL en intempserv8.
-- Acceso de solo lectura a TODO el schema — gen-config.py se encarga
-- de whitelistear las tablas expuestas via MCP (excluye config/logs).
-- =====================================================================

CREATE USER IF NOT EXISTS 'mcp_reader'@'%' IDENTIFIED BY '<PASSWORD>';

GRANT SELECT ON `glpi-ie`.* TO 'mcp_reader'@'%';

FLUSH PRIVILEGES;

-- Verificacion (opcional):
-- SHOW GRANTS FOR 'mcp_reader'@'%';
