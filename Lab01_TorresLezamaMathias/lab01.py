# -*- coding: utf-8 -*-
"""
Laboratorio 1 - Inteligencia de Negocios
Del dato crudo a la decision gerencial
Comercial Los Andes S.A.C. - Agosto 2026

Ejecutar desde la raiz de lab01_torres/:  python lab01.py
"""

import os
import pandas as pd

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 30)

RUTA = "datos/"
IGV = 0.18


def titulo(texto):
    print("\n" + "=" * 78)
    print(texto)
    print("=" * 78)


# =============================================================================
# PARTE 1. Carga y reconocimiento de las fuentes
# =============================================================================
titulo("PARTE 1. CARGA Y RECONOCIMIENTO DE LAS FUENTES")

ventas       = pd.read_csv(RUTA + "ventas_pos_202608.csv")
comprobantes = pd.read_csv(RUTA + "comprobantes_202608.csv")
despachos    = pd.read_csv(RUTA + "despachos_202608.csv")
productos    = pd.read_csv(RUTA + "productos.csv")
tiendas      = pd.read_csv(RUTA + "tiendas.csv")
mensual      = pd.read_csv(RUTA + "ventas_mensual_2025_2026.csv")

fuentes = {
    "ventas": ventas, "comprobantes": comprobantes,
    "despachos": despachos, "productos": productos,
    "tiendas": tiendas, "mensual": mensual,
}

print("--- Paso 1.1. Dimensiones de cada fuente ---")
for nombre, df in fuentes.items():
    print("%-14s filas=%6d columnas=%2d" % (nombre, df.shape[0], df.shape[1]))

print("\n--- Paso 1.2. Tipos de dato de ventas_pos_202608 ---")
print(ventas.dtypes)
print("\nPrimeras 10 filas:")
print(ventas.head(10))

print("\n--- Paso 1.3. Columnas de cada fuente (insumo Tabla 3) ---")
for nombre, df in fuentes.items():
    print("%-14s -> %s" % (nombre, list(df.columns)))

print("\n--- Maestro de tiendas (Punto de control 0) ---")
print(tiendas)


# =============================================================================
# PARTE 2. Perfilado y diagnostico de calidad
# =============================================================================
titulo("PARTE 2. PERFILADO Y DIAGNOSTICO DE CALIDAD")

# --- Paso 2.1. Valores nulos -------------------------------------------------
print("--- Paso 2.1. Nulos por columna (ventas) ---")
print(ventas.isna().sum())
n_nulos_cant = ventas["cantidad"].isna().sum()
n_nulos_prec = ventas["precio_unitario"].isna().sum()
n_nulos_fila = ventas[["cantidad", "precio_unitario"]].isna().any(axis=1).sum()
print("Filas sin cantidad o sin precio: %d" % n_nulos_fila)

# --- Paso 2.2. Filas duplicadas ----------------------------------------------
print("\n--- Paso 2.2. Duplicados exactos ---")
n_dup = ventas.duplicated().sum()
print("Filas duplicadas exactas:", n_dup)
print(ventas[ventas.duplicated(keep=False)].sort_values("id_linea").head(6))

# --- Paso 2.3. Formatos de fecha inconsistentes ------------------------------
print("\n--- Paso 2.3. Formatos de fecha ---")
print(ventas["fecha_pedido"].head(3).tolist())
con_barra = ventas["fecha_pedido"].str.contains("/").sum()
print("Fechas en formato dd/mm/aaaa:", con_barra)

# --- Paso 2.4. Codigos de tienda inconsistentes ------------------------------
print("\n--- Paso 2.4. Codigos de tienda ---")
print(sorted(ventas["codigo_tienda"].unique()))
n_tienda_min = (ventas["codigo_tienda"] != ventas["codigo_tienda"].str.upper()).sum()
print("Filas con codigo en minuscula:", n_tienda_min)

