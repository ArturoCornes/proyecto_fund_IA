"""
etl.py
======
Curso IA y FL 2026 — Universidad de Montevideo
Proyecto 4: UY-CompraTracker

Propósito:
    Cargar el dataset de compras públicas (ya reducido por preparar_dataset.py),
    limpiarlo, normalizarlo y almacenarlo en una base SQLite lista para ser
    consultada por el módulo pyDatalog.

AVISO: Este script se distribuye "tal cual" (as-is), sin garantías de
ningún tipo. Fue preparado con fines exclusivamente educativos para el
Curso de IA y FL 2026 — Universidad de Montevideo.

Uso:
    python etl.py --input compras_procesadas.csv --db compras.db

Salida:
    - compras.db         : base SQLite con la tabla `compras` cargada
    - hechos_datalog.py  : hechos Python listos para importar en pyDatalog
"""

import argparse
import sqlite3
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime


# =============================================================================
# SECCIÓN 1 — SCHEMA DE LA BASE DE DATOS
# Los estudiantes pueden modificar o extender este schema según sus necesidades.
# =============================================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS compras (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    organismo           TEXT,
    proveedor           TEXT,
    monto               REAL,
    fecha_licitacion    TEXT,     -- formato ISO: YYYY-MM-DD
    fecha_adjudicacion  TEXT,     -- formato ISO: YYYY-MM-DD
    objeto_licitacion   TEXT,
    estado              TEXT,
    dias_adjudicacion   INTEGER   -- campo derivado: días entre licitación y adjudicación
);

CREATE INDEX IF NOT EXISTS idx_organismo ON compras(organismo);
CREATE INDEX IF NOT EXISTS idx_proveedor  ON compras(proveedor);
CREATE INDEX IF NOT EXISTS idx_estado     ON compras(estado);
"""


def crear_base(ruta_db: str) -> sqlite3.Connection:
    """
    Crea la base SQLite y el schema de la tabla `compras`.

    Parámetros
    ----------
    ruta_db : str
        Ruta al archivo .db (se crea si no existe).

    Retorna
    -------
    sqlite3.Connection
        Conexión abierta a la base.

    Nota para estudiantes
    ---------------------
    Esta función ya está implementada como punto de partida.
    Pueden agregar tablas adicionales (por ejemplo, `alertas` o `organismos`)
    siguiendo el mismo patrón: definir el CREATE TABLE en SCHEMA y llamar
    conn.executescript() con el nuevo bloque.
    """
    conn = sqlite3.connect(ruta_db)
    conn.executescript(SCHEMA)
    conn.commit()
    print(f"[OK] Base de datos creada/verificada: {ruta_db}")
    return conn


# =============================================================================
# SECCIÓN 2 — CARGA Y LIMPIEZA
# Los estudiantes deben completar las funciones marcadas con TODO.
# =============================================================================

def cargar_csv(ruta_csv: str) -> pd.DataFrame:
    """Carga el CSV de compras y retorna un DataFrame."""
    if not os.path.exists(ruta_csv):
        print(f"[ERROR] No se encuentra el archivo: {ruta_csv}")
        sys.exit(1)

    df = pd.read_csv(ruta_csv, encoding="utf-8", low_memory=False)
    print(f"[OK] CSV cargado: {len(df):,} filas, {len(df.columns)} columnas")
    return df


def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y normaliza el DataFrame.

    Transformaciones ya implementadas:
        - Elimina filas sin organismo o proveedor.
        - Normaliza texto a mayúsculas sin espacios dobles.
        - Convierte monto a float.
        - Asegura que dias_adjudicacion sea entero.

    TODO para estudiantes:
        - Agregar filtros adicionales según lo que observen en sus datos.
        - Por ejemplo: eliminar registros con estado = 'CANCELADA' si no
          son relevantes para su análisis, o imputar montos faltantes.
    """
    filas_inicio = len(df)

    # Eliminar filas sin clave
    df = df.dropna(subset=["organismo", "proveedor"])

    # Normalizar texto
    for col in ["organismo", "proveedor", "objeto_licitacion", "estado"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.strip()
                .str.upper()
                .str.replace(r"\s+", " ", regex=True)
            )

    # Monto a numérico
    if "monto" in df.columns:
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce")

    # dias_adjudicacion a entero (NaN → -1 como centinela)
    if "dias_adjudicacion" in df.columns:
        df["dias_adjudicacion"] = (
            pd.to_numeric(df["dias_adjudicacion"], errors="coerce")
            .fillna(-1)
            .astype(int)
        )

    filas_fin = len(df)
    print(f"[OK] Limpieza: {filas_inicio - filas_fin} filas eliminadas, "
          f"{filas_fin:,} filas restantes")

    # TODO: agregar aquí sus propias transformaciones
    # Ejemplo:
    # df = df[df["estado"] != "CANCELADA"]

    return df.reset_index(drop=True)


