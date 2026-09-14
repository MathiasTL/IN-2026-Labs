DROP DATABASE IF EXISTS dm_mercandina;
CREATE DATABASE dm_mercandina
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE dm_mercandina;

-- ================= AREA DE STAGING (espejo del origen) =================
CREATE TABLE stg_producto (
  cod_producto     VARCHAR(20),   nombre_producto VARCHAR(200),
  marca            VARCHAR(80),   categoria       VARCHAR(60),
  subcategoria     VARCHAR(60),   unidad_medida   VARCHAR(15),
  es_marca_propia  VARCHAR(5),
  precio_lista     VARCHAR(20),
  costo_unitario   VARCHAR(20)
) ENGINE=InnoDB;

CREATE TABLE stg_producto_cambio LIKE stg_producto;
ALTER TABLE stg_producto_cambio ADD COLUMN fecha_cambio VARCHAR(20);

CREATE TABLE stg_tienda (
  cod_tienda     VARCHAR(15),  nombre_tienda  VARCHAR(120),
  formato        VARCHAR(30),  distrito       VARCHAR(60),
  ciudad         VARCHAR(60),  region         VARCHAR(60),
  area_m2        VARCHAR(20),  fecha_apertura VARCHAR(20)
) ENGINE=InnoDB;

CREATE TABLE stg_tienda_cambio LIKE stg_tienda;
ALTER TABLE stg_tienda_cambio ADD COLUMN fecha_cambio VARCHAR(20);

CREATE TABLE stg_cliente (
  doc_cliente VARCHAR(20), nombre   VARCHAR(120), segmento   VARCHAR(30),
  distrito    VARCHAR(60), ciudad   VARCHAR(60),  fecha_alta VARCHAR(20)
) ENGINE=InnoDB;

CREATE TABLE stg_cliente_cambio LIKE stg_cliente;
ALTER TABLE stg_cliente_cambio ADD COLUMN fecha_cambio VARCHAR(20);

CREATE TABLE stg_promocion (
  cod_promocion  VARCHAR(15), nombre_promocion VARCHAR(120),
  tipo_promocion VARCHAR(40), fecha_inicio     VARCHAR(20),
  fecha_fin      VARCHAR(20)
) ENGINE=InnoDB;

CREATE TABLE stg_venta_pos (
  nro_ticket        VARCHAR(30), fecha_emision   VARCHAR(20),
  cod_tienda        VARCHAR(15), cod_producto    VARCHAR(20),
  doc_cliente       VARCHAR(20), cod_promocion   VARCHAR(15),
  tipo_comprobante  VARCHAR(20), forma_pago      VARCHAR(25),
  canal             VARCHAR(20), flag_devolucion VARCHAR(5),
  cantidad          VARCHAR(20), precio_unitario VARCHAR(20),
  costo_unitario    VARCHAR(20), descuento       VARCHAR(20),
  importe_neto      VARCHAR(20),
  KEY ix_stg_fecha (fecha_emision),
  KEY ix_stg_prod  (cod_producto)
) ENGINE=InnoDB;

-- ================= DIMENSIONES =================
CREATE TABLE dim_tiempo (
  tiempo_key    INT           NOT NULL,  -- AAAAMMDD
  fecha         DATE          NOT NULL,
  anio          SMALLINT      NOT NULL,
  trimestre     TINYINT       NOT NULL,
  mes           TINYINT       NOT NULL,
  nombre_mes    VARCHAR(12)   NOT NULL,
  anio_mes      CHAR(7)       NOT NULL,
  dia_mes       TINYINT       NOT NULL,
  dia_semana    TINYINT       NOT NULL,
  nombre_dia    VARCHAR(10)   NOT NULL,
  es_fin_semana TINYINT(1)    NOT NULL,
  es_dia_pago   TINYINT(1)    NOT NULL,
  PRIMARY KEY (tiempo_key),
  UNIQUE KEY ux_tiempo_fecha (fecha)
) ENGINE=InnoDB;

CREATE TABLE dim_producto (
  producto_key      INT           NOT NULL AUTO_INCREMENT,
  producto_id       VARCHAR(20)   NOT NULL,   -- clave natural
  nombre_producto   VARCHAR(200)  NOT NULL,
  marca             VARCHAR(80)   NOT NULL,
  categoria         VARCHAR(60)   NOT NULL,   -- SCD Tipo 2
  subcategoria      VARCHAR(60)   NOT NULL,   -- SCD Tipo 2
  unidad_medida     VARCHAR(15)   NOT NULL,
  es_marca_propia   TINYINT(1)    NOT NULL DEFAULT 0,
  precio_lista      DECIMAL(12,2) NULL,
  costo_estandar    DECIMAL(12,2) NULL,
  fecha_inicio_vig  DATE          NOT NULL,
  fecha_fin_vig     DATE          NOT NULL DEFAULT '9999-12-31',
  es_vigente        TINYINT(1)    NOT NULL DEFAULT 1,
  fecha_carga       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (producto_key),
  KEY ix_prod_natural (producto_id, fecha_inicio_vig, fecha_fin_vig),
  KEY ix_prod_categoria (categoria, subcategoria)
) ENGINE=InnoDB;

