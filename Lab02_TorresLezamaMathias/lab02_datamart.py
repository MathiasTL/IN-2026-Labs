# -*- coding: utf-8 -*-
"""
Laboratorio 2 - Inteligencia de Negocios
Construccion de un datamart analitico y ejecucion de operaciones OLAP
MercaAndina - Setiembre 2026

Ejecutar desde la raiz de lab02_torres/:  python lab02_datamart.py

El script recorre los ocho pasos de la guia dirigida y, al final, la
actividad propuesta (seccion 11). Cada resultado se imprime en consola y
se acumula en salidas/resultados.txt para armar el informe.
"""

import json
import os

import duckdb

# ---------------------------------------------------------------------------
# Utilidades de ejecucion y captura de resultados
# ---------------------------------------------------------------------------

SALIDAS = "salidas"
os.makedirs(SALIDAS, exist_ok=True)

_bitacora = []   # texto plano de todo lo ejecutado, para el informe
_cifras = {}     # valores escalares que se citan en el informe


def titulo(texto):
    """Encabezado de seccion, visible en consola y en la bitacora."""
    linea = "\n" + "=" * 78 + "\n" + texto + "\n" + "=" * 78
    print(linea)
    _bitacora.append(linea)


def subtitulo(texto):
    linea = "\n--- " + texto + " " + "-" * max(0, 70 - len(texto))
    print(linea)
    _bitacora.append(linea)


def q(sql, etiqueta=None):
    """Ejecuta una consulta, muestra el resultado y lo guarda en la bitacora."""
    df = con.execute(sql).df()
    texto = df.to_string(index=False)
    print(texto)
    if etiqueta:
        _bitacora.append("[" + etiqueta + "]")
    _bitacora.append(texto)
    return df


# ---------------------------------------------------------------------------
# PASO 1: conexion y carga de las fuentes
# ---------------------------------------------------------------------------

titulo("PASO 1: CONEXION Y CARGA DE LAS FUENTES")

# La base se crea como archivo en disco: se puede reabrir sin recargar.
if os.path.exists("lab02.duckdb"):
    os.remove("lab02.duckdb")
con = duckdb.connect("lab02.duckdb")

# DuckDB lee los CSV directamente. Se crea una vista por cada fuente.
# Importante: se fuerzan a texto los numeros de documento. Si dejamos que el
# motor los infiera, los tomaria como enteros y luego no podriamos insertar
# la fila de valor desconocido ('N/D').
con.execute("""
CREATE OR REPLACE VIEW src_ventas_cab AS
    SELECT * FROM read_csv('datos/ventas_cabecera.csv',
        header=true, types={'nro_documento_cliente': 'VARCHAR'});

CREATE OR REPLACE VIEW src_ventas_det AS
    SELECT * FROM read_csv_auto('datos/ventas_detalle.csv', header=true);

CREATE OR REPLACE VIEW src_productos AS
    SELECT * FROM read_csv_auto('datos/productos.csv', header=true);

CREATE OR REPLACE VIEW src_tiendas AS
    SELECT * FROM read_csv_auto('datos/tiendas.csv', header=true);

CREATE OR REPLACE VIEW src_clientes AS
    SELECT * FROM read_csv('datos/clientes.csv',
        header=true, types={'nro_documento': 'VARCHAR'});

CREATE OR REPLACE VIEW src_promos AS
    SELECT * FROM read_csv_auto('datos/promociones.csv', header=true);

CREATE OR REPLACE VIEW src_inventario AS
    SELECT * FROM read_csv_auto('datos/inventario_cierre_mensual.csv', header=true);
""")

subtitulo("1.1 Conteo de filas por fuente")
df = q("""
SELECT 'ventas_cabecera' AS fuente, COUNT(*) AS filas FROM src_ventas_cab
UNION ALL SELECT 'ventas_detalle', COUNT(*) FROM src_ventas_det
UNION ALL SELECT 'productos',      COUNT(*) FROM src_productos
UNION ALL SELECT 'tiendas',        COUNT(*) FROM src_tiendas
UNION ALL SELECT 'clientes',       COUNT(*) FROM src_clientes
UNION ALL SELECT 'promociones',    COUNT(*) FROM src_promos
UNION ALL SELECT 'inventario',     COUNT(*) FROM src_inventario
ORDER BY fuente;
""")
_cifras["conteo_fuentes"] = dict(zip(df["fuente"], df["filas"].astype(int)))


# ---------------------------------------------------------------------------
# PASO 2: perfilado de las fuentes
# ---------------------------------------------------------------------------

titulo("PASO 2: PERFILADO DE LAS FUENTES")

subtitulo("2.1 Como estan escritas las categorias")
df = q("""
SELECT categoria, COUNT(*) AS productos
FROM   src_productos
GROUP BY categoria
ORDER BY categoria;
""")
_cifras["categorias_crudas"] = int(len(df))
_cifras["tabla_categorias_crudas"] = df.astype(str).values.tolist()

subtitulo("2.2 Claves duplicadas en el maestro de productos")
df = q("""
SELECT sku, COUNT(*) AS veces
FROM   src_productos
GROUP BY sku
HAVING COUNT(*) > 1;
""")
_cifras["skus_duplicados"] = df["sku"].tolist()

