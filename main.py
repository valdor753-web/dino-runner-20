import pygame, random, math, json, os, wave, tempfile
try:
    import numpy as np
    HAY_NUMPY = True
except Exception:
    HAY_NUMPY = False

pygame.init()
try: pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
except pygame.error: pass

ANCHO, ALTO = 800, 400
ANDROID = 'ANDROID_ARGUMENT' in os.environ
try:
    VENTANA = pygame.display.set_mode((ANCHO, ALTO), pygame.SCALED | (pygame.FULLSCREEN if ANDROID else 0))
except pygame.error:
    VENTANA = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption('Dino Runner 2.0 - Ultimate Edition')
RELOJ = pygame.time.Clock()
FPS = 60

# ---------- DINO FRAMES (optimizado) ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DINO_DIR = os.path.join(BASE_DIR, "img", "dino")
DINO_FRAMES = {"correr": [], "salto": [], "agacharse": []}
def _load_scaled(path, target_h):
    try:
        img = pygame.image.load(path)
        # convert_alpha es mas rapido para blit y mantiene transparencia
        try:
            img = img.convert_alpha()
        except Exception:
            img = img.convert()
        w, h = img.get_size()
        scale = target_h / h
        nw, nh = int(w * scale), int(h * scale)
        # smoothscale solo si es grande, mas rapido que scale para reducciones
        if nw != w or nh != h:
            img = pygame.transform.smoothscale(img, (nw, nh))
        return img
    except Exception:
        return None

# precarga una sola vez y ya escalado -> evita lag en juego
for _n in (1,2,3,4):
    _p = os.path.join(DINO_DIR, f"correr{_n}.png")
    _im = _load_scaled(_p, 58)
    if _im: DINO_FRAMES["correr"].append(_im)
for _n in (1,2,3):
    _p = os.path.join(DINO_DIR, f"salto{_n}.png")
    _im = _load_scaled(_p, 58)
    if _im: DINO_FRAMES["salto"].append(_im)
for _n in (1,2):
    _p = os.path.join(DINO_DIR, f"agacharse{_n}.png")
    _im = _load_scaled(_p, 38)
    if _im: DINO_FRAMES["agacharse"].append(_im)

def mk_font(size, bold=True):
    for nombre in ('dejavusansmono', 'couriernew', 'courier', 'monospace'):
        try:
            f = pygame.font.SysFont(nombre, size, bold=bold)
            if f: return f
        except Exception: pass
    return pygame.font.Font(None, int(size * 1.25))

FUENTE, FUENTE_G, FUENTE_XG = mk_font(18), mk_font(27), mk_font(42)

# Carpeta de guardado: en Android el directorio del juego es de solo lectura.
DATA_DIR = os.environ.get('ANDROID_PRIVATE') or os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(DATA_DIR, '.w'), 'w') as _f: _f.write('1')
    os.remove(os.path.join(DATA_DIR, '.w'))
except Exception:
    DATA_DIR = tempfile.gettempdir()
SAVE_FILE = os.path.join(DATA_DIR, 'progreso_dino.json')
SCORE_FILE = os.path.join(DATA_DIR, 'top_scores.txt')

# ---------- SAVE / RECORD ----------
def default_save():
    return {'monedas': 0, 'mejor_puntuacion': 0, 'niveles_desbloqueados': 1,
            'dino': 'clasico', 'arma': 'fuego', 'mejoras': {'vida': 0, 'salto': 0, 'velocidad': 0, 'escudo': 0},
            'armas': ['fuego'], 'dinos': ['clasico']}
def load_save():
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f: d = json.load(f)
        base = default_save(); base.update(d)
        base['mejoras'] = {**default_save()['mejoras'], **d.get('mejoras', {})}
        return base
    except Exception:
        return default_save()
def save_progress():
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f: json.dump(progreso, f, indent=2, ensure_ascii=False)
    except Exception: pass
def load_scores():
    # Formato nuevo: "NOMBRE|puntos|tipo" por linea (tipo: pelea/resistencia/''). Acepta formatos viejos sin tipo.
    try:
        datos = []
        with open(SCORE_FILE, 'r', encoding='utf-8') as f:
            for linea in f.read().splitlines():
                linea = linea.strip()
                if not linea: continue
                if '|' in linea:
                    partes = linea.split('|')
                    n = partes[0][:10]; p = int(partes[1]); t = partes[2] if len(partes) > 2 else ''
                    datos.append((n, p, t))
                else:
                    for p in linea.split(): datos.append(('JUGADOR', int(p), ''))
        return sorted(datos, key=lambda d: d[1], reverse=True)[:10]
    except Exception: return []
def save_score(score, tipo=''):
    global scores
    scores = sorted(scores + [(nombre_jugador or 'JUGADOR', score, tipo)], key=lambda d: d[1], reverse=True)[:10]
    try:
        with open(SCORE_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(f'{n}|{p}|{t}' for n, p, t in scores))
    except Exception: pass

progreso = load_save(); scores = load_scores()
nombre_jugador = str(progreso.get('nombre', ''))[:10]

# ---------- AUDIO ----------
FS = 44100
SONIDOS = {}
def tone(freq, dur, vol=.25):
    n = max(1, int(FS * dur)); t = np.arange(n) / FS
    a = np.sin(2 * np.pi * freq * t) * np.linspace(1, 0, n) ** .7 * vol
    a = np.clip(a * 32767, -32767, 32767).astype(np.int16)
    if pygame.mixer.get_init() and pygame.mixer.get_init()[2] == 2: a = np.column_stack((a, a))
    return pygame.sndarray.make_sound(a)
def noise(dur, vol=.2):
    n = max(1, int(FS * dur)); a = np.random.uniform(-1, 1, n) * np.linspace(1, 0, n) ** .8 * vol
    a = np.clip(a * 32767, -32767, 32767).astype(np.int16)
    if pygame.mixer.get_init() and pygame.mixer.get_init()[2] == 2: a = np.column_stack((a, a))
    return pygame.sndarray.make_sound(a)
if HAY_NUMPY:
    try:
        SONIDOS = {'salto': tone(620, .12, .3), 'disparo': tone(1100, .07, .22), 'moneda': tone(900, .08, .25),
                   'golpe': noise(.25, .35), 'power': tone(500, .25, .35), 'compra': tone(800, .16, .3),
                   'jefe': tone(120, .5, .35), 'victoria': tone(900, .8, .35), 'error': tone(180, .15, .25)}
    except Exception: SONIDOS = {}
def play(s):
    if s in SONIDOS: SONIDOS[s].play()

