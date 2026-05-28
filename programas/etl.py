"""
etl.py
======
Curso IA y FL 2026 - Universidad de Montevideo
Proyecto 4: UY-CompraTracker

Carga el CSV producido por preparar_dataset.py, valida/normaliza los datos y
los almacena en SQLite para ser consultados por pyDatalog.
"""

import argparse
from datetime import datetime
import os
import sqlite3
import sys

import pandas as pd


COLUMNAS_DB = [
    "ocid",
    "id_licitacion",
    "id_adjudicacion",
    "organismo",
    "proveedor",
    "monto",
    "moneda",
    "fecha_licitacion",
    "fecha_adjudicacion",
    "objeto_licitacion",
    "estado",
    "dias_adjudicacion",
]


COLUMNAS_ADICIONALES = {
    "ocid": "TEXT",
    "id_licitacion": "TEXT",
    "id_adjudicacion": "TEXT",
    "moneda": "TEXT",
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS compras (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ocid                TEXT,
    id_licitacion       TEXT,
    id_adjudicacion     TEXT,
    organismo           TEXT,
    proveedor           TEXT,
    monto               REAL,
    moneda              TEXT,
    fecha_licitacion    TEXT,     -- formato ISO: YYYY-MM-DD
    fecha_adjudicacion  TEXT,     -- formato ISO: YYYY-MM-DD
    objeto_licitacion   TEXT,
    estado              TEXT,
    dias_adjudicacion   INTEGER   -- dias entre licitacion y adjudicacion
);
"""


INDICES = """
CREATE INDEX IF NOT EXISTS idx_organismo ON compras(organismo);
CREATE INDEX IF NOT EXISTS idx_proveedor  ON compras(proveedor);
CREATE INDEX IF NOT EXISTS idx_estado     ON compras(estado);
CREATE INDEX IF NOT EXISTS idx_ocid       ON compras(ocid);
"""


def crear_base(ruta_db: str) -> sqlite3.Connection:
    """Crea/verifica la base SQLite y actualiza columnas nuevas si hace falta."""
    conn = sqlite3.connect(ruta_db)
    conn.executescript(SCHEMA)
    sincronizar_schema(conn)
    conn.executescript(INDICES)
    conn.commit()
    print(f"[OK] Base de datos creada/verificada: {ruta_db}")
    return conn


def sincronizar_schema(conn: sqlite3.Connection) -> None:
    """Agrega columnas nuevas cuando la DB ya existia con el schema anterior."""
    existentes = {
        fila[1]
        for fila in conn.execute("PRAGMA table_info(compras)").fetchall()
    }

    for columna, tipo in COLUMNAS_ADICIONALES.items():
        if columna not in existentes:
            conn.execute(f"ALTER TABLE compras ADD COLUMN {columna} {tipo}")


def cargar_csv(ruta_csv: str) -> pd.DataFrame:
    """Carga el CSV de compras y retorna un DataFrame."""
    if not os.path.exists(ruta_csv):
        print(f"[ERROR] No se encuentra el archivo: {ruta_csv}")
        sys.exit(1)

    df = pd.read_csv(ruta_csv, encoding="utf-8", low_memory=False)
    print(f"[OK] CSV cargado: {len(df):,} filas, {len(df.columns)} columnas")
    return df


def normalizar_texto(serie: pd.Series) -> pd.Series:
    return (
        serie.astype("string")
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
        .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA})
    )


def normalizar_fecha(serie: pd.Series) -> pd.Series:
    fecha = pd.to_datetime(serie, errors="coerce", utc=True)
    fecha = fecha.dt.tz_convert(None)
    return fecha.dt.strftime("%Y-%m-%d")


def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y normaliza el DataFrame.

    El CSV de entrada ya debe estar a nivel de adjudicacion: una fila por
    proveedor adjudicado, con datos de licitacion fusionados por `ocid` cuando
    esten disponibles.
    """
    filas_inicio = len(df)

    requeridas = {"organismo", "proveedor"}
    faltantes = sorted(requeridas - set(df.columns))

    if faltantes:
        print(f"[ERROR] Faltan columnas requeridas: {faltantes}")
        sys.exit(1)

    # Quitar filas que no representan una adjudicacion usable.
    df = df.dropna(subset=["organismo", "proveedor"]).copy()

    for col in [
        "organismo",
        "proveedor",
        "objeto_licitacion",
        "estado",
        "moneda",
    ]:
        if col in df.columns:
            df[col] = normalizar_texto(df[col])

    for col in ["ocid", "id_licitacion", "id_adjudicacion"]:
        if col in df.columns:
            df[col] = (
                df[col].astype("string")
                .str.strip()
                .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA})
            )

    if "monto" in df.columns:
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce")

    for col in ["fecha_licitacion", "fecha_adjudicacion"]:
        if col in df.columns:
            df[col] = normalizar_fecha(df[col])

    if {"fecha_licitacion", "fecha_adjudicacion"} <= set(df.columns):
        fecha_lic = pd.to_datetime(df["fecha_licitacion"], errors="coerce")
        fecha_adj = pd.to_datetime(df["fecha_adjudicacion"], errors="coerce")
        dias = (fecha_adj - fecha_lic).dt.days
        dias[dias < 0] = pd.NA

        if "dias_adjudicacion" in df.columns:
            dias_originales = pd.to_numeric(
                df["dias_adjudicacion"],
                errors="coerce",
            )
            dias = dias.where(dias.notna(), dias_originales)

        df["dias_adjudicacion"] = pd.to_numeric(
            dias,
            errors="coerce",
        ).astype("Int64")
    elif "dias_adjudicacion" in df.columns:
        df["dias_adjudicacion"] = pd.to_numeric(
            df["dias_adjudicacion"],
            errors="coerce",
        ).astype("Int64")

    filas_fin = len(df)
    print(
        f"[OK] Limpieza: {filas_inicio - filas_fin} filas eliminadas, "
        f"{filas_fin:,} filas restantes"
    )

    return df.reset_index(drop=True)


