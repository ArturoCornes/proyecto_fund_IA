from pyDatalog import pyDatalog

# Los terminos deben declararse a nivel de modulo. Si se crean dentro de una
# funcion, pyDatalog no siempre puede exponerlos como variables locales.
pyDatalog.create_terms('Tx, Usuario, Monto, transaccion_db, cuenta_riesgo_db, X, Y, Z')

def extraer_datos_para_prolog() -> dict:
    """
    Simula una base de datos y extrae los registros en formato de tuplas.
    """
    pyDatalog.clear()
    # 1. Base de datos simulada (Hechos en Datalog)
    + transaccion_db("tx_001", "juan", 15000)   # Fraude (Juan es sospechoso y > 10k)
    + transaccion_db("tx_002", "maria", 500)    # Limpio
    + transaccion_db("tx_003", "pedro", 65000)  # Fraude (Masiva)
    + transaccion_db("tx_004", "juan", 200)     # Vigilancia (Juan es sospechoso)
    + transaccion_db("tx_005", "lucia", 9000)   # Limpio

    + cuenta_riesgo_db("juan")
    + cuenta_riesgo_db("carlos")

    # 2. Consultas Datalog (Filtramos y preparamos los datos)
    # Extraemos todas las transacciones y cuentas.
    # El atributo .data de Datalog devuelve exactamente List[Tuple], ¡perfecto para el orquestador!
    print("ran")
    return {
        "transaccion": transaccion_db(X, Y, Z).data,
        "cuenta_sospechosa": cuenta_riesgo_db(X).data
    }
