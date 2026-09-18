"""
DINO RUNNER 2.0 - PORT KIVY (ANDROID)
Puerto de pygame a Kivy para APK. Usa frames de img/dino y fondos de img/fondo.
Suelo solo verde + 1 nube + pradera base, como pediste.
"""
import os, sys, random, math, json, tempfile

os.environ['KIVY_LOG_LEVEL'] = 'warning'

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.properties import StringProperty

try:
    from kivy.core.audio import SoundLoader
    HAS_AUDIO = SoundLoader is not None
except:
    SoundLoader = None
    HAS_AUDIO = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANCHO, ALTO = 800, 400
DATA_DIR = os.environ.get('ANDROID_PRIVATE') or BASE_DIR
try:
    open(os.path.join(DATA_DIR, '.w'), 'w').close()
    os.remove(os.path.join(DATA_DIR, '.w'))
except:
    DATA_DIR = tempfile.gettempdir()
SAVE_FILE = os.path.join(DATA_DIR, 'progreso_dino.json')
SCORE_FILE = os.path.join(DATA_DIR, 'top_scores.txt')

def default_save():
    return {'monedas': 0, 'mejor_puntuacion': 0, 'niveles_desbloqueados': 1,
            'dino': 'clasico', 'arma': 'fuego', 'mejoras': {'vida': 0, 'salto': 0, 'velocidad': 0, 'escudo': 0},
            'armas': ['fuego'], 'dinos': ['clasico']}
def load_save():
    try:
        import json
        with open(SAVE_FILE, 'r', encoding='utf-8') as f: d=json.load(f)
        base=default_save(); base.update(d)
        base['mejoras']={**default_save()['mejoras'], **d.get('mejoras',{})}
        return base
    except: return default_save()
def save_progress():
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f: json.dump(progreso, f, indent=2, ensure_ascii=False)
    except: pass
def load_scores():
    try:
        datos=[]
        with open(SCORE_FILE,'r',encoding='utf-8') as f:
            for linea in f.read().splitlines():
                if '|' in linea:
                    p=linea.split('|'); datos.append((p[0][:10],int(p[1]),p[2] if len(p)>2 else ''))
        return sorted(datos, key=lambda d:d[1], reverse=True)[:10]
    except: return []
def save_score(score, tipo=''):
    global scores
    scores = sorted(scores + [(nombre_jugador or 'JUGADOR', score, tipo)], key=lambda d:d[1], reverse=True)[:10]
    try:
        with open(SCORE_FILE,'w',encoding='utf-8') as f:
            f.write('\n'.join(f'{n}|{p}|{t}' for n,p,t in scores))
    except: pass

progreso = load_save(); scores = load_scores()
nombre_jugador = str(progreso.get('nombre',''))[:10]

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

if progreso.get('dino') not in DINOS: progreso['dino']='clasico'
if progreso.get('arma') not in ARMAS: progreso['arma']='fuego'
progreso['dinos']=[k for k in progreso.get('dinos',['clasico']) if k in DINOS] or ['clasico']
progreso['armas']=[k for k in progreso.get('armas',['fuego']) if k in ARMAS] or ['fuego']
save_progress()

# Textures cache
TEX = {}
def _load_tex(path):
    if path in TEX: return TEX[path]
    try:
        tex = CoreImage(path).texture
        TEX[path]=tex
        return tex
    except: return None

def load_textures():
    # dino frames
    for name in ['correr1','correr2','correr3','correr4','salto1','salto2','salto3','agacharse1','agacharse2']:
        p=os.path.join(BASE_DIR,'img','dino', name+'.png')
        if os.path.exists(p): TEX[name]=_load_tex(p)
    # fondos
    for i in range(1,9):
        p=os.path.join(BASE_DIR,'img','fondo',f'fondo{i}.png')
        if os.path.exists(p): TEX[f'fondo{i}']=_load_tex(p)

load_textures()

# Estado del juego
estado='menu'; menu_sel=0
dino_sel=list(DINOS).index(progreso['dino']); arma_sel=list(ARMAS).index(progreso['arma'])
nivel=1; puntos=0; monedas_partida=0; vidas=3; tiempo=0
x=60.; y=300.; vy=0.; saltos=0; agachado=False; invuln=0; escudo=False
velocidad=8.; obstaculos=[]; monedas=[]; enemigos=[]; proyectiles=[]; particulas=[]
jefe=None; jefe_timer=0; juego_ganado=False; gameover_reason=''; tipo_victoria=''
corona=None; caja_proteccion=None; proteccion_timer=0
frame=0; shot_timer=0; scroll=0.; jefes_vencidos=set(); jefe_vencido=''

