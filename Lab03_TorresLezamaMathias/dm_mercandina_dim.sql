USE dm_mercandina;

-- ================= CARGA DEL AREA DE STAGING =================
LOAD DATA LOCAL INFILE '/Users/mathiastl/Courses/CICLO 8/IN/Lab03_TorresLezamaMathias/datos/productos.csv'
INTO TABLE stg_producto
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/mathiastl/Courses/CICLO 8/IN/Lab03_TorresLezamaMathias/datos/productos_cambios.csv'
INTO TABLE stg_producto_cambio
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/mathiastl/Courses/CICLO 8/IN/Lab03_TorresLezamaMathias/datos/tiendas.csv'
INTO TABLE stg_tienda
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/mathiastl/Courses/CICLO 8/IN/Lab03_TorresLezamaMathias/datos/tiendas_cambios.csv'
INTO TABLE stg_tienda_cambio
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/mathiastl/Courses/CICLO 8/IN/Lab03_TorresLezamaMathias/datos/clientes.csv'
INTO TABLE stg_cliente
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/mathiastl/Courses/CICLO 8/IN/Lab03_TorresLezamaMathias/datos/clientes_cambios.csv'
INTO TABLE stg_cliente_cambio
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/mathiastl/Courses/CICLO 8/IN/Lab03_TorresLezamaMathias/datos/promociones.csv'
INTO TABLE stg_promocion
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/mathiastl/Courses/CICLO 8/IN/Lab03_TorresLezamaMathias/datos/ventas.csv'
INTO TABLE stg_venta_pos
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- Verificacion de la carga (Figura 10 de la guia)
SELECT 'stg_producto'        AS tabla, COUNT(*) AS filas FROM stg_producto
UNION ALL SELECT 'stg_producto_cambio', COUNT(*) FROM stg_producto_cambio
UNION ALL SELECT 'stg_tienda',          COUNT(*) FROM stg_tienda
UNION ALL SELECT 'stg_tienda_cambio',   COUNT(*) FROM stg_tienda_cambio
UNION ALL SELECT 'stg_cliente',         COUNT(*) FROM stg_cliente
UNION ALL SELECT 'stg_cliente_cambio',  COUNT(*) FROM stg_cliente_cambio
UNION ALL SELECT 'stg_promocion',       COUNT(*) FROM stg_promocion
UNION ALL SELECT 'stg_venta_pos',       COUNT(*) FROM stg_venta_pos;

-- ================= ETAPA 4: DIMENSION TIEMPO =================
SET SESSION cte_max_recursion_depth = 5000;

INSERT INTO dim_tiempo
  (tiempo_key, fecha, anio, trimestre, mes, nombre_mes, anio_mes,
   dia_mes, dia_semana, nombre_dia, es_fin_semana, es_dia_pago)
WITH RECURSIVE seq AS (
  SELECT DATE('2024-01-01') AS f
  UNION ALL
  SELECT DATE_ADD(f, INTERVAL 1 DAY) FROM seq WHERE f < '2027-12-31'
)
SELECT
  CAST(DATE_FORMAT(f, '%Y%m%d') AS UNSIGNED),
  f,
  YEAR(f),
  QUARTER(f),
  MONTH(f),
  ELT(MONTH(f), 'Enero','Febrero','Marzo','Abril','Mayo','Junio',
                'Julio','Agosto','Setiembre','Octubre','Noviembre','Diciembre'),
  DATE_FORMAT(f, '%Y-%m'),
  DAYOFMONTH(f),
  WEEKDAY(f) + 1,
  ELT(WEEKDAY(f) + 1, 'Lunes','Martes','Miercoles','Jueves','Viernes',
                       'Sabado','Domingo'),
  CASE WHEN WEEKDAY(f) >= 5 THEN 1 ELSE 0 END,
  CASE WHEN DAYOFMONTH(f) IN (15, 16) OR f = LAST_DAY(f) THEN 1 ELSE 0 END
FROM seq;

SELECT COUNT(*) FROM dim_tiempo;   -- debe devolver 1461

-- ================= FILAS ESPECIALES =================
-- Producto y tienda: -1 = Desconocido
INSERT INTO dim_producto
  (producto_key, producto_id, nombre_producto, marca, categoria,
   subcategoria, unidad_medida, es_marca_propia, fecha_inicio_vig,
   fecha_fin_vig, es_vigente)
VALUES (-1, 'DESCONOCIDO', 'Desconocido', 'Desconocido',
        'Desconocido', 'Desconocido', 'NA', 0, '1900-01-01', '9999-12-31', 1);

