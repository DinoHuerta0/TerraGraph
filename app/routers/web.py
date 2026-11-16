"""Página web: sirve el HTML que sube planes y dibuja el grafo."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

# app/static/, con el HTML, el CSS y el JavaScript de la página.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

router = APIRouter(tags=["web"])


# Fuera de /docs: no es parte de la API, es la página que la usa.
@router.get("/", include_in_schema=False)
def get_index() -> FileResponse:
    """La página principal.

    Un análisis guardado se abre con `/?id=<uuid>`; el JavaScript lee el `id` y
    lo consulta en la API, así que el servidor siempre devuelve el mismo HTML.
    """
    return FileResponse(STATIC_DIR / "index.html")