subtitulo("2.3 Datos obligatorios faltantes: productos sin costo")
df = q("""
SELECT sku, nombre_producto, precio_lista, costo_unitario
FROM   src_productos
WHERE  costo_unitario IS NULL;
""")
_cifras["productos_sin_costo"] = df["sku"].tolist()

subtitulo("2.4 Comprobantes sin cliente identificado")
df = q("""
SELECT COUNT(*) AS comprobantes_sin_cliente,
       ROUND(100.0 * COUNT(*) /
            (SELECT COUNT(*) FROM src_ventas_cab), 1) AS pct
FROM   src_ventas_cab
WHERE  nro_documento_cliente IS NULL;
""")
_cifras["comprobantes_sin_cliente"] = int(df["comprobantes_sin_cliente"][0])
_cifras["pct_comprobantes_sin_cliente"] = float(df["pct"][0])

subtitulo("2.5 Periodo cubierto por los datos")
df = q("""
SELECT MIN(fecha_emision) AS desde,
       MAX(fecha_emision) AS hasta,
       COUNT(DISTINCT fecha_emision) AS dias_con_venta
FROM   src_ventas_cab;
""")
_cifras["periodo_desde"] = str(df["desde"][0])
_cifras["periodo_hasta"] = str(df["hasta"][0])
_cifras["dias_con_venta"] = int(df["dias_con_venta"][0])


# ---------------------------------------------------------------------------
# PASO 4: construccion de la dimension tiempo
# (el paso 3 es de diseno, se documenta en el informe)
# ---------------------------------------------------------------------------

titulo("PASO 4: DIMENSION TIEMPO")

# La dimension tiempo se genera por adelantado; nunca se deriva de las fechas
# presentes en el hecho. Necesitamos todos los dias del calendario, incluso
# aquellos sin ninguna venta, para que las series temporales no salten dias.
con.execute("""
CREATE OR REPLACE TABLE dim_tiempo AS
WITH calendario AS (
    SELECT CAST(RANGE AS DATE) AS fecha
    FROM RANGE(DATE '2025-01-01', DATE '2027-01-01', INTERVAL 1 DAY)
)
SELECT CAST(strftime(fecha, '%Y%m%d') AS INTEGER) AS id_tiempo,
       fecha,
       YEAR(fecha)                       AS anio,
       QUARTER(fecha)                    AS trimestre,
       'T' || QUARTER(fecha)             AS nombre_trimestre,
       MONTH(fecha)                      AS mes,
       strftime(fecha, '%Y-%m')          AS anio_mes,
       CASE MONTH(fecha)
           WHEN 1 THEN 'Enero'      WHEN 2  THEN 'Febrero'
           WHEN 3 THEN 'Marzo'      WHEN 4  THEN 'Abril'
           WHEN 5 THEN 'Mayo'       WHEN 6  THEN 'Junio'
           WHEN 7 THEN 'Julio'      WHEN 8  THEN 'Agosto'
           WHEN 9 THEN 'Setiembre'  WHEN 10 THEN 'Octubre'
           WHEN 11 THEN 'Noviembre' ELSE 'Diciembre'
       END                               AS nombre_mes,
       WEEKOFYEAR(fecha)                 AS semana_iso,
       DAY(fecha)                        AS dia,
       DAYOFWEEK(fecha)                  AS dia_semana,
       CASE DAYOFWEEK(fecha)
           WHEN 0 THEN 'Domingo'   WHEN 1 THEN 'Lunes'
           WHEN 2 THEN 'Martes'    WHEN 3 THEN 'Miercoles'
           WHEN 4 THEN 'Jueves'    WHEN 5 THEN 'Viernes'
           ELSE 'Sabado'
       END                               AS nombre_dia,
       CASE WHEN DAYOFWEEK(fecha) IN (0, 6) THEN 'S' ELSE 'N' END AS es_fin_semana,
       -- Feriados nacionales del Peru: atributo del calendario del negocio
       -- que ningun sistema fuente proporciona. Lo aporta el almacen.
       CASE WHEN strftime(fecha, '%m-%d') IN
            ('01-01','05-01','06-29','07-28','07-29','08-30',
             '10-08','11-01','12-08','12-25')
            THEN 'S' ELSE 'N' END        AS es_feriado
FROM calendario;
""")

subtitulo("4.1 Control de la dimension tiempo")
df = q("""SELECT COUNT(*) AS filas, MIN(fecha) AS desde,
                 MAX(fecha) AS hasta FROM dim_tiempo""")
_cifras["dim_tiempo_filas"] = int(df["filas"][0])


# ---------------------------------------------------------------------------
# PASO 5: construccion de las dimensiones restantes
# ---------------------------------------------------------------------------

titulo("PASO 5: DIMENSIONES PRODUCTO, TIENDA, CLIENTE, PROMOCION Y TRANSACCION")

