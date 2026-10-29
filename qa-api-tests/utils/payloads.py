"""Constructores de payloads de emision y helpers de mutacion por 'path' tipo a.b.0.c."""
import copy

RECEPTOR_CANONICO = {
    "rut": "26461274-8",
    "razonSocial": "Empresa Receptora SpA",
    "giro": 458,          # acteco.id 'Edicion de programas informaticos' (rubro 10) - verificado QA
    "direccion": "Av. Providencia 1234",
    "comuna": 13101,      # comuna.id 'Santiago' (RM) - verificado QA
    "email": "factura@empresa.cl",
    "telefono": "92323420",
}


def factura33(**overrides):
    p = {
        "rutEmisor": "10471336-K",
        "tipoDte": 33,
        "receptor": copy.deepcopy(RECEPTOR_CANONICO),
        "items": [
            {"numeroLinea": 1, "nombreItem": "Servicio QA", "cantidad": 1,
             "precioUnitarioNeto": 100000, "monto": 100000},
        ],
        "montoNeto": 100000,
        "montoIVA": 19000,
        "montoTotal": 119000,
    }
    p.update(overrides)
    return p


def factura33_completa(**overrides):
    p = factura33()
    p["items"] = [
        {"numeroLinea": 1, "nombreItem": "Consultoria TI", "descripcion": "Desarrollo",
         "cantidad": 10, "precioUnitarioNeto": 50000, "codigoItem": "SKU-1", "unidadMedida": "UN",
         "movimientoItem": {"tipo": "D", "tipoValor": "%", "porcentaje": 10, "monto": 50000},
         "monto": 450000},
        {"numeroLinea": 2, "nombreItem": "Licencia software", "cantidad": 2,
         "precioUnitarioNeto": 80000, "monto": 160000},
    ]
    p["montoNeto"] = 610000
    p["montoIVA"] = 115900
    p["montoTotal"] = 725900
    p.update(overrides)
    return p


def factura34(**overrides):
    p = {
        "rutEmisor": "10471336-K",
        "tipoDte": 34,
        "receptor": copy.deepcopy(RECEPTOR_CANONICO),
        "items": [
            {"numeroLinea": 1, "nombreItem": "Consulta medica general", "cantidad": 1,
             "precioUnitarioNeto": 45000, "monto": 45000},
        ],
        "montoTotal": 45000,
    }
    p.update(overrides)
    return p


def nota_credito(folio_ref: int, tipo_ref: int = 33, **overrides):
    p = {
        "codigoReferencia": 1,
        "razonReferencia": "Anula documento por error en datos del receptor",
        "rutEmisor": "10471336-K",
        "receptor": {
            "rut": "26461274-8",
            "razonSocial": "Empresa Receptora SpA",
            "giro": "Edicion de programas informaticos",
            "direccion": "Av. Providencia 1234",
            "comuna": "Santiago",
            "email": "factura@empresa.cl",
            "telefono": "92323420",
        },
        "datosFactura": {
            "tipoDte": tipo_ref,
            "folio": folio_ref,
            "items": [
                {"numeroLinea": 1, "nombreItem": "Servicio QA", "cantidad": 1,
                 "precioUnitarioNeto": 100000, "monto": 100000},
            ],
            "montoNeto": 100000,
            "montoIVA": 19000,
            "montoTotal": 119000,
        },
    }
    p.update(overrides)
    return p


_MISSING = object()


def _split(path):
    return [int(x) if x.lstrip("-").isdigit() else x for x in path.split(".")]


def mutate(payload: dict, path: str, value):
    """Devuelve copia con path=value. value=DROP elimina la clave."""
    p = copy.deepcopy(payload)
    keys = _split(path)
    node = p
    for k in keys[:-1]:
        node = node[k]
    last = keys[-1]
    if value is DROP:
        if isinstance(node, list):
            node.pop(last)
        else:
            node.pop(last, None)
    else:
        node[last] = value
    return p


class _Drop:
    def __repr__(self):
        return "DROP"


DROP = _Drop()
