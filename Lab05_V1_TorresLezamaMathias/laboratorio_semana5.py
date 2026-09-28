# =============================================================
#  LABORATORIO SEMANA 5 — INTELIGENCIA DE NEGOCIOS
#  Datamart Analitico de Ventas - COMERCIAL INCA S.A.C.
#  Prof. Juan Gamarra Moreno — UNMSM 2026-1
#  Alumno: Torres Lezama, Mathias
# =============================================================
#
#  Fuente: "Laboratory Guide Week 5.pdf" (10 paginas).
#
#  Desviaciones respecto al codigo tal cual aparece en el PDF,
#  decididas junto con el alumno:
#   - DIM_CLIENTE: el PDF asigna 'departamento' con un if que
#     manda a 'Lima' distritos que no son de Lima (Trujillo,
#     Arequipa, Cusco, Piura, Chiclayo). Aqui se corrige usando
#     un mapeo distrito -> departamento explicito y correcto.
#   - DIM_PRODUCTO: el texto del PDF dice "80 productos", pero
#     el codigo (random.randint(5, 9) por cada una de las 12
#     subcategorias) genera entre 60 y 108. Se deja el codigo
#     del PDF tal cual: es la fuente de verdad de la ejecucion.
# =============================================================

import pandas as pd
import numpy as np
from faker import Faker
from datetime import date, timedelta
import random
import os

# Configurar semilla para reproducibilidad
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker('es_ES')  # 'es_PE' no existe en esta version de Faker (40.x); se usa 'es_ES' como locale mas cercano disponible
Faker.seed(SEED)

# Carpeta de salida para los archivos CSV
os.makedirs('datamart_ventas', exist_ok=True)
print('Entorno configurado correctamente.')


# =============================================================
# PASO 2: Construccion de DIM_TIEMPO
# =============================================================
def crear_dim_tiempo(fecha_inicio='2022-01-01', fecha_fin='2025-12-31'):
    fechas = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='D')
    meses_es = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    dias_es = {0: 'Lunes', 1: 'Martes', 2: 'Miercoles',
               3: 'Jueves', 4: 'Viernes', 5: 'Sabado', 6: 'Domingo'}
    df = pd.DataFrame({
        'id_tiempo':    fechas.strftime('%Y%m%d').astype(int),
        'fecha':        fechas.date,
        'dia':          fechas.day,
        'nombre_dia':   fechas.dayofweek.map(dias_es),
        'semana':       fechas.isocalendar().week.astype(int),
        'mes':          fechas.month,
        'nombre_mes':   fechas.month.map(meses_es),
        'trimestre':    fechas.quarter,
        'semestre':     np.where(fechas.month <= 6, 1, 2),
        'anio':         fechas.year,
        'es_fin_semana': (fechas.dayofweek >= 5).astype(int),
        'es_feriado':   0,  # simplificado
    })
    return df


dim_tiempo = crear_dim_tiempo()
dim_tiempo.to_csv('datamart_ventas/DIM_TIEMPO.csv', index=False)
print(f'DIM_TIEMPO: {len(dim_tiempo)} filas generadas.')
print(dim_tiempo.head(3).to_string())


# =============================================================
# PASO 3: Construccion de DIM_PRODUCTO
# =============================================================
categorias = {
    'Electronica': ['Smartphones', 'Laptops', 'Accesorios TI', 'Audio'],
    'Hogar':       ['Muebles', 'Decoracion', 'Electrodomesticos'],
    'Ropa':        ['Hombre', 'Mujer', 'Calzado'],
    'Alimentacion': ['Abarrotes', 'Bebidas'],
}

marcas = ['Samsung', 'LG', 'Sony', 'HP', 'Lenovo', 'Asus', 'Bose',
          'IKEA', 'Mabe', 'Adidas', 'Nike', 'Gloria', 'Alicorp', 'BIC']
unidades = ['UND', 'KG', 'LT', 'PAQ', 'CJA']

filas = []
prod_id = 1
for cat, subcats in categorias.items():
    for subcat in subcats:
        n_prods = random.randint(5, 9)
        for _ in range(n_prods):
            precio = round(random.uniform(15, 2500), 2)
            filas.append({
                'id_producto':    prod_id,
                'codigo':         f'PROD-{prod_id:04d}',
                'nombre':         fake.catch_phrase()[:40],
                'subcategoria':   subcat,
                'categoria':      cat,
                'marca':          random.choice(marcas),
                'unidad_medida':  random.choice(unidades),
                'precio_lista':   precio,
            })
            prod_id += 1

dim_producto = pd.DataFrame(filas)
dim_producto.to_csv('datamart_ventas/DIM_PRODUCTO.csv', index=False)
print(f'DIM_PRODUCTO: {len(dim_producto)} filas generadas.')
print(dim_producto[['id_producto', 'codigo', 'subcategoria', 'categoria', 'precio_lista']].head(5).to_string())