# --- Paso 2.5. Cantidades negativas y precios atipicos -----------------------
print("\n--- Paso 2.5. Cantidades negativas y precios atipicos ---")
n_negativos = (ventas["cantidad"] < 0).sum()
print("Cantidades negativas:", n_negativos)
print(ventas["precio_unitario"].describe())
print("Percentil 99 del precio: %.2f" % ventas["precio_unitario"].quantile(0.99))
print("Precios sobre 900:", (ventas["precio_unitario"] > 900).sum())

# --- Paso 2.6. Integridad referencial ----------------------------------------
print("\n--- Paso 2.6. Integridad referencial ---")
huerfanos = ~ventas["sku"].isin(productos["sku"])
print("Lineas con SKU inexistente:", huerfanos.sum())
print("SKU distintos no catalogados:", ventas.loc[huerfanos, "sku"].nunique())

sin_pedido = ~comprobantes["id_pedido"].isin(ventas["id_pedido"])
print("Comprobantes sin pedido asociado:", sin_pedido.sum())

# --- Paso 2.7. Categorias no normalizadas ------------------------------------
print("\n--- Paso 2.7. Categorias del catalogo ---")
print(sorted(productos["categoria"].unique()))
print("Valores distintos:", productos["categoria"].nunique())
n_precio_lista_nulo = productos["precio_lista"].isna().sum()
print("Productos sin precio_lista:", n_precio_lista_nulo)

# --- Paso 2.8. Aplicar la limpieza -------------------------------------------
print("\n--- Paso 2.8. Aplicacion de reglas de limpieza ---")
v = ventas.copy()
print("Filas iniciales:", len(v))

# R1. Eliminar duplicados exactos
v = v.drop_duplicates()
print("R1 sin duplicados       :", len(v))

# R2. Normalizar el codigo de tienda
v["codigo_tienda"] = v["codigo_tienda"].str.upper().str.strip()

# R3. Parsear la fecha admitiendo los dos formatos presentes
f1 = pd.to_datetime(v["fecha_pedido"], format="%Y-%m-%d", errors="coerce")
f2 = pd.to_datetime(v["fecha_pedido"], format="%d/%m/%Y", errors="coerce")
v["fecha_pedido"] = f1.fillna(f2)
print("R3 fechas sin convertir :", v["fecha_pedido"].isna().sum())

# R4. Descartar lineas sin cantidad o sin precio
v = v.dropna(subset=["cantidad", "precio_unitario"])
print("R4 sin nulos            :", len(v))

# R5. Descartar cantidades negativas (se tratan aparte como devoluciones)
v = v[v["cantidad"] > 0]
print("R5 sin negativos        :", len(v))

# R6. Descartar precios atipicos: mas de 20 veces la mediana
limite = 20 * v["precio_unitario"].median()
print("R6 umbral de precio     : %.2f" % limite)
v = v[v["precio_unitario"] <= limite]
print("R6 sin atipicos         :", len(v))

# R7. Calcular el valor de cada linea (con IGV)
v["valor_linea"] = v["cantidad"] * v["precio_unitario"] * (1 - v["descuento_pct"])

# R8. Normalizar la categoria en el catalogo de productos
prod = productos.copy()
prod["categoria"] = (prod["categoria"].str.strip().str.upper()
                     .replace({"PINTURA": "PINTURAS"}))
print("R8 categorias distintas :", prod["categoria"].nunique())
print("Categorias finales      :", sorted(prod["categoria"].dropna().unique()))


# =============================================================================
# PARTE 3. Reproducir el problema de las tres cifras
# =============================================================================
titulo("PARTE 3. EL PROBLEMA DE LAS TRES CIFRAS")

# --- Paso 3.1. Cifra del area comercial --------------------------------------
# Definicion: total de pedidos registrados, CON IGV, SIN descontar anulados.
comercial = v["valor_linea"].sum()
print("COMERCIAL : S/ %15s" % format(comercial, ",.2f"))

# --- Paso 3.2. Cifra del area de finanzas ------------------------------------
# Definicion: comprobantes emitidos, SIN IGV, neto de notas de credito,
# considerando unicamente los que tienen pedido asociado en el detalle.
comp = comprobantes[comprobantes["id_pedido"].isin(v["id_pedido"])]
emitidos = comp[comp["tipo_comprobante"] != "NOTA_CREDITO"]["monto_total"].sum()
notas_cr = comp[comp["tipo_comprobante"] == "NOTA_CREDITO"]["monto_total"].sum()

