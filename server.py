import asyncio
import json
import hashlib
import math
import random
import os
from aiohttp import web

players = {}
clients = {}  # ws -> pid

HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
<title>Slime World</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap');

* { margin:0; padding:0; box-sizing:border-box; }
body { overflow:hidden; background:#060612; touch-action:none; font-family:'Outfit',sans-serif; }
canvas { display:block; }

#overlay {
    position:fixed; inset:0; z-index:10;
    display:flex; align-items:center; justify-content:center;
    background:radial-gradient(ellipse at center, rgba(10,10,30,0.92) 0%, rgba(2,2,8,0.98) 100%);
    backdrop-filter:blur(12px);
    transition: opacity 0.6s ease, visibility 0.6s ease;
}
#overlay.hidden { opacity:0; visibility:hidden; pointer-events:none; }

#login-box {
    background: linear-gradient(145deg, rgba(30,30,60,0.7), rgba(15,15,35,0.9));
    border:1px solid rgba(120,100,255,0.25);
    border-radius:24px;
    padding:48px 40px 40px;
    text-align:center;
    box-shadow: 0 0 80px rgba(100,80,255,0.15), inset 0 1px 0 rgba(255,255,255,0.06);
    max-width:380px; width:90%;
    animation: floatIn 0.7s cubic-bezier(0.16,1,0.3,1);
}
@keyframes floatIn {
    from { opacity:0; transform:translateY(30px) scale(0.95); }
    to { opacity:1; transform:translateY(0) scale(1); }
}
#login-box h1 {
    font-size:2rem; font-weight:700;
    background:linear-gradient(135deg,#a78bfa,#60a5fa,#34d399);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:8px;
}
#login-box p { color:rgba(200,200,230,0.6); font-size:0.9rem; margin-bottom:28px; }
#name-input {
    width:100%; padding:14px 18px;
    border:1px solid rgba(120,100,255,0.3); border-radius:14px;
    background:rgba(20,20,50,0.6); color:#e0e0ff;
    font-size:1.05rem; font-family:'Outfit',sans-serif;
    outline:none; transition:border-color 0.3s, box-shadow 0.3s;
    text-align:center; letter-spacing:0.5px;
}
#name-input:focus { border-color:rgba(160,140,255,0.6); box-shadow:0 0 20px rgba(120,100,255,0.2); }
#name-input::placeholder { color:rgba(160,160,200,0.35); }
#join-btn {
    width:100%; margin-top:16px; padding:14px;
    border:none; border-radius:14px;
    background:linear-gradient(135deg,#7c3aed,#6366f1);
    color:#fff; font-size:1.05rem; font-weight:600;
    font-family:'Outfit',sans-serif; cursor:pointer;
    transition:transform 0.15s,box-shadow 0.2s;
    box-shadow:0 4px 20px rgba(100,80,255,0.35);
}
#join-btn:hover { transform:translateY(-2px); box-shadow:0 6px 28px rgba(100,80,255,0.5); }
#join-btn:active { transform:translateY(0); }

#chat-container {
    position:absolute; bottom:20px; left:20px; width:300px;
    pointer-events:none; display:flex; flex-direction:column; justify-content:flex-end; z-index:5;
}
.chat-msg {
    color:rgba(255,255,255,0.75); font-size:13px; margin-top:4px;
    text-shadow:1px 1px 2px rgba(0,0,0,0.8); word-wrap:break-word;
    animation: fadeMsg 5s forwards;
}
@keyframes fadeMsg { 0% { opacity: 0; transform: translateY(5px); } 10% { opacity: 1; transform: translateY(0); } 80% { opacity: 1; transform: translateY(0); } 100% { opacity: 0; transform: translateY(-5px); } }
#chat-input-wrapper {
    position:absolute; bottom:20px; left:20px; width:300px; display:none; z-index:6;
}
#chat-input-wrapper.active { display:block; }
#chat-input {
    width:100%; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.1);
    border-radius:8px; color:#fff; padding:8px 12px; font-family:'Outfit',sans-serif;
    font-size:13px; outline:none;
}
</style>
</head>
<body>