# Dimension Producto: aqui se aplican las tres decisiones derivadas del
# perfilado: conformar las categorias, eliminar el SKU duplicado e imputar
# el costo faltante.
con.execute("""
CREATE OR REPLACE TABLE dim_producto AS
WITH limpio AS (
    SELECT sku,
           TRIM(nombre_producto) AS nombre_producto,
           TRIM(marca)           AS marca,
           TRIM(subcategoria)    AS subcategoria,
           -- CONFORMADO: una sola forma de escribir cada categoria.
           -- Quitamos espacios y normalizamos a formato Titulo.
           UPPER(SUBSTR(TRIM(categoria), 1, 1)) ||
           LOWER(SUBSTR(TRIM(categoria), 2))    AS categoria,
           TRIM(linea)           AS linea,
           unidad_medida,
           precio_lista,
           -- IMPUTACION: si falta el costo, lo estimamos al 72 % del precio
           -- y lo marcamos, para no ocultar que es un valor calculado.
           COALESCE(costo_unitario, ROUND(precio_lista * 0.72, 2))
                                 AS costo_unitario,
           CASE WHEN costo_unitario IS NULL THEN 'S' ELSE 'N' END
                                 AS costo_imputado,
           -- DEDUPLICACION: numeramos las filas de cada SKU y nos quedamos
           -- solo con la primera.
           ROW_NUMBER() OVER (PARTITION BY sku ORDER BY nombre_producto) AS rn
    FROM src_productos
)
SELECT ROW_NUMBER() OVER (ORDER BY sku) AS id_producto,  -- clave subrogada
       sku, nombre_producto, marca, subcategoria, categoria, linea,
       unidad_medida, precio_lista, costo_unitario, costo_imputado
FROM   limpio
WHERE  rn = 1;

-- Fila de valor desconocido: sin ella se pierden hechos en las uniones.
INSERT INTO dim_producto VALUES
 (-1, 'N/D', 'No determinado', 'No determinada', 'No determinada',
  'No determinada', 'No determinada', 'N/D', 0, 0, 'N');
""")

subtitulo("5.1 Verificacion del conformado de categorias")
df = q("""
SELECT categoria, COUNT(*) AS productos
FROM   dim_producto
WHERE  id_producto <> -1
GROUP BY categoria
ORDER BY categoria;
""")
_cifras["categorias_conformadas"] = int(len(df))
_cifras["tabla_categorias_conformadas"] = df.astype(str).values.tolist()

con.execute("""
CREATE OR REPLACE TABLE dim_tienda AS
SELECT ROW_NUMBER() OVER (ORDER BY codigo_tienda) AS id_tienda,
       codigo_tienda, nombre_tienda, formato, distrito, zona_comercial,
       ciudad, region, fecha_apertura, metros_cuadrados
FROM   src_tiendas;

INSERT INTO dim_tienda VALUES
 (-1, 'N/D', 'No determinado', 'No determinado', 'No determinado',
  'No determinada', 'No determinada', 'No determinada', NULL, 0);

CREATE OR REPLACE TABLE dim_cliente AS
SELECT ROW_NUMBER() OVER (ORDER BY nro_documento) AS id_cliente,
       nro_documento, nombre_cliente, segmento, tiene_tarjeta,
       distrito_residencia, fecha_alta
FROM   src_clientes;

-- Esta fila representa la venta sin cliente identificado: casi el 39 %.
INSERT INTO dim_cliente VALUES
 (-1, 'N/D', 'Cliente no identificado', 'No identificado', 'N',
  'No determinado', NULL);

CREATE OR REPLACE TABLE dim_promocion AS
SELECT ROW_NUMBER() OVER (ORDER BY codigo_promocion) AS id_promocion,
       codigo_promocion, nombre_promocion, tipo_promocion,
       fecha_inicio, fecha_fin, descuento_pct
FROM   src_promos;

INSERT INTO dim_promocion VALUES
 (-1, 'N/D', 'No determinada', 'No determinada', NULL, NULL, 0);

-- DIMENSION BASURA: combina indicadores de baja cardinalidad.
CREATE OR REPLACE TABLE dim_transaccion AS
SELECT ROW_NUMBER() OVER (ORDER BY tipo_comprobante, forma_pago)
           AS id_transaccion,
       tipo_comprobante, forma_pago,
       CASE WHEN forma_pago LIKE 'Tarjeta%' THEN 'S' ELSE 'N' END
           AS es_pago_con_tarjeta
FROM   (SELECT DISTINCT tipo_comprobante, forma_pago FROM src_ventas_cab);

INSERT INTO dim_transaccion VALUES (-1, 'N/D', 'No determinada', 'N');
""")

subtitulo("5.2 Cifras de control de las dimensiones")
df = q("""
SELECT 'dim_tiempo' AS dimension, COUNT(*) AS filas FROM dim_tiempo
UNION ALL SELECT 'dim_producto',    COUNT(*) FROM dim_producto
UNION ALL SELECT 'dim_tienda',      COUNT(*) FROM dim_tienda
UNION ALL SELECT 'dim_cliente',     COUNT(*) FROM dim_cliente
UNION ALL SELECT 'dim_promocion',   COUNT(*) FROM dim_promocion
UNION ALL SELECT 'dim_transaccion', COUNT(*) FROM dim_transaccion
ORDER BY dimension;
""")
_cifras["control_dimensiones"] = dict(zip(df["dimension"], df["filas"].astype(int)))


