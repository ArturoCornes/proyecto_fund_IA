"""
pipeline_04_gastos_y_exclusivos.py
====================================
Pipeline: Gastos por Organismo y Proveedores Exclusivos

Reglas utilizadas (analisis_pyDatalog.py):
  - Region 5) proveedor_exclusivo(P) -> proveedores que trabajan con solo 1 organismo
  - Region 9) gasto_total_organismo[O] == X -> suma total de montos adjudicados por organismo

Objetivo: Identificar los organismos con mayor gasto total y detectar proveedores exclusivos (monopolio en un solo organismo).
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

    # Etapa 2: Análisis de gastos y proveedores exclusivos
    analysis_stage = Stage(
        name="analyze_expenses_exclusive",
        engine="pydatalog",
        rule_file="analisis_pyDatalog.py",
        queries=[
            Query("gasto_total_organismo[O] == X"),
            Query("proveedor_exclusivo(P)")
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
    print("PIPELINE 4: Gastos por Organismo y Proveedores Exclusivos")
    print("=" * 60)
    results = run()
    for i, ks in enumerate(results):
        print(f"\n--- Resultado Etapa {i}: {ks.facts.keys()} ---")
        for pred, rows in ks.facts.items():
            print(f"  {pred}({len(rows)} filas)")
            for row in rows[:10]:
                print(f"    {row}")
