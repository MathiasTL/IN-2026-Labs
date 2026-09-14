# -*- coding: utf-8 -*-
"""
Actividad propuesta - Laboratorio 1 de Inteligencia de Negocios
La decision de expansion: en que ciudad concentrar cuatro locales nuevos.

Ejecutar desde la raiz de lab01_torres/:  python actividad01.py
"""

import os
import pandas as pd

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 30)

RUTA = "datos/"


def titulo(texto):
    print("\n" + "=" * 78)
    print(texto)
    print("=" * 78)


# =============================================================================
# Carga y preparacion
# =============================================================================
titulo("ACTIVIDAD PROPUESTA. LA DECISION DE EXPANSION")

mensual = pd.read_csv(RUTA + "ventas_mensual_2025_2026.csv")
tiendas = pd.read_csv(RUTA + "tiendas.csv")

m = mensual.merge(tiendas, on="codigo_tienda", how="left")
m["anio"] = m["periodo"].str[:4].astype(int)
m["mes"] = m["periodo"].str[5:7].astype(int)

print("Filas del agregado mensual :", len(m))
print("Periodos disponibles       : %s a %s" % (m["periodo"].min(), m["periodo"].max()))

# El canal en linea (WEB) no es una plaza fisica: figura con ciudad Lima y con
# cero metros cuadrados de sala. Incluirlo atribuiria a Lima toda la venta
# digital nacional y haria indefinida la venta por m2. Se excluye de la
# comparacion entre ciudades y se reporta por separado.
web = m[m["codigo_tienda"] == "WEB"]
fis = m[m["codigo_tienda"] != "WEB"].copy()

print("\nCanal en linea excluido de la comparacion entre ciudades:")
print("  venta neta acumulada WEB : S/ %s" % format(web["venta_neta"].sum(), ",.2f"))
print("  m2_sala del canal WEB    : %d" % tiendas.loc[tiendas["codigo_tienda"] == "WEB",
                                                     "m2_sala"].iloc[0])
print("Locales fisicos por ciudad :")
print(tiendas[tiendas["codigo_tienda"] != "WEB"].groupby("ciudad")["codigo_tienda"]
      .count().to_string())


# =============================================================================
# TAREA 1. Tres indicadores comparables entre ciudades
# =============================================================================
titulo("TAREA 1. INDICADORES COMPARABLES ENTRE CIUDADES")

# --- Indicador 1. Margen bruto porcentual ------------------------------------
# Se agrega primero y se divide despues: el promedio de los margenes mensuales
# daria un promedio de razones, que pondera igual un mes grande y uno chico.
ind1 = fis.groupby("ciudad")[["venta_neta", "costo_mercaderia"]].sum()
ind1["margen_bruto_pct"] = (100 * (ind1["venta_neta"] - ind1["costo_mercaderia"])
                            / ind1["venta_neta"])

print("--- Indicador 1. Margen bruto porcentual (acumulado ene-2025 a ago-2026) ---")
print(ind1[["margen_bruto_pct"]].round(2).sort_values("margen_bruto_pct",
                                                      ascending=False).to_string())

# --- Indicador 2. Venta neta por m2 de sala (ultimos 12 meses) ---------------
# Ventana movil: setiembre 2025 a agosto 2026, ambos inclusive.
periodos = sorted(fis["periodo"].unique())
ult12 = periodos[-12:]
print("\n--- Indicador 2. Venta neta por m2 de sala (ultimos 12 meses: %s a %s) ---"
      % (ult12[0], ult12[-1]))

u12 = fis[fis["periodo"].isin(ult12)]
venta_u12 = u12.groupby("ciudad")["venta_neta"].sum()

# Los m2 se toman del maestro de tiendas, no del agregado mensual: en el
# agregado cada tienda aparece repetida una vez por mes y por categoria.
m2_ciudad = (tiendas[tiendas["codigo_tienda"] != "WEB"]
             .groupby("ciudad")["m2_sala"].sum())

ind2 = pd.DataFrame({"venta_neta_12m": venta_u12, "m2_sala": m2_ciudad})
ind2["venta_por_m2"] = ind2["venta_neta_12m"] / ind2["m2_sala"]
print(ind2.round(2).sort_values("venta_por_m2", ascending=False).to_string())

# --- Indicador 3. Crecimiento interanual ene-ago 2026 vs ene-ago 2025 --------
# Se compara la misma ventana de meses en ambos anios para evitar el sesgo de
# estacionalidad: 2026 solo tiene datos hasta agosto.
ene_ago = fis[fis["mes"].between(1, 8)]
piv = ene_ago.pivot_table(index="ciudad", columns="anio",
                          values="venta_neta", aggfunc="sum")
ind3 = piv.rename(columns={2025: "ene_ago_2025", 2026: "ene_ago_2026"})
ind3["crecimiento_pct"] = (100 * (ind3["ene_ago_2026"] / ind3["ene_ago_2025"] - 1))

