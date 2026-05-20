"""
preparar_dataset.py
===================
Curso IA y FL 2026 — Universidad de Montevideo
Proyecto 4: UY-CompraTracker

Propósito:
    Tomar el CSV de compras públicas (~100.000 registros) del Catálogo de
    Datos Abiertos de Uruguay y producir un subconjunto limpio de 5.000
    registros representativo, listo para que los estudiantes trabajen.

Uso:
    python preparar_dataset.py --input compras_publicas.csv
                               --output compras_procesadas.csv
                               --n 5000

Salida:
    - compras_procesadas.csv   : dataset reducido y limpio
    - reporte_preparacion.txt  : resumen de decisiones de limpieza
"""

import argparse
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime


# ── Configuración de columnas esperadas ───────────────────────────────────────
COLUMNAS_ESPERADAS = [
    "organismo",
    "proveedor",
    "monto",
    "fecha_licitacion",
    "fecha_adjudicacion",
    "objeto_licitacion",
    "estado",
]

# Posibles nombres alternativos en el CSV original (el catálogo cambia headers)
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


def detectar_columnas(df, reporte):
    """Mapea columnas reales del CSV a los nombres canónicos del proyecto."""
    cols_lower = {c.lower().replace(" ", "_"): c for c in df.columns}
    mapeo = {}

    for nombre_canonical, posibles in ALIASES.items():
        encontrado = None
        for alias in posibles:
            if alias in cols_lower:
                encontrado = cols_lower[alias]
                break
        if encontrado:
            mapeo[encontrado] = nombre_canonical
        else:
            log(f"  [AVISO] Columna '{nombre_canonical}' no encontrada. "
                f"Se creará vacía.", reporte)

    return mapeo


def limpiar_montos(serie, reporte):
    """Convierte montos a float, eliminando símbolos de moneda y separadores."""
    original_nulls = serie.isna().sum()

    # Remover símbolos comunes: $, UYU, USD, puntos de miles, comas decimales
    limpia = (
        serie.astype(str)
        .str.replace(r"[$UYusd\s]", "", regex=True)
        .str.replace(r"\.", "", regex=True)   # punto como separador de miles
        .str.replace(",", ".", regex=False)    # coma como separador decimal
        .str.strip()
    )
    limpia = pd.to_numeric(limpia, errors="coerce")

    nuevos_nulls = limpia.isna().sum() - original_nulls
    if nuevos_nulls > 0:
        log(f"  [LIMPIEZA] Montos no convertibles: {nuevos_nulls} → reemplazados por NaN",
            reporte)

    # Eliminar montos negativos o cero (probablemente errores)
    negativos = (limpia <= 0).sum()
    limpia[limpia <= 0] = np.nan
    if negativos > 0:
        log(f"  [LIMPIEZA] Montos negativos o cero: {negativos} → reemplazados por NaN",
            reporte)

    return limpia


def limpiar_fechas(serie, nombre_col, reporte):
    """Parsea fechas con múltiples formatos posibles."""
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formatos:
        try:
            resultado = pd.to_datetime(serie, format=fmt, errors="coerce")
            parseados = resultado.notna().sum()
            if parseados > len(serie) * 0.5:  # al menos 50% parseados
                nulos = resultado.isna().sum()
                log(f"  [FECHAS] '{nombre_col}': formato '{fmt}', "
                    f"{parseados} válidas, {nulos} nulas.", reporte)
                return resultado
        except Exception:
            continue

    # Último recurso: inferencia automática
    resultado = pd.to_datetime(serie, infer_datetime_format=True, errors="coerce")
    log(f"  [FECHAS] '{nombre_col}': inferencia automática, "
        f"{resultado.notna().sum()} válidas.", reporte)
    return resultado


def normalizar_texto(serie):
    """Normaliza strings: mayúsculas, sin espacios dobles, strip."""
    return (
        serie.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
        .replace("NAN", np.nan)
        .replace("NONE", np.nan)
    )