<div id="overlay">
    <div id="login-box">
        <h1>🟢 Slime World</h1>
        <p>Elige tu nombre y entra al mundo</p>
        <input id="name-input" type="text" placeholder="Tu nombre..." maxlength="16" autocomplete="off"/>
        <button id="join-btn">Entrar</button>
    </div>
</div>
<div id="chat-container"></div>
<div id="chat-input-wrapper"><input id="chat-input" type="text" maxlength="60" autocomplete="off" placeholder="Escribe un mensaje..."/></div>
<canvas id="c"></canvas>

<script>
// ══════════════════════════════════════════════
//  ESTADO GLOBAL
// ══════════════════════════════════════════════
let ws = null, myId = null, myName = "";
let players = {};
let camera = {x:0, y:0};
let w, h;
let connected = false, joined = false;

const c = document.getElementById("c");
const ctx = c.getContext("2d");
const overlay = document.getElementById("overlay");
const nameInput = document.getElementById("name-input");
const joinBtn = document.getElementById("join-btn");
const chatContainer = document.getElementById("chat-container");
const chatInputWrapper = document.getElementById("chat-input-wrapper");
const chatInput = document.getElementById("chat-input");

function resize() { w = c.width = innerWidth; h = c.height = innerHeight; }
window.addEventListener("resize", resize);
resize();

// ── Estrellas ──
const stars = Array.from({length:250}, () => ({
    x: Math.random()*6000-3000,
    y: Math.random()*6000-3000,
    r: Math.random()*1.2+0.3,
    z: Math.random()*0.12+0.04,
    phase: Math.random()*Math.PI*2
}));

// ══════════════════════════════════════════════
//  AUDIO Y EFECTOS
// ══════════════════════════════════════════════
const AudioContext = window.AudioContext || window.webkitAudioContext;
const audioCtx = new AudioContext();

function playPlop() {
    if (audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    
    osc.type = 'sine';
    const now = audioCtx.currentTime;
    
    // Caída rápida de frecuencia para el "plop"
    osc.frequency.setValueAtTime(600, now);
    osc.frequency.exponentialRampToValueAtTime(150, now + 0.1);
    
    // Volumen (fade in muy rápido, luego fade out)
    gainNode.gain.setValueAtTime(0, now);
    gainNode.gain.linearRampToValueAtTime(0.5, now + 0.02);
    gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
    
    osc.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    
    osc.start(now);
    osc.stop(now + 0.15);
}

let particles = [];
function createExplosion(x, y, hue) {
    for (let i = 0; i < 15; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = Math.random() * 5 + 2;
        particles.push({
            x: x, y: y,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            life: 1.0,
            hue: hue,
            size: Math.random() * 5 + 3
        });
    }
}

// ══════════════════════════════════════════════
//  SOFT-BODY: sistema de resortes por vértices
// ══════════════════════════════════════════════
// Cada slime tiene N puntos de control alrededor de un cuadrado redondeado.
// Cada punto tiene posición actual, velocidad, y posición de reposo.
// Un resorte tira cada punto hacia su reposo → efecto jelly.

const SB_POINTS = 16;        // más puntos = curva más suave
const SB_SIZE = 24;          // mitad del tamaño del cuadrado
const SB_RADIUS = 10;        // radio de las esquinas
const SB_STIFFNESS = 0.3;    // rigidez alta → regresa rápido
const SB_DAMPING = 0.72;     // amortiguación fuerte
const SB_MAX_DISP = 6;       // desplazamiento máximo desde reposo

// Generar posiciones de reposo: cuadrado redondeado
function generateRestShape() {
    // Crear un rounded-rect como polígono con SB_POINTS puntos
    const pts = [];
    const s = SB_SIZE;
    const r = SB_RADIUS;

    // Esquinas: top-right, bottom-right, bottom-left, top-left
    const corners = [
        {cx: s-r, cy: -(s-r), startA: -Math.PI/2, endA: 0},
        {cx: s-r, cy: s-r,    startA: 0,           endA: Math.PI/2},
        {cx: -(s-r), cy: s-r, startA: Math.PI/2,   endA: Math.PI},
        {cx: -(s-r), cy: -(s-r), startA: Math.PI,  endA: Math.PI*1.5}
    ];

    const ptsPerCorner = Math.floor(SB_POINTS / 4);
    const extra = SB_POINTS - ptsPerCorner * 4;

    for (let ci = 0; ci < 4; ci++) {
        const c = corners[ci];
        const n = ptsPerCorner + (ci < extra ? 1 : 0);
        for (let i = 0; i < n; i++) {
            const t = i / n;
            const angle = c.startA + (c.endA - c.startA) * t;
            pts.push({
                rx: c.cx + Math.cos(angle) * r,
                ry: c.cy + Math.sin(angle) * r
            });
        }
    }
    return pts;
}

const REST_SHAPE = generateRestShape();

function createSoftBody() {
    return REST_SHAPE.map(p => ({
        x: p.rx, y: p.ry,    // posición actual (relativa al centro del slime)
        vx: 0, vy: 0,        // velocidad
        rx: p.rx, ry: p.ry   // posición de reposo
    }));
}

function updateSoftBody(body, dt) {
    for (const p of body) {
        // Fuerza del resorte hacia reposo
        const diffX = p.rx - p.x;
        const diffY = p.ry - p.y;
        p.vx = (p.vx + diffX * SB_STIFFNESS * dt) * SB_DAMPING;
        p.vy = (p.vy + diffY * SB_STIFFNESS * dt) * SB_DAMPING;
        p.x += p.vx * dt;
        p.y += p.vy * dt;

        // Clamp: nunca más de SB_MAX_DISP píxeles del reposo
        const dx = p.x - p.rx;
        const dy = p.y - p.ry;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist > SB_MAX_DISP) {
            p.x = p.rx + (dx / dist) * SB_MAX_DISP;
            p.y = p.ry + (dy / dist) * SB_MAX_DISP;
            // Reducir velocidad al clampear
            p.vx *= 0.3;
            p.vy *= 0.3;
        }
    }
}