finanzas = (emitidos - notas_cr) / (1 + IGV)
print("FINANZAS  : S/ %15s" % format(finanzas, ",.2f"))
print("   emitidos  : %s" % format(emitidos, ",.2f"))
print("   notas cr. : %s" % format(notas_cr, ",.2f"))

# --- Paso 3.3. Cifra del area de logistica -----------------------------------
# Definicion: guias efectivamente despachadas, valorizadas a precio de lista.
desp = despachos[despachos["estado_despacho"] == "DESPACHADO"]
logistica = desp["valor_lista"].sum()
print("LOGISTICA : S/ %15s" % format(logistica, ",.2f"))

# --- Paso 3.4. Comparar y cuantificar la brecha ------------------------------
cifras = {"Comercial": comercial, "Finanzas": finanzas, "Logistica": logistica}
mayor, menor = max(cifras.values()), min(cifras.values())

print()
for area, valor in cifras.items():
    print("%-10s S/ %15s" % (area, format(valor, ",.2f")))
print("Brecha absoluta : S/ %s" % format(mayor - menor, ",.2f"))
print("Brecha relativa : %.1f%% sobre la cifra menor" % (100 * (mayor / menor - 1)))

# --- Paso 3.5.1. Descomposicion Comercial vs Finanzas ------------------------
# Se descompone la brecha en tres efectos aplicados en cadena.
print("\n--- Paso 3.5.1. Descomposicion de la brecha Comercial - Finanzas ---")

anulados_val = v[v["estado_pedido"] == "ANULADO"]["valor_linea"].sum()
registrados_val = v[v["estado_pedido"] == "REGISTRADO"]["valor_linea"].sum()

efecto_anulados = anulados_val                                   # con IGV
efecto_igv = registrados_val - registrados_val / (1 + IGV)        # IGV sobre lo registrado
efecto_notas = notas_cr / (1 + IGV)                               # notas de credito sin IGV
subtotal = comercial - efecto_anulados - efecto_igv - efecto_notas
residuo = subtotal - finanzas

print("Comercial (con IGV, incl. anulados)   : S/ %s" % format(comercial, ",.2f"))
print("(-) Pedidos anulados                  : S/ %s" % format(efecto_anulados, ",.2f"))
print("(-) IGV sobre pedidos registrados     : S/ %s" % format(efecto_igv, ",.2f"))
print("(-) Notas de credito (sin IGV)        : S/ %s" % format(efecto_notas, ",.2f"))
print("(=) Subtotal reconstruido             : S/ %s" % format(subtotal, ",.2f"))
print("Finanzas (real)                       : S/ %s" % format(finanzas, ",.2f"))
print("Residuo (comprobantes vs detalle POS) : S/ %s" % format(residuo, ",.2f"))

brecha_cf = comercial - finanzas
print("\nParticipacion de cada efecto en la brecha Comercial-Finanzas:")
for nombre, val in [("Anulados", efecto_anulados), ("IGV", efecto_igv),
                    ("Notas de credito", efecto_notas), ("Residuo", residuo)]:
    print("  %-18s S/ %14s  (%5.1f%%)" % (nombre, format(val, ",.2f"),
                                          100 * val / brecha_cf))

# --- Paso 3.5.2. Por que Logistica no es subconjunto de Comercial ------------
print("\n--- Paso 3.5.2. Causas de la diferencia con Logistica ---")
print("Estados de despacho:")
print(despachos["estado_despacho"].value_counts())

desp_sin_pedido = ~despachos["id_pedido"].isin(v["id_pedido"])
print("Guias sin pedido en el detalle POS    :", desp_sin_pedido.sum())
print("Pedidos distintos despachados         :", desp["id_pedido"].nunique())
print("Pedidos distintos en el detalle POS   :", v["id_pedido"].nunique())

desp_anulados = desp[desp["id_pedido"].isin(
    v[v["estado_pedido"] == "ANULADO"]["id_pedido"])]
