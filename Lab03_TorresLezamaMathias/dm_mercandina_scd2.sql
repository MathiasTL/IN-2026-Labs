USE dm_mercandina;

-- ================= SCD TIPO 2: dim_producto =================
-- PASO 1: cerrar la version vigente
UPDATE dim_producto d
JOIN   stg_producto_cambio ch ON ch.cod_producto = d.producto_id
SET    d.fecha_fin_vig = DATE_SUB(STR_TO_DATE(ch.fecha_cambio, '%Y-%m-%d'),
                                    INTERVAL 1 DAY),
       d.es_vigente    = 0
WHERE  d.es_vigente = 1;

-- PASO 2: insertar la nueva version
INSERT INTO dim_producto
  (producto_id, nombre_producto, marca, categoria, subcategoria,
   unidad_medida, es_marca_propia, precio_lista, costo_estandar,
   fecha_inicio_vig, fecha_fin_vig, es_vigente)
SELECT ch.cod_producto, ch.nombre_producto, ch.marca, ch.categoria,
       ch.subcategoria, ch.unidad_medida,
       CAST(ch.es_marca_propia AS UNSIGNED),
       CAST(ch.precio_lista AS DECIMAL(12,2)),
       CAST(ch.costo_unitario AS DECIMAL(12,2)),
       STR_TO_DATE(ch.fecha_cambio, '%Y-%m-%d'), '9999-12-31', 1
FROM stg_producto_cambio ch;

-- ================= SCD TIPO 2: dim_tienda =================
-- PASO 1: cerrar la version vigente
UPDATE dim_tienda d
JOIN   stg_tienda_cambio ch ON ch.cod_tienda = d.tienda_id
SET    d.fecha_fin_vig = DATE_SUB(STR_TO_DATE(ch.fecha_cambio, '%Y-%m-%d'),
                                    INTERVAL 1 DAY),
       d.es_vigente    = 0
WHERE  d.es_vigente = 1;

-- PASO 2: insertar la nueva version
INSERT INTO dim_tienda
  (tienda_id, nombre_tienda, formato, distrito, ciudad, region,
   area_m2, fecha_apertura, fecha_inicio_vig, fecha_fin_vig, es_vigente)
SELECT ch.cod_tienda, ch.nombre_tienda, ch.formato, ch.distrito, ch.ciudad,
       ch.region, CAST(ch.area_m2 AS DECIMAL(10,2)),
       STR_TO_DATE(ch.fecha_apertura, '%Y-%m-%d'),
       STR_TO_DATE(ch.fecha_cambio, '%Y-%m-%d'), '9999-12-31', 1
FROM stg_tienda_cambio ch;

-- ================= SCD TIPO 2: dim_cliente =================
-- PASO 1: cerrar la version vigente
UPDATE dim_cliente d
JOIN   stg_cliente_cambio ch ON ch.doc_cliente = d.cliente_id
SET    d.fecha_fin_vig = DATE_SUB(STR_TO_DATE(ch.fecha_cambio, '%Y-%m-%d'),
                                    INTERVAL 1 DAY),
       d.es_vigente    = 0
WHERE  d.es_vigente = 1;

-- PASO 2: insertar la nueva version
INSERT INTO dim_cliente
  (cliente_id, nombre, segmento, distrito, ciudad, fecha_alta,
   fecha_inicio_vig, fecha_fin_vig, es_vigente)
SELECT ch.doc_cliente, ch.nombre, ch.segmento, ch.distrito, ch.ciudad,
       STR_TO_DATE(ch.fecha_alta, '%Y-%m-%d'),
       STR_TO_DATE(ch.fecha_cambio, '%Y-%m-%d'), '9999-12-31', 1
FROM stg_cliente_cambio ch;

-- ================= VERIFICACION (Tabla 6 de la guia) =================
-- Los conteos incluyen las filas especiales (-1/-2): no se ven afectadas
-- por el SCD Tipo 2, pero la Tabla 6 de la guia las suma en el total.
SELECT 'dim_producto' AS dimension,
       COUNT(*) AS filas_totales,
       SUM(es_vigente = 1) AS filas_vigentes,
       SUM(es_vigente = 0) AS filas_cerradas
FROM dim_producto
UNION ALL
SELECT 'dim_tienda', COUNT(*), SUM(es_vigente = 1), SUM(es_vigente = 0)
FROM dim_tienda
UNION ALL
SELECT 'dim_cliente', COUNT(*), SUM(es_vigente = 1), SUM(es_vigente = 0)
FROM dim_cliente;

-- Verificacion sobre un producto reclasificado (Figura 15)
SELECT producto_key, producto_id, categoria, subcategoria,
       fecha_inicio_vig, fecha_fin_vig, es_vigente
FROM   dim_producto
WHERE  producto_id = (SELECT cod_producto FROM stg_producto_cambio LIMIT 1)
ORDER BY fecha_inicio_vig;