// Aplicar impulso desde una dirección (colisión) — sutil
function applySoftBodyImpulse(body, nx, ny, strength) {
    const cappedStr = Math.min(strength, 3); // limitar fuerza
    for (const p of body) {
        // Solo afecta puntos en la dirección del impacto
        const dot = (p.rx * nx + p.ry * ny) / SB_SIZE;
        const influence = clamp(dot, 0, 1);
        const pushStrength = cappedStr * influence * 0.6;
        p.vx += nx * pushStrength;
        p.vy += ny * pushStrength;
    }
}

// Dibujar el cuerpo como curva suave
function drawSoftBodyPath(body) {
    const n = body.length;
    ctx.beginPath();
    // Usar Catmull-Rom → Bézier para curva suave por todos los puntos
    for (let i = 0; i < n; i++) {
        const p0 = body[(i - 1 + n) % n];
        const p1 = body[i];
        const p2 = body[(i + 1) % n];
        const p3 = body[(i + 2) % n];

        if (i === 0) {
            ctx.moveTo(p1.x, p1.y);
        }

        // Catmull-Rom to cubic bezier — tensión baja para menos distorsión
        const tension = 0.2;
        const cp1x = p1.x + (p2.x - p0.x) * tension;
        const cp1y = p1.y + (p2.y - p0.y) * tension;
        const cp2x = p2.x - (p3.x - p1.x) * tension;
        const cp2y = p2.y - (p3.y - p1.y) * tension;

        ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
    }
    ctx.closePath();
}

