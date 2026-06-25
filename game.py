import pygame
import asyncio
import aiohttp
import json
import math
import random
import sys
import colorsys

# ══════════════════════════════════════════════
#  CONFIGURACIÓN Y CONSTANTES
# ══════════════════════════════════════════════
WIDTH, HEIGHT = 1000, 700
FPS = 60

SB_POINTS = 24
SB_SIZE = 26
SB_STIFFNESS = 0.3
SB_DAMPING = 0.72
SB_MAX_DISP = 6

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def lerp(a, b, t):
    return a + (b - a) * t

def angle_diff(a, b):
    d = b - a
    while d > math.pi: d -= 2 * math.pi
    while d < -math.pi: d += 2 * math.pi
    return d

def generate_rest_shape():
    pts = []
    s = SB_SIZE
    n = 3.0
    for i in range(SB_POINTS):
        angle = (i / SB_POINTS) * math.pi * 2
        cosA = math.cos(angle)
        sinA = math.sin(angle)
        x = math.pow(abs(cosA), 2/n) * s * (1 if cosA >= 0 else -1)
        y = math.pow(abs(sinA), 2/n) * s * (1 if sinA >= 0 else -1)
        pts.append({"rx": x, "ry": y})
    return pts

REST_SHAPE = generate_rest_shape()

# ══════════════════════════════════════════════
#  CLASES DE ESTADO
# ══════════════════════════════════════════════
class Slime:
    def __init__(self, pid):
        self.id = pid
        self.x = 0
        self.y = 0
        self.dx = 0
        self.dy = 0
        self.hue = 0
        self.name = ""
        self.bumpNx = 0
        self.bumpNy = 0
        self.bumpStr = 0
        
        self.sx = 0
        self.sy = 0
        self.eyeAngle = 0
        self.blinkTimer = random.uniform(2, 6)
        self.blinkFrame = 0
        self.chatMsg = ""
        self.chatTimer = 0
        
        self.body = [{"x": p["rx"], "y": p["ry"], "vx": 0, "vy": 0, "rx": p["rx"], "ry": p["ry"]} for p in REST_SHAPE]

class Particle:
    def __init__(self, x, y, hue):
        self.x = x
        self.y = y
        a = random.uniform(0, math.pi * 2)
        s = random.uniform(1, 4)
        self.vx = math.cos(a) * s
        self.vy = math.sin(a) * s
        self.size = random.uniform(3, 7)
        self.life = 1.0
        self.hue = hue