# ---------------------------------------------------------------------------
# PASO 6: carga de la tabla de hechos
# ---------------------------------------------------------------------------

titulo("PASO 6: CARGA DE HECHO_VENTAS")

# Busqueda de claves (key lookup): cada clave natural del origen se
# reemplaza por la clave subrogada de la dimension.
#   - INNER JOIN con dim_tiempo: toda venta tiene fecha y el calendario
#     cubre todo el periodo, la union nunca falla.
#   - LEFT JOIN + COALESCE(clave, -1) con las demas: si la clave natural
#     no existe o viene vacia, conservamos el hecho y lo asociamos a la
#     fila de valor desconocido. Un INNER JOIN aqui eliminaria el 39 %
#     de las ventas.
con.execute("""
CREATE OR REPLACE TABLE hecho_ventas AS
SELECT
    ROW_NUMBER() OVER (ORDER BY c.nro_comprobante, d.nro_linea)
        AS id_venta_linea,
    t.id_tiempo,
    COALESCE(p.id_producto,    -1) AS id_producto,
    COALESCE(ti.id_tienda,     -1) AS id_tienda,
    COALESCE(cl.id_cliente,    -1) AS id_cliente,
    COALESCE(pr.id_promocion,  -1) AS id_promocion,
    COALESCE(tr.id_transaccion,-1) AS id_transaccion,
    c.nro_comprobante,                        -- dimension degenerada
    -- Medidas, todas al grano de linea de comprobante:
    d.cantidad,
    d.importe_bruto,
    d.importe_descuento,
    ROUND(d.importe_bruto - d.importe_descuento, 2)      AS importe_neto,
    ROUND(d.cantidad * p.costo_unitario, 2)              AS costo_venta,
    ROUND(d.importe_bruto - d.importe_descuento
          - d.cantidad * p.costo_unitario, 2)            AS margen_bruto
FROM       src_ventas_det   d
INNER JOIN src_ventas_cab   c  ON d.nro_comprobante   = c.nro_comprobante
INNER JOIN dim_tiempo       t  ON t.fecha             = c.fecha_emision
LEFT  JOIN dim_producto     p  ON p.sku               = d.sku
LEFT  JOIN dim_tienda       ti ON ti.codigo_tienda    = c.codigo_tienda
LEFT  JOIN dim_cliente      cl ON cl.nro_documento    = c.nro_documento_cliente
LEFT  JOIN dim_promocion    pr ON pr.codigo_promocion = d.codigo_promocion
LEFT  JOIN dim_transaccion  tr ON tr.tipo_comprobante = c.tipo_comprobante
                              AND tr.forma_pago       = c.forma_pago;
""")


# ---------------------------------------------------------------------------
# PASO 7: verificacion de la carga
# ---------------------------------------------------------------------------

titulo("PASO 7: VERIFICACION DE LA CARGA")

subtitulo("7.1 Cuadre de filas y de importes")
df = q("""
SELECT COUNT(*)                                        AS filas_hecho,
       (SELECT COUNT(*) FROM src_ventas_det)           AS filas_origen,
       ROUND(SUM(importe_bruto), 2)                    AS bruto_datamart,
       ROUND((SELECT SUM(importe_bruto) FROM src_ventas_det), 2)
                                                       AS bruto_origen,
       ROUND(SUM(importe_descuento), 2)                AS descuento_datamart,
       ROUND(SUM(importe_neto), 2)                     AS neto_datamart,
       ROUND(SUM(importe_bruto)
             - (SELECT SUM(importe_bruto) FROM src_ventas_det), 2)
                                                       AS diferencia
FROM   hecho_ventas;
""")
_cifras["cuadre"] = {k: (float(v) if v is not None else None)
                     for k, v in df.iloc[0].astype(float).items()}

subtitulo("7.2 Busqueda de hechos huerfanos (debe dar cero en todas)")
df = q("""
SELECT 'producto' AS dimension, COUNT(*) AS huerfanos
FROM       hecho_ventas h
LEFT  JOIN dim_producto p ON h.id_producto = p.id_producto
WHERE  p.id_producto IS NULL
UNION ALL
SELECT 'tienda', COUNT(*) FROM hecho_ventas h
LEFT  JOIN dim_tienda t ON h.id_tienda = t.id_tienda
WHERE  t.id_tienda IS NULL
UNION ALL
SELECT 'cliente', COUNT(*) FROM hecho_ventas h
LEFT  JOIN dim_cliente c ON h.id_cliente = c.id_cliente
WHERE  c.id_cliente IS NULL
UNION ALL
SELECT 'tiempo', COUNT(*) FROM hecho_ventas h
LEFT  JOIN dim_tiempo t ON h.id_tiempo = t.id_tiempo
WHERE  t.id_tiempo IS NULL;
""")
_cifras["huerfanos"] = dict(zip(df["dimension"], df["huerfanos"].astype(int)))

subtitulo("7.3 Peso de los valores desconocidos")
df = q("""
SELECT COUNT(*)                                          AS lineas_totales,
       SUM(CASE WHEN id_cliente = -1 THEN 1 ELSE 0 END)  AS lineas_sin_cliente,
       ROUND(100.0 * SUM(CASE WHEN id_cliente = -1 THEN 1 ELSE 0 END)
             / COUNT(*), 1)                              AS pct_sin_cliente
FROM   hecho_ventas;
""")
_cifras["pct_lineas_sin_cliente"] = float(df["pct_sin_cliente"][0])
_cifras["lineas_sin_cliente"] = int(df["lineas_sin_cliente"][0])


