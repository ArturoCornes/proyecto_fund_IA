"""
pipeline_01_proveedores_frecuentes.py
=====================================
Pipeline: Proveedores Frecuentes y Dominantes

Reglas utilizadas (analisis_pyDatalog.py):
  - Region 1) proveedor_frecuente(P)       -> proveedores con >10 adjudicaciones
  - Region 3) adjudica(O, P, C)            -> mapeo organismo-proveedor-cantidad
  - Region 6) porcentaje_adjudicaciones[O,P] == Porcentaje -> % de adjudicaciones por proveedor en un organismo

Objetivo: Identificar proveedores que realizan muchas compras y ver su concentración por organismo.
"""

from LogiFlow.logiflow import Pipeline, Stage, Orchestrator, Query


def run() -> list:
    """Ejecuta el pipeline y retorna los KnowledgeSets de cada etapa."""

    # Etapa 1: Carga de hechos base (datos crudos)
    load_stage = Stage(
        name="load_data",
        engine="pydatalog",
        rule_file="hechos_datalog.py",
        queries=[],
        outputs=[],
        depends_on=[]
    )

    # Etapa 2: Análisis de proveedores frecuentes y dominantes
    analysis_stage = Stage(
        name="analyze_suppliers",
        engine="pydatalog",
        rule_file="analisis_pyDatalog.py",
        queries=[
            Query("proveedor_frecuente(P)"),
            Query("adjudica(O, P, C)"),
            Query("porcentaje_adjudicaciones[O, P] == Porcentaje")
        ],
        outputs=[],
        depends_on=[load_stage]
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
    print("PIPELINE 1: Proveedores Frecuentes y Dominantes")
    print("=" * 60)
    results = run()
    for i, ks in enumerate(results):
        print(f"\n--- Resultado Etapa {i}: {ks.facts.keys()} ---")
        for pred, rows in ks.facts.items():
            print(f"  {pred}({len(rows)} filas)")
            for row in rows[:10]:
                print(f"    {row}")
