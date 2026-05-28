"""
preparar_dataset.py
===================
Curso IA y FL 2026 — Universidad de Montevideo
Proyecto 4: UY-CompraTracker

Versión modificada para leer archivos JSON OCDS
de compras públicas uruguayas.
"""

import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd


COLUMNAS_SALIDA = [
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
]


def log(msg, archivo=None):
    print(msg)
    if archivo:
        archivo.write(msg + "\n")


def esta_vacio(valor):
    if valor is None:
        return True
    if isinstance(valor, str):
        return valor.strip() == ""
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def primero_no_vacio(*valores):
    for valor in valores:
        if not esta_vacio(valor):
            return valor
    return np.nan


def fecha_mas_antigua(actual, nueva):
    if esta_vacio(actual):
        return nueva
    if esta_vacio(nueva):
        return actual

    actual_dt = pd.to_datetime(actual, errors="coerce", utc=True)
    nueva_dt = pd.to_datetime(nueva, errors="coerce", utc=True)

    if pd.isna(actual_dt):
        return nueva
    if pd.isna(nueva_dt):
        return actual
    return nueva if nueva_dt < actual_dt else actual


def fecha_licitacion_release(release):
    tender = release.get("tender", {}) or {}
    periodo = tender.get("tenderPeriod", {}) or {}

    return primero_no_vacio(
        periodo.get("startDate"),
        tender.get("datePublished"),
        release.get("date"),
    )


def actualizar_licitacion(licitaciones, release):
    ocid = release.get("ocid")
    tender = release.get("tender", {}) or {}

    if esta_vacio(ocid) or not tender:
        return

    buyer = release.get("buyer", {}) or {}
    procuring = tender.get("procuringEntity", {}) or {}

    nueva = {
        "ocid": ocid,
        "id_licitacion": tender.get("id"),
        "organismo": primero_no_vacio(buyer.get("name"), procuring.get("name")),
        "fecha_licitacion": fecha_licitacion_release(release),
        "objeto_licitacion": primero_no_vacio(
            tender.get("title"),
            tender.get("description"),
        ),
    }

    actual = licitaciones.get(ocid)

    if actual is None:
        licitaciones[ocid] = nueva
        return

    for campo, valor in nueva.items():
        if campo == "fecha_licitacion":
            actual[campo] = fecha_mas_antigua(actual.get(campo), valor)
        elif esta_vacio(actual.get(campo)) and not esta_vacio(valor):
            actual[campo] = valor


def convertir_float(valor):
    if esta_vacio(valor):
        return np.nan
    try:
        return float(valor)
    except (TypeError, ValueError):
        return np.nan


def monto_adjudicacion(award):
    valor = award.get("value", {}) or {}
    monto = convertir_float(valor.get("amount"))
    moneda = valor.get("currency")

    if not esta_vacio(monto) and monto > 0:
        return monto, moneda

    total = 0.0

    for item in award.get("items", []) or []:
        cantidad = convertir_float(item.get("quantity"))
        unit_value = (
            item.get("unit", {}) or {}
        ).get("value", {}) or {}
        precio = convertir_float(unit_value.get("amount"))

        if esta_vacio(moneda):
            moneda = unit_value.get("currency")

        if esta_vacio(cantidad) or esta_vacio(precio):
            continue

        total += cantidad * precio

    if total > 0:
        return total, moneda
    return np.nan, moneda


def descripcion_adjudicacion(award):
    for item in award.get("items", []) or []:
        clasificacion = item.get("classification", {}) or {}
        descripcion = primero_no_vacio(
            clasificacion.get("description"),
            item.get("description"),
        )

        if not esta_vacio(descripcion):
            return descripcion

    return award.get("title")