print("Guias DESPACHADAS de pedidos ANULADOS :", len(desp_anulados))
print("  valorizadas en S/ %s" % format(desp_anulados["valor_lista"].sum(), ",.2f"))
print("Logistica valoriza a PRECIO DE LISTA: ignora descuentos comerciales.")
print("Descuento promedio aplicado en ventas : %.2f %%"
      % (100 * v["descuento_pct"].mean()))


# =============================================================================
# PARTE 4. Definicion unica y panel de indicadores
# =============================================================================
titulo("PARTE 4. DEFINICION UNICA Y PANEL DE INDICADORES")

# --- Paso 4.1. Definicion corporativa de VENTA NETA --------------------------
# Valor de las lineas de pedidos NO anulados = cantidad * precio * (1 - dcto),
# expresado SIN IGV y neto de notas de credito del periodo.
# Reconocimiento en fecha de pedido. Dueno: Gerencia de Administracion y Finanzas.
registrados = v[v["estado_pedido"] == "REGISTRADO"]
venta_neta = (registrados["valor_linea"].sum() - notas_cr) / (1 + IGV)
print("VENTA NETA AGOSTO 2026 : S/ %s" % format(venta_neta, ",.2f"))

# --- Paso 4.2. Panel de indicadores ------------------------------------------
n_pedidos   = registrados["id_pedido"].nunique()
n_pedidos_t = v["id_pedido"].nunique()
unidades    = registrados["cantidad"].sum()

ticket       = venta_neta / n_pedidos
lineas_ped   = len(registrados) / n_pedidos
tasa_anul    = 100 * (1 - n_pedidos / n_pedidos_t)
digital      = registrados[registrados["canal"] == "DIGITAL"]
part_digital = 100 * (digital["valor_linea"].sum() / (1 + IGV)) / venta_neta

print("\n--- Panel minimo de indicadores - Agosto 2026 ---")
print("1. Venta neta del mes        : S/ %s" % format(venta_neta, ",.2f"))
print("2. Numero de pedidos         : %d" % n_pedidos)
print("3. Ticket promedio (s/IGV)   : S/ %.2f" % ticket)
print("4. Unidades vendidas         : %d" % unidades)
print("5. Lineas por pedido         : %.2f" % lineas_ped)
print("6. Tasa de anulacion         : %.2f %%" % tasa_anul)
print("7. Participacion del digital : %.2f %%" % part_digital)

# --- Paso 4.3. Desagregacion por tienda y por categoria ----------------------
print("\n--- Paso 4.3.a. Ranking de locales por venta neta ---")
por_tienda = (registrados.groupby("codigo_tienda")["valor_linea"].sum()
              .div(1 + IGV).sort_values(ascending=False).round(2))
por_tienda = por_tienda.rename("venta_neta").reset_index()
por_tienda = por_tienda.merge(tiendas, on="codigo_tienda", how="left")
print(por_tienda[["codigo_tienda", "nombre_tienda", "ciudad", "venta_neta"]].head(5))

print("\n--- Paso 4.3.b. Venta neta por categoria ---")
con_cat = registrados.merge(prod[["sku", "categoria"]], on="sku", how="left")
por_cat = (con_cat.groupby("categoria", dropna=False)["valor_linea"].sum()
           .div(1 + IGV).sort_values(ascending=False).round(2))
print(por_cat)

venta_sin_cat = por_cat[por_cat.index.isna()].sum() if por_cat.index.isna().any() else 0.0
print("\nVenta NO atribuible a categoria (SKU fuera del catalogo): S/ %s (%.2f%%)"
      % (format(venta_sin_cat, ",.2f"), 100 * venta_sin_cat / venta_neta))

# --- Paso 4.4. Exportar los resultados ---------------------------------------
os.makedirs("salidas", exist_ok=True)
por_tienda.to_csv("salidas/kpi_por_tienda.csv", index=False, encoding="utf-8")
por_cat.to_csv("salidas/kpi_por_categoria.csv", encoding="utf-8")

