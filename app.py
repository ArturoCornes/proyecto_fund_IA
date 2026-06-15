"""
app.py — Servidor Web para UY-CompraTracker
=============================================
Flask application that:
  1. Serves the HTML/CSS/JS dashboard at /
  2. Exposes REST API endpoints to list and run symbolic pipelines

API Endpoints:
  GET  /api/pipelines          — List all available pipelines with metadata
  POST /api/run/<pipeline_id>  — Execute a pipeline and return results as JSON

Usage:
    python app.py              # runs on http://localhost:5000
"""

import importlib
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, jsonify, render_template

app = Flask(__name__)


PIPELINE_REGISTRY = {
    "pipeline_01_proveedores_frecuentes": {
        "title": "Proveedores Frecuentes y Dominantes",
        "description": (
            "Identifica proveedores con más de 10 adjudicaciones y analiza su "
            "concentración porcentual por organismo. Útil para detectar proveedores "
            "recurrentes en el sector público."
        ),
        "rules": [
            "proveedor_frecuente(P) — Proveedores con >10 adjudicaciones",
            "adjudica(O, P, C) — Mapeo cantidad de adjudicaciones org-proveedor",
            "porcentaje_adjudicaciones(O,P) — % adjudicaciones por proveedor en organismo",
        ],
        "engine": "pydatalog",
        "stage_names": ["load_data", "analyze_suppliers"],
    },
    "pipeline_02_concentracion": {
        "title": "Alta Concentración de Compras",
        "description": (
            "Detecta organismos donde un solo proveedor concentra más del 40% de las "
            "compras (por cantidad o monto). Alerta temprana sobre posible favoritismo."
        ),
        "rules": [
            "alta_concentracion(O, P) — Proveedor con >40% adjudicaciones en organismo",
            "adjudica(O, P, C) — Cantidad de adjudicaciones por pareja org-prov",
            "porcentaje_monto_proveedor(O,P) — % del monto total que representa cada proveedor",
        ],
        "engine": "pydatalog",
        "stage_names": ["load_data", "analyze_concentration"],
    },
    "pipeline_03_tiempo_adjudicacion": {
        "title": "Tiempo de Adjudicación",
        "description": (
            "Analiza el tiempo promedio entre licitación y adjudicación por pareja "
            "organismo-proveedor, comparado con el promedio general. Plazos anómalos "
            "pueden indicar irregularidades."
        ),
        "rules": [
            "tiempo_de_adjudicacion(O,P,TiempoPromedio) — Promedio días org-proveedor",
            "promedio_general_tiempo_adjudicaciones(PromedioGeneral) — Promedio global",
        ],
        "engine": "pydatalog",
        "stage_names": ["load_data", "analyze_times"],
    },
    "pipeline_04_gastos_y_exclusivos": {
        "title": "Gastos por Organismo y Proveedores Exclusivos",
        "description": (
            "Calcula el gasto total adjudicado por organismo e identifica proveedores "
            "exclusivos (monopolio en un solo organismo). Útil para análisis de "
            "dependencia presupuestaria."
        ),
        "rules": [
            "gasto_total_organismo(O, X) — Suma total de montos por organismo",
            "proveedor_exclusivo(P) — Proveedores que trabajan con solo 1 organismo",
        ],
        "engine": "pydatalog",
        "stage_names": ["load_data", "analyze_expenses_exclusive"],
    },
    "pipeline_05_cobertura_y_datos": {
        "title": "Cobertura y Calidad de Datos",
        "description": (
            "Identifica proveedores muy extendidos (presentes en >25% de organismos) y "
            "aquellos con alta tasa de datos faltantes en el campo días_de_adjudicación."
        ),
        "rules": [
            "proveedor_muy_extendido(P) — Proveedores que cubren >25% de los organismos",
            "cobertura_organismos(P, Porcentaje) — % cobertura por proveedor",
            "porcentaje_faltantes_proveedor(P, Porcentaje) — % adjudicaciones sin campo días_adj",
        ],
        "engine": "pydatalog",
        "stage_names": ["load_data", "analyze_coverage_data_quality"],
    },
    "pipeline_06_deteccion_completa": {
        "title": "Detección Completa de Fraude (PyDatalog + Prolog)",
        "description": (
            "Pipeline completo que combina ambos motores simbólicos. PyDatalog extrae "
            "métricas cuantitativas y las inyecta en Prolog, que aplica reglas de "
            "detección de fraude: concentración sospechosa, adjudicaciones repetidas "
            "excesivas, sobretiempo y recomendación final de auditoría."
        ),
        "rules": [
            "PyDatalog: adjudica(O,P,C), total_adjudicaciones(O,T)",
            "PyDatalog: tiempo_de_adjudicacion(O,P,TiempoPromedio)",
            "Prolog: riesgo_concentracion — >=40% en un organismo",
            "Prolog: adjudicacion_repetida — >3 adjudicaciones en un organismo",
            "Prolog: alerta_sobretiempo — tiempo >1.5x promedio general",
            "Prolog: recomendar_auditoria(Org,Prov,motivo(Tipo,Valor))",
        ],
        "engine": "both",
        "stage_names": ["load_data", "extract_data", "detect_fraud"],
    },
}


