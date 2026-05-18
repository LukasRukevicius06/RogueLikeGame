"""
BLAZE BRIGADE  ·  main.py
Changes in this version:
  · FIX: Options screen from pause no longer freezes the game
  · FIX: Per-map highscores stored in highscore.json
  · NEW: Pre-game lobby screen (highscore + difficulty selector)
  · NEW: Difficulty system — Easy / Normal / Hard / Expert
  · NEW: Opened chests persist for current + 1 extra wave before despawning
"""

import pygame as py
import sys, random, os, json, math, csv
import settings
from settings import *

py.init()
py.mixer.init()

# ── Game state ────────────────────────────────────────────────────────────────
game_state   = 'menu'          # menu | map_select | pre_game | playing | paused | options
options_from = 'menu'
mouse_clicked = False
master_volume = 0.7
god_mode      = False

# ── Difficulty config ─────────────────────────────────────────────────────────
# Applied at init_game() time; enemies & player init read from here.
DIFFICULTY_PRESETS = {
    'Easy':   {'enemy_hp_mult': 0.5,  'enemy_speed_mult': 0.8,  'start_hearts': 3, 'label': 'Easy',   'col': (60,180,60)},
    'Normal': {'enemy_hp_mult': 1.0,  'enemy_speed_mult': 1.0,  'start_hearts': 3, 'label': 'Normal', 'col': (60,140,220)},
    'Hard':   {'enemy_hp_mult': 1.5,  'enemy_speed_mult': 1.0,  'start_hearts': 2, 'label': 'Hard',   'col': (220,130,0)},
    'Expert': {'enemy_hp_mult': 2.0,  'enemy_speed_mult': 1.0,  'start_hearts': 1, 'label': 'Expert', 'col': (210,30,30)},
}
selected_difficulty = 'Normal'   # updated by PreGameScreen before init_game()

def difficulty_cfg():
    return DIFFICULTY_PRESETS[selected_difficulty]

# ── Path helpers ──────────────────────────────────────────────────────────────
def sp(*p): return os.path.join("sprites", *p)
def ap(f):  return os.path.join("audio", f)

# ── Retro font loader ─────────────────────────────────────────────────────────
def _font(names, size, bold=False):
    for name in names:
        try:
            f = py.font.SysFont(name, size, bold=bold)
            if f: return f
        except Exception:
            pass
    return py.font.SysFont(None, size, bold=bold)

DISPLAY_FONTS = ['Trebuchet MS', 'Arial', 'Verdana', 'Tahoma', 'Comic Sans MS']
BODY_FONTS    = ['Courier New', 'Consolas', 'Courier', 'Comic Sans MS']

title_font = _font(DISPLAY_FONTS, 80, bold=False)
wave_font  = _font(DISPLAY_FONTS, 56, bold=False)
my_font    = _font(BODY_FONTS,    26, bold=False)
small_font = _font(BODY_FONTS,    20, bold=False)
tiny_font  = _font(BODY_FONTS,    16, bold=False)

# ── Display ───────────────────────────────────────────────────────────────────
display = py.display.set_mode((display_width, display_height), py.RESIZABLE)
py.display.set_caption('BLAZE BRIGADE')

# ── Map configurations ────────────────────────────────────────────────────────
MAP_CONFIGS = {
    1: {
        'name': 'The Outpost',
        'desc': 'A maze of corridors — learn every corner.',
        'csv':  'test_level.csv',
        'start_col': 22, 'start_row': 17,
        'spawn_zones': [
            (36, 4), (50, 4), (55, 14), (50, 26), (40, 29),
            (10, 29), (8,  14), (35, 9), (20, 9),
        ],
    },
    2: {
        'name': 'Dead Ring',
        'desc': 'Circular corridors — run the ring to survive.',
        'csv':  'map2_ring.csv',
        'start_col': 30, 'start_row': 17,
        'spawn_zones': [
            (5,  4), (20, 4), (40, 4), (54, 4),
            (5,  17), (54, 17),
            (5,  30), (20, 30), (40, 30), (54, 30),
            (14, 11), (45, 11), (14, 23), (45, 23),
        ],
    },
    3: {
        'name': 'The Cathedral',
        'desc': 'A grand arena with flanking wings — nowhere to hide.',
        'csv':  'map3_cathedral.csv',
        'start_col': 30, 'start_row': 17,
        'spawn_zones': [
            (20, 5), (30, 5), (40, 5),
            (20, 28), (30, 28), (40, 28),
            (8,  10), (8,  17), (8,  24),
            (52, 10), (52, 17), (52, 24),
            (7,  5), (53, 5),
        ],
    },
}

TILE_SIZE      = 64
MAP_OFFSET_X   = -418
MAP_OFFSET_Y   = -508
active_map_cfg = MAP_CONFIGS[1]

def set_active_map(cfg):
    global MAP_OFFSET_X, MAP_OFFSET_Y, active_map_cfg
    active_map_cfg = cfg
    MAP_OFFSET_X   = player_start_x - cfg['start_col'] * TILE_SIZE
    MAP_OFFSET_Y   = player_start_y - cfg['start_row'] * TILE_SIZE

set_active_map(MAP_CONFIGS[1])

# ── Static assets ─────────────────────────────────────────────────────────────
gameIcon = py.image.load(sp("ui", "icon.png"))
py.display.set_icon(gameIcon)

crosshair  = py.transform.smoothscale_by(
    py.image.load(sp("player", "crosshair.png")).convert_alpha(), 0.1)
fireball   = py.image.load(sp("projectiles", "fireball_sprite.png")).convert_alpha()

slime_frames = [
    py.transform.scale(
        py.image.load(sp("slime", f"slime_animation_{i}.png")), (64, 60))
    for i in range(4)
]

full_heart  = py.transform.scale_by(py.image.load(sp("ui", "full_heart.png")), 4)
half_heart  = py.transform.scale_by(py.image.load(sp("ui", "half_heart.png")), 4)
empty_heart = py.transform.scale_by(py.image.load(sp("ui", "empty_heart.png")), 4)

bullet_sound = py.mixer.Sound(ap("344312__musiclegends__laser-shoot7.wav"))
death_sound  = py.mixer.Sound(ap("173126__replix__death-sound-male.wav"))

# ── Optional assets (graceful fallback) ───────────────────────────────────────
sword_frames = []
for _i in range(9):
    try:
        _sf = py.image.load(sp("player", "sword", f"swing_{_i}.png")).convert_alpha()
        _h  = 160
        _w  = int(_sf.get_width() * _h / _sf.get_height())
        sword_frames.append(py.transform.smoothscale(_sf, (_w, _h)))
    except Exception:
        break

explosion_frames = []
for _i in range(16):
    try:
        _ef = py.image.load(sp("projectiles", f"explosion_{_i}.png")).convert_alpha()
        explosion_frames.append(py.transform.scale(_ef, (96, 96)))
    except Exception:
        break

try:
    hand_gun   = py.transform.scale(
        py.image.load(sp("player", "hand_gun.png")).convert_alpha(), (48, 28))
except Exception:
    hand_gun = None

try:
    _hs = py.image.load(sp("player", "hand_sword.png")).convert_alpha()
    _sh = 48
    _sw = int(_hs.get_width() * _sh / _hs.get_height())
    hand_sword = py.transform.smoothscale(_hs, (_sw, _sh))
except Exception:
    hand_sword = None

def _load_mp3(path):
    if not os.path.exists(path):
        return None
    try:
        snd = py.mixer.Sound(path)
        def _play():
            snd.set_volume(master_volume); snd.play()
        return _play
    except Exception as e:
        print(f"[audio] {path}: {e}"); return None

explosion_sound_play = _load_mp3(ap("explosion.mp3"))
reload_sound_play    = _load_mp3(ap("reload.mp3"))
ui_click_sound_play  = _load_mp3(ap("ui_click.mp3"))
life_lost_sound_play = _load_mp3(ap("life_lost.mp3"))
game_over_sound_play = _load_mp3(ap("game_over.mp3"))

bomb_frames = []
for _i in range(4):
    try:
        _bf = py.image.load(sp("bomb", f"bomb_{_i}.png")).convert_alpha()
        bomb_frames.append(py.transform.scale(_bf, (52, 52)))
    except Exception:
        break

bomb_explosion_frames = []
for _i in range(32):
    try:
        _bef = py.image.load(sp("bomb", f"explosion_{_i}.png")).convert_alpha()
        _bh  = 140
        _bw  = int(_bef.get_width() * _bh / _bef.get_height())
        bomb_explosion_frames.append(py.transform.smoothscale(_bef, (_bw, _bh)))
    except Exception:
        break

def apply_volume(vol):
    global master_volume
    master_volume = max(0.0, min(1.0, vol))
    bullet_sound.set_volume(master_volume)
    death_sound.set_volume(master_volume)

apply_volume(master_volume)

# ── Gameplay constants ────────────────────────────────────────────────────────
SPLASH_RADIUS  = 80
SHOP_RANGE     = 150
SHOP_DURATION  = 900
BUBBLE_RADIUS  = 200
HIGHSCORE_FILE = "highscore.json"
RELOAD_TIME    = 120
WALL_GRACE     = 5
DROP_LIFETIME  = 600
DROP_RADIUS    = 45
BOUNCE_LIMIT   = 3

# How many waves an opened chest lingers before being removed
CHEST_LINGER_WAVES = 1   # stays for the wave it was opened + this many more


