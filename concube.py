import hashlib
import hmac
import json
import math
import os
import random
import re
import secrets
import sys

import numpy as np
import pygame

# ==========================================================
# KHỞI TẠO
# ==========================================================
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

AUDIO_OK = False
try:
    pygame.mixer.init()
    AUDIO_OK = True
except pygame.error:
    AUDIO_OK = False

if AUDIO_OK:
    SAMPLE_RATE, _fmt, MIXER_CH = pygame.mixer.get_init()
    pygame.mixer.set_num_channels(16)
    pygame.mixer.set_reserved(1)  
else:
    SAMPLE_RATE, MIXER_CH = 44100, 2

WIDTH, HEIGHT = 800, 700
FPS = 60
window = pygame.display.set_mode((WIDTH, HEIGHT))
screen = pygame.Surface((WIDTH, HEIGHT))  
pygame.display.set_caption("CON CẶC")

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

FONT_NAMES = "consolas,couriernew,dejavusansmono,liberationmono,monospace"


def make_font(size, bold=False):
    return pygame.font.SysFont(FONT_NAMES, size, bold=bold)


font_title = make_font(26, True)
font_large = make_font(28, True)
font_medium = make_font(17, True)
font_small = make_font(14)
font_tiny = make_font(12)


muted = False
MUSIC_VOLUME = 0.5


def to_sound(mono):
    arr = np.column_stack((mono, mono)) if MIXER_CH >= 2 else mono
    return pygame.sndarray.make_sound(np.ascontiguousarray(arr))


def generate_sound(wave_type="sine", freq=440, duration=0.1, fade_out=True, freq_slide=0):
    if not AUDIO_OK:
        return None
    n = max(1, int(SAMPLE_RATE * duration))
    t = np.linspace(0, duration, n, False)
    phase = freq * t + 0.5 * freq_slide * t ** 2  # pha tích lũy -> tiếng "vút" đúng nghĩa
    if wave_type == "sine":
        wave = np.sin(2 * np.pi * phase)
    elif wave_type == "square":
        wave = np.sign(np.sin(2 * np.pi * phase))
    elif wave_type == "saw":
        wave = 2 * (phase - np.floor(phase + 0.5))
    elif wave_type == "noise":
        wave = np.random.uniform(-1, 1, n)
    else:
        wave = np.sin(2 * np.pi * phase)
    if fade_out:
        wave = wave * np.linspace(1, 0, n)
    return to_sound((wave * 11000).astype(np.int16))


def generate_music_track(pattern, speed=0.15):
    if not AUDIO_OK:
        return None
    chunks = []
    for freq in pattern:
        n = max(1, int(SAMPLE_RATE * speed))
        if freq == 0:
            chunks.append(np.zeros(n, dtype=np.int16))
        else:
            t = np.linspace(0, speed, n, False)
            wave = 0.4 * np.sin(2 * np.pi * freq * t) + 0.2 * np.sign(np.sin(2 * np.pi * (freq / 2) * t))
            env = np.linspace(1, 0.2, n)
            chunks.append((wave * env * 6000).astype(np.int16))
    return to_sound(np.concatenate(chunks))


sfx_laser_single = generate_sound("saw", 600, 0.08, freq_slide=-3000)
sfx_laser_double = generate_sound("square", 800, 0.1, freq_slide=-4000)
sfx_laser_triple = generate_sound("saw", 1100, 0.12, freq_slide=-5000)
sfx_laser_hexa = generate_sound("noise", 1500, 0.15, freq_slide=-6000)
sfx_explosion = generate_sound("noise", 200, 0.25)
sfx_powerup = generate_sound("sine", 523, 0.2, freq_slide=2000)
sfx_level_up = generate_sound("square", 440, 0.4, freq_slide=1200)
sfx_hit = generate_sound("square", 180, 0.22, freq_slide=-500)
sfx_warning = generate_sound("saw", 300, 0.5, freq_slide=200)

mel_menu = [261, 329, 392, 523, 392, 329, 261, 0, 220, 277, 329, 440, 329, 277]
mel_game = [150, 150, 300, 150, 150, 350, 150, 150, 400, 350, 300, 200]
bgm_menu = generate_music_track(mel_menu, 0.18)
bgm_game = generate_music_track(mel_game, 0.11)
bgm_channel = pygame.mixer.Channel(0) if AUDIO_OK else None
current_bgm = None


def play(snd):
    if snd is not None and not muted:
        snd.play()


def play_bgm(name):
    global current_bgm
    if not AUDIO_OK or name is None or current_bgm == name:
        return
    bgm_channel.stop()
    bgm_channel.play(bgm_menu if name == "MENU" else bgm_game, loops=-1)
    bgm_channel.set_volume(0 if muted else MUSIC_VOLUME)
    current_bgm = name


def set_muted(value):
    global muted
    muted = value
    if AUDIO_OK:
        bgm_channel.set_volume(0 if muted else MUSIC_VOLUME)


MENU_STATES = ("MENU", "LOGIN_REGISTER", "SELECT_DIFFICULTY", "SHOP_WEAPON", "SHOP_SKIN", "PROFILE")
WORLD_STATES = ("PLAYING", "PAUSED", "GAME_OVER", "VICTORY")

# ==========================================================
# DỮ LIỆU CẤU HÌNH
# ==========================================================
difficulties = {
    "EASY": {"name": "DỄ", "speed_mod": 0.7, "spawn_mod": 1.4, "coin_mod": 1.0, "color": (96, 214, 160)},
    "NORMAL": {"name": "THƯỜNG", "speed_mod": 1.0, "spawn_mod": 1.0, "coin_mod": 1.5, "color": (255, 200, 64)},
    "HARD": {"name": "KHÓ", "speed_mod": 1.4, "spawn_mod": 0.7, "coin_mod": 2.5, "color": (236, 92, 100)},
}
current_difficulty = "NORMAL"

skins = {
    1: {"name": "Galaga Classic", "primary": (255, 255, 255), "wing": (200, 30, 30), "price": 0, "desc": "Phi thuyền tiêm kích 2D truyền thống.", "unlocked": True},
    2: {"name": "Lục Bảo", "primary": (96, 214, 160), "wing": (40, 120, 110), "price": 150, "desc": "Thân ngọc lục bảo, cánh xanh rêu.", "unlocked": False},
    3: {"name": "Chiến Hạm Vàng", "primary": (255, 215, 0), "wing": (255, 120, 0), "price": 300, "desc": "Giáp mạ vàng Arcade.", "unlocked": False},
    4: {"name": "Phượng Hoàng Lửa", "primary": (255, 50, 50), "wing": (255, 200, 0), "price": 500, "desc": "Tối đa hỏa lực bắn ruồi.", "unlocked": False},
    5: {"name": "Chim tung canhs", "primary": (90, 50, 50), "wing": (255, 200, 0), "price": 9999, "desc": "chim cất cánh.", "unlocked": False},
    6: {"name": "Quan âm vồ bồ tác", "primary": (35, 50, 50), "wing": (90, 200, 0), "price": 99999, "desc": "Tối đa hỏa lực bắn ruồi.", "unlocked": False}
}

# type: >0 = cấp đạn, -1 = tăng tốc đạn, -2 = tăng máu khởi đầu
weapon_shop_items = [
    {"type": 2, "name": "Đạn Đôi", "cost": 150, "desc": "Bắn 2 tia đạn song song"},
    {"type": 3, "name": "Đạn Ba", "cost": 300, "desc": "Bắn 3 tia hỏa lực thẳng"},
    {"type": 4, "name": "Đạn Bốn Tỏa", "cost": 500, "desc": "4 tia đạn tỏa góc rộng"},
    {"type": 5, "name": "Đạn Cánh Bướm (5 Tỏa)", "cost": 800, "desc": "5 tia đạn tỏa đều 5 hướng"},
    {"type": 10, "name": "Bão Đạn (10 Tỏa)", "cost": 1500, "desc": "Sức mạnh tối thượng tỏa 10 hướng"},
    {"type": -1, "name": "Tăng Tốc Đạn (+4)", "cost": 100, "desc": "Đạn bay nhanh hơn (tối đa 25)"},
    {"type": -2, "name": "Giáp Cường Hóa (+1 HP)", "cost": 200, "desc": "Bắt đầu mỗi màn với nhiều máu hơn (tối đa 6)"},
]
VALID_BULLET_TYPES = (1, 2, 3, 4, 5, 10)
BULLET_SPEED_MIN, BULLET_SPEED_MAX = 13, 25
START_HP_MIN, START_HP_MAX = 3, 6
SPREAD_ANGLES = {
    4: [-0.25, -0.08, 0.08, 0.25],
    5: [-0.4, -0.2, 0, 0.2, 0.4],
    10: [-0.6, -0.45, -0.3, -0.15, -0.05, 0.05, 0.15, 0.3, 0.45, 0.6],
}

MAX_LEVELS = 100
SCORE_PER_LEVEL = 500
MAX_HP = 8

