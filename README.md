<div align="center">
  <img src="./Assets/logo.png" alt="Integral de Empaques" width="300" />
</div>

# Nombre del Proyecto

> Breve descripcion del proyecto (1-2 lineas).

---

## Stack Tecnologico

| Capa              | Tecnologia              |
| ----------------- | ----------------------- |
| **Lenguaje**      | C# / Python / etc.      |
| **Runtime**       | .NET 8 / Node.js / etc. |
| **Base de datos** | SQL Server              |

---

## Requisitos

- [ ] Requisito 1
- [ ] Requisito 2

---

## Instalacion y Ejecucion

### 1. Clonar el repositorio

```bash
git clone https://github.com/ORGANIZACION/NOMBRE-REPO.git
cd NOMBRE-REPO
```

### 2. Configurar hooks de Git

```bash
# Windows: doble click en setup.bat
# O manualmente:
git config core.hooksPath .githooks
```

### 3. Configurar OpenProject

Editar `.openproject.conf` y poner el `PROJECT_ID` correspondiente:

```
PROJECT_ID=9    # Cambiar segun proyecto
TYPE_ID=10      # Tipo de tarea (10 = CAMBIO)
```

IDs de proyectos disponibles:

| ID  | Proyecto                       |
| --- | ------------------------------ |
| 16  | DESPACHO EN LINEA              |
| 15  | ETIQUETADO PRODUCTO EN PROCESO |
| 14  | GESTION HUMANA                 |
| 13  | GENERACION IPT                 |
| 12  | DESBLOQUEO DE ORDENES          |
| 11  | KARDEX                         |
| 10  | Procesos Disciplinarios        |
| 9   | ALISTAMIENTO                   |
| 8   | Daily Sistemas                 |

### 4. Configurar API Key de OpenProject

```powershell
[Environment]::SetEnvironmentVariable("OPENPROJECT_API_KEY","TU_API_KEY","User")
```

> Reiniciar la terminal despues de configurar la variable.

### 5. Ejecutar el proyecto

```bash
# Completar segun tipo de proyecto
```

---

## Estructura del Proyecto

```
NOMBRE-REPO/
├── .github/
│   └── copilot-instructions.md   GitHub Copilot → AGENTS.md
├── .githooks/
│   └── post-commit               Hook post-commit → OpenProject
├── assets/
│   └── logo.png                  Logo de la empresa
├── docs/                         Documentacion adicional (Modelados y demás)
├── skills/                       Skills de Claude Code (opcional)
├── .cursorrules                  Cursor → AGENTS.md
├── .openproject.conf             PROJECT_ID y TYPE_ID del proyecto
├── AGENTS.md                     Contexto central para agentes de IA
├── CLAUDE.md                     Claude Code → AGENTS.md
├── GEMINI.md                     Gemini → AGENTS.md
├── README.md
└── setup.bat                     Configuracion inicial (hooks)
```

---

## Desarrollo Asistido por IA

Este proyecto esta preparado para trabajar con agentes de IA de cualquier proveedor. Toda la configuracion del proyecto se centraliza en **`AGENTS.md`**, y cada proveedor tiene su archivo que apunta ahi:

| Archivo                           | Agente                                |
| --------------------------------- | ------------------------------------- |
| `AGENTS.md`                       | Contexto central (todos leen de aqui) |
| `CLAUDE.md`                       | Claude Code (Anthropic)               |
| `GEMINI.md`                       | Gemini (Google)                       |
| `.github/copilot-instructions.md` | GitHub Copilot                        |
| `.cursorrules`                    | Cursor                                |

Para agregar contexto al proyecto, editar **`AGENTS.md`** — todos los agentes lo reciben automaticamente.

---

## Licencia

Software propietario de **Integral de Empaques S.A.S.** — Uso interno exclusivo.
