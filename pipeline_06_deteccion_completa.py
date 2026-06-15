"""
pipeline_06_deteccion_completa.py
===================================
Pipeline: Detección Completa de Fraude (PyDatalog + Prolog)

Este pipeline combina ambos motores simbólicos en una cadena de análisis:

Etapa 1 - PyDatalog (hechos): Carga los datos base.

Etapa 2 - PyDatalog (análisis cuantitativo):
  Reglas utilizadas (analisis_pyDatalog.py):
    - Region 3) adjudica(O, P, C)           -> cantidad de adjudicaciones por pareja org-prov
    - Region 11) tiempo_de_adjudicacion(O,P,TiempoPromedio) -> promedio dias adjudicacion
    - Region 12) promedio_general_tiempo_adjudicaciones(PromedioGeneral)

Etapa 3 - Prolog (detección de fraude):
  Reglas utilizadas (motor_prolog.pl):
    - riesgo_concentracion(O, P, Porcentaje) -> proveedor concentra >=40% en un organismo
    - adjudicacion_repetida(O, P, Cantidad)   -> proveedor tiene >3 adjudicaciones en un organismo  
    - alerta_sobretiempo(O, P, Tiempo, PromedioGeneral) -> tiempo de adjudicación >1.5x el promedio general
    - recomendar_auditoria(Organismo, Proveedor, motivo(Tipo, Valor)) -> recomendación final de auditoría

Objetivo: Pipeline completo que detecta patrones sospechosos y recomienda auditorías basadas en concentración, 
repetición excesiva y sobretiempo.
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

    # Etapa 2: Análisis cuantitativo con PyDatalog
    pydatalog_stage = Stage(
        name="extract_data",
        engine="pydatalog",
        rule_file="analisis_pyDatalog.py",
        queries=[
            Query("adjudica(Organismo, Proveedor, Cantidad)"),
            Query("total_adjudicaciones(Organismo, Total)"),
            Query("tiempo_de_adjudicacion(O, P, TiempoPromedio)"),
            Query("promedio_general_tiempo_adjudicaciones(PromedioGeneral)")
        ],
        outputs=[],
        depends_on=[]
    )

    # Etapa 3: Detección de fraude con Prolog (depende del análisis PyDatalog)
    prolog_stage = Stage(
        name="detect_fraud",
        engine="prolog",
        rule_file="motor_prolog.pl",
        queries=[
            Query("recomendar_auditoria(Org, Prov, motivo(Motivo, Valor))")
        ],
        outputs=[],
        depends_on=[pydatalog_stage]
    )

    # Armar pipeline con dependencias
    pipeline = Pipeline()
    pipeline.add_stage(load_stage)
    pipeline.add_stage(pydatalog_stage)
    pipeline.add_stage(prolog_stage)

    # Ejecutar
    orchestrator = Orchestrator()
    results = orchestrator.run_pipeline(pipeline)

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("PIPELINE 6: Detección Completa de Fraude")
    print("=" * 60)
    results = run()
    
    for i, ks in enumerate(results):
        stage_names = ["load_data", "extract_data", "detect_fraud"]
        name = stage_names[i] if i < len(stage_names) else f"stage_{i}"
        print(f"\n--- Resultado Etapa {i}: {name} ---")
        for pred, rows in ks.facts.items():
            print(f"  {pred}({len(rows)} filas)")
            for row in rows[:15]:
                print(f"    {row}")
