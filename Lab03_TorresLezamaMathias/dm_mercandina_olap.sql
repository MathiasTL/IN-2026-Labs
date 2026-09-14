USE dm_mercandina;

-- (1) ROLL-UP: del detalle mensual al total trimestral por ciudad
SELECT t.anio, t.trimestre, s.ciudad, SUM(f.importe_venta) AS venta
FROM   fact_venta f
JOIN   dim_tiempo t ON t.tiempo_key = f.tiempo_key
JOIN   dim_tienda s ON s.tienda_key = f.tienda_key
GROUP BY t.anio, t.trimestre, s.ciudad
ORDER BY 1, 2, 4 DESC;

-- (2) DRILL-DOWN: de categoria a subcategoria dentro de un mes
SELECT p.categoria, p.subcategoria, SUM(f.importe_venta) AS venta
FROM   fact_venta f
JOIN   dim_tiempo   t ON t.tiempo_key   = f.tiempo_key
JOIN   dim_producto p ON p.producto_key = f.producto_key
WHERE  t.anio_mes = '2026-05'
GROUP BY p.categoria, p.subcategoria
ORDER BY p.categoria, venta DESC;

-- (3) SLICE: se fija una sola dimension
SELECT t.anio_mes, SUM(f.importe_venta) AS venta
FROM   fact_venta f
JOIN   dim_tiempo t ON t.tiempo_key = f.tiempo_key
JOIN   dim_tienda s ON s.tienda_key = f.tienda_key
WHERE  s.ciudad = 'Arequipa'
GROUP BY t.anio_mes ORDER BY 1;

-- (4) DICE: se restringen varias dimensiones a la vez
SELECT s.ciudad, p.categoria, SUM(f.importe_venta) AS venta
FROM   fact_venta f
JOIN   dim_tiempo   t ON t.tiempo_key   = f.tiempo_key
JOIN   dim_tienda   s ON s.tienda_key   = f.tienda_key
JOIN   dim_producto p ON p.producto_key = f.producto_key
WHERE  s.ciudad IN ('Lima', 'Cusco')
  AND  p.categoria IN ('Bebidas', 'Snacks', 'Lacteos')
  AND  t.anio_mes BETWEEN '2026-04' AND '2026-06'
GROUP BY s.ciudad, p.categoria;

-- (5) PIVOT: los meses pasan de filas a columnas
SELECT s.ciudad,
  SUM(CASE WHEN t.anio_mes = '2026-01' THEN f.importe_venta END) AS ene,
  SUM(CASE WHEN t.anio_mes = '2026-02' THEN f.importe_venta END) AS feb,
  SUM(CASE WHEN t.anio_mes = '2026-03' THEN f.importe_venta END) AS mar,
  SUM(CASE WHEN t.anio_mes = '2026-04' THEN f.importe_venta END) AS abr,
  SUM(CASE WHEN t.anio_mes = '2026-05' THEN f.importe_venta END) AS may,
  SUM(CASE WHEN t.anio_mes = '2026-06' THEN f.importe_venta END) AS jun
FROM fact_venta f
JOIN dim_tiempo t ON t.tiempo_key = f.tiempo_key
JOIN dim_tienda s ON s.tienda_key = f.tienda_key
GROUP BY s.ciudad;

-- (6) DRILL-ACROSS: en la etapa 9 se resuelve con una sola tabla de hechos,
--     comparando el periodo con y sin promocion sobre la misma dimension
WITH con_promo AS (
  SELECT p.categoria, SUM(f.importe_venta) AS venta_promo
  FROM   fact_venta f JOIN dim_producto p ON p.producto_key = f.producto_key
  WHERE  f.promocion_key <> -2 GROUP BY p.categoria
), sin_promo AS (
  SELECT p.categoria, SUM(f.importe_venta) AS venta_normal
  FROM   fact_venta f JOIN dim_producto p ON p.producto_key = f.producto_key
  WHERE  f.promocion_key = -2 GROUP BY p.categoria
)
SELECT COALESCE(a.categoria, b.categoria) AS categoria,
       a.venta_promo, b.venta_normal,
       ROUND(100.0 * a.venta_promo /
             NULLIF(a.venta_promo + b.venta_normal, 0), 2) AS pct_promocionado
FROM   con_promo a LEFT JOIN sin_promo b ON a.categoria = b.categoria;

-- ================= MATERIALIZACION DEL CUBO =================
-- MySQL 8: agregados jerarquicos con WITH ROLLUP
SELECT COALESCE(t.anio_mes, '== TOTAL ==') AS periodo,
       COALESCE(s.ciudad,   '-- todas --') AS ciudad,
       ROUND(SUM(f.importe_venta), 2)      AS venta,
       GROUPING(s.ciudad)                  AS es_subtotal_periodo,
       GROUPING(t.anio_mes)                AS es_total_general
FROM   fact_venta f
JOIN   dim_tiempo t ON t.tiempo_key = f.tiempo_key
JOIN   dim_tienda s ON s.tienda_key = f.tienda_key
GROUP BY t.anio_mes, s.ciudad WITH ROLLUP;

-- Equivalente en PostgreSQL, SQL Server u Oracle (dejar comentado):
-- SELECT t.anio_mes, s.ciudad, SUM(f.importe_venta) AS venta
-- FROM   fact_venta f
-- JOIN   dim_tiempo t ON t.tiempo_key = f.tiempo_key
-- JOIN   dim_tienda s ON s.tienda_key = f.tienda_key
-- GROUP BY GROUPING SETS (
--   (t.anio_mes, s.ciudad),  -- venta mensual por ciudad
--   (t.anio_mes),            -- venta mensual total
--   (s.ciudad),              -- total general
--   () );
