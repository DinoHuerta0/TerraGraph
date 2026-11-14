"""Modelos guardados en PostgreSQL."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Analysis(Base):
    """Un plan subido por alguien; se consulta por su UUID.

    Solo se guarda el plan, no el resultado: el análisis se recalcula al
    consultarlo con `GraphAnalyzer`.
    """

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    # JSONB en Postgres; JSON genérico en otras bases (SQLite en las pruebas).
    plan_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    resource_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