def level_speed():
    return min(23, [8,10,12,14,16,17,19,21][nivel-1]) * DINOS[progreso['dino']]['vel'] * (1+progreso['mejoras']['velocidad']*.08)

def rect_player():
    # hitbox igual que pygame para colisiones
    return (int(x)+5, int(y)+(25 if agachado else 4), 40 if agachado else 30, 16 if agachado else 45)

def spawn_group(px=None):
    if px is None: px=850
    max_count=1 if nivel<=1 else (2 if nivel<=3 else 3)
    cur,arr=px,[]
    min_gap,max_gap=(95,155) if nivel<=2 else ((80,135) if nivel<=4 else (65,120))
    for _ in range(random.randint(1,max_count)):
        weights=[0.45,0.25,0.20,0.10] if nivel<=2 else [0.40,0.22,0.28,0.10]
        typ=random.choices(['cactus','roca','avion','agua'], weights)[0]
        yy={'cactus':300,'roca':300,'avion':random.choice([190,245,285]),'agua':300}[typ]
        w=random.choice([28,38,48]) if typ!='avion' else 34
        arr.append({'x':cur,'y':yy,'w':w,'tipo':typ})
        cur+=w+random.randint(min_gap,max_gap)
    return arr

def spawn_enemy():
    cap={1:0,2:1,3:1,4:2,5:2,6:3,7:4,8:5}.get(nivel,5)
    if len(enemigos)>=cap: return
    if random.random() > {2:.006,3:.010,4:.015,5:.020,6:.024,7:.028,8:.032}.get(nivel,.005): return
    tipos=['murcielago','raptor_enemigo','robot']
    enemigos.append({'x':850+random.randint(0,120),'y':random.choice([215,255,295]),
                     'tipo':random.choice(tipos),'vx':velocidad*(0.58+nivel*0.012)+random.uniform(0.5,2.0),'phase':random.random()*6})

class DinoWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.core_app=None
        Clock.schedule_interval(self.update, 1/60.)

    def set_app(self, app):
        self.core_app=app

    def on_touch_down(self, touch):
        # controles tactiles simples: izquierda salta, derecha dispara, abajo agacha
        if touch.x < self.width*0.3 and touch.y < self.height*0.5:
            self.do_jump()
        elif touch.x > self.width*0.7:
            self.do_shoot()
        elif touch.y < self.height*0.3:
            global agachado; agachado=True
        return super().on_touch_down(touch)
    def on_touch_up(self, touch):
        global agachado
        agachado=False
        return super().on_touch_up(touch)

    def do_jump(self):
        global vy, saltos
        if saltos < 2:
            vy = -(DINOS[progreso['dino']]['salto'] + progreso['mejoras']['salto'])
            saltos+=1
    def do_shoot(self):
        global shot_timer
        if shot_timer>0: return
        a=ARMAS[progreso['arma']]
        base_y=y+18
        for i in range(a['cantidad']):
            off=(i-(a['cantidad']-1)/2)*4
            proyectiles.append({'x':x+45,'y':base_y,'vx':a['vel'],'vy':off,'d':a['danio'],'r':7})
        shot_timer=a['cooldown']

    def update(self, dt):
        global frame, shot_timer, scroll, velocidad, puntos, monedas_partida, invuln, proteccion_timer, vy, y, saltos, nivel, estado, jefe, jefe_timer, juego_ganado, tipo_victoria, x
        if estado not in ('play','boss','puerta'): 
            self.draw()
            return
        # update igual que pygame
        frame+=1
        if invuln>0: invuln-=1
        if proteccion_timer>0: proteccion_timer-=1
        if shot_timer>0: shot_timer-=1
        # movimiento jugador (teclado)
        keys = Window.request_keyboard(None, self)
        # simplificado: usa Window.keyboard
        # gravedad
        vy+=0.8; y+=vy
        if y>=300: y=300; vy=0; saltos=0
        if estado=='puerta':
            # puerta timer
            global puerta_timer
            puerta_timer-=1
            if puerta_timer<=0: estado='play'
            self.draw(); return
        velocidad=level_speed(); scroll+=velocidad
        for o in obstaculos: o['x']-=velocidad
        if not obstaculos or obstaculos[-1]['x'] < 800 - random.randint(420,600):
            obstaculos.extend(spawn_group(max(850, obstaculos[-1]['x']+obstaculos[-1]['w']+random.randint(150,280)) if obstaculos else 850))
            puntos+=1
        for o in obstaculos[:]:
            if o['x'] < -80: obstaculos.remove(o); puntos+=8
        for c in monedas: c['x']-=velocidad
        if not monedas or monedas[-1]['x']<500:
            if random.random()<0.55: monedas.append({'x':850,'y':random.choice([190,240,285]),'r':8})
        for c in monedas[:]:
            if c['x']<-30: monedas.remove(c); continue
            rx,ry,rw,rh=rect_player()
            if rx < c['x']+c['r'] and rx+rw > c['x']-c['r'] and ry < c['y']+c['r'] and ry+rh > c['y']-c['r']:
                monedas.remove(c); monedas_partida+=1; progreso['monedas']+=1; save_progress()
        spawn_enemy()
        for e in enemigos[:]:
            e['x']-=e['vx']; e['phase']+=0.1
            if e['tipo']=='murcielago': e['y']+=math.sin(e['phase'])*1.8
            if e['x']<-80: enemigos.remove(e); puntos+=15; continue
            rx,ry,rw,rh=rect_player()
            if rx < e['x']+45 and rx+rw > e['x'] and ry < e['y']+35 and ry+rh > e['y']:
                if proteccion_timer<=0:
                    # hurt
                    global vidas, escudo, gameover_reason
                    if escudo: escudo=False
                    else:
                        vidas-=1; invuln=100
                        if vidas<=0:
                            gameover_reason='ENEMIGO'; estado='gameover'; save_score(puntos)
                            progreso['mejor_puntuacion']=max(progreso['mejor_puntuacion'], puntos); save_progress()
                    if e in enemigos: enemigos.remove(e)
                break
        # obstaculos colision
        for o in obstaculos[:]:
            r = (int(o['x'])+3, int(o['y'])+(25 if o['tipo']=='roca' else 7), max(8,o['w']-6), 20)
            rx,ry,rw,rh=rect_player()
            if rx < r[0]+r[2] and rx+rw > r[0] and ry < r[1]+r[3] and ry+rh > r[1]:
                if proteccion_timer<=0:
                    if escudo: escudo=False
                    else:
                        vidas-=1; invuln=100
                        if vidas<=0:
                            gameover_reason='OBSTACULO'; estado='gameover'; save_score(puntos)
                            progreso['mejor_puntuacion']=max(progreso['mejor_puntuacion'], puntos); save_progress()
                        else:
                            x=60.; y=300.; vy=0.
                    break
        # proyectiles
        for p in proyectiles[:]:
            p['x']+=p['vx']; p['y']+=p['vy']
            if p['x']>830: proyectiles.remove(p); continue
            pr=(int(p['x']-8),int(p['y']-8),16,16)
            hit=False
            for e in enemigos[:]:
                if pr[0] < e['x']+45 and pr[0]+pr[2] > e['x'] and pr[1] < e['y']+35 and pr[1]+pr[3] > e['y']:
                    enemigos.remove(e); puntos+=30; hit=True; break
            if hit and p in proyectiles: proyectiles.remove(p)
            # jefe
            if jefe and pr[0] < jefe['x']+150 and pr[0]+pr[2] > jefe['x'] and pr[1] < jefe['y']+150 and pr[1]+pr[3] > jefe['y']:
                jefe['hp']-=ARMAS[progreso['arma']]['danio']; puntos+=30
                if p in proyectiles: proyectiles.remove(p)
                if jefe['hp']<=0:
                    puntos+=300; monedas_partida+=50; progreso['monedas']+=50
                    progreso['mejor_puntuacion']=max(progreso['mejor_puntuacion'], puntos); save_progress()
                    if nivel in (3,6):
                        jefes_vencidos.add(nivel); jefe_vencido=jefe['name']; jefe=None; estado='jefe_ok'
                    else:
                        tipo_victoria='pelea'; save_score(puntos, tipo_victoria); estado='victory'; juego_ganado=True; jefe=None
                    break
        # jefe update simplificado
        if jefe:
            jefe_timer+=1; jefe['phase']=jefe.get('phase',0)+0.06; jefe['y']=165+math.sin(jefe['phase'])*28
        # victoria resistencia
        if puntos >= 120*nivel and nivel < 8:
            if nivel in (3,6) and nivel not in jefes_vencidos:
                # boss
                bosses={3:('DRAGON','dragon',(190,40,50),12),6:('TITAN','titan',(100,70,170),18)}
                name,tipo,color,hp=bosses.get(nivel, bosses[6])
                jefe = {'x':620.,'y':180.,'hp':hp,'max':hp,'type':tipo,'name':name,'color':color,'phase':0.0,'final':False}
                estado='boss'; jefes_vencidos.add(nivel)
            else:
                nivel+=1; velocidad=level_speed()
        if nivel==8 and puntos>=960 and estado!='victory':
            puntos+=200; monedas_partida+=30; progreso['monedas']+=30
            progreso['mejor_puntuacion']=max(progreso['mejor_puntuacion'], puntos)
            tipo_victoria='resistencia'; save_score(puntos, tipo_victoria); save_progress()
            estado='victory'; juego_ganado=True
        self.draw()

    def draw(self):
        self.canvas.clear()
        # fondo
        with self.canvas:
            # pradera base + cielo + nube + suelo verde (nivel 1)
            tex = TEX.get(f'fondo{nivel}')
            if tex:
                Color(1,1,1,1)
                Rectangle(texture=tex, pos=self.pos, size=self.size)
            else:
                Color(0.47,0.78,0.96)
                Rectangle(pos=self.pos, size=self.size)
            if nivel==1:
                # cielo ya en textura, solo nube y suelo verde solido
                Color(1,1,1,1)
                cx = (scroll*0.12) % 900 - 120
                # nube
                Color(1,1,1,1)
                Ellipse(pos=(self.x+cx, self.y+self.height-80), size=(110,38))
                Ellipse(pos=(self.x+cx+22, self.y+self.height-65), size=(88,34))
                # suelo verde solido
                Color(0.18,0.62,0.27)
                Rectangle(pos=(self.x, self.y), size=(self.width, 50))
        # obstaculos
        with self.canvas:
            for o in obstaculos:
                # convertir x del mundo a pantalla: o['x'] - scroll? En pygame o['x'] ya es pantalla con scroll, aqui igual
                # mapeamos 850 -> width
                sx = self.x + o['x'] * (self.width/850*0.9)
                # simplificado: dibujar rect
                if o['tipo']=='cactus':
                    Color(0.15,0.52,0.23)
                    Rectangle(pos=(sx, self.y+50), size=(o['w']*0.6, 45))
                elif o['tipo']=='roca':
                    Color(0.35,0.35,0.38)
                    Rectangle(pos=(sx, self.y+50), size=(o['w']*0.7, 30))
                elif o['tipo']=='agua':
                    Color(0.09,0.36,0.69)
                    Rectangle(pos=(sx, self.y+50), size=(o['w']*0.7, 14))
                else: # avion
                    Color(0.91,0.93,0.97)
                    Rectangle(pos=(sx, self.y+120), size=(34,14))
        # monedas
        with self.canvas:
            for c in monedas:
                sx = self.x + c['x'] * (self.width/850*0.9)
                Color(1,0.8,0.16)
                Ellipse(pos=(sx, self.y+ c['y']*0.3), size=(16,16))
        # enemigos
        with self.canvas:
            for e in enemigos:
                sx = self.x + e['x'] * (self.width/850*0.9)
                Color(0.73,0.24,0.28) if e['tipo']=='raptor_enemigo' else Color(0.36,0.27,0.5) if e['tipo']=='murcielago' else Color(0.52,0.6,0.66)
                Rectangle(pos=(sx, self.y+ e['y']*0.3), size=(45,35))
        # proyectiles
        with self.canvas:
            for p in proyectiles:
                sx = self.x + p['x'] * (self.width/850*0.9)
                col = ARMAS[progreso['arma']]['color']
                Color(col[0]/255, col[1]/255, col[2]/255)
                Ellipse(pos=(sx, self.y+ p['y']*0.3), size=(14,14))
        # dino
        with self.canvas:
            if invuln%8<4:
                # elegir frame
                if agachado:
                    tex = TEX.get('agacharse1')
                    if TEX.get('agacharse2') and frame%16<8: tex=TEX.get('agacharse2')
                elif y<300 or vy!=0:
                    # salto
                    if vy < -4: tex=TEX.get('salto1')
                    elif vy > 4: tex=TEX.get('salto3')
                    else: tex=TEX.get('salto2')
                else:
                    # correr 4 frames
                    idx = (frame//5) % 4
                    tex=TEX.get(f'correr{idx+1}')
                if tex:
                    Color(1,1,1,1)
                    # dino pos: x=60 -> mapear
                    dx = self.x + 60 * (self.width/800)
                    dy = self.y + (y-260)*0.3 + 50  # ajustar
                    if agachado:
                        Rectangle(texture=tex, pos=(dx, dy-10), size=(55,38))
                    else:
                        Rectangle(texture=tex, pos=(dx, dy), size=(60,58))
                else:
                    Color(0.27,0.74,0.27)
                    Rectangle(pos=(self.x+60, self.y+80), size=(30,45))
        # UI
        with self.canvas:
            Color(0,0,0,0.5)
            Rectangle(pos=(self.x+5, self.y+self.height-30), size=(200,25))
            Color(1,1,1,1)
        # labels via Label widget no canvas, usamos CoreLabel? simplificado: no texto en canvas, usa Label overlay
        # jefe
        if jefe:
            with self.canvas:
                Color(jefe['color'][0]/255, jefe['color'][1]/255, jefe['color'][2]/255)
                Rectangle(pos=(self.x+self.width-180, self.y+self.height-80), size=(150,50))

class DinoApp(App):
    def build(self):
        Window.clearcolor = (0.1,0.14,0.2,1)
        root = FloatLayout()
        self.game = DinoWidget(size_hint=(1,1), pos_hint={'x':0,'y':0})
        self.game.set_app(self)
        root.add_widget(self.game)
        # UI overlay
        self.lbl = Label(text='DINO RUNNER KIVY', size_hint=(1,None), height=30, pos_hint={'top':1}, color=(1,1,1,1))
        root.add_widget(self.lbl)
        # botones
        btn_jugar = Button(text='JUGAR', size_hint=(0.3,0.12), pos_hint={'center_x':0.5,'y':0.4})
        btn_jugar.bind(on_press=lambda x: self.start_game())
        self.btn_jugar=btn_jugar
        root.add_widget(btn_jugar)
        Clock.schedule_interval(self.update_ui, 0.1)
        return root

    def start_game(self):
        global estado, nivel, puntos, monedas_partida, vidas, x,y,vy, obstaculos, monedas, enemigos, proyectiles, nivel, scroll, juego_ganado
        nivel=1; puntos=0; monedas_partida=0; vidas=3; x=60.; y=300.; vy=0.
        obstaculos.clear(); monedas.clear(); enemigos.clear(); proyectiles.clear()
        for o in spawn_group(850): obstaculos.append(o)
        estado='play'
        self.btn_jugar.opacity=0; self.btn_jugar.disabled=True
        Window.bind(on_key_down=self.on_key)

    def on_key(self, win, key, scancode, codepoint, mod):
        if key==32: # espacio salto
            self.game.do_jump()
        elif key==13: # enter disparo
            self.game.do_shoot()

    def update_ui(self, dt):
        if estado=='play' or estado=='boss':
            self.lbl.text=f'PUNTOS {puntos:05d}  NIVEL {nivel}  VIDAS {vidas}'
        elif estado=='gameover':
            self.lbl.text=f'GAME OVER {gameover_reason} - PUNTOS {puntos}'
            self.btn_jugar.text='REINTENTAR'; self.btn_jugar.opacity=1; self.btn_jugar.disabled=False
        elif estado=='victory':
            self.lbl.text=f'¡VICTORIA! {tipo_victoria} PUNTOS {puntos}'
            self.btn_jugar.text='MENU'; self.btn_jugar.opacity=1; self.btn_jugar.disabled=False
            # al ganar vuelve a menu
        elif estado=='jefe_ok':
            self.lbl.text=f'¡JEFE {jefe_vencido} VENCIDO!'
        else:
            self.lbl.text='DINO RUNNER 2.0 KIVY - TOCA JUGAR'

if __name__=='__main__':
    DinoApp().run()
