"""
pipeline_08_proveedores_por_organismo.py
=========================================
Pipeline: Proveedores por Organismo Gubernamental

Reglas utilizadas (analisis_pyDatalog.py):
  - Region 14) proveedor_organismo(O, P) — lista todos los pares organismo-proveedor únicos
  - Region 10) monto_proveedor_organismo[O, P] — suma del monto que un proveedor recibió de un organismo

Objetivo: Obtener la lista completa de proveedores registrados para cada organismo
gubernamental, junto con el monto total que cada uno recibió de dicho organismo.
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

    # Etapa 2: Análisis — proveedores por organismo + montos
    analysis_stage = Stage(
        name="proveedores_por_organismo",
        engine="pydatalog",
        rule_file="analisis_pyDatalog.py",
        queries=[
            # Regla 14: lista de pares organismo-proveedor únicos
            Query("proveedor_organismo(O, P)"),
            # Regla 10: monto total que cada proveedor recibió de cada organismo
            Query("monto_proveedor_organismo[O, P] == M"),
        ],
        outputs=[],
        depends_on=[load_stage]
    )

    pipeline = Pipeline()
    pipeline.add_stage(load_stage)
    pipeline.add_stage(analysis_stage)

    orchestrator = Orchestrator()
    results = orchestrator.run_pipeline(pipeline)

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("PIPELINE 8: Proveedores por Organismo Gubernamental")
    print("=" * 60)
    results = run()
    for i, ks in enumerate(results):
        print(f"\n--- Resultado Etapa {i}: {list(ks.facts.keys())} ---")
        for pred, rows in ks.facts.items():
            print(f"  {pred} ({len(rows)} filas)")
            for row in rows[:10]:
                print(f"    {row}")
