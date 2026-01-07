# Sistema de Gestión de Alertas de Emergencia

Sistema de gestión de alertas de emergencia para la comarca de Las Hurdes (Cáceres) basado en LoRaWAN, PostgreSQL con PostGIS y Python.

## Descripción

El sistema recibe alertas de emergencia desde dispositivos LoRaWAN y asigna automáticamente el recurso más cercano y disponible.

**Funcionamiento:**
1. El dispositivo LoRaWAN envía una alerta con ID, coordenadas GPS y tipo de emergencia
2. Los datos se registran en PostgreSQL con PostGIS
3. El algoritmo determina qué recursos son apropiados para el tipo de emergencia y están disponibles
4. Calcula cuál está más cerca usando PostGIS
5. Asigna el recurso y actualiza su estado de disponibilidad

## Tecnologías

- Python 3.12.0
- PostgreSQL 16 con PostGIS 3.4
- paho-mqtt 2.1.0
- psycopg2-binary 2.9.11

## Instalación

### Requisitos previos

1. PostgreSQL 16 con extensión PostGIS
2. Python 3.12 o superior
3. pgAdmin 4 (recomendado para Windows)

### Pasos de instalación

**1. Instalar dependencias de Python:**

```bash
pip install -r requirements.txt
```

Durante el desarrollo usé `psycopg2-binary==2.9.11` y `paho-mqtt==2.1.0`.

**2. Crear la base de datos:**

Lo más fácil es usar pgAdmin 4:
- Crear nueva base de datos con nombre `sistema_emergencias`
- **Importante**: En la pestaña Definition, configurar Encoding: UTF8, Collation: C, Character type: C
- Abrir Query Tool (botón derecho sobre la BD) y ejecutar todo el contenido del archivo `sistema_emergencias.sql`

Si prefieres línea de comandos:
```sql
CREATE DATABASE sistema_emergencias
    WITH ENCODING='UTF8' LC_COLLATE='C' LC_CTYPE='C';
```

Luego cargar el script:
```bash
psql -U postgres -d sistema_emergencias -f sistema_emergencias.sql
```

Para verificar que se creó bien:
```sql
SELECT COUNT(*) FROM puntos_emergencia;
-- Debe devolver: 8
```

**3. Configurar la conexión:**

Copiar `config.example.py` a `config.py` y poner tu contraseña de PostgreSQL en `DB_CONFIG`.

## Uso

### Prueba rápida del sistema

La forma más sencilla de probar el sistema es ejecutar:

```bash
python prueba_sistema.py
```

Este script ejecuta 4 casos de prueba automáticos sin necesidad de tener MQTT instalado.

Si todo funciona bien, deberías ver algo así:
```
SISTEMA DE GESTION DE ALERTAS DE EMERGENCIA
============================================================

Conectando a base de datos...
Conexion establecida

EJECUTANDO PRUEBAS
============================================================

PRUEBA 1: Emergencia Medica en Caminomorisco
...
RESULTADO: EXITOSO
  Recurso asignado: Centro de Salud de Caminomorisco
  Distancia: 34 m
  Tiempo estimado: 3 min

[3 pruebas más...]

RESUMEN
============================================================
Total: 4
Exitosas: 4
Fallidas: 0

TODAS LAS PRUEBAS PASARON
```

### Uso con MQTT (avanzado)

Si tienes instalado Mosquitto o ChirpStack, puedes probar el flujo completo:

En una terminal:
```bash
python listener.py
```

En otra terminal:
```bash
python test_alerta.py
```

El listener recibirá las alertas simuladas y las procesará en tiempo real.

## Problemas que me encontré

### Error: UnicodeDecodeError 'utf-8'

Este error me dio bastantes quebraderos de cabeza al principio. La causa era que la base de datos no estaba creada con encoding UTF8.

**Solución:** Borrar la base de datos y recrearla con encoding UTF8 explícito como indico arriba. En Windows es especialmente importante forzar UTF8 en la creación.

