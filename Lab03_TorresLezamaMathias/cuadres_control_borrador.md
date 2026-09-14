# Cuadres de control — Lab 3 MERCANDINA

## Perfilado (Etapa 1)

**1. Longitud máxima de `nombre_producto`**
38 caracteres (ejemplo: "Verduras congelada Lamborghini Sur 424"). Se declarará `VARCHAR(200)` con margen amplio para no arriesgar truncamientos ante nombres futuros más largos.

**2. Cardinalidad de `unidad_medida` y `forma_pago`**
- `unidad_medida` (productos.csv): 4 valores — `KG`, `LT`, `PAQ`, `UND`. Baja cardinalidad, pero es un atributo propio del producto, no amerita dimensión aparte.
- `forma_pago` (ventas.csv): 4 valores — `Billetera movil`, `Efectivo`, `Tarjeta credito`, `Tarjeta debito`. Baja cardinalidad → candidato correcto para la dimensión junk (`dim_transaccion`), junto con `tipo_comprobante`, `canal` y `flag_devolucion`.

**3. Proporción de `doc_cliente` vacío en ventas.csv**
58,198 de 106,708 filas → **54.53%**. No es un error: es venta anónima (cliente no fidelizado), situación legítima del negocio en una tienda de conveniencia. Corresponde a la clave `-2` (No aplica) en `dim_cliente`, no a `-1` (Desconocido).

**4. Proporción de `cod_promocion` vacío**
83,085 de 106,708 filas → **77.86%**. Mismo criterio: la mayoría de las compras no lleva promoción. Clave `-2` en `dim_promocion`.

**5. Filas con cantidad negativa**
741 filas. Representan devoluciones (coinciden con `flag_devolucion = 1`): cantidad, importe_neto y descuento negativos revierten una venta previa. El signo de `importe_neto` debe conservarse tal cual al cargar la tabla de hechos — no tomar valor absoluto.

**6. Códigos de producto en ventas.csv ausentes del catálogo**
7 códigos huérfanos: `P90001` a `P90007`, afectando 362 líneas de ventas (**0.33%** del total). Confirma el uso obligatorio de `LEFT JOIN` (no `INNER JOIN`) al cargar la tabla de hechos, con `COALESCE` hacia la fila `-1` (Desconocido) de `dim_producto`. Con `INNER JOIN` estas 362 líneas desaparecerían sin aviso y el total del datamart dejaría de coincidir con el origen.

---

## Controles de carga (Etapa 8)

### Control 1 — Conteo de filas
```
filas_origen  filas_hecho  diferencia
106708        106708       0
```
**Interpretación**: ninguna fila del origen se perdió ni se duplicó al cargar la tabla de hechos; la carga de staging y el JOIN con `dim_tiempo` cubren el 100% de las líneas del POS.

### Control 2 — Cuadre de importes
```
importe_origen   importe_hecho
3430651.54       3430651.54
```
**Interpretación**: el dinero cuadra al centavo. Usar `DECIMAL(18,2)` en vez de FLOAT/DOUBLE y cargar directamente `importe_neto` (sin recalcularlo) evita cualquier diferencia de redondeo.

### Control 3 — Integridad referencial (huérfanos)
```
huerfanos_producto  huerfanos_tienda  huerfanos_cliente  huerfanos_promocion
0                   0                 0                  0
```
**Interpretación**: cero huérfanos en las cuatro dimensiones con historia. El `LEFT JOIN` + `COALESCE` hacia las claves -1/-2 garantiza que toda fila de hechos tenga una clave foránea válida, aunque el dato de origen no exista o esté vacío.

### Control 4 — Calidad de datos absorbida
```
pct_prod_desc  pct_tienda_desc  pct_anonimas  pct_sin_promo
0.339          0.000            54.54         77.86
```
**Interpretación**: el 0.339% de producto desconocido es el problema de calidad real (los 7 códigos huérfanos del perfilado) — se reporta al área responsable del catálogo ERP con un umbral de tolerancia propuesto del 0.5%; si se superara, el datamart debería bloquear la carga hasta corregir el origen. El 54.54% de ventas anónimas y el 77.86% sin promoción NO son defectos: son el comportamiento normal de una tienda de conveniencia (la mayoría de las compras no pasa por el programa de fidelización ni por una campaña).

### Control 5 — Duplicados de grano
```
filas_duplicadas
0
```
**Interpretación**: la clave primaria de `fact_venta` (tiempo_key, producto_key, tienda_key, nro_ticket) no admite duplicados, y en efecto no los hay — la carga de hechos se ejecutó una sola vez, como corresponde a un script no idempotente.

### Control 6 — Versiones vigentes duplicadas
```
filas
0
```
**Interpretación**: ninguna clave natural (producto_id, tienda_id, cliente_id) tiene dos versiones vigentes simultáneas. Esto confirma que el `WHERE d.es_vigente = 1` del Paso 1 del SCD Tipo 2 se aplicó correctamente antes de insertar la nueva versión.

### Control 7 — Cobertura temporal
```
fechas_sin_dimension
0
```
**Interpretación**: el rango generado para `dim_tiempo` (2024-01-01 a 2027-12-31) cubre sin excepción las fechas del semestre de ventas (2026-01-01 a 2026-06-30).

### Resumen contra la Tabla 8 de la guía
Los siete controles coinciden exactamente con los resultados esperados publicados por el profesor. No hubo que corregir ninguna etapa anterior.
