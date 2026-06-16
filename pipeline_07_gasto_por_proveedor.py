"""
pipeline_07_gasto_por_proveedor.py
====================================
Pipeline: Gasto Total por Proveedor

Reglas utilizadas (analisis_pyDatalog.py):
  - Region 13) gasto_total_proveedor[P] == X -> suma de montos adjudicados por proveedor (en UYU)

Objetivo: Calcular cuánto dinero recibió en total cada proveedor a lo largo de todas sus
adjudicaciones y presentar el ranking de mayor a menor.
"""

from LogiFlow.logiflow import Pipeline, Stage, Orchestrator, Query


def run() -> list:
    """Ejecuta el pipeline y retorna los KnowledgeSets de cada etapa."""

    load_stage = Stage(
        name="load_data",
        engine="pydatalog",
        rule_file="hechos_datalog.py",
        queries=[],
        outputs=[],
        depends_on=[]
    )

    analysis_stage = Stage(
        name="analyze_spending_by_supplier",
        engine="pydatalog",
        rule_file="analisis_pyDatalog.py",
        queries=[
            Query("gasto_total_proveedor[P] == X"),
        ],
        outputs=[],
        depends_on=[load_stage]
    )

    pipeline = Pipeline()
    pipeline.add_stage(load_stage)
    pipeline.add_stage(analysis_stage)

    orchestrator = Orchestrator()
    results = orchestrator.run_pipeline(pipeline)

    # Sort gasto_total_proveedor descending by monto (index 1 of each tuple).
    # The KnowledgeSet stores the full query string as the predicate key
    # (e.g. "gasto_total_proveedor[P] == X"), so we match by prefix.
    analysis_ks = results[-1]
    for pred, rows in analysis_ks.facts.items():
        if pred.startswith("gasto_total_proveedor"):
            rows.sort(
                key=lambda row: row[1] if row[1] is not None else 0,
                reverse=True
            )

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("PIPELINE 7: Gasto Total por Proveedor (ranking mayor a menor)")
    print("=" * 60)
    results = run()
    for i, ks in enumerate(results):
        print(f"\n--- Resultado Etapa {i}: {list(ks.facts.keys())} ---")
        for pred, rows in ks.facts.items():
            print(f"  {pred} ({len(rows)} filas)")
            for row in rows[:20]:
                print(f"    {row}")