INSERT INTO dim_tienda
  (tienda_key, tienda_id, nombre_tienda, formato, distrito, ciudad,
   region, area_m2, fecha_inicio_vig, fecha_fin_vig, es_vigente)
VALUES (-1, 'DESCONOCIDO', 'Desconocido', 'Desconocido', 'Desconocido',
        'Desconocido', 'Desconocido', 0, '1900-01-01', '9999-12-31', 1);

-- Cliente: -1 = Desconocido, -2 = No aplica (venta anonima)
INSERT INTO dim_cliente
  (cliente_key, cliente_id, nombre, segmento, distrito, ciudad,
   fecha_inicio_vig, fecha_fin_vig, es_vigente)
VALUES
  (-1, 'DESCONOCIDO', 'Desconocido', 'Desconocido', 'Desconocido',
   'Desconocido', '1900-01-01', '9999-12-31', 1),
  (-2, 'NO_APLICA', 'Venta anonima', 'No aplica', 'No aplica',
   'No aplica', '1900-01-01', '9999-12-31', 1);

-- Promocion: -2 = No aplica (la mayoria de las ventas no lleva promocion)
INSERT INTO dim_promocion
  (promocion_key, promocion_id, nombre_promocion, tipo_promocion,
   fecha_inicio, fecha_fin)
VALUES (-2, 'NO_APLICA', 'Sin promocion', 'No aplica',
        '1900-01-01', '9999-12-31');

-- ================= ETAPA 5: CARGA INICIAL DE LAS DIMENSIONES =================
INSERT INTO dim_producto
  (producto_id, nombre_producto, marca, categoria, subcategoria,
   unidad_medida, es_marca_propia, precio_lista, costo_estandar,
   fecha_inicio_vig, fecha_fin_vig, es_vigente)
SELECT cod_producto, nombre_producto, marca, categoria, subcategoria,
       unidad_medida, CAST(es_marca_propia AS UNSIGNED),
       CAST(precio_lista AS DECIMAL(12,2)),
       CAST(costo_unitario AS DECIMAL(12,2)),
       '1900-01-01', '9999-12-31', 1
FROM   stg_producto;

INSERT INTO dim_tienda
  (tienda_id, nombre_tienda, formato, distrito, ciudad, region,
   area_m2, fecha_apertura, fecha_inicio_vig, fecha_fin_vig, es_vigente)
SELECT cod_tienda, nombre_tienda, formato, distrito, ciudad, region,
       CAST(area_m2 AS DECIMAL(10,2)), STR_TO_DATE(fecha_apertura, '%Y-%m-%d'),
       '1900-01-01', '9999-12-31', 1
FROM   stg_tienda;

INSERT INTO dim_cliente
  (cliente_id, nombre, segmento, distrito, ciudad, fecha_alta,
   fecha_inicio_vig, fecha_fin_vig, es_vigente)
SELECT doc_cliente, nombre, segmento, distrito, ciudad,
       STR_TO_DATE(fecha_alta, '%Y-%m-%d'),
       '1900-01-01', '9999-12-31', 1
FROM   stg_cliente;

INSERT INTO dim_promocion
  (promocion_id, nombre_promocion, tipo_promocion, fecha_inicio, fecha_fin)
SELECT cod_promocion, nombre_promocion, tipo_promocion,
       STR_TO_DATE(fecha_inicio, '%Y-%m-%d'),
       STR_TO_DATE(fecha_fin, '%Y-%m-%d')
FROM   stg_promocion;

-- La dimension junk se construye con las combinaciones REALMENTE observadas
INSERT INTO dim_transaccion (tipo_comprobante, forma_pago, canal, es_devolucion)
SELECT DISTINCT tipo_comprobante, forma_pago, canal,
       CAST(flag_devolucion AS UNSIGNED)
FROM   stg_venta_pos;

-- Verificacion de conteos (Tabla 5 de la guia)
SELECT 'dim_tiempo' AS dimension, COUNT(*) AS filas FROM dim_tiempo
UNION ALL SELECT 'dim_producto',    COUNT(*) FROM dim_producto
UNION ALL SELECT 'dim_tienda',      COUNT(*) FROM dim_tienda
UNION ALL SELECT 'dim_cliente',     COUNT(*) FROM dim_cliente
UNION ALL SELECT 'dim_promocion',   COUNT(*) FROM dim_promocion
UNION ALL SELECT 'dim_transaccion', COUNT(*) FROM dim_transaccion;
