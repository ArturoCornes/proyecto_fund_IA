"""
preparar_dataset.py
===================
Curso IA y FL 2026 — Universidad de Montevideo
Proyecto 4: UY-CompraTracker

Versión modificada para leer archivos JSON OCDS
de compras públicas uruguayas.
"""

import argparse
import sys
import os
import glob
import json
import pandas as pd
import numpy as np
from datetime import datetime


COLUMNAS_ESPERADAS = [
    "organismo",
    "proveedor",
    "monto",
    "fecha_licitacion",
    "fecha_adjudicacion",
    "objeto_licitacion",
    "estado",
]

ALIASES = {
    "organismo":          ["organismo", "organism", "entidad", "unidad_ejecutora"],
    "proveedor":          ["proveedor", "empresa", "razonsocial", "razon_social"],
    "monto":              ["monto", "importe", "monto_adjudicado", "precio"],
    "fecha_licitacion":   ["fecha_licitacion", "fecha_publicacion", "fecha_apertura"],
    "fecha_adjudicacion": ["fecha_adjudicacion", "fecha_adj", "adjudicacion"],
    "objeto_licitacion":  ["objeto_licitacion", "objeto", "descripcion", "detalle"],
    "estado":             ["estado", "status", "estado_licitacion"],
}


def log(msg, archivo=None):
    print(msg)
    if archivo:
        archivo.write(msg + "\n")


def cargar_jsons_ocds(carpeta, reporte):
    """
    Lee archivos OCDS l-*.json y a-*.json
    y construye un DataFrame unificado.
    """

    filas = []

    archivos = glob.glob(os.path.join(carpeta, "*.json"))

    log(f"  JSON encontrados: {len(archivos)}", reporte)

    for archivo in archivos:

        log(f"    Procesando: {os.path.basename(archivo)}", reporte)

        try:
            with open(archivo, encoding="utf-8") as f:
                data = json.load(f)

        except Exception as e:
            log(f"    [ERROR] No se pudo leer {archivo}: {e}", reporte)
            continue

        releases = data.get("releases", [])

        for release in releases:

            tag = release.get("tag", [])

            # =========================================================
            # LICITACIONES
            # =========================================================
            if "tender" in tag:

                tender = release.get("tender", {})

                filas.append({
                    "organismo":
                        release.get("buyer", {}).get("name"),

                    "proveedor":
                        np.nan,

                    "monto":
                        np.nan,

                    "fecha_licitacion":
                        tender.get("tenderPeriod", {})
                              .get("startDate"),

                    "fecha_adjudicacion":
                        np.nan,

                    "objeto_licitacion":
                        tender.get("title"),

                    "estado":
                        np.nan
                })

            # =========================================================
            # ADJUDICACIONES
            # =========================================================
            if "award" in tag or "awards" in release:

                awards = release.get("awards", [])

                for award in awards:

                    proveedor = np.nan

                    suppliers = award.get("suppliers", [])

                    if suppliers:
                        proveedor = suppliers[0].get("name")

                    # calcular monto total
                    monto_total = 0

                    for item in award.get("items", []):

                        cantidad = item.get("quantity", 0)

                        precio = (
                            item.get("unit", {})
                                .get("value", {})
                                .get("amount", 0)
                        )

                        monto_total += cantidad * precio

                    filas.append({
                        "organismo":
                            release.get("buyer", {}).get("name"),

                        "proveedor":
                            proveedor,

                        "monto":
                            monto_total if monto_total > 0 else np.nan,

                        "fecha_licitacion":
                            np.nan,

                        "fecha_adjudicacion":
                            award.get("date"),

                        "objeto_licitacion":
                            award.get("title"),

                        "estado":
                            award.get("status")
                    })

    df = pd.DataFrame(filas)

    return df


def limpiar_montos(serie, reporte):
    original_nulls = serie.isna().sum()

    limpia = (
        serie.astype(str)
        .str.replace(r"[$UYusd\s]", "", regex=True)
        .str.replace(r"\.", "", regex=True)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )

    limpia = pd.to_numeric(limpia, errors="coerce")

    nuevos_nulls = limpia.isna().sum() - original_nulls

    if nuevos_nulls > 0:
        log(f"  [LIMPIEZA] Montos no convertibles: {nuevos_nulls}", reporte)

    negativos = (limpia <= 0).sum()

    limpia[limpia <= 0] = np.nan

    if negativos > 0:
        log(f"  [LIMPIEZA] Montos negativos o cero: {negativos}", reporte)

    return limpia


def limpiar_fechas(serie, nombre_col, reporte):

    resultado = pd.to_datetime(serie, errors="coerce")

    log(
        f"  [FECHAS] '{nombre_col}': "
        f"{resultado.notna().sum()} válidas.",
        reporte
    )

    return resultado


def normalizar_texto(serie):

    return (
        serie.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
        .replace("NAN", np.nan)
        .replace("NONE", np.nan)
    )