print("\n--- Indicador 3. Crecimiento interanual (ene-ago 2026 vs ene-ago 2025) ---")
print(ind3.round(2).sort_values("crecimiento_pct", ascending=False).to_string())

# --- Tablero consolidado por ciudad ------------------------------------------
tablero = pd.DataFrame({
    "margen_bruto_pct": ind1["margen_bruto_pct"],
    "venta_por_m2_12m": ind2["venta_por_m2"],
    "crecimiento_pct": ind3["crecimiento_pct"],
    "locales": tiendas[tiendas["codigo_tienda"] != "WEB"].groupby("ciudad").size(),
    "m2_sala": m2_ciudad,
    "venta_neta_12m": ind2["venta_neta_12m"],
}).round(2)

print("\n--- Tablero consolidado por ciudad ---")
print(tablero.to_string())

# Indicadores complementarios que sustentan el argumento en contra.
extra = fis[fis["periodo"].isin(ult12)].groupby("ciudad").agg(
    num_clientes=("num_clientes", "sum"),
    num_transacciones=("num_transacciones", "sum"),
    unidades=("unidades", "sum"))
extra["ticket_promedio"] = (venta_u12 / extra["num_transacciones"])
print("\n--- Indicadores complementarios (ultimos 12 meses) ---")
print(extra.round(2).to_string())

os.makedirs("salidas", exist_ok=True)
tablero.to_csv("salidas/expansion_indicadores_ciudad.csv", encoding="utf-8")
extra.round(2).to_csv("salidas/expansion_complementarios.csv", encoding="utf-8")
print("\nArchivos exportados en salidas/")


# --- Prueba de robustez: sesgo por locales en maduracion ---------------------
# T10 (Yanahuara, Arequipa) abrio en ene-2024 y T12 (Victor Larco, Trujillo) en
# ago-2024. Un local en rampa de maduracion infla el crecimiento interanual de
# su ciudad. Se recalcula el indicador 3 con locales comparables: solo los que
# ya operaban antes de enero de 2025.
titulo("PRUEBA DE ROBUSTEZ DEL CRECIMIENTO INTERANUAL")

tiendas["fecha_apertura"] = pd.to_datetime(tiendas["fecha_apertura"])
maduros = tiendas.loc[tiendas["fecha_apertura"] < "2024-01-01", "codigo_tienda"]
print("Locales excluidos por maduracion:",
      sorted(set(tiendas["codigo_tienda"]) - set(maduros) - {"WEB"}))

comp = ene_ago[ene_ago["codigo_tienda"].isin(maduros)]
piv_c = comp.pivot_table(index="ciudad", columns="anio",
                         values="venta_neta", aggfunc="sum")
piv_c["crecimiento_comparable_pct"] = 100 * (piv_c[2026] / piv_c[2025] - 1)
print(piv_c.round(2).to_string())


# =============================================================================
# TAREA 2. Verificacion contra los seis criterios de calidad (Tabla 8)
# =============================================================================
titulo("TAREA 2. VERIFICACION DE INDICADORES (Tabla 8)")

criterios = pd.DataFrame([
    ["Margen bruto % por ciudad",
     "Si", "Si", "Si", "Si", "Corregido", "Corregido"],
    ["Venta neta por m2 de sala (12m)",
     "Corregido", "Si", "Si", "Si", "Si", "Si"],
    ["Crecimiento interanual ene-ago",
     "Si", "Si", "Si", "Parcial", "Si", "Corregido"],
], columns=["indicador", "especifico", "medible_reproducible", "alineado",
            "accionable", "temporal", "contextualizado"])
print(criterios.to_string(index=False))

print("""
Correcciones aplicadas tras la verificacion:

I1 Margen bruto porcentual
   - Temporal: la definicion inicial no acotaba el periodo. Se fija la ventana
     acumulada ene-2025 a ago-2026 y se declara explicitamente.
   - Contextualizado: un margen aislado no dice nada. Se compara contra el
     margen consolidado de la cadena, que es de %.2f %%.
   - Metodo: se agregan venta y costo antes de dividir. Promediar los margenes
     mensuales daria un promedio de razones que pondera igual un mes alto y uno
     bajo, y sesgaria el resultado.

I2 Venta neta por metro cuadrado
   - Especifico: la definicion original no precisaba que m2 usar. Se toma
     m2_sala del maestro de tiendas y se excluye el canal WEB, que tiene cero
     metros cuadrados y volveria indefinida la division.

I3 Crecimiento interanual
   - Contextualizado: el indicador crudo premia a las ciudades con locales
     recien abiertos, que crecen por maduracion y no por desempeno de la plaza.
     Se agrega la version comparable, que excluye T10 y T12 (aperturas de 2024).
   - Accionable: es parcial. Senala donde crecer, pero por si solo no dice
     cuanto invertir; requiere cruzarse con el costo de ocupacion, dato que hoy
     no existe en las fuentes disponibles.
""" % (100 * (fis["venta_neta"].sum() - fis["costo_mercaderia"].sum())
       / fis["venta_neta"].sum()))

