# Plan de trabajo — Lab 3 (Datamart MERCANDINA)

Alcance de esta laptop (Mac): Etapas 0–9 + Actividad propuesta (todo SQL).
Etapa 10 (Power BI) queda pendiente para la otra laptop (Windows).

Cada fase indica: qué se hizo, comandos clave (Mac y equivalente Windows cuando difiere), y estado.

---

## Fase 1 — Entorno (Etapa 0) ✅ HECHO

- MySQL no estaba instalado → instalado vía Homebrew (`brew install mysql`).
  - Versión: `26.7.0` (cumple "8.0 o superior").
  - Windows: instalar MySQL Community Server 8.0+ desde el sitio oficial (el instalador ya trae el servicio configurado).
- Servicio iniciado: `brew services start mysql`.
  - Windows: el servicio "MySQL80" arranca solo, o `net start MySQL80`.
- Verificación (Fig. 1):
  - `SELECT VERSION();` → 26.7.0
  - `SHOW VARIABLES LIKE 'secure_file_priv';` → `NULL` (carga desde archivo deshabilitada por completo)
  - `SHOW VARIABLES LIKE 'local_infile';` → estaba en `OFF`
- Acción tomada: `SET GLOBAL local_infile = 1;` → ahora en `ON`.
  - **Importante**: esta variable NO persiste si se reinicia el servicio de MySQL. Si en algún momento `local_infile` vuelve a `OFF`, repetir el comando.
  - Además del lado servidor, el **cliente** también necesita el flag. Al conectar por CLI para la carga (Fase 4), usar:
    - Mac/Linux: `mysql --local-infile=1 -u root`
    - Windows: `mysql --local-infile=1 -u root -p` (o activar "Allow LOAD DATA LOCAL INFILE" en MySQL Workbench: Edit > Preferences > SQL Editor)
- CSV verificados en `datos/`: los 8 archivos presentes, `ventas.csv` con 106,709 líneas (106,708 datos + encabezado) — coincide con el `LEEME.txt` y la Tabla 2 de la guía.
- Nota: como `secure_file_priv = NULL`, la ruta de los CSV no importa (no se usa `LOAD DATA INFILE` a secas) — se usará `LOAD DATA LOCAL INFILE` apuntando directo a la carpeta `datos/` del proyecto, sin copiar nada a una carpeta especial de MySQL.

---

## Fase 2 — Perfilado (Etapa 1) ✅ HECHO

- Inspección de `productos.csv`, `tiendas.csv`, `clientes.csv` y `ventas.csv` con `awk`/`comm` (sin abrir en Excel/Numbers, evitando el riesgo de corrupción de fechas que advierte la guía).
- Windows: los mismos comandos funcionan igual en PowerShell con WSL, o se pueden replicar con `Import-Csv` + `Group-Object`/`Measure-Object` si no hay WSL disponible.
- Las 6 preguntas de perfilado respondidas y guardadas en `cuadres_control_borrador.md` (sección Perfilado). Resultados:
  1. Longitud máxima `nombre_producto`: 38 caracteres.
  2. `unidad_medida`: 4 valores (KG, LT, PAQ, UND). `forma_pago`: 4 valores (Billetera movil, Efectivo, Tarjeta credito, Tarjeta debito).
  3. `doc_cliente` vacío: 54.53% (venta anónima, clave -2).
  4. `cod_promocion` vacío: 77.86% (sin promoción, clave -2).
  5. Cantidad negativa: 741 filas (devoluciones, signo se conserva).
  6. Códigos de producto huérfanos: 7 (`P90001`–`P90007`), 362 líneas (0.33%) → confirma LEFT JOIN + COALESCE en la carga de hechos.
- Todos los resultados cuadran con lo anticipado por la guía (Tabla 8 y "Resultado esperado del perfilado").

## Fase 3 — DDL (Etapa 2) ✅ HECHO
→ `dm_mercandina_ddl.sql`: BD `dm_mercandina`, 8 tablas staging, 6 dimensiones, `fact_venta` particionada.
- Ejecutado sobre BD vacía sin errores.
- `SHOW TABLES` → 15 tablas (6 dim + 1 hecho + 8 staging).
- Particiones de `fact_venta`: 6 (p2025, p2026q1–q4, pmax) — confirmado vía `information_schema.partitions`.
- **Nota para el informe**: la guía (pág. 8) dice "verifique que las trece tablas existen" con el comentario `-- 6 de staging + 6 dimensiones + 1 hecho` (=13), pero la Figura 5 declara 8 tablas de staging, no 6. El total real correcto es 15. Inconsistencia menor de la propia guía; el DDL sigue fielmente las Figuras 5–7.
- Windows: mismo script, se ejecuta igual con `mysql -u root -p < dm_mercandina_ddl.sql` o pegándolo en Workbench.

## Fase 4 — Staging + dimensión tiempo + filas especiales (Etapas 3–4) ✅ HECHO
→ `dm_mercandina_dim.sql` (parte 1): `LOAD DATA LOCAL INFILE` de los 8 CSV, generación de `dim_tiempo`, filas -1/-2.
- Comando usado: `mysql --local-infile=1 -u root < dm_mercandina_dim.sql`
  - Windows: `mysql --local-infile=1 -u root -p < dm_mercandina_dim.sql`, o si LOAD DATA sigue bloqueado, usar el asistente de importación de MySQL Workbench (plan alternativo de la guía, pág. 3).
