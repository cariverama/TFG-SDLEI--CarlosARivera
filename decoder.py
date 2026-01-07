"""Decodificador de payloads LoRaWAN"""

import base64
import struct
import logging

logger = logging.getLogger(__name__)


class PayloadDecoder:
    """Decodifica los mensajes binarios de los dispositivos"""
    
    TIPOS = {
        1: 'medica',
        2: 'policial',
        3: 'bomberos',
        4: 'rescate'
    }
    
    def decode(self, payload_base64: str) -> dict:
        """
        Decodifica payload de 11 bytes:
        [tipo][lat 4B][lon 4B][bat][flags]
        """
        try:
            payload_bytes = base64.b64decode(payload_base64)
            
            if len(payload_bytes) < 11:
                logger.error(f"Payload incompleto: {len(payload_bytes)} bytes")
                return None
            
            tipo_codigo = payload_bytes[0]
            lat_raw = struct.unpack('>i', payload_bytes[1:5])[0]
            lon_raw = struct.unpack('>i', payload_bytes[5:9])[0]
            bateria = payload_bytes[9]
            
            # Las coordenadas vienen multiplicadas por 10^6
            latitud = lat_raw / 1_000_000.0
            longitud = lon_raw / 1_000_000.0
            tipo = self.TIPOS.get(tipo_codigo, 'medica')
            
            logger.info(f"Payload decodificado: tipo={tipo}, coords=({latitud:.6f}, {longitud:.6f})")
            
            return {
                'tipo': tipo,
                'latitud': latitud,
                'longitud': longitud,
                'bateria': bateria
            }
            
        except Exception as e:
            logger.error(f"Error decodificando: {e}")
            return None