# ---------------------------------------------------------------------------
# PASO 8: operaciones OLAP sobre el datamart
# ---------------------------------------------------------------------------

titulo("PASO 8: OPERACIONES OLAP")

subtitulo("8.1 ROLL-UP: agregacion con subtotales por region y categoria (2026)")
# El porcentaje de margen se calcula como division de dos sumas, nunca como
# promedio de los porcentajes de cada fila: es una medida no aditiva.
df = q("""
SELECT COALESCE(ti.region, 'TOTAL GENERAL')      AS region,
       COALESCE(p.categoria, '  Subtotal region') AS categoria,
       ROUND(SUM(h.importe_neto), 2)             AS venta_neta,
       ROUND(SUM(h.margen_bruto), 2)             AS margen,
       ROUND(100.0 * SUM(h.margen_bruto)
             / NULLIF(SUM(h.importe_neto), 0), 1) AS pct_margen
FROM       hecho_ventas h
INNER JOIN dim_tienda   ti ON h.id_tienda   = ti.id_tienda
INNER JOIN dim_producto p  ON h.id_producto = p.id_producto
INNER JOIN dim_tiempo   t  ON h.id_tiempo   = t.id_tiempo
WHERE  t.anio = 2026
GROUP BY ROLLUP (ti.region, p.categoria)
ORDER BY region, categoria;
""")
_cifras["rollup"] = df.astype(str).values.tolist()

subtitulo("8.1b Comprobacion: promedio de porcentajes vs. division de sumas")
df = q("""
WITH por_producto AS (
    SELECT p.id_producto,
           SUM(h.importe_neto) AS neto,
           SUM(h.margen_bruto) AS margen
    FROM       hecho_ventas h
    INNER JOIN dim_producto p ON h.id_producto = p.id_producto
    INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
    WHERE  t.anio = 2026
    GROUP BY p.id_producto
)
SELECT ROUND(AVG(100.0 * margen / NULLIF(neto, 0)), 2) AS promedio_de_pct,
       ROUND(100.0 * SUM(margen) / NULLIF(SUM(neto), 0), 2) AS pct_correcto
FROM   por_producto;
""")
_cifras["no_aditiva"] = {"promedio_de_pct": float(df["promedio_de_pct"][0]),
                         "pct_correcto": float(df["pct_correcto"][0])}

subtitulo("8.2 DRILL-DOWN: de categoria anual a mes y subcategoria (Lacteos 2026)")
df = q("""
SELECT t.anio_mes, p.subcategoria,
       ROUND(SUM(h.importe_neto), 2) AS venta_neta
FROM       hecho_ventas h
INNER JOIN dim_producto p ON h.id_producto = p.id_producto
INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
WHERE  p.categoria = 'Lacteos' AND t.anio = 2026
GROUP BY t.anio_mes, p.subcategoria
ORDER BY t.anio_mes, p.subcategoria;
""")
_cifras["drilldown"] = df.astype(str).values.tolist()

subtitulo("8.3 SLICE: fijamos una sola dimension (anio 2026)")
df = q("""
SELECT ti.region, ROUND(SUM(h.importe_neto), 2) AS venta_neta
FROM       hecho_ventas h
INNER JOIN dim_tienda ti ON h.id_tienda = ti.id_tienda
INNER JOIN dim_tiempo t  ON h.id_tiempo = t.id_tiempo
WHERE  t.anio = 2026
GROUP BY ti.region
ORDER BY venta_neta DESC;
""")
_cifras["slice"] = df.astype(str).values.tolist()

subtitulo("8.3b DICE: restringimos zona, categoria y trimestre simultaneamente")
# Nota: se incluye t.mes en el GROUP BY aunque no se muestre, porque ordenar
# por nombre_mes daria un orden alfabetico en lugar del cronologico.
df = q("""
SELECT ti.zona_comercial, p.categoria, t.nombre_mes,
       ROUND(SUM(h.importe_neto), 2) AS venta_neta
FROM       hecho_ventas h
INNER JOIN dim_tienda   ti ON h.id_tienda   = ti.id_tienda
INNER JOIN dim_producto p  ON h.id_producto = p.id_producto
INNER JOIN dim_tiempo   t  ON h.id_tiempo   = t.id_tiempo
WHERE  ti.zona_comercial IN ('Lima Norte', 'Lima Sur')
  AND  p.categoria       IN ('Lacteos', 'Bebidas')
  AND  t.anio = 2026 AND t.trimestre = 2
GROUP BY ti.zona_comercial, p.categoria, t.nombre_mes, t.mes
ORDER BY ti.zona_comercial, p.categoria, t.mes;
""")
_cifras["dice"] = df.astype(str).values.tolist()