# ══════════════════════════════════════════════
#  CLIENTE PRINCIPAL (PYGAME + ASYNCIO)
# ══════════════════════════════════════════════
async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Slime World - Escritorio")
    clock = pygame.time.Clock()
    
    font = pygame.font.SysFont("Segoe UI", 16, bold=True)
    chat_font = pygame.font.SysFont("Segoe UI", 14, bold=True)
    
    players = {}
    my_id = None
    camera = {"x": 0, "y": 0}
    particles = []
    stars = [{"x": random.uniform(-3000, 3000), "y": random.uniform(-3000, 3000), 
              "r": random.uniform(0.3, 1.5), "z": random.uniform(0.04, 0.16),
              "phase": random.uniform(0, math.pi * 2)} for _ in range(250)]

    send_queue = asyncio.Queue()

    # Tarea de red (Websockets con aiohttp)
    async def network_task():
        nonlocal my_id
        session = aiohttp.ClientSession()
        try:
            async with session.ws_connect('ws://localhost:8000/ws') as ws:
                # Login
                await ws.send_json({"type": "name", "name": "JugadorPy"})
                
                async def receiver():
                    nonlocal my_id
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            t = data.get("type")
                            if t == "id":
                                my_id = data["id"]
                            elif t == "state":
                                for k, v in data["players"].items():
                                    if k not in players:
                                        players[k] = Slime(k)
                                        players[k].sx = v["x"]
                                        players[k].sy = v["y"]
                                    
                                    p = players[k]
                                    p.x = v["x"]
                                    p.y = v["y"]
                                    p.dx = v["dx"]
                                    p.dy = v["dy"]
                                    p.hue = v["hue"]
                                    p.name = v["name"]
                                    
                                    if v.get("bumpStr", 0) > p.bumpStr + 0.1:
                                        p.bumpNx = v["bumpNx"]
                                        p.bumpNy = v["bumpNy"]
                                        p.bumpStr = v["bumpStr"]
                                        
                                # Remove disconnected
                                for k in list(players.keys()):
                                    if k not in data["players"]:
                                        del players[k]
                                        
                            elif t == "chat":
                                pid = data["id"]
                                if pid in players:
                                    players[pid].chatMsg = data["msg"]
                                    players[pid].chatTimer = 240 # frames
                                    
                            elif t == "plop":
                                for _ in range(12): # Reducido un 25% (era 15)
                                    particles.append(Particle(data["x"], data["y"], data["hue"]))
                                    
                async def sender():
                    while True:
                        msg = await send_queue.get()
                        await ws.send_json(msg)

                await asyncio.gather(receiver(), sender())
        except Exception as e:
            print(f"Error de red: {e}")
        finally:
            await session.close()
            
    asyncio.create_task(network_task())

    # Funciones de físicas y dibujo locales
    def apply_impulse(body, nx, ny, strength):
        capped = min(strength, 10)
        idx, idy = -nx, -ny
        for p in body:
            dot = (p["rx"] * idx + p["ry"] * idy) / SB_SIZE
            if dot > 0:
                push = capped * dot * 1.5
                p["vx"] += nx * push
                p["vy"] += ny * push

    def update_soft_body(body, dt):
        for p in body:
            p["vx"] = (p["vx"] + (p["rx"] - p["x"]) * SB_STIFFNESS * dt) * SB_DAMPING
            p["vy"] = (p["vy"] + (p["ry"] - p["y"]) * SB_STIFFNESS * dt) * SB_DAMPING
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            
            dx, dy = p["x"] - p["rx"], p["y"] - p["ry"]
            dist = math.hypot(dx, dy)
            if dist > SB_MAX_DISP:
                p["x"] = p["rx"] + (dx/dist) * SB_MAX_DISP
                p["y"] = p["ry"] + (dy/dist) * SB_MAX_DISP
                p["vx"] *= 0.3
                p["vy"] *= 0.3

    def hsl_to_color(h, s, l):
        r, g, b = colorsys.hls_to_rgb(h/360.0, l, s)
        return (int(r*255), int(g*255), int(b*255))

    chat_input_active = False
    chat_text = ""

    running = True
    while running:
        w, h = screen.get_size()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and not chat_input_active:
                mx, my = pygame.mouse.get_pos()
                tx = mx - w/2 + camera["x"]
                ty = my - h/2 + camera["y"]
                send_queue.put_nowait({"type": "input", "tx": tx, "ty": ty})
            elif event.type == pygame.MOUSEMOTION and getattr(event, 'buttons', (0,))[0] and not chat_input_active:
                mx, my = pygame.mouse.get_pos()
                tx = mx - w/2 + camera["x"]
                ty = my - h/2 + camera["y"]
                send_queue.put_nowait({"type": "input", "tx": tx, "ty": ty})
            elif event.type == pygame.KEYDOWN:
                if chat_input_active:
                    if event.key == pygame.K_ESCAPE:
                        chat_input_active = False
                    elif event.key == pygame.K_RETURN:
                        if chat_text.strip():
                            send_queue.put_nowait({"type": "chat", "msg": chat_text.strip()})
                        chat_input_active = False
                        chat_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        chat_text = chat_text[:-1]
                    else:
                        if len(chat_text) < 60:
                            chat_text += event.unicode
                else:
                    if event.key == pygame.K_SLASH or event.key == pygame.K_MINUS:
                        chat_input_active = True
                        chat_text = ""

        # Update
        if my_id in players:
            me = players[my_id]
            camera["x"] = lerp(camera["x"], me.sx, 0.1)
            camera["y"] = lerp(camera["y"], me.sy, 0.1)

        for p in players.values():
            p.sx = lerp(p.sx, p.x, 0.3)
            p.sy = lerp(p.sy, p.y, 0.3)
            
            if p.bumpStr > 0:
                apply_impulse(p.body, p.bumpNx, p.bumpNy, p.bumpStr)
                p.bumpStr = 0
            update_soft_body(p.body, 1.0)
            
            p.blinkTimer -= 1/60
            if p.blinkTimer <= 0:
                p.blinkFrame = 8
                p.blinkTimer = random.uniform(2, 6)
            if p.blinkFrame > 0:
                p.blinkFrame -= 1
                
            if p.chatTimer > 0:
                p.chatTimer -= 1

        for p in particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 0.05
        particles = [p for p in particles if p.life > 0]

        # Render
        screen.fill((6, 6, 18)) # Fondo oscuro
        
        # Grid
        grid_s = 60
        off_x = -camera["x"] % grid_s
        off_y = -camera["y"] % grid_s
        for i in range(int(w/grid_s) + 2):
            pygame.draw.line(screen, (255, 255, 255), (i*grid_s + off_x, 0), (i*grid_s + off_x, h))
        for i in range(int(h/grid_s) + 2):
            pygame.draw.line(screen, (255, 255, 255), (0, i*grid_s + off_y), (w, i*grid_s + off_y))
            
        # Add slight transparency overlay to grid (hacky way in pygame)
        overlay = pygame.Surface((w, h))
        overlay.fill((6, 6, 18))
        overlay.set_alpha(245)
        screen.blit(overlay, (0,0))
        
        # Stars
        t = pygame.time.get_ticks() / 1000.0
        for s in stars:
            sx = (s["x"] - camera["x"] * s["z"]) % w
            sy = (s["y"] - camera["y"] * s["z"]) % h
            alpha = (math.sin(t * 2 + s["phase"]) + 1) * 0.5
            color = int(100 + 155 * alpha)
            pygame.draw.circle(screen, (color, color, color), (int(sx), int(sy)), s["r"])
            
        # Particles
        for p in particles:
            sx = int(p.x - camera["x"] + w/2)
            sy = int(p.y - camera["y"] + h/2)
            color = hsl_to_color(p.hue, 1.0, 0.5)
            pygame.draw.circle(screen, color, (sx, sy), int(p.size * p.life))

        # Slimes
        for p in players.values():
            sx = p.sx - camera["x"] + w/2
            sy = p.sy - camera["y"] + h/2
            
            # Body polygon
            poly = [(sx + bp["x"], sy + bp["y"]) for bp in p.body]
            body_color = hsl_to_color(p.hue, 0.55, 0.75) # pastel
            pygame.draw.polygon(screen, body_color, poly)
            
            border_color = hsl_to_color(p.hue, 0.45, 0.45) # oscuro
            pygame.draw.polygon(screen, border_color, poly, 3)
            
            # Eyes
            speed = math.hypot(p.dx, p.dy)
            tgt_a = p.eyeAngle
            if speed > 0.4: tgt_a = math.atan2(p.dy, p.dx)
            p.eyeAngle += angle_diff(p.eyeAngle, tgt_a) * 0.1
            lx = math.cos(p.eyeAngle) * 2
            ly = math.sin(p.eyeAngle) * 1.5
            
            openness = 1.0
            if p.blinkFrame > 0:
                half = 4
                openness = (p.blinkFrame - half)/half if p.blinkFrame > half else 1 - p.blinkFrame/half
                openness = clamp(openness, 0, 1)
            
            eye_h = 10 * openness
            eye_c = hsl_to_color(p.hue, 0.40, 0.18)
            spacing = 7
            eye_y = -6
            
            if eye_h > 0.5:
                pygame.draw.line(screen, eye_c, (sx - spacing + lx, sy + eye_y + ly - eye_h/2), (sx - spacing + lx, sy + eye_y + ly + eye_h/2), 4)
                pygame.draw.line(screen, eye_c, (sx + spacing + lx, sy + eye_y + ly - eye_h/2), (sx + spacing + lx, sy + eye_y + ly + eye_h/2), 4)
            else:
                pygame.draw.line(screen, eye_c, (sx - spacing - 2 + lx, sy + eye_y + ly), (sx - spacing + 2 + lx, sy + eye_y + ly), 3)
                pygame.draw.line(screen, eye_c, (sx + spacing - 2 + lx, sy + eye_y + ly), (sx + spacing + 2 + lx, sy + eye_y + ly), 3)

            # Name tag
            name_surf = font.render(p.name, True, (255, 255, 255))
            screen.blit(name_surf, (sx - name_surf.get_width()//2, sy - 40))
            if p.id == my_id:
                pygame.draw.circle(screen, (80, 220, 120), (sx - name_surf.get_width()//2 - 8, sy - 31), 4)

            # Chat bubble
            if p.chatTimer > 0 and p.chatMsg:
                chat_surf = chat_font.render(p.chatMsg, True, (255, 255, 255))
                pad = 8
                cw = chat_surf.get_width() + pad * 2
                ch = chat_surf.get_height() + pad * 2
                cb_x = sx - cw//2
                cb_y = sy - 40 - ch - 8
                
                # Draw rounded bubble (simple rect for pygame)
                pygame.draw.rect(screen, (15, 15, 20), (cb_x, cb_y, cw, ch), border_radius=12)
                screen.blit(chat_surf, (cb_x + pad, cb_y + pad))

        # Chat Input UI
        if chat_input_active:
            pygame.draw.rect(screen, (0, 0, 0), (20, h - 60, 300, 40), border_radius=8)
            pygame.draw.rect(screen, (100, 100, 100), (20, h - 60, 300, 40), 1, border_radius=8)
            input_surf = chat_font.render(chat_text + ("|" if time.time() % 1 > 0.5 else ""), True, (255, 255, 255))
            screen.blit(input_surf, (30, h - 50))
            
        pygame.display.flip()
        
        await asyncio.sleep(0.001) # Ceder control a asyncio
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