def samplear_representativo(df, n, reporte):

    n_organismos = int(n * 0.60)
    n_proveedores = int(n * 0.25)
    n_random = n - n_organismos - n_proveedores

    log(f"\n  Estrategia de muestreo:", reporte)
    log(f"    - {n_organismos} por organismo", reporte)
    log(f"    - {n_proveedores} por proveedor", reporte)
    log(f"    - {n_random} aleatorios", reporte)

    indices = set()

    try:
        muestra_org = (
            df.groupby("organismo", group_keys=False)
            .apply(lambda g: g.sample(
                min(len(g), max(1, int(n_organismos * len(g) / len(df)))),
                random_state=42
            ))
        )

        indices.update(muestra_org.index.tolist())

    except Exception as e:
        log(f"  [AVISO] Estrato organismo falló: {e}", reporte)

    restante = df[~df.index.isin(indices)]

    if len(restante) > 0:

        try:
            muestra_prov = (
                restante.groupby("proveedor", group_keys=False)
                .apply(lambda g: g.sample(
                    min(len(g), max(1, int(n_proveedores * len(g) / len(restante)))),
                    random_state=42
                ))
            )

            indices.update(muestra_prov.index.tolist())

        except Exception as e:
            log(f"  [AVISO] Estrato proveedor falló: {e}", reporte)

    restante2 = df[~df.index.isin(indices)]

    if len(restante2) > 0:

        n_ale = min(n_random, len(restante2))

        muestra_ale = restante2.sample(n_ale, random_state=42)

        indices.update(muestra_ale.index.tolist())

    resultado = df.loc[list(indices)].sample(frac=1, random_state=42)

    return resultado.head(n)


def generar_reporte(df_original, df_final, reporte):

    log("\n" + "=" * 60, reporte)
    log("RESUMEN FINAL", reporte)
    log("=" * 60, reporte)

    log(f"  Registros originales : {len(df_original):,}", reporte)
    log(f"  Registros en salida  : {len(df_final):,}", reporte)

    log(f"\n  Nulos por columna:", reporte)

    for col in df_final.columns:

        n = df_final[col].isna().sum()

        pct = 100 * n / len(df_final)

        log(f"    {col:25s}: {n:5d} ({pct:.1f}%)", reporte)


def main():

    parser = argparse.ArgumentParser(
        description="Prepara dataset OCDS de compras públicas"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Carpeta con archivos JSON OCDS"
    )

    parser.add_argument(
        "--output",
        default="compras_procesadas.csv"
    )

    parser.add_argument(
        "--n",
        type=int,
        default=5000
    )

    parser.add_argument(
        "--reporte",
        default="reporte_preparacion.txt"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: no se encuentra '{args.input}'")
        sys.exit(1)

    with open(args.reporte, "w", encoding="utf-8") as rep:

        log("=" * 60, rep)
        log("PREPARACIÓN DATASET OCDS", rep)
        log("=" * 60, rep)

        # CARGA JSON
        log("\n[1] Cargando JSON OCDS...", rep)

        df = cargar_jsons_ocds(args.input, rep)

        log(f"  Filas cargadas : {len(df):,}", rep)
        log(f"  Columnas       : {list(df.columns)}", rep)

        df_original = df.copy()

        # LIMPIEZA
        log("\n[2] Limpiando datos...", rep)

        for col in ["organismo", "proveedor", "objeto_licitacion", "estado"]:
            df[col] = normalizar_texto(df[col])

        df["monto"] = limpiar_montos(df["monto"], rep)

        df["fecha_licitacion"] = limpiar_fechas(
            df["fecha_licitacion"],
            "fecha_licitacion",
            rep
        )

        df["fecha_adjudicacion"] = limpiar_fechas(
            df["fecha_adjudicacion"],
            "fecha_adjudicacion",
            rep
        )

        df["dias_adjudicacion"] = (
            df["fecha_adjudicacion"] - df["fecha_licitacion"]
        ).dt.days

        df.loc[df["dias_adjudicacion"] < 0, "dias_adjudicacion"] = np.nan

        log(f"  Registros tras limpieza: {len(df):,}", rep)

        # MUESTREO
        log("\n[3] Generando muestra...", rep)

        if len(df) <= args.n:
            df_final = df
        else:
            df_final = samplear_representativo(df, args.n, rep)

        df_final = df_final.copy()

        df_final["fecha_licitacion"] = (
            df_final["fecha_licitacion"]
            .dt.strftime("%Y-%m-%d")
        )

        df_final["fecha_adjudicacion"] = (
            df_final["fecha_adjudicacion"]
            .dt.strftime("%Y-%m-%d")
        )

        # GUARDADO
        log(f"\n[4] Guardando '{args.output}'...", rep)

        df_final.to_csv(args.output, index=False, encoding="utf-8")

        generar_reporte(df_original, df_final, rep)

        log("\n✓ Proceso completado.", rep)


if __name__ == "__main__":
    main()