def insertar_en_db(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """Refresca la tabla `compras` con los registros del DataFrame."""
    columnas_presentes = [c for c in COLUMNAS_DB if c in df.columns]
    df_insertar = (
        df[columnas_presentes]
        .astype(object)
        .where(pd.notnull(df[columnas_presentes]), None)
    )

    registros = df_insertar.to_dict(orient="records")

    placeholders = ", ".join(["?" for _ in columnas_presentes])
    cols_str = ", ".join(columnas_presentes)
    sql = f"INSERT INTO compras ({cols_str}) VALUES ({placeholders})"

    cursor = conn.cursor()
    cursor.execute("DELETE FROM compras")
    cursor.executemany(sql, [tuple(r[c] for c in columnas_presentes) for r in registros])
    conn.commit()
    print(f"[OK] {cursor.rowcount:,} registros insertados en la tabla `compras`")


def literal_texto(valor):
    if valor is None:
        return "None"
    texto = str(valor).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{texto}'"


def literal_numero(valor):
    if valor is None:
        return "None"
    return f"{valor:.2f}" if isinstance(valor, float) else str(valor)


def exportar_hechos(conn: sqlite3.Connection, ruta_salida: str) -> None:
    """Genera un archivo hechos_datalog.py con hechos base para pyDatalog."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id, ocid, id_licitacion, id_adjudicacion,
            organismo, proveedor, monto, moneda,
            fecha_licitacion, fecha_adjudicacion,
            dias_adjudicacion, estado
        FROM compras
        ORDER BY id
    """)
    filas = cursor.fetchall()

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write('"""\n')
        f.write("hechos_datalog.py\n")
        f.write("Generado automaticamente por etl.py\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write('"""\n\n')
        f.write("from pyDatalog import pyDatalog\n\n")
        f.write(
            "pyDatalog.create_terms('"
            "compra, ocid_de, licitacion_de, adjudicacion_de, "
            "organismo_de, proveedor_de, monto_de, moneda_de, "
            "fecha_licitacion_de, fecha_adjudicacion_de, "
            "dias_adj_de, estado_de"
            "')\n\n"
        )
        f.write("def cargar_hechos():\n")
        f.write('    """Carga todos los hechos en el motor pyDatalog."""\n\n')

        for fila in filas:
            (
                id_,
                ocid,
                id_lic,
                id_adj,
                org,
                prov,
                monto,
                moneda,
                fecha_lic,
                fecha_adj,
                dias,
                estado,
            ) = fila

            f.write(f"    +(compra[{id_}])\n")
            f.write(f"    + (ocid_de[{id_}]                 == {literal_texto(ocid)})\n")
            f.write(f"    + (licitacion_de[{id_}]           == {literal_texto(id_lic)})\n")
            f.write(f"    + (adjudicacion_de[{id_}]         == {literal_texto(id_adj)})\n")
            f.write(f"    + (organismo_de[{id_}]            == {literal_texto(org)})\n")
            f.write(f"    + (proveedor_de[{id_}]            == {literal_texto(prov)})\n")
            f.write(f"    + (monto_de[{id_}]                == {literal_numero(monto)})\n")
            f.write(f"    + (moneda_de[{id_}]               == {literal_texto(moneda)})\n")
            f.write(f"    + (fecha_licitacion_de[{id_}]     == {literal_texto(fecha_lic)})\n")
            f.write(f"    + (fecha_adjudicacion_de[{id_}]   == {literal_texto(fecha_adj)})\n")
            f.write(f"    + (dias_adj_de[{id_}]             == {literal_numero(dias)})\n")
            f.write(f"    + (estado_de[{id_}]               == {literal_texto(estado)})\n")
            f.write("\n")

    print(f"[OK] Hechos exportados: {ruta_salida} ({len(filas):,} registros)")


def verificar_carga(conn: sqlite3.Connection) -> None:
    """Imprime un resumen de la base cargada."""
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM compras").fetchone()[0]
    organismos = cur.execute("SELECT COUNT(DISTINCT organismo) FROM compras").fetchone()[0]
    proveedores = cur.execute("SELECT COUNT(DISTINCT proveedor) FROM compras").fetchone()[0]
    fusionadas = cur.execute("""
        SELECT COUNT(*)
        FROM compras
        WHERE fecha_licitacion IS NOT NULL
          AND fecha_adjudicacion IS NOT NULL
    """).fetchone()[0]
    con_dias = cur.execute("""
        SELECT COUNT(*)
        FROM compras
        WHERE dias_adjudicacion IS NOT NULL
    """).fetchone()[0]

    print("\n" + "=" * 50)
    print("VERIFICACION DE CARGA")
    print("=" * 50)
    print(f"  Total de registros      : {total:,}")
    print(f"  Organismos unicos       : {organismos}")
    print(f"  Proveedores unicos      : {proveedores}")
    print(f"  Filas con ambas fechas  : {fusionadas:,}")
    print(f"  Filas con dias calculado: {con_dias:,}")

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

    print("\n  Distribucion por estado:")
    rows = cur.execute("""
        SELECT estado, COUNT(*) as n
        FROM compras
        GROUP BY estado
        ORDER BY n DESC
    """).fetchall()
    for estado, n in rows:
        etiqueta = estado if estado is not None else "SIN ESTADO"
        print(f"    {etiqueta:20s}: {n:,}")

    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="ETL para Proyecto 4 UY-CompraTracker - IA y FL 2026"
    )
    parser.add_argument(
        "--input",
        default="compras_procesadas.csv",
        help="CSV de entrada (default: compras_procesadas.csv)",
    )
    parser.add_argument(
        "--db",
        default="compras.db",
        help="Archivo SQLite de salida (default: compras.db)",
    )
    parser.add_argument(
        "--hechos",
        default="hechos_datalog.py",
        help="Archivo de hechos pyDatalog (default: hechos_datalog.py)",
    )
    parser.add_argument(
        "--sin-hechos",
        action="store_true",
        help="Omitir la exportacion de hechos pyDatalog",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("ETL - UY-CompraTracker")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    df = cargar_csv(args.input)
    df = limpiar_datos(df)
    conn = crear_base(args.db)
    insertar_en_db(df, conn)

    if not args.sin_hechos:
        exportar_hechos(conn, args.hechos)

    verificar_carga(conn)

    conn.close()
    print("\nOK - ETL completado.")
    print(f"  Base SQLite  : {args.db}")
    if not args.sin_hechos:
        print(f"  Hechos       : {args.hechos}")


if __name__ == "__main__":
    main()