subtitulo("8.4 PIVOT: categorias en filas, trimestres en columnas (2026)")
df = q("""
SELECT * FROM (
    PIVOT (
        SELECT p.categoria, t.nombre_trimestre, h.importe_neto
        FROM       hecho_ventas h
        INNER JOIN dim_producto p ON h.id_producto = p.id_producto
        INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
        WHERE  t.anio = 2026
    ) ON nombre_trimestre USING ROUND(SUM(importe_neto), 2)
      GROUP BY categoria
) ORDER BY categoria;
""")
_cifras["pivot"] = [list(df.columns)] + df.astype(str).values.tolist()

subtitulo("8.5 Comparativo contra el mismo periodo del anio anterior")
# El LAG se calcula en una CTE separada y el filtro por anio se aplica
# despues. Si el WHERE anio = 2026 fuera junto a la ventana, las filas de
# 2025 desaparecerian antes de evaluarla y la columna del anio anterior
# saldria vacia.
df = q("""
WITH venta_mensual AS (
    SELECT t.anio, t.mes, p.categoria,
           SUM(h.importe_neto) AS venta_neta
    FROM       hecho_ventas h
    INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
    INNER JOIN dim_producto p ON h.id_producto = p.id_producto
    GROUP BY t.anio, t.mes, p.categoria
),
con_anterior AS (
    SELECT anio, mes, categoria, venta_neta,
           LAG(venta_neta) OVER (PARTITION BY categoria, mes ORDER BY anio)
               AS venta_anio_anterior
    FROM venta_mensual
)
SELECT anio, mes, categoria,
       ROUND(venta_neta, 2)           AS venta_neta,
       ROUND(venta_anio_anterior, 2)  AS venta_anio_anterior,
       ROUND(100.0 * (venta_neta - venta_anio_anterior)
             / NULLIF(venta_anio_anterior, 0), 1) AS variacion_pct
FROM   con_anterior
WHERE  anio = 2026
ORDER BY categoria, mes;
""")
_cifras["interanual"] = df.astype(str).values.tolist()

subtitulo("8.6 Analisis del programa de fidelizacion")
df = q("""
SELECT t.anio_mes,
       ROUND(SUM(h.importe_neto), 2) AS venta_total,
       ROUND(SUM(CASE WHEN c.tiene_tarjeta = 'S'
                      THEN h.importe_neto ELSE 0 END), 2)
           AS venta_fidelizada,
       ROUND(100.0 * SUM(CASE WHEN c.tiene_tarjeta = 'S'
                              THEN h.importe_neto ELSE 0 END)
             / NULLIF(SUM(h.importe_neto), 0), 1) AS pct_fidelizada
FROM       hecho_ventas h
INNER JOIN dim_cliente c ON h.id_cliente = c.id_cliente
INNER JOIN dim_tiempo  t ON h.id_tiempo  = t.id_tiempo
GROUP BY t.anio_mes
ORDER BY t.anio_mes;
""")
_cifras["fidelizacion"] = df.astype(str).values.tolist()


# ---------------------------------------------------------------------------
# PREGUNTAS DE ANALISIS (seccion 10.7 de la guia)
# ---------------------------------------------------------------------------

titulo("PREGUNTAS DE ANALISIS")

subtitulo("P1. Region con mayor venta neta 2026 y categoria de mayor margen %")
df = q("""
SELECT ti.region,
       ROUND(SUM(h.importe_neto), 2) AS venta_neta,
       ROUND(100.0 * SUM(h.margen_bruto) / NULLIF(SUM(h.importe_neto),0), 2)
           AS pct_margen
FROM       hecho_ventas h
INNER JOIN dim_tienda ti ON h.id_tienda = ti.id_tienda
INNER JOIN dim_tiempo t  ON h.id_tiempo = t.id_tiempo
WHERE  t.anio = 2026
GROUP BY ti.region
ORDER BY venta_neta DESC;
""")
_cifras["p1_regiones"] = df.astype(str).values.tolist()

df = q("""
SELECT p.categoria,
       ROUND(SUM(h.importe_neto), 2) AS venta_neta,
       ROUND(100.0 * SUM(h.margen_bruto) / NULLIF(SUM(h.importe_neto),0), 2)
           AS pct_margen
FROM       hecho_ventas h
INNER JOIN dim_producto p ON h.id_producto = p.id_producto
INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
WHERE  t.anio = 2026
GROUP BY p.categoria
ORDER BY pct_margen DESC;
""")
_cifras["p1_categorias"] = df.astype(str).values.tolist()

subtitulo("P2. Fidelizacion: efecto de la fila de cliente no identificado")
df = q("""
SELECT ROUND(100.0 * SUM(CASE WHEN c.tiene_tarjeta = 'S'
                              THEN h.importe_neto ELSE 0 END)
             / NULLIF(SUM(h.importe_neto), 0), 2) AS pct_sobre_venta_total,
       ROUND(100.0 * SUM(CASE WHEN c.tiene_tarjeta = 'S'
                              THEN h.importe_neto ELSE 0 END)
             / NULLIF(SUM(CASE WHEN h.id_cliente <> -1
                               THEN h.importe_neto ELSE 0 END), 0), 2)
           AS pct_sobre_venta_identificada,
       ROUND(100.0 * SUM(CASE WHEN h.id_cliente = -1
                              THEN h.importe_neto ELSE 0 END)
             / NULLIF(SUM(h.importe_neto), 0), 2) AS pct_venta_no_identificada
FROM       hecho_ventas h
INNER JOIN dim_cliente c ON h.id_cliente = c.id_cliente;
""")
_cifras["p2"] = {k: float(v) for k, v in df.iloc[0].items()}