def cargar_releases_json(archivo, reporte):
    try:
        with open(archivo, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log(f"    [ERROR] No se pudo leer {archivo}: {e}", reporte)
        return []

    return data.get("releases", []) or []


def cargar_jsons_ocds(carpeta, reporte):
    """
    Lee archivos OCDS l-*.json y a-*.json. Primero indexa las licitaciones por
    `ocid` y luego genera filas de adjudicacion fusionadas con esos datos.
    """

    archivos = sorted(glob.glob(os.path.join(carpeta, "*.json")))

    log(f"  JSON encontrados: {len(archivos)}", reporte)

    licitaciones = {}
    total_releases = 0
    releases_licitacion = 0
    releases_adjudicacion = 0

    for archivo in archivos:
        log(f"    Indexando licitaciones: {os.path.basename(archivo)}", reporte)
        releases = cargar_releases_json(archivo, reporte)
        total_releases += len(releases)

        for release in releases:
            if release.get("tender"):
                releases_licitacion += 1
                actualizar_licitacion(licitaciones, release)

    filas = []

    for archivo in archivos:
        log(f"    Fusionando adjudicaciones: {os.path.basename(archivo)}", reporte)
        releases = cargar_releases_json(archivo, reporte)

        for release in releases:
            tag = release.get("tag", []) or []

            if "award" not in tag:
                continue

            releases_adjudicacion += 1
            ocid = release.get("ocid")
            licitacion = licitaciones.get(ocid, {})
            buyer = release.get("buyer", {}) or {}

            for award in release.get("awards", []) or []:
                suppliers = award.get("suppliers", []) or []

                if not suppliers:
                    continue

                proveedor = suppliers[0].get("name")
                monto, moneda = monto_adjudicacion(award)

                filas.append({
                    "ocid": ocid,
                    "id_licitacion": primero_no_vacio(
                        licitacion.get("id_licitacion"),
                        (release.get("tender", {}) or {}).get("id"),
                    ),
                    "id_adjudicacion": award.get("id"),
                    "organismo": primero_no_vacio(
                        buyer.get("name"),
                        licitacion.get("organismo"),
                    ),
                    "proveedor": proveedor,
                    "monto": monto,
                    "moneda": moneda,
                    "fecha_licitacion": licitacion.get("fecha_licitacion"),
                    "fecha_adjudicacion": primero_no_vacio(
                        award.get("date"),
                        release.get("date"),
                    ),
                    "objeto_licitacion": primero_no_vacio(
                        licitacion.get("objeto_licitacion"),
                        descripcion_adjudicacion(award),
                    ),
                    "estado": award.get("status"),
                })

    df = pd.DataFrame(filas, columns=COLUMNAS_SALIDA)
    fusionadas = int(df["fecha_licitacion"].notna().sum()) if not df.empty else 0
    sin_licitacion = len(df) - fusionadas

    log(f"  Releases leidos              : {total_releases:,}", reporte)
    log(f"  Releases con datos tender    : {releases_licitacion:,}", reporte)
    log(f"  Licitaciones indexadas       : {len(licitaciones):,}", reporte)
    log(f"  Releases de adjudicacion     : {releases_adjudicacion:,}", reporte)
    log(f"  Filas de adjudicacion        : {len(df):,}", reporte)
    log(f"  Filas fusionadas por ocid    : {fusionadas:,}", reporte)
    log(f"  Filas sin tender disponible  : {sin_licitacion:,}", reporte)

    return df


def limpiar_montos(serie, reporte):
    original_nulls = serie.isna().sum()
    limpia = pd.to_numeric(serie, errors="coerce")
    pendientes = limpia.isna() & serie.notna()

    if pendientes.any():
        texto = (
            serie[pendientes]
            .astype(str)
            .str.replace(r"(?i)(UYU|USD|US\$|\$|UY)", "", regex=True)
            .str.replace(r"\s+", "", regex=True)
            .str.replace(r"\.", "", regex=True)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        limpia.loc[pendientes] = pd.to_numeric(texto, errors="coerce")

    nuevos_nulls = max(0, int(limpia.isna().sum() - original_nulls))

    if nuevos_nulls > 0:
        log(f"  [LIMPIEZA] Montos no convertibles: {nuevos_nulls}", reporte)

    no_positivos = int((limpia <= 0).sum())
    limpia[limpia <= 0] = np.nan

    if no_positivos > 0:
        log(f"  [LIMPIEZA] Montos negativos o cero: {no_positivos}", reporte)

    return limpia


def limpiar_fechas(serie, nombre_col, reporte):
    resultado = pd.to_datetime(serie, errors="coerce", utc=True)
    resultado = resultado.dt.tz_convert(None)

    log(
        f"  [FECHAS] '{nombre_col}': "
        f"{resultado.notna().sum()} validas.",
        reporte
    )

    return resultado


def normalizar_texto(serie):
    return (
        serie.astype("string")
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
        .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA})
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
        log(f"  [AVISO] Estrato organismo fallo: {e}", reporte)

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
            log(f"  [AVISO] Estrato proveedor fallo: {e}", reporte)

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
        pct = 0 if len(df_final) == 0 else 100 * n / len(df_final)

        log(f"    {col:25s}: {n:5d} ({pct:.1f}%)", reporte)


def main():

    parser = argparse.ArgumentParser(
        description="Prepara dataset OCDS de compras publicas"
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
        log("PREPARACION DATASET OCDS", rep)
        log("=" * 60, rep)

        # CARGA Y FUSION JSON
        log("\n[1] Cargando y fusionando JSON OCDS...", rep)

        df = cargar_jsons_ocds(args.input, rep)

        log(f"  Filas cargadas : {len(df):,}", rep)
        log(f"  Columnas       : {list(df.columns)}", rep)

        df_original = df.copy()

        # LIMPIEZA
        log("\n[2] Limpiando datos...", rep)

        for col in ["organismo", "proveedor", "objeto_licitacion", "estado", "moneda"]:
            df[col] = normalizar_texto(df[col])

        df["monto"] = limpiar_montos(df["monto"], rep).round(2)

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

        negativos = int((df["dias_adjudicacion"] < 0).sum())
        df.loc[df["dias_adjudicacion"] < 0, "dias_adjudicacion"] = np.nan

        if negativos > 0:
            log(f"  [FECHAS] Duraciones negativas descartadas: {negativos}", rep)

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

        log("\nOK - Proceso completado.", rep)


if __name__ == "__main__":
    main()