// ══════════════════════════════════════════════
//  WEBSOCKET
// ══════════════════════════════════════════════
function connectWS() {
    const wsProtocol = location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(wsProtocol + location.host + "/ws");
    ws.onopen = () => { connected = true; };
    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === "init") {
            myId = data.id;
            if (myName) ws.send(JSON.stringify({type:"name", name:myName}));
        }
        else if (data.type === "chat") {
            const p = players[data.id];
            const pName = p ? p.name : "???";
            const el = document.createElement("div");
            el.className = "chat-msg";
            
            // Protección contra XSS (Inyección de JavaScript/HTML)
            const strong = document.createElement("strong");
            strong.textContent = pName + ":";
            el.appendChild(strong);
            el.appendChild(document.createTextNode(" " + data.msg));
            
            chatContainer.appendChild(el);
            setTimeout(() => el.remove(), 5000);
            if (p) {
                p.chatMsg = data.msg;
                p.chatTimer = 4000;
            }
        }
        else if (data.type === "state") {
            const now = performance.now();
            for (const id in data.players) {
                const s = data.players[id];
                if (!players[id]) {
                    players[id] = {
                        x: s.x, y: s.y,
                        sx: s.x, sy: s.y,
                        hue: s.hue,
                        name: s.name || "???",
                        dx: s.dx||0, dy: s.dy||0,
                        // Soft-body
                        body: createSoftBody(),
                        // Parpadeo y chat
                        blinkTimer: Math.random()*240+100,
                        blinkFrame: 0,
                        eyeAngle: 0,
                        chatMsg: "",
                        chatTimer: 0,
                        lastUpdate: now
                    };
                } else {
                    const p = players[id];
                    p.x = s.x; p.y = s.y;
                    p.hue = s.hue;
                    p.name = s.name || p.name;
                    p.dx = s.dx||0;
                    p.dy = s.dy||0;
                    // Bump del servidor → impulso al soft-body
                    if (s.bumpNx !== undefined && s.bumpStr > 0) {
                        applySoftBodyImpulse(p.body, s.bumpNx, s.bumpNy, s.bumpStr);
                    }
                    p.lastUpdate = now;
                }
            }
            for (const id in players) {
                if (!data.players[id]) {
                    const p = players[id];
                    createExplosion(p.sx, p.sy, p.hue);
                    playPlop();
                    delete players[id];
                }
            }
        }
    };
    ws.onclose = () => {
        connected = false; myId = null; players = {};
        setTimeout(connectWS, 2000);
    };
}
connectWS();

// ══════════════════════════════════════════════
//  LOGIN
// ══════════════════════════════════════════════
function doJoin() {
    const name = nameInput.value.trim();
    if (!name) { nameInput.style.borderColor="rgba(255,80,80,0.7)"; return; }
    myName = name;
    if (ws && ws.readyState===1 && myId) ws.send(JSON.stringify({type:"name", name:myName}));
    overlay.classList.add("hidden");
    joined = true;
    if (audioCtx.state === 'suspended') audioCtx.resume(); // Activar audio on click
}
joinBtn.addEventListener("click", doJoin);
nameInput.addEventListener("keydown", e => { if(e.key==="Enter") doJoin(); });
nameInput.addEventListener("input", () => { nameInput.style.borderColor="rgba(120,100,255,0.3)"; });

// ══════════════════════════════════════════════
//  INPUT Y CHAT
// ══════════════════════════════════════════════
window.addEventListener("keydown", e => {
    if (!joined) return;
    if (e.key === "/" && !chatInputWrapper.classList.contains("active")) {
        e.preventDefault();
        chatInputWrapper.classList.add("active");
        chatInput.value = "";
        chatInput.focus();
    } else if (e.key === "Escape" && chatInputWrapper.classList.contains("active")) {
        chatInputWrapper.classList.remove("active");
        chatInput.blur();
    } else if (e.key === "Enter" && chatInputWrapper.classList.contains("active")) {
        const msg = chatInput.value.trim();
        if (msg && ws && ws.readyState === 1) ws.send(JSON.stringify({type:"chat", msg}));
        chatInputWrapper.classList.remove("active");
        chatInput.blur();
    }
});
chatInputWrapper.addEventListener("pointerdown", e => e.stopPropagation());

function sendTarget(tx, ty) {
    if (ws && ws.readyState===1 && joined) ws.send(JSON.stringify({type:"input", tx, ty}));
}
function getWorldPos(e) {
    const evt = e.touches ? e.touches[0] : e;
    return { x: evt.clientX - w/2 + camera.x, y: evt.clientY - h/2 + camera.y };
}
c.addEventListener("pointerdown", e => { if(!joined) return; const p=getWorldPos(e); sendTarget(p.x,p.y); });
c.addEventListener("pointermove", e => { if(!joined||e.buttons===0) return; const p=getWorldPos(e); sendTarget(p.x,p.y); });

// ══════════════════════════════════════════════
//  UTILIDADES
// ══════════════════════════════════════════════
function lerp(a, b, t) { return a+(b-a)*t; }
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

