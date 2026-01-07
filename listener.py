"""
Listener MQTT para recibir alertas de ChirpStack
"""

import paho.mqtt.client as mqtt
import json
import logging
import signal
import sys
import os
from integracion import SistemaEmergencias

if sys.platform == 'win32':
    os.environ['PGCLIENTENCODING'] = 'UTF8'
    os.environ['PYTHONIOENCODING'] = 'utf-8'

logger = logging.getLogger(__name__)


class ListenerLoRaWAN:
    
    def __init__(self, mqtt_config: dict, db_config: dict):
        self.mqtt_config = mqtt_config
        self.sistema = SistemaEmergencias(db_config)
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Autenticacion MQTT si es necesaria
        username = mqtt_config.get('username')
        password = mqtt_config.get('password')
        if username and password:
            self.client.username_pw_set(username, password)
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Conectado al broker MQTT")
            topic = self.mqtt_config['topic']
            client.subscribe(topic)
            logger.info(f"Suscrito a: {topic}")
        else:
            logger.error(f"Error de conexion (codigo: {rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"Desconexion inesperada (rc={rc})")
    
    def _on_message(self, client, userdata, msg):
        """Procesa mensajes recibidos"""
        try:
            logger.info("Mensaje recibido")
            
            payload = json.loads(msg.payload.decode('utf-8'))
            
            # Extraer datos de ChirpStack
            dev_eui = payload.get('devEUI', payload.get('deviceName', 'unknown'))
            payload_base64 = payload.get('data', '')
            
            logger.info(f"DevEUI: {dev_eui}")
            
            resultado = self.sistema.procesar_alerta(dev_eui, payload_base64)
            
            if resultado['exito']:
                logger.info("Alerta procesada correctamente")
                asig = resultado['asignacion']
                logger.info(f"Alerta ID: {resultado['alerta_id']}")
                logger.info(f"Recurso: {asig['nombre']} ({asig['municipio']})")
                logger.info(f"Distancia: {asig['distancia_metros']:.0f}m, Tiempo: {asig['tiempo_estimado_minutos']}min")
            else:
                logger.error(f"Error: {resultado.get('error')}")
                
        except json.JSONDecodeError:
            logger.error("JSON invalido")
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
    
    def iniciar(self):
        """Inicia el listener"""
        try:
            logger.info("Iniciando listener LoRaWAN")
            logger.info(f"Broker MQTT: {self.mqtt_config['broker']}:{self.mqtt_config['port']}")
            logger.info(f"Topic: {self.mqtt_config['topic']}")
            
            if not self.sistema.conectar_bd():
                logger.error("No se pudo conectar a BD")
                return False
            
            self.client.connect(
                self.mqtt_config['broker'],
                self.mqtt_config['port'],
                60
            )
            
            logger.info("Listener activo. Presiona Ctrl+C para detener")
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            logger.info("Interrupcion recibida")
            self.detener()
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
    
    def detener(self):
        logger.info("Deteniendo listener")
        self.client.disconnect()
        self.sistema.desconectar_bd()


def signal_handler(sig, frame):
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('sistema_emergencias.log')
        ]
    )
    
    try:
        from config import DB_CONFIG, MQTT_CONFIG
    except ImportError:
        print("Error: No se encontro config.py")
        sys.exit(1)
    
    listener = ListenerLoRaWAN(MQTT_CONFIG, DB_CONFIG)
    listener.iniciar()
