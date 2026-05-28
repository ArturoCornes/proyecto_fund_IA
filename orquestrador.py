from collections import defaultdict
from pathlib import Path

try:
    from pyDatalog import pyDatalog
    from pyswip import Prolog
except ImportError as exc:
    raise SystemExit(
        "[ERROR] Faltan dependencias. Instale pyDatalog y pyswip para ejecutar "
        "el puente pyDatalog -> Prolog."
    ) from exc

import analisis_pyDatalog  # importa y registra las reglas pyDatalog


BASE_DIR = Path(__file__).resolve().parent
MOTOR_PROLOG = BASE_DIR / "motor_prolog.pl"
MOTOR_PROLOG_PATH = str(MOTOR_PROLOG).replace("\\", "/")
MAX_RESULTADOS = 20


def consultar_pydatalog(consulta):
    resultado = pyDatalog.ask(consulta)
    if resultado is None:
        return []
    return list(resultado.answers or [])


def atomo_prolog(valor):
    texto = str(valor).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{texto}'"


def numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def assertz(prolog, predicado, *argumentos):
    prolog.assertz(f"{predicado}({', '.join(argumentos)})")


def cargar_hechos_en_prolog(prolog):
    pyDatalog.create_terms(
        "X, O, P, C, D, "
        "adjudicaciones_org, adjudicaciones_proveedor_org, "
        "organismo_de, proveedor_de, dias_adj_de"
    )

    prolog.consult(MOTOR_PROLOG_PATH)
    prolog.retractall("adjudica(_, _, _)")
    prolog.retractall("total_adjudicaciones(_, _)")
    prolog.retractall("tiempo_de_adjudicacion(_, _, _)")
    prolog.retractall("promedio_general_tiempo_adjudicaciones(_)")

    for organismo, total in consultar_pydatalog("adjudicaciones_org[O] == C"):
        total = numero(total)
        if organismo is None or total is None:
            continue
        assertz(
            prolog,
            "total_adjudicaciones",
            atomo_prolog(organismo),
            str(int(total)),
        )

    for organismo, proveedor, cantidad in consultar_pydatalog(
        "adjudicaciones_proveedor_org[O, P] == C"
    ):
        cantidad = numero(cantidad)
        if organismo is None or proveedor is None or cantidad is None:
            continue
        assertz(
            prolog,
            "adjudica",
            atomo_prolog(organismo),
            atomo_prolog(proveedor),
            str(int(cantidad)),
        )

    tiempos = defaultdict(list)

    for organismo, proveedor, dias in consultar_pydatalog(
        "(organismo_de[X] == O) & "
        "(proveedor_de[X] == P) & "
        "(dias_adj_de[X] == D)"
    ):
        dias = numero(dias)
        if organismo is None or proveedor is None or dias is None or dias < 0:
            continue
        tiempos[(organismo, proveedor)].append(dias)

    todos_los_tiempos = [
        dias
        for valores in tiempos.values()
        for dias in valores
    ]

    if todos_los_tiempos:
        promedio = sum(todos_los_tiempos) / len(todos_los_tiempos)
        assertz(
            prolog,
            "promedio_general_tiempo_adjudicaciones",
            f"{promedio:.2f}",
        )

    for (organismo, proveedor), valores in tiempos.items():
        promedio = sum(valores) / len(valores)
        assertz(
            prolog,
            "tiempo_de_adjudicacion",
            atomo_prolog(organismo),
            atomo_prolog(proveedor),
            f"{promedio:.2f}",
        )


def valor_prolog(valor):
    if isinstance(valor, bytes):
        return valor.decode("utf-8")
    return str(valor)


def imprimir_seccion(titulo, filas, formatear):
    print(f"\n{titulo}")
    print("=" * len(titulo))

    if not filas:
        print("Sin resultados.")
        return

    for fila in filas[:MAX_RESULTADOS]:
        print(f"- {formatear(fila)}")

    if len(filas) > MAX_RESULTADOS:
        print(f"... {len(filas) - MAX_RESULTADOS} resultados mas.")


def main():
    prolog = Prolog()
    cargar_hechos_en_prolog(prolog)

    riesgos = list(prolog.query(
        "riesgo_concentracion(Organismo, Proveedor, Porcentaje)"
    ))
    riesgos.sort(key=lambda x: float(x["Porcentaje"]), reverse=True)

    repetidas = list(prolog.query(
        "adjudicacion_repetida(Organismo, Proveedor, Cantidad)"
    ))
    repetidas.sort(key=lambda x: int(x["Cantidad"]), reverse=True)

    sobretiempos = list(prolog.query(
        "alerta_sobretiempo(Organismo, Proveedor, Tiempo, Promedio)"
    ))
    sobretiempos.sort(key=lambda x: float(x["Tiempo"]), reverse=True)

    recomendaciones = list(prolog.query(
        "recomendar_auditoria(Organismo, Proveedor, Motivo)"
    ))

    imprimir_seccion(
        "Riesgos de concentracion",
        riesgos,
        lambda r: (
            f"{valor_prolog(r['Organismo'])} -> "
            f"{valor_prolog(r['Proveedor'])}: "
            f"{float(r['Porcentaje']):.1f}% de las adjudicaciones"
        ),
    )

    imprimir_seccion(
        "Adjudicaciones repetidas",
        repetidas,
        lambda r: (
            f"{valor_prolog(r['Organismo'])} -> "
            f"{valor_prolog(r['Proveedor'])}: "
            f"{int(r['Cantidad'])} adjudicaciones"
        ),
    )

    imprimir_seccion(
        "Alertas por sobretiempo",
        sobretiempos,
        lambda r: (
            f"{valor_prolog(r['Organismo'])} -> "
            f"{valor_prolog(r['Proveedor'])}: "
            f"{float(r['Tiempo']):.1f} dias promedio "
            f"(general {float(r['Promedio']):.1f})"
        ),
    )

    imprimir_seccion(
        "Recomendaciones de auditoria",
        recomendaciones,
        lambda r: (
            f"{valor_prolog(r['Organismo'])} -> "
            f"{valor_prolog(r['Proveedor'])}: "
            f"{valor_prolog(r['Motivo'])}"
        ),
    )


if __name__ == "__main__":
    main()
