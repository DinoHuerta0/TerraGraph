from fastapi import FastAPI

from app.routers import analyses, health

app = FastAPI(title="TerraGraph")
app.include_router(health.router)
app.include_router(analyses.router)

# Los errores del servicio se convierten en 404, 413 o 422.
for error_type in analyses.ERROR_STATUS_CODES:
    app.add_exception_handler(error_type, analyses.handle_service_error)
