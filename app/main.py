from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="TerraGraph")
app.include_router(health.router)
