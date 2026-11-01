
import pygame
import random
import math
import json
import os
import sys

# ==========================================================
# PINK POWER SURVIVOR 2.0
# Python 3.14 + pygame-ce
#
# WASD          Move
# Mouse         Aim
# Left Click    Shoot
# 1,2,3,4       Change weapon
# R             Reload
# SPACE         Energy blast
# SHIFT         Dash
# H             Heal
# Q             Shield
# M             Mini-map
# B             Shop
# ESC           Pause
# ==========================================================

pygame.init()
pygame.mixer.quit()

WIDTH, HEIGHT = 1200, 750
FPS = 60
WORLD_W, WORLD_H = 2600, 1900

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pink Power Survivor 2.0")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 21, bold=True)
SMALL = pygame.font.SysFont("arial", 15)
BIG = pygame.font.SysFont("arial", 52, bold=True)

PINK = (255, 70, 175)
LIGHT_PINK = (255, 175, 220)
DARK_PINK = (135, 25, 90)
WHITE = (255, 255, 255)
BLACK = (10, 10, 15)
RED = (220, 40, 45)
GREEN = (70, 220, 120)
GOLD = (255, 210, 65)
BLUE = (90, 180, 255)

SAVE_FILE = "pink_power_save.json"

# ---------------- SAVE ----------------

def load_save():
    try:
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return {
            "high_score": 0,
            "coins": 0,
            "level": 1,
            "damage": 0,
            "max_health": 100
        }

save = load_save()

def save_game():
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(save, f, indent=4)
    except OSError:
        pass

def text(surface, value, x, y, color=WHITE, font=FONT):
    image = font.render(str(value), True, color)
    surface.blit(image, (x, y))

def clamp(v, low, high):
    return max(low, min(high, v))

def dist(x1, y1, x2, y2):
    return math.hypot(x2-x1, y2-y1)

def bar(surface, x, y, w, h, value, maximum, color):
    pygame.draw.rect(surface, (50, 40, 50), (x,y,w,h), border_radius=5)
    fill = int(w * clamp(value / max(1, maximum), 0, 1))
    pygame.draw.rect(surface, color, (x,y,fill,h), border_radius=5)
    pygame.draw.rect(surface, WHITE, (x,y,w,h), 1, border_radius=5)

def world_screen(x, y, camera):
    return int(x-camera[0]), int(y-camera[1])

# ---------------- PARTICLES ----------------

class Particle:
    def __init__(self, x, y, color, power=5):
        self.x, self.y = x, y
        angle = random.random()*math.tau
        speed = random.uniform(1, power)
        self.vx = math.cos(angle)*speed
        self.vy = math.sin(angle)*speed
        self.color = color
        self.life = random.randint(15, 35)
        self.radius = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, camera):
        if self.life > 0:
            x,y = world_screen(self.x,self.y,camera)
            pygame.draw.circle(screen,self.color,(x,y),max(1,self.radius))

# ---------------- BULLETS ----------------

