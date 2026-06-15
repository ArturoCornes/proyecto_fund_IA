"""
pipeline_03_tiempo_adjudicacion.py
====================================
Pipeline: Análisis de Tiempo de Adjudicación

Reglas utilizadas (analisis_pyDatalog.py):
  - Region 11) tiempo_de_adjudicacion(O, P, TiempoPromedio) -> promedio dias entre licitacion y adjudicacion por pareja organismo-proveedor
  - Region 12) promedio_general_tiempo_adjudicaciones(PromedioGeneral) -> promedio general de todos los tiempos

Objetivo: Analizar cuánto tarda en promediar cada proveedor en ser adjudicado por cada organismo, comparado con el promedio general.
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

    # Etapa 2: Análisis de tiempos
    analysis_stage = Stage(
        name="analyze_times",
        engine="pydatalog",
        rule_file="analisis_pyDatalog.py",
        queries=[
            Query("tiempo_de_adjudicacion(O, P, TiempoPromedio)"),
            Query("promedio_general_tiempo_adjudicaciones(PromedioGeneral)")
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
    print("PIPELINE 3: Tiempo de Adjudicación")
    print("=" * 60)
    results = run()
    for i, ks in enumerate(results):
        print(f"\n--- Resultado Etapa {i}: {ks.facts.keys()} ---")
        for pred, rows in ks.facts.items():
            print(f"  {pred}({len(rows)} filas)")
            for row in rows[:10]:
                print(f"    {row}")
