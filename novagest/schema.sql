-- ==========================================================
-- SCRIPT COMPLETO Y UNIFICADO PARA IGOR POS (NOVAGEST_DB)
-- ==========================================================

-- TABLA DE INQUILINOS / NEGOCIOS (SaaS Multi-tenant)
CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo_modulo VARCHAR(20) NOT NULL CHECK (tipo_modulo IN ('GASTRONOMIA', 'COMERCIO')),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    suscripcion_estado VARCHAR(20) DEFAULT 'PRUEBA_GRATIS',
    fin_prueba_gratis TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days',
    plan_tipo VARCHAR(20) DEFAULT 'NINGUNO'
);

-- USUARIOS DEL SISTEMA
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) DEFAULT 'CAJERO' CHECK (rol IN ('ADMIN', 'CAJERO', 'MESERO'))
);

-- CATEGORÍAS
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
    nombre VARCHAR(50) NOT NULL
);

-- PRODUCTOS (Versión robusta y unificada con soporte multi-tenant)
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
    categoria_id INT REFERENCES categorias(id),
    codigo_barras VARCHAR(50),
    nombre VARCHAR(100) NOT NULL,
    variante_talla_color VARCHAR(50),
    numero_serie_imei VARCHAR(100),
    costo_adquisicion NUMERIC(12, 2) NOT NULL DEFAULT 0,
    precio_venta NUMERIC(12, 2) NOT NULL DEFAULT 0,
    stock_actual INT NOT NULL DEFAULT 0,
    stock_minimo INT NOT NULL DEFAULT 5
);

-- CONTROL DE CAJA
CREATE TABLE IF NOT EXISTS cajas (
    id SERIAL PRIMARY KEY,
    empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
    usuario_id INT REFERENCES usuarios(id),
    monto_inicial NUMERIC(12, 2) NOT NULL,
    efectivo_esperado NUMERIC(12, 2) NOT NULL,
    efectivo_real NUMERIC(12, 2) DEFAULT 0,
    diferencia NUMERIC(12, 2) DEFAULT 0,
    estado VARCHAR(10) DEFAULT 'ABIERTA' CHECK (estado IN ('ABIERTA', 'CERRADA')),
    fecha_apertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMP
);

-- REGISTRO DE VENTAS
CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
    caja_id INT REFERENCES cajas(id),
    usuario_id INT REFERENCES usuarios(id),
    subtotal NUMERIC(12, 2) NOT NULL,
    descuento NUMERIC(12, 2) DEFAULT 0,
    total NUMERIC(12, 2) NOT NULL,
    efectivo_entregado NUMERIC(12, 2) DEFAULT 0,
    cambio_devuelto NUMERIC(12, 2) DEFAULT 0,
    metodo_pago VARCHAR(20) CHECK (metodo_pago IN ('EFECTIVO', 'TRANSFERENCIA', 'TARJETA_DEBITO', 'TARJETA_CREDITO', 'COMBINADO')),
    fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS detalle_ventas (
    id SERIAL PRIMARY KEY,
    venta_id INT REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INT REFERENCES productos(id),
    cantidad INT NOT NULL,
    precio_unitario NUMERIC(12, 2) NOT NULL,
    costo_unitario NUMERIC(12, 2) NOT NULL
);

-- TRAZABILIDAD DE INVENTARIO
CREATE TABLE IF NOT EXISTS historial_inventario (
    id SERIAL PRIMARY KEY,
    empresa_id INT REFERENCES empresas(id) ON DELETE CASCADE,
    producto_id INT REFERENCES productos(id) ON DELETE CASCADE,
    tipo_movimiento VARCHAR(20) CHECK (tipo_movimiento IN ('ENTRADA_COMPRA', 'SALIDA_VENTA', 'AJUSTE', 'DEVOLUCION_PROVEEDOR', 'PERDIDA_DANO')),
    cantidad INT NOT NULL,
    motivo TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CONFIGURACIÓN DE MESAS (Para gastronomía/restaurantes)
CREATE TABLE IF NOT EXISTS mesas_config (
    id SERIAL PRIMARY KEY,
    nombre_mesa VARCHAR(50) NOT NULL,
    estado VARCHAR(20) DEFAULT 'Libre'
);

-- CLIENTES
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    identificacion VARCHAR(50) NOT NULL
);

-- FACTURAS
CREATE TABLE IF NOT EXISTS facturas (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes(id),
    subtotal NUMERIC(10, 2) NOT NULL,
    propina NUMERIC(10, 2) NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    metodo_pago VARCHAR(30) NOT NULL,
    efectivo_recibido NUMERIC(10, 2) DEFAULT 0,
    cambio_devuelto NUMERIC(10, 2) DEFAULT 0,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);