class Bullet:
    def __init__(self,x,y,target,damage,color,speed=13,radius=5):
        self.x,self.y=x,y
        self.damage=damage
        self.color=color
        self.radius=radius
        self.life=85

        dx=target[0]-x
        dy=target[1]-y
        length=math.hypot(dx,dy) or 1

        self.vx=dx/length*speed
        self.vy=dy/length*speed

    def update(self):
        self.x+=self.vx
        self.y+=self.vy
        self.life-=1

    def draw(self,camera):
        x,y=world_screen(self.x,self.y,camera)
        pygame.draw.circle(screen,self.color,(x,y),self.radius)
        pygame.draw.circle(screen,WHITE,(x,y),max(1,self.radius//2))

# ---------------- PLAYER ----------------

class Player:
    def __init__(self):
        self.x=WORLD_W//2
        self.y=WORLD_H//2

        self.level=max(1,int(save.get("level",1)))
        self.xp=0
        self.xp_needed=100

        self.max_health=max(100,int(save.get("max_health",100)))
        self.health=float(self.max_health)
        self.energy=100
        self.max_energy=100

        self.speed=4.1
        self.angle=0
        self.anim=0

        self.damage_bonus=max(0,int(save.get("damage",0)))
        self.coins=max(0,int(save.get("coins",0)))
        self.score=0
        self.kills=0

        self.weapon=1
        self.weapons={
            1: {"name":"PISTOL","damage":25,"ammo":15,"max":15,"rate":330},
            2: {"name":"SHOTGUN","damage":18,"ammo":8,"max":8,"rate":700},
            3: {"name":"RIFLE","damage":13,"ammo":45,"max":45,"rate":100},
            4: {"name":"LASER","damage":38,"ammo":10,"max":10,"rate":450}
        }

        self.reload=0
        self.dash_cd=0
        self.blast_cd=0
        self.heal_cd=0
        self.shield_cd=0
        self.shield=0
        self.invincible=0

        self.regeneration=False

    def update(self,keys):
        dx=0
        dy=0

        if keys[pygame.K_w] or keys[pygame.K_UP]: dy-=1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy+=1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx-=1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx+=1

        if dx or dy:
            length=math.hypot(dx,dy)
            self.x+=dx/length*self.speed
            self.y+=dy/length*self.speed
            self.anim+=0.22

        self.x=clamp(self.x,35,WORLD_W-35)
        self.y=clamp(self.y,35,WORLD_H-35)

        for name in ("dash_cd","blast_cd","heal_cd","shield_cd","invincible","shield"):
            setattr(self,name,max(0,getattr(self,name)-1))

        self.energy=min(100,self.energy+0.045)

        if self.regeneration:
            self.health=min(self.max_health,self.health+0.025)

        if self.reload>0:
            self.reload-=1
            if self.reload==0:
                weapon=self.weapons[self.weapon]
                weapon["ammo"]=weapon["max"]

    def shoot(self,target,bullets):
        weapon=self.weapons[self.weapon]

        if self.reload>0 or weapon["ammo"]<=0:
            return

        weapon["ammo"]-=1
        damage=weapon["damage"]+self.damage_bonus

        if self.weapon==2:
            for spread in (-0.24,-0.12,0,0.12,0.24):
                angle=math.atan2(target[1]-self.y,target[0]-self.x)+spread
                point=(self.x+math.cos(angle)*500,
                       self.y+math.sin(angle)*500)
                bullets.append(Bullet(self.x,self.y,point,damage,GOLD,11,5))
        else:
            color=BLUE if self.weapon==4 else LIGHT_PINK
            speed=18 if self.weapon==4 else 13
            bullets.append(Bullet(self.x,self.y,target,damage,color,speed,5))

    def dash(self,keys,particles):
        if self.dash_cd or self.energy<20:
            return

        dx=int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy=int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP])
        length=math.hypot(dx,dy)

        if length==0:
            return

        self.x=clamp(self.x+dx/length*150,35,WORLD_W-35)
        self.y=clamp(self.y+dy/length*150,35,WORLD_H-35)

        self.energy-=20
        self.invincible=35
        self.dash_cd=110

        for _ in range(25):
            particles.append(Particle(self.x,self.y,PINK,8))

    def blast(self,zombies,particles):
        if self.energy<40 or self.blast_cd:
            return

        self.energy-=40
        self.blast_cd=180

        for z in zombies:
            if dist(self.x,self.y,z.x,z.y)<300:
                z.health-=110+self.damage_bonus*2
                z.stun=40

        for _ in range(100):
            particles.append(Particle(self.x,self.y,LIGHT_PINK,12))

    def heal(self):
        if self.energy>=30 and self.heal_cd==0:
            self.energy-=30
            self.health=min(self.max_health,self.health+40)
            self.heal_cd=240

    def activate_shield(self):
        if self.energy>=25 and self.shield_cd==0:
            self.energy-=25
            self.shield=180
            self.shield_cd=360

    def gain_xp(self,amount):
        self.xp+=amount
        while self.xp>=self.xp_needed:
            self.xp-=self.xp_needed
            self.level+=1
            self.xp_needed=int(self.xp_needed*1.35)
            self.max_health+=10
            self.health=min(self.max_health,self.health+30)
            self.max_energy=100
            self.energy=100

    def draw(self,camera,mouse_world):
        sx,sy=world_screen(self.x,self.y,camera)
        self.angle=math.atan2(mouse_world[1]-self.y,mouse_world[0]-self.x)

        # Aura and shield
        pygame.draw.circle(screen,(120,35,100),(sx,sy),34,2)

        if self.shield:
            pygame.draw.circle(screen,BLUE,(sx,sy),42,3)

        if self.invincible and self.invincible%6<3:
            pygame.draw.circle(screen,WHITE,(sx,sy),39,3)

        # Hair
        pygame.draw.ellipse(screen,(80,25,50),(sx-18,sy-30,36,50))

        # Cape
        pygame.draw.polygon(screen,(210,40,135),
            [(sx-12,sy-12),(sx-31,sy+17),(sx-14,sy+10),(sx+10,sy-12)])

        # Legs
        walk=int(math.sin(self.anim)*4)
        pygame.draw.line(screen,LIGHT_PINK,(sx-6,sy+10),(sx-10+walk,sy+30),8)
        pygame.draw.line(screen,LIGHT_PINK,(sx+6,sy+10),(sx+10-walk,sy+30),8)

        pygame.draw.ellipse(screen,DARK_PINK,(sx-18,sy+24,15,8))
        pygame.draw.ellipse(screen,DARK_PINK,(sx+3,sy+24,15,8))

        # Suit and face
        pygame.draw.ellipse(screen,PINK,(sx-17,sy-19,34,38))
        pygame.draw.circle(screen,(255,210,185),(sx,sy-25),11)

        pygame.draw.circle(screen,BLACK,(sx-4,sy-26),2)
        pygame.draw.circle(screen,BLACK,(sx+4,sy-26),2)

        # Arm aimed at mouse
        ax=sx+math.cos(self.angle)*24
        ay=sy+math.sin(self.angle)*24
        pygame.draw.line(screen,LIGHT_PINK,(sx,sy-5),(ax,ay),8)
        pygame.draw.circle(screen,WHITE,(int(ax),int(ay)),4)

