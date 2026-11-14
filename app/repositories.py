"""Acceso a la tabla `analyses`."""

import uuid

from sqlalchemy.orm import Session

from app.models import Analysis


class AnalysisRepository:
    """Guarda y busca análisis en la base.

    Es la única clase que usa la sesión de SQLAlchemy: el servicio (#16) solo
    llama a `save` y `get`, y en sus pruebas se cambia por un repositorio en
    memoria.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, analysis: Analysis) -> Analysis:
        """Inserta el análisis y lo devuelve con `id` y `created_at`."""
        self._session.add(analysis)
        self._session.commit()
        # created_at lo pone la base; refresh lo lee aunque la sesión use
        # expire_on_commit=False.
        self._session.refresh(analysis)
        return analysis

    def get(self, analysis_id: uuid.UUID) -> Analysis | None:
        """Devuelve el análisis, o `None` si no existe ese id."""
        return self._session.get(Analysis, analysis_id)