### Error: psql no se reconoce como comando

En Windows, psql no suele estar en el PATH. Usa pgAdmin 4 que es más cómodo.

### Error: paho-mqtt callback API deprecated

Si ves warnings de paho-mqtt sobre el callback API version 1, asegúrate de tener la versión 2.1.0 y que en el código se usa `mqtt.CallbackAPIVersion.VERSION2`.

### Error de conexión MQTT

Si no tienes Mosquitto instalado, simplemente usa `prueba_sistema.py` que funciona sin necesidad de MQTT.

## Estructura

```
sistema-gestion-emergencias/
├── decoder.py                # Decodificador payloads
├── integracion.py            # Logica y algoritmo
├── listener.py               # Listener MQTT
├── prueba_sistema.py         # Script de prueba
├── test_alerta.py            # Envio alertas MQTT
├── config.py                 # Configuracion (no incluido en repo)
├── config.example.py         # Plantilla de configuracion
├── sistema_emergencias.sql   # Script BD
├── requirements.txt          # Dependencias
└── README.md                 # Este archivo
```

## Base de Datos

### Tablas principales

- `alertas`: Guarda las alertas recibidas con su ubicación y estado
- `puntos_emergencia`: Los 8 recursos de emergencia en Las Hurdes (3 centros médicos, 2 policiales, 2 de bomberos, 1 de rescate)
- `asignaciones`: Relaciona cada alerta con el recurso asignado

### Algoritmo de asignación

El corazón del sistema es una query PostGIS que calcula distancias reales:

```sql
SELECT 
    pe.id, pe.nombre,
    ST_Distance(
        pe.ubicacion::geography,
        alerta.ubicacion::geography
    ) AS distancia_metros
FROM puntos_emergencia pe
WHERE pe.tipo = alerta.tipo AND pe.disponible = true
ORDER BY distancia_metros ASC
LIMIT 1
```

La función `ST_Distance` con el tipo `geography` calcula distancias reales en metros teniendo en cuenta la curvatura de la Tierra. Esto es importante para obtener resultados precisos.

## Formato de Payload

Los dispositivos envían payloads binarios de 11 bytes con esta estructura:

| Bytes | Campo | Descripción |
|-------|-------|-------------|
| 0 | Tipo | 1=médica, 2=policial, 3=bomberos, 4=rescate |
| 1-4 | Latitud | Entero de 4 bytes × 10^6 (big-endian) |
| 5-8 | Longitud | Entero de 4 bytes × 10^6 (big-endian) |
| 9 | Batería | Porcentaje 0-100 |
| 10 | Flags | Reservado |

Ejemplo de emergencia médica en coordenadas (40.3645, -6.2900):
```
Payload en Base64: AQJn6dT/oAWwVQE=
```

## Verificación de resultados

Algunas consultas útiles para revisar que todo funciona bien:

```sql
-- Ver las alertas recibidas
SELECT * FROM alertas ORDER BY fecha_creacion DESC;

-- Ver las asignaciones realizadas
SELECT 
    a.id, a.tipo, 
    pe.nombre AS recurso,
    asig.distancia_metros,
    asig.tiempo_estimado_segundos/60 AS tiempo_min
FROM alertas a
JOIN asignaciones asig ON a.id = asig.alerta_id
JOIN puntos_emergencia pe ON asig.punto_emergencia_id = pe.id;

-- Ver estado de disponibilidad de recursos
SELECT nombre, tipo, disponible, capacidad_actual, capacidad_maxima 
FROM puntos_emergencia;
```

## Notas adicionales

- Desarrollado y probado en Windows 10
- Es fundamental crear la base de datos con encoding UTF-8 para evitar errores
- Para demostrar el funcionamiento basta con ejecutar `prueba_sistema.py`
- Los scripts `listener.py` y `test_alerta.py` solo funcionan si tienes un broker MQTT instalado

## Autor

Trabajo Fin de Grado - Universidad de Extremadura - 2025

