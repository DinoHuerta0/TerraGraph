from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.monitoring import init_sentry
from app.routers import analyses, health, web

# Antes de crear la app, para que Sentry instrumente FastAPI desde el inicio.
init_sentry()

app = FastAPI(title="TerraGraph")
app.include_router(health.router)
app.include_router(analyses.router)
app.include_router(web.router)

# CSS y JavaScript de la página, en /static/styles.css y /static/app.js.
app.mount("/static", StaticFiles(directory=web.STATIC_DIR), name="static")

# Los errores del servicio se convierten en 404, 413 o 422.
for error_type in analyses.ERROR_STATUS_CODES:
    app.add_exception_handler(error_type, analyses.handle_service_error)
