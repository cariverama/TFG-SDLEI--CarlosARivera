# -*- coding: utf-8 -*-
"""Script de prueba del sistema sin MQTT"""

import sys
import os
import base64
import struct

if sys.platform == 'win32':
    os.environ['PGCLIENTENCODING'] = 'UTF8'
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from integracion import SistemaEmergencias
from config import DB_CONFIG

def crear_payload(tipo_emergencia, latitud, longitud, bateria=85):
    """Crea un payload binario simulado"""
    lat_int = int(latitud * 1_000_000)
    lon_int = int(longitud * 1_000_000)
    payload_bytes = struct.pack('>BiiBB', tipo_emergencia, lat_int, lon_int, bateria, 0x01)
    return base64.b64encode(payload_bytes).decode()

CASOS_PRUEBA = [
    {
        'nombre': 'Emergencia Medica en Caminomorisco',
        'dispositivo_id': '0004a30b001b7ad1',
        'tipo': 1,
        'lat': 40.3645,
        'lon': -6.2900
    },
    {
        'nombre': 'Emergencia Policial en Nunomoral',
        'dispositivo_id': '0004a30b001b7ad2',
        'tipo': 2,
        'lat': 40.4056,
        'lon': -6.2534
    },
    {
        'nombre': 'Incendio en Pinofranqueado',
        'dispositivo_id': '0004a30b001b7ad3',
        'tipo': 3,
        'lat': 40.3333,
        'lon': -6.3205
    },
    {
        'nombre': 'Rescate en Casar de Palomero',
        'dispositivo_id': '0004a30b001b7ad4',
        'tipo': 4,
        'lat': 40.3789,
        'lon': -6.1834
    }
]

def ejecutar_prueba(sistema, caso, numero):
    """Ejecuta un caso de prueba"""
    print(f"\nPRUEBA {numero}: {caso['nombre']}")
    print("="*60)
    
    payload = crear_payload(caso['tipo'], caso['lat'], caso['lon'])
    print(f"  Dispositivo: {caso['dispositivo_id']}")
    print(f"  Ubicacion: ({caso['lat']}, {caso['lon']})")
    print(f"  Payload: {payload[:30]}...")
    
    try:
        resultado = sistema.procesar_alerta(caso['dispositivo_id'], payload)
        
        if resultado['exito']:
            print(f"\nRESULTADO: EXITOSO")
            print(f"  Alerta ID: {resultado['alerta_id']}")
            
            if 'asignacion' in resultado:
                asig = resultado['asignacion']
                print(f"  Recurso asignado: {asig['nombre']}")
                print(f"  Municipio: {asig['municipio']}")
                print(f"  Distancia: {asig['distancia_metros']:.0f} m")
                print(f"  Tiempo estimado: {asig['tiempo_estimado_minutos']} min")
            
            return True
        else:
            print(f"\nRESULTADO: FALLIDO")
            print(f"  Razon: {resultado.get('mensaje', 'Error desconocido')}")
            return False
            
    except Exception as e:
        print(f"\nRESULTADO: ERROR")
        print(f"  Error: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("SISTEMA DE GESTION DE ALERTAS DE EMERGENCIA")
    print("="*60)
    
    print("\nConectando a base de datos...")
    sistema = SistemaEmergencias(DB_CONFIG)
    
    if not sistema.conectar_bd():
        print("ERROR: No se pudo conectar a la base de datos")
        print("Verifica que PostgreSQL este corriendo y la configuracion en config.py")
        return
    
    print("Conexion establecida")
    
    print("\n" + "="*60)
    print("EJECUTANDO PRUEBAS")
    print("="*60)
    
    resultados = []
    for i, caso in enumerate(CASOS_PRUEBA, 1):
        exito = ejecutar_prueba(sistema, caso, i)
        resultados.append(exito)
    
    sistema.desconectar_bd()
    
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    print(f"Total: {len(resultados)}")
    print(f"Exitosas: {sum(resultados)}")
    print(f"Fallidas: {len(resultados) - sum(resultados)}")
    
    if all(resultados):
        print("\nTODAS LAS PRUEBAS PASARON")
    else:
        print("\nALGUNAS PRUEBAS FALLARON")
    
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrumpido")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
