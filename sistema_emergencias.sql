-- Base de datos del sistema de gestion de alertas de emergencia
-- Requiere la extension PostGIS para calculos geograficos

CREATE EXTENSION IF NOT EXISTS postgis;

-- Tipos de datos personalizados
CREATE TYPE tipo_emergencia AS ENUM (
    'medica',
    'policial',
    'bomberos',
    'rescate'
);

CREATE TYPE estado_alerta AS ENUM (
    'pendiente',
    'asignada',
    'resuelta'
);

-- Tabla principal de alertas recibidas
CREATE TABLE alertas (
    id SERIAL PRIMARY KEY,
    dispositivo_id VARCHAR(50) NOT NULL,
    tipo tipo_emergencia NOT NULL,
    ubicacion GEOMETRY(Point, 4326) NOT NULL,
    estado estado_alerta DEFAULT 'pendiente' NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_ubicacion CHECK (ST_SRID(ubicacion) = 4326)
);

CREATE INDEX idx_alertas_estado ON alertas(estado);
CREATE INDEX idx_alertas_ubicacion ON alertas USING GIST(ubicacion);

-- Recursos de emergencia disponibles en Las Hurdes
CREATE TABLE puntos_emergencia (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    tipo tipo_emergencia NOT NULL,
    ubicacion GEOMETRY(Point, 4326) NOT NULL,
    municipio VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    capacidad_actual INTEGER DEFAULT 0,
    capacidad_maxima INTEGER DEFAULT 5,
    disponible BOOLEAN DEFAULT true NOT NULL,
    velocidad_promedio_kmh NUMERIC(5,2) DEFAULT 50.0,
    tiempo_preparacion_segundos INTEGER DEFAULT 180,
    CONSTRAINT chk_ubicacion_punto CHECK (ST_SRID(ubicacion) = 4326),
    CONSTRAINT chk_capacidad CHECK (
        capacidad_actual >= 0 AND 
        capacidad_maxima > 0 AND 
        capacidad_actual <= capacidad_maxima
    )
);

CREATE INDEX idx_puntos_tipo ON puntos_emergencia(tipo);
CREATE INDEX idx_puntos_disponible ON puntos_emergencia(disponible) WHERE disponible = true;
CREATE INDEX idx_puntos_ubicacion ON puntos_emergencia USING GIST(ubicacion);

-- Relacion entre alertas y recursos asignados
CREATE TABLE asignaciones (
    id SERIAL PRIMARY KEY,
    alerta_id INTEGER NOT NULL REFERENCES alertas(id) ON DELETE CASCADE,
    punto_emergencia_id INTEGER NOT NULL REFERENCES puntos_emergencia(id),
    distancia_metros NUMERIC(10,2) NOT NULL,
    tiempo_estimado_segundos INTEGER NOT NULL,
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_distancia CHECK (distancia_metros >= 0),
    CONSTRAINT chk_tiempo CHECK (tiempo_estimado_segundos > 0)
);

CREATE INDEX idx_asignaciones_alerta ON asignaciones(alerta_id);
CREATE INDEX idx_asignaciones_punto ON asignaciones(punto_emergencia_id);

-- Trigger: cuando se asigna un recurso, marcarlo como ocupado
CREATE OR REPLACE FUNCTION ocupar_recurso()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE puntos_emergencia 
    SET capacidad_actual = capacidad_actual + 1,
        disponible = (capacidad_actual + 1 < capacidad_maxima)
    WHERE id = NEW.punto_emergencia_id;
    
    UPDATE alertas 
    SET estado = 'asignada'
    WHERE id = NEW.alerta_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ocupar_recurso
    AFTER INSERT ON asignaciones
    FOR EACH ROW EXECUTE FUNCTION ocupar_recurso();

-- Trigger: cuando se resuelve una alerta, liberar el recurso
CREATE OR REPLACE FUNCTION liberar_recurso()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado = 'resuelta' AND OLD.estado != 'resuelta' THEN
        UPDATE puntos_emergencia pe
        SET capacidad_actual = GREATEST(capacidad_actual - 1, 0),
            disponible = (GREATEST(capacidad_actual - 1, 0) < capacidad_maxima)
        WHERE pe.id IN (
            SELECT punto_emergencia_id 
            FROM asignaciones 
            WHERE alerta_id = NEW.id
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_liberar_recurso
    AFTER UPDATE ON alertas
    FOR EACH ROW EXECUTE FUNCTION liberar_recurso();

-- Datos iniciales: 8 puntos de emergencia en Las Hurdes

-- Centros de salud
INSERT INTO puntos_emergencia (codigo, nombre, tipo, ubicacion, municipio, telefono, capacidad_maxima, velocidad_promedio_kmh) VALUES
('CS-CAMINO-01', 'Centro de Salud de Caminomorisco', 'medica', ST_SetSRID(ST_MakePoint(-6.2901, 40.3642), 4326), 'Caminomorisco', '927434001', 3, 45.0),
('CL-NUNO-01', 'Consultorio Local de Nuñomoral', 'medica', ST_SetSRID(ST_MakePoint(-6.2534, 40.4056), 4326), 'Nuñomoral', '927435012', 2, 40.0),
('CL-PINO-01', 'Consultorio Local de Pinofranqueado', 'medica', ST_SetSRID(ST_MakePoint(-6.3205, 40.3333), 4326), 'Pinofranqueado', '927436023', 2, 40.0);

-- Puestos Guardia Civil
INSERT INTO puntos_emergencia (codigo, nombre, tipo, ubicacion, municipio, telefono, capacidad_maxima, velocidad_promedio_kmh) VALUES
('GC-CAMINO-01', 'Puesto Guardia Civil Caminomorisco', 'policial', ST_SetSRID(ST_MakePoint(-6.2889, 40.3655), 4326), 'Caminomorisco', '927434100', 4, 60.0),
('GC-NUNO-01', 'Puesto Guardia Civil Nuñomoral', 'policial', ST_SetSRID(ST_MakePoint(-6.2545, 40.4067), 4326), 'Nuñomoral', '927435100', 3, 60.0);

-- Servicios de bomberos
INSERT INTO puntos_emergencia (codigo, nombre, tipo, ubicacion, municipio, telefono, capacidad_maxima, velocidad_promedio_kmh, tiempo_preparacion_segundos) VALUES
('PB-CAMINO-01', 'Parque Bomberos Caminomorisco', 'bomberos', ST_SetSRID(ST_MakePoint(-6.2912, 40.3628), 4326), 'Caminomorisco', '927434200', 5, 50.0, 300),
('PC-PINO-01', 'Proteccion Civil Pinofranqueado', 'bomberos', ST_SetSRID(ST_MakePoint(-6.3198, 40.3345), 4326), 'Pinofranqueado', '927436200', 3, 45.0, 360);

-- Rescate en montaña
INSERT INTO puntos_emergencia (codigo, nombre, tipo, ubicacion, municipio, telefono, capacidad_maxima, velocidad_promedio_kmh, tiempo_preparacion_segundos) VALUES
('GREIM-01', 'GREIM Rescate Montaña', 'rescate', ST_SetSRID(ST_MakePoint(-6.2878, 40.3670), 4326), 'Caminomorisco', '927434300', 4, 40.0, 420);

-- Verificar que se creó todo correctamente
SELECT 'Base de datos creada' AS estado;
SELECT tipo, COUNT(*) AS cantidad FROM puntos_emergencia GROUP BY tipo;
