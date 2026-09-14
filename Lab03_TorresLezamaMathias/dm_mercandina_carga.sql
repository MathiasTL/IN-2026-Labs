USE dm_mercandina;

INSERT INTO fact_venta
  (tiempo_key, producto_key, tienda_key, cliente_key, promocion_key,
   transaccion_key, nro_ticket, cantidad, importe_venta, importe_costo,
   importe_descuento)
SELECT
  t.tiempo_key,
  COALESCE(p.producto_key, -1),      -- producto no hallado en el catalogo
  COALESCE(s.tienda_key,   -1),
  COALESCE(cl.cliente_key, -2),      -- venta anonima (no es un error)
  COALESCE(pr.promocion_key, -2),    -- venta sin promocion
  tr.transaccion_key,
  o.nro_ticket,
  CAST(o.cantidad AS DECIMAL(12,3)),
  CAST(o.importe_neto AS DECIMAL(18,2)),
  CAST(o.costo_unitario AS DECIMAL(18,2))
    * CAST(o.cantidad AS DECIMAL(12,3)),
  CAST(o.descuento AS DECIMAL(18,2))
FROM        stg_venta_pos o
JOIN        dim_tiempo t
  ON t.fecha = STR_TO_DATE(o.fecha_emision, '%Y-%m-%d')
LEFT JOIN   dim_producto p
  ON p.producto_id = o.cod_producto
  AND STR_TO_DATE(o.fecha_emision, '%Y-%m-%d')
       BETWEEN p.fecha_inicio_vig AND p.fecha_fin_vig
LEFT JOIN   dim_tienda s
  ON s.tienda_id = o.cod_tienda
  AND STR_TO_DATE(o.fecha_emision, '%Y-%m-%d')
       BETWEEN s.fecha_inicio_vig AND s.fecha_fin_vig
LEFT JOIN   dim_cliente cl
  ON cl.cliente_id = NULLIF(o.doc_cliente, '')
  AND STR_TO_DATE(o.fecha_emision, '%Y-%m-%d')
       BETWEEN cl.fecha_inicio_vig AND cl.fecha_fin_vig
LEFT JOIN   dim_promocion pr
  ON pr.promocion_id = NULLIF(o.cod_promocion, '')
JOIN        dim_transaccion tr
  ON tr.tipo_comprobante = o.tipo_comprobante
  AND tr.forma_pago      = o.forma_pago
  AND tr.canal           = o.canal
  AND tr.es_devolucion   = CAST(o.flag_devolucion AS UNSIGNED);