def start_music():
    # Música procedural corta, guardada como WAV temporal y repetida en bucle.
    if not (HAY_NUMPY and pygame.mixer.get_init()): return
    path = os.path.join(tempfile.gettempdir(), 'dino_runner_music.wav')
    if not os.path.exists(path):
        dur = .42; notes = [220, 277, 330, 277, 196, 247, 294, 247]; samples = []
        for f in notes:
            n = int(FS * dur); t = np.arange(n) / FS
            samples.append((np.sin(2 * np.pi * f * t) * .08 + np.sin(2 * np.pi * f * 2 * t) * .025) * np.linspace(1, .2, n))
        arr = np.clip(np.concatenate(samples) * 32767, -32767, 32767).astype(np.int16)
        stereo = np.column_stack((arr, arr))
        with wave.open(path, 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(FS); w.writeframes(stereo.tobytes())
    try:
        pygame.mixer.music.load(path); pygame.mixer.music.set_volume(.16); pygame.mixer.music.play(-1)
    except Exception: pass
start_music()

# ---------- GAME DATA ----------
DINOS = {
 'clasico':     {'nombre': 'DINO CLASICO', 'precio': 0,   'color': (70, 190, 70),  'salto': 13,   'vel': 1.00, 'vida': 0},
 'raptor':      {'nombre': 'RAPTOR',       'precio': 80,  'color': (60, 150, 220), 'salto': 14,   'vel': 1.10, 'vida': 0},
 'triceratops': {'nombre': 'TRICERATOPS',  'precio': 150, 'color': (210, 130, 60), 'salto': 11.5, 'vel': 0.95, 'vida': 1},
 'rex':         {'nombre': 'T-REX',        'precio': 250, 'color': (190, 60, 70),  'salto': 12.5, 'vel': 1.03, 'vida': 2}}
ARMAS = {
 'fuego':  {'nombre': 'BOLA DE FUEGO', 'precio': 0,   'color': (255, 150, 20),  'danio': 1, 'cooldown': 16, 'cantidad': 1, 'vel': 17},
 'triple': {'nombre': 'TRIPLE SHOT',   'precio': 180, 'color': (80, 210, 255),  'danio': 1, 'cooldown': 20, 'cantidad': 3, 'vel': 16},
 'pesada': {'nombre': 'BOLA PESADA',   'precio': 260, 'color': (210, 90, 255),  'danio': 2, 'cooldown': 28, 'cantidad': 1, 'vel': 12},
 'rapida': {'nombre': 'RAPID FIRE',    'precio': 350, 'color': (255, 245, 80),  'danio': 1, 'cooldown': 7,  'cantidad': 1, 'vel': 19}}
MEJORAS = [('vida', 'VIDA EXTRA', 100, '+1 vida inicial'), ('salto', 'SUPER SALTO', 120, 'salto +1'),
           ('velocidad', 'PIERNAS RAPIDAS', 140, 'velocidad +8%'), ('escudo', 'ESCUDO', 220, 'bloquea un golpe por partida')]
NIVELES = [('PUERTA DE MADERA', 'BOSQUE'), ('PUERTA DE PIEDRA', 'CUEVA'), ('PUERTA METALICA', 'FABRICA'),
           ('PUERTA FUTURISTA', 'CIUDAD'), ('PORTAL ESPACIAL', 'ESPACIO'), ('PUERTA DEL JEFE', 'CASTILLO'),
           ('PUERTA VOLCANICA', 'VOLCAN'), ('PORTAL FINAL', 'DIMENSION X')]

# Normaliza partidas antiguas que no tengan estos campos.
if progreso.get('dino') not in DINOS: progreso['dino'] = 'clasico'
if progreso.get('arma') not in ARMAS: progreso['arma'] = 'fuego'
progreso['dinos'] = [k for k in progreso.get('dinos', ['clasico']) if k in DINOS] or ['clasico']
progreso['armas'] = [k for k in progreso.get('armas', ['fuego']) if k in ARMAS] or ['fuego']
save_progress()

# ---------- STATE ----------
estado = 'menu'; menu_sel = 0
dino_sel = list(DINOS).index(progreso['dino']); arma_sel = list(ARMAS).index(progreso['arma'])
nivel = 1; puntos = 0; monedas_partida = 0; vidas = 3; tiempo = 0; limite_tiempo = 60
x = 60.; y = 300.; vy = 0.; saltos = 0; agachado = False; invuln = 0; escudo = False
velocidad = 8.; obstaculos = []; monedas = []; enemigos = []; proyectiles = []; particulas = []
puerta_timer = 0; puerta_nivel = 1; mensaje = ''; mensaje_timer = 0
jefe = None; jefe_timer = 0; juego_ganado = False; gameover_reason = ''; tipo_victoria = ''
corona = None; caja_proteccion = None; proteccion_timer = 0
frame = 0; shot_timer = 0; caja_timer = 0; corona_timer = 0; boss_proyectiles = []; scroll = 0.
jefes_vencidos = set(); jefe_vencido = ''

# ---------- CONTROLES TACTILES ----------
# Botones virtuales estilo consola: mano izquierda mueve, mano derecha salta y dispara.
BTN_JUEGO = {
    'izq':     pygame.Rect(14, 300, 64, 64),
    'der':     pygame.Rect(86, 300, 64, 64),
    'abajo':   pygame.Rect(50, 228, 64, 64),
    'salto':   pygame.Rect(722, 300, 64, 64),
    'disparo': pygame.Rect(650, 228, 64, 64),
    'esc':     pygame.Rect(742, 8, 46, 34)}
BTN_MENU = {
    'arriba': pygame.Rect(30, 228, 64, 64),
    'abajo':  pygame.Rect(30, 300, 64, 64),
    'enter':  pygame.Rect(706, 300, 80, 64),
    'esc':    pygame.Rect(706, 228, 80, 64)}
ICONOS = {'izq': '<', 'der': '>', 'abajo': 'v', 'arriba': '^', 'salto': 'A', 'disparo': 'FUEGO',
          'enter': 'OK', 'esc': 'ATRAS'}
# Teclado en pantalla para escribir el nombre antes de jugar.
BTN_NOMBRE = {}
for _fila, _txt in enumerate(('ABCDEFGHIJ', 'KLMNOPQRST')):
    for _i, _ch in enumerate(_txt):
        BTN_NOMBRE[_ch] = pygame.Rect(48 + _i * 71, 152 + _fila * 54, 62, 46)
for _i, _ch in enumerate('UVWXYZ'):
    BTN_NOMBRE[_ch] = pygame.Rect(48 + _i * 71, 260, 62, 46)
BTN_NOMBRE['BORRAR'] = pygame.Rect(474, 260, 130, 46)
BTN_NOMBRE['JUGAR'] = pygame.Rect(614, 260, 134, 46)
BTN_NOMBRE['esc'] = pygame.Rect(624, 96, 124, 40)
dedos = {}          # toques activos (multitáctil) normalizados a coordenadas del juego
antes_pulsado = set()
repeticion = {}

def botones_activos():
    if estado == 'nombre': return BTN_NOMBRE
    return BTN_JUEGO if estado in ('play', 'boss', 'puerta') else BTN_MENU

def puntos_tactiles():
    pts = list(dedos.values())
    if pygame.mouse.get_pressed()[0]: pts.append(pygame.mouse.get_pos())
    return pts

def tocado(nombre):
    r = botones_activos().get(nombre)
    return bool(r) and any(r.collidepoint(p) for p in puntos_tactiles())

def mantenido(nombre):
    # Detección continua: sirve para correr o mantenerse agachado.
    k = pygame.key.get_pressed()
    teclas = {'izq': (pygame.K_LEFT, pygame.K_a), 'der': (pygame.K_RIGHT, pygame.K_d),
              'abajo': (pygame.K_DOWN, pygame.K_s), 'salto': (pygame.K_SPACE, pygame.K_UP),
              'disparo': (pygame.K_RETURN,)}.get(nombre, ())
    return any(k[t] for t in teclas) or tocado(nombre)

def procesar_toques():
    # Convierte los toques mantenidos en acciones (con repetición en los menús).
    global antes_pulsado
    previo = estado
    ahora = {n for n in botones_activos() if tocado(n)}
    for n in sorted(ahora):
        if n not in antes_pulsado:
            repeticion[n] = 20; accion(n)
        elif n in ('arriba', 'abajo'):
            repeticion[n] = repeticion.get(n, 20) - 1
            if repeticion[n] <= 0: repeticion[n] = 7; accion(n)
        if estado != previo:
            # Cambió de pantalla: el dedo que sigue apoyado no debe pulsar el botón nuevo.
            antes_pulsado = {b for b in botones_activos() if tocado(b)}
            return
    antes_pulsado = ahora

CACHE_BTN = {}
def dibujar_botones():
    # Botones semitransparentes para que los pulgares no tapen el juego.
    for n, r in botones_activos().items():
        if n not in CACHE_BTN:
            s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            if r.w == r.h:
                pygame.draw.circle(s, (12, 20, 34, 92), (r.w // 2, r.h // 2), r.w // 2)
                pygame.draw.circle(s, (255, 255, 255, 70), (r.w // 2, r.h // 2), r.w // 2, 2)
            else:
                pygame.draw.rect(s, (12, 20, 34, 92), (0, 0, r.w, r.h), border_radius=10)
                pygame.draw.rect(s, (255, 255, 255, 70), (0, 0, r.w, r.h), 2, border_radius=10)
            col = (255, 220, 80) if n in ('salto', 'enter', 'JUGAR') else (255, 140, 90) if n in ('disparo', 'BORRAR') else (225, 235, 250)
            etiqueta = ICONOS.get(n, n)
            f = FUENTE if len(etiqueta) > 2 else FUENTE_G
            et = f.render(etiqueta, True, col); et.set_alpha(215)
            s.blit(et, (r.w // 2 - et.get_width() // 2, r.h // 2 - et.get_height() // 2))
            CACHE_BTN[n] = s
        VENTANA.blit(CACHE_BTN[n], r.topleft)
        if tocado(n):
            pygame.draw.circle(VENTANA, (255, 255, 255), r.center, r.w // 2 - 2, 2) if r.w == r.h else \
                pygame.draw.rect(VENTANA, (255, 255, 255), r, 2, border_radius=10)

# ---------- HELPERS ----------
def text(txt, ty, font=FUENTE, color=(255, 255, 255), center=True, sombra=True):
    s = font.render(txt, True, color)
    px = ANCHO // 2 - s.get_width() // 2 if center else 12
    if sombra:
        sh = font.render(txt, True, (0, 0, 0)); sh.set_alpha(150); VENTANA.blit(sh, (px + 2, ty + 2))
    VENTANA.blit(s, (px, ty)); return s

def panel(rect, alpha=110, color=(8, 14, 26), radio=10):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), (0, 0, rect.w, rect.h), border_radius=radio)
    pygame.draw.rect(s, (255, 255, 255, 45), (0, 0, rect.w, rect.h), 1, border_radius=radio)
    VENTANA.blit(s, rect.topleft)

def gradiente(w, h, c1, c2):
    s = pygame.Surface((w, h))
    for i in range(h):
        f = i / max(1, h - 1)
        s.fill(tuple(int(c1[k] * (1 - f) + c2[k] * f) for k in range(3)), (0, i, w, 1))
    return s

def brillo(px, py, r, color, alpha=70):
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(4, 0, -1):
        pygame.draw.circle(s, (*color, alpha // i), (r, r), int(r * i / 4))
    VENTANA.blit(s, (px - r, py - r))

def sombra_suelo(px, py, w, h=8, alpha=80):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, alpha), (0, 0, w, h))
    VENTANA.blit(s, (px, py))

def rect_player():
    return pygame.Rect(int(x) + 5, int(y) + (25 if agachado else 4), 40 if agachado else 30, 16 if agachado else 45)
def level_speed():
    return min(23, [8, 10, 12, 14, 16, 17, 19, 21][nivel - 1]) * DINOS[progreso['dino']]['vel'] * (1 + progreso['mejoras']['velocidad'] * .08)
def set_message(s, d=100):
    global mensaje, mensaje_timer; mensaje = s; mensaje_timer = d

def spawn_group(px=None):
    # Grupos pasables: crecen poco a poco con el nivel, sin bloquear todo el camino.
    if px is None: px = 850
    max_count = 1 if nivel <= 1 else (2 if nivel <= 3 else 3)
    cur, arr = px, []
    min_gap, max_gap = (95, 155) if nivel <= 2 else ((80, 135) if nivel <= 4 else (65, 120))
    for _ in range(random.randint(1, max_count)):
        weights = [0.45, 0.25, 0.20, 0.10] if nivel <= 2 else [0.40, 0.22, 0.28, 0.10]
        typ = random.choices(['cactus', 'roca', 'avion', 'agua'], weights)[0]
        yy = {'cactus': 300, 'roca': 300, 'avion': random.choice([190, 245, 285]), 'agua': 300}[typ]
        w = random.choice([28, 38, 48]) if typ != 'avion' else 34
        arr.append({'x': cur, 'y': yy, 'w': w, 'tipo': typ})
        cur += w + random.randint(min_gap, max_gap)
    return arr

def spawn_coin():
    if random.random() < .55: monedas.append({'x': 850, 'y': random.choice([190, 240, 285]), 'r': 8})

def spawn_enemy():
    # Enemigos escalonados: el nivel 2 admite como máximo uno a la vez.
    cap = {1: 0, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 7: 4, 8: 5}.get(nivel, 5)
    if len(enemigos) >= cap: return
    if random.random() > {2: .006, 3: .010, 4: .015, 5: .020, 6: .024, 7: .028, 8: .032}.get(nivel, .005): return
    tipos = ['murcielago', 'raptor_enemigo', 'robot'] + (['raptor_enemigo', 'robot'] if nivel >= 5 else [])
    enemigos.append({'x': 850 + random.randint(0, 120), 'y': random.choice([215, 255, 295]),
                     'tipo': random.choice(tipos),
                     'vx': velocidad * (0.58 + nivel * 0.012) + random.uniform(0.5, 2.0),
                     'phase': random.random() * 6})

def add_particles(px, py, col=(255, 170, 30), n=10):
    for _ in range(n):
        particulas.append([px, py, random.uniform(-3, 3), random.uniform(-4, 1), random.randint(2, 5), col])

def reset_run():
    global estado, nivel, puntos, monedas_partida, vidas, tiempo, limite_tiempo, x, y, vy, saltos, agachado, invuln, escudo
    global velocidad, obstaculos, monedas, enemigos, proyectiles, particulas, puerta_timer, puerta_nivel, jefe, jefe_timer
    global juego_ganado, gameover_reason, tipo_victoria, shot_timer, corona, caja_proteccion, proteccion_timer, caja_timer, corona_timer, boss_proyectiles
    nivel = 1; puntos = 0; monedas_partida = 0; tiempo = 0; limite_tiempo = 60
    vidas = 3 + DINOS[progreso['dino']]['vida'] + progreso['mejoras']['vida']
    x = 60.; y = 300.; vy = 0.; saltos = 0; agachado = False; invuln = 0
    escudo = progreso['mejoras']['escudo'] > 0
    velocidad = level_speed(); obstaculos = spawn_group(850); monedas = []; enemigos = []; proyectiles = []; particulas = []
    puerta_timer = 100; puerta_nivel = 1; jefe = None; jefe_timer = 0; juego_ganado = False; gameover_reason = ''; tipo_victoria = ''
    corona = None; caja_proteccion = None; proteccion_timer = 0; shot_timer = 0
    caja_timer = 300; corona_timer = 480; boss_proyectiles = []; jefes_vencidos.clear(); estado = 'puerta'

def start_game():
    reset_run()

def next_level():
    global nivel, velocidad, puerta_timer, puerta_nivel, estado, caja_timer, corona_timer, corona, caja_proteccion
    if nivel >= 8: boss_start(final=True); return
    nivel += 1
    velocidad = level_speed(); puerta_nivel = nivel; puerta_timer = 100; estado = 'puerta'
    obstaculos.clear(); enemigos.clear(); proyectiles.clear()
    corona = None; caja_proteccion = None; caja_timer = 120; corona_timer = 300

def hurt(reason='OBSTACULO'):
    global vidas, invuln, escudo, estado, gameover_reason, x, y, vy, obstaculos
    if invuln > 0: return
    if escudo:
        escudo = False; add_particles(x + 20, y + 20, (80, 210, 255), 25); set_message('¡ESCUDO ROTO!', 70); return
    vidas -= 1; invuln = 100; add_particles(x + 20, y + 20, (255, 60, 60), 25); play('golpe')
    if vidas <= 0:
        gameover_reason = reason; estado = 'gameover'; save_score(puntos)
        progreso['mejor_puntuacion'] = max(progreso['mejor_puntuacion'], puntos); save_progress()
    else:
        x = 60.; y = 300.; vy = 0.; obstaculos = spawn_group(850); set_message('¡TE GOLPEARON! VIDAS: ' + str(vidas), 90)

def shoot():
    global shot_timer
    if shot_timer > 0: return
    a = ARMAS[progreso['arma']]; base_y = y + 18
    for i in range(a['cantidad']):
        off = (i - (a['cantidad'] - 1) / 2) * 4
        proyectiles.append({'x': x + 45, 'y': base_y, 'vx': a['vel'], 'vy': off, 'd': a['danio'], 'r': 7})
    shot_timer = a['cooldown']; play('disparo')

def boss_start(final=False):
    global jefe, estado, jefe_timer, nivel, boss_proyectiles, x, y, vy, saltos, agachado, invuln
    global corona, caja_proteccion, caja_timer, corona_timer
    # 'tipo' decide el dibujo (dragon/titan); 'name' es el nombre mostrado. El jefe final es siempre un dragon.
    bosses = {3: ('DRAGON', 'dragon', (190, 40, 50), 12, 11.0),
              6: ('TITAN', 'titan', (100, 70, 170), 18, 12.5),
              8: ('DRAGON REY', 'dragon', (150, 30, 165), 26, 14.5)}
    if final: nivel = 8
    name, tipo, color, hp, attack_speed = bosses.get(nivel, bosses[8])
    jefe = {'x': 620., 'y': 180., 'hp': hp, 'max': hp, 'type': tipo, 'name': name, 'color': color,
            'attack_speed': attack_speed, 'phase': 0.0, 'final': nivel == 8}
    jefe_timer = 0; estado = 'boss'; obstaculos.clear(); enemigos.clear(); proyectiles.clear(); boss_proyectiles = []
    corona = None; caja_proteccion = None; caja_timer = 120; corona_timer = 300
    # Al entrar al jefe el Dino siempre aparece en el suelo y con invulnerabilidad breve.
    x = 60.; y = 300.; vy = 0.; saltos = 0; agachado = False; invuln = 90
    play('jefe'); set_message('¡JEFE: ' + name + '!', 140)

def victoria_resistencia():
    # Completar los 8 niveles sin enfrentar al dragon final: victoria POR RESISTENCIA.
    global estado, juego_ganado, tipo_victoria, puntos, monedas_partida
    puntos += 200; monedas_partida += 30; progreso['monedas'] += 30
    progreso['mejor_puntuacion'] = max(progreso['mejor_puntuacion'], puntos)
    tipo_victoria = 'resistencia'; save_score(puntos, tipo_victoria); save_progress()
    estado = 'victory'; juego_ganado = True; play('victoria')

def buy(kind):
    for k, nombre, precio, desc in MEJORAS:
        if k == kind:
            lvl = progreso['mejoras'][k]; cost = precio * (lvl + 1)
            if progreso['monedas'] >= cost and lvl < 3:
                progreso['monedas'] -= cost; progreso['mejoras'][k] += 1
                save_progress(); play('compra'); set_message('¡MEJORA COMPRADA!', 80)
            else: play('error')

def buy_dino(key):
    if key not in progreso['dinos']:
        if progreso['monedas'] >= DINOS[key]['precio']:
            progreso['monedas'] -= DINOS[key]['precio']; progreso['dinos'].append(key); save_progress(); play('compra')
        else: play('error')
def buy_weapon(key):
    if key not in progreso['armas']:
        if progreso['monedas'] >= ARMAS[key]['precio']:
            progreso['monedas'] -= ARMAS[key]['precio']; progreso['armas'].append(key); save_progress(); play('compra')
        else: play('error')

# ---------- DRAWING (OPTIMIZADO CON IMAGENES) ----------
TEMAS = [((120, 200, 245), (222, 246, 214)), ((32, 30, 48), (96, 72, 58)), ((62, 72, 84), (148, 112, 78)),
         ((14, 12, 58), (58, 84, 134)), ((4, 4, 26), (22, 26, 68)), ((28, 8, 32), (78, 16, 38)),
         ((78, 20, 6), (156, 58, 16)), ((10, 6, 24), (48, 16, 74))]
SUELOS = [(96, 158, 78), (78, 60, 48), (108, 84, 60), (44, 52, 92), (26, 28, 62), (62, 26, 42), (118, 44, 16), (44, 18, 66)]
CACHE_FONDO = {}
FONDOS = {}
def _load_fondos():
    for lv in range(1, 9):
        p = os.path.join(BASE_DIR, "img", "fondo", f"fondo{lv}.png")
        try:
            img = pygame.image.load(p)
            try: img = img.convert()
            except: pass
            # asegura 800x400
            if img.get_size() != (ANCHO, ALTO):
                img = pygame.transform.smoothscale(img, (ANCHO, ALTO))
            FONDOS[lv] = img
        except Exception:
            # fallback gradiente procedural cacheado
            top, bot = TEMAS[lv-1]
            s = gradiente(ANCHO, 350, top, bot)
            suelo = gradiente(ANCHO, 50, SUELOS[lv-1], tuple(max(0,c-38) for c in SUELOS[lv-1]))
            base = pygame.Surface((ANCHO, ALTO)); base.blit(s,(0,0)); base.blit(suelo,(0,350))
            FONDOS[lv] = base
_load_fondos()
def fondo_nivel(lv):
    return FONDOS.get(lv, CACHE_FONDO.get(lv))

def draw_bg(lv):
    img = FONDOS.get(lv)
    if img is not None:
        VENTANA.blit(img, (0, 0))
    else:
        VENTANA.blit(fondo_nivel(lv), (0, 0))
    # NIVEL 1: solo suelo verde solido + 1 nube
    if lv == 1:
        cx = int((scroll * 0.12) % 900) - 120
        cy = 42
        pygame.draw.ellipse(VENTANA, (255, 255, 255), (cx, cy+10, 110, 38))
        pygame.draw.ellipse(VENTANA, (255, 255, 255), (cx+22, cy, 88, 34))
        pygame.draw.ellipse(VENTANA, (245, 245, 245), (cx+18, cy+18, 94, 22))
        # suelo donde corre - solo verde solido
        pygame.draw.rect(VENTANA, (46, 158, 70), (0, 350, 800, 50))
        return
    # otros niveles: solo linea de suelo barata
    pygame.draw.line(VENTANA, (245, 245, 245), (0, 350), (800, 350), 2)
    for i in range(20):
        gx = (i * 60 - scroll) % 860 - 30
        pygame.draw.line(VENTANA, (255, 255, 255), (gx, 356), (gx + 22, 356), 2)
        pygame.draw.circle(VENTANA, (0, 0, 0), (int((gx * 1.7) % 800), 372 + (i % 3) * 7), 2)

def draw_dino(px, py, col, kind='clasico', fr=0, enemy=False):
    # Enemigo sigue siendo procedural minimo (raptor), jugador usa frames de E:\dino run\img\dino
    if enemy:
        # enemigo raptor simple y rapido (sin todo el detalle del jugador)
        c = col; osc = tuple(max(0, v - 55) for v in c)
        pygame.draw.rect(VENTANA, c, (px + 10, py + 14, 28, 27), border_radius=9)
        pygame.draw.rect(VENTANA, osc, (px + 12, py + 32, 24, 8), border_radius=4)
        pygame.draw.rect(VENTANA, c, (px + 22, py, 26, 21), border_radius=8)
        pygame.draw.circle(VENTANA, (255, 255, 255), (px + 41, py + 7), 5)
        pygame.draw.circle(VENTANA, (18, 18, 22), (px + 42, py + 7), 2)
        return
    # --- JUGADOR: solo frames ---
    sombra_suelo(px + 4, 344, 46, 8, 70 if py < 290 else 95)
    # agachado
    if agachado:
        if DINO_FRAMES["agacharse"]:
            idx = (fr // 8) % len(DINO_FRAMES["agacharse"])
            img = DINO_FRAMES["agacharse"][idx]
            # centrado para que los pies queden en 344
            VENTANA.blit(img, (px - 2, py + 8))
        return
    # en el aire -> salto
    if y < 300 or vy != 0:
        if DINO_FRAMES["salto"]:
            if vy < -4:
                img = DINO_FRAMES["salto"][0]
            elif vy > 4:
                img = DINO_FRAMES["salto"][2] if len(DINO_FRAMES["salto"]) > 2 else DINO_FRAMES["salto"][-1]
            else:
                img = DINO_FRAMES["salto"][1] if len(DINO_FRAMES["salto"]) > 1 else DINO_FRAMES["salto"][0]
            VENTANA.blit(img, (px - 5, py - 4))
        return
    # corriendo
    if DINO_FRAMES["correr"]:
        idx = (fr // 5) % len(DINO_FRAMES["correr"])
        img = DINO_FRAMES["correr"][idx]
        VENTANA.blit(img, (px - 5, py - 6))
        return

def draw_coin(c):
    cx, cy, r = int(c['x']), int(c['y']), c['r']
    w = max(2, int(abs(math.sin(frame * .12 + cx * .05)) * r))
    brillo(cx, cy, r + 6, (255, 210, 60), 60)
    pygame.draw.ellipse(VENTANA, (255, 205, 40), (cx - w, cy - r, w * 2, r * 2))
    pygame.draw.ellipse(VENTANA, (255, 245, 150), (cx - w, cy - r, w * 2, r * 2), 2)
    if w > 4: pygame.draw.ellipse(VENTANA, (255, 240, 130), (cx - w + 2, cy - r + 3, max(2, w), r))

def draw_avion(xx, yy):
    # Avión enemigo: reemplaza a los antiguos pájaros.
    cuerpo, osc, acento = (232, 238, 248), (146, 156, 172), (222, 62, 58)
    bal = math.sin(frame * .15 + xx * .02) * 2
    yy = int(yy + bal)
    pygame.draw.polygon(VENTANA, osc, [(xx + 24, yy + 12), (xx + 44, yy + 1), (xx + 34, yy + 14)])
    pygame.draw.ellipse(VENTANA, cuerpo, (xx, yy + 8, 42, 14))
    pygame.draw.ellipse(VENTANA, osc, (xx, yy + 8, 42, 14), 1)
    pygame.draw.polygon(VENTANA, cuerpo, [(xx + 2, yy + 9), (xx - 10, yy + 15), (xx + 2, yy + 21)])
    pygame.draw.polygon(VENTANA, acento, [(xx + 34, yy + 9), (xx + 48, yy - 5), (xx + 47, yy + 11)])
    pygame.draw.polygon(VENTANA, (198, 206, 220), [(xx + 20, yy + 17), (xx + 40, yy + 30), (xx + 32, yy + 18)])
    pygame.draw.rect(VENTANA, acento, (xx + 6, yy + 13, 16, 3), border_radius=2)
    pygame.draw.circle(VENTANA, (110, 205, 255), (xx + 8, yy + 14), 4)
    pygame.draw.circle(VENTANA, (255, 255, 255), (xx + 7, yy + 13), 2)
    h = abs(math.sin(frame * .9)) * 9 + 3
    pygame.draw.line(VENTANA, (70, 70, 80), (xx - 9, int(yy + 15 - h)), (xx - 9, int(yy + 15 + h)), 2)
    for i in range(4):
        pygame.draw.circle(VENTANA, (255, 255, 255), (xx + 52 + i * 9, yy + 15 + int(math.sin(frame * .3 + i) * 2)), max(1, 4 - i))

def draw_obs(o):
    xx, yy, w = int(o['x']), int(o['y']), o['w']
    if o['tipo'] == 'cactus':
        sombra_suelo(xx, 344, w + 10)
        pygame.draw.rect(VENTANA, (38, 132, 58), (xx + 8, yy, w - 12, 45), border_radius=6)
        pygame.draw.rect(VENTANA, (66, 176, 86), (xx + 10, yy + 3, 5, 38), border_radius=3)
        pygame.draw.rect(VENTANA, (38, 132, 58), (xx, yy + 15, 11, 15), border_radius=5)
        pygame.draw.rect(VENTANA, (38, 132, 58), (xx + w - 5, yy + 8, 11, 17), border_radius=5)
        for i in range(yy + 6, yy + 42, 9):
            pygame.draw.line(VENTANA, (200, 235, 190), (xx + 10, i), (xx + 6, i - 3), 1)
    elif o['tipo'] == 'roca':
        sombra_suelo(xx - 2, 344, w + 14)
        pts = [(xx, yy + 45), (xx + 8, yy + 22), (xx + w // 2, yy + 14), (xx + w - 8, yy + 27), (xx + w, yy + 45)]
        pygame.draw.polygon(VENTANA, (88, 88, 96), pts)
        pygame.draw.polygon(VENTANA, (124, 124, 134), [(xx + 8, yy + 22), (xx + w // 2, yy + 14), (xx + w // 2, yy + 30)])
        pygame.draw.polygon(VENTANA, (58, 58, 66), pts, 2)
    elif o['tipo'] == 'agua':
        pygame.draw.rect(VENTANA, (22, 92, 175), (xx, yy + 31, w, 14), border_radius=4)
        pygame.draw.rect(VENTANA, (54, 152, 235), (xx + 2, yy + 32, w - 4, 6), border_radius=3)
        for i in range(0, w, 10):
            pygame.draw.circle(VENTANA, (190, 230, 255), (xx + i + 5, yy + 33 + int(math.sin(frame * .2 + i) * 2)), 2)
    else:
        draw_avion(xx, yy)

def draw_enemy(e):
    xx, yy = int(e['x']), int(e['y'])
    c = {'murcielago': (92, 68, 128), 'raptor_enemigo': (185, 62, 72), 'robot': (132, 152, 168)}[e['tipo']]
    if e['tipo'] == 'murcielago':
        al = math.sin(e['phase'] * 2) * 8
        pygame.draw.polygon(VENTANA, c, [(xx, yy + 15), (xx + 14, yy + al), (xx + 28, yy + 15), (xx + 40, yy + 3 + al), (xx + 35, yy + 25), (xx + 5, yy + 25)])
        pygame.draw.circle(VENTANA, (30, 20, 44), (xx + 20, yy + 17), 8)
        pygame.draw.circle(VENTANA, (255, 90, 90), (xx + 17, yy + 15), 2)
        pygame.draw.circle(VENTANA, (255, 90, 90), (xx + 24, yy + 15), 2)
    elif e['tipo'] == 'robot':
        pygame.draw.rect(VENTANA, c, (xx + 6, yy + 8, 30, 26), border_radius=6)
        pygame.draw.rect(VENTANA, (92, 108, 124), (xx + 10, yy + 12, 22, 8), border_radius=3)
        pygame.draw.circle(VENTANA, (255, 80, 60), (xx + 16, yy + 16), 3)
        pygame.draw.circle(VENTANA, (255, 80, 60), (xx + 26, yy + 16), 3)
        pygame.draw.rect(VENTANA, (70, 82, 96), (xx + 12, yy + 34, 7, 8), border_radius=2)
        pygame.draw.rect(VENTANA, (70, 82, 96), (xx + 24, yy + 34, 7, 8), border_radius=2)
        pygame.draw.line(VENTANA, (190, 210, 230), (xx + 21, yy + 8), (xx + 21, yy), 2)
        pygame.draw.circle(VENTANA, (120, 230, 255), (xx + 21, yy - 2), 3)
    else:
        draw_dino(xx, yy, c, 'rex', frame, True)

def draw_dragon(bx, by, c, osc, cl):
    # Dragon alado con su propia anatomia: ala, cuello curvo, hocico largo y cuernos hacia atras.
    # El dragon final (jefe['final']) es mas grande e imponente, con brillo y aura propias.
    grande = jefe.get('final', False)
    aleteo = math.sin(jefe['phase'] * 2.2)
    sombra_suelo(bx + 40, 348, 170 if grande else 150, 14 if grande else 12, 90 if grande else 85)
    brillo(bx + 95, by + 60, 160 if grande else 130, c, 55 if grande else 40)
    if grande: brillo(bx + 60, by + 10, 90, (255, 90, 60), 35)
    ala = [(bx + 96, by + 52), (bx + 148, by - 42 - 20 * aleteo), (bx + 200, by - 2 - 12 * aleteo),
           (bx + 172, by + 16), (bx + 196, by + 54), (bx + 132, by + 76)]
    pygame.draw.polygon(VENTANA, osc, ala)
    pygame.draw.polygon(VENTANA, cl, ala, 3)
    for p in (ala[1], ala[2], ala[4]):
        pygame.draw.line(VENTANA, cl, (bx + 100, by + 56), (int(p[0]), int(p[1])), 3)
    pygame.draw.polygon(VENTANA, c, [(bx + 118, by + 78), (bx + 198, by + 66), (bx + 252, by + 96),
                                     (bx + 204, by + 96), (bx + 128, by + 108)])
    pygame.draw.polygon(VENTANA, cl, [(bx + 252, by + 96), (bx + 226, by + 74), (bx + 232, by + 116)])
    pygame.draw.line(VENTANA, osc, (bx + 92, by + 128), (bx + 78, by + 176), 15)
    pygame.draw.line(VENTANA, osc, (bx + 138, by + 124), (bx + 148, by + 176), 15)
    for px in (78, 148):
        for d in (-11, 0, 11):
            pygame.draw.line(VENTANA, cl, (bx + px, by + 176), (bx + px + d - 4, by + 184), 4)
    pygame.draw.ellipse(VENTANA, c, (bx + 50, by + 46, 118, 88))
    pygame.draw.ellipse(VENTANA, cl, (bx + 66, by + 76, 76, 44))
    for i in range(3):
        pygame.draw.arc(VENTANA, osc, (bx + 70 + i * 6, by + 80, 64, 36), 3.6, 5.8, 2)
    cuello = [(bx + 74, by + 62), (bx + 58, by + 20), (bx + 40, by - 6), (bx + 64, by - 12),
              (bx + 88, by + 18), (bx + 104, by + 58)]
    pygame.draw.polygon(VENTANA, c, cuello)
    pygame.draw.polygon(VENTANA, cl, [(bx + 78, by + 58), (bx + 66, by + 16), (bx + 56, by - 4), (bx + 70, by - 2), (bx + 92, by + 54)])
    pygame.draw.ellipse(VENTANA, c, (bx + 12, by - 20, 58, 36))
    pygame.draw.polygon(VENTANA, c, [(bx + 26, by - 12), (bx - 22, by - 2), (bx - 20, by + 9), (bx + 30, by + 10)])
    pygame.draw.polygon(VENTANA, osc, [(bx + 30, by + 10), (bx - 16, by + 14), (bx - 8, by + 26), (bx + 34, by + 22)])
    for tx in range(-12, 26, 9):
        pygame.draw.polygon(VENTANA, (255, 250, 225), [(bx + tx, by + 9), (bx + tx + 5, by + 9), (bx + tx + 2, by + 17)])
        pygame.draw.polygon(VENTANA, (255, 250, 225), [(bx + tx + 2, by + 16), (bx + tx + 7, by + 16), (bx + tx + 4, by + 10)])
    pygame.draw.polygon(VENTANA, cl, [(bx + 44, by - 14), (bx + 82, by - 40), (bx + 58, by - 8)])
    pygame.draw.polygon(VENTANA, cl, [(bx + 30, by - 16), (bx + 58, by - 38), (bx + 44, by - 10)])
    pygame.draw.polygon(VENTANA, osc, [(bx + 40, by + 2), (bx + 70, by + 10), (bx + 44, by + 14)])
    if grande: brillo(bx + 26, by - 8, 18, (255, 120, 60), 90)
    pygame.draw.circle(VENTANA, (255, 240, 140), (bx + 26, by - 8), 7)
    pygame.draw.ellipse(VENTANA, (30, 12, 10), (bx + 25, by - 14, 4, 12))
    pygame.draw.circle(VENTANA, (255, 255, 255), (bx + 24, by - 11), 2)
    pygame.draw.circle(VENTANA, (40, 20, 18), (bx - 6, by + 2), 2)
    for dx in range(60, 150, 16):
        pygame.draw.polygon(VENTANA, cl, [(bx + dx, by + 56), (bx + dx + 8, by + 32), (bx + dx + 16, by + 58)])
    if jefe_timer < (16 if grande else 12):
        brillo(bx - 18, by + 16, 30 if grande else 24, (255, 150, 40), 120 if grande else 110)
        for i in range(7 if grande else 5):
            pygame.draw.circle(VENTANA, (255, 190 - i * 20, 50), (bx - 18 - i * 10, by + 16 + int(math.sin(frame * .4 + i) * 5)), 8 - i)

def draw_boss():
    if not jefe: return
    bx, by, c = int(jefe['x']), int(jefe['y']), jefe['color']
    osc = tuple(max(0, v - 50) for v in c); cl = tuple(min(255, v + 55) for v in c)
    if jefe['type'] == 'dragon':
        draw_dragon(bx, by, c, osc, cl)
        dibujar_barra_jefe(); return
    sombra_suelo(bx + 40, 348, 140, 12, 90)
    brillo(bx + 90, by + 70, 120, c, 40)
    pygame.draw.polygon(VENTANA, osc, [(bx + 65, by + 78), (bx + 185, by + 48), (bx + 205, by + 72), (bx + 90, by + 105)])
    pygame.draw.ellipse(VENTANA, c, (bx + 40, by + 45, 120, 90))
    pygame.draw.ellipse(VENTANA, cl, (bx + 52, by + 56, 64, 34))
    pygame.draw.polygon(VENTANA, c, [(bx + 70, by + 70), (bx + 62, by + 22), (bx + 78, by - 8), (bx + 118, by + 5), (bx + 132, by + 28), (bx + 118, by + 60)])
    pygame.draw.polygon(VENTANA, c, [(bx + 56, by + 4), (bx + 10, by + 10), (bx - 5, by + 28), (bx + 18, by + 44), (bx + 78, by + 42)])
    pygame.draw.polygon(VENTANA, (78, 16, 26), [(bx + 8, by + 35), (bx + 58, by + 40), (bx + 38, by + 58), (bx + 14, by + 53)])
    for tx in range(16, 58, 12):
        pygame.draw.polygon(VENTANA, (255, 248, 220), [(bx + tx, by + 40), (bx + tx + 5, by + 40), (bx + tx + 2, by + 49)])
    pygame.draw.circle(VENTANA, (255, 238, 130), (bx + 12, by + 18), 8)
    pygame.draw.circle(VENTANA, (20, 10, 10), (bx + 13, by + 18), 4)
    pygame.draw.circle(VENTANA, (255, 255, 255), (bx + 10, by + 15), 2)
    if jefe['type'] == 'titan':
        pygame.draw.polygon(VENTANA, cl, [(bx + 45, by + 8), (bx + 32, by - 28), (bx + 55, by - 10), (bx + 72, by - 35), (bx + 78, by + 12)])
    else:
        pygame.draw.polygon(VENTANA, cl, [(bx + 42, by + 3), (bx + 30, by - 30), (bx + 55, by - 8), (bx + 82, by - 28), (bx + 76, by + 12)])
        pygame.draw.polygon(VENTANA, cl, [(bx + 78, by + 20), (bx + 104, by - 4), (bx + 98, by + 30)])
    for a, b, w in [((78, 72), (30, 88), 9), ((30, 88), (14, 82), 6), ((92, 76), (55, 95), 9), ((55, 95), (40, 91), 6),
                    ((82, 120), (78, 164), 14), ((128, 116), (138, 164), 14), ((62, 164), (82, 164), 7), ((138, 164), (158, 164), 7)]:
        pygame.draw.line(VENTANA, osc, (bx + a[0], by + a[1]), (bx + b[0], by + b[1]), w)
    for dx in range(55, 145, 18):
        pygame.draw.polygon(VENTANA, cl, [(bx + dx, by + 55), (bx + dx + 9, by + 35), (bx + dx + 17, by + 58)])
    dibujar_barra_jefe()

def dibujar_barra_jefe():
    ratio = max(0, min(1, jefe['hp'] / jefe['max']))
    panel(pygame.Rect(226, 14, 348, 24), 130)
    pygame.draw.rect(VENTANA, (60, 12, 18), (232, 20, 336, 12), border_radius=6)
    VENTANA.blit(gradiente(max(1, int(336 * ratio)), 12, (255, 110, 90), (190, 25, 45)), (232, 20))
    pygame.draw.rect(VENTANA, (255, 255, 255), (232, 20, 336, 12), 1, border_radius=6)
    text(('JEFE: ' if nivel < 8 else 'JEFE FINAL: ') + jefe['name'], 40, FUENTE, (255, 120, 130))

def fondo_menu(c1, c2):
    VENTANA.blit(gradiente(ANCHO, ALTO, c1, c2), (0, 0))
    for i in range(45):
        sx = (i * 173 + frame * .6) % 820 - 10; sy = (i * 97 + frame * .25) % 400
        pygame.draw.circle(VENTANA, (255, 255, 255), (int(sx), int(sy)), 1 if i % 3 else 2)

def item_menu(txt, ty, sel, col_sel=(255, 220, 60), ancho=380):
    if sel:
        panel(pygame.Rect(ANCHO // 2 - ancho // 2, ty - 5, ancho, 34), 120, (40, 60, 110))
    text(('> ' if sel else '  ') + txt, ty, FUENTE_G, col_sel if sel else (222, 228, 238))

def draw_menu():
    fondo_menu((10, 18, 40), (34, 16, 56))
    brillo(400, 55, 150, (255, 210, 60), 40)
    text('DINO RUNNER 2.0', 30, FUENTE_XG, (255, 222, 60))
    text('ULTIMATE EVOLUTION', 80, FUENTE_G, (90, 225, 255))
    for i, it in enumerate(['JUGAR', 'SELECCIONAR DINO', 'SELECCIONAR ARMA', 'TIENDA', 'CLASIFICACION', 'GUARDAR / SALIR']):
        item_menu(it, 126 + i * 30, i == menu_sel)
    panel(pygame.Rect(240, 356, 320, 30), 120)
    text(f'MONEDAS {progreso["monedas"]}   MEJOR {progreso["mejor_puntuacion"]}', 362, FUENTE, (255, 216, 60))

def draw_select(title, items, sel, owned=None, prices=None):
    fondo_menu((12, 22, 44), (26, 12, 40))
    text(title, 24, FUENTE_XG, (255, 222, 60))
    current = progreso['dino'] if title == 'DINOSAURIOS' else progreso['arma']
    for i, it in enumerate(items):
        extra = ''
        if owned is not None:
            if it == current and it in owned: extra = ' [ELEGIDO]'
            elif it in owned: extra = ' [OK]'
            else: extra = f' [{prices[it]} C]'
        item_menu(it.upper() + extra, 92 + i * 40, i == sel, ancho=460)
    panel(pygame.Rect(110, 300, 580, 30), 110)
    text('MOVER: ^ v    ELEGIR/COMPRAR: OK    VOLVER: ATRAS', 306, FUENTE, (196, 206, 220))
    text(f'Monedas: {progreso["monedas"]}', 340, FUENTE, (255, 216, 60))

def draw_shop():
    fondo_menu((26, 16, 38), (14, 10, 28))
    text('TIENDA DE MEJORAS', 18, FUENTE_XG, (255, 214, 60))
    for i, (k, n, p, d) in enumerate(MEJORAS):
        lvl = progreso['mejoras'][k]; cost = p * (lvl + 1)
        if i == menu_sel: panel(pygame.Rect(30, 80 + i * 48, 600, 44), 120, (50, 40, 90))
        s = FUENTE_G.render(('> ' if i == menu_sel else '  ') + f'{n}  NIVEL {lvl}/3  {cost}C', True,
                            (255, 220, 60) if i == menu_sel else (234, 238, 246))
        VENTANA.blit(s, (36, 82 + i * 48))
        VENTANA.blit(FUENTE.render(d, True, (172, 192, 214)), (54, 110 + i * 48))
    panel(pygame.Rect(230, 300, 340, 30), 110)
    text(f'MONEDAS {progreso["monedas"]}   OK: COMPRAR', 306, FUENTE, (255, 216, 60))

ETIQUETA_TIPO = {'pelea': 'PELEA', 'resistencia': 'RESIST'}
def draw_scores():
    fondo_menu((8, 18, 32), (16, 10, 34))
    text('TABLA DE CLASIFICACION', 22, FUENTE_XG, (255, 222, 60))
    if not scores: text('AUN NO HAY PUNTAJES', 150, FUENTE_G, (200, 210, 225))
    for i, (n, p, t) in enumerate(scores[:8]):
        col = (255, 216, 60) if i == 0 else (225, 232, 244)
        if n == nombre_jugador and i > 0: col = (130, 235, 160)
        etq = ETIQUETA_TIPO.get(t, '------')
        fila = FUENTE_G.render(f'{i + 1:02d}.  {n[:10]:<10}  {p:06d}  {etq:<6}', True, col)
        sh = FUENTE_G.render(f'{i + 1:02d}.  {n[:10]:<10}  {p:06d}  {etq:<6}', True, (0, 0, 0)); sh.set_alpha(150)
        VENTANA.blit(sh, (ANCHO // 2 - fila.get_width() // 2 + 2, 82 + i * 27))
        VENTANA.blit(fila, (ANCHO // 2 - fila.get_width() // 2, 80 + i * 27))
    text('ATRAS: volver', 320, FUENTE, (190, 198, 212))

def draw_nombre():
    fondo_menu((10, 20, 44), (30, 14, 50))
    text('¿QUIEN VA A JUGAR?', 22, FUENTE_XG, (255, 222, 60))
    text('Escribe tu nombre para la clasificacion', 70, FUENTE, (180, 200, 225))
    caja = pygame.Rect(240, 96, 370, 44)
    panel(caja, 150, (20, 34, 62))
    cursor = '_' if (frame // 20) % 2 == 0 else ' '
    s = FUENTE_XG.render((nombre_jugador + cursor) or cursor, True, (255, 255, 255))
    VENTANA.blit(s, (caja.centerx - s.get_width() // 2, caja.y + 2))
    text('BORRAR: borra una letra    JUGAR: empezar    ATRAS: menu', 340, FUENTE, (176, 192, 214))

def draw_jefe_ok():
    draw_game()
    ov = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); ov.fill((0, 0, 0, 165)); VENTANA.blit(ov, (0, 0))
    brillo(400, 90, 170, (255, 214, 60), 55)
    text('¡GANASTE!', 48, FUENTE_XG, (255, 222, 60))
    text(f'DERROTASTE AL {jefe_vencido}', 116, FUENTE_G, (255, 255, 255))
    text(f'{nombre_jugador or "JUGADOR"}: {puntos} PUNTOS', 162, FUENTE_G, (90, 225, 255))
    text(f'+50 MONEDAS   TOTAL {monedas_partida}', 202, FUENTE_G, (255, 214, 50))
    text('OK: seguir al siguiente nivel', 320, FUENTE, (200, 208, 222))

def draw_game_ui():
    panel(pygame.Rect(8, 6, 214, 74), 120)
    VENTANA.blit(FUENTE.render(f'PUNTOS  {puntos:05d}', True, (255, 255, 255)), (18, 12))
    VENTANA.blit(FUENTE.render(f'MONEDAS {monedas_partida}', True, (255, 214, 50)), (18, 34))
    VENTANA.blit(FUENTE.render('VIDAS', True, (255, 120, 120)), (18, 56))
    for i in range(max(0, vidas)):
        cx = 96 + i * 20
        pygame.draw.circle(VENTANA, (235, 60, 70), (cx, 64), 6)
        pygame.draw.circle(VENTANA, (255, 140, 150), (cx - 2, 62), 2)
    panel(pygame.Rect(300, 6, 200, 52), 120)
    text(f'NIVEL {nivel}', 12, FUENTE, (255, 255, 255))
    text(f'SPEED {velocidad:.1f}', 34, FUENTE, (180, 222, 255))
    if escudo: text('ESCUDO ACTIVO', 62, FUENTE, (110, 225, 255))
    if proteccion_timer > 0: text(f'PROTECCION {proteccion_timer / 60:.1f}s', 86, FUENTE, (110, 225, 255))
    if mensaje_timer > 0:
        s = FUENTE_G.render(mensaje, True, (255, 198, 60))
        panel(pygame.Rect(ANCHO // 2 - s.get_width() // 2 - 14, 112, s.get_width() + 28, 34), 140)
        text(mensaje, 116, FUENTE_G, (255, 198, 60))
    if estado == 'boss':
        text(f'ARMA: {ARMAS[progreso["arma"]]["nombre"]}', 366, FUENTE, (205, 222, 255))

def draw_game():
    draw_bg(nivel)
    for c in monedas: draw_coin(c)
    if corona is not None:
        cx, cy = int(corona['x']), int(corona['y'])
        brillo(cx, cy, 26, (255, 220, 50), 80)
        pygame.draw.polygon(VENTANA, (255, 214, 40), [(cx - 16, cy - 13), (cx - 8, cy + 5), (cx, cy - 6), (cx + 8, cy + 5), (cx + 16, cy - 13), (cx + 12, cy + 11), (cx - 12, cy + 11)])
        pygame.draw.polygon(VENTANA, (255, 248, 180), [(cx - 16, cy - 13), (cx - 8, cy + 5), (cx, cy - 6), (cx + 8, cy + 5), (cx + 16, cy - 13), (cx + 12, cy + 11), (cx - 12, cy + 11)], 2)
        for dx in (-12, 0, 12): pygame.draw.circle(VENTANA, (255, 90, 110), (cx + dx, cy + 6), 2)
    if caja_proteccion is not None:
        bx, by = int(caja_proteccion['x']), int(caja_proteccion['y'])
        brillo(bx, by, 26, (80, 200, 255), 70)
        pygame.draw.rect(VENTANA, (60, 170, 240), (bx - 17, by - 17, 34, 34), border_radius=8)
        pygame.draw.rect(VENTANA, (220, 250, 255), (bx - 12, by - 12, 24, 24), 2, border_radius=6)
        pygame.draw.polygon(VENTANA, (255, 255, 255), [(bx - 7, by - 5), (bx + 7, by - 5), (bx, by + 9)])
    for o in obstaculos: draw_obs(o)
    for e in enemigos: draw_enemy(e)
    for p in proyectiles:
        col = ARMAS[progreso['arma']]['color']
        brillo(int(p['x']), int(p['y']), p['r'] + 8, col, 90)
        pygame.draw.circle(VENTANA, col, (int(p['x']), int(p['y'])), p['r'])
        pygame.draw.circle(VENTANA, (255, 255, 255), (int(p['x']) - 2, int(p['y']) - 2), max(1, p['r'] // 3))
    for p in boss_proyectiles:
        brillo(int(p['x']), int(p['y']), p['r'] + 10, (255, 110, 50), 90)
        pygame.draw.circle(VENTANA, (255, 95, 45), (int(p['x']), int(p['y'])), p['r'])
        pygame.draw.circle(VENTANA, (255, 232, 140), (int(p['x']), int(p['y'])), max(2, p['r'] // 2))
    for p in particulas:
        pygame.draw.circle(VENTANA, p[5], (int(p[0]), int(p[1])), max(1, int(p[4])))
    if estado == 'boss': draw_boss()
    if invuln % 8 < 4: draw_dino(int(x), int(y), DINOS[progreso['dino']]['color'], progreso['dino'], frame)
    draw_game_ui()
    if puerta_timer > 0 and estado == 'puerta':
        ov = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); ov.fill((0, 0, 0, 150)); VENTANA.blit(ov, (0, 0))
        text(f'NIVEL {puerta_nivel}', 55, FUENTE_XG, (255, 222, 60))
        text(NIVELES[puerta_nivel - 1][0], 125, FUENTE_G, (255, 255, 255))
        text(NIVELES[puerta_nivel - 1][1], 172, FUENTE_G, (90, 225, 255))
        text('¡PREPARATE!', 232, FUENTE_G, (255, 132, 60))

def draw_end():
    fondo_menu((8, 14, 32), (28, 12, 44))
    brillo(400, 80, 170, (255, 214, 60), 45)
    es_pelea = tipo_victoria == 'pelea'
    text('¡GANASTE!', 45, FUENTE_XG, (255, 222, 60))
    text('VICTORIA POR PELEA' if es_pelea else 'VICTORIA POR RESISTENCIA', 100, FUENTE, (255, 170, 60) if es_pelea else (110, 225, 255))
    text('DERROTASTE AL DRAGON FINAL' if es_pelea else 'COMPLETASTE LOS 8 NIVELES', 130, FUENTE_G, (255, 255, 255))
    text(f'{nombre_jugador or "JUGADOR"}: {puntos} PUNTOS', 175, FUENTE_G, (90, 225, 255))
    text(f'MONEDAS CONSEGUIDAS: {monedas_partida}', 212, FUENTE_G, (255, 214, 50))
    text('¡PREMIO DESBLOQUEADO!', 252, FUENTE_G, (110, 255, 130))
    text('OK: volver al menu', 320, FUENTE, (196, 204, 218))

def draw_over():
    draw_game()
    ov = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA); ov.fill((0, 0, 0, 160)); VENTANA.blit(ov, (0, 0))
    text('GAME OVER', 70, FUENTE_XG, (255, 72, 72))
    text(gameover_reason, 132, FUENTE_G, (255, 184, 184))
    text(f'PUNTOS {puntos}   MONEDAS {monedas_partida}', 185, FUENTE_G, (255, 222, 70))
    text('OK: menu     ^: reintentar', 250, FUENTE, (224, 230, 240))

# ---------- UPDATE ----------
def update_play():
    global y, vy, saltos, agachado, invuln, velocidad, puntos, monedas_partida, tiempo, nivel, puerta_timer, estado
    global frame, shot_timer, corona, x, caja_proteccion, proteccion_timer, caja_timer, corona_timer, scroll
    if estado == 'boss': update_boss(); return
    if invuln > 0: invuln -= 1
    if proteccion_timer > 0: proteccion_timer -= 1
    if shot_timer > 0: shot_timer -= 1
    tiempo += 1; frame += 1
    agachado = mantenido('abajo')
    if mantenido('izq'): x -= 5.0
    if mantenido('der'): x += 5.0
    x = max(20.0, min(430.0, x))
    vy += .8; y += vy
    if y >= 300: y = 300; vy = 0; saltos = 0
    if estado == 'puerta':
        puerta_timer -= 1
        if puerta_timer <= 0: estado = 'play'
        return
    velocidad = level_speed(); scroll += velocidad
    for o in obstaculos: o['x'] -= velocidad
    if not obstaculos or obstaculos[-1]['x'] < 800 - random.randint(420, 600):
        obstaculos.extend(spawn_group(max(850, obstaculos[-1]['x'] + obstaculos[-1]['w'] + random.randint(150, 280)) if obstaculos else 850))
        puntos += 1
    for o in obstaculos[:]:
        if o['x'] < -80: obstaculos.remove(o); puntos += 8
    for c in monedas: c['x'] -= velocidad
    if not monedas or monedas[-1]['x'] < 500: spawn_coin()
    for c in monedas[:]:
        if c['x'] < -30: monedas.remove(c); continue
        if rect_player().colliderect(pygame.Rect(int(c['x'] - c['r']), int(c['y'] - c['r']), c['r'] * 2, c['r'] * 2)):
            monedas.remove(c); monedas_partida += 1; progreso['monedas'] += 1
            play('moneda'); add_particles(c['x'], c['y'], (255, 220, 30), 8)
    # Corona y caja: aparecen garantizadas desde el nivel 1, arriba y alcanzables.
    caja_timer += 1; corona_timer += 1
    if caja_proteccion is None and caja_timer >= 300 and estado == 'play':
        caja_proteccion = {'x': 850., 'y': 120., 'r': 17}; caja_timer = 0
        set_message('CAJA ARRIBA: SALTA PARA ATRAPARLA', 150)
    if caja_proteccion is not None:
        caja_proteccion['x'] -= max(6.0, velocidad * .76)
        if caja_proteccion['x'] < -45: caja_proteccion = None
        elif rect_player().colliderect(pygame.Rect(int(caja_proteccion['x'] - 20), int(caja_proteccion['y'] - 20), 40, 40)):
            add_particles(caja_proteccion['x'], caja_proteccion['y'], (80, 210, 255), 35); play('power')
            caja_proteccion = None; proteccion_timer = 600; caja_timer = 0
            set_message('PROTECCION TOTAL: 10 SEGUNDOS', 150)
    if corona is None and corona_timer >= 900 and estado == 'play' and not juego_ganado:
        corona = {'x': 850., 'y': 95., 'r': 16, 'activa': True}; corona_timer = 0
        set_message('CORONA ARRIBA: ATRAPALA PARA IR AL JEFE FINAL', 180)
    if corona is not None:
        corona['x'] -= max(6.0, velocidad * .72)
        if corona['x'] < -45: corona = None
        elif rect_player().colliderect(pygame.Rect(int(corona['x'] - 20), int(corona['y'] - 20), 40, 40)):
            add_particles(corona['x'], corona['y'], (255, 220, 40), 35); play('victoria'); corona = None
            puntos += 100; save_progress(); boss_start(final=True); return
    spawn_enemy()
    for e in enemigos[:]:
        e['x'] -= e['vx']; e['phase'] += .1
        if e['tipo'] == 'murcielago': e['y'] += math.sin(e['phase']) * 1.8
        if e['x'] < -80: enemigos.remove(e); puntos += 15; continue
        if rect_player().colliderect(pygame.Rect(int(e['x']), int(e['y']), 45, 35)):
            if proteccion_timer > 0: continue
            hurt('ENEMIGO')
            if e in enemigos: enemigos.remove(e)
            break
    for o in obstaculos[:]:
        r = pygame.Rect(int(o['x']) + 3, int(o['y']) + (25 if o['tipo'] == 'roca' else 7), max(8, o['w'] - 6), 20)
        if rect_player().colliderect(r):
            if proteccion_timer > 0: continue
            hurt('AVION' if o['tipo'] == 'avion' else o['tipo'].upper()); break
    # Las armas solo dañan enemigos y al jefe, nunca cactus, rocas ni agua.
    for p in proyectiles[:]:
        p['x'] += p['vx']; p['y'] += p['vy']
        if p['x'] > 830: proyectiles.remove(p); continue
        pr = pygame.Rect(int(p['x'] - 8), int(p['y'] - 8), 16, 16); hit = False
        for e in enemigos[:]:
            if pr.colliderect(pygame.Rect(int(e['x']), int(e['y']), 45, 35)):
                enemigos.remove(e); puntos += 30; add_particles(p['x'], p['y'], (255, 80, 80), 12); hit = True; break
        if hit and p in proyectiles: proyectiles.remove(p)
    for p in particulas[:]:
        p[0] += p[2]; p[1] += p[3]; p[3] += .15; p[4] -= .12
        if p[4] <= 0: particulas.remove(p)
    # Historia de 8 niveles: completar el nivel 8 sin pelear con el dragon es la victoria POR RESISTENCIA.
    # La pelea con el dragon final solo se desbloquea atrapando la corona (el comodin).
    if puntos >= 120 * nivel and nivel < 8:
        if nivel in (3, 6) and nivel not in jefes_vencidos: boss_start()
        else: next_level()
        return
    if nivel == 8 and puntos >= 960: victoria_resistencia()

def update_boss():
    global jefe, jefe_timer, puntos, estado, juego_ganado, monedas_partida, vidas, invuln, proteccion_timer, tipo_victoria
    global x, y, vy, saltos, agachado, frame, shot_timer, nivel, velocidad, obstaculos, puerta_timer, puerta_nivel, jefe_vencido
    if not jefe: return
    if invuln > 0: invuln -= 1
    if proteccion_timer > 0: proteccion_timer -= 1
    if shot_timer > 0: shot_timer -= 1
    frame += 1
    agachado = mantenido('abajo')
    if mantenido('izq'): x -= 5.5
    if mantenido('der'): x += 5.5
    x = max(30.0, min(520.0, x))
    vy += 0.8; y += vy
    if y >= 300: y = 300; vy = 0; saltos = 0
    if y < 60: y = 60; vy = 0
    jefe_timer += 1; jefe['phase'] += 0.06
    jefe['y'] = 165 + math.sin(jefe['phase']) * 28
    if jefe_timer >= max(13, int(58 - (jefe['max'] - jefe['hp']) * 1.35)):
        jefe_timer = 0
        patrones = [210, 245, 280, 305] + ([185, 225, 265, 315] if jefe['hp'] <= jefe['max'] * 0.55 else [])
        for _ in range(2 if jefe['hp'] <= jefe['max'] * 0.45 else 1):
            yy = random.choice(patrones)
            dx = x - (jefe['x'] - 15); dy = (y + 18) - yy
            mag = max(1.0, math.hypot(dx, dy)); speed = jefe['attack_speed'] * 0.78
            boss_proyectiles.append({'x': jefe['x'] - 12, 'y': yy, 'vx': dx / mag * speed, 'vy': dy / mag * speed, 'r': 9})
        if jefe['hp'] <= jefe['max'] * 0.35 and random.random() < 0.45:
            enemigos.append({'x': jefe['x'] - 15, 'y': random.choice([215, 285]), 'tipo': 'raptor_enemigo',
                             'vx': jefe['attack_speed'] + 2.5, 'phase': 0})
    for e in enemigos[:]:
        e['x'] -= e['vx']; e['phase'] += 0.12
        if e['tipo'] == 'murcielago': e['y'] += math.sin(e['phase']) * 2.0
        if e['x'] < -60: enemigos.remove(e); continue
        if rect_player().colliderect(pygame.Rect(int(e['x']), int(e['y']), 45, 35)):
            if proteccion_timer > 0: continue
            hurt('ATAQUE DEL JEFE')
            if e in enemigos: enemigos.remove(e)
            if estado == 'gameover': return
    for p in boss_proyectiles[:]:
        p['x'] += p['vx']; p['y'] += p['vy']
        if p['x'] < -30 or p['x'] > 830 or p['y'] < 10 or p['y'] > 345:
            boss_proyectiles.remove(p); continue
        if pygame.Rect(int(p['x'] - p['r']), int(p['y'] - p['r']), p['r'] * 2, p['r'] * 2).colliderect(rect_player()):
            boss_proyectiles.remove(p)
            if proteccion_timer > 0:
                set_message('¡LA PROTECCION BLOQUEO EL ATAQUE!', 55)
            else:
                hurt('BOLA DEL JEFE')
                if estado == 'gameover': return
    for p in proyectiles[:]:
        p['x'] += p['vx']; p['y'] += p['vy']
        if p['x'] > 830 or p['y'] < 20 or p['y'] > 350: proyectiles.remove(p); continue
        if pygame.Rect(int(p['x'] - 8), int(p['y'] - 8), 16, 16).colliderect(pygame.Rect(int(jefe['x']), int(jefe['y']), 150, 150)):
            jefe['hp'] -= ARMAS[progreso['arma']]['danio']; puntos += 30
            add_particles(p['x'], p['y'], ARMAS[progreso['arma']]['color'], 16); proyectiles.remove(p)
            if jefe['hp'] <= 0:
                try:
                    puntos += 300; monedas_partida += 50; progreso['monedas'] += 50
                    progreso['niveles_desbloqueados'] = max(progreso['niveles_desbloqueados'], min(8, nivel + 1))
                    progreso['mejor_puntuacion'] = max(progreso['mejor_puntuacion'], puntos)
                    save_progress()
                    if nivel in (3, 6):
                        save_score(puntos)
                        enemigos.clear(); proyectiles.clear(); boss_proyectiles.clear()
                        jefes_vencidos.add(nivel)
                        jefe_vencido = jefe['name']; jefe = None
                        estado = 'jefe_ok'; play('victoria')
                        # log para debug del jefe intermedio
                        try:
                            with open(os.path.join(DATA_DIR, 'crash.log'), 'a', encoding='utf-8') as _lf:
                                _lf.write(f"JEFE {jefe_vencido} vencido nivel {nivel} puntos {puntos}\n")
                        except: pass
                        return
                    # Se derroto al dragon final (llegado mediante el comodin/corona): victoria POR PELEA.
                    tipo_victoria = 'pelea'
                    try: save_score(puntos, tipo_victoria)
                    except Exception as _e:
                        try:
                            with open(os.path.join(DATA_DIR, 'crash.log'), 'a', encoding='utf-8') as _lf:
                                _lf.write(f"save_score fallo {repr(_e)}\n")
                        except: pass
                    estado = 'victory'; jefe = None; juego_ganado = True; boss_proyectiles.clear(); play('victoria')
                    try:
                        with open(os.path.join(DATA_DIR, 'crash.log'), 'a', encoding='utf-8') as _lf:
                            _lf.write(f"VICTORIA PELEA nivel {nivel} puntos {puntos} tipo {tipo_victoria} estado {estado}\n")
                    except: pass
                    return
                except Exception as _e:
                    try:
                        with open(os.path.join(DATA_DIR, 'crash.log'), 'a', encoding='utf-8') as _lf:
                            import traceback; _lf.write("ERROR JEFE FINAL: " + traceback.format_exc() + "\n")
                    except: pass
                    # fallback: forzar victoria para no colgarse
                    try: tipo_victoria = 'pelea'; estado = 'victory'; jefe = None; juego_ganado = True
                    except: pass
                    return

# ---------- ACCIONES (teclado y táctil comparten la misma lógica) ----------
def accion(a):
    global menu_sel, estado, dino_sel, arma_sel, agachado, vy, saltos, nombre_jugador
    global nivel, velocidad, obstaculos, puerta_timer, puerta_nivel
    if estado == 'nombre':
        if a == 'BORRAR': nombre_jugador = nombre_jugador[:-1]
        elif a == 'esc': estado = 'menu'
        elif a in ('JUGAR', 'enter', 'salto'):
            nombre_jugador = (nombre_jugador.strip() or 'JUGADOR')[:10]
            progreso['nombre'] = nombre_jugador; save_progress(); start_game()
        elif len(a) == 1 and len(nombre_jugador) < 10:
            nombre_jugador += a
        return
    if estado == 'jefe_ok':
        if a in ('enter', 'salto', 'esc'):
            estado = 'puerta'; puerta_timer = 100; puerta_nivel = nivel + 1
            nivel += 1; velocidad = level_speed(); obstaculos = spawn_group(850)
        return
    if estado == 'menu':
        if a == 'arriba': menu_sel = (menu_sel - 1) % 6
        elif a == 'abajo': menu_sel = (menu_sel + 1) % 6
        elif a in ('enter', 'salto'):
            if menu_sel == 0: estado = 'nombre'
            elif menu_sel == 1: estado = 'dino'
            elif menu_sel == 2: estado = 'weapon'
            elif menu_sel == 3: menu_sel = 0; estado = 'shop'
            elif menu_sel == 4: estado = 'scores'
            else: save_progress(); pygame.quit(); raise SystemExit
    elif estado in ('dino', 'weapon'):
        items = list(DINOS) if estado == 'dino' else list(ARMAS)
        if a == 'arriba':
            if estado == 'dino': dino_sel = (dino_sel - 1) % len(items)
            else: arma_sel = (arma_sel - 1) % len(items)
        elif a == 'abajo':
            if estado == 'dino': dino_sel = (dino_sel + 1) % len(items)
            else: arma_sel = (arma_sel + 1) % len(items)
        elif a == 'esc': estado = 'menu'; menu_sel = 0
        elif a in ('enter', 'salto'):
            volver = False
            if estado == 'dino':
                key = items[dino_sel]
                if key in progreso['dinos']:
                    progreso['dino'] = key; save_progress(); play('compra')
                    set_message('DINO SELECCIONADO: ' + DINOS[key]['nombre'], 70); volver = True
                else:
                    antes = len(progreso['dinos']); buy_dino(key)
                    if len(progreso['dinos']) > antes:
                        progreso['dino'] = key; dino_sel = items.index(key); save_progress()
                        set_message('¡DINO COMPRADO Y SELECCIONADO!', 90); volver = True
                    else: set_message('NO TIENES SUFICIENTES MONEDAS', 90)
            else:
                key = items[arma_sel]
                if key in progreso['armas']:
                    progreso['arma'] = key; save_progress(); play('compra')
                    set_message('ARMA SELECCIONADA: ' + ARMAS[key]['nombre'], 70); volver = True
                else:
                    antes = len(progreso['armas']); buy_weapon(key)
                    if len(progreso['armas']) > antes:
                        progreso['arma'] = key; arma_sel = items.index(key); save_progress()
                        set_message('¡ARMA COMPRADA Y SELECCIONADA!', 90); volver = True
                    else: set_message('NO TIENES SUFICIENTES MONEDAS', 90)
            if volver: estado = 'menu'; menu_sel = 0
    elif estado == 'shop':
        if a == 'arriba': menu_sel = (menu_sel - 1) % len(MEJORAS)
        elif a == 'abajo': menu_sel = (menu_sel + 1) % len(MEJORAS)
        elif a in ('enter', 'salto'): buy(MEJORAS[menu_sel][0])
        elif a == 'esc': estado = 'menu'; menu_sel = 0
    elif estado == 'scores':
        if a in ('esc', 'enter', 'salto'): estado = 'menu'
    elif estado in ('play', 'boss', 'puerta'):
        if a == 'esc': estado = 'menu'; menu_sel = 0; save_progress()
        elif a in ('salto', 'arriba'):
            if saltos < 2:
                vy = -(DINOS[progreso['dino']]['salto'] + progreso['mejoras']['salto']); saltos += 1; play('salto')
        elif a in ('disparo', 'enter'): shoot()
    elif estado == 'gameover':
        if a in ('salto', 'arriba'): start_game()
        elif a in ('enter', 'esc'): estado = 'menu'; menu_sel = 0; save_progress()
    elif estado == 'victory':
        if a in ('enter', 'salto', 'esc'): estado = 'menu'; menu_sel = 0; save_progress()

TECLAS = {pygame.K_UP: 'arriba', pygame.K_w: 'arriba', pygame.K_DOWN: 'abajo', pygame.K_s: 'abajo',
          pygame.K_LEFT: 'izq', pygame.K_a: 'izq', pygame.K_RIGHT: 'der', pygame.K_d: 'der',
          pygame.K_SPACE: 'salto', pygame.K_RETURN: 'enter', pygame.K_ESCAPE: 'esc', pygame.K_AC_BACK: 'esc'}

# ---------- MAIN (con log anti-cuelgue) ----------
while True:
    try:
        frame += 1
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: save_progress(); pygame.quit(); raise SystemExit
            elif ev.type == pygame.KEYDOWN:
                if estado == 'nombre':
                    if ev.key == pygame.K_BACKSPACE: accion('BORRAR')
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER): accion('JUGAR')
                    elif ev.key in (pygame.K_ESCAPE, pygame.K_AC_BACK): accion('esc')
                    elif ev.unicode and (ev.unicode.isalnum() or ev.unicode == ' '): accion(ev.unicode.upper())
                elif ev.key in TECLAS: accion(TECLAS[ev.key])
            elif ev.type == pygame.FINGERDOWN: dedos[ev.finger_id] = (ev.x * ANCHO, ev.y * ALTO)
            elif ev.type == pygame.FINGERMOTION: dedos[ev.finger_id] = (ev.x * ANCHO, ev.y * ALTO)
            elif ev.type == pygame.FINGERUP: dedos.pop(ev.finger_id, None)
        procesar_toques()
        if estado in ('play', 'boss', 'puerta'): update_play()
        if mensaje_timer > 0: mensaje_timer -= 1
        if estado == 'menu': draw_menu()
        elif estado == 'nombre': draw_nombre()
        elif estado == 'jefe_ok': draw_jefe_ok()
        elif estado == 'dino': draw_select('DINOSAURIOS', list(DINOS), dino_sel, progreso['dinos'], {k: v['precio'] for k, v in DINOS.items()})
        elif estado == 'weapon': draw_select('ARMAS', list(ARMAS), arma_sel, progreso['armas'], {k: v['precio'] for k, v in ARMAS.items()})
        elif estado == 'shop': draw_shop()
        elif estado == 'scores': draw_scores()
        elif estado == 'gameover': draw_over()
        elif estado == 'victory': draw_end()
        else: draw_game()
        dibujar_botones()
        pygame.display.flip(); RELOJ.tick(FPS)
    except Exception as _e:
        try:
            with open(os.path.join(DATA_DIR, 'crash.log'), 'a', encoding='utf-8') as _lf:
                import traceback; _lf.write("CRASH MAIN LOOP: " + traceback.format_exc() + "\n")
        except: pass
        # no cerrar, volver al menu para no colgarse
        try: estado = 'menu'
        except: pass
        pygame.display.flip(); RELOJ.tick(15)