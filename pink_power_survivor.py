import pygame
import random
import math
import json
import sys
from array import array

# ==========================================================
# PINK POWER SURVIVOR 3.0
# Python 3.10+ / pygame-ce (also works with pygame)
#
# WASD / Arrows  Move            Mouse   Aim
# Left Click     Shoot (hold)    1-4     Change weapon
# R              Reload          SPACE   Energy blast
# SHIFT          Dash            H       Heal
# Q              Shield          M       Mini-map
# B              Shop            ESC     Pause
# ==========================================================

pygame.init()
AUDIO = False
try:
    pygame.mixer.init(22050, -16, 1, 512)
    AUDIO = True
except pygame.error:
    pass

WIDTH, HEIGHT = 1200, 750
FPS = 60
WORLD_W, WORLD_H = 2600, 1900
WIN_WAVE = 20

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pink Power Survivor 3.0")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 21, bold=True)
SMALL = pygame.font.SysFont("arial", 15)
TINY = pygame.font.SysFont("arial", 14, bold=True)
MID = pygame.font.SysFont("arial", 28, bold=True)
BIG = pygame.font.SysFont("arial", 52, bold=True)
HUGE = pygame.font.SysFont("arial", 72, bold=True)

PINK = (255, 70, 175)
LIGHT_PINK = (255, 175, 220)
DARK_PINK = (135, 25, 90)
WHITE = (255, 255, 255)
BLACK = (10, 10, 15)
RED = (220, 40, 45)
GREEN = (70, 220, 120)
GOLD = (255, 210, 65)
BLUE = (90, 180, 255)
CYAN = (90, 240, 240)
ORANGE = (255, 130, 30)

SAVE_FILE = "pink_power_save.json"

# ---------------- SAVE ----------------

DEFAULT_SAVE = {
    "high_score": 0, "best_wave": 0, "coins": 0,
    "up_damage": 0, "up_health": 0, "up_regen": 0,
    "up_energy": 0, "up_speed": 0,
}


def load_save():
    data = dict(DEFAULT_SAVE)
    try:
        with open(SAVE_FILE, "r") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            for k in DEFAULT_SAVE:
                if isinstance(loaded.get(k), (int, float)):
                    data[k] = max(0, int(loaded[k]))
    except (OSError, ValueError, TypeError):
        pass
    return data


save = load_save()


def save_game():
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(save, f, indent=4)
    except OSError:
        pass


# ---------------- SOUND (synthesised, no files needed) ----------------

SOUNDS = {}


def make_sound(freq, dur, vol, slide=0.0, noise=0.0, wave="square"):
    n = int(22050 * dur)
    buf = array("h")
    phase = 0.0
    for i in range(n):
        t = i / n
        f = max(20.0, freq + slide * t)
        phase += f / 22050
        if wave == "square":
            s = 1.0 if (phase % 1.0) < 0.5 else -1.0
        else:
            s = math.sin(phase * math.tau)
        if noise:
            s = s * (1 - noise) + random.uniform(-1, 1) * noise
        buf.append(int(s * vol * (1 - t) ** 1.5 * 32767))
    return pygame.mixer.Sound(buffer=buf)


def build_sounds():
    if not AUDIO:
        return
    specs = {
        "pistol": (520, .07, .16, -300, .35, "square"),
        "rifle": (430, .05, .12, -200, .4, "square"),
        "shotgun": (160, .16, .28, -80, .7, "square"),
        "laser": (900, .12, .16, -600, 0, "sine"),
        "hit": (220, .04, .10, -100, .5, "square"),
        "boom": (90, .45, .35, -50, .85, "square"),
        "pickup": (600, .12, .18, 500, 0, "sine"),
        "hurt": (180, .15, .28, -120, .4, "square"),
        "level": (400, .40, .22, 600, 0, "sine"),
        "empty": (150, .04, .12, 0, 0, "square"),
        "dash": (300, .12, .18, 500, .5, "sine"),
        "blast": (120, .35, .30, 300, .6, "sine"),
        "wave": (300, .30, .20, 300, 0, "sine"),
    }
    for name, args in specs.items():
        try:
            SOUNDS[name] = make_sound(*args)
        except (pygame.error, TypeError, ValueError):
            pass


def sfx(name):
    s = SOUNDS.get(name)
    if s:
        s.play()


build_sounds()

# ---------------- HELPERS ----------------


def text(surface, value, x, y, color=WHITE, font=FONT, center=False, shadow=False):
    image = font.render(str(value), True, color)
    rect = image.get_rect(center=(x, y)) if center else image.get_rect(topleft=(x, y))
    if shadow:
        sh = font.render(str(value), True, (0, 0, 0))
        surface.blit(sh, rect.move(2, 2))
    surface.blit(image, rect)


def clamp(v, low, high):
    return max(low, min(high, v))


def dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def bar(surface, x, y, w, h, value, maximum, color):
    pygame.draw.rect(surface, (50, 40, 50), (x, y, w, h), border_radius=5)
    fill = int(w * clamp(value / max(1, maximum), 0, 1))
    if fill > 0:
        pygame.draw.rect(surface, color, (x, y, fill, h), border_radius=5)
    pygame.draw.rect(surface, WHITE, (x, y, w, h), 1, border_radius=5)


def world_screen(x, y, camera):
    return int(x - camera[0]), int(y - camera[1])


def on_screen(sx, sy, margin=80):
    return -margin < sx < WIDTH + margin and -margin < sy < HEIGHT + margin


FX = {"shake": 0.0, "flash": 0}

_GLOW = {}


def glow(x, y, radius, color, alpha=90):
    """Soft cached glow (used for eyes, auras, explosions)."""
    radius = max(4, int(radius))
    key = (radius, color, alpha)
    surf = _GLOW.get(key)
    if surf is None:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        steps = 9
        for i in range(steps):
            rr = int(radius * (1 - i / steps))
            a = int(alpha * ((i + 1) / steps) ** 2)
            pygame.draw.circle(surf, (*color, a), (radius, radius), max(1, rr))
        _GLOW[key] = surf
    screen.blit(surf, (int(x) - radius, int(y) - radius))


def _E(col, x, y, w, h, width=0):
    pygame.draw.ellipse(screen, col, (int(x), int(y), max(1, int(w)), max(1, int(h))), width)


def _C(col, x, y, rad, width=0):
    pygame.draw.circle(screen, col, (int(x), int(y)), max(1, int(rad)), width)


# ---------------- EFFECTS ----------------


class Particle:
    def __init__(self, x, y, color, power=5):
        self.x, self.y = x, y
        angle = random.random() * math.tau
        speed = random.uniform(1, max(1.1, power))
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.max_life = random.randint(15, 35)
        self.life = self.max_life
        self.radius = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= 1

    def draw(self, camera):
        x, y = world_screen(self.x, self.y, camera)
        if on_screen(x, y):
            r = max(1, int(self.radius * self.life / self.max_life))
            pygame.draw.circle(screen, self.color, (x, y), r)


class FloatText:
    def __init__(self, x, y, value, color=WHITE, big=False):
        self.x, self.y = x, y
        self.value, self.color, self.big = value, color, big
        self.life = 50

    def update(self):
        self.y -= 0.8
        self.life -= 1

    def draw(self, camera):
        x, y = world_screen(self.x, self.y, camera)
        text(screen, self.value, x, y, self.color, MID if self.big else TINY,
             center=True, shadow=True)


class Ring:
    def __init__(self, x, y, max_r, color, speed=None):
        self.x, self.y, self.r, self.max_r, self.color = x, y, 10, max_r, color
        self.speed = speed or max_r / 14
        self.life = 1

    def update(self):
        self.r += self.speed
        if self.r >= self.max_r:
            self.life = 0

    def draw(self, camera):
        x, y = world_screen(self.x, self.y, camera)
        width = max(1, int(6 * (1 - self.r / self.max_r)))
        pygame.draw.circle(screen, self.color, (x, y), int(self.r), width)


# ---------------- PROJECTILES ----------------

WEAPONS = {
    1: dict(name="PISTOL", damage=25, mag=15, rate=330, reload=55, spread=.02,
            speed=14, life=80, pierce=0, pellets=1, color=LIGHT_PINK, radius=5,
            shake=1.5, sfx="pistol"),
    2: dict(name="SHOTGUN", damage=14, mag=8, rate=650, reload=90, spread=.24,
            speed=12, life=38, pierce=0, pellets=7, color=GOLD, radius=5,
            shake=5, sfx="shotgun"),
    3: dict(name="RIFLE", damage=13, mag=40, rate=95, reload=80, spread=.06,
            speed=15, life=85, pierce=0, pellets=1, color=ORANGE, radius=4,
            shake=1.2, sfx="rifle"),
    4: dict(name="LASER", damage=40, mag=12, rate=420, reload=100, spread=0,
            speed=24, life=60, pierce=4, pellets=1, color=BLUE, radius=6,
            shake=2.5, sfx="laser"),
}


