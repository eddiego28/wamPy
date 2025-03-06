# Proyecto WAMP - Publicador y Subscriptor

Este proyecto implementa una interfaz de publicador y suscriptor utilizando WAMP (con Autobahn) y PyQt5.  
Se registran en un fichero de log las operaciones de envío y recepción de mensajes, incluyendo timestamp, topic, realm y el contenido del mensaje en formato JSON.


## Ejecución

1. Asegúrate de tener instaladas las dependencias:  

2. Ejecuta la interfaz principal:


## Notas

- El fichero de log se crea en el directorio raíz del proyecto con un nombre basado en la fecha y hora de inicio.
- Al hacer doble clic en un mensaje en la tabla (tanto en el publicador como en el suscriptor), se abrirá un diálogo que muestra el contenido del mensaje en formato JSON.