# =============================================================
# PASO 4: Construccion de DIM_CLIENTE
# =============================================================
segmentos = ['Minorista', 'Mayorista', 'Corporativo', 'Gobierno']
tipos = ['Persona Natural', 'Empresa']
distritos = ['Miraflores', 'San Isidro', 'Surco', 'La Molina', 'San Borja',
             'Barranco', 'Lince', 'Magdalena', 'Jesus Maria', 'Pueblo Libre',
             'Trujillo', 'Arequipa', 'Cusco', 'Piura', 'Chiclayo']

# Mapeo distrito -> provincia (igual al del PDF)
provincias_map = {
    'Miraflores': 'Lima', 'San Isidro': 'Lima', 'Surco': 'Lima',
    'La Molina': 'Lima', 'San Borja': 'Lima', 'Barranco': 'Lima',
    'Lince': 'Lima', 'Magdalena': 'Lima', 'Jesus Maria': 'Lima',
    'Pueblo Libre': 'Lima', 'Trujillo': 'La Libertad',
    'Arequipa': 'Arequipa', 'Cusco': 'Cusco',
    'Piura': 'Piura', 'Chiclayo': 'Lambayeque',
}

# CORREGIDO respecto al PDF: el departamento se deriva del distrito con un
# mapeo explicito, en vez del if que enviaba a 'Lima' todo lo que no
# estuviera en la lista de distritos limenos.
departamentos_map = {
    'Miraflores': 'Lima', 'San Isidro': 'Lima', 'Surco': 'Lima',
    'La Molina': 'Lima', 'San Borja': 'Lima', 'Barranco': 'Lima',
    'Lince': 'Lima', 'Magdalena': 'Lima', 'Jesus Maria': 'Lima',
    'Pueblo Libre': 'Lima', 'Trujillo': 'La Libertad',
    'Arequipa': 'Arequipa', 'Cusco': 'Cusco',
    'Piura': 'Piura', 'Chiclayo': 'Lambayeque',
}

filas = []
for i in range(1, 201):
    dist = random.choice(distritos)
    tipo = random.choice(tipos)
    nombre = fake.company() if tipo == 'Empresa' else fake.name()
    filas.append({
        'id_cliente':   i,
        'ruc_dni':      fake.numerify(text='########'),
        'nombre':       nombre[:50],
        'tipo_cliente': tipo,
        'segmento':     random.choice(segmentos),
        'email':        fake.email(),
        'telefono':     fake.phone_number(),
        'distrito':     dist,
        'provincia':    provincias_map[dist],
        'departamento': departamentos_map[dist],
    })

dim_cliente = pd.DataFrame(filas)
dim_cliente.to_csv('datamart_ventas/DIM_CLIENTE.csv', index=False)
print(f'DIM_CLIENTE: {len(dim_cliente)} filas generadas.')


# =============================================================
# PASO 5: Construccion de DIM_TIENDA y DIM_VENDEDOR
# =============================================================
tiendas_data = [
    (1, 'T001', 'Miraflores', 'Tienda Premium', 'Lima', 'Lima', 'Lima'),
    (2, 'T002', 'San Isidro', 'Tienda Premium', 'Lima', 'Lima', 'Lima'),
    (3, 'T003', 'Surco', 'Tienda Estandar', 'Lima', 'Lima', 'Lima'),
    (4, 'T004', 'La Molina', 'Tienda Estandar', 'Lima', 'Lima', 'Lima'),
    (5, 'T005', 'Miraflores', 'Online', 'Lima', 'Lima', 'Lima'),
    (6, 'T006', 'Trujillo', 'Tienda Estandar', 'Trujillo', 'La Libertad', 'Norte'),
    (7, 'T007', 'Arequipa', 'Tienda Premium', 'Arequipa', 'Arequipa', 'Sur'),
    (8, 'T008', 'Cusco', 'Tienda Estandar', 'Cusco', 'Cusco', 'Sur'),
    (9, 'T009', 'Piura', 'Tienda Estandar', 'Piura', 'Piura', 'Norte'),
    (10, 'T010', 'Chiclayo', 'Tienda Estandar', 'Chiclayo', 'Lambayeque', 'Norte'),
]
cols_t = ['id_tienda', 'codigo', 'nombre', 'formato', 'distrito', 'provincia', 'region']
dim_tienda = pd.DataFrame(tiendas_data, columns=cols_t)
dim_tienda.to_csv('datamart_ventas/DIM_TIENDA.csv', index=False)
print(f'DIM_TIENDA: {len(dim_tienda)} filas generadas.')

puestos = ['Asesor de Ventas', 'Vendedor Senior', 'Jefe de Tienda']
filas_v = []
for i in range(1, 31):
    filas_v.append({
        'id_vendedor':   i,
        'codigo':        f'VEN-{i:03d}',
        'nombre':        fake.name(),
        'puesto':        random.choice(puestos),
        'id_tienda_asig': random.randint(1, 10),
        'activo':        1,
    })
