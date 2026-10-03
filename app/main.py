from fastapi import FastAPI

from app.routers import health

import os

app = FastAPI(title="TerraGraph")
app.include_router(health.router)
