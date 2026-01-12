# -*- coding: utf-8 -*-
"""Configuracion del sistema - ARCHIVO DE EJEMPLO"""

# PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'sistema_emergencias',
    'user': 'postgres',
    'password': 'tu_password_aqui'  # CAMBIAR
}

# MQTT (ChirpStack)
MQTT_CONFIG = {
    'broker': 'localhost',
    'port': 1883,
    'username': '',
    'password': '',
    'topic': 'application/+/device/+/event/up'
}


