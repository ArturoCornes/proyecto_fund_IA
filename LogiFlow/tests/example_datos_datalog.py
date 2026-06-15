from pathlib import Path

from logiflow import Orchestrator, Pipeline, Stage, Query, Fact, KnowledgeSet

# 1. Import the Python-based PyDatalog logic
from . import datos_datalog

_TEST_DIR = Path(__file__).resolve().parent

def run_legacy_example():
    print("--- Running Legacy PyDatalog Integration Example ---")
    
    # 2. Extract data manually using the Python function
    raw_data = datos_datalog.extraer_datos_para_prolog()
    print(f"\nExtracted from Python PyDatalog: {raw_data}")

    # 3. Convert it into the new standard KnowledgeSet DTO
    ks = KnowledgeSet()
    for predicate, rows in raw_data.items():
        for row in rows:
            if isinstance(row, tuple):
                ks.add_fact(predicate, *row)
            else:
                ks.add_fact(predicate, row)
                
    # 4. We can inject this directly into a Prolog stage via its `outputs` property
    # (or we could build a custom 'Python' engine wrapper).
    
    # Let's map the KnowledgeSet to Facts for the Prolog stage
    prolog_outputs = []
    for predicate, rows in ks.facts.items():
        for row in rows:
            prolog_outputs.append(Fact(predicate, *row))

    prolog_stage = Stage(
        name="detect_fraud",
        engine="prolog",
        rule_file=str(_TEST_DIR / "reglas.pl"),
        queries=[
            Query("alerta_fraude(TxID, Usuario, Alerta)"),
        ],
        outputs=prolog_outputs,  # Injecting the bridged data here
        depends_on=[]
    )

    pipeline = Pipeline()
    pipeline.add_stage(prolog_stage)

    # 5. Run the orchestrator
    orchestrator = Orchestrator()
    results = orchestrator.run_pipeline(pipeline)
    
    # 6. Display the results
    prolog_knowledge = results[0] # Only one stage in pipeline
    print("\n--- Prolog KnowledgeSet Results ---")
    for alert in prolog_knowledge.facts.get("alerta_fraude", []):
        print(f"Alert Detected: TxID={alert[0]}, User={alert[1]}, Reason='{alert[2]}'")

if __name__ == "__main__":
    run_legacy_example()