// ══════════════════════════════════════════════
//  DIBUJAR SLIME
// ══════════════════════════════════════════════
function drawSlime(p, isMe) {
    const px = p.sx;
    const py = p.sy;

    ctx.save();
    ctx.translate(px, py);

    // ── Cuerpo soft-body ──
    // Color base + gradiente sutil
    const bodyGrad = ctx.createLinearGradient(0, -SB_SIZE, 0, SB_SIZE);
    bodyGrad.addColorStop(0, `hsl(${p.hue}, 65%, 72%)`);
    bodyGrad.addColorStop(1, `hsl(${p.hue}, 60%, 52%)`);

    ctx.fillStyle = bodyGrad;
    drawSoftBodyPath(p.body);
    ctx.fill();

    // ── Brillo sutil (highlight) ──
    ctx.globalAlpha = 0.18;
    const hlGrad = ctx.createRadialGradient(-5, -SB_SIZE*0.5, 2, 0, 0, SB_SIZE*1.1);
    hlGrad.addColorStop(0, "rgba(255,255,255,0.8)");
    hlGrad.addColorStop(0.5, "rgba(255,255,255,0)");
    ctx.fillStyle = hlGrad;
    drawSoftBodyPath(p.body);
    ctx.fill();
    ctx.globalAlpha = 1;

    // ── Ojos: dos líneas verticales ──
    const speed = Math.hypot(p.dx, p.dy);
    let targetAngle = p.eyeAngle;
    if (speed > 0.4) targetAngle = Math.atan2(p.dy, p.dx);
    p.eyeAngle = lerp(p.eyeAngle, targetAngle, 0.1);
    const lookX = Math.cos(p.eyeAngle) * 2;
    const lookY = Math.sin(p.eyeAngle) * 1.5;

    const eyeSpacing = 7;
    const eyeY = -2;
    const eyeHeight = 10;

    // Parpadeo: eyeOpenness va de 0 (cerrado) a 1 (abierto)
    let eyeOpenness = 1;
    if (p.blinkFrame > 0) {
        const half = 4;
        if (p.blinkFrame > half) {
            eyeOpenness = (p.blinkFrame - half) / half;
        } else {
            eyeOpenness = 1 - p.blinkFrame / half;
        }
        eyeOpenness = clamp(eyeOpenness, 0, 1);
    }

    const actualEyeH = eyeHeight * eyeOpenness;

    // Color de los ojos: oscuro
    ctx.strokeStyle = `hsl(${p.hue}, 40%, 18%)`;
    ctx.lineCap = "round";
    ctx.lineWidth = 3.5;

    if (actualEyeH > 0.5) {
        // Ojo izquierdo
        ctx.beginPath();
        ctx.moveTo(-eyeSpacing + lookX, eyeY - actualEyeH/2 + lookY);
        ctx.lineTo(-eyeSpacing + lookX, eyeY + actualEyeH/2 + lookY);
        ctx.stroke();

        // Ojo derecho
        ctx.beginPath();
        ctx.moveTo(eyeSpacing + lookX, eyeY - actualEyeH/2 + lookY);
        ctx.lineTo(eyeSpacing + lookX, eyeY + actualEyeH/2 + lookY);
        ctx.stroke();
    } else {
        // Cerrado → línea horizontal
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(-eyeSpacing - 2 + lookX, eyeY + lookY);
        ctx.lineTo(-eyeSpacing + 2 + lookX, eyeY + lookY);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(eyeSpacing - 2 + lookX, eyeY + lookY);
        ctx.lineTo(eyeSpacing + 2 + lookX, eyeY + lookY);
        ctx.stroke();
    }
    ctx.restore();
}