def _serialize_value(value):
    if isinstance(value, tuple):
        return [_serialize_value(v) for v in value]
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def _serialize_ks(ks):
    """Convert a logiflow.KnowledgeSet into a plain dict for JSON."""
    if ks is None:
        return {}
    result = {}
    for predicate, rows in getattr(ks, "facts", {}).items():
        result[predicate] = [_serialize_value(row) for row in rows]
    return result


def _run_pipeline_module(pipeline_id):
    """Dynamically import and run the pipeline module."""
    try:
        mod = importlib.import_module(pipeline_id)
    except Exception as exc:
        return {}, f"Cannot import module '{pipeline_id}': {exc}"

    if not hasattr(mod, "run"):
        return {}, (
            f"Module '{pipeline_id}' has no run() function. "
            "Make sure the pipeline file defines a callable `run()`."
        )

    try:
        raw_results = mod.run()
    except Exception as exc:
        return {}, f"Pipeline execution failed: {exc}"

    if not isinstance(raw_results, (list, tuple)):
        return {}, "Expected run() to return a list of KnowledgeSets."

    stage_names = PIPELINE_REGISTRY.get(pipeline_id, {}).get("stage_names", [])
    stages = []
    for i, ks in enumerate(raw_results):
        stage_name = stage_names[i] if i < len(stage_names) else f"Etapa {i + 1}"
        stages.append({
            "name": stage_name,
            "facts": _serialize_ks(ks),
        })

    return {"stages": stages}, None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/pipelines", methods=["GET"])
def list_pipelines():
    result = []
    for pid, meta in PIPELINE_REGISTRY.items():
        result.append({
            "id": pid,
            "title": meta["title"],
            "description": meta["description"],
            "rules": meta["rules"],
            "engine": meta["engine"],
        })
    return jsonify(result)


@app.route("/api/run/<pipeline_id>", methods=["POST"])
def run_pipeline(pipeline_id):
    if pipeline_id not in PIPELINE_REGISTRY:
        return jsonify({
            "error": f"Pipeline '{pipeline_id}' not found.",
            "available_pipelines": list(PIPELINE_REGISTRY.keys()),
        }), 404

    meta = PIPELINE_REGISTRY[pipeline_id]
    stage_results, error = _run_pipeline_module(pipeline_id)

    if error:
        return jsonify({"error": error}), 500

    return jsonify({
        "title": meta["title"],
        "description": meta["description"],
        "engine": meta["engine"],
        "timestamp": datetime.now().isoformat(),
        **stage_results,
    })


if __name__ == "__main__":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("=" * 60)
    print("UY-CompraTracker - Dashboard Web")
    print(f"Available pipelines: {len(PIPELINE_REGISTRY)}")
    # for pid in PIPELINE_REGISTRY:
    #     title = PIPELINE_REGISTRY[pid]["title"]
    #     print(f"  [ {pid} ] -> {title}")
    # print("=" * 60)
    app.run(debug=True, host="127.0.0.1", port=5000)
