# TerraGraph

Analizador de infraestructura Terraform basado en grafos. Proyecto final de CI/CD.

> **Estado:** en fase de diseño. Todavía no hay código ejecutable; este README se actualizará conforme avancen los milestones.

## Qué hace

TerraGraph recibe un plan de Terraform en formato JSON (la salida de `terraform show -json plan.tfplan`), construye el grafo dirigido de dependencias entre recursos y responde tres preguntas:

- **¿En qué orden se crean los recursos?** Orden topológico, agrupado en niveles que pueden crearse en paralelo.
- **¿Qué se rompe si destruyo este recurso?** Radio de impacto: todos los recursos que dependen de él, directa o transitivamente.
- **¿El plan tiene dependencias circulares?** Detección y reporte de ciclos.

Cada usuario inicia sesión con su cuenta de GitHub y guarda sus análisis. Una página web dibuja el grafo y resalta el radio de impacto al seleccionar un nodo.

## Stack

| Capa | Tecnología |
|---|---|
| Aplicación | Python 3.12, FastAPI, Pydantic |
| Base de datos | PostgreSQL en Neon, SQLAlchemy, Alembic |
| Autenticación | GitHub OAuth, JWT en cookie |
| Front | HTML, JavaScript, Cytoscape.js |
| Pruebas y calidad | pytest, pytest-cov, Ruff |
| Contenedores | Docker, Docker Compose, Docker Hub |
| CI/CD | GitHub Actions |
| Infraestructura | Terraform, AWS (VPC, EC2, S3), k3s, Traefik, DuckDNS |

## Arquitectura

El código se divide en dos capas:

- **Núcleo de grafos:** lógica pura sin dependencias externas (`ResourceGraph`, `PlanParser`, `CycleDetector`, `OrderPlanner`, `BlastRadiusCalculator`, `GraphExporter`).
- **Aplicación:** API, usuarios y persistencia (`AuthService`, `AnalysisService`, repositorios y routers).

La aplicación corre como contenedor en k3s sobre una EC2. Los datos viven en Neon, fuera de AWS, así que la infraestructura puede destruirse al final de cada sesión de trabajo sin perder información.

Los diagramas de clases, infraestructura y deployment están en la [Wiki](https://github.com/DinoHuerta0/TerraGraph/wiki).

## Estructura prevista

```text
TerraGraph/
├── app/
│   ├── core/          # núcleo de grafos
│   ├── services/      # AuthService, AnalysisService
│   ├── repositories/  # acceso a PostgreSQL
│   ├── routers/       # endpoints de la API
│   └── static/        # página web
├── tests/
│   └── fixtures/      # planes de Terraform de ejemplo
├── migrations/        # Alembic
├── k8s/               # manifiestos de Kubernetes
├── terraform/         # infraestructura de AWS
├── .github/workflows/ # ci, cd, infra-up, infra-down
├── Dockerfile
└── docker-compose.yml
```

## Cómo ejecutarlo

Pendiente. Se documentará al completar el milestone M4, cuando exista el entorno local con Docker Compose.

## Pipeline

| Workflow | Disparador | Qué hace |
|---|---|---|
| `ci.yml` | Pull request hacia `main` | Lint, pruebas con cobertura y build de la imagen |
| `cd.yml` | Merge a `main` o tag `vX.Y.Z` | Pruebas, build, push a Docker Hub y despliegue por SSH |
| `infra-up.yml` | Manual | `terraform apply` |
| `infra-down.yml` | Manual | `terraform destroy` |

El pipeline falla si alguna prueba falla o si la cobertura baja de 80 %.

## Flujo de trabajo

Se usa GitHub Flow:

- `main` está protegida y siempre es desplegable.
- Cada issue se trabaja en una rama corta: `feature/<issue>-<descripción>`, `fix/…`, `infra/…` o `docs/…`.
- Los cambios entran por pull request con los checks aprobados y squash merge.
- Los commits siguen Conventional Commits (`feat:`, `fix:`, `test:`, `ci:`, `docs:`).

## Plan de trabajo

| Milestone | Entregable |
|---|---|
| M1 · Diseño y base | Repositorio, Wiki, board, esqueleto del proyecto y CI mínimo |
| M2 · Núcleo de grafos | `ResourceGraph`, `PlanParser` y `CycleDetector` con pruebas |
| M3 · Análisis | `OrderPlanner`, `BlastRadiusCalculator`, exportador y `GraphAnalyzer` |
| M4 · Persistencia y login | Postgres, migraciones, repositorios, login con GitHub y endpoints |
| M5 · Contenedor y pipeline | Dockerfile, Docker Hub y pipeline completo de CI |
| M6 · Infraestructura y despliegue | Terraform, k3s, workflows de infraestructura y despliegue continuo |
| M7 · Visualización y cierre | Página web, demo con el plan propio y documentación final |

El avance se sigue en el [Project Board](https://github.com/DinoHuerta0/TerraGraph/projects) y en los [milestones](https://github.com/DinoHuerta0/TerraGraph/milestones).

## Documentación

- [Wiki: presentación del proyecto](https://github.com/DinoHuerta0/TerraGraph/wiki)
- [Issues](https://github.com/DinoHuerta0/TerraGraph/issues)

## Autor

[DinoHuerta0](https://github.com/DinoHuerta0)