function drawName(p, isMe) {
    const px = p.sx;
    const py = p.sy;

    ctx.save();
    ctx.font = "600 13px 'Outfit', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    const nameY = py - SB_SIZE - 16;

    const nameW = ctx.measureText(p.name).width + 16;
    ctx.fillStyle = "rgba(0,0,0,0.4)";
    ctx.beginPath();
    ctx.roundRect(px - nameW/2, nameY - 15, nameW, 22, 8);
    ctx.fill();

    ctx.fillStyle = isMe ? "#fff" : `hsl(${p.hue},60%,85%)`;
    ctx.fillText(p.name, px, nameY + 4);

    if (isMe) {
        ctx.font = "600 10px 'Outfit', sans-serif";
        ctx.fillStyle = "rgba(140,255,160,0.65)";
        ctx.fillText("⬤ tú", px, nameY - 16);
    }
    ctx.restore();

    // ── Globo de Chat ──
    if (p.chatTimer > 0 && p.chatMsg) {
        ctx.save();
        
        let scale = 1;
        let alpha = 1;
        
        // Timer de 4000 a 0
        if (p.chatTimer > 3800) {
            // Pop de entrada (easeOutBack)
            const t = (4000 - p.chatTimer) / 200;
            const c1 = 1.70158;
            const c3 = c1 + 1;
            const t1 = t - 1;
            scale = 1 + c3 * t1 * t1 * t1 + c1 * t1 * t1;
            alpha = t;
        } else if (p.chatTimer < 300) {
            // Fade out de salida
            alpha = p.chatTimer / 300;
            scale = 0.9 + 0.1 * alpha;
        }

        ctx.globalAlpha = clamp(alpha, 0, 1);
        
        ctx.font = "600 12px 'Outfit', sans-serif";
        const msgW = ctx.measureText(p.chatMsg).width + 16;
        const bubbleY = nameY - 24;
        
        // Escalar desde la punta de la cola
        ctx.translate(px, bubbleY);
        ctx.scale(Math.max(0, scale), Math.max(0, scale));
        
        ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
        
        // Cola más pequeña y sutil
        ctx.beginPath();
        ctx.moveTo(-4, 0);
        ctx.lineTo(4, 0);
        ctx.lineTo(0, 4);
        ctx.fill();

        // Cuerpo del globo
        ctx.beginPath();
        ctx.roundRect(-msgW/2, -24, msgW, 24, 10);
        ctx.fill();

        ctx.fillStyle = "rgba(0, 0, 0, 0.9)";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(p.chatMsg, 0, -12);
        ctx.restore();
    }
}

// ══════════════════════════════════════════════
//  RENDER LOOP
// ══════════════════════════════════════════════
let lastTime = performance.now();

