# Lab 5 — Laboratory Guide Week 5 (10 págs) — COMERCIAL INCA / DISTRIBUIDORA ANDINA

## Objetivo
Completar el laboratorio de la Semana 5 de Inteligencia de Negocios (UNMSM),
guía "Laboratory Guide Week 5.pdf" (10 páginas): construir un Datamart
Analítico de Ventas con Python (Faker + pandas + numpy) para el caso
COMERCIAL INCA S.A.C., importarlo a Power BI Desktop y crear el modelo
dimensional, medidas DAX y visualizaciones OLAP. Luego resolver la actividad
propuesta (DISTRIBUIDORA ANDINA E.I.R.L.) de forma autónoma.

## Por qué
Entregable de curso, evaluado por el docente (16 pts guiado + 12 pts
actividad, ver criterios en el PDF).

## Ubicación
`IN/Lab05_V1_TorresLezamaMathias/`

## Decisiones registradas
- Entorno: `mamba env mlenv` (Python 3.12.13). Se instaló `numpy`, `faker`,
  `openpyxl` (pandas 3.0.2 ya estaba). No se crea venv aparte.
- DIM_CLIENTE: se corrige el bug de mapeo departamento/distrito del PDF
  (el `if` original asignaba "Lima" a Trujillo/Arequipa/Cusco/Piura/Chiclayo).
  Se usa el mapeo geográfico correcto vía `provincias_map`/`departamentos_map`.
- DIM_PRODUCTO: se deja el código del PDF tal cual (60–108 productos según
  `random.randint(5,9)` por subcategoría), aunque el texto diga "80". El
  código es la fuente de verdad.
- "Dataset B Distribuidora Andina" (ya provisto por el docente, en
  `Lab05_V1_TorresLezamaMathias/Dataset B Distribuidora Andina Sept 25 2026/`)
  se usa solo como referencia de forma/rangos, no como fuente de datos: la
  actividad propuesta pide generar `FACT_PEDIDOS` con Python nosotros mismos.
- TDD: no aplica (script de generación de datos + exploración en Power BI,
  no hay lógica de negocio testeable de forma unitaria significativa).
  Verificación por corrida + validación de integridad referencial (incluida
  en el propio guide, Paso 7).
- RDD / commits: usuario tiene regla global de no commitear sin confirmación
  explícita en el turno — no se ejecuta `git commit` automáticamente al
  cerrar tareas.

## Checklist

### Fase 1 — Entorno y generación de datos (COMERCIAL INCA, guiado)
- [x] T1.1 Entorno `mlenv` verificado e instalado (pandas, numpy, faker, openpyxl)
- [x] T1.2 Crear `laboratorio_semana5.py` — setup + imports + semilla
- [x] T1.3 `DIM_TIEMPO` (1,461 filas) — OK
- [x] T1.4 `DIM_PRODUCTO` (60–108 filas, código fiel al PDF) — 84 filas generadas
- [x] T1.5 `DIM_CLIENTE` (200 filas, mapeo departamento corregido) — OK
- [x] T1.6 `DIM_TIENDA` y `DIM_VENDEDOR` — 10 y 30 filas
- [x] T1.7 `FACT_VENTAS` (5,000 filas, estacionalidad) — OK
- [x] T1.8 Validación de integridad referencial (Paso 7 del guide) — 100% OK en Producto/Cliente/Tienda/Vendedor, 96.0% en Tiempo (normal, no todos los días tienen venta)
- [x] T1.9 Ejecutar el script y verificar salidas en `datamart_ventas/*.csv` — 6 CSV generados correctamente

### Fase 2 — Power BI (guiado) — pendiente
- [ ] T2.1 Importar 6 tablas y crear 5 relaciones *:1
- [ ] T2.2 Crear 7 medidas DAX
- [ ] T2.3 Crear 6 visuales OLAP en "Dashboard Ventas"

### Fase 3 — Actividad propuesta (DISTRIBUIDORA ANDINA, autónoma) — pendiente
- [ ] T3.1 Diagrama del esquema estrella
- [ ] T3.2 Script Python: 4 dimensiones + `FACT_PEDIDOS` (3,000) en `datamart_pedidos/`, validación FK
- [ ] T3.3 Power BI: 4 relaciones, 3 medidas DAX
- [ ] T3.4 4 reportes (A, B, C, D)

### Fase 4 — Entregable — pendiente
- [ ] T4.1 Guardar `.py`, `.pbix`, diagrama, capturas

## Progreso / evidencia
- 2026-09-27: entorno `mlenv` completado y verificado (import pandas, numpy,
  faker, openpyxl exitoso).
- 2026-09-27: Fase 1 completa. `laboratorio_semana5.py` corrido en `mlenv`.
  Hallazgo adicional al ejecutar: Faker 40.x no incluye el locale `es_PE`
  usado en el PDF (`AttributeError: Invalid configuration for faker locale
  'es_PE'`); se cambió a `es_ES` (locale español más cercano disponible en
  esta versión). Salidas verificadas en `datamart_ventas/`:
  DIM_TIEMPO=1461, DIM_PRODUCTO=84, DIM_CLIENTE=200, DIM_TIENDA=10,
  DIM_VENDEDOR=30, FACT_VENTAS=5000. Integridad referencial: 100% OK en
  Producto/Cliente/Tienda/Vendedor, 96.0% en Tiempo (esperado, no todos los
  días del período tienen venta).

- 2026-09-28: se generó `Lab05_V1_TorresLezamaMathias/GUIA_DASHBOARD_POWERBI.md`
  como guía autocontenida de la Fase 2 (importar, relaciones, 7 medidas DAX,
  6 visuales), para que el usuario la ejecute en Power BI Desktop en una
  laptop Windows (VM Parallels/UTM) sin depender de guía turno a turno.

## Siguiente paso
Fase 2 (Power BI): usuario ejecuta `GUIA_DASHBOARD_POWERBI.md` en la laptop
Windows. Pendiente confirmar resultado (relaciones, medidas, .pbix guardado)
y avanzar a Fase 3 (actividad DISTRIBUIDORA ANDINA).

## Nota sobre mirror
Engram no disponible esta sesión (MCP desconectado) — mirror pendiente de
sincronizar cuando el servidor vuelva a estar disponible.
