# TFG-SDLEI--CarlosARivera
Sistema de información para la gestión de emergencias en zonas con limitaciones de cobertura móvil.
1. Requisitos del sistema 
Para ejecutar el sistema se necesita disponer de los siguientes softwares de 
código abierto: 
  • PostgreSQL con la extensión PostGIS, para la gestion de datos 
  relacionales y geoespaciales. 
  Disponible en: https://www.postgresql.org/download/  
  • Python, versión 3.9 o superior, para la ejecución de la lógica del 
  sistema. 
  Disponible en: https://www.python.org/downloads/ 
  • Eclipse Mosquitto, como bróker MQTT para la simulación de la red 
  LoRaWAN. 
  Disponible en: https://mosquitto.org/download/

2. Configurar el entorno 
Una vez instalados los softwares indicados se debe de seguir el siguiente 
proceso para realizar una comprobación del funcionamiento del sistema: 
  1. Crear 
  una base de datos en PostgreSQL denominada 
  sistema_emergencias. 
  2. Ejecutar el script sistema_emergencias.sql, incluido en el proyecto, 
  para la creación de las tablas, tipos de datos y extensiones necesarias. 
  3. Editar el archivo config.py, ajustando los parámetros de conexión a la 
  base de datos (usuario, contraseña y puerto) según la configuración 
  local. 
  4. Desde un terminal, sitúate en el directorio del proyecto y ejecuta el 
  siguiente comando para instalar las dependencias: 
  pip install -r requirements.txt 

Autor: Carlos Alberto Rivera Amador