function loop(now) {
    const rawDt = (now - lastTime) / 16.67;
    const dt = Math.min(rawDt, 3);
    lastTime = now;

    ctx.clearRect(0, 0, w, h);

    // ── Fondo ──
    ctx.fillStyle = "#060612";
    ctx.fillRect(0, 0, w, h);

    // ── Estrellas (parallax + twinkle) ──
    for (const s of stars) {
        s.phase += 0.015 * dt;
        const alpha = 0.35 + Math.sin(s.phase) * 0.3;
        ctx.globalAlpha = clamp(alpha, 0.05, 0.8);
        ctx.fillStyle = "#c8c0e8";
        const px = ((s.x - camera.x * s.z) % w + w) % w;
        const py = ((s.y - camera.y * s.z) % h + h) % h;
        ctx.beginPath();
        ctx.arc(px, py, s.r, 0, Math.PI*2);
        ctx.fill();
    }
    ctx.globalAlpha = 1;

    // ── Actualizar jugadores ──
    for (const id in players) {
        const p = players[id];

        // Interpolación de posición
        p.sx = lerp(p.sx, p.x, 0.16 * dt);
        p.sy = lerp(p.sy, p.y, 0.16 * dt);

        // Soft-body update
        updateSoftBody(p.body, dt);

        // Squish MUY sutil por velocidad de movimiento
        const speed = Math.hypot(p.dx, p.dy);
        if (speed > 2) {
            const angle = Math.atan2(p.dy, p.dx);
            const stretchAmt = Math.min(speed * 0.06, 1.2); // muy reducido
            const cosA = Math.cos(angle);
            const sinA = Math.sin(angle);
            for (const pt of p.body) {
                const dot = (pt.rx * cosA + pt.ry * sinA) / SB_SIZE;
                if (dot > 0.2) {
                    // Empuje muy suave solo en la dirección del movimiento
                    pt.vx += cosA * stretchAmt * dot * 0.08 * dt;
                    pt.vy += sinA * stretchAmt * dot * 0.08 * dt;
                }
            }
        }

        // Parpadeo y Chat
        p.blinkTimer -= dt;
        if (p.blinkTimer <= 0) {
            p.blinkFrame = 8;
            p.blinkTimer = Math.random() * 250 + 100;
        }
        if (p.blinkFrame > 0) p.blinkFrame = Math.max(0, p.blinkFrame - 0.4 * dt);
        if (p.chatTimer > 0) p.chatTimer -= dt * 16.67;
    }

    // ── Cámara ──
    if (myId && players[myId]) {
        camera.x = lerp(camera.x, players[myId].sx, 0.07 * dt);
        camera.y = lerp(camera.y, players[myId].sy, 0.07 * dt);
    }

    // ── Dibujar mundo ──
    ctx.save();
    ctx.translate(w/2 - camera.x, h/2 - camera.y);

    // Grid sutil
    ctx.strokeStyle = "rgba(60,55,100,0.06)";
    ctx.lineWidth = 1;
    const gs = 100;
    const sx = Math.floor((camera.x - w/2)/gs)*gs;
    const sy = Math.floor((camera.y - h/2)/gs)*gs;
    ctx.beginPath();
    for (let x=sx; x<camera.x+w/2+gs; x+=gs) { ctx.moveTo(x,sy); ctx.lineTo(x,camera.y+h/2+gs); }
    for (let y=sy; y<camera.y+h/2+gs; y+=gs) { ctx.moveTo(sx,y); ctx.lineTo(camera.x+w/2+gs,y); }
    ctx.stroke();

    // Orden de dibujado: y-sort puro para que el que está más abajo se dibuje por encima
    const sortedIds = Object.keys(players).sort((a,b) => players[a].sy - players[b].sy);

    // Dibujar slimes
    for (const id of sortedIds) drawSlime(players[id], id===myId);

    // Dibujar nombres en una pasada adicional para que estén por encima de todo
    for (const id of sortedIds) drawName(players[id], id===myId);

    // ── Partículas (Explosión) ──
    for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.vx *= 0.92;
        p.vy *= 0.92;
        p.life -= 0.04 * dt;
        if (p.life <= 0) {
            particles.splice(i, 1);
        } else {
            ctx.globalAlpha = p.life;
            ctx.fillStyle = `hsl(${p.hue}, 70%, 75%)`;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI*2);
            ctx.fill();
        }
    }
    ctx.globalAlpha = 1;

    ctx.restore();

    // ── HUD ──
    if (joined && !connected) {
        ctx.save();
        ctx.font = "600 14px 'Outfit',sans-serif";
        ctx.fillStyle = "rgba(255,120,120,0.8)";
        ctx.textAlign = "center";
        ctx.fillText("Reconectando...", w/2, 30);
        ctx.restore();
    } else if (joined) {
        ctx.save();
        ctx.font = "500 12px 'Outfit',sans-serif";
        ctx.fillStyle = "rgba(200,200,230,0.3)";
        ctx.textAlign = "left";
        const count = Object.keys(players).length;
        ctx.fillText(`${count} slime${count!==1?"s":""} online`, 14, 24);
        ctx.restore();
    }

    requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
