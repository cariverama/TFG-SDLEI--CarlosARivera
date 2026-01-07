"""
Simulador de alertas de emergencia via MQTT
"""

import paho.mqtt.client as mqtt
import json
import time
import base64
import struct

BROKER = 'localhost'
PORT = 1883
APPLICATION_ID = '1'


def generar_payload(tipo, lat, lon, bateria=85):
    """Genera payload de 11 bytes"""
    lat_int = int(lat * 1_000_000)
    lon_int = int(lon * 1_000_000)
    payload_bytes = struct.pack('>BiiBB', tipo, lat_int, lon_int, bateria, 0x01)
    return base64.b64encode(payload_bytes).decode()


ALERTAS_PRUEBA = {
    '1': {
        'descripcion': 'Emergencia Medica',
        'dev_eui': '0004a30b001b7ad1',
        'tipo': 1,
        'lat': 40.3645,
        'lon': -6.2900
    },
    '2': {
        'descripcion': 'Emergencia Policial',
        'dev_eui': '0004a30b001b7ad2',
        'tipo': 2,
        'lat': 40.4056,
        'lon': -6.2534
    },
    '3': {
        'descripcion': 'Incendio',
        'dev_eui': '0004a30b001b7ad3',
        'tipo': 3,
        'lat': 40.3333,
        'lon': -6.3205
    },
    '4': {
        'descripcion': 'Rescate en Montana',
        'dev_eui': '0004a30b001b7ad4',
        'tipo': 4,
        'lat': 40.3789,
        'lon': -6.1834
    }
}


def enviar_alerta(opcion: str):
    """Envia alerta via MQTT"""
    if opcion not in ALERTAS_PRUEBA:
        print(f"Opcion invalida: {opcion}")
        return
    
    alerta = ALERTAS_PRUEBA[opcion]
    payload = generar_payload(alerta['tipo'], alerta['lat'], alerta['lon'])
    topic = f"application/{APPLICATION_ID}/device/{alerta['dev_eui']}/event/up"
    
    # Formato ChirpStack
    mensaje = {
        "devEUI": alerta['dev_eui'],
        "fPort": 1,
        "data": payload,
        "rxInfo": [{
            "rssi": -85,
            "loRaSNR": 7.5,
            "gatewayID": "0000000000000001"
        }],
        "txInfo": {
            "frequency": 868100000,
            "dr": 5
        }
    }
    
    print(f"\nEnviando alerta: {alerta['descripcion']}")
    print(f"  Dispositivo: {alerta['dev_eui']}")
    print(f"  Ubicacion GPS: {alerta['lat']}, {alerta['lon']}")
    
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(BROKER, PORT, 60)
        result = client.publish(topic, json.dumps(mensaje))
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("Enviado correctamente")
            print("\nRevisa el listener para ver el resultado")
        else:
            print(f"Error enviando (codigo {result.rc})")
        
        client.disconnect()
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nVerifica que el broker MQTT este corriendo")


def mostrar_menu():
    print("\n" + "="*50)
    print("SIMULADOR DE ALERTAS DE EMERGENCIA")
    print("="*50)
    print("\nSelecciona el tipo de alerta a enviar:\n")
    
    for key, alerta in ALERTAS_PRUEBA.items():
        print(f"  {key}. {alerta['descripcion']}")
    
    print("\n  0. Salir")
    print("-"*50)
    print("\nNota: El sistema asignara automaticamente")
    print("el recurso disponible mas cercano")


if __name__ == "__main__":
    print("\nSistema de Gestion de Emergencias")
    print(f"Broker MQTT: {BROKER}:{PORT}")
    
    while True:
        mostrar_menu()
        opcion = input("\nOpcion: ").strip()
        
        if opcion == '0':
            print("\nSaliendo...")
            break
        elif opcion in ALERTAS_PRUEBA:
            enviar_alerta(opcion)
            time.sleep(2)
        else:
            print("\nOpcion invalida")