# ==========================================================
# BỐ CỤC NÚT (dùng chung cho vẽ và xử lý click -> không bao giờ lệch nhau)
# ==========================================================
R = {
    "auth_user": pygame.Rect(90, 260, WIDTH - 180, 40),
    "auth_pass": pygame.Rect(90, 340, WIDTH - 180, 40),
    "auth_action": pygame.Rect(90, 410, WIDTH - 180, 45),
    "auth_switch": pygame.Rect(90, 470, WIDTH - 180, 35),
    "diff": pygame.Rect(20, 80, 140, 45),
    "profile": pygame.Rect(WIDTH // 2 - 100, 80, 200, 45),
    "settings": pygame.Rect(WIDTH - 65, 80, 45, 45),
    "pop_frame": pygame.Rect(WIDTH - 175, 132, 165, 135),
    "pop_sound": pygame.Rect(WIDTH - 165, 137, 145, 35),
    "pop_logout": pygame.Rect(WIDTH - 165, 180, 145, 35),
    "pop_quit": pygame.Rect(WIDTH - 165, 223, 145, 35),
    "play": pygame.Rect(WIDTH // 2 - 90, HEIGHT - 110, 180, 55),
    "shop_skin": pygame.Rect(30, HEIGHT - 100, 130, 45),
    "shop_weapon": pygame.Rect(WIDTH - 160, HEIGHT - 100, 130, 45),
    "profile_back": pygame.Rect(50, HEIGHT - 70, WIDTH - 100, 45),
    "diff_back": pygame.Rect(50, HEIGHT - 80, WIDTH - 100, 40),
    "shop_tab": pygame.Rect(50, HEIGHT - 110, WIDTH - 100, 40),
    "shop_back": pygame.Rect(50, HEIGHT - 60, WIDTH - 100, 40),
    "pause_frame": pygame.Rect(80, HEIGHT // 2 - 140, 440, 270),
    "pause_resume": pygame.Rect(120, HEIGHT // 2 + 70, 150, 42),
    "pause_menu": pygame.Rect(330, HEIGHT // 2 + 70, 150, 42),
    "end_retry": pygame.Rect(80, HEIGHT // 2 + 40, 180, 45),
    "end_menu": pygame.Rect(340, HEIGHT // 2 + 40, 180, 45),
}


def diff_rect(idx):
    return pygame.Rect(70, 180 + idx * 90, WIDTH - 140, 60)


def weapon_card_rect(idx):
    return pygame.Rect(35, 114 + idx * 64, WIDTH - 170, 56)


def skin_card_rect(sk_id):
    return pygame.Rect(40, 120 + (sk_id - 1) * 105, WIDTH - 80, 95)


USERS_FILE = os.path.join(BASE_DIR, "users.json")
current_user = None

coins = 500
current_skin_id = 1
high_score = 0
bullet_type = 1
bullet_speed = 13
start_hp = 3
dirty = False  


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password, stored):
    try:
        if stored.startswith("pbkdf2$"):
            salt = stored.split("$")[1]
            return hmac.compare_digest(hash_password(password, salt), stored)
        legacy = hashlib.md5(password.encode("utf-8")).hexdigest()  # tương thích file cũ
        return hmac.compare_digest(legacy, stored)
    except Exception:
        return False


def is_legacy_hash(stored):
    return not stored.startswith("pbkdf2$")


def atomic_write_json(path, data):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def read_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else default
        except Exception:
            return default
    return default


def load_users():
    return read_json(USERS_FILE, {})


def save_users(users_data):
    atomic_write_json(USERS_FILE, users_data)


def get_user_save_file(username):
    # tên file là hash -> không thể "../" thoát thư mục, không đụng tên lạ
    digest = hashlib.sha1(username.encode("utf-8")).hexdigest()[:16]
    return os.path.join(BASE_DIR, f"player_data_{digest}.json")


def load_game_data(username):
    path = get_user_save_file(username)
    if not os.path.exists(path) and re.fullmatch(r"[\w\-.]+", username):
        legacy = os.path.join(BASE_DIR, f"player_data_{username}.json")
        if os.path.exists(legacy):
            path = legacy
    return read_json(path, {})


def clamp_int(value, lo, hi, default):
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def save_game_data():
    global dirty
    if not current_user:
        return
    data = {
        "coins": coins,
        "unlocked_skins": [s_id for s_id, sk in skins.items() if sk["unlocked"]],
        "current_skin": current_skin_id,
        "high_score": high_score,
        "bullet_type": bullet_type,
        "bullet_speed": bullet_speed,
        "start_hp": start_hp,
        "difficulty": current_difficulty,
        "muted": muted,
    }
    if atomic_write_json(get_user_save_file(current_user), data):
        dirty = False


def apply_loaded_user_data(username):
    global coins, current_skin_id, high_score, bullet_type, bullet_speed, start_hp, current_difficulty
    data = load_game_data(username)
    coins = clamp_int(data.get("coins", 500), 0, 10 ** 9, 500)
    high_score = clamp_int(data.get("high_score", 0), 0, 10 ** 9, 0)
    bt = data.get("bullet_type", 1)
    bullet_type = bt if bt in VALID_BULLET_TYPES else 1
    bullet_speed = clamp_int(data.get("bullet_speed", 13), BULLET_SPEED_MIN, BULLET_SPEED_MAX, 13)
    start_hp = clamp_int(data.get("start_hp", 3), START_HP_MIN, START_HP_MAX, 3)
    diff = data.get("difficulty", "NORMAL")
    current_difficulty = diff if diff in difficulties else "NORMAL"
    set_muted(bool(data.get("muted", False)))

    unlocked = data.get("unlocked_skins", [1])
    for s_id in skins:
        skins[s_id]["unlocked"] = (s_id == 1) or (s_id in unlocked)
    cs = data.get("current_skin", 1)
    current_skin_id = cs if cs in skins and skins[cs]["unlocked"] else 1


auth_mode = "LOGIN"
input_username = ""
input_password = ""
active_field = "username"
auth_message = ""
auth_msg_color = (255, 80, 80)

toast_msg = ""
toast_color = (255, 255, 255)
toast_timer = 0


def set_toast(msg, ok=True):
    global toast_msg, toast_color, toast_timer
    toast_msg, toast_timer = msg, 100
    toast_color = (96, 214, 160) if ok else (255, 106, 61)



state = "SPLASH"
running = True
show_settings_popup = False

score = 0
level = 1
level_score_start = 0
player_hp = 3
player_x, player_y = WIDTH // 2 - 25.0, HEIGHT - 100.0
player_speed = 7

bullets = []
enemy_bullets = []
enemies = []
particles = []
engine_thrusters = []
powerups = []
current_boss = None

temp_weapon_type = 1
temp_weapon_timer = 0
shield_timer = 0
invincible_timer = 0
shake = 0
banner_text = ""
banner_timer = 0
auto_fire = False
cooldown_timer = 0
spawn_timer = 0
autosave_timer = 0

TEMP_WEAPON_FRAMES = 720
SHIELD_FRAMES = 480
INVINCIBLE_FRAMES = 90

menu_rocket = {"x": -100.0, "y": HEIGHT // 2 - 20.0, "vx": 6, "vy": -1.2}
clock = pygame.time.Clock()

stars = []
for _ in range(120):
    layer = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
    stars.append({"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT),
                  "layer": layer, "speed": layer * 1.5, "size": layer, "brightness": random.randint(150, 255)})



C_BG = (16, 13, 26)
C_PANEL = (30, 24, 46)
C_PANEL_HI = (50, 40, 76)
C_INK = (10, 8, 16)
C_CREAM = (244, 233, 206)
C_DIM = (150, 138, 172)
C_ORANGE = (255, 106, 61)
C_GOLD = (255, 200, 64)
C_MINT = (96, 214, 160)
C_PINK = (236, 92, 140)
C_RED = (222, 64, 56)
SHADOW_RED = (150, 50, 40)

sprite_cache = {}


def shade(color, f):
    return tuple(max(0, min(255, int(v * f))) for v in color)


def chamfer_points(rect, c=4):
    x, y, w, h = rect
    return [(x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h - c),
            (x + w - c, y + h), (x + c, y + h), (x, y + h - c), (x, y + c)]


def draw_panel(surface, rect, fill=C_PANEL, border=C_CREAM, sh=4, cut=4, bw=2):
    rect = pygame.Rect(rect)
    if sh:
        pygame.draw.polygon(surface, C_INK, chamfer_points(rect.move(sh, sh), cut))
    pygame.draw.polygon(surface, fill, chamfer_points(rect, cut))
    pygame.draw.polygon(surface, border, chamfer_points(rect, cut), bw)


def build_sprite(rows, palette, scale=3, mirror=True):
    half_w = len(rows[0])
    w = half_w * 2 if mirror else half_w
    surf = pygame.Surface((w * scale, len(rows) * scale), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        full = row + row[::-1] if mirror else row
        for x, ch in enumerate(full):
            col = palette.get(ch)
            if col:
                pygame.draw.rect(surf, col, (x * scale, y * scale, scale, scale))
    return surf


PLAYER_ROWS = [
    ".......W",
    ".......W",
    "......WW",
    "......WC",
    ".....OWC",
    ".....WWW",
    "..R..WWw",
    ".RR.OWWw",
    ".RRrOWWw",
    "RRRrrWWw",
    "RRrRrwWw",
    "RrRRr.Ww",
    "R.rr..Ew",
    "R....EEE",
    ".....E.E",
    "........",
]
ENEMY_ROWS = {
    1: ["L....", ".L.AA", "..AAA", ".AAEP", "AAAAA", "AaAaA", "A.AAA", "L.A..", "L...."],
    2: [".....", "..AAA", ".AAAA", "AAEEA", "AAAAA", ".aAAA", "..aAA", ".L.L.", "L...L"],
    3: ["....A", "...AA", "..AAA", ".AACC", "AAACC", "AaAAA", ".AaAA", "..AaA", "...aA"],
}
BOSS_ROWS = [
    "..........aA",
    ".........aAA",
    "L.......aAAA",
    "LL.....aAAAA",
    "LLL...aAAAAA",
    "LLLL.aAAAAAA",
    "LLLLAAAAAAAA",
    "LaLLAAAAAAAA",
    "LaLAAAAEEEAA",
    ".aAAAAAEPPEA",
    "..AAAAAEEEAA",
    "..aAAAAAAAAA",
    "...aAAAAAdAA",
    "....aAAAdddA",
    ".....aAAAddd",
    "......aAAAdd",
    ".......aaAAd",
    "..........aa",
]
ROCKET_ROWS = [
    "......WWWWW.....",
    "..F..WWWWWWR....",
    "FFFWWWWWWWWWRR..",
    "FFEWWWCCWWWWWRRR",
    "FFFWWWWWWWWWRR..",
    "..F..WWWWWWR....",
    "......WWWWW.....",
]
PIXEL_HEART = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]


def heart_sprite(filled):
    key = ("heart", filled)
    if key not in sprite_cache:
        col = C_RED if filled else (70, 62, 90)
        sprite_cache[key] = build_sprite(PIXEL_HEART, {"X": col}, 3, mirror=False)
    return sprite_cache[key]


def get_enemy_sprite(e_type, flag=False):
    key = ("enemy", e_type, flag)
    if key not in sprite_cache:
        if e_type == 1:
            pal = {"A": C_RED, "a": shade(C_RED, 0.6), "E": C_CREAM, "P": C_INK, "L": C_GOLD}
        elif e_type == 2:
            pal = {"A": (96, 170, 110), "a": (60, 115, 80), "E": C_CREAM, "P": C_INK, "L": C_GOLD}
        else:
            pal = {"A": (150, 100, 210), "a": (95, 60, 150), "C": C_GOLD if flag else C_RED}
        sprite_cache[key] = build_sprite(ENEMY_ROWS[e_type], pal, 4)
    return sprite_cache[key]


def get_boss_sprite(rage, bright):
    key = ("boss", rage, bright)
    if key not in sprite_cache:
        body = (200, 40, 50) if rage else (130, 70, 190)
        pal = {"A": body, "a": shade(body, 0.6), "d": shade(body, 0.8), "L": (214, 150, 60),
               "E": (255, 210, 60) if bright else (200, 110, 40), "P": C_INK}
        sprite_cache[key] = build_sprite(BOSS_ROWS, pal, 5)
    return sprite_cache[key]


def get_rocket_sprite():
    if "rocket" not in sprite_cache:
        pal = {"W": C_CREAM, "F": C_ORANGE, "E": C_GOLD, "C": (120, 170, 230), "R": C_RED}
        sprite_cache["rocket"] = build_sprite(ROCKET_ROWS, pal, 3, mirror=False)
    return sprite_cache["rocket"]


BUTTON_KINDS = {
    # fill, fill_hover, border, border_hover, text, text_hover
    "normal": (C_PANEL, C_PANEL_HI, C_DIM, C_GOLD, C_CREAM, C_GOLD),
    "primary": (C_ORANGE, C_GOLD, C_CREAM, C_CREAM, C_INK, C_INK),
    "danger": ((130, 44, 52), (190, 58, 60), (236, 120, 110), C_CREAM, C_CREAM, C_CREAM),
}


def blit_text(surf, font, text, color, shadow=None, **anchor):
    img = font.render(text, False, color)
    rect = img.get_rect(**anchor)
    if shadow:
        surf.blit(font.render(text, False, shadow), rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def draw_card_frame(surface, rect, border_color=C_CREAM, fill_color=C_PANEL, radius=0):
    draw_panel(surface, rect, fill=fill_color[:3], border=border_color)


def draw_button(surface, rect, label, font, hover, kind="normal", selected=False, accent=None):
    fill, fill_h, border, border_h, text, text_h = BUTTON_KINDS[kind]
    if selected and accent:
        fill, fill_h, border, border_h, text, text_h = accent, accent, C_CREAM, C_CREAM, C_INK, C_INK
    draw_panel(surface, rect, fill_h if hover else fill, border_h if hover else border, sh=3)
    blit_text(surface, font, label, text_h if hover else text, center=rect.center)


def draw_gear_icon(surface, cx, cy, radius=14, color=C_CREAM, teeth=8):
    for dy in (-7, 0, 7):  # biểu tượng menu 3 gạch
        pygame.draw.rect(surface, color, (cx - 10, cy + dy - 2, 20, 4))


def draw_heart(surface, x, y, filled=True):
    surface.blit(heart_sprite(filled), (x, y))


def draw_bullet_preview(surface, x, y, b_type, width=80, height=55):
    box = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, C_INK, box)
    pygame.draw.rect(surface, C_DIM, box, 2)
    cx, cy = x + width // 2, y + height - 8
    if b_type == -2:
        hs = heart_sprite(True)
        surface.blit(hs, hs.get_rect(center=box.center))
        return
    if b_type == -1:
        for dx in (-14, 0, 14):
            pygame.draw.rect(surface, C_CREAM, (cx + dx - 1, cy - 34, 3, 34))
        return
    if b_type == 1:
        angles = [0]
    elif b_type == 2:
        angles = [-0.1, 0.1]
    elif b_type == 3:
        angles = [-0.2, 0, 0.2]
    else:
        angles = SPREAD_ANGLES.get(b_type, [0])
    color = C_ORANGE if b_type >= 4 else C_CREAM
    length = height - 20
    for rad in angles:
        ex = cx + length * math.sin(rad)
        ey = cy - length * math.cos(rad)
        pygame.draw.line(surface, color, (cx, cy), (ex, ey), 2)
        pygame.draw.rect(surface, C_GOLD, (int(ex) - 2, int(ey) - 2, 4, 4))


ship_cache = {}


def get_ship_surface(skin_id):
    if skin_id not in ship_cache:
        sk = skins.get(skin_id, skins[1])
        pal = {"W": sk["primary"], "w": shade(sk["primary"], 0.65), "R": sk["wing"], "r": shade(sk["wing"], 0.6),
               "C": C_GOLD, "O": C_INK, "E": C_ORANGE}
        ship_cache[skin_id] = build_sprite(PLAYER_ROWS, pal, 3)
    return ship_cache[skin_id]


def draw_player(surface, x, y, skin_id):
    surface.blit(get_ship_surface(skin_id), (int(x) + 1, int(y) + 1))


def draw_shield_bubble(surface, x, y):
    t = pygame.time.get_ticks()
    pulse = 4 + int(math.sin(t * 0.012) * 3)
    s = pygame.Surface((90, 90), pygame.SRCALPHA)
    pygame.draw.circle(s, (96, 214, 160, 45), (45, 45), 32 + pulse)
    pygame.draw.circle(s, (244, 233, 206, 220), (45, 45), 32 + pulse, 2)
    surface.blit(s, (int(x) + 25 - 45, int(y) + 25 - 45))


def draw_menu_animated_rocket(surface):
    r = menu_rocket
    r["x"] += r["vx"]
    r["y"] += r["vy"]
    if r["x"] > WIDTH + 150:
        r["x"] = -150
        r["y"] = random.randint(HEIGHT // 2 - 60, HEIGHT // 2 + 60)
    rx, ry = r["x"], r["y"]
    if random.random() < 0.8:
        particles.append({"x": rx - 6, "y": ry + 10 + random.uniform(-4, 4), "vx": -random.uniform(3, 6),
                          "vy": random.uniform(-1, 1), "size": random.randint(3, 6),
                          "color": random.choice([C_ORANGE, C_GOLD]), "life": 0.8})
    surface.blit(get_rocket_sprite(), (int(rx), int(ry)))


def draw_enemy(surface, enemy):
    x, y, w, h = enemy["rect"]
    sprite = get_enemy_sprite(enemy["type"], enemy["hp"] <= 1)
    bob = int(math.sin((pygame.time.get_ticks() + enemy.get("seed", 0)) * 0.012) * 2)
    surface.blit(sprite, (x, y + 2 + bob))


def draw_boss(surface, boss):
    x, y, w, h = boss["rect"]
    ratio = max(0.0, boss["hp"] / boss["max_hp"])
    bright = (pygame.time.get_ticks() // 250) % 2 == 0
    surface.blit(get_boss_sprite(ratio < 0.3, bright), (x, y))

    bar_w = 300
    bx = WIDTH // 2 - bar_w // 2
    pygame.draw.rect(surface, C_INK, (bx, 15, bar_w, 14))
    pygame.draw.rect(surface, C_RED if ratio < 0.3 else C_ORANGE, (bx, 15, int(bar_w * ratio), 14))
    pygame.draw.rect(surface, C_CREAM, (bx, 15, bar_w, 14), 2)
    blit_text(surface, font_small, f"TRÙM MÀN {level} - HP: {int(max(0, boss['hp']))}", C_CREAM, shadow=C_INK,
              midtop=(WIDTH // 2, 32))


# ==========================================================
# HIỆU ỨNG
# ==========================================================
def update_stars(move=True):
    for star in stars:
        if move:
            star["y"] += star["speed"]
            if star["y"] > HEIGHT:
                star["y"] = 0
                star["x"] = random.randint(0, WIDTH)


STAR_TINTS = {1: (110, 104, 140), 2: (190, 180, 205), 3: (255, 214, 120)}


def draw_stars(surface):
    surface.fill(C_BG)
    for star in stars:
        col = shade(STAR_TINTS[star["layer"]], 0.55 + 0.45 * star["brightness"] / 255)
        pygame.draw.rect(surface, col, (int(star["x"]), int(star["y"]), star["size"], star["size"]))


def create_explosion(x, y, color=(255, 150, 50), count=18, sound=True):
    if sound:
        play(sfx_explosion)
    for _ in range(count):
        if len(particles) > 350:
            break
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 7)
        particles.append({"x": x, "y": y, "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
                          "size": random.randint(3, 6), "color": color, "life": 1.0})


def step_particles():
    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["life"] -= 0.04
        if p["life"] <= 0:
            particles.remove(p)
    for t in engine_thrusters[:]:
        t["y"] += t["vy"]
        t["life"] -= 0.08
        if t["life"] <= 0:
            engine_thrusters.remove(t)


def draw_particles(surface):
    for p in particles:
        f = max(0.0, p["life"])
        col = tuple(int(c * f + bg * (1 - f)) for c, bg in zip(p["color"], C_BG))
        s = max(2, int(p["size"] * (0.6 + f)))
        pygame.draw.rect(surface, col, (int(p["x"]) - s // 2, int(p["y"]) - s // 2, s, s))


def draw_thrusters(surface):
    for t in engine_thrusters:
        col = C_GOLD if t["life"] > 0.5 else C_ORANGE
        s = max(2, int(t["size"] * t["life"] * 1.4))
        pygame.draw.rect(surface, col, (int(t["x"]) - s // 2, int(t["y"]), s, s))


def create_engine_thruster(x, y):
    engine_thrusters.append({"x": x, "y": y, "vy": random.uniform(3, 6), "size": random.randint(3, 5), "life": 1.0})


POWERUP_COLORS = {"HP": (96, 214, 160), "SHIELD": (120, 170, 230), "DOUBLE": (255, 200, 64),
                  "TRIPLE": (255, 150, 60), "HEXA": (236, 92, 140), "COIN": (244, 233, 206)}
POWERUP_LABELS = {"HP": "HP", "SHIELD": "SH", "DOUBLE": "2X", "TRIPLE": "3X", "HEXA": "5X", "COIN": "$"}


def spawn_powerup(x, y, force=False):
    if force or random.random() < 0.18:
        kind = random.choices(list(POWERUP_COLORS), weights=[0.18, 0.17, 0.2, 0.15, 0.1, 0.2])[0]
        powerups.append({"x": x - 13.0, "y": float(y), "type": kind})


def draw_powerups(surface):
    for item in powerups:
        r = pygame.Rect(int(item["x"]), int(item["y"]), 26, 26)
        draw_panel(surface, r, fill=POWERUP_COLORS[item["type"]], border=C_INK, sh=2, cut=3)
        blit_text(surface, font_tiny, POWERUP_LABELS[item["type"]], C_INK, center=r.center)


# ==========================================================
# LOGIC GAME
# ==========================================================
def reset_match():
    global score, level, level_score_start, player_hp, player_x, player_y, current_boss
    global temp_weapon_type, temp_weapon_timer, shield_timer, invincible_timer, shake
    global cooldown_timer, spawn_timer, banner_text, banner_timer
    score = 0
    level = 1
    level_score_start = 0
    player_hp = start_hp
    player_x, player_y = WIDTH // 2 - 25.0, HEIGHT - 100.0
    for lst in (bullets, enemy_bullets, enemies, particles, powerups, engine_thrusters):
        lst.clear()
    current_boss = None
    temp_weapon_type, temp_weapon_timer = 1, 0
    shield_timer = invincible_timer = shake = 0
    cooldown_timer = spawn_timer = 0
    banner_text, banner_timer = "MÀN 1", 110


def add_score(n):
    global score, high_score
    score += n
    if score > high_score:
        high_score = score


def add_coins(n):
    global coins, dirty
    coins += n
    dirty = True


def end_run(victory):
    global state
    state = "VICTORY" if victory else "GAME_OVER"
    save_game_data()


def damage_player(amount=1):
    global player_hp, invincible_timer, shake
    if invincible_timer > 0 or shield_timer > 0:
        return False
    player_hp -= amount
    invincible_timer = INVINCIBLE_FRAMES
    shake = 14
    create_explosion(player_x + 25, player_y + 25, (255, 60, 60), 22, sound=False)
    play(sfx_hit)
    if player_hp <= 0:
        end_run(False)
    return True


def effective_bullet_type():
    if temp_weapon_timer > 0 and temp_weapon_type > bullet_type:
        return temp_weapon_type
    return bullet_type


def add_pbullet(x, y, vx, vy, color):
    bullets.append({"x": x, "y": y, "vx": vx, "vy": vy, "color": color})


def fire_player_bullets():
    b_type = effective_bullet_type()
    cx, cy = player_x + 25, player_y
    sp = bullet_speed
    cyan, pink = (244, 233, 206), (255, 106, 61)
    if b_type == 1:
        add_pbullet(cx, cy, 0, -sp, cyan)
        play(sfx_laser_single)
    elif b_type == 2:
        add_pbullet(player_x + 12, cy + 8, 0, -sp, cyan)
        add_pbullet(player_x + 38, cy + 8, 0, -sp, cyan)
        play(sfx_laser_double)
    elif b_type == 3:
        add_pbullet(player_x + 4, cy + 20, 0, -sp, cyan)
        add_pbullet(cx, cy + 6, 0, -sp, cyan)
        add_pbullet(player_x + 46, cy + 20, 0, -sp, cyan)
        play(sfx_laser_triple)
    else:
        for rad in SPREAD_ANGLES.get(b_type, SPREAD_ANGLES[5]):
            add_pbullet(cx, cy + 5, sp * math.sin(rad), -sp * math.cos(rad), pink)
        play(sfx_laser_hexa)


def enemy_bullet_speed():
    return max(3.5, 5.5 * difficulties[current_difficulty]["speed_mod"])


def enemy_fire_aimed(ex, ey, speed):
    ang = math.atan2((player_y + 25) - ey, (player_x + 25) - ex)
    enemy_bullets.append({"x": ex, "y": ey, "vx": speed * math.cos(ang), "vy": speed * math.sin(ang)})


def boss_shoot(boss):
    cx, by = boss["rect"].centerx, boss["rect"].bottom - 15
    sp = enemy_bullet_speed()
    ratio = boss["hp"] / boss["max_hp"]
    if ratio > 0.6:
        for off in (-22, 22):
            enemy_bullets.append({"x": cx + off, "y": by, "vx": 0, "vy": sp})
    elif ratio > 0.3:
        for a in (-0.5, -0.25, 0, 0.25, 0.5):
            enemy_bullets.append({"x": cx, "y": by, "vx": sp * math.sin(a), "vy": sp * math.cos(a)})
    else:
        for a in (-0.7, -0.35, 0, 0.35, 0.7):
            enemy_bullets.append({"x": cx, "y": by, "vx": sp * math.sin(a), "vy": sp * math.cos(a)})
        enemy_fire_aimed(cx, by, sp * 1.15)


def spawn_boss():
    global current_boss, banner_text, banner_timer
    hp = 100 + level * 40
    rect = pygame.Rect(WIDTH // 2 - 60, -120, 120, 90)
    current_boss = {"rect": rect, "x": float(rect.x), "y": -120.0, "hp": hp, "max_hp": hp,
                    "vx": 2.5 + min(3.0, level * 0.03), "shoot_timer": 0}
    banner_text, banner_timer = "CẢNH BÁO! TRÙM XUẤT HIỆN", 140
    play(sfx_warning)


def kill_boss():
    global current_boss, level, level_score_start, banner_text, banner_timer
    b = current_boss
    diff = difficulties[current_difficulty]
    create_explosion(b["rect"].centerx, b["rect"].centery, (255, 215, 0), 60)
    play(sfx_level_up)
    add_coins(int(100 * level * diff["coin_mod"]))
    add_score(100)
    spawn_powerup(b["rect"].centerx, b["rect"].centery, force=True)
    current_boss = None
    enemies.clear()
    enemy_bullets.clear()
    if level >= MAX_LEVELS:
        end_run(True)
    else:
        level += 1
        level_score_start = score
        banner_text, banner_timer = f"MÀN {level}", 110
        save_game_data()


def spawn_enemy():
    types = [1, 2] + ([3] if level >= 3 else [])
    weights = [0.45, 0.4, 0.15] if level >= 3 else [0.5, 0.5]
    t = random.choices(types, weights=weights)[0]
    x = random.randint(40, WIDTH - 80)
    rect = pygame.Rect(x, -40, 40, 40)
    enemies.append({"rect": rect, "type": t, "x": float(x), "y": -40.0, "init_x": x,
                    "phase": random.uniform(0, math.pi * 2), "seed": random.randint(0, 1000),
                    "hp": 2 if t == 3 else 1, "shoot_cd": random.randint(50, 110)})


def update_game():
    global player_x, player_y, cooldown_timer, spawn_timer
    global temp_weapon_timer, temp_weapon_type, shield_timer, invincible_timer, banner_timer
    global player_hp

    diff = difficulties[current_difficulty]
    keys = pygame.key.get_pressed()
    dx = int(bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])) - int(bool(keys[pygame.K_LEFT] or keys[pygame.K_a]))
    dy = int(bool(keys[pygame.K_DOWN] or keys[pygame.K_s])) - int(bool(keys[pygame.K_UP] or keys[pygame.K_w]))
    spd = player_speed * (0.7071 if dx and dy else 1.0)
    player_x = max(0, min(WIDTH - 50, player_x + dx * spd))
    player_y = max(0, min(HEIGHT - 50, player_y + dy * spd))

    if invincible_timer > 0:
        invincible_timer -= 1
    if shield_timer > 0:
        shield_timer -= 1
    if temp_weapon_timer > 0:
        temp_weapon_timer -= 1
    if banner_timer > 0:
        banner_timer -= 1

    create_engine_thruster(player_x + 19, player_y + 44)
    create_engine_thruster(player_x + 31, player_y + 44)

    # --- Bắn ---
    cooldown_timer += 1
    wants_fire = pygame.mouse.get_pressed()[0] or auto_fire or keys[pygame.K_j]
    delay = 8 if effective_bullet_type() < 5 else 10
    if wants_fire and cooldown_timer >= delay:
        cooldown_timer = 0
        fire_player_bullets()

    hitbox = pygame.Rect(int(player_x) + 12, int(player_y) + 8, 26, 34)
    player_rect = pygame.Rect(int(player_x), int(player_y), 50, 50)

    # --- Trùm ---
    global current_boss
    if current_boss is None and (score - level_score_start) >= SCORE_PER_LEVEL:
        spawn_boss()
    if current_boss:
        b = current_boss
        if b["y"] < 50:
            b["y"] += 2
        else:
            b["x"] += b["vx"]
            if b["x"] <= 10 or b["x"] + 120 >= WIDTH - 10:
                b["vx"] *= -1
            b["shoot_timer"] += 1
            interval = max(14, int((45 - level * 0.3) * diff["spawn_mod"]))
            if b["hp"] / b["max_hp"] < 0.3:
                interval = int(interval * 0.75)
            if b["shoot_timer"] >= interval:
                b["shoot_timer"] = 0
                boss_shoot(b)
        b["rect"].x, b["rect"].y = int(b["x"]), int(b["y"])
        if hitbox.colliderect(b["rect"]):
            damage_player()
            if state != "PLAYING":
                return

    # --- Địch ---
    enemy_speed = min(7.0, (2.2 + level * 0.1) * diff["speed_mod"])
    spawn_rate = max(10, int((35 - level * 0.2) * diff["spawn_mod"]))
    if not current_boss:
        spawn_timer += 1
        if spawn_timer >= spawn_rate:
            spawn_timer = 0
            spawn_enemy()

    for e in enemies[:]:
        e["y"] += enemy_speed * (0.7 if e["type"] == 3 else 1.0)
        e["x"] = e["init_x"] + math.sin(e["y"] * 0.03 + e["phase"]) * 40
        e["x"] = max(0, min(WIDTH - 40, e["x"]))
        e["rect"].x, e["rect"].y = int(e["x"]), int(e["y"])

        if e["type"] == 3 and e["y"] > 0 and e["y"] < player_y - 80:
            e["shoot_cd"] -= 1
            if e["shoot_cd"] <= 0:
                e["shoot_cd"] = max(45, int(110 * diff["spawn_mod"]) - level)
                enemy_fire_aimed(e["rect"].centerx, e["rect"].bottom, enemy_bullet_speed() * 0.9)

        if hitbox.colliderect(e["rect"]):
            create_explosion(e["rect"].centerx, e["rect"].centery, (255, 90, 60))
            enemies.remove(e)
            damage_player()
            if state != "PLAYING":
                return
        elif e["rect"].top > HEIGHT:
            enemies.remove(e)

    # --- Đạn người chơi ---
    alive = []
    for bl in bullets:
        bl["x"] += bl["vx"]
        bl["y"] += bl["vy"]
        if bl["y"] < -30 or bl["y"] > HEIGHT + 30 or bl["x"] < -30 or bl["x"] > WIDTH + 30:
            continue
        brect = pygame.Rect(int(bl["x"]) - 4, int(bl["y"]) - 10, 8, 20)
        hit = False
        if current_boss and brect.colliderect(current_boss["rect"]):
            hit = True
            current_boss["hp"] -= 10
            create_explosion(bl["x"], bl["y"], (244, 233, 206), 4, sound=False)
            if current_boss["hp"] <= 0:
                kill_boss()
        else:
            for e in enemies:
                if e["hp"] > 0 and brect.colliderect(e["rect"]):
                    e["hp"] -= 1
                    hit = True
                    create_explosion(bl["x"], bl["y"], (244, 233, 206), 3, sound=False)
                    break
        if not hit:
            alive.append(bl)
    bullets[:] = alive
    if state != "PLAYING":
        return

    for e in enemies[:]:
        if e["hp"] <= 0:
            add_score(30 if e["type"] == 3 else 15)
            add_coins(int((8 if e["type"] == 3 else 5) * diff["coin_mod"]))
            create_explosion(e["rect"].centerx, e["rect"].centery, (255, 200, 64))
            spawn_powerup(e["rect"].centerx, e["rect"].centery)
            enemies.remove(e)

    # --- Đạn địch ---
    alive = []
    for eb in enemy_bullets:
        eb["x"] += eb["vx"]
        eb["y"] += eb["vy"]
        if eb["y"] > HEIGHT + 20 or eb["y"] < -40 or eb["x"] < -20 or eb["x"] > WIDTH + 20:
            continue
        if pygame.Rect(int(eb["x"]) - 5, int(eb["y"]) - 5, 10, 10).colliderect(hitbox):
            damage_player()
            if state != "PLAYING":
                return
            continue
        alive.append(eb)
    enemy_bullets[:] = alive

    # --- Vật phẩm ---
    for p in powerups[:]:
        p["y"] += 2
        if p["y"] > HEIGHT:
            powerups.remove(p)
            continue
        if player_rect.colliderect(pygame.Rect(int(p["x"]), int(p["y"]), 26, 26)):
            play(sfx_powerup)
            kind = p["type"]
            if kind == "HP":
                if player_hp < MAX_HP:
                    player_hp += 1
                else:
                    add_coins(15)
            elif kind == "SHIELD":
                shield_timer = SHIELD_FRAMES
            elif kind == "COIN":
                add_coins(int(20 * diff["coin_mod"]))
            else:
                new_type = {"DOUBLE": 2, "TRIPLE": 3, "HEXA": 5}[kind]
                if temp_weapon_timer <= 0 or new_type >= temp_weapon_type:
                    temp_weapon_type = new_type
                temp_weapon_timer = TEMP_WEAPON_FRAMES
            powerups.remove(p)


# ==========================================================
# XÁC THỰC
# ==========================================================
USERNAME_RE = re.compile(r"[\w\-.]{3,16}")


def process_auth_action():
    global current_user, state, auth_message, auth_msg_color, input_username, input_password
    username = input_username.strip()
    password = input_password

    if not username or not password:
        auth_message, auth_msg_color = "Vui lòng nhập đầy đủ Tên & Mật khẩu!", (255, 80, 80)
        return

    users = load_users()
    if auth_mode == "LOGIN":
        stored = users.get(username)
        if isinstance(stored, str) and verify_password(password, stored):
            if is_legacy_hash(stored):  # nâng cấp MD5 -> PBKDF2
                users[username] = hash_password(password)
                save_users(users)
            current_user = username
            apply_loaded_user_data(username)
            state, auth_message = "MENU", ""
            input_password = ""
            play(sfx_level_up)
        else:
            auth_message, auth_msg_color = "Tài khoản hoặc mật khẩu không chính xác!", (255, 80, 80)
    else:
        if not USERNAME_RE.fullmatch(username):
            auth_message, auth_msg_color = "Tên 3-16 ký tự: chữ, số, '-', '_' hoặc '.'", (255, 80, 80)
        elif len(password) < 4:
            auth_message, auth_msg_color = "Mật khẩu cần ít nhất 4 ký tự!", (255, 80, 80)
        elif username in users:
            auth_message, auth_msg_color = "Tài khoản này đã tồn tại!", (255, 80, 80)
        else:
            users[username] = hash_password(password)
            save_users(users)
            current_user = username
            apply_loaded_user_data(username)
            save_game_data()
            state, auth_message = "MENU", ""
            input_password = ""
            play(sfx_level_up)


def logout():
    global current_user, input_username, input_password, state, show_settings_popup, auth_message
    save_game_data()
    current_user = None
    input_username, input_password = "", ""
    auth_message = ""
    state = "LOGIN_REGISTER"
    show_settings_popup = False


# ==========================================================
# SHOP
# ==========================================================
def item_cost(item):
    if item["type"] == -1:
        return item["cost"] * (1 + (bullet_speed - BULLET_SPEED_MIN) // 4)
    if item["type"] == -2:
        return item["cost"] * (start_hp - START_HP_MIN + 1)
    return item["cost"]


def item_maxed(item):
    t = item["type"]
    if t == -1:
        return bullet_speed >= BULLET_SPEED_MAX
    if t == -2:
        return start_hp >= START_HP_MAX
    return bullet_type >= t


def try_buy_weapon(item):
    global coins, bullet_type, bullet_speed, start_hp
    if item_maxed(item):
        set_toast("Đã đạt mức tối đa!", False)
        return
    cost = item_cost(item)
    if coins < cost:
        set_toast(f"Không đủ xu! Cần {cost}", False)
        return
    coins -= cost
    if item["type"] == -1:
        bullet_speed = min(BULLET_SPEED_MAX, bullet_speed + 4)
        play(sfx_powerup)
    elif item["type"] == -2:
        start_hp = min(START_HP_MAX, start_hp + 1)
        play(sfx_powerup)
    else:
        bullet_type = item["type"]
        play(sfx_level_up)
    set_toast("Mua thành công!", True)
    save_game_data()


def try_buy_or_select_skin(s_id):
    global current_skin_id, coins
    sk = skins[s_id]
    if sk["unlocked"]:
        current_skin_id = s_id
        save_game_data()
        play(sfx_powerup)
    elif coins >= sk["price"]:
        coins -= sk["price"]
        sk["unlocked"] = True
        current_skin_id = s_id
        save_game_data()
        play(sfx_level_up)
        set_toast("Mở khóa skin mới!", True)
    else:
        set_toast(f"Không đủ xu! Cần {sk['price']}", False)


# ==========================================================
# XỬ LÝ SỰ KIỆN
# ==========================================================
def handle_login_event(event):
    global active_field, auth_mode, auth_message, input_username, input_password
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = event.pos
        if R["auth_user"].collidepoint(pos):
            active_field = "username"
        elif R["auth_pass"].collidepoint(pos):
            active_field = "password"
        elif R["auth_action"].collidepoint(pos):
            process_auth_action()
        elif R["auth_switch"].collidepoint(pos):
            auth_mode = "REGISTER" if auth_mode == "LOGIN" else "LOGIN"
            auth_message = ""
    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_TAB:
            active_field = "password" if active_field == "username" else "username"
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if active_field == "username" and not input_password:
                active_field = "password"
            else:
                process_auth_action()
        elif event.key == pygame.K_BACKSPACE:
            if active_field == "username":
                input_username = input_username[:-1]
            else:
                input_password = input_password[:-1]
        elif event.unicode and event.unicode.isprintable():
            if active_field == "username" and len(input_username) < 16:
                input_username += event.unicode
            elif active_field == "password" and len(input_password) < 16:
                input_password += event.unicode


def handle_keydown(key):
    global state, auto_fire
    if key in (pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_p):
        if state == "PLAYING":
            state = "PAUSED"
        elif state == "PAUSED":
            state = "PLAYING"
        elif key == pygame.K_ESCAPE and state in ("PROFILE", "SELECT_DIFFICULTY", "SHOP_WEAPON", "SHOP_SKIN"):
            state = "MENU"
    elif key == pygame.K_m:
        set_muted(not muted)
        save_game_data()
    elif key == pygame.K_f and state in ("PLAYING", "PAUSED"):
        auto_fire = not auto_fire


def handle_click(pos):
    global state, show_settings_popup, running, current_difficulty
    if state == "MENU":
        if show_settings_popup:
            if R["pop_sound"].collidepoint(pos):
                set_muted(not muted)
                save_game_data()
                return
            if R["pop_logout"].collidepoint(pos):
                logout()
                return
            if R["pop_quit"].collidepoint(pos):
                save_game_data()
                running = False
                return
        if R["settings"].collidepoint(pos):
            show_settings_popup = not show_settings_popup
            return
        show_settings_popup = False
        if R["diff"].collidepoint(pos):
            state = "SELECT_DIFFICULTY"
        elif R["profile"].collidepoint(pos):
            state = "PROFILE"
        elif R["play"].collidepoint(pos):
            reset_match()
            state = "PLAYING"
        elif R["shop_skin"].collidepoint(pos):
            state = "SHOP_SKIN"
        elif R["shop_weapon"].collidepoint(pos):
            state = "SHOP_WEAPON"

    elif state == "PROFILE":
        if R["profile_back"].collidepoint(pos):
            state = "MENU"

    elif state == "SELECT_DIFFICULTY":
        for idx, k in enumerate(("EASY", "NORMAL", "HARD")):
            if diff_rect(idx).collidepoint(pos):
                current_difficulty = k
                save_game_data()
                state = "MENU"
                return
        if R["diff_back"].collidepoint(pos):
            state = "MENU"

    elif state == "SHOP_WEAPON":
        for idx, item in enumerate(weapon_shop_items):
            if weapon_card_rect(idx).collidepoint(pos):
                try_buy_weapon(item)
                return
        if R["shop_tab"].collidepoint(pos):
            state = "SHOP_SKIN"
        elif R["shop_back"].collidepoint(pos):
            state = "MENU"

    elif state == "SHOP_SKIN":
        for sk_id in skins:
            if skin_card_rect(sk_id).collidepoint(pos):
                try_buy_or_select_skin(sk_id)
                return
        if R["shop_tab"].collidepoint(pos):
            state = "SHOP_WEAPON"
        elif R["shop_back"].collidepoint(pos):
            state = "MENU"

    elif state == "PAUSED":
        if R["pause_resume"].collidepoint(pos):
            state = "PLAYING"
        elif R["pause_menu"].collidepoint(pos):
            save_game_data()
            state = "MENU"

    elif state in ("GAME_OVER", "VICTORY"):
        if R["end_retry"].collidepoint(pos):
            reset_match()
            state = "PLAYING"
        elif R["end_menu"].collidepoint(pos):
            state = "MENU"


# ==========================================================
# MÀN HÌNH
# ==========================================================
SPLASH_DURATION = 150
splash_timer = 0


def draw_splash(surface, timer):
    alpha = 255
    if timer < 30:
        alpha = int(timer / 30 * 255)
    elif timer > SPLASH_DURATION - 30:
        alpha = int((SPLASH_DURATION - timer) / 30 * 255)
    alpha = max(0, min(255, alpha))

    layer = pygame.Surface((WIDTH, HEIGHT))
    layer.fill(C_BG)
    cx, cy = WIDTH // 2, HEIGHT // 2 - 60
    bob = int(math.sin(timer * 0.12) * 5)
    ship = pygame.transform.scale(get_ship_surface(1), (144, 144))
    layer.blit(ship, (cx - 72, cy - 72 + bob))
    for dx in (-12, 12):
        pygame.draw.rect(layer, C_ORANGE, (cx + dx - 4, cy + 72 + bob, 8, 10 + (timer // 3) % 3 * 4))
    blit_text(layer, font_small, "MADE WITH", C_DIM, midtop=(cx, cy + 112))
    blit_text(layer, font_large, "CON CẶC", C_CREAM, shadow=SHADOW_RED, midtop=(cx, cy + 132)) # Thay đổi made with tùy m thích 

    progress = min(1.0, timer / SPLASH_DURATION)
    seg_n, seg_w, gap = 20, 11, 3
    total = seg_n * (seg_w + gap) - gap
    bx, by = cx - total // 2, cy + 204
    filled = int(seg_n * progress)
    for i in range(seg_n):
        pygame.draw.rect(layer, C_GOLD if i < filled else C_PANEL_HI, (bx + i * (seg_w + gap), by, seg_w, 14))
    blit_text(layer, font_small, f"ĐANG TẢI {int(progress * 100)}%", C_DIM, midtop=(cx, by + 24))
    layer.set_alpha(alpha)
    surface.fill((0, 0, 0))
    surface.blit(layer, (0, 0))


def draw_world():
    draw_thrusters(screen)
    draw_powerups(screen)
    for b in bullets:
        sp = math.hypot(b["vx"], b["vy"]) or 1
        tail = (b["x"] - b["vx"] / sp * 16, b["y"] - b["vy"] / sp * 16)
        pygame.draw.line(screen, b["color"], tail, (b["x"], b["y"]), 4)
        pygame.draw.rect(screen, C_GOLD, (int(b["x"]) - 2, int(b["y"]) - 2, 4, 4))
    for eb in enemy_bullets:
        x, y = int(eb["x"]), int(eb["y"])
        pygame.draw.polygon(screen, C_ORANGE, [(x, y - 6), (x + 6, y), (x, y + 6), (x - 6, y)])
        pygame.draw.rect(screen, C_CREAM, (x - 2, y - 2, 4, 4))
    for e in enemies:
        draw_enemy(screen, e)
    if current_boss:
        draw_boss(screen, current_boss)
    if state != "GAME_OVER":
        blink = invincible_timer > 0 and (invincible_timer // 5) % 2 == 0
        if not blink:
            draw_player(screen, player_x, player_y, current_skin_id)
        if shield_timer > 0 and (shield_timer > 90 or (shield_timer // 6) % 2 == 0):
            draw_shield_bubble(screen, player_x, player_y)
    draw_particles(screen)


def draw_timer_bar(y, label, frames, total, color):
    blit_text(screen, font_tiny, label, color, shadow=C_INK, topleft=(15, y))
    segs = 10
    on = max(1, int(segs * frames / total + 0.99))
    for i in range(segs):
        pygame.draw.rect(screen, color if i < on else C_PANEL_HI, (66 + i * 8, y + 2, 6, 9))


def draw_hud():
    blit_text(screen, font_medium, f"ĐIỂM {score:06d}", C_CREAM, shadow=C_INK, topleft=(15, 12))
    blit_text(screen, font_medium, f"XU {coins}", C_GOLD, shadow=C_INK, topleft=(15, 36))
    for i in range(max(start_hp, player_hp)):
        draw_heart(screen, 15 + i * 25, 62, i < player_hp)
    y = 90
    if temp_weapon_timer > 0:
        draw_timer_bar(y, f"{temp_weapon_type}X", temp_weapon_timer, TEMP_WEAPON_FRAMES, C_GOLD)
        y += 16
    if shield_timer > 0:
        draw_timer_bar(y, "KHIÊN", shield_timer, SHIELD_FRAMES, C_MINT)

    blit_text(screen, font_medium, f"MÀN {level}/{MAX_LEVELS}", C_CREAM, shadow=C_INK, topright=(WIDTH - 15, 12))
    d = difficulties[current_difficulty]
    blit_text(screen, font_tiny, d["name"], d["color"], shadow=C_INK, topright=(WIDTH - 15, 34))
    if auto_fire:
        blit_text(screen, font_tiny, "TỰ ĐỘNG BẮN", C_MINT, shadow=C_INK, topright=(WIDTH - 15, 48))

    prog = 0.0 if current_boss else min(1.0, (score - level_score_start) / SCORE_PER_LEVEL)
    seg_n = 30
    seg_w = WIDTH / seg_n
    filled = int(seg_n * prog)
    for i in range(seg_n):
        pygame.draw.rect(screen, C_ORANGE if i < filled else C_PANEL, (int(i * seg_w) + 1, HEIGHT - 9, int(seg_w) - 2, 6))

    if banner_timer > 0:
        col = C_RED if current_boss else C_GOLD
        if current_boss and (banner_timer // 8) % 2:
            col = C_CREAM
        img = font_large.render(banner_text, False, col)
        sh = font_large.render(banner_text, False, C_INK)
        comp = pygame.Surface((img.get_width() + 3, img.get_height() + 3), pygame.SRCALPHA)
        comp.blit(sh, (3, 3))
        comp.blit(img, (0, 0))
        comp.set_alpha(min(255, banner_timer * 6))
        screen.blit(comp, comp.get_rect(center=(WIDTH // 2, HEIGHT // 3)))


def draw_toast():
    if toast_timer > 0:
        img = font_small.render(toast_msg, False, toast_color)
        img.set_alpha(min(255, toast_timer * 8))
        screen.blit(img, img.get_rect(midtop=(WIDTH // 2, 90)))


def draw_login(m_pos):
    draw_panel(screen, pygame.Rect(40, 60, WIDTH - 80, 580))
    title = "ĐĂNG NHẬP" if auth_mode == "LOGIN" else "ĐĂNG KÝ TÀI KHOẢN"
    blit_text(screen, font_large, title, C_GOLD, shadow=SHADOW_RED, midtop=(WIDTH // 2, 90))
    screen.blit(get_ship_surface(current_skin_id), (WIDTH // 2 - 24, 150))
    blink = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""

    fields = (("auth_user", "username", "Tên tài khoản:", input_username, (90, 235)),
              ("auth_pass", "password", "Mật khẩu:", "*" * len(input_password), (90, 315)))
    for key, field, label, value, pos in fields:
        blit_text(screen, font_small, label, C_DIM, topleft=pos)
        rect = R[key]
        act = active_field == field
        pygame.draw.rect(screen, C_INK, rect)
        pygame.draw.rect(screen, C_GOLD if act else C_DIM, rect, 2)
        blit_text(screen, font_medium, value + (blink if act else ""), C_CREAM, midleft=(rect.x + 10, rect.centery))

    draw_button(screen, R["auth_action"], "ĐĂNG NHẬP" if auth_mode == "LOGIN" else "TẠO TÀI KHOẢN", font_medium,
                R["auth_action"].collidepoint(m_pos), kind="primary")
    sw = "Chưa có tài khoản? Đăng ký ngay" if auth_mode == "LOGIN" else "Đã có tài khoản? Đăng nhập"
    blit_text(screen, font_small, sw, C_GOLD if R["auth_switch"].collidepoint(m_pos) else C_DIM, center=R["auth_switch"].center)
    if auth_message:
        blit_text(screen, font_small, auth_message, C_ORANGE, midtop=(WIDTH // 2, 525))
    blit_text(screen, font_tiny, "Tab: đổi ô | Enter: xác nhận | M: âm thanh", C_DIM, midtop=(WIDTH // 2, 600))


def draw_menu(m_pos):
    blit_text(screen, font_title, "Chan Nhau Trên Không Gian", C_GOLD, shadow=SHADOW_RED, midtop=(WIDTH // 2, 22))
    pygame.draw.rect(screen, C_ORANGE, (WIDTH // 2 - 150, 58, 300, 3))

    d = difficulties[current_difficulty]
    hov = R["diff"].collidepoint(m_pos)
    draw_panel(screen, R["diff"], C_PANEL_HI if hov else C_PANEL, d["color"] if hov else C_DIM, sh=3)
    blit_text(screen, font_tiny, "ĐỘ KHÓ", C_DIM, midtop=(R["diff"].centerx, R["diff"].top + 5))
    blit_text(screen, font_medium, d["name"], d["color"], midtop=(R["diff"].centerx, R["diff"].top + 20))

    pr = R["profile"]
    hov = pr.collidepoint(m_pos)
    draw_panel(screen, pr, C_PANEL_HI if hov else C_PANEL, C_GOLD if hov else C_DIM, sh=3)
    pygame.draw.rect(screen, C_CREAM, (pr.x + 16, pr.y + 9, 12, 12))
    pygame.draw.rect(screen, C_CREAM, (pr.x + 11, pr.y + 24, 22, 10))
    name = (current_user[:9] + "..") if len(current_user) > 9 else current_user
    blit_text(screen, font_small, name.upper(), C_CREAM, topleft=(pr.x + 42, pr.y + 4))
    blit_text(screen, font_tiny, f"Xu {coins} | KL {high_score}", C_GOLD, topleft=(pr.x + 42, pr.y + 24))

    st = R["settings"]
    hov = st.collidepoint(m_pos)
    draw_panel(screen, st, C_PANEL_HI if hov else C_PANEL, C_GOLD if hov else C_DIM, sh=3)
    draw_gear_icon(screen, st.centerx, st.centery, color=C_GOLD if hov else C_CREAM)

    draw_menu_animated_rocket(screen)

    bob = int(math.sin(pygame.time.get_ticks() * 0.004) * 4)
    ship = pygame.transform.scale(get_ship_surface(current_skin_id), (96, 96))
    sx, sy = WIDTH // 2 - 48, HEIGHT // 2 - 40 + bob
    for dx in (-8, 8):
        pygame.draw.rect(screen, random.choice([C_ORANGE, C_GOLD]), (WIDTH // 2 + dx - 3, sy + 90, 6, random.randint(8, 16)))
    screen.blit(ship, (sx, sy))
    plate = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 + 86, 120, 6)
    pygame.draw.rect(screen, C_DIM, plate)
    pygame.draw.rect(screen, C_INK, plate.move(0, 6))

    draw_button(screen, R["shop_skin"], "Shop Skin", font_small, R["shop_skin"].collidepoint(m_pos))
    draw_button(screen, R["play"], "BẮT ĐẦU", font_large, R["play"].collidepoint(m_pos), kind="primary")
    draw_button(screen, R["shop_weapon"], "Shop Vũ Khí", font_small, R["shop_weapon"].collidepoint(m_pos))

    blit_text(screen, font_tiny, "WASD/Mũi tên: bay | Chuột/J: bắn | F: tự bắn", C_DIM, midbottom=(WIDTH // 2, HEIGHT - 24))
    blit_text(screen, font_tiny, "ESC/Space: tạm dừng | M: bật/tắt âm thanh", C_DIM, midbottom=(WIDTH // 2, HEIGHT - 8))

    if show_settings_popup:
        draw_panel(screen, R["pop_frame"], C_PANEL, C_GOLD)
        draw_button(screen, R["pop_sound"], f"Âm thanh: {'TẮT' if muted else 'BẬT'}", font_small, R["pop_sound"].collidepoint(m_pos))
        draw_button(screen, R["pop_logout"], "Đổi Tài Khoản", font_small, R["pop_logout"].collidepoint(m_pos))
        draw_button(screen, R["pop_quit"], "Thoát Game", font_small, R["pop_quit"].collidepoint(m_pos), kind="danger")


def draw_profile(m_pos):
    draw_panel(screen, pygame.Rect(40, 50, WIDTH - 80, HEIGHT - 100))
    blit_text(screen, font_large, "TRANG CÁ NHÂN", C_GOLD, shadow=SHADOW_RED, midtop=(WIDTH // 2, 70))
    cx = WIDTH // 2
    pygame.draw.rect(screen, C_CREAM, (cx - 18, 122, 36, 36))
    pygame.draw.rect(screen, C_INK, (cx - 9, 134, 5, 5))
    pygame.draw.rect(screen, C_INK, (cx + 4, 134, 5, 5))
    pygame.draw.rect(screen, C_CREAM, (cx - 32, 164, 64, 22))
    blit_text(screen, font_large, current_user.upper(), C_CREAM, shadow=C_INK, midtop=(cx, 196))

    box = pygame.Rect(60, 244, WIDTH - 120, 276)
    draw_panel(screen, box, C_PANEL_HI, C_DIM, sh=0)
    d = difficulties[current_difficulty]
    rows = [
        ("Tiền xu", str(coins), C_GOLD),
        ("Kỷ lục cao nhất", str(high_score), C_ORANGE),
        ("Skin đang dùng", skins[current_skin_id]["name"], C_PINK),
        ("Cấp độ đạn", f"Cấp {bullet_type}", C_CREAM),
        ("Tốc độ đạn", str(bullet_speed), C_MINT),
        ("Máu khởi đầu", str(start_hp), C_RED),
        ("Độ khó", d["name"], d["color"]),
    ]
    for idx, (label, value, col) in enumerate(rows):
        y = box.y + 18 + idx * 36
        pygame.draw.rect(screen, col, (box.x + 16, y + 3, 9, 9))
        blit_text(screen, font_small, label, C_DIM, topleft=(box.x + 38, y))
        blit_text(screen, font_small, value, col, topright=(box.right - 20, y))

    draw_button(screen, R["profile_back"], "QUAY LẠI MENU", font_small, R["profile_back"].collidepoint(m_pos))


def draw_back_button(rect, m_pos):
    draw_button(screen, rect, "QUAY LẠI MENU", font_small, rect.collidepoint(m_pos), kind="danger")


def draw_difficulty(m_pos):
    draw_panel(screen, pygame.Rect(40, 60, WIDTH - 80, HEIGHT - 120))
    blit_text(screen, font_large, "CHỌN ĐỘ KHÓ", C_GOLD, shadow=SHADOW_RED, midtop=(WIDTH // 2, 90))
    for idx, k in enumerate(("EASY", "NORMAL", "HARD")):
        d = difficulties[k]
        rect = diff_rect(idx)
        hov = rect.collidepoint(m_pos)
        sel = k == current_difficulty
        draw_panel(screen, rect, d["color"] if sel else (C_PANEL_HI if hov else C_PANEL), d["color"], sh=3)
        tcol = C_INK if sel else d["color"]
        blit_text(screen, font_medium, d["name"], tcol, center=(rect.centerx, rect.centery - 9))
        blit_text(screen, font_tiny, f"Xu thưởng x{d['coin_mod']}", C_INK if sel else C_DIM, center=(rect.centerx, rect.centery + 12))
    draw_back_button(R["diff_back"], m_pos)


def draw_shop_weapon(m_pos):
    draw_panel(screen, pygame.Rect(20, 20, WIDTH - 40, HEIGHT - 40))
    blit_text(screen, font_large, "SHOP VŨ KHÍ", C_GOLD, shadow=SHADOW_RED, midtop=(WIDTH // 2, 28))
    blit_text(screen, font_medium, f"XU CÓ SẴN: {coins}", C_CREAM, midtop=(WIDTH // 2, 64))
    for idx, item in enumerate(weapon_shop_items):
        card = weapon_card_rect(idx)
        hov = card.collidepoint(m_pos)
        maxed = item_maxed(item)
        border = C_MINT if maxed else (C_GOLD if hov else C_DIM)
        draw_panel(screen, card, C_PANEL_HI if hov else C_PANEL, border, sh=3)
        col = C_MINT if maxed else C_CREAM
        status = " (ĐÃ CÓ)" if (maxed and item["type"] > 0) else (" (TỐI ĐA)" if maxed else f" - {item_cost(item)} Xu")
        blit_text(screen, font_medium, item["name"] + status, col, topleft=(card.x + 10, card.y + 8))
        blit_text(screen, font_tiny, item["desc"], C_DIM, topleft=(card.x + 10, card.y + 32))
        draw_bullet_preview(screen, WIDTH - 125, card.y, item["type"], 80, card.height)
    draw_toast()
    draw_button(screen, R["shop_tab"], "SANG SHOP SKIN PHI THUYỀN", font_small, R["shop_tab"].collidepoint(m_pos))
    draw_back_button(R["shop_back"], m_pos)


def draw_shop_skin(m_pos):
    draw_panel(screen, pygame.Rect(20, 20, WIDTH - 40, HEIGHT - 40))
    blit_text(screen, font_large, "SHOP SKIN", C_GOLD, shadow=SHADOW_RED, midtop=(WIDTH // 2, 28))
    blit_text(screen, font_medium, f"XU CÓ SẴN: {coins}", C_CREAM, midtop=(WIDTH // 2, 64))
    for sk_id, sk in skins.items():
        card = skin_card_rect(sk_id)
        hov = card.collidepoint(m_pos)
        active = sk_id == current_skin_id
        border = C_MINT if active else (C_GOLD if hov else (C_CREAM if sk["unlocked"] else C_DIM))
        draw_panel(screen, card, C_PANEL_HI if hov else C_PANEL, border, sh=3)
        draw_player(screen, WIDTH - 110, card.y + 22, sk_id)
        status = "ĐANG CHỌN" if active else ("ĐÃ SỞ HỮU (CLICK CHỌN)" if sk["unlocked"] else f"GIÁ: {sk['price']} XU")
        blit_text(screen, font_medium, sk["name"], C_CREAM, topleft=(card.x + 15, card.y + 10))
        blit_text(screen, font_small, status, C_MINT if sk["unlocked"] else C_GOLD, topleft=(card.x + 15, card.y + 36))
        blit_text(screen, font_tiny, sk["desc"], C_DIM, topleft=(card.x + 15, card.y + 62))
    draw_toast()
    draw_button(screen, R["shop_tab"], "SANG SHOP VŨ KHÍ", font_small, R["shop_tab"].collidepoint(m_pos))
    draw_back_button(R["shop_back"], m_pos)


def draw_pause(m_pos):
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((6, 4, 14, 160))
    screen.blit(veil, (0, 0))
    draw_panel(screen, R["pause_frame"], C_PANEL, C_GOLD)
    f = R["pause_frame"]
    blit_text(screen, font_large, "TẠM DỪNG", C_GOLD, shadow=SHADOW_RED, midtop=(WIDTH // 2, f.y + 14))
    hints = ["WASD / Mũi tên: di chuyển", "Chuột trái / J: bắn", "F: bật/tắt tự động bắn",
             "M: bật/tắt âm thanh", "ESC / Space / P: tạm dừng"]
    for i, h in enumerate(hints):
        blit_text(screen, font_small, h, C_CREAM, midtop=(WIDTH // 2, f.y + 66 + i * 22))
    draw_button(screen, R["pause_resume"], "TIẾP TỤC", font_small, R["pause_resume"].collidepoint(m_pos), kind="primary")
    draw_button(screen, R["pause_menu"], "VỀ MENU", font_small, R["pause_menu"].collidepoint(m_pos), kind="danger")


def draw_end_screen(m_pos, victory):
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((6, 4, 14, 140))
    screen.blit(veil, (0, 0))
    if victory:
        draw_panel(screen, pygame.Rect(40, HEIGHT // 2 - 160, WIDTH - 80, 300), C_PANEL, C_MINT)
        blit_text(screen, font_large, "PHÁ ĐẢO GAME!", C_GOLD, shadow=SHADOW_RED, midtop=(WIDTH // 2, HEIGHT // 2 - 130))
        blit_text(screen, font_medium, f"Đã vượt qua toàn bộ {MAX_LEVELS} màn!", C_MINT, midtop=(WIDTH // 2, HEIGHT // 2 - 85))
        blit_text(screen, font_medium, f"Tổng điểm: {score}", C_CREAM, midtop=(WIDTH // 2, HEIGHT // 2 - 55))
        blit_text(screen, font_small, f"Kỷ lục cao nhất: {high_score}", C_GOLD, midtop=(WIDTH // 2, HEIGHT // 2 - 25))
    else:
        draw_panel(screen, pygame.Rect(50, HEIGHT // 2 - 150, WIDTH - 100, 280), C_PANEL, C_RED)
        blit_text(screen, font_large, "GAME OVER", C_RED, shadow=C_INK, midtop=(WIDTH // 2, HEIGHT // 2 - 120))
        blit_text(screen, font_medium, f"Điểm: {score} | Màn: {level}/{MAX_LEVELS}", C_CREAM, midtop=(WIDTH // 2, HEIGHT // 2 - 65))
        blit_text(screen, font_small, f"Kỷ lục cao nhất: {high_score}", C_GOLD, midtop=(WIDTH // 2, HEIGHT // 2 - 30))
        if score >= high_score and score > 0:
            blit_text(screen, font_small, "KỶ LỤC MỚI!", C_MINT, midtop=(WIDTH // 2, HEIGHT // 2 - 5))
    draw_button(screen, R["end_retry"], "CHƠI LẠI", font_medium, R["end_retry"].collidepoint(m_pos), kind="primary")
    draw_button(screen, R["end_menu"], "MENU", font_medium, R["end_menu"].collidepoint(m_pos))


scanlines = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
for _y in range(0, HEIGHT, 3):
    pygame.draw.line(scanlines, (0, 0, 0, 34), (0, _y), (WIDTH, _y))


def present():
    global shake
    ox = oy = 0
    if shake > 0:
        s = max(1, shake // 2)
        ox, oy = random.randint(-s, s), random.randint(-s, s)
        window.fill((0, 0, 0))
    window.blit(screen, (ox, oy))
    window.blit(scanlines, (0, 0))
    pygame.display.flip()


def bgm_for_state(s):
    if s in MENU_STATES:
        return "MENU"
    if s in ("PLAYING", "PAUSED"):
        return "GAME"
    return None


# ==========================================================
# VÒNG LẶP CHÍNH
# ==========================================================
FOCUS_LOST = getattr(pygame, "WINDOWFOCUSLOST", -1)

while running:
    play_bgm(bgm_for_state(state))

    # ---------- Splash ----------
    if state == "SPLASH":
        splash_timer += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                state = "LOGIN_REGISTER"
        if splash_timer >= SPLASH_DURATION:
            state = "LOGIN_REGISTER"
        draw_splash(screen, splash_timer)
        present()
        clock.tick(FPS)
        continue

    # ---------- Sự kiện ----------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game_data()
            running = False
        elif event.type == FOCUS_LOST:
            if state == "PLAYING":
                state = "PAUSED"
        elif state == "LOGIN_REGISTER":
            handle_login_event(event)
        elif event.type == pygame.KEYDOWN:
            handle_keydown(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            handle_click(event.pos)

    # ---------- Cập nhật ----------
    if state == "PLAYING":
        update_game()
    if state != "PAUSED":
        update_stars(True)
        step_particles()
        if shake > 0:
            shake -= 1
    if toast_timer > 0:
        toast_timer -= 1

    autosave_timer += 1
    if autosave_timer >= 600:
        autosave_timer = 0
        if dirty:
            save_game_data()

    # ---------- Vẽ ----------
    m_pos = pygame.mouse.get_pos()
    draw_stars(screen)

    if state in WORLD_STATES:
        draw_world()
        if state in ("PLAYING", "PAUSED"):
            draw_hud()
        if state == "PAUSED":
            draw_pause(m_pos)
        elif state == "GAME_OVER":
            draw_end_screen(m_pos, False)
        elif state == "VICTORY":
            draw_end_screen(m_pos, True)
    else:
        draw_particles(screen)
        if state == "LOGIN_REGISTER":
            draw_login(m_pos)
        elif state == "MENU":
            draw_menu(m_pos)
        elif state == "PROFILE":
            draw_profile(m_pos)
        elif state == "SELECT_DIFFICULTY":
            draw_difficulty(m_pos)
        elif state == "SHOP_WEAPON":
            draw_shop_weapon(m_pos)
        elif state == "SHOP_SKIN":
            draw_shop_skin(m_pos)

    present()
    clock.tick(FPS)

save_game_data()
pygame.quit()
sys.exit()