</script>
</body>
</html>
"""


async def index(request):
    return web.Response(text=HTML, content_type="text/html")


async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    pid = str(id(ws))
    hue = int(hashlib.md5(pid.encode()).hexdigest()[:4], 16) % 360
    sx = random.uniform(-300, 300)
    sy = random.uniform(-300, 300)
    players[pid] = {
        "x": sx, "y": sy,
        "tx": sx, "ty": sy,
        "hue": hue,
        "name": "???",
        "dx": 0, "dy": 0,
        "bumpNx": 0, "bumpNy": 0, "bumpStr": 0
    }
    clients[ws] = pid

    try:
        await ws.send_json({"type": "init", "id": pid})
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data["type"] == "input":
                    players[pid]["tx"] = float(data["tx"])
                    players[pid]["ty"] = float(data["ty"])
                elif data["type"] == "name":
                    name = str(data.get("name", "???"))[:16].strip()
                    if name:
                        players[pid]["name"] = name
                elif data["type"] == "chat":
                    chat_msg = str(data.get("msg", ""))[:60].strip()
                    if chat_msg:
                        chat_payload = {"type": "chat", "id": pid, "msg": chat_msg}
                        for c_ws in list(clients.keys()):
                            try:
                                await c_ws.send_json(chat_payload)
                            except Exception:
                                pass
    except Exception:
        pass
    finally:
        clients.pop(ws, None)
        players.pop(pid, None)

    return ws


async def game_loop(app):
    """Bucle de simulación autoritativo — 30 TPS"""
    VELOCITY = 5.5
    TICK_RATE = 1 / 30.0
    SLIME_RADIUS = 26
    BOUNCE_FORCE = 6.0

    try:
        while True:
            await asyncio.sleep(TICK_RATE)
            pids = list(players.keys())

            # ─ Integración cinemática ─
            for pid in pids:
                p = players.get(pid)
                if not p: continue
                dx = p["tx"] - p["x"]
                dy = p["ty"] - p["y"]
                dist = math.hypot(dx, dy)

                if dist > VELOCITY:
                    p["dx"] = (dx / dist) * VELOCITY
                    p["dy"] = (dy / dist) * VELOCITY
                    p["x"] += p["dx"]
                    p["y"] += p["dy"]
                elif dist > 0.5:
                    p["dx"] = dx * 0.4
                    p["dy"] = dy * 0.4
                    p["x"] += p["dx"]
                    p["y"] += p["dy"]
                else:
                    p["x"] = p["tx"]
                    p["y"] = p["ty"]
                    p["dx"] *= 0.8
                    p["dy"] *= 0.8

            # ─ Colisiones (soft-body bump) ─
            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    pa = players.get(pids[i])
                    pb = players.get(pids[j])
                    if not pa or not pb: continue
                    ddx = pb["x"] - pa["x"]
                    ddy = pb["y"] - pa["y"]
                    dist = math.hypot(ddx, ddy)
                    min_dist = SLIME_RADIUS * 2

                    if 0.01 < dist < min_dist:
                        overlap = (min_dist - dist) / 2
                        nx = ddx / dist
                        ny = ddy / dist

                        pa["x"] -= nx * overlap
                        pa["y"] -= ny * overlap
                        pb["x"] += nx * overlap
                        pb["y"] += ny * overlap

                        pa["tx"] -= nx * overlap * 0.3
                        pa["ty"] -= ny * overlap * 0.3
                        pb["tx"] += nx * overlap * 0.3
                        pb["ty"] += ny * overlap * 0.3

                        pa["dx"] -= nx * BOUNCE_FORCE * 0.3
                        pa["dy"] -= ny * BOUNCE_FORCE * 0.3
                        pb["dx"] += nx * BOUNCE_FORCE * 0.3
                        pb["dy"] += ny * BOUNCE_FORCE * 0.3

                        bump_strength = max(0, min(8, overlap * 1.2))
                        pa["bumpNx"] = -nx
                        pa["bumpNy"] = -ny
                        pa["bumpStr"] = bump_strength
                        pb["bumpNx"] = nx
                        pb["bumpNy"] = ny
                        pb["bumpStr"] = bump_strength

            if not clients:
                for p in players.values(): p["bumpStr"] = 0
                continue

            # ─ Broadcast ─
            state_payload = {
                "type": "state",
                "players": {
                    k: {
                        "x": round(v["x"], 1),
                        "y": round(v["y"], 1),
                        "hue": v["hue"],
                        "name": v["name"],
                        "dx": round(v["dx"], 2),
                        "dy": round(v["dy"], 2),
                        "bumpNx": round(v.get("bumpNx", 0), 3),
                        "bumpNy": round(v.get("bumpNy", 0), 3),
                        "bumpStr": round(v.get("bumpStr", 0), 2)
                    }
                    for k, v in players.items()
                }
            }

            for p in players.values():
                p["bumpStr"] = 0

            dead = []
            for c_ws in list(clients.keys()):
                try:
                    await c_ws.send_json(state_payload)
                except Exception:
                    dead.append(c_ws)
            for d in dead:
                pid = clients.pop(d, None)
                if pid:
                    players.pop(pid, None)
    except asyncio.CancelledError:
        pass


async def start_background_tasks(app):
    app['game_loop'] = asyncio.create_task(game_loop(app))

async def cleanup_background_tasks(app):
    app['game_loop'].cancel()
    await app['game_loop']

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/ws', ws_handler)
    
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    port = int(os.environ.get("PORT", 8000))
    print(f"🟢 Slime World corriendo en puerto {port}!")
    web.run_app(app, host="0.0.0.0", port=port)
