# Dango (Slime World)

Slime World es un pequeño juego/entorno multijugador minimalista. 

Los jugadores controlan pequeños cuadraditos redondeados (slimes) que cuentan con un sistema físico de **soft-body** (cuerpos blandos) hecho a medida en Canvas 2D. 

## Características
* Físicas de cuerpos blandos (rebotes y deformaciones gelatinosas sutiles)
* Entorno espacial relajante (Parallax de estrellas)
* Chat integrado y efímero en forma de burbujas flotantes
* Arquitectura autoritativa (El servidor de Python calcula la física)
* Backend asíncrono optimizado con un solo puerto para fácil hosteo (Render, Koyeb, etc.)

## Instalación y ejecución local

1. Clona el repositorio
2. Instala la dependencia (usa `aiohttp` para manejar HTTP y WebSockets a la vez):
   ```bash
   pip install -r requirements.txt
   ```
3. Corre el servidor:
   ```bash
   python server.py
   ```
4. Abre `http://localhost:8000` en tu navegador.

## Despliegue en Render.com
Este repositorio está preparado para ser publicado directamente como un **Web Service** en Render. 
Como `aiohttp` sirve ambos protocolos (WebSockets y HTTP) sobre el mismo puerto que Render inyecta vía la variable de entorno `$PORT`, funcionará automáticamente ("out of the box").
