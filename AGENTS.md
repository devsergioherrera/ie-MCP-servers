# AGENTS.md

## Project overview

<!-- Nombre, descripcion breve, stack con versiones -->

- **Nombre**:
- **Tipo**: <!-- WinForms / API / Web / Script -->
- **Empresa**: Integral de Empaques S.A.S.
- **Stack**: <!-- ej: C# 12, .NET 8, SQL Server, Dapper -->

## Commands

## Project structure

La documentación del contexto podrá encontrarla en docs/ pero las carpetas utilizadas se podrán encontrar en:

<!-- Carpetas clave y su proposito -->

```
NOMBRE_PROYECTO/
├── Models/         Entidades del dominio
├── Services/       Logica de negocio
├── Repository/     Acceso a datos
├── DTOs/           Objetos de transferencia
└── ...
```

## Code style

- Queries SQL parametrizadas (`@param`), nunca concatenar
- Logica de negocio en Services, nunca en UI/Forms
- Nombres descriptivos orientados al negocio, PascalCase para clases
- Metodos async con sufijo `Async`
- Enums para comparaciones de tipo/estado, no strings

## Git workflow

- Commits: prefijo convencional (`feat:`, `fix:`, `docs:`, `refactor:`)
- Hook `post-commit` crea tarea automatica en OpenProject
- Configurar con `setup.bat` y editar `.openproject.conf`
- La creación de ramas depende del proyecto, no siempre es necesario por efectos de tiempo.

## Boundaries

### Siempre

- Validar con datos reales antes de subir cambios
- Usar tipado fuerte.
- Usar patrones de diseño
- Priorizar el uso de variables de entorno si es necesario (Como por ejemplo el app.config para proyectos de .NET)
- Si se cambia el nombre de los métodos, cambiar las referencias que a estos apuntan.

### Preguntar primero

- Cambios en esquema de base de datos
- Modificaciones a vistas SQL compartidas con BI
- Cambios cross-database (linked server)

### Nunca

- Modificar tablas del ERP (solo lectura)
- Alterar `KARDEX_BODEGA` sin revision
- Commitear credenciales o connection strings
- Romper flujos de estado entre sistemas
