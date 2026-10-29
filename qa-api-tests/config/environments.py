"""Configuracion de ambientes. DEV queda declarado pero NO se ejecuta en Fase 1.
ENV=QA (default) o ENV=DUMMYS (mock, solo canal App)."""
import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENTS = {
    "QA": {
        # login oficial QA (confirmado por el usuario): v2 / verticalqa.
        # El manual v1.5 documenta v1/apiqa (queda como alterno).
        "auth_url": "https://verticalqa.mcdesaqa.cl/public/auth/web/v2/login",
        "auth_url_alt": "https://apiqa.mcdesaqa.cl/public/auth/web/v1/login",
        "base_recepcion": "https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion",
        "base_nc": "https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/recepcion-nc",
        "base_consultas": "https://apiqa-cloud.mcdesaqa.cl/central/dte/fe/consultas",
        "user": os.getenv("QA_USER", "10471336-K"),
        "pass": os.getenv("QA_PASS", ""),
    },
    "DEV": {
        "auth_url": "https://apidev.mcdesaqa.cl/public/auth/web/v2/login",
        "auth_url_alt": "https://apidev.mcdesaqa.cl/public/auth/web/v1/login",
        "base_recepcion": "https://apidev-cloud.mcdesaqa.cl/central/dte/fe/recepcion",
        "base_nc": "https://apidev-cloud.mcdesaqa.cl/central/dte/fe/recepcion-nc",
        "base_consultas": "https://apidev-cloud.mcdesaqa.cl/central/dte/fe/consultas",
        "user": os.getenv("DEV_USER", ""),
        "pass": os.getenv("DEV_PASS", ""),
    },
    # APIs mock (devtunnel de un colega) mientras QA/DEV estan lentos. Solo expone el canal
    # App/POS (/v1/app/...) + actuator/health: sin login ni rutas con JWT. No emite DTE reales.
    # Coleccion: "Api Documento Tributario (Factura y NC) App-POS.postman_collection.json" (raiz).
    "DUMMYS": {
        "mock": True,
        "auth_url": "",
        "auth_url_alt": "",
        "base_recepcion": os.getenv("DUMMYS_BASE", "https://5nnpwr8b-3000.brs.devtunnels.ms") + "/central/dte/fe/recepcion",
        "base_nc": os.getenv("DUMMYS_BASE", "https://5nnpwr8b-3000.brs.devtunnels.ms") + "/central/dte/fe/recepcion-nc",
        "base_consultas": os.getenv("DUMMYS_BASE", "https://5nnpwr8b-3000.brs.devtunnels.ms") + "/central/dte/fe/consultas",
        "health": os.getenv("DUMMYS_BASE", "https://5nnpwr8b-3000.brs.devtunnels.ms") + "/mcs-central-be-recepcion-fe/actuator/health",
        "user": "10471336-K",
        "pass": "",
    },
}

# ambientes ejecutables: QA (Fase 1) y DUMMYS (mock, solo canal App). DEV sigue sin ejecutarse.
_EJECUTABLES = ("QA", "DUMMYS")


def env_name():
    env = os.getenv("ENV", "QA").upper()
    if env not in _EJECUTABLES:
        raise RuntimeError(f"Fase 1 solo ejecuta contra {'/'.join(_EJECUTABLES)}. ENV={env} no permitido.")
    return env


def current():
    return ENVIRONMENTS[env_name()]


def is_mock():
    return bool(current().get("mock"))


def reports_dir():
    """QA -> reports/ ; DUMMYS -> reports/dummys/ (no mezcla evidencia ni matriz con QA)."""
    base = pathlib.Path(__file__).resolve().parent.parent / "reports"
    return base / "dummys" if env_name() == "DUMMYS" else base


DTE_BUDGET = int(os.getenv("DTE_BUDGET", "54"))