subtitulo("P3. Impacto de haber usado INNER JOIN con dim_cliente")
df = q("""
SELECT ROUND(SUM(importe_neto), 2)                       AS neto_con_left_join,
       ROUND(SUM(CASE WHEN id_cliente <> -1
                      THEN importe_neto ELSE 0 END), 2)  AS neto_con_inner_join,
       COUNT(*)                                          AS filas_con_left_join,
       SUM(CASE WHEN id_cliente <> -1 THEN 1 ELSE 0 END) AS filas_con_inner_join,
       ROUND(100.0 * SUM(CASE WHEN id_cliente = -1
                              THEN importe_neto ELSE 0 END)
             / SUM(importe_neto), 2)                     AS pct_venta_perdida
FROM   hecho_ventas;
""")
_cifras["p3"] = {k: float(v) for k, v in df.iloc[0].items()}

subtitulo("P4. Efecto de los dos productos con costo imputado sobre el margen")
df = q("""
SELECT p.categoria,
       ROUND(100.0 * SUM(h.margen_bruto)
             / NULLIF(SUM(h.importe_neto), 0), 2) AS pct_margen_reportado,
       ROUND(100.0 * SUM(CASE WHEN p.costo_imputado = 'N'
                              THEN h.margen_bruto ELSE 0 END)
             / NULLIF(SUM(CASE WHEN p.costo_imputado = 'N'
                               THEN h.importe_neto ELSE 0 END), 0), 2)
           AS pct_margen_sin_imputados,
       ROUND(100.0 * SUM(CASE WHEN p.costo_imputado = 'S'
                              THEN h.importe_neto ELSE 0 END)
             / NULLIF(SUM(h.importe_neto), 0), 2) AS pct_venta_imputada
FROM       hecho_ventas h
INNER JOIN dim_producto p ON h.id_producto = p.id_producto
GROUP BY p.categoria
HAVING SUM(CASE WHEN p.costo_imputado = 'S' THEN 1 ELSE 0 END) > 0
ORDER BY p.categoria;
""")
_cifras["p4"] = df.astype(str).values.tolist()


# ---------------------------------------------------------------------------
# SECCION 11: ACTIVIDAD PROPUESTA - HECHO_INVENTARIO Y DRILL-ACROSS
# ---------------------------------------------------------------------------

titulo("ACTIVIDAD PROPUESTA: HECHO_INVENTARIO Y DRILL-ACROSS")

# Grano: una fila por producto, por tienda y por cierre mensual.
# Tipo: tabla de hechos de instantanea periodica (periodic snapshot).
# Se reutilizan exclusivamente las dimensiones ya construidas: tiempo,
# tienda y producto. No se crea ninguna dimension nueva.
con.execute("""
CREATE OR REPLACE TABLE hecho_inventario AS
SELECT
    ROW_NUMBER() OVER (ORDER BY i.fecha_cierre, i.codigo_tienda, i.sku)
        AS id_inventario,
    t.id_tiempo,
    COALESCE(ti.id_tienda,  -1) AS id_tienda,
    COALESCE(p.id_producto, -1) AS id_producto,
    i.stock_unidades,                 -- medida semiaditiva
    i.valorizado_costo                -- medida semiaditiva
FROM       src_inventario i
INNER JOIN dim_tiempo    t  ON t.fecha          = i.fecha_cierre
LEFT  JOIN dim_tienda    ti ON ti.codigo_tienda = i.codigo_tienda
LEFT  JOIN dim_producto  p  ON p.sku            = i.sku;
""")

subtitulo("11.1 Cuadre de filas y de cierres mensuales")
df = q("""
SELECT COUNT(*)                                   AS filas_hecho,
       (SELECT COUNT(*) FROM src_inventario)      AS filas_origen,
       COUNT(DISTINCT id_tiempo)                  AS cierres_mensuales,
       ROUND(SUM(valorizado_costo), 2)            AS valorizado_total,
       ROUND((SELECT SUM(valorizado_costo) FROM src_inventario), 2)
                                                  AS valorizado_origen
FROM   hecho_inventario;
""")
_cifras["inv_cuadre"] = {k: float(v) for k, v in df.iloc[0].items()}

subtitulo("11.2 Huerfanos en hecho_inventario (debe dar cero)")
df = q("""
SELECT 'producto' AS dimension, COUNT(*) AS huerfanos
FROM       hecho_inventario h
LEFT  JOIN dim_producto p ON h.id_producto = p.id_producto
WHERE  p.id_producto IS NULL
UNION ALL
SELECT 'tienda', COUNT(*) FROM hecho_inventario h
LEFT  JOIN dim_tienda t ON h.id_tienda = t.id_tienda
WHERE  t.id_tienda IS NULL
UNION ALL
SELECT 'tiempo', COUNT(*) FROM hecho_inventario h
LEFT  JOIN dim_tiempo t ON h.id_tiempo = t.id_tiempo
WHERE  t.id_tiempo IS NULL;
""")
_cifras["inv_huerfanos"] = dict(zip(df["dimension"], df["huerfanos"].astype(int)))