panel = pd.DataFrame({
    "indicador": ["Venta neta del mes", "Numero de pedidos", "Ticket promedio (s/IGV)",
                  "Unidades vendidas", "Lineas por pedido", "Tasa de anulacion (%)",
                  "Participacion canal digital (%)"],
    "valor": [round(venta_neta, 2), n_pedidos, round(ticket, 2), int(unidades),
              round(lineas_ped, 2), round(tasa_anul, 2), round(part_digital, 2)],
})
panel.to_csv("salidas/panel_indicadores.csv", index=False, encoding="utf-8")

tres_cifras = pd.DataFrame({
    "area": ["Comercial", "Finanzas", "Logistica", "DEFINICION UNICA"],
    "cifra": [round(comercial, 2), round(finanzas, 2), round(logistica, 2),
              round(venta_neta, 2)],
})
tres_cifras.to_csv("salidas/tres_cifras.csv", index=False, encoding="utf-8")

print("\nArchivos exportados en la carpeta salidas/")


# =============================================================================
# PARTE 5. Clasificacion de los indicadores
# =============================================================================
titulo("PARTE 5. CLASIFICACION DE INDICADORES (pirámide de Anthony)")

venta_top   = por_tienda.iloc[0]
venta_media = por_tienda[por_tienda["codigo_tienda"] != "WEB"]["venta_neta"].mean()

clasificacion = pd.DataFrame([
    ["Venta neta del mes", "S/ %s" % format(venta_neta, ",.2f"), "Estrategico",
     "Si. Tiene meta anual y dueno (Gcia. Adm. y Finanzas).",
     "Revision del plan comercial"],
    ["Ticket promedio", "S/ %.2f" % ticket, "Tactico",
     "Si. Accionable via pricing, cross-selling y mezcla de surtido.",
     "Rediseno de promociones y bundles"],
    ["Tasa de anulacion", "%.2f %%" % tasa_anul, "Operativo",
     "Si. Umbral definido; dispara revision de causa raiz por local.",
     "Auditoria del proceso de captura de pedidos"],
    ["Participacion canal digital", "%.2f %%" % part_digital, "Estrategico",
     "Si. Mide avance de la estrategia de omnicanalidad.",
     "Reasignacion del presupuesto de marketing digital"],
    ["Lineas por pedido", "%.2f" % lineas_ped, "Tactico",
     "NO. Descriptivo: sin meta, sin dueno y sin accion definida ante desvio.",
     "Ninguna accion definida (no supera la prueba del KPI)"],
    ["Venta por local", "S/ %s (top: %s)" % (format(venta_top["venta_neta"], ",.2f"),
                                             venta_top["codigo_tienda"]), "Tactico",
     "Si. Base de metas por local y de la evaluacion del jefe de tienda.",
     "Plan de recuperacion del local por debajo de meta"],
], columns=["indicador", "valor", "nivel_decision", "es_kpi", "accion_si_se_desvia"])

for _, r in clasificacion.iterrows():
    print("\n%-28s %s" % (r["indicador"], r["valor"]))
    print("  Nivel   : %s" % r["nivel_decision"])
    print("  KPI     : %s" % r["es_kpi"])
    print("  Accion  : %s" % r["accion_si_se_desvia"])

clasificacion.to_csv("salidas/clasificacion_indicadores.csv",
                     index=False, encoding="utf-8")

print("\n--- Evidencia: 'Lineas por pedido' no supera la prueba del KPI ---")
lpp_tienda = (registrados.groupby("codigo_tienda")["id_pedido"]
              .agg(lineas="size", pedidos="nunique"))
lpp_tienda["lineas_por_pedido"] = (lpp_tienda["lineas"] / lpp_tienda["pedidos"]).round(2)
print(lpp_tienda[["lineas_por_pedido"]].sort_values("lineas_por_pedido"))
print("Rango entre locales: %.2f - %.2f (dispersion minima)"
      % (lpp_tienda["lineas_por_pedido"].min(), lpp_tienda["lineas_por_pedido"].max()))
print("Venta neta promedio por local fisico: S/ %s" % format(venta_media, ",.2f"))
print("\nArchivos exportados en salidas/")
