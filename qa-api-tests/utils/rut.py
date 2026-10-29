"""Utilidades de RUT chileno (modulo 11)."""


def dv(numero: int) -> str:
    s, m = 0, 2
    for d in reversed(str(numero)):
        s += int(d) * m
        m = 2 if m == 7 else m + 1
    r = 11 - (s % 11)
    return "0" if r == 11 else "K" if r == 10 else str(r)


def formatear(numero: int, con_puntos: bool = False, con_guion: bool = True) -> str:
    cuerpo = str(numero)
    if con_puntos:
        partes = []
        while len(cuerpo) > 3:
            partes.insert(0, cuerpo[-3:])
            cuerpo = cuerpo[:-3]
        partes.insert(0, cuerpo)
        cuerpo = ".".join(partes)
    return f"{cuerpo}-{dv(numero)}" if con_guion else f"{cuerpo}{dv(numero)}"


def es_valido(rut: str) -> bool:
    rut = rut.replace(".", "").replace("-", "").strip().upper()
    if len(rut) < 2 or not rut[:-1].isdigit():
        return False
    return dv(int(rut[:-1])) == rut[-1]


# RUT valido distinto del emisor QA (10471336-K), para el caso critico sub != rutEmisor
RUT_OTRO_VALIDO = formatear(77151256)  # 77151256-9  (usado en ejemplos del manual)
RUT_RECEPTOR = "26461274-8"            # de la coleccion mundo feliz
EMISOR_QA = "10471336-K"