subtitulo("11.3 Demostracion de la semiaditividad del stock (2025)")
# Primera consulta: sumar el stock a lo largo del anio. La cifra no tiene
# sentido de negocio, porque suma doce fotos del mismo inventario.
df = q("""
SELECT ROUND(SUM(h.stock_unidades), 0) AS suma_incorrecta_del_anio
FROM       hecho_inventario h
INNER JOIN dim_tiempo t ON h.id_tiempo = t.id_tiempo
WHERE  t.anio = 2025;
""")
_cifras["semi_incorrecta"] = float(df["suma_incorrecta_del_anio"][0])

# Tratamiento correcto: el stock se suma libremente sobre producto y tienda,
# pero sobre el tiempo se toma el ultimo cierre o el promedio de los cierres.
df = q("""
WITH por_cierre AS (
    SELECT t.id_tiempo, SUM(h.stock_unidades) AS stock_cierre
    FROM       hecho_inventario h
    INNER JOIN dim_tiempo t ON h.id_tiempo = t.id_tiempo
    WHERE  t.anio = 2025
    GROUP BY t.id_tiempo
)
SELECT ROUND(AVG(stock_cierre), 0) AS stock_promedio_mensual,
       ROUND(MAX(stock_cierre) FILTER (WHERE id_tiempo =
             (SELECT MAX(id_tiempo) FROM por_cierre)), 0) AS stock_ultimo_cierre
FROM   por_cierre;
""")
_cifras["semi_correcta"] = {k: float(v) for k, v in df.iloc[0].items()}

subtitulo("11.4 DRILL-ACROSS: rotacion por mes y categoria (1er semestre 2026)")
# Se agrega cada hecho por separado al mismo nivel de detalle (mes y
# categoria) y recien despues se unen por sus atributos conformados. Unir
# las dos tablas de hechos directamente produciria un producto cartesiano.
df = q("""
WITH venta AS (
    SELECT t.anio_mes, p.categoria,
           SUM(h.cantidad) AS unidades_vendidas
    FROM       hecho_ventas h
    INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
    INNER JOIN dim_producto p ON h.id_producto = p.id_producto
    WHERE  t.anio = 2026 AND t.mes <= 6
    GROUP BY t.anio_mes, p.categoria
),
stock AS (
    SELECT t.anio_mes, p.categoria,
           SUM(h.stock_unidades) AS stock_cierre
    FROM       hecho_inventario h
    INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
    INNER JOIN dim_producto p ON h.id_producto = p.id_producto
    WHERE  t.anio = 2026 AND t.mes <= 6
    GROUP BY t.anio_mes, p.categoria
)
SELECT v.anio_mes, v.categoria,
       v.unidades_vendidas,
       s.stock_cierre,
       ROUND(1.0 * v.unidades_vendidas / NULLIF(s.stock_cierre, 0), 3)
           AS indice_rotacion
FROM       venta v
INNER JOIN stock s ON v.anio_mes = s.anio_mes
                  AND v.categoria = s.categoria
ORDER BY v.anio_mes, v.categoria;
""")
_cifras["drill_across"] = df.astype(str).values.tolist()

subtitulo("11.5 Las tres categorias de menor rotacion (1er semestre 2026)")
df = q("""
WITH venta AS (
    SELECT p.categoria, SUM(h.cantidad) AS unidades_vendidas
    FROM       hecho_ventas h
    INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
    INNER JOIN dim_producto p ON h.id_producto = p.id_producto
    WHERE  t.anio = 2026 AND t.mes <= 6
    GROUP BY p.categoria
),
stock AS (
    SELECT p.categoria,
           SUM(h.stock_unidades) / COUNT(DISTINCT h.id_tiempo)
               AS stock_promedio
    FROM       hecho_inventario h
    INNER JOIN dim_tiempo   t ON h.id_tiempo   = t.id_tiempo
    INNER JOIN dim_producto p ON h.id_producto = p.id_producto
    WHERE  t.anio = 2026 AND t.mes <= 6
    GROUP BY p.categoria
)
SELECT v.categoria,
       v.unidades_vendidas,
       ROUND(s.stock_promedio, 0) AS stock_promedio_mensual,
       ROUND(1.0 * v.unidades_vendidas / NULLIF(s.stock_promedio, 0), 3)
           AS indice_rotacion
FROM       venta v
INNER JOIN stock s ON v.categoria = s.categoria
ORDER BY indice_rotacion ASC;
""")
_cifras["rotacion_categorias"] = df.astype(str).values.tolist()


# ---------------------------------------------------------------------------
# Persistencia de los resultados para el informe
# ---------------------------------------------------------------------------

with open(os.path.join(SALIDAS, "resultados.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(_bitacora))

with open(os.path.join(SALIDAS, "cifras.json"), "w", encoding="utf-8") as f:
    json.dump(_cifras, f, ensure_ascii=False, indent=2, default=str)

con.close()

print("\n\nProceso terminado. Resultados en salidas/resultados.txt y "
      "salidas/cifras.json. Base: lab02.duckdb")
