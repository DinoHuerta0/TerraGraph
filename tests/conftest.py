"""Configuración común de todas las pruebas."""

import os

# Las pruebas nunca mandan eventos a Sentry, aunque el .env cargado tenga SENTRY_DSN.
# conftest.py se importa antes que app.main, así que init_sentry() ya no lo encuentra.
os.environ.pop("SENTRY_DSN", None)
