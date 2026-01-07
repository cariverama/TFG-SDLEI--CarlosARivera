"""
Sistema de gestion de emergencias
Procesa alertas y asigna recursos
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import os
import sys
from decoder import PayloadDecoder

# Fix para encoding en Windows
if sys.platform == 'win32':
    os.environ['PGCLIENTENCODING'] = 'UTF8'
    os.environ['PYTHONIOENCODING'] = 'utf-8'

logger = logging.getLogger(__name__)


class SistemaEmergencias:
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.decoder = PayloadDecoder()
        self.conn = None
        self.cursor = None
    
    def conectar_bd(self) -> bool:
        """Conecta a la base de datos"""
        try:
            self.conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config.get('port', 5432),
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                options='-c client_encoding=UTF8'
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info(f"Conectado a BD: {self.db_config['database']}")
            return True
        except Exception as e:
            logger.error(f"Error conectando a BD: {e}")
            return False
    
    def desconectar_bd(self):
        """Cierra la conexion"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Desconectado de BD")
    
    def procesar_alerta(self, dispositivo_id: str, payload_base64: str) -> dict:
        """Procesa una alerta: decodifica, registra y asigna recurso"""
        logger.info(f"Procesando alerta de dispositivo: {dispositivo_id}")
        
        # Decodificar payload
        datos = self.decoder.decode(payload_base64)
        if not datos:
            return {'exito': False, 'error': 'Payload invalido'}
        
        # Registrar alerta
        alerta_id = self._registrar_alerta(
            dispositivo_id=dispositivo_id,
            tipo=datos['tipo'],
            latitud=datos['latitud'],
            longitud=datos['longitud']
        )
        
        if not alerta_id:
            return {'exito': False, 'error': 'Error en BD'}
        
        logger.info(f"Alerta registrada: ID {alerta_id}")
        
        # Asignar recurso
        asignacion = self._asignar_recurso(alerta_id, datos['tipo'])
        
        if not asignacion:
            logger.warning(f"No hay recursos disponibles")
            return {
                'exito': False,
                'alerta_id': alerta_id,
                'error': 'Sin recursos disponibles'
            }
        
        logger.info(f"Recurso asignado: {asignacion['nombre']}")
        
        return {
            'exito': True,
            'alerta_id': alerta_id,
            'dispositivo_id': dispositivo_id,
            'tipo': datos['tipo'],
            'asignacion': {
                'recurso_id': asignacion['id'],
                'nombre': asignacion['nombre'],
                'municipio': asignacion['municipio'],
                'distancia_metros': float(asignacion['distancia_metros']),
                'tiempo_estimado_minutos': asignacion['tiempo_estimado_segundos'] // 60
            }
        }
    
    def _registrar_alerta(self, dispositivo_id: str, tipo: str, 
                         latitud: float, longitud: float) -> int:
        """Inserta una alerta en la base de datos"""
        try:
            query = """
                INSERT INTO alertas (dispositivo_id, tipo, ubicacion) 
                VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                RETURNING id
            """
            
            self.cursor.execute(query, (dispositivo_id, tipo, longitud, latitud))
            result = self.cursor.fetchone()
            self.conn.commit()
            
            return result['id'] if result else None
            
        except Exception as e:
            logger.error(f"Error registrando alerta: {e}")
            self.conn.rollback()
            return None
    
    def _asignar_recurso(self, alerta_id: int, tipo: str) -> dict:
        """Busca el recurso mas cercano disponible del tipo correspondiente"""
        try:
            # Usa ST_Distance de PostGIS para calcular distancias
            query = """
                WITH alerta AS (
                    SELECT id, tipo, ubicacion
                    FROM alertas
                    WHERE id = %s
                )
                SELECT 
                    pe.id,
                    pe.nombre,
                    pe.codigo,
                    pe.municipio,
                    pe.telefono,
                    ST_Distance(
                        pe.ubicacion::geography,
                        alerta.ubicacion::geography
                    ) AS distancia_metros,
                    (
                        (ST_Distance(pe.ubicacion::geography, alerta.ubicacion::geography) / 1000.0) / 
                        (pe.velocidad_promedio_kmh / 60.0) * 60 + 
                        pe.tiempo_preparacion_segundos
                    )::INTEGER AS tiempo_estimado_segundos
                FROM puntos_emergencia pe
                CROSS JOIN alerta
                WHERE 
                    pe.tipo = alerta.tipo
                    AND pe.disponible = true
                ORDER BY distancia_metros ASC
                LIMIT 1
            """
            
            self.cursor.execute(query, (alerta_id,))
            recurso = self.cursor.fetchone()
            
            if not recurso:
                return None
            
            # Crear registro de asignacion
            query_asignar = """
                INSERT INTO asignaciones (
                    alerta_id,
                    punto_emergencia_id,
                    distancia_metros,
                    tiempo_estimado_segundos
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """
            
            self.cursor.execute(query_asignar, (
                alerta_id,
                recurso['id'],
                recurso['distancia_metros'],
                recurso['tiempo_estimado_segundos']
            ))
            
            self.conn.commit()
            
            return recurso
            
        except Exception as e:
            logger.error(f"Error asignando recurso: {e}")
            self.conn.rollback()
            return None
    
    def resolver_alerta(self, alerta_id: int) -> bool:
        """
        Marca una alerta como resuelta y libera el recurso asignado
        
        Args:
            alerta_id: ID de la alerta a resolver
            
        Returns:
            True si se resolvio correctamente
        """
        try:
            query = """
                UPDATE alertas 
                SET estado = 'resuelta'
                WHERE id = %s AND estado != 'resuelta'
                RETURNING id
            """
            
            self.cursor.execute(query, (alerta_id,))
            result = self.cursor.fetchone()
            self.conn.commit()
            
            if result:
                logger.info(f"Alerta {alerta_id} resuelta, recurso liberado")
                return True
            else:
                logger.warning(f"Alerta {alerta_id} no encontrada o ya estaba resuelta")
                return False
                
        except Exception as e:
            logger.error(f"Error resolviendo alerta: {e}")
            self.conn.rollback()
            return False
    
    def __enter__(self):
        self.conectar_bd()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.desconectar_bd()