criterios.to_csv("salidas/expansion_criterios_calidad.csv",
                 index=False, encoding="utf-8")


# =============================================================================
# TAREA 3. Recomendacion a la gerencia general
# =============================================================================
titulo("TAREA 3. RECOMENDACION A LA GERENCIA GENERAL")

t = tablero
print("""
RECOMENDACION: concentrar los cuatro locales nuevos en AREQUIPA.

Sustento (los tres indicadores para las tres ciudades)

                         Arequipa        Lima        Trujillo
  Margen bruto %%          %6.2f %%      %6.2f %%      %6.2f %%
  Venta neta por m2 12m   S/ %7.2f   S/ %7.2f   S/ %7.2f
  Crecimiento interanual  %6.2f %%      %6.2f %%      %6.2f %%
  Locales actuales        %6d        %6d        %6d

Arequipa lidera dos de los tres indicadores. Su margen bruto de %.2f %% supera
al de Lima en %.2f puntos porcentuales, lo que significa que cada sol vendido
en esa plaza deja mas utilidad. Su crecimiento interanual de %.2f %% quintuplica
el de Lima y se mantiene en %.2f %% al excluir los locales en maduracion, de
modo que no es un efecto de rampa sino desempeno real de la plaza. Con solo
tres locales frente a los siete de Lima, la ciudad muestra el menor grado de
saturacion de la cadena.

ARGUMENTO EN CONTRA DE LA PROPIA RECOMENDACION
Lima produce S/ %.2f por metro cuadrado, un %.1f %% mas que Arequipa, y es el
indicador estandar de productividad del retail. Su mercado absoluto es %.1f
veces mayor (S/ %s frente a S/ %s en los ultimos doce meses) y concentra %s
clientes distintos frente a %s. Un crecimiento de %.2f %% sobre una base tres
veces menor exige menos volumen incremental que un %.2f %% sobre la base de
Lima, de modo que la comparacion de tasas favorece estructuralmente a la plaza
chica. Si el criterio de la gerencia fuera maximizar venta absoluta por metro
cuadrado y no rentabilidad ni crecimiento, la decision correcta seria Lima.

DATO QUE HOY NO EXISTE Y HARIA MAS SOLIDA LA RECOMENDACION
El costo de ocupacion por metro cuadrado en cada plaza: alquiler, servicios y
planilla. Los indicadores disponibles miden ingreso y margen de mercaderia,
pero ninguno mide el costo de operar el local. Una plaza con mayor margen bruto
puede ser menos rentable si su alquiler por metro cuadrado es superior, y esa
informacion no esta en ninguna de las seis fuentes. En segundo lugar, faltan
datos de mercado (poblacion, ingreso per capita y competencia por distrito) y
de canibalizacion entre locales propios, necesarios para saber si un cuarto
local en Arequipa sumaria venta nueva o solo redistribuiria la existente.
""" % (
    t.loc["Arequipa", "margen_bruto_pct"], t.loc["Lima", "margen_bruto_pct"],
    t.loc["Trujillo", "margen_bruto_pct"],
    t.loc["Arequipa", "venta_por_m2_12m"], t.loc["Lima", "venta_por_m2_12m"],
    t.loc["Trujillo", "venta_por_m2_12m"],
    t.loc["Arequipa", "crecimiento_pct"], t.loc["Lima", "crecimiento_pct"],
    t.loc["Trujillo", "crecimiento_pct"],
    int(t.loc["Arequipa", "locales"]), int(t.loc["Lima", "locales"]),
    int(t.loc["Trujillo", "locales"]),
    t.loc["Arequipa", "margen_bruto_pct"],
    t.loc["Arequipa", "margen_bruto_pct"] - t.loc["Lima", "margen_bruto_pct"],
    t.loc["Arequipa", "crecimiento_pct"],
    piv_c.loc["Arequipa", "crecimiento_comparable_pct"],
    t.loc["Lima", "venta_por_m2_12m"],
    100 * (t.loc["Lima", "venta_por_m2_12m"] / t.loc["Arequipa", "venta_por_m2_12m"] - 1),
    t.loc["Lima", "venta_neta_12m"] / t.loc["Arequipa", "venta_neta_12m"],
    format(t.loc["Lima", "venta_neta_12m"], ",.2f"),
    format(t.loc["Arequipa", "venta_neta_12m"], ",.2f"),
    format(int(extra.loc["Lima", "num_clientes"]), ","),
    format(int(extra.loc["Arequipa", "num_clientes"]), ","),
    t.loc["Arequipa", "crecimiento_pct"], t.loc["Lima", "crecimiento_pct"],
))