class Bullet:
    def __init__(self, x, y, angle, damage, color, speed, radius, life, pierce, crit):
        self.x, self.y = x, y
        self.damage, self.color, self.radius = damage, color, radius
        self.life, self.pierce, self.crit = life, pierce, crit
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.hit = set()

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, camera):
        x, y = world_screen(self.x, self.y, camera)
        if not on_screen(x, y):
            return
        pygame.draw.line(screen, self.color, (x - self.vx * .9, y - self.vy * .9), (x, y),
                         max(2, self.radius))
        pygame.draw.circle(screen, self.color, (x, y), self.radius)
        pygame.draw.circle(screen, WHITE, (x, y), max(1, self.radius // 2))


class EnemyBullet:
    def __init__(self, x, y, angle, damage, speed=5.0):
        self.x, self.y, self.damage = x, y, damage
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.radius = 7
        self.life = 160

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, camera):
        x, y = world_screen(self.x, self.y, camera)
        if on_screen(x, y):
            pygame.draw.circle(screen, (60, 200, 60), (x, y), self.radius)
            pygame.draw.circle(screen, (190, 255, 150), (x, y), self.radius // 2)


# ---------------- UPGRADES / PERKS ----------------

UPGRADES = [
    dict(key="damage", name="Damage", desc="+4 damage per shot", base=50, max=10),
    dict(key="health", name="Max Health", desc="+20 max health", base=60, max=10),
    dict(key="regen", name="Regeneration", desc="Passive health regen", base=90, max=5),
    dict(key="energy", name="Energy Core", desc="+20 max energy", base=45, max=8),
    dict(key="speed", name="Swift Legs", desc="+4% move speed", base=70, max=6),
]


def upgrade_price(u):
    return int(u["base"] * (1 + 0.6 * save.get("up_" + u["key"], 0)))


PERKS = [
    ("Hollow Points", "+20% damage", lambda p: p.mul("dmg_mult", 1.2)),
    ("Swift Boots", "+10% move speed", lambda p: p.mul("speed_mult", 1.1)),
    ("Vitality", "+30 max health & heal", lambda p: p.add_health(30)),
    ("Trigger Happy", "+15% fire rate", lambda p: p.mul("fire_mult", 1.15)),
    ("Power Cell", "+40% energy regen", lambda p: p.mul("energy_regen", 1.4)),
    ("Vampiric Rounds", "Heal 2 HP per kill", lambda p: p.add("kill_heal", 2)),
    ("Sharpshooter", "+10% crit chance", lambda p: p.add("crit", .10)),
    ("Piercing Rounds", "Bullets pierce +1", lambda p: p.add("extra_pierce", 1)),
    ("Quick Dash", "Dash cooldown -25%", lambda p: p.mul("dash_mult", .75)),
    ("Scavenger", "+25% pickup magnet", lambda p: p.mul("magnet", 1.25)),
]

# ---------------- PLAYER ----------------


class Player:
    def __init__(self):
        self.x, self.y = WORLD_W / 2, WORLD_H / 2
        self.level, self.xp, self.xp_needed = 1, 0, 100
        self.pending_levels = 0

        self.max_health, self.max_energy = 100, 100
        self.speed, self.speed_mult = 4.1, 1.0
        self.damage_bonus, self.dmg_mult = 0, 1.0
        self.fire_mult, self.crit = 1.0, .05
        self.energy_regen, self.regen = 1.0, 0.0
        self.kill_heal, self.extra_pierce = 0, 0
        self.dash_mult, self.magnet = 1.0, 1.0

        self.angle, self.anim = 0, 0
        self.moving = False
        self.score, self.kills = 0, 0
        self.weapon = 1
        self.ammo = {k: w["mag"] for k, w in WEAPONS.items()}

        self.reload = self.reload_total = self.reload_weapon = 0
        self.dash_cd = self.blast_cd = self.heal_cd = self.shield_cd = 0
        self.shield = self.invincible = self.rapid = self.double = 0
        self.cdmax = {"dash": 110, "blast": 180, "heal": 240, "shield": 360}

        for u in UPGRADES:
            for _ in range(save.get("up_" + u["key"], 0)):
                self.apply_upgrade(u["key"])
        self.health = float(self.max_health)
        self.energy = float(self.max_energy)

    # coins live in the save so they persist between runs
    @property
    def coins(self):
        return save["coins"]

    @coins.setter
    def coins(self, v):
        save["coins"] = max(0, int(v))

    def mul(self, name, f):
        setattr(self, name, getattr(self, name) * f)

    def add(self, name, v):
        setattr(self, name, getattr(self, name) + v)

    def add_health(self, v):
        self.max_health += v
        self.health += v

    def apply_upgrade(self, key):
        if key == "damage":
            self.damage_bonus += 4
        elif key == "health":
            self.add_health(20)
        elif key == "regen":
            self.regen += 0.012
        elif key == "energy":
            self.max_energy += 20
            self.energy = min(self.max_energy, getattr(self, "energy", 0) + 20)
        elif key == "speed":
            self.speed_mult *= 1.04

    def take_damage(self, amount):
        if self.invincible or self.shield:
            return False
        self.health -= amount
        self.invincible = 14
        FX["shake"] = max(FX["shake"], 7)
        FX["flash"] = 18
        sfx("hurt")
        return True

    def update(self, keys, particles, mouse_world):
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        self.moving = bool(dx or dy)
        if dx or dy:
            length = math.hypot(dx, dy)
            sp = self.speed * self.speed_mult
            self.x += dx / length * sp
            self.y += dy / length * sp
            self.anim += 0.22
        self.x = clamp(self.x, 35, WORLD_W - 35)
        self.y = clamp(self.y, 35, WORLD_H - 35)
        self.angle = math.atan2(mouse_world[1] - self.y, mouse_world[0] - self.x)

        for name in ("dash_cd", "blast_cd", "heal_cd", "shield_cd",
                     "invincible", "shield", "rapid", "double"):
            setattr(self, name, max(0, getattr(self, name) - 1))

        self.energy = min(self.max_energy, self.energy + 0.045 * self.energy_regen)
        if self.regen:
            self.health = min(self.max_health, self.health + self.regen)

        if self.reload > 0:
            self.reload -= 1
            if self.reload == 0:
                self.ammo[self.reload_weapon] = WEAPONS[self.reload_weapon]["mag"]

    def switch_weapon(self, n):
        if n != self.weapon:
            self.weapon = n
            self.reload = 0  # switching cancels a reload (no more ammo bug)

    def start_reload(self):
        w = WEAPONS[self.weapon]
        if self.reload == 0 and self.ammo[self.weapon] < w["mag"]:
            self.reload = self.reload_total = w["reload"]
            self.reload_weapon = self.weapon

    def fire_delay(self):
        rate = WEAPONS[self.weapon]["rate"] / self.fire_mult
        return rate / 1.8 if self.rapid else rate

    def shoot(self, target, bullets, particles):
        w = WEAPONS[self.weapon]
        if self.reload > 0:
            return False
        if self.ammo[self.weapon] <= 0:
            sfx("empty")
            self.start_reload()
            return False
        self.ammo[self.weapon] -= 1
        base = math.atan2(target[1] - self.y, target[0] - self.x)
        dmg = (w["damage"] + self.damage_bonus) * self.dmg_mult * (2 if self.double else 1)
        for _ in range(w["pellets"]):
            ang = base + random.uniform(-w["spread"], w["spread"])
            crit = random.random() < self.crit
            bullets.append(Bullet(self.x + math.cos(ang) * 26, self.y + math.sin(ang) * 26,
                                  ang, dmg * (2 if crit else 1), w["color"], w["speed"],
                                  w["radius"], w["life"], w["pierce"] + self.extra_pierce, crit))
        mx, my = self.x + math.cos(base) * 30, self.y + math.sin(base) * 30
        for _ in range(4):
            particles.append(Particle(mx, my, w["color"], 4))
        FX["shake"] = max(FX["shake"], w["shake"])
        sfx(w["sfx"])
        if self.ammo[self.weapon] == 0:
            self.start_reload()
        return True

    def dash(self, keys, particles):
        if self.dash_cd or self.energy < 20:
            return
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        if dx == 0 and dy == 0:  # no direction held: dash toward the cursor
            dx, dy = math.cos(self.angle), math.sin(self.angle)
        length = math.hypot(dx, dy) or 1
        ox, oy = self.x, self.y
        self.x = clamp(self.x + dx / length * 160, 35, WORLD_W - 35)
        self.y = clamp(self.y + dy / length * 160, 35, WORLD_H - 35)
        for i in range(16):
            t = i / 15
            particles.append(Particle(ox + (self.x - ox) * t, oy + (self.y - oy) * t, PINK, 2))
        self.energy -= 20
        self.invincible = 35
        self.cdmax["dash"] = int(110 * self.dash_mult)
        self.dash_cd = self.cdmax["dash"]
        sfx("dash")

    def blast(self, zombies, particles, rings):
        if self.energy < 40 or self.blast_cd:
            return
        self.energy -= 40
        self.blast_cd = self.cdmax["blast"]
        dmg = (110 + self.damage_bonus * 2) * self.dmg_mult
        for z in zombies:
            d = dist(self.x, self.y, z.x, z.y)
            if d < 320:
                z.health -= dmg
                z.stun = 45
                z.hurt = 5
                push = (320 - d) * .35
                nx, ny = (z.x - self.x) / (d or 1), (z.y - self.y) / (d or 1)
                z.x += nx * push
                z.y += ny * push
        rings.append(Ring(self.x, self.y, 320, LIGHT_PINK))
        rings.append(Ring(self.x, self.y, 220, PINK, 12))
        for _ in range(80):
            particles.append(Particle(self.x, self.y, LIGHT_PINK, 12))
        FX["shake"] = max(FX["shake"], 12)
        sfx("blast")

    def heal(self):
        if self.energy >= 30 and self.heal_cd == 0 and self.health < self.max_health:
            self.energy -= 30
            self.health = min(self.max_health, self.health + 40)
            self.heal_cd = self.cdmax["heal"]
            sfx("pickup")

    def activate_shield(self):
        if self.energy >= 25 and self.shield_cd == 0:
            self.energy -= 25
            self.shield = 180
            self.shield_cd = self.cdmax["shield"]
            sfx("pickup")

    def gain_xp(self, amount, rings):
        self.xp += amount
        while self.xp >= self.xp_needed:
            self.xp -= self.xp_needed
            self.level += 1
            self.pending_levels += 1
            self.xp_needed = int(self.xp_needed * 1.3)
            self.max_health += 5
            self.health = min(self.max_health, self.health + 30)
            self.energy = self.max_energy
            rings.append(Ring(self.x, self.y, 200, GOLD))
            sfx("level")

    def draw(self, camera):
        sx, sy = world_screen(self.x, self.y, camera)
        ticks = pygame.time.get_ticks()
        fx, fy = math.cos(self.angle), math.sin(self.angle)
        bob = int(abs(math.sin(self.anim * 1.2)) * 4) if self.moving else int(math.sin(ticks * .004) * 1.5)
        walk = math.sin(self.anim) * 5 if self.moving else 0

        SKIN = (255, 226, 207)
        HAIR, HAIR_D = (255, 110, 185), (222, 66, 148)

        glow(sx, sy, 50, PINK, 60)
        _E((18, 18, 24), sx - 17, sy + 26, 34, 11)

        if self.shield:
            pulse = 44 + int(math.sin(ticks * .01) * 2)
            _C(BLUE, sx, sy, pulse, 3)
            glow(sx, sy, pulse, BLUE, 50)
        if self.invincible and self.invincible % 6 < 3:
            _C(WHITE, sx, sy, 40, 3)
        if self.rapid:
            _C(CYAN, sx, sy, 47, 1)
        if self.double:
            _C(GOLD, sx, sy, 50, 1)

        hx, hy = sx, sy - 26 - bob

        # fluttering cape
        flap = math.sin(ticks * .012) * 4 + (6 if self.moving else 0)
        sh = -fx * 10
        cape = [(sx - 9, sy - 6 - bob), (sx + 9, sy - 6 - bob),
                (sx + 15 + sh, sy + 20 + flap), (sx - 15 + sh, sy + 20 - flap)]
        pygame.draw.polygon(screen, (255, 140, 200), cape)
        pygame.draw.polygon(screen, (205, 60, 140), cape, 2)

        # pigtails (sway with movement)
        for side in (-1, 1):
            swing = math.sin(ticks * .008 + side) * 3 - fx * 4 + (math.sin(self.anim * 2) * 3 if self.moving else 0)
            end = (hx + side * 25 + swing, hy + 17)
            pygame.draw.line(screen, HAIR_D, (hx + side * 13, hy - 3), end, 11)
            pygame.draw.line(screen, HAIR, (hx + side * 13, hy - 3), end, 8)
            _C(HAIR, end[0], end[1], 7)
            _C(HAIR_D, end[0], end[1], 7, 1)

        # little legs with socks and boots
        for side in (-1, 1):
            lx = sx + side * 6
            foot = (lx + walk * side * .7, sy + 25)
            pygame.draw.line(screen, (250, 240, 250), (lx, sy + 12 - bob), foot, 7)
            pygame.draw.line(screen, (255, 150, 205), (lx, sy + 19), (foot[0], foot[1] - 1), 3)
            _E((205, 50, 135), foot[0] - 8, foot[1] - 2, 16, 9)
            _E((255, 220, 240), foot[0] - 4 + side * 2, foot[1] - 1, 8, 4)

        # dress
        dress = [(sx - 9, sy - 8 - bob), (sx + 9, sy - 8 - bob), (sx + 17, sy + 14 - bob), (sx - 17, sy + 14 - bob)]
        pygame.draw.polygon(screen, PINK, dress)
        pygame.draw.polygon(screen, (200, 40, 125), dress, 2)
        _E(LIGHT_PINK, sx - 18, sy + 9 - bob, 36, 9)
        pygame.draw.line(screen, WHITE, (sx - 10, sy + 1 - bob), (sx + 10, sy + 1 - bob), 3)
        _E(WHITE, sx - 8, sy - 12 - bob, 16, 6)
        # heart emblem
        _C(WHITE, sx - 2, sy - 5 - bob, 2)
        _C(WHITE, sx + 2, sy - 5 - bob, 2)
        pygame.draw.polygon(screen, WHITE, [(sx - 4, sy - 4 - bob), (sx + 4, sy - 4 - bob), (sx, sy + 1 - bob)])

        # off-hand
        ox, oy = sx - fy * 14, sy + 3 - bob
        pygame.draw.line(screen, SKIN, (sx - fy * 8, sy - 5 - bob), (ox, oy), 5)
        _C(WHITE, ox, oy, 4)

        # head
        _C(HAIR, hx, hy - 1, 19)
        for bx in (-15, 15):
            _C(HAIR, hx + bx, hy - 14, 8)
            _C(HAIR_D, hx + bx, hy - 14, 4)
        _C(SKIN, hx, hy + 3, 14)
        for bx, by in ((-9, -7), (-3, -9), (4, -9), (10, -6)):
            _C(HAIR, hx + bx, hy + by, 6)
        # bow
        pygame.draw.polygon(screen, WHITE, [(hx, hy - 20), (hx - 10, hy - 27), (hx - 10, hy - 13)])
        pygame.draw.polygon(screen, WHITE, [(hx, hy - 20), (hx + 10, hy - 27), (hx + 10, hy - 13)])
        _C((255, 90, 150), hx, hy - 20, 3)

        # big sparkly eyes that look toward the cursor
        blink = (ticks % 3200) < 130
        for side in (-1, 1):
            ex, ey = hx + side * 6.5, hy + 3
            if blink:
                pygame.draw.line(screen, (90, 40, 70), (ex - 4, ey), (ex + 4, ey), 2)
            else:
                _E(WHITE, ex - 4.5, ey - 6, 9, 12)
                ix, iy = ex + fx * 1.6, ey + fy * 1.6 + 1
                _C((110, 70, 170), ix, iy, 4)
                _C((20, 10, 30), ix, iy, 2)
                _C(WHITE, ix - 1.5, iy - 2, 2)
                _C(WHITE, ix + 2, iy + 2, 1)
                pygame.draw.line(screen, (90, 40, 70), (ex + side * 4, ey - 5), (ex + side * 7, ey - 7), 2)
        _C((255, 150, 170), hx - 10, hy + 9, 3)
        _C((255, 150, 170), hx + 10, hy + 9, 3)
        pygame.draw.arc(screen, (170, 60, 90), (int(hx) - 4, int(hy) + 7, 8, 6), math.pi, math.tau, 2)

        # aiming arm + cute toy blaster
        shx, shy = sx, sy - 6 - bob
        hand = (shx + fx * 19, shy + fy * 19)
        pygame.draw.line(screen, SKIN, (shx, shy), hand, 6)
        gun_end = (hand[0] + fx * 17, hand[1] + fy * 17)
        pygame.draw.line(screen, (70, 40, 80), hand, gun_end, 8)
        pygame.draw.line(screen, WEAPONS[self.weapon]["color"], hand, gun_end, 5)
        _C(WHITE, gun_end[0], gun_end[1], 3)
        _C(WHITE, hand[0], hand[1], 5)

        if self.reload > 0:
            bar(screen, sx - 22, sy - 62, 44, 6, self.reload_total - self.reload, self.reload_total, GOLD)



# ---------------- ZOMBIES ----------------

ZOMBIE_STATS = {
    # radius, hp, speed, damage, colour
    "normal": lambda w: (28, 95 + w * 8, 1.3 + w * .025, 13, (105, 125, 75)),
    "fast": lambda w: (21, 55 + w * 6, 2.4 + w * .035, 9, (145, 125, 75)),
    "tank": lambda w: (40, 220 + w * 16, .8 + w * .015, 22, (80, 95, 65)),
    "exploder": lambda w: (29, 85 + w * 7, 1.45 + w * .02, 28, (170, 80, 65)),
    "poison": lambda w: (31, 115 + w * 9, 1.1 + w * .02, 15, (90, 135, 85)),
    "spitter": lambda w: (25, 75 + w * 6, 1.0 + w * .02, 10, (110, 150, 70)),
    "boss": lambda w: (65, 1100 + w * 120, .9 + w * .02, 28, (80, 95, 60)),
}


HEAD_COL = {
    "normal": (140, 150, 110), "fast": (165, 150, 115), "tank": (105, 120, 92),
    "exploder": (170, 110, 88), "poison": (110, 165, 100), "spitter": (135, 165, 90),
    "boss": (95, 105, 88),
}


class Zombie:
    def __init__(self, x, y, wave, kind, elite=False):
        self.x, self.y = x, y
        self.stun = self.hurt = 0
        self.anim = random.random() * 10
        self.attack_cd = 0
        self.timer = random.randint(60, 140)
        self.charge = 0
        self.face = 0
        self.tilt = random.uniform(-.3, .3)
        self.eye_big = random.choice((-1, 1))
        self.wounds = [(random.uniform(-.7, .7), random.uniform(-.1, .8), random.uniform(.5, 1.2))
                       for _ in range(random.randint(2, 4))]
        self.kind = kind
        self.boss = kind == "boss"
        self.elite = elite

        r, hp, sp, dmg, col = ZOMBIE_STATS[kind](wave)
        if elite:
            r, hp, sp, dmg = int(r * 1.25), hp * 2.3, sp * 1.1, dmg * 1.3
        self.radius, self.max_health, self.speed, self.damage, self.color = r, hp, sp, dmg, col
        self.health = self.max_health

    def update(self, player, zombies, enemy_bullets, particles):
        if self.hurt:
            self.hurt -= 1
        self.attack_cd = max(0, self.attack_cd - 1)
        if self.stun:
            self.stun -= 1
            return

        dx, dy = player.x - self.x, player.y - self.y
        d = math.hypot(dx, dy) or 1
        self.face = math.atan2(dy, dx)
        speed = self.speed
        mx, my = dx / d, dy / d

        if self.boss:
            self.timer -= 1
            if self.charge > 0:
                self.charge -= 1
                speed *= 3.2
            elif self.timer <= 0:
                self.charge = 40
                self.timer = 200
                if random.random() < .6:  # ring of projectiles
                    for i in range(10):
                        enemy_bullets.append(EnemyBullet(self.x, self.y, i * math.tau / 10, 12, 4.5))
        elif self.kind == "spitter":
            if d < 220:
                mx, my = -mx, -my
                speed *= .8
            elif d < 330:
                speed = 0
            self.timer -= 1
            if self.timer <= 0 and d < 620:
                self.timer = 110
                enemy_bullets.append(EnemyBullet(self.x, self.y, self.face, 9, 5.5))

        self.x += mx * speed
        self.y += my * speed
        self.anim += .15

        # separation so zombies don't stack into one blob
        for o in zombies:
            if o is self:
                continue
            ddx, ddy = self.x - o.x, self.y - o.y
            dd = math.hypot(ddx, ddy)
            min_d = (self.radius + o.radius) * .8
            if 0 < dd < min_d:
                push = (min_d - dd) * .08
                self.x += ddx / dd * push
                self.y += ddy / dd * push

        self.x = clamp(self.x, 20, WORLD_W - 20)
        self.y = clamp(self.y, 20, WORLD_H - 20)

    def draw(self, camera):
        sx, sy = world_screen(self.x, self.y, camera)
        if not on_screen(sx, sy, 140):
            return
        r, k, t = self.radius, self.kind, self.anim
        hurt = self.hurt > 0
        fx, fy = math.cos(self.face), math.sin(self.face)
        px, py = -fy, fx
        s = 1 if self.tilt >= 0 else -1
        BONE = (228, 218, 186)
        DARK = (28, 22, 26)
        skin = (255, 255, 255) if hurt else HEAD_COL[k]
        body = (255, 255, 255) if hurt else self.color
        arm_col = (255, 255, 255) if hurt else tuple(min(255, c + 25) for c in self.color)

        # ---- auras ----
        if self.boss:
            glow(sx, sy, r * 2.4, (255, 0, 0), 95)
        elif k == "exploder":
            glow(sx, sy, r * 2, ORANGE, 85)
        elif k == "poison":
            glow(sx, sy, r * 2.2, (60, 255, 60), 75)
        elif k == "spitter":
            glow(sx, sy, r * 2, (180, 255, 60), 55)
        if self.elite:
            glow(sx, sy, r * 2, GOLD, 90)
        _E((8, 8, 10), sx - r, sy + r * .65, r * 2, r * .6)

        # ---- spikes / speed streaks ----
        if self.boss or k == "tank":
            n = 5 if self.boss else 2
            for i in range(n):
                a = self.face + math.pi + (i - (n - 1) / 2) * .5 if self.boss else self.face + math.pi / 2 + i * math.pi
                ca, sa = math.cos(a), math.sin(a)
                b0 = (sx + ca * r * .7, sy + sa * r * .7)
                pts = [(b0[0] - sa * r * .17, b0[1] + ca * r * .17), (b0[0] + sa * r * .17, b0[1] - ca * r * .17),
                       (sx + ca * r * 1.55, sy + sa * r * 1.55)]
                pygame.draw.polygon(screen, BONE, pts)
                pygame.draw.polygon(screen, DARK, pts, 1)
        if k == "fast":
            for i in (-1, 0, 1):
                pygame.draw.line(screen, (80, 80, 70), (sx - fx * r * 1.1 + px * i * r * .5, sy - fy * r * 1.1 + py * i * r * .5),
                                 (sx - fx * r * 2.2 + px * i * r * .5, sy - fy * r * 2.2 + py * i * r * .5), 2)

        # ---- shuffling legs ----
        lw = max(5, r // 3)
        for side in (-1, 1):
            ph = math.sin(t * 2 + side * 1.6)
            pygame.draw.line(screen, (45, 40, 45), (sx + side * r * .3, sy + r * .5),
                             (sx + side * r * .35 + ph * r * .3, sy + r * 1.0), lw)

        # ---- torso, torn clothes, wound with exposed ribs ----
        torso = (sx - r * .85, sy - r * .55, r * 1.7, r * 1.6)
        _E(body, *torso)
        _E(DARK, *torso, 2)
        cloth = [(sx - r * .9, sy), (sx - r * .7, sy + r * .95), (sx - r * .4, sy + r * .6), (sx - r * .15, sy + r * 1.0),
                 (sx + r * .2, sy + r * .62), (sx + r * .5, sy + r * .98), (sx + r * .9, sy + r * .1),
                 (sx + r * .4, sy - r * .35), (sx - r * .4, sy - r * .35)]
        pygame.draw.polygon(screen, (70, 50, 60) if not hurt else (230, 230, 230), cloth)
        wx, wy = sx - s * r * .3, sy - r * .05
        _E((85, 12, 18), wx - r * .35, wy - r * .35, r * .7, r * .7)
        for i in range(4):
            y = wy - r * .25 + i * r * .17
            pygame.draw.line(screen, BONE, (wx - r * .28, y), (wx + r * .28, y + r * .04), 2)
        pygame.draw.line(screen, (60, 8, 12), (wx, wy - r * .3), (wx, wy + r * .3), 2)
        for ox, oy, sz in self.wounds:
            _C((125, 12, 18), sx + ox * r, sy + oy * r, max(2, sz * r * .2))
            _C((70, 6, 10), sx + ox * r, sy + oy * r, max(1, sz * r * .09))

        if k == "exploder":
            pulse = .5 + .5 * math.sin(t * 3)
            _C((255, 130 + int(90 * pulse), 30), sx + s * r * .3, sy + r * .25, r * (.4 + .12 * pulse))
            glow(sx + s * r * .3, sy + r * .25, r * .9, (255, 170, 40), 130)
            for a in (0.3, 1.5, 2.6, 3.8, 5.0):
                pygame.draw.line(screen, (255, 230, 90), (sx + s * r * .3, sy + r * .25),
                                 (sx + s * r * .3 + math.cos(a) * r * .65, sy + r * .25 + math.sin(a) * r * .65), 2)
        elif k == "poison":
            for i in range(3):
                dy = (t * 9 + i * 13) % (r * .9)
                _C((90, 255, 90), sx + (i - 1) * r * .45, sy + r * .35 + dy, 3)

        # ---- long reaching arms with claws ----
        aw = max(5, r // 4)
        for side in (-1, 1):
            shx, shy = sx + side * r * .7, sy - r * .25
            reach = r * (1.5 + .15 * math.sin(t * 1.5 + side))
            wob = math.sin(t + side) * r * .25
            hx2 = shx + fx * reach + px * (side * r * .15 + wob)
            hy2 = shy + fy * reach + py * (side * r * .15 + wob)
            ex = (shx + hx2) / 2 + px * side * r * .3
            ey = (shy + hy2) / 2 + py * side * r * .3
            for w, col in ((aw + 3, DARK), (aw, arm_col)):
                pygame.draw.line(screen, col, (shx, shy), (ex, ey), w)
                pygame.draw.line(screen, col, (ex, ey), (hx2, hy2), w)
            for a in (-.5, 0, .5):
                ca = self.face + a
                pygame.draw.line(screen, BONE, (hx2, hy2), (hx2 + math.cos(ca) * r * .55, hy2 + math.sin(ca) * r * .55), 2)

        # ---- head ----
        hr = int(r * .8)
        hx = sx + fx * r * .25 + math.sin(t * .7) * 2
        hy = sy - r * .75 + math.sin(t * 1.3) * 1.5
        _C(skin, hx, hy, hr)
        _C(DARK, hx, hy, hr, 2)
        for i in range(4):
            x0 = hx + (i - 1.5) * hr * .35
            pygame.draw.line(screen, (35, 28, 28), (x0, hy - hr * .95), (x0 + (i - 1.5) * 3, hy - hr * .45), 2)
        # bone-exposed cheek
        pts = [(hx + s * hr * .15, hy - hr * .15), (hx + s * hr * .78, hy + hr * .05),
               (hx + s * hr * .55, hy + hr * .5), (hx + s * hr * .1, hy + hr * .22)]
        pygame.draw.polygon(screen, (110, 15, 20), pts)
        pygame.draw.polygon(screen, BONE, [(hx + s * hr * .3, hy), (hx + s * hr * .62, hy + hr * .1), (hx + s * hr * .45, hy + hr * .32)])
        vein = (60, 200, 60) if k == "poison" else ((255, 150, 40) if k == "exploder" else (75, 40, 60))
        for side in (-1, 1):
            pygame.draw.line(screen, vein, (hx + side * hr * .4, hy - hr * .1), (hx + side * hr * .8, hy - hr * .6), 1)
            pygame.draw.line(screen, vein, (hx + side * hr * .4, hy), (hx + side * hr * .55, hy + hr * .4), 1)
        if k == "tank":
            pygame.draw.line(screen, (140, 20, 25), (hx - hr * .7, hy - hr * .5), (hx + hr * .2, hy + hr * .6), 3)

        # glowing red eyes in black sockets, angry brows
        for side in (-1, 1):
            ex = hx + side * hr * .4
            ey = hy - hr * .12 + self.tilt * hr * .3 * side
            big = 1.25 if self.eye_big == side else 1.0
            _E((8, 0, 4), ex - hr * .3 * big, ey - hr * .28 * big, hr * .6 * big, hr * .56 * big)
            glow(ex, ey, hr * .8, (255, 30, 30), 130)
            _C((255, 45, 45), ex, ey, max(3, hr * .17 * big))
            _C((255, 225, 200), ex, ey, max(1, hr * .07))
            pygame.draw.line(screen, DARK, (ex + side * hr * .35, ey - hr * .42), (ex - side * hr * .3, ey - hr * .2), 3)

        pygame.draw.polygon(screen, (30, 12, 18), [(hx, hy + hr * .02), (hx - hr * .11, hy + hr * .3), (hx + hr * .11, hy + hr * .3)])

        # gaping jagged mouth, teeth, drool
        mw = hr * (1.25 if k == "spitter" else 1.1)
        mtop = hy + hr * .33
        opn = hr * (.45 + .2 * math.sin(t * 1.3)) * (1.4 if k == "spitter" else 1)
        mh = hr * .35 + opn
        _E((40, 4, 10), hx - mw / 2, mtop, mw, mh)
        n = 7
        for i in range(1, n - 1):
            x0 = hx - mw / 2 + mw * (i + .5) / n
            tw = mw / n * .5
            h1 = hr * (.24 + .12 * (i % 2))
            h2 = hr * (.2 + .1 * ((i + 1) % 2))
            pygame.draw.polygon(screen, (235, 225, 180), [(x0 - tw, mtop + hr * .04), (x0 + tw, mtop + hr * .04), (x0, mtop + h1)])
            pygame.draw.polygon(screen, (225, 215, 170), [(x0 - tw, mtop + mh - hr * .04), (x0 + tw, mtop + mh - hr * .04), (x0, mtop + mh - h2)])
        drool_col = (150, 255, 60) if k in ("spitter", "poison") else (160, 12, 18)
        for dx in (-.3, .15):
            ln = hr * (.3 + .3 * (1 + math.sin(t + dx * 5)) / 2)
            pygame.draw.line(screen, drool_col, (hx + dx * hr, mtop + mh), (hx + dx * hr, mtop + mh + ln), 2)
            _C(drool_col, hx + dx * hr, mtop + mh + ln, 2)

        if k == "spitter":
            sac = (hx, hy + hr * 1.05)
            _C((175, 205, 60), sac[0], sac[1], hr * .5)
            _C(DARK, sac[0], sac[1], hr * .5, 2)
            _C((235, 255, 150), sac[0] - 3, sac[1] - 2, max(2, hr * .12))
            _C((235, 255, 150), sac[0] + 4, sac[1] + 3, max(1, hr * .08))

        if self.boss:
            for side in (-1, 1):
                horn = [(hx + side * hr * .3, hy - hr * .8), (hx + side * hr * .88, hy - hr * .5), (hx + side * hr * 1.4, hy - hr * 1.9)]
                pygame.draw.polygon(screen, BONE, horn)
                pygame.draw.polygon(screen, DARK, horn, 2)
                _C((255, 40, 40), hx + side * hr * .3, hy - hr * .62, max(2, hr * .1))

        # ---- labels and health bar ----
        top = int(sy - (r * 1.95 if self.boss else r * 1.6)) - 12
        bar(screen, sx - r, top, r * 2, 7, self.health, self.max_health, RED)
        if self.boss:
            text(screen, "BOSS", sx, top - 14, GOLD, SMALL, center=True)
        elif self.elite:
            _C(GOLD, sx, sy, r + 10, 2)
            text(screen, "ELITE", sx, top - 12, GOLD, TINY, center=True)


# ---------------- PICKUPS ----------------

PICKUP_STYLE = {
    "health": (GREEN, "+"), "energy": (PINK, "E"), "ammo": (GOLD, "A"),
    "coin": (GOLD, "$"), "rapid": (CYAN, "R"), "double": (ORANGE, "2x"),
}


class Pickup:
    def __init__(self, x, y, kind):
        self.x, self.y, self.kind = x, y, kind
        self.life = 900
        self.t = random.random() * 6

    def update(self, player):
        self.life -= 1
        self.t += .1
        d = dist(player.x, player.y, self.x, self.y)
        if d < 140 * player.magnet and d > 1:
            self.x += (player.x - self.x) / d * 6
            self.y += (player.y - self.y) / d * 6

    def draw(self, camera):
        if self.life < 150 and self.life % 10 < 5:
            return
        sx, sy = world_screen(self.x, self.y, camera)
        if not on_screen(sx, sy):
            return
        sy += int(math.sin(self.t) * 3)
        color, symbol = PICKUP_STYLE[self.kind]
        pygame.draw.circle(screen, color, (sx, sy), 14)
        pygame.draw.circle(screen, WHITE, (sx, sy), 14, 2)
        text(screen, symbol, sx, sy, BLACK, TINY, center=True)


# ---------------- WORLD ----------------

tint_surface = pygame.Surface((WIDTH, HEIGHT))
tint_surface.fill((10, 10, 35))
hurt_surface = pygame.Surface((WIDTH, HEIGHT))
hurt_surface.fill((200, 0, 20))
dim_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
dim_surface.fill((15, 5, 25, 200))
vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for i in range(45):
    a = int(170 * (1 - i / 45) ** 2)
    pygame.draw.rect(vignette, (200, 0, 30, a), (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 1)
panel_surface = pygame.Surface((320, 305), pygame.SRCALPHA)
panel_surface.fill((10, 5, 20, 150))


def draw_world(camera, world_time):
    night = (math.sin(world_time * .0005) + 1) / 2
    shade = int(35 + night * 18)
    screen.fill((shade, shade + 5, shade + 8))

    grid = 100
    sx = int(camera[0] // grid) * grid
    sy = int(camera[1] // grid) * grid
    for x in range(sx, int(camera[0] + WIDTH) + grid, grid):
        xx = int(x - camera[0])
        pygame.draw.line(screen, (48, 50, 53), (xx, 0), (xx, HEIGHT))
    for y in range(sy, int(camera[1] + HEIGHT) + grid, grid):
        yy = int(y - camera[1])
        pygame.draw.line(screen, (48, 50, 53), (0, yy), (WIDTH, yy))

    for bx in range(0, WORLD_W, 450):
        for by in range(0, WORLD_H, 450):
            if (bx // 450 + by // 450) % 2 == 0:
                x, y = world_screen(bx + 50, by + 50, camera)
                if -220 < x < WIDTH + 100 and -180 < y < HEIGHT + 100:
                    pygame.draw.rect(screen, (35, 38, 43), (x, y, 175, 140))
                    pygame.draw.rect(screen, (75, 75, 80), (x, y, 175, 140), 3)
                    for wx in range(3):
                        for wy in range(2):
                            lit = (bx // 450 + wx + wy * 2 + by // 450) % 3 != 0
                            pygame.draw.rect(screen, (110, 90, 60) if lit else (45, 40, 40),
                                             (x + 20 + wx * 50, y + 20 + wy * 50, 25, 22))

    ox, oy = world_screen(0, 0, camera)
    pygame.draw.rect(screen, DARK_PINK, (ox, oy, WORLD_W, WORLD_H), 8)

    tint_surface.set_alpha(int(night * 45))
    screen.blit(tint_surface, (0, 0))


def draw_minimap(player, zombies, pickups, camera):
    w, h = 180, 130
    x, y = WIDTH - w - 20, HEIGHT - h - 20
    pygame.draw.rect(screen, (15, 15, 25), (x, y, w, h))
    pygame.draw.rect(screen, LIGHT_PINK, (x, y, w, h), 2)
    pygame.draw.rect(screen, (90, 60, 90),
                     (x + camera[0] / WORLD_W * w, y + camera[1] / WORLD_H * h,
                      WIDTH / WORLD_W * w, HEIGHT / WORLD_H * h), 1)
    for p in pickups:
        pygame.draw.circle(screen, PICKUP_STYLE[p.kind][0],
                           (int(x + p.x / WORLD_W * w), int(y + p.y / WORLD_H * h)), 2)
    for z in zombies:
        pygame.draw.circle(screen, GOLD if z.boss else RED,
                           (int(x + z.x / WORLD_W * w), int(y + z.y / WORLD_H * h)), 4 if z.boss else 3)
    pygame.draw.circle(screen, PINK, (int(x + player.x / WORLD_W * w), int(y + player.y / WORLD_H * h)), 5)


# ---------------- HUD ----------------


def draw_ability(x, key, label, cd, cdmax, cost, energy):
    y = HEIGHT - 76
    r = pygame.Rect(x, y, 56, 56)
    pygame.draw.rect(screen, (40, 20, 50), r, border_radius=8)
    ready = cd == 0 and energy >= cost
    if cd > 0:
        h = int(56 * cd / max(1, cdmax))
        s = pygame.Surface((56, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        screen.blit(s, (x, y + 56 - h))
    pygame.draw.rect(screen, LIGHT_PINK if ready else (110, 70, 100), r, 2, border_radius=8)
    text(screen, key, x + 28, y + 14, WHITE, TINY, center=True)
    text(screen, label, x + 28, y + 32, LIGHT_PINK if ready else (140, 110, 140), TINY, center=True)
    text(screen, f"{cost}E", x + 28, y + 46, BLUE if energy >= cost else RED, TINY, center=True)


def draw_hud(player, wave, zombies, remaining, combo, banner_text, banner_timer, mult):
    screen.blit(panel_surface, (10, 8))
    text(screen, "PINK POWER SURVIVOR", 20, 12, LIGHT_PINK)
    text(screen, f"LEVEL {player.level}", 20, 40, GOLD)

    text(screen, "HEALTH", 20, 76, WHITE, SMALL)
    bar(screen, 100, 76, 190, 18, player.health, player.max_health, GREEN)
    text(screen, f"{int(player.health)}/{player.max_health}", 195, 85, WHITE, TINY, center=True)
    text(screen, "ENERGY", 20, 102, WHITE, SMALL)
    bar(screen, 100, 102, 190, 18, player.energy, player.max_energy, PINK)
    text(screen, "XP", 20, 128, WHITE, SMALL)
    bar(screen, 100, 128, 190, 15, player.xp, player.xp_needed, BLUE)

    text(screen, f"Wave: {wave} / {WIN_WAVE}", 20, 158, GOLD)
    text(screen, f"Score: {player.score}", 20, 186)
    text(screen, f"Kills: {player.kills}", 20, 214)
    text(screen, f"Coins: {player.coins}", 20, 242, GOLD)
    if combo >= 2:
        text(screen, f"COMBO x{combo}  (score x{mult:.2f})", 20, 272, ORANGE, SMALL)

    w = WEAPONS[player.weapon]
    text(screen, f"Weapon: {w['name']}", WIDTH - 270, 15, LIGHT_PINK)
    if player.reload:
        text(screen, "RELOADING...", WIDTH - 270, 45, GOLD)
    else:
        text(screen, f"Ammo: {player.ammo[player.weapon]} / {w['mag']}", WIDTH - 270, 45,
             RED if player.ammo[player.weapon] <= w["mag"] * .2 else WHITE)
    text(screen, f"Zombies left: {remaining}", WIDTH - 270, 75, RED)
    text(screen, "1 Pistol  2 Shotgun  3 Rifle  4 Laser", WIDTH - 270, 105, (200, 160, 190), SMALL)

    ty = 130
    if player.rapid:
        text(screen, f"RAPID FIRE {player.rapid // 60 + 1}s", WIDTH - 270, ty, CYAN, SMALL)
        ty += 20
    if player.double:
        text(screen, f"DOUBLE DAMAGE {player.double // 60 + 1}s", WIDTH - 270, ty, ORANGE, SMALL)

    x0 = WIDTH // 2 - 140
    draw_ability(x0, "SHIFT", "Dash", player.dash_cd, player.cdmax["dash"], 20, player.energy)
    draw_ability(x0 + 72, "SPACE", "Blast", player.blast_cd, player.cdmax["blast"], 40, player.energy)
    draw_ability(x0 + 144, "H", "Heal", player.heal_cd, player.cdmax["heal"], 30, player.energy)
    draw_ability(x0 + 216, "Q", "Shield", player.shield_cd, player.cdmax["shield"], 25, player.energy)

    boss = next((z for z in zombies if z.boss), None)
    if boss:
        bar(screen, WIDTH // 2 - 220, 20, 440, 20, boss.health, boss.max_health, RED)
        text(screen, "BOSS ZOMBIE", WIDTH // 2, 50, GOLD, SMALL, center=True)

    if banner_timer > 0:
        a = clamp(banner_timer / 40, 0, 1)
        col = tuple(int(c * a) for c in LIGHT_PINK)
        text(screen, banner_text, WIDTH // 2, 180, col, HUGE, center=True, shadow=True)


# ---------------- SHOP / PERK SCREENS ----------------


def shop_layout():
    panel = pygame.Rect(WIDTH // 2 - 270, HEIGHT // 2 - 270, 540, 540)
    rects = [pygame.Rect(panel.x + 40, panel.y + 120 + i * 78, 460, 66) for i in range(len(UPGRADES))]
    return panel, rects


def draw_shop(mouse):
    screen.blit(dim_surface, (0, 0))
    panel, rects = shop_layout()
    pygame.draw.rect(screen, (30, 15, 35), panel, border_radius=15)
    pygame.draw.rect(screen, LIGHT_PINK, panel, 3, border_radius=15)
    text(screen, "POWER SHOP", WIDTH // 2, panel.y + 45, LIGHT_PINK, BIG, center=True)
    text(screen, f"Coins: {save['coins']}", WIDTH // 2, panel.y + 92, GOLD, FONT, center=True)
    for i, (u, rect) in enumerate(zip(UPGRADES, rects)):
        lvl = save.get("up_" + u["key"], 0)
        maxed = lvl >= u["max"]
        price = upgrade_price(u)
        affordable = not maxed and save["coins"] >= price
        base = (155, 35, 110) if rect.collidepoint(mouse) and affordable else (85, 30, 75)
        pygame.draw.rect(screen, base if affordable or maxed else (55, 30, 55), rect, border_radius=8)
        pygame.draw.rect(screen, WHITE if affordable else (120, 100, 120), rect, 1, border_radius=8)
        text(screen, f"[{i + 1}] {u['name']}  Lv {lvl}/{u['max']}", rect.x + 14, rect.y + 8)
        text(screen, u["desc"], rect.x + 14, rect.y + 38, (210, 170, 200), SMALL)
        label = "MAX" if maxed else f"{price} coins"
        text(screen, label, rect.right - 14 - FONT.size(label)[0], rect.y + 20,
             GREEN if affordable else (RED if not maxed else GOLD))
    text(screen, "Click or press 1-5 to buy  |  B / ESC to close", WIDTH // 2, panel.bottom - 22,
         WHITE, SMALL, center=True)


def buy_upgrade(player, index):
    u = UPGRADES[index]
    lvl = save.get("up_" + u["key"], 0)
    price = upgrade_price(u)
    if lvl >= u["max"] or save["coins"] < price:
        return
    save["coins"] -= price
    save["up_" + u["key"]] = lvl + 1
    player.apply_upgrade(u["key"])
    save_game()
    sfx("pickup")


def perk_rects():
    return [pygame.Rect(WIDTH // 2 - 495 + i * 335, HEIGHT // 2 - 130, 320, 260) for i in range(3)]


def draw_levelup(choices, mouse, level):
    screen.blit(dim_surface, (0, 0))
    text(screen, "LEVEL UP!", WIDTH // 2, 150, GOLD, BIG, center=True, shadow=True)
    text(screen, f"You reached level {level}. Choose a perk:", WIDTH // 2, 205, WHITE, FONT, center=True)
    for i, (rect, perk) in enumerate(zip(perk_rects(), choices)):
        hot = rect.collidepoint(mouse)
        pygame.draw.rect(screen, (155, 35, 110) if hot else (70, 25, 65), rect, border_radius=14)
        pygame.draw.rect(screen, GOLD if hot else LIGHT_PINK, rect, 3, border_radius=14)
        text(screen, str(i + 1), rect.centerx, rect.y + 40, GOLD, BIG, center=True)
        text(screen, perk[0], rect.centerx, rect.y + 120, WHITE, MID, center=True)
        text(screen, perk[1], rect.centerx, rect.y + 170, LIGHT_PINK, FONT, center=True)


# ---------------- GAME STATE ----------------

player = None
zombies, bullets, enemy_bullets, particles = [], [], [], []
pickups, floaters, rings = [], [], []
wave = 1
quota = spawned = spawn_timer = intermission = 0
banner_text, banner_timer = "", 0
combo = combo_timer = 0
perk_choices = []
world_time = 0
last_shot = 0
cam = [WORLD_W / 2 - WIDTH / 2, WORLD_H / 2 - HEIGHT / 2]


def start_wave():
    global quota, spawned, spawn_timer, banner_text, banner_timer
    quota = 6 + wave * 3
    spawned = 0
    spawn_timer = 0
    boss_wave = wave % 5 == 0
    banner_text = f"BOSS WAVE {wave}" if boss_wave else f"WAVE {wave}"
    banner_timer = 150
    if boss_wave:
        zombies.append(spawn_zombie(wave, "boss"))
    sfx("wave")


def reset_game():
    global player, zombies, bullets, enemy_bullets, particles, pickups, floaters, rings
    global wave, intermission, combo, combo_timer, FX
    player = Player()
    zombies, bullets, enemy_bullets, particles = [], [], [], []
    pickups, floaters, rings = [], [], []
    wave = 1
    intermission = 0
    combo = combo_timer = 0
    FX["shake"] = 0
    FX["flash"] = 0
    start_wave()


def spawn_zombie(w, kind=None):
    px, py = player.x, player.y
    x, y = px, py
    for _ in range(10):
        a = random.random() * math.tau
        r = random.uniform(520, 720)
        x = clamp(px + math.cos(a) * r, 50, WORLD_W - 50)
        y = clamp(py + math.sin(a) * r, 50, WORLD_H - 50)
        if dist(x, y, px, py) > 380:
            break
    elite = False
    if kind is None:
        weights = {
            "normal": 45,
            "fast": 20 if w >= 2 else 0,
            "exploder": 10 if w >= 2 else 0,
            "tank": 14 if w >= 3 else 0,
            "poison": 10 if w >= 3 else 0,
            "spitter": 14 if w >= 4 else 0,
        }
        kind = random.choices(list(weights), weights=list(weights.values()))[0]
        elite = w >= 5 and random.random() < .06
    return Zombie(x, y, w, kind, elite)


def explode(x, y, radius, dmg):
    FX["shake"] = max(FX["shake"], 14)
    sfx("boom")
    rings.append(Ring(x, y, radius, ORANGE))
    for _ in range(50):
        particles.append(Particle(x, y, random.choice([(255, 120, 30), (255, 200, 60), (200, 60, 30)]), 9))
    d = dist(player.x, player.y, x, y)
    if d < radius + 20:
        player.take_damage(dmg * (1 - clamp(d / (radius + 40), 0, 1) * .6))
    for o in zombies:
        if o.health > 0 and dist(o.x, o.y, x, y) < radius:
            o.health -= dmg * 2
            o.hurt = 5


def kill_zombie(z):
    global combo, combo_timer
    combo += 1
    combo_timer = 150
    mult = min(3.0, 1 + combo * .05)
    base = 250 if z.boss else (60 if z.elite else 30)
    pts = int(base * mult)
    player.score += pts
    player.kills += 1
    player.coins += 40 if z.boss else (8 if z.elite else random.choice([2, 3, 3, 4]))
    player.gain_xp(60 if z.boss else (35 if z.elite else 20), rings)
    floaters.append(FloatText(z.x, z.y - z.radius, f"+{pts}", GOLD))

    for _ in range(24):
        particles.append(Particle(z.x, z.y, (120, 180, 85), 8))
    if z.kind == "exploder":
        explode(z.x, z.y, 120, 30)
    if player.kill_heal:
        player.health = min(player.max_health, player.health + player.kill_heal)

    drops = 4 if z.boss else (2 if z.elite else (1 if random.random() < .33 else 0))
    for _ in range(drops):
        kind = random.choices(list(PICKUP_STYLE), weights=[22, 20, 22, 24, 6, 6])[0]
        pickups.append(Pickup(z.x + random.randint(-25, 25), z.y + random.randint(-25, 25), kind))
    if z.boss:
        FX["shake"] = 22
        rings.append(Ring(z.x, z.y, 400, GOLD))
    zombies.remove(z)


def finish_run():
    save["high_score"] = max(save["high_score"], player.score)
    save["best_wave"] = max(save["best_wave"], wave)
    save_game()


def collect_pickup(p):
    sfx("pickup")
    k = p.kind
    if k == "health":
        player.health = min(player.max_health, player.health + 35)
        floaters.append(FloatText(player.x, player.y - 40, "+HP", GREEN))
    elif k == "energy":
        player.energy = min(player.max_energy, player.energy + 35)
        floaters.append(FloatText(player.x, player.y - 40, "+ENERGY", PINK))
    elif k == "ammo":
        player.ammo = {n: w["mag"] for n, w in WEAPONS.items()}
        player.reload = 0
        floaters.append(FloatText(player.x, player.y - 40, "AMMO REFILL", GOLD))
    elif k == "coin":
        player.coins += 20
        floaters.append(FloatText(player.x, player.y - 40, "+20", GOLD))
    elif k == "rapid":
        player.rapid = 600
        floaters.append(FloatText(player.x, player.y - 40, "RAPID FIRE!", CYAN, True))
    elif k == "double":
        player.double = 600
        floaters.append(FloatText(player.x, player.y - 40, "DOUBLE DAMAGE!", ORANGE, True))


reset_game()
game_state = "menu"
shop_return = "menu"
show_map = True
running = True

WEAPON_KEYS = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4}
SHOP_KEYS = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]

# ---------------- MAIN LOOP ----------------

while running:
    dt = clock.tick(FPS)
    world_time += dt

    keys = pygame.key.get_pressed()
    mouse = pygame.mouse.get_pos()

    # smooth camera + screen shake
    tx = clamp(player.x - WIDTH / 2, 0, WORLD_W - WIDTH)
    ty = clamp(player.y - HEIGHT / 2, 0, WORLD_H - HEIGHT)
    cam[0] += (tx - cam[0]) * .18
    cam[1] += (ty - cam[1]) * .18
    shake = FX["shake"]
    camera = (cam[0] + random.uniform(-shake, shake), cam[1] + random.uniform(-shake, shake))
    FX["shake"] = max(0, shake - .8)
    FX["flash"] = max(0, FX["flash"] - 1)
    mouse_world = (mouse[0] + camera[0], mouse[1] + camera[1])

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            finish_run()
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state == "playing":
                    game_state = "paused"
                elif game_state == "paused":
                    game_state = "playing"
                elif game_state == "shop":
                    game_state = shop_return
                elif game_state in ("gameover", "victory"):
                    game_state = "menu"

            if game_state == "menu":
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    reset_game()
                    game_state = "playing"
                elif event.key == pygame.K_b:
                    shop_return = "menu"
                    game_state = "shop"

            elif game_state == "playing":
                if event.key in WEAPON_KEYS:
                    player.switch_weapon(WEAPON_KEYS[event.key])
                elif event.key == pygame.K_r:
                    player.start_reload()
                elif event.key == pygame.K_SPACE:
                    player.blast(zombies, particles, rings)
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    player.dash(keys, particles)
                elif event.key == pygame.K_h:
                    player.heal()
                elif event.key == pygame.K_q:
                    player.activate_shield()
                elif event.key == pygame.K_b:
                    shop_return = "playing"
                    game_state = "shop"
                elif event.key == pygame.K_m:
                    show_map = not show_map

            elif game_state == "shop":
                if event.key == pygame.K_b:
                    game_state = shop_return
                elif event.key in SHOP_KEYS:
                    buy_upgrade(player, SHOP_KEYS.index(event.key))

            elif game_state == "levelup":
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    idx = (pygame.K_1, pygame.K_2, pygame.K_3).index(event.key)
                    perk_choices[idx][2](player)
                    player.pending_levels -= 1
                    sfx("pickup")
                    game_state = "playing"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == "menu":
                if pygame.Rect(WIDTH // 2 - 125, 365, 250, 65).collidepoint(event.pos):
                    reset_game()
                    game_state = "playing"
                elif pygame.Rect(WIDTH // 2 - 125, 445, 250, 50).collidepoint(event.pos):
                    shop_return = "menu"
                    game_state = "shop"

            elif game_state == "shop":
                for i, rect in enumerate(shop_layout()[1]):
                    if rect.collidepoint(event.pos):
                        buy_upgrade(player, i)

            elif game_state == "levelup":
                for i, rect in enumerate(perk_rects()):
                    if rect.collidepoint(event.pos):
                        perk_choices[i][2](player)
                        player.pending_levels -= 1
                        sfx("pickup")
                        game_state = "playing"

            elif game_state in ("gameover", "victory"):
                if pygame.Rect(WIDTH // 2 - 120, 440, 240, 60).collidepoint(event.pos):
                    game_state = "menu"

    # ---------------- UPDATE ----------------

    if game_state == "playing":
        player.update(keys, particles, mouse_world)

        if pygame.mouse.get_pressed()[0]:
            now = pygame.time.get_ticks()
            if now - last_shot >= player.fire_delay():
                if player.shoot(mouse_world, bullets, particles):
                    last_shot = now
                else:
                    last_shot = now  # throttle the empty-click sound too

        # ----- wave management -----
        if banner_timer > 0:
            banner_timer -= 1

        if intermission > 0:
            intermission -= 1
            if intermission == 0:
                wave += 1
                start_wave()
        elif spawned >= quota and not zombies:
            bonus = 10 + wave * 3
            player.coins += bonus
            player.health = min(player.max_health, player.health + player.max_health * .25)
            floaters.append(FloatText(player.x, player.y - 60, f"WAVE CLEARED  +{bonus} coins", GOLD, True))
            save["best_wave"] = max(save["best_wave"], wave)
            if wave >= WIN_WAVE:
                finish_run()
                game_state = "victory"
            else:
                intermission = 240
                banner_text = f"WAVE {wave} CLEARED"
                banner_timer = 150
                sfx("level")
        elif spawned < quota:
            spawn_timer += 1
            alive_cap = min(45, 10 + wave * 2)
            if spawn_timer > max(14, 70 - wave * 2) and len(zombies) < alive_cap:
                spawn_timer = 0
                zombies.append(spawn_zombie(wave))
                spawned += 1

        # ----- zombies -----
        for z in zombies[:]:
            z.update(player, zombies, enemy_bullets, particles)
            d = dist(player.x, player.y, z.x, z.y)

            if d < z.radius + 22 and z.attack_cd == 0 and not z.stun:
                if z.kind == "exploder":
                    z.health = 0  # detonates on contact
                elif player.take_damage(z.damage * .6):
                    z.attack_cd = 40

            if z.kind == "poison" and d < 130 and player.shield == 0:
                player.health -= .02

            if z.health <= 0:
                kill_zombie(z)

        # ----- player bullets -----
        for b in bullets[:]:
            b.update()
            if b.life <= 0 or not (0 < b.x < WORLD_W and 0 < b.y < WORLD_H):
                bullets.remove(b)
                continue
            for z in zombies:
                if z in b.hit:
                    continue
                if dist(b.x, b.y, z.x, z.y) < z.radius + b.radius:
                    z.health -= b.damage
                    z.hurt = 4
                    z.x += b.vx * .08
                    z.y += b.vy * .08
                    b.hit.add(z)
                    floaters.append(FloatText(z.x, z.y - z.radius - 10,
                                              f"{int(b.damage)}{'!' if b.crit else ''}",
                                              GOLD if b.crit else WHITE, b.crit))
                    for _ in range(3):
                        particles.append(Particle(b.x, b.y, (150, 40, 40), 4))
                    if random.random() < .4:
                        sfx("hit")
                    if b.pierce <= 0:
                        bullets.remove(b)
                        break
                    b.pierce -= 1

        # ----- enemy bullets -----
        for eb in enemy_bullets[:]:
            eb.update()
            if eb.life <= 0:
                enemy_bullets.remove(eb)
            elif dist(eb.x, eb.y, player.x, player.y) < eb.radius + 20:
                player.take_damage(eb.damage)
                enemy_bullets.remove(eb)

        # ----- pickups -----
        for p in pickups[:]:
            p.update(player)
            if dist(player.x, player.y, p.x, p.y) < 38:
                collect_pickup(p)
                pickups.remove(p)
            elif p.life <= 0:
                pickups.remove(p)

        # ----- effects -----
        for group in (particles, floaters):
            for e in group[:]:
                e.update()
                if e.life <= 0:
                    group.remove(e)
        for r in rings[:]:
            r.update()
            if r.life <= 0:
                rings.remove(r)

        if combo_timer > 0:
            combo_timer -= 1
            if combo_timer == 0:
                combo = 0

        # ----- state transitions -----
        if player.health <= 0:
            player.health = 0
            finish_run()
            sfx("boom")
            game_state = "gameover"
        elif player.pending_levels > 0:
            perk_choices = random.sample(PERKS, 3)
            game_state = "levelup"

    # ---------------- DRAW ----------------

    draw_world(camera, world_time)

    for r in rings:
        r.draw(camera)
    for p in pickups:
        p.draw(camera)
    for z in sorted(zombies, key=lambda zz: zz.y):
        z.draw(camera)
    for eb in enemy_bullets:
        eb.draw(camera)
    for b in bullets:
        b.draw(camera)
    if game_state != "menu":
        player.draw(camera)
    for p in particles:
        p.draw(camera)
    for f in floaters:
        f.draw(camera)

    if game_state in ("playing", "paused", "levelup", "gameover", "victory") or \
            (game_state == "shop" and shop_return == "playing"):
        # crosshair
        if game_state == "playing":
            pygame.draw.circle(screen, WHITE, mouse, 10, 1)
            pygame.draw.line(screen, WHITE, (mouse[0] - 16, mouse[1]), (mouse[0] - 6, mouse[1]))
            pygame.draw.line(screen, WHITE, (mouse[0] + 6, mouse[1]), (mouse[0] + 16, mouse[1]))
            pygame.draw.line(screen, WHITE, (mouse[0], mouse[1] - 16), (mouse[0], mouse[1] - 6))
            pygame.draw.line(screen, WHITE, (mouse[0], mouse[1] + 6), (mouse[0], mouse[1] + 16))

        if FX["flash"]:
            hurt_surface.set_alpha(FX["flash"] * 5)
            screen.blit(hurt_surface, (0, 0))
        if player.health < player.max_health * .3 and game_state == "playing":
            vignette.set_alpha(int(110 + 100 * math.sin(world_time * .01)))
            screen.blit(vignette, (0, 0))

        remaining = len(zombies) + max(0, quota - spawned)
        draw_hud(player, wave, zombies, remaining, combo, banner_text, banner_timer,
                 min(3.0, 1 + combo * .05))
        if show_map:
            draw_minimap(player, zombies, pickups, camera)

    if game_state == "menu":
        screen.blit(dim_surface, (0, 0))
        text(screen, "PINK POWER SURVIVOR", WIDTH // 2, 230, LIGHT_PINK, BIG, center=True)
        text(screen, "THE CITY HAS FALLEN. SHE HAS NOT.", WIDTH // 2, 310, WHITE, FONT, center=True)

        rect = pygame.Rect(WIDTH // 2 - 125, 365, 250, 65)
        hot = rect.collidepoint(mouse)
        pygame.draw.rect(screen, PINK if hot else DARK_PINK, rect, border_radius=12)
        pygame.draw.rect(screen, WHITE, rect, 2, border_radius=12)
        text(screen, "START GAME", rect.centerx, rect.centery, WHITE, FONT, center=True)

        rect2 = pygame.Rect(WIDTH // 2 - 125, 445, 250, 50)
        pygame.draw.rect(screen, (155, 35, 110) if rect2.collidepoint(mouse) else (70, 25, 65),
                         rect2, border_radius=10)
        pygame.draw.rect(screen, LIGHT_PINK, rect2, 2, border_radius=10)
        text(screen, "POWER SHOP (B)", rect2.centerx, rect2.centery, WHITE, FONT, center=True)

        text(screen, f"High Score: {save['high_score']}    Best Wave: {save['best_wave']}    "
                     f"Coins: {save['coins']}", WIDTH // 2, 530, GOLD, FONT, center=True)
        text(screen, "WASD Move | Mouse Aim | Click Shoot | 1-4 Weapons | R Reload",
             WIDTH // 2, 580, WHITE, SMALL, center=True)
        text(screen, "SPACE Blast | SHIFT Dash | H Heal | Q Shield | M Map | ENTER to start",
             WIDTH // 2, 604, LIGHT_PINK, SMALL, center=True)

    elif game_state == "paused":
        screen.blit(dim_surface, (0, 0))
        text(screen, "PAUSED", WIDTH // 2, HEIGHT // 2, LIGHT_PINK, BIG, center=True)
        text(screen, "Press ESC to continue", WIDTH // 2, HEIGHT // 2 + 55, WHITE, FONT, center=True)

    elif game_state == "shop":
        draw_shop(mouse)

    elif game_state == "levelup":
        draw_levelup(perk_choices, mouse, player.level)

    elif game_state == "gameover":
        screen.blit(dim_surface, (0, 0))
        text(screen, "GAME OVER", WIDTH // 2, 250, RED, BIG, center=True)
        text(screen, f"Score: {player.score}   Kills: {player.kills}   Wave: {wave}",
             WIDTH // 2, 330, WHITE, FONT, center=True)
        new_best = player.score >= save["high_score"] and player.score > 0
        text(screen, "NEW HIGH SCORE!" if new_best else f"High Score: {save['high_score']}",
             WIDTH // 2, 370, GOLD, FONT, center=True)
        rect = pygame.Rect(WIDTH // 2 - 120, 440, 240, 60)
        pygame.draw.rect(screen, PINK if rect.collidepoint(mouse) else DARK_PINK, rect, border_radius=10)
        text(screen, "MAIN MENU", rect.centerx, rect.centery, WHITE, FONT, center=True)

    elif game_state == "victory":
        screen.blit(dim_surface, (0, 0))
        text(screen, "CITY SAVED!", WIDTH // 2, 250, LIGHT_PINK, BIG, center=True)
        text(screen, f"Final Score: {player.score}", WIDTH // 2, 330, GOLD, FONT, center=True)
        text(screen, "You are the ultimate survivor!", WIDTH // 2, 375, WHITE, FONT, center=True)
        rect = pygame.Rect(WIDTH // 2 - 120, 440, 240, 60)
        pygame.draw.rect(screen, PINK if rect.collidepoint(mouse) else DARK_PINK, rect, border_radius=10)
        text(screen, "MAIN MENU", rect.centerx, rect.centery, WHITE, FONT, center=True)

    pygame.display.flip()

# ---------------- EXIT ----------------

save_game()
pygame.quit()
sys.exit()