CREATE TABLE dim_tienda (
  tienda_key       INT           NOT NULL AUTO_INCREMENT,
  tienda_id        VARCHAR(15)   NOT NULL,
  nombre_tienda    VARCHAR(120)  NOT NULL,
  formato          VARCHAR(30)   NOT NULL,   -- SCD Tipo 2
  distrito         VARCHAR(60)   NOT NULL,
  ciudad           VARCHAR(60)   NOT NULL,
  region           VARCHAR(60)   NOT NULL,
  area_m2          DECIMAL(10,2) NOT NULL,   -- SCD Tipo 2
  fecha_apertura   DATE          NULL,       -- SCD Tipo 0
  fecha_inicio_vig DATE          NOT NULL,
  fecha_fin_vig    DATE          NOT NULL DEFAULT '9999-12-31',
  es_vigente       TINYINT(1)    NOT NULL DEFAULT 1,
  PRIMARY KEY (tienda_key),
  KEY ix_tienda_natural (tienda_id, fecha_inicio_vig, fecha_fin_vig)
) ENGINE=InnoDB;

CREATE TABLE dim_cliente (
  cliente_key      INT           NOT NULL AUTO_INCREMENT,
  cliente_id       VARCHAR(20)   NOT NULL,
  nombre           VARCHAR(120)  NOT NULL,
  segmento         VARCHAR(30)   NOT NULL,   -- SCD Tipo 2
  distrito         VARCHAR(60)   NOT NULL,   -- SCD Tipo 2
  ciudad           VARCHAR(60)   NOT NULL,   -- SCD Tipo 2
  fecha_alta       DATE          NULL,       -- SCD Tipo 0
  fecha_inicio_vig DATE          NOT NULL,
  fecha_fin_vig    DATE          NOT NULL DEFAULT '9999-12-31',
  es_vigente       TINYINT(1)    NOT NULL DEFAULT 1,
  PRIMARY KEY (cliente_key),
  KEY ix_cli_natural (cliente_id, fecha_inicio_vig, fecha_fin_vig)
) ENGINE=InnoDB;

CREATE TABLE dim_promocion (
  promocion_key    INT           NOT NULL AUTO_INCREMENT,
  promocion_id     VARCHAR(15)   NOT NULL,
  nombre_promocion VARCHAR(120)  NOT NULL,
  tipo_promocion   VARCHAR(40)   NOT NULL,
  fecha_inicio     DATE          NOT NULL,
  fecha_fin        DATE          NULL,
  PRIMARY KEY (promocion_key),
  KEY ix_promo_natural (promocion_id)
) ENGINE=InnoDB;

-- Dimension JUNK: agrupa indicadores de baja cardinalidad
CREATE TABLE dim_transaccion (
  transaccion_key  INT          NOT NULL AUTO_INCREMENT,
  tipo_comprobante VARCHAR(20)  NOT NULL,
  forma_pago       VARCHAR(25)  NOT NULL,
  canal            VARCHAR(20)  NOT NULL,
  es_devolucion    TINYINT(1)   NOT NULL,
  PRIMARY KEY (transaccion_key),
  UNIQUE KEY ux_trans (tipo_comprobante, forma_pago, canal, es_devolucion)
) ENGINE=InnoDB;

-- ================= TABLA DE HECHOS =================
CREATE TABLE fact_venta (
  tiempo_key        INT            NOT NULL,
  producto_key      INT            NOT NULL,
  tienda_key        INT            NOT NULL,
  cliente_key       INT            NOT NULL,
  promocion_key     INT            NOT NULL,
  transaccion_key   INT            NOT NULL,
  nro_ticket        VARCHAR(30)    NOT NULL,  -- dimension degenerada
  cantidad          DECIMAL(12,3)  NOT NULL,
  importe_venta     DECIMAL(18,2)  NOT NULL,
  importe_costo     DECIMAL(18,2)  NOT NULL,
  importe_descuento DECIMAL(18,2)  NOT NULL DEFAULT 0,
  PRIMARY KEY (tiempo_key, producto_key, tienda_key, nro_ticket),
  KEY ix_fact_producto (producto_key),
  KEY ix_fact_tienda   (tienda_key),
  KEY ix_fact_cliente  (cliente_key),
  KEY ix_fact_promo    (promocion_key),
  KEY ix_fact_ticket   (nro_ticket)
)
ENGINE=InnoDB
PARTITION BY RANGE (tiempo_key) (
  PARTITION p2025   VALUES LESS THAN (20260101),
  PARTITION p2026q1 VALUES LESS THAN (20260401),
  PARTITION p2026q2 VALUES LESS THAN (20260701),
  PARTITION p2026q3 VALUES LESS THAN (20261001),
  PARTITION p2026q4 VALUES LESS THAN (20270101),
  PARTITION pmax    VALUES LESS THAN MAXVALUE
);
