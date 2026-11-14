"""Monitoreo de errores y rendimiento con Sentry."""

import os

import sentry_sdk


def init_sentry() -> bool:
    """Activa Sentry si existe `SENTRY_DSN`; si no, la app corre sin monitoreo.

    Las pruebas y el CI no tienen el DSN, así que no mandan eventos.
    Devuelve `True` si Sentry quedó activo.
    """
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        # Separa en Sentry lo de tu máquina (development) de lo real (production).
        environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
        # SHA del commit desplegado; agrupa los errores por versión.
        release=os.environ.get("SENTRY_RELEASE"),
        # Con poco tráfico se puede medir el 100 % de las peticiones.
        traces_sample_rate=1.0,
    )
    return True