def samplear_representativo(df, n, reporte):
    """
    Estrategia de muestreo estratificado para preservar diversidad:
    - 60% muestreo estratificado por organismo (los más frecuentes)
    - 25% muestreo estratificado por proveedor (los más frecuentes)
    - 15% muestra aleatoria del resto (captura organismos/proveedores raros)

    Esto garantiza que los estudiantes encuentren patrones reales de
    concentración y adjudicación repetida al aplicar sus reglas pyDatalog.
    """
    n_organismos = int(n * 0.60)
    n_proveedores = int(n * 0.25)
    n_random      = n - n_organismos - n_proveedores

    log(f"\n  Estrategia de muestreo:", reporte)
    log(f"    - {n_organismos} registros estratificados por organismo (60%)", reporte)
    log(f"    - {n_proveedores} registros estratificados por proveedor (25%)", reporte)
    log(f"    - {n_random} registros aleatorios (15%)", reporte)

    indices = set()

    # Estrato 1: por organismo
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
        log(f"  [AVISO] Estrato organismo falló: {e}. Usando muestra aleatoria.", reporte)

    # Estrato 2: por proveedor (sobre los no seleccionados aún)
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
            log(f"  [AVISO] Estrato proveedor falló: {e}.", reporte)

    # Estrato 3: aleatorio del resto
    restante2 = df[~df.index.isin(indices)]
    if len(restante2) > 0:
        n_ale = min(n_random, len(restante2))
        muestra_ale = restante2.sample(n_ale, random_state=42)
        indices.update(muestra_ale.index.tolist())

    resultado = df.loc[list(indices)].sample(frac=1, random_state=42)  # shuffle
    return resultado.head(n)


def generar_reporte(df_original, df_final, decisiones, reporte):
    log("\n" + "="*60, reporte)
    log("RESUMEN FINAL", reporte)
    log("="*60, reporte)
    log(f"  Registros originales : {len(df_original):,}", reporte)
    log(f"  Registros en salida  : {len(df_final):,}", reporte)
    log(f"  Columnas             : {list(df_final.columns)}", reporte)
    log(f"\n  Nulos por columna:", reporte)
    for col in df_final.columns:
        n = df_final[col].isna().sum()
        pct = 100 * n / len(df_final)
        log(f"    {col:25s}: {n:5d} ({pct:.1f}%)", reporte)

    log(f"\n  Organismos únicos    : {df_final['organismo'].nunique()}", reporte)
    log(f"  Proveedores únicos   : {df_final['proveedor'].nunique()}", reporte)

    if "monto" in df_final.columns:
        log(f"\n  Estadísticas de monto:", reporte)
        log(f"    Mediana : {df_final['monto'].median():,.0f}", reporte)
        log(f"    Media   : {df_final['monto'].mean():,.0f}", reporte)
        log(f"    Máximo  : {df_final['monto'].max():,.0f}", reporte)
        log(f"    Mínimo  : {df_final['monto'].min():,.0f}", reporte)

    if "dias_adjudicacion" in df_final.columns:
        log(f"\n  Días hasta adjudicación:", reporte)
        log(f"    Mediana : {df_final['dias_adjudicacion'].median():.0f} días", reporte)
        log(f"    Media   : {df_final['dias_adjudicacion'].mean():.0f} días", reporte)