dim_vendedor = pd.DataFrame(filas_v)
dim_vendedor.to_csv('datamart_ventas/DIM_VENDEDOR.csv', index=False)
print(f'DIM_VENDEDOR: {len(dim_vendedor)} filas generadas.')


# =============================================================
# PASO 6: Construccion de FACT_VENTAS
# =============================================================
N_TRANSACCIONES = 5000

# Pesos de estacionalidad por mes (Dic y Nov tienen mas ventas)
pesos_mes = [0.06, 0.06, 0.07, 0.07, 0.07, 0.07, 0.07, 0.08, 0.08, 0.09, 0.10, 0.12]

# Ids disponibles
ids_tiempo = dim_tiempo['id_tiempo'].tolist()
ids_producto = dim_producto['id_producto'].tolist()
ids_cliente = dim_cliente['id_cliente'].tolist()
ids_tienda = dim_tienda['id_tienda'].tolist()
ids_vendedor = dim_vendedor['id_vendedor'].tolist()

# Tabla de precios para calcular montos coherentes
precio_ref = dim_producto.set_index('id_producto')['precio_lista'].to_dict()

filas_f = []
for i in range(1, N_TRANSACCIONES + 1):
    id_prod = random.choice(ids_producto)
    precio_unit = round(precio_ref[id_prod] * random.uniform(0.85, 1.05), 2)
    cantidad = random.randint(1, 20)
    descuento_p = round(random.uniform(0, 0.25), 4)  # 0% a 25%
    monto_bruto = round(precio_unit * cantidad, 2)
    descuento = round(monto_bruto * descuento_p, 2)
    monto_neto = round(monto_bruto - descuento, 2)
    costo = round(monto_neto * random.uniform(0.45, 0.70), 2)
    igv = round(monto_neto * 0.18, 2)
    margen = round(monto_neto - costo, 2)

    # Seleccionar fecha con pesos estacionales
    row_t = dim_tiempo.sample(
        1, weights=dim_tiempo['mes'].map(dict(enumerate(pesos_mes, 1))),
        random_state=None,
    ).iloc[0]

    filas_f.append({
        'id_venta':         i,
        'id_tiempo':        int(row_t['id_tiempo']),
        'id_producto':      id_prod,
        'id_cliente':       random.choice(ids_cliente),
        'id_tienda':        random.choice(ids_tienda),
        'id_vendedor':      random.choice(ids_vendedor),
        'nro_comprobante':  f'F{random.randint(1, 999):03d}-{random.randint(1, 9999):04d}',
        'nro_linea':        random.randint(1, 10),
        'cantidad':         cantidad,
        'precio_unit_sol':  precio_unit,
        'monto_bruto_sol':  monto_bruto,
        'descuento_sol':    descuento,
        'monto_neto_sol':   monto_neto,
        'costo_sol':        costo,
        'margen_bruto_sol': margen,
        'igv_sol':          igv,
    })

fact_ventas = pd.DataFrame(filas_f)
fact_ventas.to_csv('datamart_ventas/FACT_VENTAS.csv', index=False)
print(f'FACT_VENTAS: {len(fact_ventas)} filas generadas.')
print(f'Monto neto total: S/ {fact_ventas["monto_neto_sol"].sum():,.2f}')
print(fact_ventas[['id_venta', 'id_tiempo', 'id_producto', 'cantidad',
                    'monto_neto_sol', 'margen_bruto_sol']].head(5).to_string())


# =============================================================
# PASO 7: Verificacion de integridad referencial
# =============================================================
def validar_fk(fact, dim, col_fk, col_pk, nombre_dim):
    ids_fact = set(fact[col_fk].unique())
    ids_dim = set(dim[col_pk].unique())
    huerfanos = ids_fact - ids_dim
    if huerfanos:
        print(f'  [ERROR] {nombre_dim}: {len(huerfanos)} FK sin correspondencia: {list(huerfanos)[:5]}')
    else:
        cobertura = len(ids_fact) / len(ids_dim) * 100
        print(f'  [OK] {nombre_dim}: todas las FK validas. Cobertura: {cobertura:.1f}%')


print('=== VALIDACION DE INTEGRIDAD REFERENCIAL ===')
validar_fk(fact_ventas, dim_tiempo, 'id_tiempo', 'id_tiempo', 'DIM_TIEMPO')
validar_fk(fact_ventas, dim_producto, 'id_producto', 'id_producto', 'DIM_PRODUCTO')
validar_fk(fact_ventas, dim_cliente, 'id_cliente', 'id_cliente', 'DIM_CLIENTE')
validar_fk(fact_ventas, dim_tienda, 'id_tienda', 'id_tienda', 'DIM_TIENDA')
validar_fk(fact_ventas, dim_vendedor, 'id_vendedor', 'id_vendedor', 'DIM_VENDEDOR')
print('=== FIN DE VALIDACION ===')