# =============================================================================
# TILEMAP
# =============================================================================
class TileMap:
    def __init__(self, csv_filename):
        self.tile_size = TILE_SIZE
        self.grid = self._load_csv(csv_filename)
        self.rows  = len(self.grid)
        self.cols  = len(self.grid[0]) if self.rows else 0
        fl = py.image.load(sp("environment", "tile_1.png")).convert_alpha()
        wl = py.image.load(sp("environment", "tile_2.png")).convert_alpha()
        self.floor_img = py.transform.scale(fl, (TILE_SIZE, TILE_SIZE))
        self.wall_img  = py.transform.scale(wl, (TILE_SIZE, TILE_SIZE))

    def _load_csv(self, fn):
        grid = []
        with open(fn, newline='') as f:
            for row in csv.reader(f):
                p = [int(v.strip()) for v in row if v.strip()]
                if p: grid.append(p)
        return grid

    def draw(self, surface, scroll):
        sw, sh = surface.get_width(), surface.get_height()
        c0 = max(0, int((scroll[0] - MAP_OFFSET_X) // self.tile_size))
        r0 = max(0, int((scroll[1] - MAP_OFFSET_Y) // self.tile_size))
        c1 = min(self.cols, c0 + sw // self.tile_size + 2)
        r1 = min(self.rows, r0 + sh // self.tile_size + 2)
        for r in range(r0, r1):
            for c in range(c0, c1):
                sx = int(c * self.tile_size - scroll[0] + MAP_OFFSET_X)
                sy = int(r * self.tile_size - scroll[1] + MAP_OFFSET_Y)
                surface.blit(self.wall_img if self.grid[r][c] == 1
                             else self.floor_img, (sx, sy))

    def _is_wall(self, col, row):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.grid[row][col] == 1
        return True

    def screen_point_in_wall(self, sx, sy, scroll):
        col = int((sx + scroll[0] - MAP_OFFSET_X) / self.tile_size)
        row = int((sy + scroll[1] - MAP_OFFSET_Y) / self.tile_size)
        return self._is_wall(col, row)

    def world_point_in_wall(self, wx, wy):
        col = int((wx - MAP_OFFSET_X) / self.tile_size)
        row = int((wy - MAP_OFFSET_Y) / self.tile_size)
        return self._is_wall(col, row)

    def player_hits_wall(self, scroll, hw=32, hh=44):
        cx, cy = player_start_x, player_start_y
        return any(self.screen_point_in_wall(sx, sy, scroll)
                   for sx, sy in [(cx-hw, cy-hh), (cx+hw, cy-hh),
                                  (cx-hw, cy+hh), (cx+hw, cy+hh)])

    def enemy_hits_wall(self, ex, ey, w=64, h=60, m=10):
        return any(self.world_point_in_wall(wx, wy)
                   for wx, wy in [(ex+m,   ey+m),  (ex+w-m, ey+m),
                                  (ex+m,   ey+h-m),(ex+w-m, ey+h-m)])

    def valid_world_pos(self, wx, wy):
        checks = [(wx+32, wy+30),
                  (wx+10, wy+10), (wx+54, wy+10),
                  (wx+10, wy+50), (wx+54, wy+50)]
        return not any(self.world_point_in_wall(px, py_) for px, py_ in checks)

    def draw_minimap(self, surface, ox, oy, scale=5):
        for r, row in enumerate(self.grid):
            for c, val in enumerate(row):
                col = (55, 55, 65) if val == 1 else (130, 170, 130)
                py.draw.rect(surface, col,
                             (ox + c*scale, oy + r*scale, scale-1, scale-1))


# =============================================================================
# SWORD SWING
# =============================================================================
class SwordSwing:
    SWEEP_ANGLE     = 120
    REACH           = 130
    DAMAGE          = 3.0
    TICKS_PER_FRAME = 2

    def __init__(self, centre_angle):
        self.centre_angle = centre_angle
        self.frame        = 0
        self.tick         = 0
        self.done         = False
        self.hit_enemies  = set()

    def update(self):
        if self.done: return False
        self.tick += 1
        if self.tick % self.TICKS_PER_FRAME == 0:
            self.frame += 1
            if self.frame >= max(len(sword_frames), 9):
                self.done = True; return False

        px, py_ = player.screen_cx, player.screen_cy

        if sword_frames and self.frame < len(sword_frames):
            img = py.transform.rotate(sword_frames[self.frame],
                                      -(self.centre_angle + 90))
            ox = math.cos(math.radians(self.centre_angle)) * 30
            oy = math.sin(math.radians(self.centre_angle)) * 30
            display.blit(img, (px + ox - img.get_width()  // 2,
                               py_ + oy - img.get_height() // 2))
        else:
            n, half = 14, self.SWEEP_ANGLE / 2
            prog  = min(1.0, self.frame / 8)
            alpha = int(230 * (1 - prog))
            for k in range(n):
                t   = k / (n - 1)
                ang = math.radians(self.centre_angle - half + self.SWEEP_ANGLE * t)
                r   = self.REACH * (0.5 + 0.5 * prog)
                ax  = px + math.cos(ang) * r
                ay  = py_ + math.sin(ang) * r
                s   = py.Surface((22, 22), py.SRCALPHA)
                py.draw.circle(s, (255, max(0, 220-int(alpha*.6)), 50, alpha), (11,11), 11)
                display.blit(s, (int(ax)-11, int(ay)-11))

        half = self.SWEEP_ANGLE / 2
        for enemy in enemies[:]:
            if id(enemy) in self.hit_enemies: continue
            ex = enemy.x + 32 - display_scroll[0]
            ey = enemy.y + 30 - display_scroll[1]
            dx, dy = ex - px, ey - py_
            d = math.hypot(dx, dy)
            if d > self.REACH or d == 0: continue
            diff = (math.degrees(math.atan2(dy, dx)) - self.centre_angle + 180) % 360 - 180
            if abs(diff) > half: continue

            dmg = self.DAMAGE * stats.damage_mult
            enemy.hp -= dmg
            self.hit_enemies.add(id(enemy))
            enemy.hit_flash = 12
            enemy.kb_vx = (dx/d) * 22
            enemy.kb_vy = (dy/d) * 22

            if enemy.hp <= 0 and enemy in enemies:
                death_sound.play()
                enemies.remove(enemy)
                stats.balance += int(enemy.MONEY_REWARD * stats.money_mult)
                stats.add_xp(enemy.XP_REWARD)
                stats.kills  += 1
                stats.lifesteal_roll()
                wx, wy = enemy.x + 32, enemy.y + 30
                if random.random() < 0.05: drops.append(Drop(wx, wy, 'heart'))
                if random.random() < 0.04: drops.append(Drop(wx, wy, 'ammo'))
                if random.random() < 0.02: chests.append(Chest(wx, wy))
        return not self.done


# =============================================================================
# PLAYER
# =============================================================================
class Player(py.sprite.Sprite):
    SWORD_COOLDOWN = 40

    def __init__(self):
        super().__init__()
        raw = py.image.load(sp("player", "player_sprite.png")).convert_alpha()
        self.base_image = py.transform.smoothscale(
            raw, (int(200*player_size), int(260*player_size)))
        self.image     = self.base_image
        self.screen_cx = player_start_x
        self.screen_cy = player_start_y
        self.pos  = (self.screen_cx, self.screen_cy)
        self.rect = self.image.get_rect(center=self.pos)
        self.speed          = PLAYER_SPEED
        self.mouse_coordinates = [0, 0]
        self.angle          = 0
        self.shoot_cooldown = 0
        self.weapon         = 1
        self.sword_cooldown = 0
        self.barrel_x = self.screen_cx
        self.barrel_y = self.screen_cy
        self.mag_size     = 20
        self.mag_ammo     = self.mag_size
        self.reserve_ammo = 180
        self.reloading    = False
        self.reload_timer = 0

    def reload_start(self):
        if not self.reloading and self.reserve_ammo > 0 and self.mag_ammo < self.mag_size:
            self.reloading    = True
            self.reload_timer = int(RELOAD_TIME * stats.reload_mult)
            if reload_sound_play: reload_sound_play()

    def reload_update(self):
        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                load = min(self.mag_size - self.mag_ammo, self.reserve_ammo)
                self.reserve_ammo -= load
                self.mag_ammo     += load
                self.reloading     = False

    def inputs(self, frozen=False):
        keys = py.key.get_pressed()
        self.mouse_coordinates = list(py.mouse.get_pos())
        if keys[py.K_1]: self.weapon = 1
        if keys[py.K_2]: self.weapon = 2
        if frozen: return

        vx = vy = 0
        if keys[py.K_a]: vx = -self.speed
        if keys[py.K_d]: vx =  self.speed
        if keys[py.K_w]: vy = -self.speed
        if keys[py.K_s]: vy =  self.speed
        if vx and vy: vx /= math.sqrt(2); vy /= math.sqrt(2)

        if vx:
            sx = 1 if vx > 0 else -1
            for _ in range(round(abs(vx))):
                display_scroll[0] += sx
                if tilemap.player_hits_wall(display_scroll):
                    display_scroll[0] -= sx; break
                for b in player_bullets: b.x -= sx

        if vy:
            sy = 1 if vy > 0 else -1
            for _ in range(round(abs(vy))):
                display_scroll[1] += sy
                if tilemap.player_hits_wall(display_scroll):
                    display_scroll[1] -= sy; break
                for b in player_bullets: b.y -= sy

        if keys[py.K_SPACE] or py.mouse.get_pressed()[0]:
            if self.weapon == 1: self._shoot()
            else:                self._swing_sword()

        if keys[py.K_r] and self.weapon == 1:
            self.reload_start()
        if keys[py.K_j]:
            enemies.append(SlimeEnemy.spawn_from_zones(wave_manager.current_wave))

    def _shoot(self):
        if self.reloading or self.mag_ammo <= 0:
            if self.mag_ammo <= 0 and self.reserve_ammo > 0: self.reload_start()
            return
        if self.shoot_cooldown == 0:
            self.shoot_cooldown = int(SHOT_COOLDOWN * upgrades.fire_rate_mult)
            dmg = stats.crit_roll(stats.damage_mult * upgrades.damage_boost)
            self._fire(self.angle, dmg)
            if upgrades.double_bullet:
                self._fire(self.angle+12, dmg); self._fire(self.angle-12, dmg)
            if upgrades.back_shot:  self._fire(self.angle+180, dmg)
            if upgrades.omni_shot:
                self._fire(self.angle+90, dmg); self._fire(self.angle+180, dmg)
                self._fire(self.angle+270, dmg)
            if not god_mode: self.mag_ammo -= 1
            bullet_sound.play()
            if self.mag_ammo == 0 and self.reserve_ammo > 0: self.reload_start()

    def _fire(self, angle, damage):
        player_bullets.append(
            Projectile(self.barrel_x, self.barrel_y, angle, fireball, damage))

    def _swing_sword(self):
        if self.sword_cooldown == 0:
            self.sword_cooldown = self.SWORD_COOLDOWN
            sword_swings.append(SwordSwing(self.angle))

    def player_rotation(self):
        dx = self.mouse_coordinates[0] - self.screen_cx
        dy = self.mouse_coordinates[1] - self.screen_cy
        self.angle = math.degrees(math.atan2(dy, dx))
        self.image = py.transform.rotate(self.base_image, -self.angle)
        self.rect  = self.image.get_rect(center=(self.screen_cx, self.screen_cy))
        self.pos   = (self.screen_cx, self.screen_cy)

    def render(self):
        display.blit(self.image, self.rect)

        ang_rad = math.radians(self.angle)
        fwd_x, fwd_y     =  math.cos(ang_rad),  math.sin(ang_rad)
        right_x, right_y = -fwd_y, fwd_x

        if self.weapon == 1 and hand_gun:
            hx = self.screen_cx + fwd_x*22 + right_x*30
            hy = self.screen_cy + fwd_y*22 + right_y*30
            rotated = py.transform.rotate(hand_gun, -self.angle)
            display.blit(rotated, (hx - rotated.get_width()//2,
                                   hy - rotated.get_height()//2))
            self.barrel_x = hx + fwd_x * 20
            self.barrel_y = hy + fwd_y * 20
        else:
            self.barrel_x = self.screen_cx
            self.barrel_y = self.screen_cy

        if self.weapon == 2 and hand_sword and self.sword_cooldown == 0:
            SWORD_ROT_OFFSET = 0
            hx = self.screen_cx + fwd_x*62 + right_x*48
            hy = self.screen_cy + fwd_y*62 + right_y*48
            rotated = py.transform.rotate(hand_sword, -self.angle + SWORD_ROT_OFFSET)
            display.blit(rotated, (hx - rotated.get_width()//2,
                                   hy - rotated.get_height()//2))

        if upgrades and upgrades.regen_shielded:
            surf = py.Surface((100, 100), py.SRCALPHA)
            py.draw.circle(surf, (80, 200, 255, 55),  (50, 50), 48)
            py.draw.circle(surf, (120, 220, 255, 200), (50, 50), 48, width=3)
            display.blit(surf, (self.screen_cx-50, self.screen_cy-50))

    def draw_crosshair(self):
        mx, my = self.mouse_coordinates
        display.blit(crosshair, (mx - crosshair.get_width()/2,
                                 my - crosshair.get_height()/2))

    def draw_weapon_hud(self):
        sw, sh = display.get_width(), display.get_height()
        pw, ph = 230, 88
        px_ = sw - pw - 14
        py_ = sh - ph - 50

        panel = py.Surface((pw, ph), py.SRCALPHA)
        py.draw.rect(panel, (10, 10, 30, 185),  (0, 0, pw, ph), border_radius=8)
        py.draw.rect(panel, (70, 70, 110, 210), (0, 0, pw, ph), width=2, border_radius=8)
        display.blit(panel, (px_, py_))

        for wi, (lbl, wid) in enumerate([('[1] Gun',1),('[2] Sword',2)]):
            col = (255, 200, 50) if self.weapon == wid else (90, 90, 90)
            display.blit(tiny_font.render(lbl, False, col), (px_+10+wi*108, py_+6))
        ul_x = px_+10 if self.weapon == 1 else px_+118
        py.draw.line(display, (255,200,50), (ul_x, py_+22), (ul_x+95, py_+22), 2)

        if self.weapon == 1:
            if self.reloading:
                rl = my_font.render('RELOADING', False, (255,200,0))
                display.blit(rl, (px_+pw//2-rl.get_width()//2, py_+30))
                ratio = 1 - self.reload_timer/RELOAD_TIME
                py.draw.rect(display, (55,55,55), (px_+10, py_+64, pw-20, 12), border_radius=4)
                py.draw.rect(display, (0,200,100), (px_+10, py_+64, int((pw-20)*ratio), 12), border_radius=4)
            else:
                col = (200,50,50) if self.mag_ammo==0 else (220,160,0) if self.mag_ammo<=5 else (255,255,255)
                big = wave_font.render(str(self.mag_ammo), True, col)
                display.blit(big, (px_+12, py_+28))
                display.blit(my_font.render('│', False, (100,100,100)), (px_+82, py_+38))
                display.blit(my_font.render(str(self.reserve_ammo), False, (160,160,160)), (px_+100, py_+42))
                display.blit(tiny_font.render('[R] reload', False, (80,80,80)),
                             (px_+pw//2-tiny_font.size('[R] reload')[0]//2, py_+ph-18))
        else:
            ready = self.sword_cooldown == 0
            lbl   = my_font.render('READY' if ready else 'SWING', False,
                                   (50,220,50) if ready else (220,180,50))
            display.blit(lbl, (px_+pw//2-lbl.get_width()//2, py_+30))
            ratio = 1 - self.sword_cooldown/self.SWORD_COOLDOWN
            py.draw.rect(display, (55,55,55), (px_+10, py_+64, pw-20, 12), border_radius=4)
            py.draw.rect(display, (50,200,50) if ready else (200,160,40),
                         (px_+10, py_+64, int((pw-20)*ratio), 12), border_radius=4)

    def main(self, frozen=False):
        self.inputs(frozen)
        self.player_rotation()
        self.render()
        self.draw_crosshair()
        if not frozen:
            self.reload_update()
            if self.shoot_cooldown > 0: self.shoot_cooldown -= 1
            if self.sword_cooldown > 0: self.sword_cooldown -= 1
        self.draw_weapon_hud()


# =============================================================================
# PLAYER STATS
# =============================================================================
class PlayerStats:
    LEVEL_UP_OPTIONS = [
        {'id': 'heart',      'name': '+1 Heart',      'desc': 'Gain a heart slot (max 6)'},
        {'id': 'damage',     'name': 'Dmg +30%',      'desc': 'All bullets hit harder'},
        {'id': 'lifesteal',  'name': 'Lifesteal',     'desc': '+5% chance to heal on kill'},
        {'id': 'dodge',      'name': 'Dodge +5%',     'desc': 'Avoid damage (cap 60%)'},
        {'id': 'money',      'name': 'Coins +10%',    'desc': 'More coins per kill'},
        {'id': 'speed',      'name': 'Speed +5%',     'desc': 'Move faster (stacks)'},
        {'id': 'ammo_refill','name': 'Ammo Cache',    'desc': '+40% max ammo to reserve'},
        {'id': 'crit',       'name': 'Crit +10%',     'desc': '10% chance for 3x damage'},
        {'id': 'fast_reload','name': 'Quick Reload',  'desc': 'Reload 20% faster (stacks)'},
        {'id': 'lucky',      'name': 'Lucky',         'desc': '+50% heart/ammo drop chance'},
        {'id': 'hp_regen',   'name': 'Regen',         'desc': 'Slowly recover half-hearts'},
    ]

    def __init__(self):
        cfg = difficulty_cfg()
        start_h = cfg['start_hearts']
        self.health = start_h * 2; self.tot_hearts = start_h; self.max_hearts = start_h
        self.half = False; self.full_hearts = start_h; self.empty_hearts = 0
        self.damage_cooldown = HIT_COOLDOWN
        self.money_sprite = py.transform.scale_by(
            py.image.load(sp("ui", "money_sprite.png")), 0.2)
        self.balance = 0
        self.xp = 0; self.level = 1; self.xp_to_next_level = 100
        self.level_up_pending = False
        self.damage_mult = 1.0; self.lifesteal_stacks = 0
        self.dodge_chance = 0.0; self.money_mult = 1.0
        self.crit_chance   = 0.0
        self.drop_luck     = 1.0
        self.reload_mult   = 1.0
        self.regen_timer   = 0
        self.regen_stacks  = 0
        self.kills = 0; self.start_ticks = py.time.get_ticks()

    def add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
            self.level_up_pending = True

    def get_available_options(self):
        out = []
        for o in self.LEVEL_UP_OPTIONS:
            if o['id'] == 'dodge'      and self.dodge_chance    >= 0.6:  continue
            if o['id'] == 'heart'      and self.max_hearts       >= 6:   continue
            if o['id'] == 'lifesteal'  and self.lifesteal_stacks >= 10:  continue
            if o['id'] == 'crit'       and self.crit_chance      >= 0.5: continue
            if o['id'] == 'fast_reload'and self.reload_mult      <= 0.3: continue
            if o['id'] == 'regen'      and self.regen_stacks     >= 5:   continue
            out.append(o)
        return out

    def apply_upgrade(self, uid):
        if   uid == 'heart'      and self.max_hearts < 6:
            self.max_hearts += 1; self.tot_hearts = self.max_hearts
            self.health = min(self.health+2, self.max_hearts*2)
        elif uid == 'damage':      self.damage_mult  *= 1.3
        elif uid == 'lifesteal':   self.lifesteal_stacks = min(self.lifesteal_stacks+1, 10)
        elif uid == 'dodge':       self.dodge_chance = min(self.dodge_chance+0.05, 0.60)
        elif uid == 'money':       self.money_mult  *= 1.1
        elif uid == 'speed':       player.speed = min(player.speed*1.05, PLAYER_SPEED*2.0)
        elif uid == 'ammo_refill':
            bonus = int(player.mag_size * 9 * 0.4)
            player.reserve_ammo = min(player.reserve_ammo + bonus, player.mag_size * 9)
        elif uid == 'crit':        self.crit_chance = min(self.crit_chance + 0.10, 0.5)
        elif uid == 'fast_reload':
            self.reload_mult = max(0.3, self.reload_mult * 0.8)
        elif uid == 'lucky':       self.drop_luck = min(self.drop_luck * 1.5, 5.0)
        elif uid == 'hp_regen':
            self.regen_stacks = min(self.regen_stacks + 1, 5)

    def lifesteal_roll(self):
        if self.lifesteal_stacks > 0 and random.random() < self.lifesteal_stacks*0.05:
            self.health = min(self.health+1, self.max_hearts*2)

    def crit_roll(self, base_damage):
        if self.crit_chance > 0 and random.random() < self.crit_chance:
            return base_damage * 3.0
        return base_damage

    def time_alive_seconds(self):
        return (py.time.get_ticks() - self.start_ticks) // 1000

    def update(self):
        if self.health > 0: self.health_calc(); self.health_display()
        self.money_track(); self.xp_bar_display()
        if self.damage_cooldown > 0: self.damage_cooldown -= 1
        if self.regen_stacks > 0 and self.health < self.max_hearts * 2:
            self.regen_timer += 1
            interval = max(60, 1800 // self.regen_stacks)
            if self.regen_timer >= interval:
                self.regen_timer = 0
                self.health = min(self.health + 1, self.max_hearts * 2)
        if god_mode:
            gm = small_font.render('⚡ GOD MODE', False, (255,80,80))
            display.blit(gm, (display.get_width()//2 - gm.get_width()//2, 10))
        # Draw difficulty badge
        dcfg = difficulty_cfg()
        if selected_difficulty != 'Normal':
            dl = tiny_font.render(f'[{dcfg["label"]}]', False, dcfg['col'])
            display.blit(dl, (display.get_width() - dl.get_width() - 10,
                               display.get_height() - 60))

    def xp_bar_display(self):
        sw, sh = display.get_width(), display.get_height()
        bw, bh, bx, by = sw-40, 20, 20, sh-40
        py.draw.rect(display, (30,30,30), (bx, by, bw, bh), border_radius=5)
        py.draw.rect(display, (100,0,220),
                     (bx, by, int(bw*self.xp/self.xp_to_next_level), bh), border_radius=5)
        py.draw.rect(display, (200,200,200), (bx, by, bw, bh), width=2, border_radius=5)
        display.blit(my_font.render(f'LVL {self.level}', False, (255,255,255)), (bx, by-35))

    def health_display(self):
        x = 0
        for _ in range(self.full_hearts):  display.blit(full_heart,  (x,0)); x+=150
        if self.half:                       display.blit(half_heart,  (x,0)); x+=150
        for _ in range(self.empty_hearts): display.blit(empty_heart, (x,0)); x+=150

    def health_calc(self):
        if self.health % 2 == 1:
            self.full_hearts = self.health//2; self.half = True
            self.empty_hearts = self.tot_hearts - self.full_hearts - 1
        else:
            self.full_hearts = self.health//2; self.half = False
            self.empty_hearts = self.tot_hearts - self.full_hearts

    def money_track(self):
        display.blit(self.money_sprite, (-10,132))
        display.blit(my_font.render(str(self.balance), False, (255,215,0)), (85,160))


# =============================================================================
# PLAYER UPGRADES
# =============================================================================
class PlayerUpgrades:
    SHOP_ITEMS = [
        {'id':'splash',        'name':'Explosive Rounds',
         'desc':'Bullets explode on impact',          'base_cost':300, 'cost_inc':0,   'max':1},
        {'id':'double_bullet', 'name':'Double Shot',
         'desc':'Fire 2 extra bullets per shot',      'base_cost':250, 'cost_inc':0,   'max':1},
        {'id':'fire_rate',     'name':'Rapid Fire',
         'desc':'Fire rate +20% per purchase',        'base_cost':200, 'cost_inc':150, 'max':4},
        {'id':'ammo_size',     'name':'Ammo Size',
         'desc':'Mag size +20% per purchase',         'base_cost':200, 'cost_inc':100, 'max':4},
        {'id':'damage_boost',  'name':'Dmg Boost',
         'desc':'Bullet damage +20% per purchase',    'base_cost':250, 'cost_inc':150, 'max':5},
        {'id':'shield',        'name':'Shield',
         'desc':'Absorb one hit completely',          'base_cost':500, 'cost_inc':0,   'max':1},
        {'id':'bouncing',      'name':'Bounce Bullets',
         'desc':'Bullets bounce off walls (3x)',      'base_cost':5000,'cost_inc':0,   'max':1},
        {'id':'piercing',      'name':'Piercing Shot',
         'desc':'Bullets pass through enemies',       'base_cost':400, 'cost_inc':0,   'max':1},
        {'id':'freeze',        'name':'Freeze Rounds',
         'desc':'10% chance to slow enemy 3s',        'base_cost':350, 'cost_inc':200, 'max':3},
        {'id':'homing',        'name':'Homing Bullets',
         'desc':'Bullets curve toward enemies',       'base_cost':800, 'cost_inc':0,   'max':1},
    ]

    def __init__(self):
        self.splash = False; self.double_bullet = False
        self.fire_rate_mult = 1.0; self.damage_boost = 1.0
        self.shield_active  = False; self.bouncing_bullets = False
        self.piercing_shots = False; self.freeze_chance = 0.0
        self.homing_bullets = False
        self.slow_enemies = False; self.regen_shield = False
        self.regen_shielded = False; self.regen_shield_cd = 0
        self.regen_shield_timer = 0
        self.back_shot = False; self.omni_shot = False
        self.ghost_rounds      = False
        self.bullet_knockback  = False
        self.xp_boost          = False
        self.coin_magnet       = False
        self.counts: dict = {}

    def get_cost(self, iid):
        it = next(i for i in self.SHOP_ITEMS if i['id']==iid)
        return it['base_cost'] + it['cost_inc'] * self.counts.get(iid, 0)

    def is_maxed(self, iid):
        it = next(i for i in self.SHOP_ITEMS if i['id']==iid)
        return self.counts.get(iid, 0) >= it['max']

    def apply(self, iid):
        self.counts[iid] = self.counts.get(iid, 0) + 1
        if   iid == 'splash':        self.splash = True
        elif iid == 'double_bullet': self.double_bullet = True
        elif iid == 'fire_rate':     self.fire_rate_mult = max(0.3, self.fire_rate_mult*0.8)
        elif iid == 'ammo_size':     player.mag_size = math.ceil(player.mag_size*1.2)
        elif iid == 'damage_boost':  self.damage_boost *= 1.2
        elif iid == 'shield':        self.shield_active = True
        elif iid == 'bouncing':      self.bouncing_bullets = True
        elif iid == 'piercing':      self.piercing_shots   = True
        elif iid == 'freeze':        self.freeze_chance    = min(self.freeze_chance + 0.10, 0.5)
        elif iid == 'homing':        self.homing_bullets   = True

    def apply_chest_upgrade(self, uid):
        if   uid == 'back_shot':    self.back_shot    = True
        elif uid == 'omni_shot':    self.omni_shot    = True
        elif uid == 'slow_enemies': self.slow_enemies = True
        elif uid == 'ghost_rounds':    self.ghost_rounds    = True
        elif uid == 'bullet_knockback':self.bullet_knockback= True
        elif uid == 'xp_boost':        self.xp_boost        = True
        elif uid == 'coin_magnet':     self.coin_magnet     = True
        elif uid == 'extra_life':
            stats.health = min(stats.health + 2, stats.max_hearts * 2)
        elif uid == 'regen_shield':
            self.regen_shield = True; self.regen_shield_cd = 480
        elif uid == 'speed_boost':
            player.speed = min(player.speed * 1.30, PLAYER_SPEED * 2.5)
            stats.max_hearts = 1; stats.tot_hearts = 1
            stats.health = 2
        elif uid == 'berserker':
            stats.damage_mult  *= 2.0
            stats.dodge_chance  = 0.0

    def regen_shield_update(self):
        if not self.regen_shield: return
        if self.regen_shielded:
            self.regen_shield_timer -= 1
            if self.regen_shield_timer <= 0:
                self.regen_shielded = False; self.regen_shield_cd = 480
        else:
            self.regen_shield_cd -= 1
            if self.regen_shield_cd <= 0:
                self.regen_shielded = True; self.regen_shield_timer = 180


# =============================================================================
# PROJECTILE  (with bouncing)
# =============================================================================
class Projectile(py.sprite.Sprite):
    def __init__(self, x, y, angle, image, damage=1.0):
        super().__init__()
        self.angle    = angle
        self.damage   = damage
        self._base    = image
        self.image    = py.transform.rotozoom(image, (-angle-90), BULLET_SCALE)
        self.rect     = self.image.get_rect()
        self.x, self.y = float(x), float(y)
        self.x_v = math.cos(math.radians(angle)) * BULLET_SPEED
        self.y_v = math.sin(math.radians(angle)) * BULLET_SPEED
        self.spawn_time   = py.time.get_ticks()
        self.wall_timer   = 0
        self.bounces_left = BOUNCE_LIMIT if (upgrades and upgrades.bouncing_bullets) else 0

    def _update_rotation(self):
        cur_angle = math.degrees(math.atan2(self.y_v, self.x_v))
        self.image = py.transform.rotozoom(self._base, (-cur_angle - 90), BULLET_SCALE)
        cx, cy = self.x + self.rect.width/2, self.y + self.rect.height/2
        self.rect = self.image.get_rect()
        self.x = cx - self.rect.width/2
        self.y = cy - self.rect.height/2

    def _centre(self):
        return (self.x + self.image.get_width()/2,
                self.y + self.image.get_height()/2)

    def _try_bounce(self):
        cx, cy = self._centre()
        hit_x = tilemap.screen_point_in_wall(cx + self.x_v, cy, display_scroll)
        hit_y = tilemap.screen_point_in_wall(cx, cy + self.y_v, display_scroll)
        if hit_x: self.x_v = -self.x_v
        if hit_y: self.y_v = -self.y_v
        if not hit_x and not hit_y:
            self.x_v = -self.x_v; self.y_v = -self.y_v
        self.bounces_left -= 1
        self.wall_timer    = 0

    def update(self):
        homing_active = upgrades and upgrades.homing_bullets and enemies
        if homing_active:
            cx_, cy_ = self._centre()
            nearest = min(enemies,
                          key=lambda e: math.hypot(e.x+32-cx_-display_scroll[0],
                                                   e.y+30-cy_-display_scroll[1]),
                          default=None)
            if nearest:
                ex = nearest.x + 32 - display_scroll[0] - cx_
                ey = nearest.y + 30 - display_scroll[1] - cy_
                d  = math.hypot(ex, ey)
                if d > 0:
                    self.x_v += (ex/d) * 0.8
                    self.y_v += (ey/d) * 0.8
                    spd = math.hypot(self.x_v, self.y_v)
                    cap = BULLET_SPEED * 1.2
                    if spd > cap:
                        self.x_v = self.x_v/spd*cap; self.y_v = self.y_v/spd*cap
            self._update_rotation()

        self.x += self.x_v; self.y += self.y_v
        self.rect.x = int(self.x); self.rect.y = int(self.y)

        cx, cy = self._centre()
        if tilemap.screen_point_in_wall(cx, cy, display_scroll):
            if upgrades and upgrades.ghost_rounds:
                pass
            else:
                self.wall_timer += 1
                if self.bounces_left > 0:
                    self._try_bounce()
                elif self.wall_timer >= WALL_GRACE:
                    if self in player_bullets: player_bullets.remove(self)
                    return
        else:
            self.wall_timer = 0

        if py.time.get_ticks() - self.spawn_time > BULLET_LIFETIME:
            if self in player_bullets: player_bullets.remove(self)
            return

        display.blit(self.image, (self.x, self.y))

    def render(self):
        display.blit(self.image, (self.x, self.y))


# =============================================================================
# EXPLOSION
# =============================================================================
class Explosion:
    TICKS_PER_FRAME = 3
    def __init__(self, wx, wy):
        self.wx, self.wy = wx, wy
        self.frame_idx = 0; self.tick = 0
        self.use_fallback = len(explosion_frames) == 0

    def update(self):
        self.tick += 1
        if self.tick % self.TICKS_PER_FRAME == 0: self.frame_idx += 1
        sx = int(self.wx - display_scroll[0])
        sy = int(self.wy - display_scroll[1])
        if self.use_fallback:
            r = min(55, self.frame_idx*6); alpha = max(0, 220 - self.frame_idx*20)
            if alpha <= 0 or self.frame_idx > 12: return False
            s = py.Surface((r*2+2, r*2+2), py.SRCALPHA)
            py.draw.circle(s, (255,140,0,alpha), (r+1,r+1), r)
            display.blit(s, (sx-r, sy-r))
        else:
            if self.frame_idx >= len(explosion_frames): return False
            img = explosion_frames[self.frame_idx]
            display.blit(img, (sx-img.get_width()//2, sy-img.get_height()//2))
        return True


# =============================================================================
# DROP
# =============================================================================
class Drop:
    def __init__(self, wx, wy, drop_type):
        self.wx, self.wy = wx, wy
        self.drop_type = drop_type
        self.lifetime  = DROP_LIFETIME
        self.bob       = random.uniform(0, math.pi*2)

    def update(self):
        self.lifetime -= 1; self.bob += 0.08
        bob_y = math.sin(self.bob) * 5
        sx = int(self.wx - display_scroll[0])
        sy = int(self.wy - display_scroll[1] + bob_y)
        r   = 14
        col = (220,50,50) if self.drop_type == 'heart' else (220,200,0)
        py.draw.circle(display, col,           (sx, sy), r)
        py.draw.circle(display, (255,255,255), (sx, sy), r, width=2)
        icon = tiny_font.render('♥' if self.drop_type == 'heart' else 'A',
                                False, (255,255,255))
        display.blit(icon, (sx-icon.get_width()//2, sy-icon.get_height()//2))
        if math.hypot(sx-player.screen_cx, sy-player.screen_cy) < DROP_RADIUS:
            if self.drop_type == 'heart':
                stats.health = min(stats.health+1, stats.max_hearts*2)
            else:
                player.reserve_ammo = player.mag_size * 9
            return False
        return self.lifetime > 0


# =============================================================================
# SLIME ENEMY
# =============================================================================
class SlimeEnemy(py.sprite.Sprite):
    XP_REWARD    = 20
    MONEY_REWARD = 50

    def __init__(self, x, y, wave=1):
        super().__init__()
        self.x, self.y = float(x), float(y)
        self.animation_count = 0; self.reset_offset = 0
        self.offset_x = random.randrange(-150, 150)
        self.offset_y = random.randrange(-150, 150)
        self.rect   = py.Rect(self.x, self.y, 64, 60)
        cfg = difficulty_cfg()
        self.max_hp = float(1+wave) * cfg['enemy_hp_mult']
        self.hp = self.max_hp
        self._speed_mult = cfg['enemy_speed_mult']
        self.hit_flash = 0
        self.kb_vx = 0.0; self.kb_vy = 0.0

    @classmethod
    def spawn_from_zones(cls, wave):
        zones = active_map_cfg['spawn_zones']
        random.shuffle(zones)
        for col, row in zones:
            wx = col * TILE_SIZE + MAP_OFFSET_X + display_scroll[0] + random.randint(-96, 96)
            wy = row * TILE_SIZE + MAP_OFFSET_Y + display_scroll[1] + random.randint(-96, 96)
            d = math.hypot(wx - player.screen_cx, wy - player.screen_cy)
            if d < 350: continue
            if tilemap.valid_world_pos(wx, wy):
                return cls(wx, wy, wave)
        for _ in range(40):
            angle = random.uniform(0, 2*math.pi)
            dist  = random.uniform(500, 700)
            wx = player.pos[0] + math.cos(angle)*dist
            wy = player.pos[1] + math.sin(angle)*dist
            if tilemap.valid_world_pos(wx, wy):
                return cls(wx, wy, wave)
        return cls(wx, wy, wave)

    def draw_health_bar(self):
        sx = self.x-display_scroll[0]; sy = self.y-display_scroll[1]
        bw, bh = 64, 8
        py.draw.rect(display, (80,0,0),      (sx, sy-14, bw, bh))
        py.draw.rect(display, (220,0,0),     (sx, sy-14, int(bw*max(0,self.hp/self.max_hp)), bh))
        py.draw.rect(display, (255,255,255), (sx, sy-14, bw, bh), width=1)

    def main(self, frozen=False):
        self.animation_count = (self.animation_count+1) % 16
        if not frozen:
            if self.reset_offset == 0:
                self.offset_x = random.randrange(-150,150)
                self.offset_y = random.randrange(-150,150)
                self.reset_offset = random.randrange(120,150)
            else:
                self.reset_offset -= 1
            self.enemy_movement()

        sx = self.x-display_scroll[0]; sy = self.y-display_scroll[1]
        frame_img = slime_frames[self.animation_count//4]
        display.blit(frame_img, (sx, sy))
        if self.hit_flash > 0:
            self.hit_flash -= 1
            fl = py.Surface(frame_img.get_size(), py.SRCALPHA)
            fl.fill((255,30,30,160)); display.blit(fl, (sx, sy))
        self.draw_health_bar()
        self.rect.topleft = (sx, sy)

    def enemy_movement(self):
        if abs(self.kb_vx) > 0.2 or abs(self.kb_vy) > 0.2:
            sx_s = 1 if self.kb_vx > 0 else -1
            for _ in range(int(abs(self.kb_vx))):
                if not tilemap.enemy_hits_wall(self.x+sx_s, self.y): self.x += sx_s
                else: self.kb_vx = 0.0; break
            sy_s = 1 if self.kb_vy > 0 else -1
            for _ in range(int(abs(self.kb_vy))):
                if not tilemap.enemy_hits_wall(self.x, self.y+sy_s): self.y += sy_s
                else: self.kb_vy = 0.0; break
            self.kb_vx *= 0.78; self.kb_vy *= 0.78
            if abs(self.kb_vx) < 0.2: self.kb_vx = 0.0
            if abs(self.kb_vy) < 0.2: self.kb_vy = 0.0
            return

        sx = self.x-display_scroll[0]; sy = self.y-display_scroll[1]
        tx = player.pos[0]+self.offset_x; ty = player.pos[1]+self.offset_y
        base_spd = (SLIME_SPEED//2) if upgrades.slow_enemies else SLIME_SPEED
        spd = max(1, int(base_spd * self._speed_mult))
        mx  = spd if tx>sx else (-spd if tx<sx else 0)
        my_ = spd if ty>sy else (-spd if ty<sy else 0)
        if mx:
            nx = self.x+mx
            if not tilemap.enemy_hits_wall(nx, self.y): self.x = nx
        if my_:
            ny = self.y+my_
            if not tilemap.enemy_hits_wall(self.x, ny): self.y = ny


# =============================================================================
# CHEST
# =============================================================================
class Chest:
    OPEN_RADIUS = 60
    try:
        _img_closed = py.transform.scale(
            py.image.load(sp("chest","chest_closed.png")).convert_alpha(), (48,40))
        _img_open   = py.transform.scale(
            py.image.load(sp("chest","chest_opened.png")).convert_alpha(), (48,40))
    except Exception:
        _img_closed = _img_open = None

    def __init__(self, wx, wy):
        self.wx, self.wy = wx, wy
        self.opened = False
        # wave number when this chest was opened (set on open)
        self.opened_wave = None

    def update(self):
        """Returns True while the chest should stay alive."""
        sx = int(self.wx-display_scroll[0]); sy = int(self.wy-display_scroll[1])

        # Draw
        if self._img_closed:
            display.blit(self._img_open if self.opened else self._img_closed, (sx-24,sy-20))
        else:
            col = (120,80,20) if not self.opened else (200,160,60)
            py.draw.rect(display, col,           (sx-22,sy-18,44,36), border_radius=5)
            py.draw.rect(display, (220,180,80),  (sx-22,sy-18,44,36), width=2, border_radius=5)
            display.blit(tiny_font.render('CHEST',False,(255,230,130)),
                         (sx-tiny_font.size('CHEST')[0]//2, sy-30))

        if not self.opened:
            if math.hypot(sx-player.screen_cx, sy-player.screen_cy) < self.OPEN_RADIUS:
                self.opened = True
                self.opened_wave = wave_manager.current_wave if wave_manager else 0
                chest_menu.open_chest()
            return True   # not yet opened — always alive

        # Opened: linger for CHEST_LINGER_WAVES additional waves
        current = wave_manager.current_wave if wave_manager else 0
        return current <= self.opened_wave + CHEST_LINGER_WAVES


# =============================================================================
# CHEST MENU
# =============================================================================
class ChestMenu:
    ALL_REWARDS = [
        {'id':'back_shot',        'name':'Back Shot',       'desc':'Also fire backwards',           'sacrifice':False},
        {'id':'omni_shot',        'name':'Omni Shot',       'desc':'Fire in all 4 directions',      'sacrifice':False},
        {'id':'slow_enemies',     'name':'Slow Curse',      'desc':'Enemies move at half speed',    'sacrifice':False},
        {'id':'regen_shield',     'name':'Regen Shield',    'desc':'Shield every 8s, lasts 3s',     'sacrifice':False},
        {'id':'ghost_rounds',     'name':'Ghost Rounds',    'desc':'Bullets pass through walls',    'sacrifice':False},
        {'id':'extra_life',       'name':'Extra Life',      'desc':'Restore 1 full heart now',      'sacrifice':False},
        {'id':'bullet_knockback', 'name':'Bullet Knockback','desc':'5% chance to blast enemies back','sacrifice':False},
        {'id':'xp_boost',         'name':'XP Surge',        'desc':'+50% XP gained from kills',     'sacrifice':False},
        {'id':'coin_magnet',      'name':'Coin Magnet',     'desc':'Nearby drops pulled to player', 'sacrifice':False},
        {'id':'speed_boost',      'name':'Speed Surge',     'desc':'+30% speed / reduced to 1♥',   'sacrifice':True},
        {'id':'berserker',        'name':'Berserker Pact',  'desc':'2x damage / lose all dodge',    'sacrifice':True},
    ]

    def __init__(self):
        self.visible = False; self.choices = []

    def open_chest(self):
        pool = list(self.ALL_REWARDS)
        if stats.health <= 2:
            pool = [r for r in pool if not r['sacrifice']]
        if not upgrades.back_shot:
            pool = [r for r in pool if r['id'] != 'omni_shot']
        owned_ids = set()
        for attr in ('back_shot','omni_shot','slow_enemies','regen_shield',
                     'ghost_rounds','bullet_knockback','xp_boost','coin_magnet'):
            if getattr(upgrades, attr, False): owned_ids.add(attr)
        pool = [r for r in pool if r['id'] not in owned_ids or r['sacrifice']]
        if not pool: return
        free_pool    = [r for r in pool if not r['sacrifice']]
        sac_pool     = [r for r in pool if r['sacrifice']]
        if free_pool:
            pick = [random.choice(free_pool)]
            remaining = [r for r in pool if r is not pick[0]]
            if remaining:
                pick.append(random.choice(remaining))
            self.choices = pick
        else:
            self.choices = random.sample(pool, min(2, len(pool)))
        self.visible = True

    def update(self): pass

    def draw(self):
        if not self.visible: return
        sw, sh = display.get_width(), display.get_height()
        ov = py.Surface((sw,sh), py.SRCALPHA); ov.fill((0,0,0,175)); display.blit(ov,(0,0))
        t = wave_font.render('CHEST OPENED!', True, (220,175,50))
        display.blit(t, (sw//2-t.get_width()//2, sh//5))
        sub = my_font.render('Choose your reward:', False, (210,210,170))
        display.blit(sub, (sw//2-sub.get_width()//2, sh//5+68))

        cw, ch = 300, 175; total_w = len(self.choices)*cw+(len(self.choices)-1)*50
        start_x = sw//2-total_w//2; cy_ = sh//2-ch//2+20; mpos = py.mouse.get_pos()

        for i, reward in enumerate(self.choices):
            cx_ = start_x + i*(cw+50)
            rect = py.Rect(cx_, cy_, cw, ch); hov = rect.collidepoint(mpos)
            can_take = not reward['sacrifice'] or stats.health > 2
            bc = (130,130,130) if not can_take else \
                 ((255,100,100) if reward['sacrifice'] else ((255,210,50) if hov else (160,130,40)))
            bg = (70,35,10) if reward['sacrifice'] else ((55,45,15) if hov else (35,28,8))
            py.draw.rect(display, bg,  rect, border_radius=14)
            py.draw.rect(display, bc,  rect, width=3, border_radius=14)
            n = my_font.render(reward['name'], False,
                               (150,150,150) if not can_take else (255,230,140))
            d = small_font.render(reward['desc'], False, (190,175,130))
            display.blit(n, (cx_+cw//2-n.get_width()//2, cy_+36))
            display.blit(d, (cx_+cw//2-d.get_width()//2, cy_+80))
            if reward['sacrifice']:
                label = '⚠ Need > 1 heart' if not can_take else '⚠ Costs 1 heart'
                col   = (130,60,60) if not can_take else (255,100,100)
                cl = small_font.render(label, False, col)
                display.blit(cl, (cx_+cw//2-cl.get_width()//2, cy_+120))
            if hov and mouse_clicked and can_take:
                if reward['sacrifice']:
                    stats.health -= 2
                    upgrades.apply_chest_upgrade(reward['id'])
                else:
                    upgrades.apply_chest_upgrade(reward['id'])
                self.visible = False; break

        skip_r = py.Rect(sw//2-80, cy_+ch+18, 160, 40)
        skip_h = skip_r.collidepoint(mpos)
        py.draw.rect(display, (55,40,25) if skip_h else (35,25,15), skip_r, border_radius=8)
        py.draw.rect(display, (180,130,50), skip_r, width=2, border_radius=8)
        sk = small_font.render('Skip / Close', False, (200,170,90))
        display.blit(sk, (skip_r.centerx-sk.get_width()//2, skip_r.centery-sk.get_height()//2))
        if skip_h and mouse_clicked:
            self.visible = False


# =============================================================================
# SLIME KING
# =============================================================================
class SlimeKing:
    MAX_HP_BASE   = 300
    SPEED         = 2
    SPAWN_INTERVAL = 420
    RING_RADIUS   = 70
    SIZE          = (192, 180)

    def __init__(self, wx, wy, wave):
        self.x, self.y    = float(wx), float(wy)
        cfg = difficulty_cfg()
        self.max_hp       = (self.MAX_HP_BASE + (wave - 10) * 40) * cfg['enemy_hp_mult']
        self.hp           = float(self.max_hp)
        self.alive        = True
        self.animation_count = 0
        self.spawn_timer  = self.SPAWN_INTERVAL
        self.ring_pulse   = 0.0
        self.offset_x = 0; self.offset_y = 0
        self.reset_offset = 0
        self.kb_vx = 0.0; self.kb_vy = 0.0
        self.frames = [py.transform.scale(f, self.SIZE) for f in slime_frames]
        w, h = self.SIZE
        self.rect = py.Rect(self.x, self.y, w, h)

    def main(self, frozen=False):
        self.animation_count = (self.animation_count + 1) % 16
        self.ring_pulse = (self.ring_pulse + 0.06) % (2 * math.pi)

        if not frozen:
            if self.reset_offset == 0:
                self.offset_x = random.randrange(-80, 80)
                self.offset_y = random.randrange(-80, 80)
                self.reset_offset = random.randrange(180, 240)
            else:
                self.reset_offset -= 1
            self._move()
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                self.spawn_timer = self.SPAWN_INTERVAL
                self._spawn_minions()

        self._draw(frozen)

    def _move(self):
        sx = self.x - display_scroll[0]; sy = self.y - display_scroll[1]
        tx = player.pos[0] + self.offset_x; ty = player.pos[1] + self.offset_y
        spd = self.SPEED

        if abs(self.kb_vx) > 0.2 or abs(self.kb_vy) > 0.2:
            for sign, attr, coord in [(1 if self.kb_vx>0 else -1, 'kb_vx', 'x'),
                                      (1 if self.kb_vy>0 else -1, 'kb_vy', 'y')]:
                for _ in range(int(abs(getattr(self, attr)))):
                    nx = self.x + (sign if attr=='kb_vx' else 0)
                    ny = self.y + (sign if attr=='kb_vy' else 0)
                    if not tilemap.enemy_hits_wall(nx, ny, w=self.SIZE[0], h=self.SIZE[1], m=16):
                        self.x, self.y = nx, ny
                    else:
                        setattr(self, attr, 0.0); break
            self.kb_vx *= 0.82; self.kb_vy *= 0.82
            if abs(self.kb_vx) < 0.2: self.kb_vx = 0.0
            if abs(self.kb_vy) < 0.2: self.kb_vy = 0.0
            return

        mx  = spd if tx > sx else (-spd if tx < sx else 0)
        my_ = spd if ty > sy else (-spd if ty < sy else 0)
        if mx:
            nx = self.x + mx
            if not tilemap.enemy_hits_wall(nx, self.y, w=self.SIZE[0], h=self.SIZE[1], m=16):
                self.x = nx
        if my_:
            ny = self.y + my_
            if not tilemap.enemy_hits_wall(self.x, ny, w=self.SIZE[0], h=self.SIZE[1], m=16):
                self.y = ny

    def _spawn_minions(self):
        for _ in range(2):
            angle = random.uniform(0, 2 * math.pi)
            dist  = random.uniform(self.RING_RADIUS + 20, self.RING_RADIUS + 80)
            wx = self.x + math.cos(angle) * dist
            wy = self.y + math.sin(angle) * dist
            if tilemap.valid_world_pos(wx, wy):
                enemies.append(SlimeEnemy(wx, wy, wave=wave_manager.current_wave))

    def _draw(self, frozen):
        sx = int(self.x - display_scroll[0])
        sy = int(self.y - display_scroll[1])
        pulse = 0.5 + 0.5 * math.sin(self.ring_pulse)
        ring_r = int(self.RING_RADIUS + 12 * pulse)
        cx_ = sx + self.SIZE[0] // 2; cy_ = sy + self.SIZE[1] // 2

        for layer_r, alpha in [(ring_r+16, 50), (ring_r+8, 90), (ring_r, 160)]:
            glow = py.Surface((layer_r*2, layer_r*2), py.SRCALPHA)
            g_col = (int(80+pulse*120), int(220-pulse*60), 60, alpha)
            py.draw.circle(glow, g_col, (layer_r, layer_r), layer_r, width=8)
            display.blit(glow, (cx_-layer_r, cy_-layer_r))

        frame = self.frames[self.animation_count // 4]
        display.blit(frame, (sx, sy))
        lbl = small_font.render('SLIME KING', False, (80, 255, 80))
        display.blit(lbl, (cx_ - lbl.get_width()//2, sy - 28))
        self.rect.topleft = (sx, sy)

    def draw_boss_bar(self, y_offset=0):
        sw = display.get_width()
        bx, by, bw, bh = 60, 14 + y_offset, sw - 120, 28
        py.draw.rect(display, (60, 0, 0),    (bx, by, bw, bh))
        ratio = max(0.0, self.hp / self.max_hp)
        py.draw.rect(display, (220, 20, 20), (bx, by, int(bw * ratio), bh))
        t = my_font.render(f'SLIME KING   {int(self.hp)} / {int(self.max_hp)}',
                           False, (255, 200, 200))
        display.blit(t, (sw//2 - t.get_width()//2, by + bh//2 - t.get_height()//2))

    def on_death(self):
        self.alive = False
        death_sound.play()
        stats.balance += int(500 * stats.money_mult)
        stats.add_xp(500)
        stats.kills += 1
        chests.append(Chest(self.x + self.SIZE[0]//2, self.y + self.SIZE[1]//2))


# =============================================================================
# BOMB EXPLOSION
# =============================================================================
class BombExplosion:
    TICKS_PER_FRAME = 2
    RADIUS          = 130

    def __init__(self, wx, wy):
        self.wx, self.wy = wx, wy
        self.frame = 0
        self.tick  = 0
        self._dealt_damage = False

    def update(self):
        self.tick += 1
        if self.tick % self.TICKS_PER_FRAME == 0:
            self.frame += 1

        sx = int(self.wx - display_scroll[0])
        sy = int(self.wy - display_scroll[1])

        if not self._dealt_damage:
            self._dealt_damage = True
            self._apply_damage(sx, sy)

        if bomb_explosion_frames:
            if self.frame >= len(bomb_explosion_frames):
                return False
            img = bomb_explosion_frames[self.frame]
            display.blit(img, (sx - img.get_width()  // 2,
                               sy - img.get_height() // 2))
        else:
            r     = min(self.RADIUS, self.frame * 18)
            alpha = max(0, 240 - self.frame * 28)
            if alpha <= 0:
                return False
            surf = py.Surface((r * 2 + 2, r * 2 + 2), py.SRCALPHA)
            py.draw.circle(surf, (255, 120, 0, alpha), (r + 1, r + 1), r)
            py.draw.circle(surf, (255, 230, 60, max(0, alpha - 60)),
                           (r + 1, r + 1), r // 2)
            display.blit(surf, (sx - r, sy - r))
        return True

    def _apply_damage(self, sx, sy):
        d_player = math.hypot(sx - player.screen_cx, sy - player.screen_cy)
        if d_player < self.RADIUS and not god_mode and stats.damage_cooldown == 0:
            stats.health -= 2
            stats.damage_cooldown = HIT_COOLDOWN * 2
            if life_lost_sound_play: life_lost_sound_play()
            if stats.health <= 0:
                if game_over_sound_play: game_over_sound_play()
                death_screen.show()

        for enemy in enemies[:]:
            ex = enemy.x + 32 - display_scroll[0]
            ey = enemy.y + 30 - display_scroll[1]
            if math.hypot(ex - sx, ey - sy) < self.RADIUS:
                enemy.hp -= 4.0
                if enemy.hp <= 0 and enemy in enemies:
                    death_sound.play()
                    enemies.remove(enemy)
                    stats.balance += int(enemy.MONEY_REWARD * stats.money_mult)
                    stats.add_xp(enemy.XP_REWARD)
                    stats.kills  += 1

        for bomb in bomb_enemies[:]:
            if bomb.state != 'exploding':
                bx = bomb.x + 26 - display_scroll[0]
                by = bomb.y + 26 - display_scroll[1]
                if math.hypot(bx - sx, by - sy) < self.RADIUS:
                    bomb.explode()


# =============================================================================
# BOMB ENEMY
# =============================================================================
class BombEnemy:
    SLOW_SPEED       = max(1, SLIME_SPEED - 2)
    FAST_SPEED       = int(SLIME_SPEED * 2.2)
    DETECTION_RADIUS = 220
    FUSE_RADIUS      = 55
    XP_REWARD        = 30
    MONEY_REWARD     = 40

    def __init__(self, x, y, wave=1):
        self.x, self.y = float(x), float(y)
        self.wave      = wave
        cfg = difficulty_cfg()
        self.max_hp    = float(max(1, wave // 2)) * cfg['enemy_hp_mult']
        self.hp        = self.max_hp
        self.state     = 'roam'
        self.anim_tick = 0; self.anim_frame = 0
        self.offset_x  = random.randrange(-100, 100)
        self.offset_y  = random.randrange(-100, 100)
        self.offset_timer = 0
        self.flash_tick = 0
        self.kb_vx = 0.0; self.kb_vy = 0.0
        self.rect = py.Rect(self.x, self.y, 52, 52)

    @classmethod
    def spawn_near_player(cls, wave):
        for _ in range(60):
            angle = random.uniform(0, 2 * math.pi)
            dist  = random.uniform(500, 750)
            wx = player.pos[0] + math.cos(angle) * dist
            wy = player.pos[1] + math.sin(angle) * dist
            if tilemap.valid_world_pos(wx, wy):
                return cls(wx, wy, wave)
        return cls(wx, wy, wave)

    def explode(self):
        if self.state == 'exploding':
            return
        self.state = 'exploding'
        if explosion_sound_play: explosion_sound_play()
        bomb_explosions.append(BombExplosion(self.x + 26, self.y + 26))
        if self in bomb_enemies:
            bomb_enemies.remove(self)

    def main(self, frozen=False):
        sx = self.x - display_scroll[0]
        sy = self.y - display_scroll[1]
        d_player = math.hypot(sx - player.screen_cx, sy - player.screen_cy)

        if not frozen:
            if abs(self.kb_vx) > 0.2 or abs(self.kb_vy) > 0.2:
                sign_x = 1 if self.kb_vx > 0 else -1
                for _ in range(int(abs(self.kb_vx))):
                    if not tilemap.enemy_hits_wall(self.x + sign_x, self.y):
                        self.x += sign_x
                    else: self.kb_vx = 0.0; break
                sign_y = 1 if self.kb_vy > 0 else -1
                for _ in range(int(abs(self.kb_vy))):
                    if not tilemap.enemy_hits_wall(self.x, self.y + sign_y):
                        self.y += sign_y
                    else: self.kb_vy = 0.0; break
                self.kb_vx *= 0.78; self.kb_vy *= 0.78
                if abs(self.kb_vx) < 0.2: self.kb_vx = 0.0
                if abs(self.kb_vy) < 0.2: self.kb_vy = 0.0
            else:
                if d_player <= self.FUSE_RADIUS:
                    self.explode(); return
                elif d_player <= self.DETECTION_RADIUS:
                    self.state = 'chase'
                else:
                    self.state = 'roam'
                self._move(d_player, sx, sy)

        self.anim_tick = (self.anim_tick + 1) % 8
        if self.anim_tick == 0:
            self.anim_frame = (self.anim_frame + 1) % max(1, len(bomb_frames))

        self.flash_tick = (self.flash_tick + 1) % 20
        sx = self.x - display_scroll[0]
        sy = self.y - display_scroll[1]

        if bomb_frames:
            frame = bomb_frames[self.anim_frame % len(bomb_frames)]
            display.blit(frame, (sx, sy))
            if self.state == 'chase' and self.flash_tick < 10:
                fl = py.Surface(frame.get_size(), py.SRCALPHA)
                fl.fill((255, 50, 50, 140))
                display.blit(fl, (sx, sy))
        else:
            col = (200, 50, 50) if (self.state == 'chase' and self.flash_tick < 10) \
                  else (40, 40, 40)
            py.draw.circle(display, col, (int(sx + 26), int(sy + 26)), 22)
            py.draw.circle(display, (255, 255, 255), (int(sx + 26), int(sy + 26)), 22, 2)

        if self.max_hp > 1:
            bw = 52
            py.draw.rect(display, (80, 0, 0),   (sx, sy - 12, bw, 7))
            py.draw.rect(display, (220, 0, 0),
                         (sx, sy - 12, int(bw * max(0, self.hp / self.max_hp)), 7))

        self.rect.topleft = (int(sx), int(sy))

    def _move(self, d_player, sx, sy):
        spd = self.FAST_SPEED if self.state == 'chase' else self.SLOW_SPEED

        if self.state == 'chase':
            dx = player.screen_cx - sx
            dy = player.screen_cy - sy
            dist = math.hypot(dx, dy) or 1
            mx  = int(spd * dx / dist)
            my_ = int(spd * dy / dist)
        else:
            if self.offset_timer <= 0:
                self.offset_x     = random.randrange(-100, 100)
                self.offset_y     = random.randrange(-100, 100)
                self.offset_timer = random.randrange(120, 200)
            else:
                self.offset_timer -= 1
            tx = player.screen_cx + self.offset_x
            ty = player.screen_cy + self.offset_y
            mx  = spd if tx > sx else (-spd if tx < sx else 0)
            my_ = spd if ty > sy else (-spd if ty < sy else 0)

        if mx:
            nx = self.x + mx
            if not tilemap.enemy_hits_wall(nx, self.y, w=52, h=52): self.x = nx
        if my_:
            ny = self.y + my_
            if not tilemap.enemy_hits_wall(self.x, ny, w=52, h=52): self.y = ny


# =============================================================================
# THROWN BOMB
# =============================================================================
class ThrownBomb:
    SPEED   = 7
    TIMEOUT = 240

    def __init__(self, wx, wy, target_x, target_y):
        self.x, self.y = float(wx), float(wy)
        dx = target_x - wx; dy = target_y - wy
        d = math.hypot(dx, dy) or 1
        self.vx = dx / d * self.SPEED
        self.vy = dy / d * self.SPEED
        self.timer = self.TIMEOUT
        self.anim_tick = 0; self.anim_frame = 0
        self.rect = py.Rect(self.x, self.y, 36, 36)

    def update(self):
        self.timer -= 1
        self.x += self.vx; self.y += self.vy
        sx = self.x - display_scroll[0]
        sy = self.y - display_scroll[1]

        self.anim_tick = (self.anim_tick + 1) % 6
        if self.anim_tick == 0:
            self.anim_frame = (self.anim_frame + 1) % max(1, len(bomb_frames))

        if bomb_frames:
            f = bomb_frames[self.anim_frame % len(bomb_frames)]
            f_scaled = py.transform.scale(f, (36, 36))
            display.blit(f_scaled, (sx, sy))
        else:
            py.draw.circle(display, (30, 30, 30), (int(sx+18), int(sy+18)), 14)
            py.draw.circle(display, (255,200,0),  (int(sx+18), int(sy+18)), 14, 2)

        self.rect.topleft = (int(sx), int(sy))

        cx_ = sx + 18; cy_ = sy + 18
        if tilemap.screen_point_in_wall(cx_, cy_, display_scroll):
            self._explode(); return False

        if self.rect.colliderect(player.rect):
            self._explode(); return False

        if self.timer <= 0:
            self._explode(); return False

        return True

    def _explode(self):
        bomb_explosions.append(BombExplosion(self.x + 18, self.y + 18))
        if explosion_sound_play: explosion_sound_play()


# =============================================================================
# BOMB KING
# =============================================================================
class BombKing:
    MAX_HP_BASE    = 250
    SPEED          = 2
    SIZE           = (200, 200)
    THROW_INTERVAL = 280
    THROW_COUNT    = 3

    def __init__(self, wx, wy, wave):
        self.x, self.y = float(wx), float(wy)
        cfg = difficulty_cfg()
        self.max_hp    = (self.MAX_HP_BASE + (wave - 20) * 35) * cfg['enemy_hp_mult']
        self.hp        = float(self.max_hp)
        self.alive     = True
        self.anim_tick = 0; self.anim_frame = 0
        self.throw_timer  = self.THROW_INTERVAL
        self.ring_pulse   = math.pi
        self.offset_x = 0; self.offset_y = 0; self.reset_offset = 0
        self.kb_vx = 0.0; self.kb_vy = 0.0
        self.frames = [py.transform.scale(f, self.SIZE) for f in bomb_frames] \
                      if bomb_frames else []
        self.rect = py.Rect(self.x, self.y, *self.SIZE)

    def main(self, frozen=False):
        self.ring_pulse = (self.ring_pulse + 0.07) % (2 * math.pi)
        self.anim_tick  = (self.anim_tick + 1) % 8
        if self.anim_tick == 0:
            self.anim_frame = (self.anim_frame + 1) % max(1, len(self.frames))

        if not frozen:
            self._move()
            self.throw_timer -= 1
            if self.throw_timer <= 0:
                self.throw_timer = self.THROW_INTERVAL
                self._throw_bombs()

        self._draw()

    def _move(self):
        if abs(self.kb_vx) > 0.2 or abs(self.kb_vy) > 0.2:
            sx_s = 1 if self.kb_vx > 0 else -1
            for _ in range(int(abs(self.kb_vx))):
                if not tilemap.enemy_hits_wall(self.x+sx_s, self.y, w=self.SIZE[0], h=self.SIZE[1], m=16):
                    self.x += sx_s
                else: self.kb_vx = 0.0; break
            sy_s = 1 if self.kb_vy > 0 else -1
            for _ in range(int(abs(self.kb_vy))):
                if not tilemap.enemy_hits_wall(self.x, self.y+sy_s, w=self.SIZE[0], h=self.SIZE[1], m=16):
                    self.y += sy_s
                else: self.kb_vy = 0.0; break
            self.kb_vx *= 0.82; self.kb_vy *= 0.82
            if abs(self.kb_vx) < 0.2: self.kb_vx = 0.0
            if abs(self.kb_vy) < 0.2: self.kb_vy = 0.0
            return

        if self.reset_offset == 0:
            self.offset_x = random.randrange(-60, 60)
            self.offset_y = random.randrange(-60, 60)
            self.reset_offset = random.randrange(200, 280)
        else:
            self.reset_offset -= 1

        sx = self.x - display_scroll[0]; sy = self.y - display_scroll[1]
        tx = player.pos[0] + self.offset_x; ty = player.pos[1] + self.offset_y
        spd = self.SPEED
        mx  = spd if tx > sx else (-spd if tx < sx else 0)
        my_ = spd if ty > sy else (-spd if ty < sy else 0)
        if mx:
            nx = self.x + mx
            if not tilemap.enemy_hits_wall(nx, self.y, w=self.SIZE[0], h=self.SIZE[1], m=16): self.x = nx
        if my_:
            ny = self.y + my_
            if not tilemap.enemy_hits_wall(self.x, ny, w=self.SIZE[0], h=self.SIZE[1], m=16): self.y = ny

    def _throw_bombs(self):
        cx_ = self.x + self.SIZE[0]//2
        cy_ = self.y + self.SIZE[1]//2
        px_ = player.pos[0]; py__ = player.pos[1]
        base_ang = math.atan2(py__ - cy_, px_ - cx_)
        spread = math.radians(25)
        offsets = [0] if self.THROW_COUNT == 1 else \
                  [spread*(i - (self.THROW_COUNT-1)/2) for i in range(self.THROW_COUNT)]
        for off in offsets:
            ang  = base_ang + off
            thrown_bombs.append(ThrownBomb(cx_, cy_, px_, py__))

    def _draw(self):
        sx = int(self.x - display_scroll[0])
        sy = int(self.y - display_scroll[1])
        cx_ = sx + self.SIZE[0]//2; cy_ = sy + self.SIZE[1]//2

        pulse = 0.5 + 0.5 * math.sin(self.ring_pulse)
        ring_r = int(80 + 14 * pulse)
        for layer_r, alpha in [(ring_r+18, 50), (ring_r+9, 90), (ring_r, 165)]:
            glow = py.Surface((layer_r*2, layer_r*2), py.SRCALPHA)
            g_col = (int(200+pulse*55), int(80+pulse*40), 0, alpha)
            py.draw.circle(glow, g_col, (layer_r, layer_r), layer_r, width=9)
            display.blit(glow, (cx_-layer_r, cy_-layer_r))

        if self.frames:
            display.blit(self.frames[self.anim_frame % len(self.frames)], (sx, sy))
        else:
            py.draw.circle(display, (30, 20, 0),   (cx_, cy_), 80)
            py.draw.circle(display, (200, 100, 0), (cx_, cy_), 80, width=5)

        lbl = small_font.render('BOMB KING', False, (255, 140, 0))
        display.blit(lbl, (cx_ - lbl.get_width()//2, sy - 28))
        self.rect.topleft = (sx, sy)

    def draw_boss_bar(self, y_offset=0):
        sw = display.get_width()
        bx, by, bw, bh = 60, 14 + y_offset, sw - 120, 28
        py.draw.rect(display, (50, 25, 0),   (bx, by, bw, bh))
        ratio = max(0.0, self.hp / self.max_hp)
        py.draw.rect(display, (220, 100, 0), (bx, by, int(bw * ratio), bh))
        t = my_font.render(f'BOMB KING   {int(self.hp)} / {int(self.max_hp)}',
                           False, (255, 200, 130))
        display.blit(t, (sw//2 - t.get_width()//2, by + bh//2 - t.get_height()//2))

    def on_death(self):
        self.alive = False
        death_sound.play()
        stats.balance += int(600 * stats.money_mult)
        stats.add_xp(600); stats.kills += 1
        cx_ = self.x + self.SIZE[0]//2
        cy_ = self.y + self.SIZE[1]//2
        bomb_explosions.append(BombExplosion(cx_, cy_))
        for i in range(8):
            ang = (2 * math.pi / 8) * i
            r   = 90
            bomb_explosions.append(
                BombExplosion(cx_ + math.cos(ang)*r, cy_ + math.sin(ang)*r))
        if explosion_sound_play: explosion_sound_play()
        chests.append(Chest(cx_, cy_))


# =============================================================================
# WAVE MANAGER
# =============================================================================
class WaveManager:
    BETWEEN_DELAY = 180; BANNER_DURATION = 120

    def __init__(self):
        self.current_wave = 0; self.wave_active = False
        self.between_wave_timer = 0; self.banner_timer = 0

    def enemy_count(self): return 3 + (self.current_wave-1)*2

    def start_next_wave(self):
        self.current_wave += 1; self.wave_active = True
        self.banner_timer  = self.BANNER_DURATION
        for _ in range(self.enemy_count()):
            enemies.append(SlimeEnemy.spawn_from_zones(self.current_wave))
        if self.current_wave >= 5:
            n_bombs = 1 + (self.current_wave - 5) // 3
            for _ in range(min(n_bombs, 6)):
                bomb_enemies.append(BombEnemy.spawn_near_player(self.current_wave))
        if self.current_wave % 5 == 0: shop.spawn()
        if self.current_wave % 10 == 0 and active_map_cfg['csv'] != 'test_level.csv':
            self._spawn_boss()

    def _spawn_boss(self):
        global slime_king, bomb_king
        zones = active_map_cfg['spawn_zones']
        shuffled = random.sample(zones, len(zones))

        for col, row in shuffled:
            wx = col * TILE_SIZE + MAP_OFFSET_X + display_scroll[0]
            wy = row * TILE_SIZE + MAP_OFFSET_Y + display_scroll[1]
            if math.hypot(wx - player.screen_cx, wy - player.screen_cy) > 600:
                if tilemap.valid_world_pos(wx, wy):
                    slime_king = SlimeKing(wx, wy, self.current_wave); break
        else:
            slime_king = SlimeKing(player.pos[0]+700, player.pos[1]+700, self.current_wave)

        if self.current_wave >= 20:
            for col, row in reversed(shuffled):
                wx = col * TILE_SIZE + MAP_OFFSET_X + display_scroll[0]
                wy = row * TILE_SIZE + MAP_OFFSET_Y + display_scroll[1]
                if math.hypot(wx - player.screen_cx, wy - player.screen_cy) > 600:
                    if tilemap.valid_world_pos(wx, wy) and \
                       (slime_king is None or math.hypot(wx-slime_king.x, wy-slime_king.y) > 200):
                        bomb_king = BombKing(wx, wy, self.current_wave); return
            bomb_king = BombKing(player.pos[0]-700, player.pos[1]-700, self.current_wave)

    def update(self):
        boss_done  = (slime_king is None or not slime_king.alive) and \
                     (bomb_king  is None or not bomb_king.alive)
        bombs_done = len(bomb_enemies) == 0
        if self.wave_active:
            if not enemies and boss_done and bombs_done:
                self.wave_active = False; self.between_wave_timer = self.BETWEEN_DELAY
        else:
            if self.between_wave_timer > 0: self.between_wave_timer -= 1
            else: self.start_next_wave()
        self.draw_wave_info()

    def draw_wave_info(self):
        sw, sh = display.get_width(), display.get_height()
        if self.banner_timer > 0:
            self.banner_timer -= 1
            b = wave_font.render(f'Wave {self.current_wave}', True, (255,220,0))
            display.blit(b, (sw//2-b.get_width()//2, sh//2-b.get_height()//2))
        info = my_font.render(f'Wave: {self.current_wave}  Enemies: {len(enemies)}',
                              False, (255,255,255))
        display.blit(info, (sw-info.get_width()-10, 10))
        if not self.wave_active and self.between_wave_timer > 0:
            secs = math.ceil(self.between_wave_timer/60)
            cd = my_font.render(f'Next wave in {secs}...', False, (200,200,200))
            display.blit(cd, (sw//2-cd.get_width()//2, sh//2+50))


# =============================================================================
# SHOP
# =============================================================================
class Shop:
    def __init__(self):
        self.active = False; self.open = False
        self.world_x = 0.0; self.world_y = 0.0; self.timer = 0
        self.current_items  = []
        self.reroll_cost    = 200
        self.reroll_count   = 0

    def spawn(self):
        if self.active: return
        MIN_DIST = 400
        player_wx = player.screen_cx + display_scroll[0]
        player_wy = player.screen_cy + display_scroll[1]
        candidates = []
        for r in range(tilemap.rows):
            for c in range(tilemap.cols):
                if tilemap.grid[r][c] != 0:
                    continue
                wx = c * TILE_SIZE + MAP_OFFSET_X + TILE_SIZE // 2
                wy = r * TILE_SIZE + MAP_OFFSET_Y + TILE_SIZE // 2
                if math.hypot(wx - player_wx, wy - player_wy) >= MIN_DIST:
                    candidates.append((wx, wy))
        if not candidates:
            return
        self.world_x, self.world_y = random.choice(candidates)
        self.active = True; self.open = False; self.timer = 0

    def _pick_items(self):
        pool = [it for it in PlayerUpgrades.SHOP_ITEMS
                if not upgrades.is_maxed(it['id'])]
        self.current_items = random.sample(pool, min(3, len(pool)))

    def _spos(self):
        return (self.world_x-display_scroll[0], self.world_y-display_scroll[1])

    def _dist(self):
        sx, sy = self._spos()
        return math.hypot(sx-player.screen_cx, sy-player.screen_cy)

    def update(self):
        if not self.active: return
        sx, sy = self._spos()
        py.draw.rect(display, (0,70,170),  (sx-28,sy-28,56,56))
        py.draw.rect(display, (0,170,255), (sx-28,sy-28,56,56), width=3)
        lbl = small_font.render('SHOP', False, (255,255,255))
        display.blit(lbl, (sx-lbl.get_width()//2, sy-50))

        if self._dist() < SHOP_RANGE and not self.open:
            self.open = True; self.timer = SHOP_DURATION
            self.reroll_cost = 200; self.reroll_count = 0
            self._pick_items()

        if self.open:
            self.timer -= 1
            self._draw_bubble(); self._enforce_bubble()
            self._draw_timer_bar(sx, sy); self._draw_ui()
            if self.timer <= 0: self.open = False; self.active = False
        else:
            self._draw_arrow()

    def _draw_bubble(self):
        px, py_ = player.screen_cx, player.screen_cy
        surf = py.Surface((BUBBLE_RADIUS*2, BUBBLE_RADIUS*2), py.SRCALPHA)
        py.draw.circle(surf, (100,150,255,45),  (BUBBLE_RADIUS,BUBBLE_RADIUS), BUBBLE_RADIUS)
        py.draw.circle(surf, (150,210,255,140), (BUBBLE_RADIUS,BUBBLE_RADIUS), BUBBLE_RADIUS, width=3)
        display.blit(surf, (px-BUBBLE_RADIUS, py_-BUBBLE_RADIUS))

    def _enforce_bubble(self):
        px, py_ = player.screen_cx, player.screen_cy
        for e in enemies:
            ex = e.x-display_scroll[0]; ey = e.y-display_scroll[1]
            dx, dy = ex-px, ey-py_; d = math.hypot(dx, dy)
            if 0 < d < BUBBLE_RADIUS:
                e.x = display_scroll[0]+px  + (dx/d)*BUBBLE_RADIUS
                e.y = display_scroll[1]+py_ + (dy/d)*BUBBLE_RADIUS

    def _draw_timer_bar(self, sx, sy):
        bw = 80
        py.draw.rect(display, (50,50,50), (sx-40,sy-62,bw,9))
        py.draw.rect(display, (0,210,90), (sx-40,sy-62,int(bw*max(0,self.timer/SHOP_DURATION)),9))

    def _draw_arrow(self):
        px, py_ = player.screen_cx, player.screen_cy
        sx, sy  = self._spos(); dx, dy = sx-px, sy-py_
        d = math.hypot(dx, dy)
        if d == 0: return
        nx, ny = dx/d, dy/d; ang = math.atan2(ny, nx)
        ax, ay = px+nx*160, py_+ny*160
        tip   = (ax, ay)
        left  = (ax-math.cos(ang-0.5)*18, ay-math.sin(ang-0.5)*18)
        right = (ax-math.cos(ang+0.5)*18, ay-math.sin(ang+0.5)*18)
        py.draw.polygon(display, (0,225,175), [tip,left,right])
        py.draw.line(display,    (0,225,175), (px,py_), (ax,ay), 2)
        dl = small_font.render(f'SHOP  {int(d)}px', False, (0,225,175))
        display.blit(dl, (int(ax)-dl.get_width()//2, int(ay)-26))

    def _draw_ui(self):
        sw, sh = display.get_width(), display.get_height()
        pw, ph = 660, 440; px_ = sw//2-pw//2; py_ = sh//2-ph//2

        panel = py.Surface((pw,ph), py.SRCALPHA)
        py.draw.rect(panel, (8,18,40,215),   (0,0,pw,ph), border_radius=14)
        py.draw.rect(panel, (0,140,255,255), (0,0,pw,ph), width=3, border_radius=14)
        display.blit(panel, (px_,py_))

        t = wave_font.render('SHOP', True, (0,200,255))
        display.blit(t, (sw//2-t.get_width()//2, py_+8))
        display.blit(my_font.render(f'Coins: {stats.balance}', False, (255,215,0)),
                     (px_+20, py_+76))

        mpos = py.mouse.get_pos(); item_y = py_+118

        for item in self.current_items:
            maxed = upgrades.is_maxed(item['id']); cost = upgrades.get_cost(item['id'])
            affordable = stats.balance >= cost; can_buy = not maxed and affordable
            irect = py.Rect(px_+16, item_y, pw-32, 60)
            bg = (38,38,38) if maxed else \
                 ((38,74,140) if irect.collidepoint(mpos) and can_buy else
                  ((18,38,78) if can_buy else (30,30,38)))
            py.draw.rect(display, bg,           irect, border_radius=8)
            py.draw.rect(display, (0,90,200),   irect, width=2, border_radius=8)
            nc = (255,255,255) if can_buy else (110,110,110)
            cnt = upgrades.counts.get(item['id'],0); mxv = item['max']
            lbl = item['name'] + (f'  [{cnt}/{mxv}]' if mxv > 1 else '')
            display.blit(my_font.render(lbl, False, nc),      (irect.x+10, irect.y+6))
            display.blit(small_font.render(item['desc'], False, (170,170,170)),
                         (irect.x+10, irect.y+34))
            status = small_font.render('OWNED', False, (0,210,90)) if maxed else \
                     small_font.render(f'{cost} coins', False,
                                       (255,215,0) if affordable else (180,55,55))
            display.blit(status, (irect.right-status.get_width()-12, irect.y+22))
            if irect.collidepoint(mpos) and mouse_clicked and can_buy:
                stats.balance -= cost; upgrades.apply(item['id'])
            item_y += 68

        rr_cost  = self.reroll_cost
        can_rr   = stats.balance >= rr_cost and len(self.current_items) > 0
        rr_rect  = py.Rect(px_+16, item_y+4, pw-32, 44)
        rr_hov   = rr_rect.collidepoint(mpos)
        rr_bg    = (60,40,10) if can_rr and rr_hov else ((40,28,6) if can_rr else (35,35,35))
        py.draw.rect(display, rr_bg,           rr_rect, border_radius=8)
        py.draw.rect(display, (220,160,0),     rr_rect, width=2, border_radius=8)
        rr_lbl = my_font.render(f'Reroll  —  {rr_cost} coins', False,
                                (255,210,80) if can_rr else (100,100,100))
        display.blit(rr_lbl, (rr_rect.centerx-rr_lbl.get_width()//2,
                               rr_rect.centery-rr_lbl.get_height()//2))
        if rr_rect.collidepoint(mpos) and mouse_clicked and can_rr:
            stats.balance    -= rr_cost
            self.reroll_cost *= 2
            self.reroll_count += 1
            self.timer        = SHOP_DURATION
            self._pick_items()

        secs = math.ceil(self.timer/60)
        t2 = small_font.render(f'Shop closes in {secs}s', False, (160,160,160))
        display.blit(t2, (sw//2-t2.get_width()//2, py_+ph-28))

        cr = py.Rect(px_+pw-44, py_+8, 36, 36)
        py.draw.rect(display, (160,30,30) if cr.collidepoint(mpos) else (100,20,20),
                     cr, border_radius=6)
        py.draw.rect(display, (255,80,80), cr, width=2, border_radius=6)
        xl = my_font.render('✕', False, (255,255,255))
        display.blit(xl, (cr.centerx-xl.get_width()//2, cr.centery-xl.get_height()//2))
        if cr.collidepoint(mpos) and mouse_clicked:
            self.open = False; self.active = False


# =============================================================================
# LEVEL-UP MENU
# =============================================================================
class LevelUpMenu:
    AUTO_FRAMES = 10*60
    def __init__(self):
        self.choices = []; self.visible = False; self.timer = 0

    def show(self):
        av = stats.get_available_options()
        if not av: return
        self.choices = random.sample(av, min(2, len(av)))
        self.visible = True; self.timer = self.AUTO_FRAMES

    def draw(self):
        if not self.visible: return
        self.timer -= 1
        if self.timer <= 0:
            stats.apply_upgrade(random.choice(self.choices)['id'])
            self.visible = False; return

        sw, sh = display.get_width(), display.get_height()
        ov = py.Surface((sw,sh), py.SRCALPHA); ov.fill((0,0,0,165)); display.blit(ov,(0,0))
        t = wave_font.render('LEVEL UP!', True, (255,220,0))
        display.blit(t, (sw//2-t.get_width()//2, sh//4-55))
        sub = my_font.render('Choose an upgrade:', False, (210,210,210))
        display.blit(sub, (sw//2-sub.get_width()//2, sh//4+8))

        bw = 300; ratio = self.timer/self.AUTO_FRAMES
        py.draw.rect(display, (55,55,55),  (sw//2-bw//2, sh//4+44, bw, 10), border_radius=4)
        py.draw.rect(display, (0,200,120), (sw//2-bw//2, sh//4+44, int(bw*ratio), 10), border_radius=4)
        secs = math.ceil(self.timer/60)
        tl = tiny_font.render(f'Auto in {secs}s', False, (130,130,130))
        display.blit(tl, (sw//2-tl.get_width()//2, sh//4+60))

        cw, ch = 260, 155; total_w = len(self.choices)*cw+(len(self.choices)-1)*40
        sx = sw//2-total_w//2; cy_ = sh//2-ch//2; mpos = py.mouse.get_pos()

        for i, choice in enumerate(self.choices):
            cx_ = sx+i*(cw+40); rect = py.Rect(cx_,cy_,cw,ch); hov = rect.collidepoint(mpos)
            py.draw.rect(display, (48,78,128) if hov else (28,48,88), rect, border_radius=12)
            py.draw.rect(display, (255,215,50) if hov else (90,140,255), rect, width=3, border_radius=12)
            n = my_font.render(choice['name'], False, (255,255,255))
            d = small_font.render(choice['desc'], False, (180,180,215))
            display.blit(n, (cx_+cw//2-n.get_width()//2, cy_+38))
            display.blit(d, (cx_+cw//2-d.get_width()//2, cy_+82))
            if hov and mouse_clicked:
                stats.apply_upgrade(choice['id']); self.visible = False; break


# =============================================================================
# DEATH SCREEN
# =============================================================================
class DeathScreen:
    def __init__(self):
        self.visible = False; self.is_new_highscore = False
        self.prev_best_wave = 0; self.final_time = 0; self.final_stats = {}

    def show(self):
        if self.visible: return
        self.visible    = True
        self.final_time = stats.time_alive_seconds()
        self.final_stats = {'wave': wave_manager.current_wave, 'time': self.final_time,
                            'money': stats.balance, 'kills': stats.kills, 'level': stats.level,
                            'difficulty': selected_difficulty}
        hs = load_highscore(active_map_cfg['csv'])
        self.prev_best_wave = hs.get('wave', 0)
        if wave_manager.current_wave > self.prev_best_wave and not god_mode:
            self.is_new_highscore = True
            save_highscore(active_map_cfg['csv'], self.final_stats)

    def draw(self):
        if not self.visible: return
        sw, sh = display.get_width(), display.get_height()
        ov = py.Surface((sw,sh), py.SRCALPHA); ov.fill((0,0,0,215)); display.blit(ov,(0,0))
        t = title_font.render('YOU DIED', True, (210,25,25))
        display.blit(t, (sw//2-t.get_width()//2, sh//8))
        ts = self.final_time; m, s = ts//60, ts%60; fs = self.final_stats
        lines = [f'Waves:  {fs["wave"]}', f'Time:  {m}m {s:02d}s',
                 f'Coins:  {fs["money"]}', f'Kills:  {fs["kills"]}',
                 f'Level:  {fs["level"]}']
        y = sh//3
        for line in lines:
            surf = my_font.render(line, False, (215,215,215))
            display.blit(surf, (sw//2-surf.get_width()//2, y)); y+=44
        hs_s = my_font.render('NEW HIGH SCORE!', False, (255,215,0)) \
               if self.is_new_highscore else \
               my_font.render(f'Best wave: {self.prev_best_wave}', False, (170,170,90))
        display.blit(hs_s, (sw//2-hs_s.get_width()//2, y+6))
        bw, bh = 220, 55; by_ = y+56
        r_rect = py.Rect(sw//2-bw-20, by_, bw, bh)
        q_rect = py.Rect(sw//2+20,    by_, bw, bh)
        mpos   = py.mouse.get_pos()
        for rect, label, bc in [(r_rect,'Play Again',(40,110,40)),(q_rect,'Main Menu',(80,60,10))]:
            col = tuple(min(255,c+45) for c in bc) if rect.collidepoint(mpos) else bc
            py.draw.rect(display, col,           rect, border_radius=10)
            py.draw.rect(display, (210,210,210), rect, width=2, border_radius=10)
            bs = my_font.render(label, False, (255,255,255))
            display.blit(bs, (rect.centerx-bs.get_width()//2, rect.centery-bs.get_height()//2))
            if rect.collidepoint(mpos) and mouse_clicked:
                global game_state
                if label == 'Play Again': game_state = 'pre_game'
                else:                     game_state = 'menu'


# =============================================================================
# PAUSE MENU  — FIX: options_from = 'paused' (not 'pause')
# =============================================================================
class PauseMenu:
    BUTTONS = ['Resume','Options','Quit to Menu','Quit Game']
    def draw(self):
        sw, sh = display.get_width(), display.get_height()
        ov = py.Surface((sw,sh), py.SRCALPHA); ov.fill((0,0,0,160)); display.blit(ov,(0,0))
        t = wave_font.render('PAUSED', True, (220,220,255))
        display.blit(t, (sw//2-t.get_width()//2, sh//5))
        bw, bh, gap = 300, 58, 18
        sy_ = sh//2 - (len(self.BUTTONS)*(bh+gap)-gap)//2; mpos = py.mouse.get_pos()
        for i, label in enumerate(self.BUTTONS):
            rect = py.Rect(sw//2-bw//2, sy_+i*(bh+gap), bw, bh); hov = rect.collidepoint(mpos)
            py.draw.rect(display, (60,90,160) if hov else (30,48,90),  rect, border_radius=10)
            py.draw.rect(display, (150,180,255) if hov else (80,110,200), rect, width=2, border_radius=10)
            ls = my_font.render(label, False, (255,255,255))
            display.blit(ls, (rect.centerx-ls.get_width()//2, rect.centery-ls.get_height()//2))
            if hov and mouse_clicked: self._handle(label)

    def _handle(self, label):
        global game_state, options_from
        if   label == 'Resume':       game_state = 'playing'
        elif label == 'Options':
            options_from = 'paused'   # ← FIX: was 'pause', must match the state key
            game_state = 'options'
        elif label == 'Quit to Menu': game_state = 'menu'
        elif label == 'Quit Game':    sys.exit()


# =============================================================================
# OPTIONS SCREEN
# =============================================================================
class OptionsScreen:
    def __init__(self):
        self.dragging = False; self.slider_x = 0; self.slider_y = 0; self.slider_w = 400

    def draw(self):
        global god_mode
        sw, sh = display.get_width(), display.get_height()
        display.fill((12,12,28))
        t = wave_font.render('OPTIONS', True, (200,220,255))
        display.blit(t, (sw//2-t.get_width()//2, sh//6))

        vl = my_font.render(f'Volume:  {int(master_volume*100)} %', False, (210,210,210))
        display.blit(vl, (sw//2-vl.get_width()//2, sh//2-70))
        self.slider_x = sw//2-self.slider_w//2; self.slider_y = sh//2-30
        sx, sy_, sw2 = self.slider_x, self.slider_y, self.slider_w
        py.draw.rect(display, (70,70,90),  (sx,sy_,sw2,10), border_radius=5)
        fill = int(master_volume*sw2)
        py.draw.rect(display, (0,160,255), (sx,sy_,fill,10), border_radius=5)
        hx, hy = sx+fill, sy_+5
        py.draw.circle(display, (255,255,255), (hx,hy), 14)
        py.draw.circle(display, (0,160,255),   (hx,hy), 14, width=2)

        cb_size = 28; cb_x = sw//2-140; cb_y = sh//2+30
        cb_rect = py.Rect(cb_x, cb_y, cb_size, cb_size); mpos = py.mouse.get_pos()
        py.draw.rect(display, (255,80,80) if god_mode else (30,30,50), cb_rect, border_radius=5)
        if god_mode:
            py.draw.lines(display, (255,255,255), False,
                          [(cb_x+5,cb_y+14),(cb_x+11,cb_y+21),(cb_x+23,cb_y+7)], 3)
        py.draw.rect(display, (255,80,80) if god_mode else (130,130,160), cb_rect, width=2, border_radius=5)
        gm_l = my_font.render('God Mode  (inf ammo, no dmg)', False,
                              (255,110,110) if god_mode else (190,190,210))
        display.blit(gm_l, (cb_x+cb_size+14, cb_y+2))
        if god_mode:
            w = tiny_font.render('⚠  Scores not saved in God Mode', False, (200,120,0))
            display.blit(w, (sw//2-w.get_width()//2, cb_y+38))
        if cb_rect.collidepoint(mpos) and mouse_clicked: god_mode = not god_mode

        hints = ['WASD — Move','SPACE — Shoot / Swing','R — Reload','ESC — Pause',
                 '1 — Gun    2 — Sword']
        for idx, hint in enumerate(hints):
            hs = small_font.render(hint, False, (130,130,155))
            display.blit(hs, (sw//2-hs.get_width()//2, sh*2//3+idx*30))

        bw, bh = 200, 54; brect = py.Rect(sw//2-bw//2, sh*5//6, bw, bh)
        hov = brect.collidepoint(mpos)
        py.draw.rect(display, (50,80,50) if hov else (30,50,30), brect, border_radius=10)
        py.draw.rect(display, (100,200,100), brect, width=2, border_radius=10)
        bs = my_font.render('Back', False, (255,255,255))
        display.blit(bs, (brect.centerx-bs.get_width()//2, brect.centery-bs.get_height()//2))
        if hov and mouse_clicked:
            global game_state; game_state = options_from

    def handle_event(self, event):
        sx, sy_, sw2 = self.slider_x, self.slider_y, self.slider_w
        hx = sx+int(master_volume*sw2); hy = sy_+5
        if event.type == py.MOUSEBUTTONDOWN:
            if math.hypot(event.pos[0]-hx, event.pos[1]-hy) < 16: self.dragging = True
        elif event.type == py.MOUSEBUTTONUP:   self.dragging = False
        elif event.type == py.MOUSEMOTION and self.dragging:
            apply_volume((event.pos[0]-sx)/sw2)


# =============================================================================
# MAP SELECT SCREEN  — clicking a map now goes to pre_game, not directly playing
# =============================================================================
class MapSelectScreen:
    def draw(self):
        global game_state, tilemap, active_map_cfg
        sw, sh = display.get_width(), display.get_height()
        display.fill((8,8,20))
        t = wave_font.render('SELECT MAP', True, (200,220,255))
        display.blit(t, (sw//2-t.get_width()//2, 30))
        sub = small_font.render('Choose your battlefield', False, (110,110,140))
        display.blit(sub, (sw//2-sub.get_width()//2, 30+t.get_height()+6))

        n      = len(MAP_CONFIGS)
        cw, ch = min(340, (sw-80)//n), 300
        gap    = (sw - n*cw) // (n+1)
        mpos   = py.mouse.get_pos(); cy_ = sh//2 - ch//2 + 20

        for idx, (mid, cfg) in enumerate(MAP_CONFIGS.items()):
            cx_ = gap + idx*(cw+gap)
            card = py.Rect(cx_, cy_, cw, ch)
            hov  = card.collidepoint(mpos)
            py.draw.rect(display, (30,50,100) if hov else (15,28,55), card, border_radius=14)
            py.draw.rect(display, (0,170,255) if hov else (40,80,160), card, width=3, border_radius=14)

            if tilemap:
                try:
                    tmp = TileMap.__new__(TileMap)
                    tmp.tile_size = TILE_SIZE
                    tmp.grid = tmp._load_csv(cfg['csv'])
                    tmp.rows = len(tmp.grid)
                    tmp.cols = len(tmp.grid[0]) if tmp.rows else 0
                    tmp.floor_img = tilemap.floor_img
                    tmp.wall_img  = tilemap.wall_img
                    scale = min((cw-20)//max(1,tmp.cols), 120//max(1,tmp.rows))
                    scale = max(1, scale)
                    tmp.draw_minimap(display, cx_+10, cy_+10, scale=scale)
                except Exception:
                    pass

            # Best wave badge
            hs = load_highscore(cfg['csv'])
            if hs.get('wave', 0) > 0:
                bw_txt = small_font.render(f"Best: Wave {hs['wave']}", False, (255,215,0))
                display.blit(bw_txt, (cx_+cw//2-bw_txt.get_width()//2, cy_+ch-100))

            nm = my_font.render(cfg['name'], False, (255,220,80))
            display.blit(nm, (cx_+cw//2-nm.get_width()//2, cy_+ch-72))
            desc_lines = _wrap(cfg['desc'], small_font, cw-24)
            for li, dl in enumerate(desc_lines):
                ds = small_font.render(dl, False, (160,180,200))
                display.blit(ds, (cx_+cw//2-ds.get_width()//2, cy_+ch-46+li*22))

            if hov and mouse_clicked:
                set_active_map(cfg)
                tilemap = TileMap(cfg['csv'])
                game_state = 'pre_game'   # ← go to lobby, not straight to playing

        back_r = py.Rect(sw//2-100, sh-80, 200, 50); hov = back_r.collidepoint(mpos)
        py.draw.rect(display, (40,60,40) if hov else (25,40,25), back_r, border_radius=10)
        py.draw.rect(display, (100,200,100), back_r, width=2, border_radius=10)
        bl = my_font.render('Back', False, (255,255,255))
        display.blit(bl, (back_r.centerx-bl.get_width()//2, back_r.centery-bl.get_height()//2))
        if back_r.collidepoint(mpos) and mouse_clicked:
            game_state = 'menu'


# =============================================================================
# PRE-GAME SCREEN  (per-map highscore + difficulty + Play)
# =============================================================================
class PreGameScreen:
    """Shown after clicking a map — lets the player pick difficulty then play."""

    DIFFICULTIES = ['Easy', 'Normal', 'Hard', 'Expert']

    def draw(self):
        global game_state, selected_difficulty
        sw, sh = display.get_width(), display.get_height()
        display.fill((8,8,20))

        cfg = active_map_cfg
        # Title
        t = wave_font.render(cfg['name'], True, (200,220,255))
        display.blit(t, (sw//2-t.get_width()//2, 30))
        sub = small_font.render(cfg['desc'], False, (110,110,140))
        display.blit(sub, (sw//2-sub.get_width()//2, 30+t.get_height()+6))

        # ── Highscore panel ───────────────────────────────────────────────────
        hs = load_highscore(cfg['csv'])
        hs_y = 130
        hs_title = my_font.render('── Best Run ──', False, (200,200,100))
        display.blit(hs_title, (sw//2-hs_title.get_width()//2, hs_y))
        if hs.get('wave', 0) > 0:
            ts = hs.get('time', 0); m, s = ts//60, ts%60
            hs_lines = [
                f"Wave {hs['wave']}",
                f"Time: {m}m {s:02d}s",
                f"Kills: {hs.get('kills','?')}   Level: {hs.get('level','?')}",
                f"Difficulty: {hs.get('difficulty','Normal')}",
            ]
            for li, line in enumerate(hs_lines):
                surf = small_font.render(line, False, (215,215,160))
                display.blit(surf, (sw//2-surf.get_width()//2, hs_y+34+li*26))
        else:
            ns = small_font.render('No runs yet — be the first!', False, (130,130,100))
            display.blit(ns, (sw//2-ns.get_width()//2, hs_y+34))

        # ── Difficulty selector ───────────────────────────────────────────────
        diff_y = hs_y + 160
        dl_title = my_font.render('Difficulty', False, (200,200,200))
        display.blit(dl_title, (sw//2-dl_title.get_width()//2, diff_y))

        btn_w, btn_h = 160, 52; gap = 16
        total_w = len(self.DIFFICULTIES)*btn_w + (len(self.DIFFICULTIES)-1)*gap
        bx = sw//2 - total_w//2; mpos = py.mouse.get_pos()

        for i, diff in enumerate(self.DIFFICULTIES):
            preset = DIFFICULTY_PRESETS[diff]
            rect   = py.Rect(bx + i*(btn_w+gap), diff_y+40, btn_w, btn_h)
            active = (diff == selected_difficulty)
            hov    = rect.collidepoint(mpos)
            border_col = preset['col']
            bg = tuple(min(255, c//2) for c in border_col) if active else \
                 (tuple(min(255, c//3) for c in border_col) if hov else (22,22,40))
            py.draw.rect(display, bg,         rect, border_radius=10)
            py.draw.rect(display, border_col, rect, width=3 if active else 2, border_radius=10)
            lbl_s = my_font.render(diff, False, border_col if active else (180,180,180))
            display.blit(lbl_s, (rect.centerx-lbl_s.get_width()//2,
                                  rect.centery-lbl_s.get_height()//2))
            if hov and mouse_clicked:
                selected_difficulty = diff

        # Difficulty description
        pdesc = {
            'Easy':   'Enemies: ½ HP · 20% slower',
            'Normal': 'Standard settings',
            'Hard':   'Enemies: 1.5× HP · start with 2 hearts',
            'Expert': 'Enemies: 2× HP · start with 1 heart',
        }
        dd = small_font.render(pdesc[selected_difficulty], False,
                               DIFFICULTY_PRESETS[selected_difficulty]['col'])
        display.blit(dd, (sw//2-dd.get_width()//2, diff_y+104))

        # ── Play button ───────────────────────────────────────────────────────
        pb_w, pb_h = 260, 66
        pb_rect = py.Rect(sw//2-pb_w//2, diff_y+150, pb_w, pb_h)
        pb_hov  = pb_rect.collidepoint(mpos)
        py.draw.rect(display, (70,46,8) if pb_hov else (48,30,4), pb_rect, border_radius=14)
        py.draw.rect(display, (255,165,0) if pb_hov else (200,120,0),
                     pb_rect, width=3, border_radius=14)
        play_s = wave_font.render('PLAY', False, (255,255,255))
        display.blit(play_s, (pb_rect.centerx-play_s.get_width()//2,
                               pb_rect.centery-play_s.get_height()//2))
        if pb_rect.collidepoint(mpos) and mouse_clicked:
            init_game()
            game_state = 'playing'

        # Back button
        back_r = py.Rect(sw//2-100, diff_y+240, 200, 50)
        back_h = back_r.collidepoint(mpos)
        py.draw.rect(display, (40,60,40) if back_h else (25,40,25), back_r, border_radius=10)
        py.draw.rect(display, (100,200,100), back_r, width=2, border_radius=10)
        bl = my_font.render('Back', False, (255,255,255))
        display.blit(bl, (back_r.centerx-bl.get_width()//2, back_r.centery-bl.get_height()//2))
        if back_r.collidepoint(mpos) and mouse_clicked:
            game_state = 'map_select'


def _wrap(text, font, max_w):
    words = text.split(); lines = []; line = ''
    for word in words:
        test = line+(' ' if line else '')+word
        if font.size(test)[0] <= max_w: line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines


# =============================================================================
# MAIN MENU
# =============================================================================
class MainMenu:
    BUTTONS = ['Play','Options','Quit']
    def draw(self):
        sw, sh = display.get_width(), display.get_height()
        display.fill((10,10,22))
        try:
            logo = py.image.load(sp("ui","blaze_time_logo.png")).convert_alpha()
            tw = int(sw*0.55); scale = tw/logo.get_width()
            logo = py.transform.smoothscale(logo, (tw, int(logo.get_height()*scale)))
            display.blit(logo, (sw//2-logo.get_width()//2, sh//10))
        except Exception:
            t = title_font.render('BLAZE BRIGADE', True, (255,140,0))
            display.blit(t, (sw//2-t.get_width()//2, sh//8))
        sub = small_font.render('Survive the waves.  Upgrade.  Prevail.', False, (150,150,175))
        display.blit(sub, (sw//2-sub.get_width()//2, sh//3+20))
        bw, bh, gap = 280, 62, 20
        total_h = len(self.BUTTONS)*(bh+gap)-gap
        sy_ = sh//2-total_h//2+60; mpos = py.mouse.get_pos()
        for i, label in enumerate(self.BUTTONS):
            rect = py.Rect(sw//2-bw//2, sy_+i*(bh+gap), bw, bh); hov = rect.collidepoint(mpos)
            is_play = label == 'Play'
            col = (80,50,10) if is_play and hov else (50,30,5) if is_play else \
                  ((50,70,130) if hov else (28,40,80))
            brd = (255,160,0) if is_play else (100,140,220)
            if hov: brd = tuple(min(255,c+40) for c in brd)
            py.draw.rect(display, col, rect, border_radius=12)
            py.draw.rect(display, brd, rect, width=3, border_radius=12)
            font  = wave_font if is_play else my_font
            ls    = font.render(label, False, (255,255,255))
            display.blit(ls, (rect.centerx-ls.get_width()//2, rect.centery-ls.get_height()//2))
            if hov and mouse_clicked: self._handle(label)

    def _handle(self, label):
        global game_state, options_from
        if   label == 'Play':    game_state = 'map_select'
        elif label == 'Options': options_from = 'menu'; game_state = 'options'
        elif label == 'Quit':    sys.exit()


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================
tilemap        = TileMap(active_map_cfg['csv'])
stats          = None; upgrades = None; player = None
enemies: list  = []; player_bullets: list = []
explosions: list = []; drops: list = []; chests: list = []; sword_swings: list = []
bomb_enemies: list = []; bomb_explosions: list = []
thrown_bombs: list = []
display_scroll = [0, 0]; slime_king = None; bomb_king = None
shop = None; wave_manager = None; level_up_menu = None; death_screen = None
chest_menu     = ChestMenu()

main_menu      = MainMenu()
map_select     = MapSelectScreen()
pre_game       = PreGameScreen()
pause_menu     = PauseMenu()
options_screen = OptionsScreen()


# =============================================================================
# HELPERS  — per-map highscore keyed by CSV filename
# =============================================================================
def load_highscore(map_csv=None):
    """Return the highscore dict for the given map (or the whole file if None)."""
    if not os.path.exists(HIGHSCORE_FILE):
        return {}
    with open(HIGHSCORE_FILE, 'r') as f:
        data = json.load(f)
    if map_csv is None:
        return data
    # data is either old flat format {wave:…} or new nested {map_csv: {wave:…}}
    if map_csv in data:
        return data[map_csv]
    # Legacy: if top-level keys look like a score dict, return empty for keyed access
    return {}

def save_highscore(map_csv, score_data):
    """Save score_data under the given map key, preserving other map scores."""
    if os.path.exists(HIGHSCORE_FILE):
        with open(HIGHSCORE_FILE, 'r') as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = {}
    else:
        existing = {}
    # If existing file has old flat format (keys are not csv names), migrate
    if existing and not any(k.endswith('.csv') for k in existing.keys()):
        # Wrap the old data under a generic key so it's not lost
        existing = {'test_level.csv': existing}
    existing[map_csv] = score_data
    with open(HIGHSCORE_FILE, 'w') as f:
        json.dump(existing, f, indent=2)

def init_game():
    global stats, upgrades, player, enemies, player_bullets, explosions
    global drops, chests, sword_swings, slime_king, bomb_king, bomb_enemies
    global bomb_explosions, thrown_bombs, display_scroll, shop, wave_manager
    global level_up_menu, death_screen
    stats          = PlayerStats(); upgrades = PlayerUpgrades(); player = Player()
    enemies        = []; player_bullets = []; explosions = []; drops = []
    chests         = []; sword_swings = []; slime_king = None; bomb_king = None
    bomb_enemies   = []; bomb_explosions = []; thrown_bombs = []
    display_scroll = [0, 0]
    shop           = Shop(); wave_manager = WaveManager()
    level_up_menu  = LevelUpMenu(); death_screen = DeathScreen()
    chest_menu.visible = False

def bullet_collision():
    for enemy in enemies[:]:
        if enemy.rect.colliderect(player.rect) and stats.damage_cooldown == 0:
            if god_mode:
                stats.damage_cooldown = HIT_COOLDOWN
            elif random.random() < stats.dodge_chance:
                stats.damage_cooldown = HIT_COOLDOWN
            elif upgrades.regen_shielded:
                stats.damage_cooldown = HIT_COOLDOWN
            elif upgrades.shield_active:
                upgrades.shield_active = False; stats.damage_cooldown = HIT_COOLDOWN
            else:
                stats.damage_cooldown = HIT_COOLDOWN; stats.health -= 1
                if life_lost_sound_play: life_lost_sound_play()
                if stats.health <= 0:
                    if game_over_sound_play: game_over_sound_play()
                    death_screen.show(); return

        for bullet in player_bullets[:]:
            if not bullet.rect.colliderect(enemy.rect): continue
            if not upgrades.piercing_shots:
                if bullet in player_bullets: player_bullets.remove(bullet)
            enemy.hp -= bullet.damage
            if upgrades.bullet_knockback and random.random() < 0.05:
                spd = math.hypot(bullet.x_v, bullet.y_v) or 1
                enemy.kb_vx = (bullet.x_v / spd) * 20
                enemy.kb_vy = (bullet.y_v / spd) * 20
            if upgrades.freeze_chance > 0 and random.random() < upgrades.freeze_chance:
                enemy.kb_vx *= 0.05; enemy.kb_vy *= 0.05
                enemy.hit_flash = max(enemy.hit_flash, 150)
            if upgrades.splash:
                if explosion_sound_play: explosion_sound_play()
                explosions.append(Explosion(enemy.x+32, enemy.y+30))
                for other in enemies[:]:
                    if other is not enemy and math.hypot(other.x-enemy.x, other.y-enemy.y) < SPLASH_RADIUS:
                        other.hp -= 0.5
            if enemy.hp <= 0 and enemy in enemies:
                death_sound.play(); enemies.remove(enemy)
                stats.balance += int(enemy.MONEY_REWARD * stats.money_mult)
                stats.add_xp(enemy.XP_REWARD); stats.kills += 1; stats.lifesteal_roll()
                wx, wy = enemy.x+32, enemy.y+30
                luck = stats.drop_luck
                if random.random() < 0.05 * luck: drops.append(Drop(wx, wy, 'heart'))
                if random.random() < 0.04 * luck: drops.append(Drop(wx, wy, 'ammo'))
                if random.random() < 0.02 * luck: chests.append(Chest(wx, wy))
            if not upgrades.piercing_shots:
                break

    if slime_king and slime_king.alive:
        for bullet in player_bullets[:]:
            if bullet.rect.colliderect(slime_king.rect):
                if not upgrades.piercing_shots:
                    if bullet in player_bullets: player_bullets.remove(bullet)
                slime_king.hp -= bullet.damage
                if slime_king.hp <= 0:
                    slime_king.on_death()
                if not upgrades.piercing_shots:
                    break

    if slime_king and slime_king.alive:
        if slime_king.rect.colliderect(player.rect) and stats.damage_cooldown == 0:
            if not god_mode and not upgrades.regen_shielded:
                stats.damage_cooldown = HIT_COOLDOWN
                stats.health -= 2
                if life_lost_sound_play: life_lost_sound_play()
                if stats.health <= 0:
                    if game_over_sound_play: game_over_sound_play()
                    death_screen.show()

    if bomb_king and bomb_king.alive:
        for bullet in player_bullets[:]:
            if bullet.rect.colliderect(bomb_king.rect):
                if not upgrades.piercing_shots:
                    if bullet in player_bullets: player_bullets.remove(bullet)
                bomb_king.hp -= bullet.damage
                if bomb_king.hp <= 0:
                    bomb_king.on_death()
                if not upgrades.piercing_shots:
                    break

    for bomb in bomb_enemies[:]:
        for bullet in player_bullets[:]:
            if bullet.rect.colliderect(bomb.rect):
                if not upgrades.piercing_shots:
                    if bullet in player_bullets: player_bullets.remove(bullet)
                bomb.hp -= bullet.damage
                bomb.kb_vx = (bullet.x_v / BULLET_SPEED) * 14
                bomb.kb_vy = (bullet.y_v / BULLET_SPEED) * 14
                if bomb.hp <= 0:
                    stats.balance += int(bomb.MONEY_REWARD * stats.money_mult)
                    stats.add_xp(bomb.XP_REWARD)
                    stats.kills += 1
                    bomb.explode()
                if not upgrades.piercing_shots:
                    break


# =============================================================================
# DRAW
# =============================================================================
def draw_display():
    display.fill((15,15,20))
    tilemap.draw(display, display_scroll)

    lvlup_open = level_up_menu.visible
    shop_open  = shop.open
    chest_open = chest_menu.visible
    all_frozen = lvlup_open or shop_open or chest_open

    global sword_swings
    for enemy in enemies: enemy.main(frozen=all_frozen)
    for bomb in bomb_enemies[:]: bomb.main(frozen=all_frozen)
    if slime_king and slime_king.alive: slime_king.main(frozen=all_frozen)
    if bomb_king  and bomb_king.alive:  bomb_king.main(frozen=all_frozen)
    explosions[:]      = [e for e in explosions      if e.update()]
    bomb_explosions[:] = [e for e in bomb_explosions if e.update()]
    thrown_bombs[:]    = [t for t in thrown_bombs    if t.update()]
    drops[:]           = [d for d in drops           if d.update()]
    sword_swings[:]    = [s for s in sword_swings    if s.update()]

    if death_screen.visible: death_screen.draw(); py.display.update(); return

    player.main(frozen=all_frozen)
    for bullet in player_bullets[:]:
        if all_frozen: bullet.render()
        else:          bullet.update()

    if not all_frozen:
        bullet_collision()
        upgrades.regen_shield_update()
        if stats.level_up_pending: stats.level_up_pending = False; level_up_menu.show()
        wave_manager.update()
    else:
        wave_manager.draw_wave_info()

    shop.update()
    chest_menu.update()
    chests[:] = [c for c in chests if c.update()]
    stats.update()
    bar_y = 0
    if slime_king and slime_king.alive:
        slime_king.draw_boss_bar(y_offset=bar_y); bar_y += 44
    if bomb_king and bomb_king.alive:
        bomb_king.draw_boss_bar(y_offset=bar_y)

    if lvlup_open: level_up_menu.draw()
    if chest_open: chest_menu.draw()
    py.display.update()


def draw_frozen_world():
    display.fill((15,15,20)); tilemap.draw(display, display_scroll)
    for enemy in enemies: enemy.main(frozen=True)
    for bomb in bomb_enemies: bomb.main(frozen=True)
    if slime_king and slime_king.alive: slime_king.main(frozen=True)
    if bomb_king  and bomb_king.alive:  bomb_king.main(frozen=True)
    for e in bomb_explosions: e.update()
    for t in thrown_bombs:    t.update()
    for bullet in player_bullets: bullet.render()
    for c in chests: c.update()
    if player: player.player_rotation(); player.render(); player.draw_weapon_hud()
    if stats: stats.update()
    bar_y = 0
    if slime_king and slime_king.alive:
        slime_king.draw_boss_bar(y_offset=bar_y); bar_y += 44
    if bomb_king and bomb_king.alive:
        bomb_king.draw_boss_bar(y_offset=bar_y)
    if wave_manager: wave_manager.draw_wave_info()


# =============================================================================
# MAIN LOOP
# =============================================================================
def main():
    global mouse_clicked, game_state
    clock = py.time.Clock()
    while True:
        mouse_clicked = False
        events = py.event.get()
        for event in events:
            if event.type == py.QUIT: sys.exit()
            if event.type == py.VIDEORESIZE:
                settings.display_width  = display.get_width()
                settings.display_height = display.get_height()
            if event.type == py.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked = True
                in_ui = (game_state != 'playing') or \
                        (shop and shop.open) or \
                        (level_up_menu and level_up_menu.visible) or \
                        (chest_menu and chest_menu.visible) or \
                        (death_screen and death_screen.visible)
                if in_ui and ui_click_sound_play:
                    ui_click_sound_play()
            if event.type == py.KEYDOWN and event.key == py.K_ESCAPE:
                if   game_state == 'playing':    game_state = 'paused'
                elif game_state == 'paused':     game_state = 'playing'
                elif game_state == 'options':    game_state = options_from
                elif game_state == 'map_select': game_state = 'menu'
                elif game_state == 'pre_game':   game_state = 'map_select'
            if game_state == 'options': options_screen.handle_event(event)

        if   game_state == 'menu':       main_menu.draw()
        elif game_state == 'map_select': map_select.draw()
        elif game_state == 'pre_game':   pre_game.draw()
        elif game_state == 'playing':    draw_display()
        elif game_state == 'paused':     draw_frozen_world(); pause_menu.draw()
        elif game_state == 'options':    options_screen.draw()

        py.display.update()
        clock.tick(FPS)


if __name__ == '__main__':
    main()