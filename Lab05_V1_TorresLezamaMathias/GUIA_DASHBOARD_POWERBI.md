# Guía — Dashboard en Power BI Desktop (Fase 2, Laboratory Guide Semana 5)

Caso: **COMERCIAL INCA S.A.C.** — datos generados con `laboratorio_semana5.py`
en `datamart_ventas/` (6 CSV: DIM_TIEMPO, DIM_PRODUCTO, DIM_CLIENTE,
DIM_TIENDA, DIM_VENDEDOR, FACT_VENTAS).

## 0. Antes de empezar

1. Copia la carpeta `datamart_ventas/` completa a un lugar accesible desde
   Windows (ej. `C:\Lab5\datamart_ventas\`). Si usas VM (Parallels/UTM),
   cópiala al disco de la VM en vez de dejarla en una carpeta compartida —
   evita rutas raras al importar.
2. Abre Power BI Desktop. Si aparece la ventana de inicio, ciérrala.

---

## 1. Importar los 6 archivos CSV

`Inicio → Obtener datos → Texto o CSV`. Repite una vez por archivo, en este
orden:

1. `DIM_TIEMPO.csv`
2. `DIM_PRODUCTO.csv`
3. `DIM_CLIENTE.csv`
4. `DIM_TIENDA.csv`
5. `DIM_VENDEDOR.csv`
6. `FACT_VENTAS.csv`

En cada vista previa verifica: delimitador **Coma**, codificación **UTF-8**.
Clic en **Cargar**.

**Verificación:** deben aparecer 6 tablas en el panel **Datos** (derecha).
Si falta alguna, revisa que seleccionaste el archivo correcto y que no hay
espacios extra en el nombre.

---

## 2. Crear las 5 relaciones (esquema estrella)

Ve a la **Vista de Modelo** (ícono de diagrama, panel izquierdo). Arrastra
desde `FACT_VENTAS` hacia cada dimensión:

| Desde (FACT_VENTAS) | Hacia               |
|----------------------|----------------------|
| `id_tiempo`          | `DIM_TIEMPO.id_tiempo`     |
| `id_producto`        | `DIM_PRODUCTO.id_producto` |
| `id_cliente`         | `DIM_CLIENTE.id_cliente`   |
| `id_tienda`          | `DIM_TIENDA.id_tienda`     |
| `id_vendedor`        | `DIM_VENDEDOR.id_vendedor` |

En cada diálogo: **Cardinalidad = Varios a uno (\*:1)**, **Dirección de
filtro cruzado = Único**. Clic en **Aceptar**.

**Verificación:** el diagrama debe mostrar `FACT_VENTAS` en el centro con
5 líneas hacia las dimensiones — símbolo `*` del lado de `FACT_VENTAS`,
`1` del lado de cada dimensión. Si alguna relación muestra `*` en ambos
extremos, elimínala y vuelve a crearla.

---

## 3. Crear las medidas DAX

En el panel **Datos**, clic derecho sobre la tabla `FACT_VENTAS` →
**Nueva medida**. Ingresa cada fórmula y presiona Enter. Repite para las 7:

| Nombre de la medida | Fórmula DAX |
|---|---|
| Total Ventas | `Total Ventas = SUM(FACT_VENTAS[monto_neto_sol])` |
| Total Costo | `Total Costo = SUM(FACT_VENTAS[costo_sol])` |
| Margen Bruto | `Margen Bruto = SUM(FACT_VENTAS[margen_bruto_sol])` |
| Margen % | `Margen % = DIVIDE([Margen Bruto], [Total Ventas], 0)` |
| Unidades Vendidas | `Unidades Vendidas = SUM(FACT_VENTAS[cantidad])` |
| Ticket Promedio | `Ticket Promedio = DIVIDE([Total Ventas], COUNTROWS(FACT_VENTAS), 0)` |
| Total Descuentos | `Total Descuentos = SUM(FACT_VENTAS[descuento_sol])` |

**Verificación:** arrastra `Total Ventas` a un visual de Tarjeta en la
Vista de Informe. Debe mostrar un valor mayor a cero (no un error ni 0).
Si sale 0 o error, revisa que las relaciones del paso 2 estén bien
establecidas y que los campos numéricos tengan tipo Decimal/Entero.

---

## 4. Crear la página "Dashboard Ventas"

Clic en el símbolo **+** en la parte inferior para crear una nueva página.
Renómbrala **Dashboard Ventas**. Agrega los siguientes 6 visuales:

### 4.1 Tarjeta KPI
Inserta un visual **Tarjeta** (o varias tarjetas). Campos:
`[Total Ventas]`, `[Margen %]`, `[Unidades Vendidas]`.
→ Demuestra: vista general del período completo (agregación máxima).

### 4.2 Gráfico de barras apiladas
- Eje X: `DIM_TIEMPO[nombre_mes]`
- Eje Y: `[Total Ventas]`
- Leyenda: `DIM_PRODUCTO[categoria]`
→ Demuestra: Roll-Up de día a mes, desglosado por categoría.

### 4.3 Gráfico de líneas
- Eje X: agrega `DIM_TIEMPO[anio]`, luego `DIM_TIEMPO[trimestre]`, luego
  `DIM_TIEMPO[mes]` (en ese orden, Power BI arma jerarquía automática)
- Eje Y (Valores): `[Total Ventas]`
- Activa el **Drill-Down** (ícono de flecha doble ↓↓ en la esquina
  superior del visual) y navega Año → Trimestre → Mes.
→ Demuestra: Drill-Down de año a mes.

### 4.4 Matriz (tabla dinámica)
- Filas: `DIM_PRODUCTO[categoria]`, luego `DIM_PRODUCTO[subcategoria]`
- Columnas: `DIM_TIEMPO[anio]`
- Valores: `[Total Ventas]`
→ Demuestra: Pivot (años en columnas) + Drill-Down por jerarquía de
producto (expande categoría → subcategoría con el `+`).

### 4.5 Mapa de árbol (Treemap)
- Grupo: `DIM_TIENDA[region]`
- Subgrupo: `DIM_TIENDA[nombre]`
- Valor: `[Total Ventas]`
→ Demuestra: Slice geográfico — distribución de ventas por región/tienda.

### 4.6 Segmentador (Slicer) x2
- Segmentador 1 — Campo: `DIM_TIEMPO[anio]`
- Segmentador 2 — Campo: `DIM_TIENDA[region]`
- Prueba seleccionar un año y una región simultáneamente: todos los
  visuales deben filtrarse a la vez.
→ Demuestra: **Dice** — filtra el cubo por año y región al mismo tiempo.

---

## 5. Guardar el entregable

1. `Archivo → Guardar como` → nombre: `Torres_Lezama_Mathias_Lab5_BI.pbix`
2. Exportar el dashboard como imagen/PDF: en la página, clic en `...`
   (tres puntos) → **Exportar → PDF**.
3. Capturas de pantalla de la página "Dashboard Ventas" completa.

**Entregables de esta fase:** el archivo `.pbix` + las capturas/PDF del
dashboard.
