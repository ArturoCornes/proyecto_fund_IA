# Biblioteca Orquestadora de IA Simbólica (Symbolic AI Orchestrator)

La Biblioteca Orquestadora de IA Simbólica es un framework en Python diseñado para administrar y ejecutar pipelines lógicos multi-motor. Permite a los desarrolladores encadenar bloques de lógica declarativa escritos en diferentes paradigmas (como PyDatalog y Prolog) en un flujo de trabajo unificado y administrado por dependencias.

## Tabla de Contenidos
1. [Conceptos Centrales](#conceptos-centrales)
2. [Intercambio de Datos (`KnowledgeSet`)](#intercambio-de-datos-knowledgeset)
3. [Motores y Wrappers](#motores-y-wrappers)
4. [Escritura de Reglas](#escritura-de-reglas)
5. [Construcción del Pipeline](#construccion-del-pipeline)
6. [Ejemplo Completo](#ejemplo-completo)

---

## Conceptos Centrales

### 1. `Orchestrator`
El `Orchestrator` es el ejecutor central. Toma un `Pipeline` definido, valida el Grafo Acíclico Dirigido (DAG) para asegurar que no existan dependencias circulares, y ejecuta las etapas (stages) en orden topológico.

### 2. `Pipeline`
Un `Pipeline` es una colección de objetos `Stage`. Define el ciclo de vida completo de la lógica de procesamiento de datos.

### 3. `Stage`
Un `Stage` representa un único paso computacional ejecutado por un motor específico.
* **`name`**: Identificador único de la etapa.
* **`engine`**: El motor lógico a utilizar (ej., `"prolog"`, `"pydatalog"`).
* **`rule_file`**: El archivo que contiene las reglas lógicas (ej., `.pl` para Prolog, `.dl` para PyDatalog).
* **`queries`**: Una lista de objetos `Query` para ejecutar contra el motor una vez que las reglas y los datos están cargados.
* **`outputs`**: (Opcional) Objetos `Fact` (hechos) pre-configurados que se inyectan en la etapa al iniciar.
* **`depends_on`**: Una lista de objetos `Stage` de los que depende y que deben ejecutarse primero. Los datos de salida de las dependencias se combinan automáticamente y se inyectan en esta etapa.

---

## Intercambio de Datos (`KnowledgeSet`)

El Orchestrator utiliza un Objeto de Transferencia de Datos (DTO) estándar llamado `KnowledgeSet`. Esto asegura que los datos puedan fluir sin problemas entre motores heterogéneos (como de PyDatalog a Prolog) sin requerir un mapeo de datos manual.

Un `KnowledgeSet` simplemente almacena hechos como un diccionario que mapea un nombre de predicado a una lista de tuplas de átomos:
```python
{
    "transaccion": [
        ("tx_001", "juan", 15000),
        ("tx_002", "maria", 500)
    ]
}
```

Cada vez que una etapa ejecuta una consulta, devuelve sus resultados envueltos en un `KnowledgeSet`. El Orchestrator recoge esto y lo inyecta automáticamente en cualquier etapa dependiente.

---

## Motores y Wrappers

### Prolog (`PrologWrapper`)
Envuelve el motor de SWI-Prolog (vía `pyswip`).
* Evalúa archivos `.pl` estándar.
* Serializa y decodifica automáticamente las cadenas de bytes (byte-strings) devueltas por PySWIP a cadenas nativas de Python.
* Inyecta automáticamente los registros entrantes del `KnowledgeSet` como objetos `Fact` de Prolog.

### PyDatalog (`PyDatalogWrapper`)
Envuelve el motor lógico `pyDatalog`.
* Analiza dinámicamente archivos de texto puro de lógica datalog (`.dl`), registrando variables de términos globalmente de forma automática.
* Mapea los resultados en forma de tuplas de `pyDatalog.ask()` limpiamente hacia los DTOs `KnowledgeSet` salientes.

---

## Escritura de Reglas

### Prolog (`.pl`)
Lógica declarativa estándar de Prolog.
```prolog
% reglas.pl
alerta_fraude(TxID, Usuario, "Transaccion masiva") :- 
    transaccion(TxID, Usuario, Monto),
    Monto > 50000.
```

### PyDatalog (`.dl`)
Sintaxis declarativa pura de PyDatalog. Los hechos se prefijan con `+`.
```text
# datos.dl
+ transaccion("tx_003", "pedro", 65000)
+ cuenta_sospechosa("pedro")
```

---

## Construcción del Pipeline

Construir un pipeline consiste en definir sus etapas, enlazar sus dependencias e introducirlas en el orquestador.

> [!WARNING]
> **Dependencias Circulares**
> Tenga cuidado al enlazar `depends_on`. El `Orchestrator` ejecuta una validación DAG antes de la ejecución y lanzará un `RecursionError` si se detecta un bucle infinito de dependencias.

---

## Ejemplo Completo

A continuación se muestra una implementación completa de un pipeline que extrae datos usando PyDatalog y los pasa a Prolog para la evaluación de fraude.

```python
from Pipeline import Pipeline, Stage
from PrologWrapper import Query
from Orchestrator import Orchestrator

# 1. Definir la etapa inicial de Extracción de Datos
pydatalog_stage = Stage(
    name="extract_data",
    engine="pydatalog",
    rule_file="datos.dl",  # Contiene los hechos sobre transacciones
    queries=[
        Query("transaccion(Tx, Usuario, Monto)"),
        Query("cuenta_sospechosa(Usuario)")
    ],
    outputs=[],
    depends_on=[]
)

# 2. Definir la etapa posterior de Lógica
prolog_stage = Stage(
    name="detect_fraud",
    engine="prolog",
    rule_file="reglas.pl", # Contiene la lógica para determinar fraude
    queries=[
        Query("alerta_fraude(TxID, Usuario, Alerta)"),
    ],
    outputs=[],
    depends_on=[pydatalog_stage] # Espera a PyDatalog e ingiere su KnowledgeSet
)

# 3. Ensamblar el Pipeline
pipeline = Pipeline()
pipeline.add_stage(pydatalog_stage)
pipeline.add_stage(prolog_stage)

# 4. Ejecutar
orchestrator = Orchestrator()
results = orchestrator.run_pipeline(pipeline)

# 5. Revisar los Resultados
prolog_knowledge = results[1] # Salida de la etapa de Prolog
print(prolog_knowledge.facts["alerta_fraude"])
# Salida: [('tx_003', 'pedro', 'Transaccion masiva')]
```
