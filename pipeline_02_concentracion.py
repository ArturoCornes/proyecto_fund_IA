"""
pipeline_02_alta_concentracion.py
==================================
Pipeline: Alta Concentración de Compras por Proveedor

Reglas utilizadas (analisis_pyDatalog.py):
  - Region 2) alta_concentracion(O, P)       -> proveedor con >40% adjudicaciones en un organismo
  - Region 3) adjudica(O, P, C)              -> mapeo cantidad de adjudicaciones
  - Region 10) porcentaje_monto_proveedor[O,P] == PorcentajeMonto -> % del monto total que representa cada proveedor

Objetivo: Detectar organismos donde un solo proveedor concentra más del 40% de las compras (cantidad o monto).
"""

from LogiFlow.logiflow import Pipeline, Stage, Orchestrator, Query


def run() -> list:
    """Ejecuta el pipeline y retorna los KnowledgeSets de cada etapa."""

    # Etapa 1: Carga de hechos base
    load_stage = Stage(
        name="load_data",
        engine="pydatalog",
        rule_file="hechos_datalog.py",
        queries=[],
        outputs=[],
        depends_on=[]
    )

    # Etapa 2: Análisis de concentración (cantidad y monto)
    analysis_stage = Stage(
        name="analyze_concentration",
        engine="pydatalog",
        rule_file="analisis_pyDatalog.py",
        queries=[
            Query("alta_concentracion(O, P)"),
            Query("adjudica(O, P, C)"),
            Query("porcentaje_monto_proveedor[O, P] == Porcentaje")
        ],
        outputs=[],
        depends_on=[]
    )

    # Armar pipeline
    pipeline = Pipeline()
    pipeline.add_stage(load_stage)
    pipeline.add_stage(analysis_stage)

    # Ejecutar
    orchestrator = Orchestrator()
    results = orchestrator.run_pipeline(pipeline)

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("PIPELINE 2: Alta Concentración de Compras")
    print("=" * 60)
    results = run()
    for i, ks in enumerate(results):
        print(f"\n--- Resultado Etapa {i}: {ks.facts.keys()} ---")
        for pred, rows in ks.facts.items():
            print(f"  {pred}({len(rows)} filas)")
            for row in rows[:10]:
                print(f"    {row}")