# =============================================================================
# SECCIÓN 3 — INSERCIÓN EN SQLITE
# =============================================================================

def insertar_en_db(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """
    Inserta el DataFrame en la tabla `compras` de SQLite.

    Usa INSERT OR IGNORE para evitar duplicados si se corre más de una vez.
    """
    columnas = [
        "organismo", "proveedor", "monto",
        "fecha_licitacion", "fecha_adjudicacion",
        "objeto_licitacion", "estado", "dias_adjudicacion"
    ]

    # Solo insertar columnas que existan en el DataFrame
    columnas_presentes = [c for c in columnas if c in df.columns]
    df_insertar = df[columnas_presentes].where(pd.notnull(df[columnas_presentes]), None)

    registros = df_insertar.to_dict(orient="records")

    placeholders = ", ".join(["?" for _ in columnas_presentes])
    cols_str = ", ".join(columnas_presentes)
    sql = f"INSERT INTO compras ({cols_str}) VALUES ({placeholders})"

    cursor = conn.cursor()
    cursor.executemany(sql, [tuple(r.values()) for r in registros])
    conn.commit()
    print(f"[OK] {cursor.rowcount:,} registros insertados en la tabla `compras`")


# =============================================================================
# SECCIÓN 4 — EXPORTAR HECHOS PARA PYDATALOG
# Los estudiantes deben completar la función exportar_hechos().
# =============================================================================

def exportar_hechos(conn: sqlite3.Connection, ruta_salida: str) -> None:
    """
    Genera un archivo hechos_datalog.py con los hechos base para pyDatalog.

    Hechos ya generados (listos para usar):
        - compra(id, organismo, proveedor, monto, dias_adjudicacion)

    TODO para estudiantes:
        Agregar los hechos adicionales que necesiten sus reglas.
        Por ejemplo, si una regla necesita saber el estado de la licitación:

            + estado_licitacion[id] = estado

        Sigan el mismo patrón que los hechos ya generados.

    Nota: pyDatalog carga estos hechos haciendo `from hechos_datalog import *`
    al inicio de analisis_pydatalog.py.
    """
    cursor = conn.cursor()

    # Consulta base — pueden agregar columnas según sus necesidades
    cursor.execute("""
        SELECT id, organismo, proveedor, monto, dias_adjudicacion, estado
        FROM compras
        ORDER BY id
    """)
    filas = cursor.fetchall()

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write('"""\n')
        f.write("hechos_datalog.py\n")
        f.write("Generado automáticamente por etl.py\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write('"""\n\n')
        f.write("from pyDatalog import pyDatalog\n\n")
        f.write("pyDatalog.create_terms(\n")
        f.write("    'compra, organismo_de, proveedor_de, monto_de,\n")
        f.write("     dias_adj_de, estado_de'\n")
        f.write(")\n\n")
        f.write("def cargar_hechos():\n")
        f.write('    """Carga todos los hechos en el motor pyDatalog."""\n\n')

        for fila in filas:
            id_, org, prov, monto, dias, estado = fila
            monto_str = f"{monto:.2f}" if monto is not None else "None"
            dias_str  = str(dias) if dias is not None else "None"
            org_esc   = str(org).replace("'", "\\'")
            prov_esc  = str(prov).replace("'", "\\'")
            est_esc   = str(estado).replace("'", "\\'")

            f.write(f"    + compra[{id_}]\n")
            f.write(f"    + organismo_de[{id_}] == '{org_esc}'\n")
            f.write(f"    + proveedor_de[{id_}]  == '{prov_esc}'\n")
            f.write(f"    + monto_de[{id_}]       == {monto_str}\n")
            f.write(f"    + dias_adj_de[{id_}]    == {dias_str}\n")
            f.write(f"    + estado_de[{id_}]      == '{est_esc}'\n")
            f.write("\n")

        f.write("    # TODO: agregar aquí sus hechos adicionales\n")
        f.write("\n")

    print(f"[OK] Hechos exportados: {ruta_salida} ({len(filas):,} registros)")


# =============================================================================
# SECCIÓN 5 — CONSULTAS DE VERIFICACIÓN
# Útiles para comprobar que la carga fue correcta antes de arrancar pyDatalog.
# =============================================================================

def verificar_carga(conn: sqlite3.Connection) -> None:
    """Imprime un resumen de la base cargada."""
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM compras").fetchone()[0]
    organismos = cur.execute("SELECT COUNT(DISTINCT organismo) FROM compras").fetchone()[0]
    proveedores = cur.execute("SELECT COUNT(DISTINCT proveedor) FROM compras").fetchone()[0]

    print("\n" + "="*50)
    print("VERIFICACIÓN DE CARGA")
    print("="*50)
    print(f"  Total de registros   : {total:,}")
    print(f"  Organismos únicos    : {organismos}")
    print(f"  Proveedores únicos   : {proveedores}")

    print("\n  Top 5 organismos por cantidad de compras:")
    rows = cur.execute("""
        SELECT organismo, COUNT(*) as n
        FROM compras
        GROUP BY organismo
        ORDER BY n DESC
        LIMIT 5
    """).fetchall()
    for org, n in rows:
        print(f"    {org:40s}: {n:,}")

    print("\n  Top 5 proveedores por monto total adjudicado:")
    rows = cur.execute("""
        SELECT proveedor, SUM(monto) as total
        FROM compras
        WHERE monto IS NOT NULL
        GROUP BY proveedor
        ORDER BY total DESC
        LIMIT 5
    """).fetchall()
    for prov, total in rows:
        print(f"    {prov:40s}: {total:,.0f}")

    print("\n  Distribución por estado:")
    rows = cur.execute("""
        SELECT estado, COUNT(*) as n
        FROM compras
        GROUP BY estado
        ORDER BY n DESC
    """).fetchall()
    for estado, n in rows:
        print(f"    {estado:20s}: {n:,}")

    print("="*50)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ETL para Proyecto 4 UY-CompraTracker — IA y FL 2026"
    )
    parser.add_argument(
        "--input", default="compras_procesadas.csv",
        help="CSV de entrada (default: compras_procesadas.csv)"
    )
    parser.add_argument(
        "--db", default="compras.db",
        help="Archivo SQLite de salida (default: compras.db)"
    )
    parser.add_argument(
        "--hechos", default="hechos_datalog.py",
        help="Archivo de hechos pyDatalog (default: hechos_datalog.py)"
    )
    parser.add_argument(
        "--sin-hechos", action="store_true",
        help="Omitir la exportación de hechos pyDatalog"
    )
    args = parser.parse_args()

    print("="*50)
    print("ETL — UY-CompraTracker")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # Pipeline ETL
    df       = cargar_csv(args.input)
    df       = limpiar_datos(df)
    conn     = crear_base(args.db)
    insertar_en_db(df, conn)

    if not args.sin_hechos:
        exportar_hechos(conn, args.hechos)

    verificar_carga(conn)

    conn.close()
    print(f"\n✓ ETL completado.")
    print(f"  Base SQLite  : {args.db}")
    if not args.sin_hechos:
        print(f"  Hechos       : {args.hechos}")


if __name__ == "__main__":
    main()