def main():
    parser = argparse.ArgumentParser(
        description="Prepara dataset de compras públicas para Proyecto 4 — IA y FL 2026"
    )
    parser.add_argument("--input",  required=True, help="CSV original de compras públicas")
    parser.add_argument("--output", default="compras_procesadas.csv",
                        help="CSV de salida (default: compras_procesadas.csv)")
    parser.add_argument("--n",      type=int, default=5000,
                        help="Cantidad de registros de salida (default: 5000)")
    parser.add_argument("--reporte", default="reporte_preparacion.txt",
                        help="Archivo de reporte (default: reporte_preparacion.txt)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: no se encuentra el archivo '{args.input}'")
        sys.exit(1)

    with open(args.reporte, "w", encoding="utf-8") as rep:

        log("="*60, rep)
        log("PREPARACIÓN DE DATASET — Proyecto 4 UY-CompraTracker", rep)
        log(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", rep)
        log(f"Archivo de entrada: {args.input}", rep)
        log(f"Registros objetivo: {args.n}", rep)
        log("="*60, rep)

        # ── 1. Carga ──────────────────────────────────────────────────────────
        log("\n[1] Cargando dataset...", rep)
        try:
            # Intentar encodings comunes en datasets uruguayos
            for enc in ["utf-8", "latin-1", "iso-8859-1"]:
                try:
                    df = pd.read_csv(args.input, encoding=enc, low_memory=False)
                    log(f"  Encoding detectado: {enc}", rep)
                    break
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            log(f"  ERROR al cargar: {e}", rep)
            sys.exit(1)

        log(f"  Filas cargadas : {len(df):,}", rep)
        log(f"  Columnas       : {list(df.columns)}", rep)
        df_original = df.copy()

        # ── 2. Mapeo de columnas ──────────────────────────────────────────────
        log("\n[2] Detectando columnas...", rep)
        mapeo = detectar_columnas(df, rep)
        df = df.rename(columns=mapeo)

        # Asegurar que todas las columnas canónicas existan
        for col in COLUMNAS_ESPERADAS:
            if col not in df.columns:
                df[col] = np.nan

        df = df[COLUMNAS_ESPERADAS]

        # ── 3. Limpieza ───────────────────────────────────────────────────────
        log("\n[3] Limpiando datos...", rep)

        # Texto
        for col in ["organismo", "proveedor", "objeto_licitacion", "estado"]:
            df[col] = normalizar_texto(df[col])

        # Montos
        df["monto"] = limpiar_montos(df["monto"], rep)

        # Fechas
        df["fecha_licitacion"]   = limpiar_fechas(df["fecha_licitacion"],   "fecha_licitacion",   rep)
        df["fecha_adjudicacion"] = limpiar_fechas(df["fecha_adjudicacion"], "fecha_adjudicacion", rep)

        # Campo derivado: días hasta adjudicación
        df["dias_adjudicacion"] = (
            df["fecha_adjudicacion"] - df["fecha_licitacion"]
        ).dt.days
        # Eliminar valores negativos (error de datos)
        invalidos = (df["dias_adjudicacion"] < 0).sum()
        df.loc[df["dias_adjudicacion"] < 0, "dias_adjudicacion"] = np.nan
        if invalidos > 0:
            log(f"  [LIMPIEZA] dias_adjudicacion negativos: {invalidos} → NaN", rep)

        # Eliminar filas sin organismo ni proveedor (inutilizables)
        antes = len(df)
        df = df.dropna(subset=["organismo", "proveedor"])
        eliminados = antes - len(df)
        if eliminados > 0:
            log(f"  [LIMPIEZA] Filas sin organismo/proveedor eliminadas: {eliminados}", rep)

        log(f"  Registros tras limpieza: {len(df):,}", rep)

        # ── 4. Muestreo representativo ────────────────────────────────────────
        log("\n[4] Generando muestra representativa...", rep)
        if len(df) <= args.n:
            log(f"  Dataset ya tiene {len(df)} filas (<= {args.n}). Se usa completo.", rep)
            df_final = df
        else:
            df_final = samplear_representativo(df, args.n, rep)

        # Convertir fechas a string para el CSV (formato ISO)
        df_final = df_final.copy()
        df_final["fecha_licitacion"]   = df_final["fecha_licitacion"].dt.strftime("%Y-%m-%d")
        df_final["fecha_adjudicacion"] = df_final["fecha_adjudicacion"].dt.strftime("%Y-%m-%d")

        # ── 5. Guardado ───────────────────────────────────────────────────────
        log(f"\n[5] Guardando '{args.output}'...", rep)
        df_final.to_csv(args.output, index=False, encoding="utf-8")
        log(f"  ✓ Archivo guardado con {len(df_final):,} registros.", rep)

        # ── 6. Reporte final ──────────────────────────────────────────────────
        generar_reporte(df_original, df_final, {}, rep)

        log("\n✓ Proceso completado.", rep)
        log(f"  Dataset listo    : {args.output}", rep)
        log(f"  Reporte completo : {args.reporte}", rep)


if __name__ == "__main__":
    main()
