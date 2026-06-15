"""
pipeline_05_cobertura_y_datos.py
==================================
Pipeline: Cobertura de Proveedores y Calidad de Datos

Reglas utilizadas (analisis_pyDatalog.py):
  - Region 7) proveedor_muy_extendido(P) -> proveedores que cubren >25% de los organismos
  - Region 8) porcentaje_faltantes_proveedor[P] == Porcentaje -> % de adjudicaciones sin campo dias_adj_de

Objetivo: Identificar proveedores muy extendidos (presentes en más del 25% de organismos) y aquellos con alta tasa de datos faltantes.
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

    # Etapa 2: Análisis de cobertura y calidad de datos
    analysis_stage = Stage(
        name="analyze_coverage_data_quality",
        engine="pydatalog",
        rule_file="analisis_pyDatalog.py",
        queries=[
            Query("proveedor_muy_extendido(P)"),
            Query("cobertura_organismos[P] == Porcentaje"),
            Query("porcentaje_faltantes_proveedor[P] == Porcentaje")
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
    print("PIPELINE 5: Cobertura de Proveedores y Calidad de Datos")
    print("=" * 60)
    results = run()
    for i, ks in enumerate(results):
        print(f"\n--- Resultado Etapa {i}: {ks.facts.keys()} ---")
        for pred, rows in ks.facts.items():
            print(f"  {pred}({len(rows)} filas)")
            for row in rows[:10]:
                print(f"    {row}")
