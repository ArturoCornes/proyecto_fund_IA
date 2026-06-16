# Symbolic AI Orchestrator Library

The Symbolic AI Orchestrator Library is a Python framework designed to manage and execute multi-engine logical pipelines. It allows developers to string together declarative logic blocks written in different paradigms (such as PyDatalog and Prolog) into a unified, dependency-managed workflow.

## Table of Contents
1. [Core Concepts](#core-concepts)
2. [Data Exchange (`KnowledgeSet`)](#data-exchange-knowledgeset)
3. [Engines & Wrappers](#engines--wrappers)
4. [Writing Rules](#writing-rules)
5. [Pipeline Construction](#pipeline-construction)
6. [Full Example](#full-example)

---

## Core Concepts

### 1. `Orchestrator`
The `Orchestrator` is the central engine runner. It takes a defined `Pipeline`, validates the Directed Acyclic Graph (DAG) to ensure no circular dependencies exist, and executes the stages in topological order. 

### 2. `Pipeline`
A `Pipeline` is a collection of `Stage` objects. It defines the complete lifecycle of your data processing logic.

### 3. `Stage`
A `Stage` represents a single computational step executed by a specific engine.
* **`name`**: Unique identifier for the stage.
* **`engine`**: The logic engine to use (e.g., `"prolog"`, `"pydatalog"`).
* **`rule_file`**: The file containing the logic rules (e.g., `.pl` for Prolog, `.dl` for PyDatalog).
* **`queries`**: A list of `Query` objects to run against the engine once the rules and data are loaded.
* **`outputs`**: (Optional) Hardcoded `Fact` objects injected into the stage upon startup.
* **`depends_on`**: A list of upstream `Stage` objects that must execute first. Data output by dependencies is automatically merged and fed into this stage.

---

## Data Exchange (`KnowledgeSet`)

The Orchestrator utilizes a standard Data Transfer Object (DTO) called the `KnowledgeSet`. This ensures data can seamlessly flow between heterogeneous engines (like PyDatalog to Prolog) without requiring manual data mapping.

A `KnowledgeSet` simply stores facts as a dictionary mapping a predicate name to a list of atom tuples:
```python
{
    "transaccion": [
        ("tx_001", "juan", 15000),
        ("tx_002", "maria", 500)
    ]
}
```

Whenever a stage executes a query, it returns its results wrapped in a `KnowledgeSet`. The Orchestrator collects this and automatically injects it into any downstream stage that depends on it.

---

## Engines & Wrappers

### Prolog (`PrologWrapper`)
Wraps the SWI-Prolog engine (via `pyswip`).
* Evaluates standard `.pl` files.
* Automatically serializes and decodes byte-strings returned by PySWIP to native Python strings.
* Automatically injects incoming `KnowledgeSet` records as Prolog `Fact` objects.

### PyDatalog (`PyDatalogWrapper`)
Wraps the `pyDatalog` logical engine.
* Dynamically parses pure text datalog logic files (`.dl`), automatically registering term variables globally.
* Maps `pyDatalog.ask()` tuple results cleanly into outgoing `KnowledgeSet` DTOs.

---

## Writing Rules

### Prolog (`.pl`)
Standard Prolog declarative logic.
```prolog
% reglas.pl
alerta_fraude(TxID, Usuario, "Transaccion masiva") :- 
    transaccion(TxID, Usuario, Monto),
    Monto > 50000.
```

### PyDatalog (`.dl`)
Pure PyDatalog declarative syntax. Prefix facts with `+`.
```text
# datos.dl
+ transaccion("tx_003", "pedro", 65000)
+ cuenta_sospechosa("pedro")
```

---

## Pipeline Construction

Building a pipeline consists of defining your stages, linking their dependencies, and feeding them into the orchestrator. 

> [!WARNING]
> **Circular Dependencies**
> Be cautious when linking `depends_on`. The `Orchestrator` runs a DAG validation before execution and will raise a `RecursionError` if an infinite dependency loop is detected.

---

## Full Example

Below is a complete implementation of a pipeline that extracts data using PyDatalog and passes it to Prolog for fraud evaluation.

```python
from Pipeline import Pipeline, Stage
from PrologWrapper import Query
from Orchestrator import Orchestrator

# 1. Define the upstream Data Extraction Stage
pydatalog_stage = Stage(
    name="extract_data",
    engine="pydatalog",
    rule_file="datos.dl",  # Contains facts about transactions
    queries=[
        Query("transaccion(Tx, Usuario, Monto)"),
        Query("cuenta_sospechosa(Usuario)")
    ],
    outputs=[],
    depends_on=[]
)

# 2. Define the downstream Logic Stage
prolog_stage = Stage(
    name="detect_fraud",
    engine="prolog",
    rule_file="reglas.pl", # Contains the logic for what constitutes fraud
    queries=[
        Query("alerta_fraude(TxID, Usuario, Alerta)"),
    ],
    outputs=[],
    depends_on=[pydatalog_stage] # Waits for PyDatalog and ingests its KnowledgeSet
)

# 3. Assemble the Pipeline
pipeline = Pipeline()
pipeline.add_stage(pydatalog_stage)
pipeline.add_stage(prolog_stage)

# 4. Execute
orchestrator = Orchestrator()
results = orchestrator.run_pipeline(pipeline)

# 5. Review Results
prolog_knowledge = results[1] # Output of the Prolog stage
print(prolog_knowledge.facts["alerta_fraude"])
# Output: [('tx_003', 'pedro', 'Transaccion masiva')]
```
