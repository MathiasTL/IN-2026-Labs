# Guía de continuidad — seguir el Lab 3 en la laptop Windows

Este documento es el punto de partida en la otra laptop. `PLAN.md` es el registro
fase a fase de lo ya hecho (con notas Windows en cada fase); esta guía es la
secuencia de arranque para no perder tiempo ni repetir trabajo innecesario.

## 1. Qué copiar de esta Mac a la laptop Windows

Toda la carpeta `Lab03_TorresLezamaMathias/`, en particular:

- `datos/` (los 8 CSV + LEEME.txt)
- `dm_mercandina_ddl.sql`
- `dm_mercandina_dim.sql`
- `dm_mercandina_scd2.sql`
- `dm_mercandina_carga.sql`
- `dm_mercandina_olap.sql`
- `cuadres_control_borrador.md`
- `PLAN.md`
- `Lab Guide 3 Business Intelligence.pdf`

Los 5 scripts SQL son **portables tal cual** entre Mac y Windows: no usan nada
específico de macOS. Lo único que cambia por máquina es la ruta absoluta que
aparece en los `LOAD DATA LOCAL INFILE` de `dm_mercandina_dim.sql` — hay que
editarla para que apunte a donde queden los CSV en Windows (paso 4).

## 2. Instalar MySQL 8 en Windows

1. Descargar "MySQL Installer" desde el sitio oficial de MySQL (Community Server 8.0+).
2. Durante la instalación, dejar el servicio "MySQL80" configurado para iniciar automáticamente.
3. Anotar la contraseña de `root` que se defina (en la Mac quedó sin contraseña; en Windows el instalador normalmente sí pide una).

## 3. Verificar el entorno (equivalente a la Fase 1 ya hecha en Mac)

En una consola (`cmd` o PowerShell):

```
mysql -u root -p -e "SELECT VERSION(); SHOW VARIABLES LIKE 'secure_file_priv'; SHOW VARIABLES LIKE 'local_infile';"
```

- Si `secure_file_priv` no es `NULL` ni vacío, copiar los CSV a esa ruta o usar `LOAD DATA LOCAL INFILE` (igual que en la Mac).
- Si `local_infile` está en `OFF`:

```
mysql -u root -p -e "SET GLOBAL local_infile = 1;"
```

Igual que en la Mac, esto no persiste entre reinicios del servicio — repetirlo si hace falta.

## 4. Editar las rutas de los CSV en `dm_mercandina_dim.sql`

El archivo tiene 8 sentencias `LOAD DATA LOCAL INFILE '/Users/mathiastl/.../datos/archivo.csv'`.
Reemplazar esa ruta por la ruta real en Windows, por ejemplo:

```
LOAD DATA LOCAL INFILE 'C:/lab3/datos/productos.csv'
```

(usar barras normales `/` o barras invertidas dobles `\\`; con barra invertida simple MySQL falla).

## 5. Recrear el datamart completo desde cero

Esto sirve doble propósito: te deja trabajando en Windows Y cumple la
"condición de aceptación" de la guía (verificar que los 4 scripts corren de
principio a fin sobre una base de datos vacía, sin intervención manual) —
algo que en la Mac ejecutamos en pasos separados y todavía no probamos de
corrido.

En orden, sin saltarse ninguno:

```
mysql -u root -p < dm_mercandina_ddl.sql
mysql --local-infile=1 -u root -p < dm_mercandina_dim.sql
mysql -u root -p < dm_mercandina_scd2.sql
mysql -u root -p < dm_mercandina_carga.sql
mysql -u root -p < dm_mercandina_olap.sql
```

Después de correrlos, confirmar que los números de salida coinciden con los
que ya están documentados en `PLAN.md` y `cuadres_control_borrador.md`
(106,708 filas en `fact_venta`, importe total 3,430,651.54, etc.). Si algo no
cuadra, revisar primero el paso 4 (ruta de los CSV) — es la causa más común de
error al migrar de máquina.

## 6. A partir de ahí

- **Fase 10 (Actividad propuesta)**: se puede seguir haciendo en cualquiera de las dos laptops, es SQL puro. Retomamos cuando quieras.
- **Etapa 10 (Power BI)**: única tarea exclusiva de la laptop Windows. Abrir Power BI Desktop y seguir la Tabla 10 de la guía (conector MySQL, seleccionar solo las 7 tablas sin prefijo `stg_`, relaciones, medidas DAX, jerarquías). Power BI va a pedir "MySQL Connector/NET" si no lo tenés instalado — el propio Power BI ofrece el link de descarga la primera vez que lo necesita.
- Seguí actualizando `PLAN.md` fase a fase, igual que hicimos en la Mac, para que el historial de avance quede en un solo lugar.