- Conteos de staging: 100% coinciden con la Tabla 4 (386, 28, 34, 6, 1200, 95, 12, 106708).
- `dim_tiempo`: 1461 filas (2024-01-01 a 2027-12-31) ✔.
- Filas especiales insertadas: dim_producto (-1), dim_tienda (-1), dim_cliente (-1 y -2), dim_promocion (-2) ✔.
- Recordatorio: `local_infile` hay que volver a activarlo (`SET GLOBAL local_infile = 1`) cada vez que se reinicie el servicio de MySQL.

## Fase 5 — Carga inicial de dimensiones (Etapa 5) ✅ HECHO
→ `dm_mercandina_dim.sql` (parte 2, agregada al mismo archivo).
- Conteos: dim_tiempo 1461, dim_producto 387, dim_tienda 35, dim_cliente 1202, dim_promocion 13, dim_transaccion 29 — 100% coincide con la Tabla 5.
- `dim_transaccion` dio 29 y no 32 (el cartesiano de 2×4×2×2): confirma que la dimensión junk se construyó con `DISTINCT` sobre combinaciones realmente observadas, no con el producto cartesiano completo — punto que la guía pide explicar en el informe (riesgo: una combinación válida que no aparezca en el semestre de carga no tendrá fila hasta que ocurra, y si la carga de hechos no maneja ese caso, fallaría el join hacia `dim_transaccion`).
- **Pendiente antes de empaquetar**: recrear la BD (DROP+DDL) y correr `dm_mercandina_dim.sql` completo de una sola vez para confirmar reproducibilidad de punta a punta (condición de aceptación de la guía). Por ahora se ejecutó en dos pasos para no duplicar el LOAD DATA.

## Fase 6 — SCD Tipo 2 (Etapa 6) ✅ HECHO
→ `dm_mercandina_scd2.sql`: patrón de dos pasos (cerrar vigente + insertar nueva) aplicado a dim_producto, dim_tienda y dim_cliente.
- Conteos finales: dim_producto 415/387/28, dim_tienda 41/35/6, dim_cliente 1297/1202/95 — 100% coincide con la Tabla 6.
  - Nota de verificación: los conteos deben incluir las filas especiales (-1/-2); no se tocan por el SCD2 pero sí se suman al total en la Tabla 6 de la guía. Un primer intento de verificación que las excluía dio 414/386/28 (aparente descuadre) — era error de la consulta de verificación, no de la carga.
- Verificado con un producto concreto (Fig. 15): dos versiones con categorías y claves subrogadas distintas, vigencia cerrada el 31/03 y abierta desde el 01/04 ✔.
- Recordatorio: script **no idempotente** — si hay que repetirlo, recrear la BD desde cero (DDL) y volver a correr los 3 scripts en orden.
- Windows: mismo script SQL, sin cambios.

## Fase 7 — Carga de hechos (Etapa 7) ✅ HECHO
→ `dm_mercandina_carga.sql`: LEFT JOIN hacia las 4 dimensiones con historia (sensible a fecha vía BETWEEN), COALESCE hacia -1/-2, NULLIF sobre doc_cliente/cod_promocion vacíos, JOIN normal hacia dim_transaccion.
- Ejecución: 1.6 s (índices de staging de la etapa 2 hacen su trabajo).
- Resultado: 106,708 filas en `fact_venta`, importe total 3,430,651.54 — coincide exacto con la Tabla 8 (control 1 y 2) y la Tabla 9.
- Los 5 detalles críticos de la Tabla 7 de la guía (LEFT JOIN no INNER, COALESCE, BETWEEN sobre vigencia, NULLIF sobre vacíos, JOIN normal a dim_transaccion) están todos aplicados.
- Windows: mismo script SQL, sin cambios.

## Fase 8 — Cuadres de control (Etapa 8) ✅ HECHO (en md, falta exportar a PDF)
→ Documentado en `cuadres_control_borrador.md`. Se exporta a `cuadres_control.pdf` al final, junto con el perfilado.
- Los 7 controles ejecutados, con captura e interpretación de cada uno.
- Los 7 coinciden exactamente con la Tabla 8 de la guía: 0 diferencia de filas, importes iguales al centavo, 0 huérfanos, 0.339%/54.54%/77.86% de calidad, 0 duplicados de grano, 0 versiones vigentes duplicadas, 0 fechas sin cobertura.
- No hubo que corregir ninguna etapa anterior.

## Fase 9 — OLAP (Etapa 9) ✅ HECHO
→ `dm_mercandina_olap.sql`: las 6 operaciones (roll-up, drill-down, slice, dice, pivot, drill-across) + materialización con `WITH ROLLUP` + versión `GROUPING SETS` comentada para otros motores.
- Los 10 valores de la Tabla 9 (valores de referencia) coinciden exactos: venta total 3,430,651.54; 32,613 tickets; ticket promedio 105.19; margen 26.76%; venta por ciudad (Lima 1,780,310.66 / Arequipa 621,510.02 / Cusco 521,301.04 / Trujillo 507,529.82); mayor venta Mayo (619,775.27); menor venta Febrero (528,200.10).
- Pendiente para el informe: explicar la diferencia ROLLUP vs GROUPING SETS (ROLLUP solo da niveles jerárquicos descendentes; GROUPING SETS permitiría, por ejemplo, el total por ciudad sin período, que ROLLUP no genera).
- Windows: mismo script SQL. Si el motor no soporta WITH ROLLUP (p. ej. versiones viejas de PostgreSQL), usar el bloque GROUPING SETS ya dejado comentado en el archivo.

## Fase 10 — Actividad propuesta ⬜ PENDIENTE
→ `actividad_propuesta.pdf`.

---

## Pendiente para la otra laptop (Windows)
- **Etapa 10**: modelo semántico en Power BI (`dm_mercandina.pbix`), conector MySQL/NET, relaciones, medidas DAX, jerarquías, matrices, validación final del total (3,430,651.54).