# ---------------- ZOMBIES ----------------

class Zombie:
    def __init__(self,x,y,wave,kind=None):
        self.x,self.y=x,y
        self.stun=0
        self.anim=random.random()*10
        self.attack_cd=0

        if kind is None:
            kind=random.choices(
                ["normal","fast","tank","exploder","poison"],
                weights=[45,20,15,10,10])[0]

        self.kind=kind
        self.boss=False

        settings={
            "normal":(28,95+wave*8,1.3+wave*.025,13,(105,125,75)),
            "fast":(21,55+wave*6,2.4+wave*.035,9,(145,125,75)),
            "tank":(40,220+wave*16,.8+wave*.015,22,(80,95,65)),
            "exploder":(29,85+wave*7,1.45+wave*.02,28,(170,80,65)),
            "poison":(31,115+wave*9,1.1+wave*.02,15,(90,135,85)),
            "boss":(65,1100+wave*120,.9+wave*.02,28,(80,95,60))
        }

        self.radius,self.max_health,self.speed,self.damage,self.color=settings[kind]
        self.health=self.max_health

    def update(self,player,particles):
        if self.stun:
            self.stun-=1
            return

        dx=player.x-self.x
        dy=player.y-self.y
        length=math.hypot(dx,dy) or 1

        # Boss periodically charges
        speed=self.speed
        if self.boss and self.attack_cd==0:
            speed*=3
            self.attack_cd=130

        self.x+=dx/length*speed
        self.y+=dy/length*speed

        self.attack_cd=max(0,self.attack_cd-1)
        self.anim+=.15

    def draw(self,camera):
        sx,sy=world_screen(self.x,self.y,camera)
        r=self.radius

        pygame.draw.ellipse(screen,(15,15,15),(sx-r,sy+r//2,r*2,r//2))
        pygame.draw.ellipse(screen,self.color,(sx-r,sy-r,r*2,r*2))

        # Huge ugly head
        pygame.draw.circle(screen,(125,135,85),(sx,sy-r//2),int(r*.78))

        # Torn clothes
        pygame.draw.polygon(screen,(65,50,55),
            [(sx-r,sy),(sx-4,sy+r),(sx+r,sy+r//2),(sx+5,sy-5)])

        # Glowing eyes
        ey=sy-r//2
        pygame.draw.circle(screen,RED,(sx-r//3,ey),max(4,r//7))
        pygame.draw.circle(screen,RED,(sx+r//3,ey),max(4,r//7))

        pygame.draw.line(screen,BLACK,(sx-r//3,sy+3),(sx+r//3,sy+3),5)

        if self.kind=="exploder":
            pygame.draw.circle(screen,(255,130,30),(sx,sy),r+7,2)

        if self.kind=="poison":
            pygame.draw.circle(screen,(80,255,80),(sx,sy),r+5,2)

        bar(screen,sx-r,sy-r-12,r*2,7,self.health,self.max_health,RED)

        if self.boss:
            text(screen,"BOSS",sx-28,sy-r-35,GOLD,SMALL)

# ---------------- PICKUPS ----------------

class Pickup:
    def __init__(self,x,y,kind):
        self.x,self.y=x,y
        self.kind=kind
        self.life=900

    def draw(self,camera):
        sx,sy=world_screen(self.x,self.y,camera)

        colors={
            "health":GREEN,
            "energy":PINK,
            "ammo":GOLD,
            "coin":GOLD
        }

        symbols={
            "health":"+",
            "energy":"E",
            "ammo":"A",
            "coin":"$"
        }

        pygame.draw.circle(screen,colors[self.kind],(sx,sy),14)
        pygame.draw.circle(screen,WHITE,(sx,sy),14,2)
        text(screen,symbols[self.kind],sx-6,sy-10,BLACK,SMALL)

# ---------------- WORLD ----------------

def draw_world(camera,world_time):
    night=(math.sin(world_time*.0005)+1)/2
    shade=int(35+night*18)
    screen.fill((shade,shade+5,shade+8))

    grid=100
    sx=int(camera[0]//grid)*grid
    sy=int(camera[1]//grid)*grid

    for x in range(sx,int(camera[0]+WIDTH)+grid,grid):
        xx=int(x-camera[0])
        pygame.draw.line(screen,(48,50,53),(xx,0),(xx,HEIGHT))

    for y in range(sy,int(camera[1]+HEIGHT)+grid,grid):
        yy=int(y-camera[1])
        pygame.draw.line(screen,(48,50,53),(0,yy),(WIDTH,yy))

    # Ruined buildings
    for bx in range(0,WORLD_W,450):
        for by in range(0,WORLD_H,450):
            if (bx//450+by//450)%2==0:
                x,y=world_screen(bx+50,by+50,camera)
                if -220<x<WIDTH+100 and -180<y<HEIGHT+100:
                    pygame.draw.rect(screen,(35,38,43),(x,y,175,140))
                    pygame.draw.rect(screen,(75,75,80),(x,y,175,140),3)

                    for wx in range(3):
                        for wy in range(2):
                            pygame.draw.rect(screen,(100,80,60),
                                (x+20+wx*50,y+20+wy*50,25,22))

    # Night tint
    overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    overlay.fill((10,10,35,int(night*45)))
    screen.blit(overlay,(0,0))

# ---------------- MINIMAP ----------------

def draw_minimap(player,zombies):
    w,h=180,130
    x=WIDTH-w-20
    y=HEIGHT-h-20

    pygame.draw.rect(screen,(15,15,25),(x,y,w,h))
    pygame.draw.rect(screen,LIGHT_PINK,(x,y,w,h),2)

    px=x+player.x/WORLD_W*w
    py=y+player.y/WORLD_H*h
    pygame.draw.circle(screen,PINK,(int(px),int(py)),5)

    for z in zombies:
        zx=x+z.x/WORLD_W*w
        zy=y+z.y/WORLD_H*h
        color=GOLD if z.boss else RED
        pygame.draw.circle(screen,color,(int(zx),int(zy)),4)

# ---------------- HUD ----------------

def draw_hud(player,wave,zombies):
    text(screen,"PINK POWER SURVIVOR 2.0",20,12,LIGHT_PINK)
    text(screen,f"LEVEL {player.level}",20,45,GOLD)

    text(screen,"HEALTH",20,82,WHITE,SMALL)
    bar(screen,100,82,190,18,player.health,player.max_health,GREEN)

    text(screen,"ENERGY",20,108,WHITE,SMALL)
    bar(screen,100,108,190,18,player.energy,100,PINK)

    text(screen,"XP",20,134,WHITE,SMALL)
    bar(screen,100,134,190,15,player.xp,player.xp_needed,BLUE)

    text(screen,f"Wave: {wave}",20,170,GOLD)
    text(screen,f"Score: {player.score}",20,198)
    text(screen,f"Kills: {player.kills}",20,226)
    text(screen,f"Coins: {player.coins}",20,254,GOLD)

    weapon=player.weapons[player.weapon]
    text(screen,f"Weapon: {weapon['name']}",WIDTH-270,15,LIGHT_PINK)
    text(screen,f"Ammo: {weapon['ammo']} / {weapon['max']}",WIDTH-270,45)
    text(screen,f"Zombies: {len(zombies)}",WIDTH-270,75,RED)

    text(screen,"WASD Move | Mouse Aim | Click Shoot",WIDTH//2-180,HEIGHT-40,WHITE,SMALL)
    text(screen,"SPACE Blast | SHIFT Dash | H Heal | Q Shield | B Shop",
         WIDTH//2-240,HEIGHT-20,LIGHT_PINK,SMALL)

# ---------------- SHOP ----------------

SHOP_ITEMS=[
    ("Damage Upgrade",50,"damage"),
    ("Max Health Upgrade",60,"health"),
    ("Regeneration Upgrade",90,"regen"),
    ("Energy Upgrade",45,"energy")
]

def draw_shop(player,mouse):
    panel=pygame.Rect(WIDTH//2-240,HEIGHT//2-220,480,440)

    pygame.draw.rect(screen,(30,15,35),panel,border_radius=15)
    pygame.draw.rect(screen,LIGHT_PINK,panel,3,border_radius=15)

    title=BIG.render("POWER SHOP",True,LIGHT_PINK)
    screen.blit(title,title.get_rect(center=(WIDTH//2,HEIGHT//2-175)))

    text(screen,f"Coins: {player.coins}",WIDTH//2-70,HEIGHT//2-130,GOLD)

    buttons=[]

    for i,(name,price,kind) in enumerate(SHOP_ITEMS):
        rect=pygame.Rect(WIDTH//2-180,HEIGHT//2-85+i*65,360,48)
        pygame.draw.rect(screen,(155,35,110) if rect.collidepoint(mouse)
                         else (85,30,75),rect,border_radius=8)
        pygame.draw.rect(screen,WHITE,rect,1,border_radius=8)
        text(screen,f"{name} - {price} coins",rect.x+15,rect.y+12)
        buttons.append((rect,price,kind))

    text(screen,"Press B or ESC to close",WIDTH//2-110,HEIGHT//2+190,WHITE,SMALL)
    return buttons

def buy_item(player,kind,price):
    if player.coins<price:
        return

    if kind=="damage":
        player.damage_bonus+=5
    elif kind=="health":
        player.max_health+=20
        player.health+=20
    elif kind=="regen":
        player.regeneration=True
    elif kind=="energy":
        player.max_energy+=20
        player.energy=min(player.max_energy,player.energy+20)

    player.coins-=price

    save["damage"]=player.damage_bonus
    save["max_health"]=player.max_health
    save["coins"]=player.coins
    save_game()

# ---------------- GAME SETUP ----------------

def spawn_zombie(player,wave,boss=False):
    side=random.randrange(4)

    if side==0:
        x,y=player.x+random.randint(-500,500),player.y-500
    elif side==1:
        x,y=player.x+random.randint(-500,500),player.y+500
    elif side==2:
        x,y=player.x-500,player.y+random.randint(-400,400)
    else:
        x,y=player.x+500,player.y+random.randint(-400,400)

    x=clamp(x,50,WORLD_W-50)
    y=clamp(y,50,WORLD_H-50)

    z=Zombie(x,y,wave,"boss" if boss else None)
    z.boss=boss
    return z

def new_game():
    p=Player()
    return p,[],[],[],[],1,0,0,False

player,zombies,bullets,particles,pickups,wave,spawn_timer,world_time,boss_spawned=new_game()

game_state="menu"
shop_buttons=[]
show_map=True
last_shot=0
running=True

# ---------------- MAIN LOOP ----------------

while running:
    dt=clock.tick(FPS)
    world_time+=dt

    keys=pygame.key.get_pressed()
    mouse=pygame.mouse.get_pos()

    camera=(
        clamp(player.x-WIDTH//2,0,WORLD_W-WIDTH),
        clamp(player.y-HEIGHT//2,0,WORLD_H-HEIGHT)
    )

    mouse_world=(mouse[0]+camera[0],mouse[1]+camera[1])

    for event in pygame.event.get():

        if event.type==pygame.QUIT:
            save["coins"]=player.coins
            save["level"]=player.level
            save["high_score"]=max(save.get("high_score",0),player.score)
            save_game()
            running=False

        if event.type==pygame.KEYDOWN:

            if event.key==pygame.K_ESCAPE:
                if game_state=="playing":
                    game_state="paused"
                elif game_state=="paused":
                    game_state="playing"
                elif game_state=="shop":
                    game_state="playing"
                elif game_state in ("gameover","victory"):
                    game_state="menu"

            if game_state=="playing":
                if event.key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4):
                    player.weapon=int(event.unicode)

                elif event.key==pygame.K_r:
                    if player.reload==0:
                        player.reload=75

                elif event.key==pygame.K_SPACE:
                    player.blast(zombies,particles)

                elif event.key in (pygame.K_LSHIFT,pygame.K_RSHIFT):
                    player.dash(keys,particles)

                elif event.key==pygame.K_h:
                    player.heal()

                elif event.key==pygame.K_q:
                    player.activate_shield()

                elif event.key==pygame.K_b:
                    game_state="shop"

                elif event.key==pygame.K_m:
                    show_map=not show_map

            elif game_state=="shop" and event.key==pygame.K_b:
                game_state="playing"

        if event.type==pygame.MOUSEBUTTONDOWN:

            if game_state=="menu":
                if pygame.Rect(WIDTH//2-125,365,250,65).collidepoint(event.pos):
                    player,zombies,bullets,particles,pickups,wave,spawn_timer,world_time,boss_spawned=new_game()
                    game_state="playing"

            elif game_state=="shop":
                for rect,price,kind in shop_buttons:
                    if rect.collidepoint(event.pos):
                        buy_item(player,kind,price)

            elif game_state=="gameover":
                if pygame.Rect(WIDTH//2-120,440,240,60).collidepoint(event.pos):
                    game_state="menu"

    # ---------------- UPDATE ----------------

    if game_state=="playing":

        player.update(keys)

        if pygame.mouse.get_pressed()[0]:
            now=pygame.time.get_ticks()
            rate=player.weapons[player.weapon]["rate"]
            if now-last_shot>=rate:
                player.shoot(mouse_world,bullets)
                last_shot=now

        spawn_timer+=1

        if wave%5==0 and not boss_spawned:
            zombies.append(spawn_zombie(player,wave,True))
            boss_spawned=True

        if spawn_timer>max(18,80-wave*3):
            spawn_timer=0
            if len(zombies)<8+wave*2:
                zombies.append(spawn_zombie(player,wave))

        for z in zombies[:]:
            z.update(player,particles)

            d=dist(player.x,player.y,z.x,z.y)

            if d<player.health*0+z.radius+20:
                if player.invincible==0 and player.shield==0:
                    player.health-=z.damage*.025

            # Exploding zombie
            if z.kind=="exploder" and d<z.radius+28:
                if player.shield==0 and player.invincible==0:
                    player.health-=.6
                for _ in range(3):
                    particles.append(Particle(z.x,z.y,(255,100,30),7))

            # Poison zombie
            if z.kind=="poison" and d<130:
                if player.shield==0:
                    player.health-=.012

            if z.health<=0:
                player.kills+=1
                player.score+=250 if z.boss else 30
                player.coins+=30 if z.boss else 3
                player.gain_xp(50 if z.boss else 20)

                for _ in range(24):
                    particles.append(Particle(z.x,z.y,(120,180,85),8))

                if random.random()<.35:
                    pickups.append(Pickup(z.x,z.y,
                        random.choice(["health","energy","ammo","coin"])))

                zombies.remove(z)

        for b in bullets[:]:
            b.update()

            if b.life<=0:
                bullets.remove(b)
                continue

            hit=False
            for z in zombies:
                if dist(b.x,b.y,z.x,z.y)<z.radius+b.radius:
                    z.health-=b.damage
                    hit=True
                    break

            if hit and b in bullets:
                bullets.remove(b)

        for p in pickups[:]:
            p.life-=1

            if dist(player.x,player.y,p.x,p.y)<38:
                if p.kind=="health":
                    player.health=min(player.max_health,player.health+35)
                elif p.kind=="energy":
                    player.energy=min(player.max_energy,player.energy+35)
                elif p.kind=="ammo":
                    for w in player.weapons.values():
                        w["ammo"]=w["max"]
                elif p.kind=="coin":
                    player.coins+=20
                pickups.remove(p)

            elif p.life<=0:
                pickups.remove(p)

        for p in particles[:]:
            p.update()
            if p.life<=0:
                particles.remove(p)

        if len(zombies)==0 and spawn_timer>100:
            wave+=1
            spawn_timer=0
            boss_spawned=False

            if wave>30:
                game_state="victory"

        if player.health<=0:
            player.health=0
            game_state="gameover"

    # ---------------- DRAW ----------------

    draw_world(camera,world_time)

    for p in pickups:
        p.draw(camera)

    for b in bullets:
        b.draw(camera)

    for z in zombies:
        z.draw(camera)

    for p in particles:
        p.draw(camera)

    player.draw(camera,mouse_world)

    if game_state in ("playing","paused","shop","gameover","victory"):
        draw_hud(player,wave,zombies)

        if show_map:
            draw_minimap(player,zombies)

    if game_state=="menu":
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((15,5,25,220))
        screen.blit(overlay,(0,0))

        title=BIG.render("PINK POWER SURVIVOR",True,LIGHT_PINK)
        screen.blit(title,title.get_rect(center=(WIDTH//2,230)))

        text(screen,"THE CITY HAS FALLEN. SHE HAS NOT.",
             WIDTH//2-200,300)

        rect=pygame.Rect(WIDTH//2-125,365,250,65)
        pygame.draw.rect(screen,DARK_PINK,rect,border_radius=12)
        pygame.draw.rect(screen,WHITE,rect,2,border_radius=12)
        text(screen,"START GAME",WIDTH//2-75,385)

        text(screen,f"High Score: {save.get('high_score',0)}",
             WIDTH//2-100,465,GOLD)

        text(screen,"WASD Move | Mouse Aim | Click Shoot | SPACE Blast",
             WIDTH//2-250,535,WHITE,SMALL)

    elif game_state=="paused":
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((10,5,20,190))
        screen.blit(overlay,(0,0))
        title=BIG.render("PAUSED",True,LIGHT_PINK)
        screen.blit(title,title.get_rect(center=(WIDTH//2,HEIGHT//2)))
        text(screen,"Press ESC to continue",WIDTH//2-110,HEIGHT//2+55)

    elif game_state=="shop":
        shop_buttons=draw_shop(player,mouse)

    elif game_state=="gameover":
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((25,0,0,200))
        screen.blit(overlay,(0,0))

        title=BIG.render("GAME OVER",True,RED)
        screen.blit(title,title.get_rect(center=(WIDTH//2,260)))

        text(screen,f"Score: {player.score}",WIDTH//2-65,340)
        text(screen,f"Kills: {player.kills}",WIDTH//2-65,375)

        rect=pygame.Rect(WIDTH//2-120,440,240,60)
        pygame.draw.rect(screen,DARK_PINK,rect,border_radius=10)
        text(screen,"MAIN MENU",WIDTH//2-65,458)

    elif game_state=="victory":
        overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        overlay.fill((20,0,30,200))
        screen.blit(overlay,(0,0))

        title=BIG.render("CITY SAVED!",True,LIGHT_PINK)
        screen.blit(title,title.get_rect(center=(WIDTH//2,260)))

        text(screen,f"Final Score: {player.score}",
             WIDTH//2-100,340,GOLD)

        text(screen,"You are the ultimate survivor!",
             WIDTH//2-170,390)

    pygame.display.flip()

# ---------------- EXIT ----------------

save["high_score"]=max(save.get("high_score",0),player.score)
save["coins"]=player.coins
save["level"]=player.level
save["damage"]=player.damage_bonus
save["max_health"]=player.max_health
save_game()

pygame.quit()
sys.exit()
