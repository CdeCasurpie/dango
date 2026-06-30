from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import webbrowser


class TextInputServer:
    def __init__(self, callback, port=6767):
        self.callback = callback
        self.port = port

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Sin logs
                pass

            def do_GET(self):
                html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>⚠ SISTEMA BLOQUEADO ⚠</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=VT323&family=Share+Tech+Mono&display=swap');

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    background: #000;
    color: #0f0;
    font-family: 'Share Tech Mono', monospace;
    min-height: 100vh;
    overflow-x: hidden;
    position: relative;
}

/* Efecto Matrix de fondo */
#matrix {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
    opacity: 0.3;
}

/* Contenedor principal */
.container {
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    position: relative;
    z-index: 1;
}

/* Header con efecto glitch */
.header {
    text-align: center;
    border: 3px solid #0f0;
    padding: 20px;
    margin-bottom: 30px;
    background: rgba(0, 20, 0, 0.9);
    box-shadow: 0 0 20px #0f0, inset 0 0 20px rgba(0, 255, 0, 0.1);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 0 20px #0f0, inset 0 0 20px rgba(0, 255, 0, 0.1); }
    50% { box-shadow: 0 0 40px #0f0, inset 0 0 40px rgba(0, 255, 0, 0.2); }
}

h1 {
    font-family: 'VT323', monospace;
    font-size: 3em;
    text-shadow: 0 0 10px #0f0, 0 0 20px #0f0;
    animation: glitch 3s infinite;
}

@keyframes glitch {
    0%, 90%, 100% { transform: translate(0); }
    92% { transform: translate(-2px, 2px); }
    94% { transform: translate(2px, -2px); }
    96% { transform: translate(-2px, -2px); }
    98% { transform: translate(2px, 2px); }
}

.warning {
    color: #f00;
    font-size: 1.2em;
    margin-top: 10px;
    text-shadow: 0 0 10px #f00;
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* Sección de pago troll */
.payment-section {
    border: 2px dashed #ff0;
    padding: 20px;
    margin: 20px 0;
    background: rgba(50, 50, 0, 0.8);
    text-align: center;
}

.payment-section h2 {
    color: #ff0;
    font-size: 1.8em;
    margin-bottom: 15px;
    text-shadow: 0 0 10px #ff0;
}

.payment-section p {
    color: #fa0;
    margin-bottom: 20px;
    font-size: 1.1em;
}

.pay-button {
    display: inline-block;
    background: linear-gradient(45deg, #ff0000, #ff6600);
    color: #fff;
    padding: 15px 40px;
    font-size: 1.5em;
    font-weight: bold;
    text-decoration: none;
    border: 3px solid #fff;
    border-radius: 5px;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 2px;
    box-shadow: 0 0 30px #f00, inset 0 0 30px rgba(255, 100, 0, 0.5);
    animation: urgent 0.5s infinite;
    transition: all 0.3s;
}

.pay-button:hover {
    transform: scale(1.1);
    box-shadow: 0 0 50px #f00, inset 0 0 50px rgba(255, 100, 0, 0.8);
}

@keyframes urgent {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

/* Contador oculto */
#countdown {
    display: none;
    text-align: center;
    margin: 20px 0;
    font-size: 1.5em;
    color: #0ff;
    text-shadow: 0 0 10px #0ff;
}

/* Sección de la llave privada */
.key-section {
    display: none;
    border: 3px solid #f0f;
    padding: 20px;
    margin: 20px 0;
    background: rgba(20, 0, 20, 0.95);
    box-shadow: 0 0 30px #f0f, inset 0 0 30px rgba(255, 0, 255, 0.1);
}

.key-section h3 {
    color: #f0f;
    text-align: center;
    font-size: 1.5em;
    margin-bottom: 15px;
    text-shadow: 0 0 15px #f0f;
}

.key-section p {
    color: #f8f;
    text-align: center;
    margin-bottom: 15px;
}

.private-key {
    background: #000;
    border: 2px solid #f0f;
    padding: 15px;
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    color: #0ff;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 300px;
    overflow-y: auto;
    box-shadow: inset 0 0 20px rgba(255, 0, 255, 0.2);
}

/* Textarea estilo terminal */
textarea {
    width: 100%;
    height: 200px;
    background: #000;
    border: 2px solid #0f0;
    color: #0f0;
    font-family: 'Courier New', monospace;
    font-size: 14px;
    padding: 15px;
    resize: vertical;
    box-shadow: inset 0 0 20px rgba(0, 255, 0, 0.1);
}

textarea:focus {
    outline: none;
    box-shadow: inset 0 0 30px rgba(0, 255, 0, 0.3), 0 0 20px #0f0;
}

/* Botón enviar */
button {
    width: 100%;
    padding: 15px;
    margin-top: 15px;
    background: #000;
    border: 3px solid #0f0;
    color: #0f0;
    font-family: 'VT323', monospace;
    font-size: 1.5em;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 3px;
    transition: all 0.3s;
}

button:hover {
    background: #0f0;
    color: #000;
    box-shadow: 0 0 30px #0f0;
}

/* Footer troll */
.footer {
    text-align: center;
    margin-top: 30px;
    padding: 20px;
    border-top: 1px solid #333;
    color: #666;
    font-size: 0.8em;
}

.skull {
    font-size: 3em;
    animation: spin 4s linear infinite;
    display: inline-block;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* Efecto de scanline */
.scanline {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        to bottom,
        transparent 50%,
        rgba(0, 255, 0, 0.03) 50%
    );
    background-size: 100% 4px;
    pointer-events: none;
    z-index: 999;
}
</style>
</head>
<body>

<canvas id="matrix"></canvas>
<div class="scanline"></div>

<div class="container">
    <div class="header">
        <h1>⚠ SISTEMA ENCRYPTADO ⚠</h1>
        <div class="warning">[ ACCESO NO AUTORIZADO DETECTADO ]</div>
        <p style="margin-top:10px;">Tus archivos han sido convertidos a bits cuánticos.</p>
    </div>

    <div class="payment-section">
        <h2>🔒 PAGO REQUERIDO PARA DESENCRIPTAR 🔒</h2>
        <p>Para recuperar tus archivos, debes realizar un donativo al mantenimiento del servidor.</p>
        <p><strong>Esta es una operación experimental universitaria.</strong></p>
        <a href="https://youtu.be/dQw4w9WgXcQ?list=RDdQw4w9WgXcQ" 
           class="pay-button" 
           target="_blank"
           onclick="iniciarSecuencia()">
           💳 IR A PÁGINA DE PAGO 💳
        </a>
    </div>

    <div id="countdown">
        Procesando transacción... Espere <span id="timer">5</span> segundos...
    </div>

    <div id="keySection" class="key-section">
        <h3>🔓 LLAVE DE DESENCRIPTADO 🔓</h3>
        <p>Copia esta llave privada y pégala abajo para liberar tus archivos:</p>
        <div class="private-key" id="privateKeyText">
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC0nqkg4JmyPSV8
9TxwWCc4iMUWkPIdYK0xOWe+FZL+6Rx9RFHegPlGAcScOff0zddU4pDv0YzOTj/F
OSMwdO7I7TG+7UjCFofpzdbXBKF8EarxHoOc2txBCtKHYzjf0o/z0ghEpm0LE1hG
QFGn/TTEwqIiK5jKs9tghzU4fnK60iCHLZSBBHOnW90ElpsGF1ecT0qyxq+T4022
8KtDNLedbbZmZshGilH0MJgV+f/596FAqAGkGILAlkYkvsTjRF0Gn8IZq06soyOU
OTkLf0Jfv0m/yFbzZySYsoicpfqpZDpqxvFE0j7JltrrwTtgtzCq+mFN0trV7Gzj
r7E/3n9xAgMBAAECggEABbAbaQwkUER0WkTfdDWVIpwirMJqxXm7v9mWxpnSU7xj
58lPf192D3oocWJdSHR1AVjTMfeE5M2lB3Z0Vmcln+aMUv67nv/A+aAVpxbKaRL7
XErW395/4ifPl8Y2+SFzOWfrV7zFS/x+IqmNiL9EuqTbIJKukJpCYH38Mz0UKtrm
gJe8N25PLi+3Kml5wM9/WRL6huyc4fMBmnN+a3/pXAv1gMMS8+Mmw94DSbkxMFSl
a0leDOALPLxRCVhdZWfZoRVaG0XwvpGjKs11JihrdLXKBgzTw9UKussiiA1ezrt3
KF2CU4wpKROt4Nr7HvdhD0PCoxJHZl51FzRPYg/72QKBgQD0gGplV6A1kkfszs6s
BOwILf9lAi9yDacrXlChxmU9AAppFH38DDwwhEGfvXcHH//R4UHKtLKF6MeVeL2k
IUVJ4w9Y9KvmGxT65uFMV0DKNOI9nc7ZuT9Z7z4ckocILWJsAYYVPDcIxRtol4tQ
9Md0k6BDR+QRcMHxzmpaBxTDHQKBgQC9HSnp8mWX2OO5suu9hJ8fz5o6AiatJ1Di
Q3waEYkvkz0x0UTvAWDM8TuBPLAChhhsKzmkXwtXUSItZVAx4hz23aYNkOhVq/2f
L2KOiui+MXLW2zpIPevZ+xHkpW6zyiPEDdXJ0DCdAQy0RewIEu/gUGRSToHXRPlt
dbmeSt+JZQKBgAf8zf0DkNNPNRRSaUQLYR6fShGlsaEbOxPan+25CoOkpbJrHfaG
+8xl9bLfQK016WiU4E5b+t0PDr4eVKuw/o98YHr6e0coKVZNBp002IQCmEWFC0Xn
nF82xqOuUcT9npKCtjupXO7naY7QLJf3dzCixgCMr7G2Kk/Y+3Z3dsEtAoGBAIQ9
1IVnn2sjm3rLhtWr26ne/jX6Mxl6GLFgB3QjNw8xouUnNVD8YbhuJ/IjgeEB7CoX
v+MVI1UXwxKDeiSnvSFTtT5fSlg+QMgD1qNet4noAioEeyjxQ+/WBZkhpdvLSl9a
XVkWYCgqB7w3+OlcdKkjDkQP6fOio9jLLdVm/hGRAoGBAKmQJb4NF/vl5cE5wayJ
00I4DXS+hM3V5tN5griv6RJIcK2PSRTCtQBDUE5iQzRnPrL2KFMJRqN6c//1Ezg2
JBb+oKXfkkTFmU/mERHNu5pKWE0fDhSg+VPPFHeFlzBwisok/3ob9zxYEowapu4g
oDQ3rQvpWeNMbMBRsQ64/8Fa
-----END PRIVATE KEY-----
        </div>
        <p style="margin-top:10px; color:#0f0;">Pega la llave arriba en el campo de texto ↓</p>
    </div>

    <textarea id="txt" placeholder="[ ESPERANDO LLAVE PRIVADA... ]" autofocus></textarea><br>
    <button onclick="enviar()">▶ EJECUTAR DESENCRIPTADO ◀</button>

    <div class="footer">
        <span class="skull">☠</span>
        <p>Sistema desarrollado para fines educativos.</p>
        <p style="color:#333;">Ningún archivo real fue dañado en este experimento.</p>
    </div>
</div>

<script>
// Efecto Matrix
const canvas = document.getElementById('matrix');
const ctx = canvas.getContext('2d');

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*';
const fontSize = 14;
const columns = canvas.width / fontSize;
const drops = [];

for(let i = 0; i < columns; i++) {
    drops[i] = Math.random() * -100;
}

function drawMatrix() {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.fillStyle = '#0f0';
    ctx.font = fontSize + 'px monospace';
    
    for(let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)];
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        
        if(drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
            drops[i] = 0;
        }
        drops[i]++;
    }
}

setInterval(drawMatrix, 50);

// Secuencia de revelado de llave
let secuenciaIniciada = false;

function iniciarSecuencia() {
    if(secuenciaIniciada) return;
    secuenciaIniciada = true;
    
    const countdown = document.getElementById('countdown');
    const timer = document.getElementById('timer');
    const keySection = document.getElementById('keySection');
    
    countdown.style.display = 'block';
    
    let segundos = 5;
    const interval = setInterval(() => {
        segundos--;
        timer.textContent = segundos;
        
        if(segundos <= 0) {
            clearInterval(interval);
            countdown.style.display = 'none';
            keySection.style.display = 'block';
            keySection.scrollIntoView({ behavior: 'smooth' });
            
            // Auto-copiar al portapapeles (opcional, puede fallar por permisos)
            const keyText = document.getElementById('privateKeyText').textContent;
            navigator.clipboard.writeText(keyText).then(() => {
                console.log('Llave copiada al portapapeles');
            }).catch(() => {
                console.log('Copia manual requerida');
            });
        }
    }, 1000);
}

// Función de envío
async function enviar(){
    const texto = document.getElementById("txt").value;
    
    if(!texto.includes('BEGIN PRIVATE KEY')) {
        alert('⚠ ERROR: Se requiere una llave privada válida ⚠');
        return;
    }
    
    // Efecto de procesamiento
    document.body.style.animation = 'glitch 0.1s infinite';
    
    await fetch("/submit",{
        method:"POST",
        body:texto
    });
    
    //window.open("", "_self");
    //window.close();
    
    document.body.innerHTML = `
        <div style="text-align:center; padding:50px; color:#0f0; font-family:monospace;">
            <h1 style="font-size:3em;">✓ DESENCRIPTADO EXITOSO</h1>
            <p style="font-size:1.5em; margin-top:20px;">Tus archivos han sido liberados.</p>
            <p style="color:#666; margin-top:30px;">Puedes cerrar esta pestaña.</p>
        </div>
    `;
}

// Redimensionar canvas
window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
});
</script>

</body>
</html>
"""

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode())

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                texto = self.rfile.read(length).decode()

                self.send_response(200)
                self.end_headers()

                outer.callback(texto)

                # Detener el servidor después de responder
                threading.Thread(
                    target=outer.server.shutdown,
                    daemon=True
                ).start()

        self.server = HTTPServer(("localhost", self.port), Handler)

    def start(self):
        webbrowser.open(f"http://localhost:{self.port}")

        try:
            self.server.serve_forever()
        finally:
            self.server.server_close()


if __name__ == "__main__":

    def procesar(texto):
        print("Recibido:")
        print(texto)

    TextInputServer(procesar).start()

    print("Aquí continúa el programa.")