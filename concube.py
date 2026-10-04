import json
import math
import os
import queue
import random
import socket
import threading
import time

import numpy as np
import pygame


SERVER_ADDR = "tienkjaz.duckdns.org:5555"

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass
AUDIO = pygame.mixer.get_init() is not None

WIDTH, HEIGHT = 600, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Đại Chiến Không Gian - Online")
clock = pygame.time.Clock()


try:
    pygame.key.start_text_input()
    pygame.key.set_text_input_rect(pygame.Rect(0, HEIGHT // 2, WIDTH, 40))
except Exception:
    pass


CONFIG_FILE = "client_config.json"
DEFAULT_PORT = 5555
MAX_LEVELS = 100
SCORE_PER_LEVEL = 500
FIRE_DELAY = 8
PLAYER_SPEED = 7
MAX_HP = 5
TMP_FRAMES = 600
MAX_BULLET_SPEED = 25
VALID_BULLETS = (1, 2, 3, 4, 5, 10)
CHAT_KEEP = 120
FIELD_MAX = {"user": 16, "pass": 32, "friend": 16, "chat": 200}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ==========================================================
# ÂM THANH
# ==========================================================
SAMPLE_RATE = 44100


class NullSound:
    def play(self, *a, **k): pass
    def stop(self): pass
    def set_volume(self, v): pass


def gen_sound(wave_type="sine", freq=440, dur=0.1, fade=True, slide=0):
    if not AUDIO:
        return NullSound()
    n = max(1, int(SAMPLE_RATE * dur))
    t = np.linspace(0, dur, n, False)
    f = freq + slide * t
    if wave_type == "square":
        w = np.sign(np.sin(2 * np.pi * f * t))
    elif wave_type == "saw":
        w = 2 * (f * t - np.floor(0.5 + f * t))
    elif wave_type == "noise":
        w = np.random.uniform(-1, 1, n)
    else:
        w = np.sin(2 * np.pi * f * t)
    if fade:
        fl = int(n * 0.8)
        if fl > 0:
            env = np.ones(n)
            env[-fl:] = np.linspace(1, 0, fl)
            w = w * env
    a = (w * 12000).astype(np.int16)
    return pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack((a, a))))


def gen_music(pattern, speed=0.15):
    if not AUDIO:
        return NullSound()
    parts = []
    for fr in pattern:
        n = max(1, int(SAMPLE_RATE * speed))
        if fr == 0:
            parts.append(np.zeros((n, 2), dtype=np.int16))
        else:
            t = np.linspace(0, speed, n, False)
            w = 0.4 * np.sin(2 * np.pi * fr * t) + 0.2 * np.sign(np.sin(2 * np.pi * (fr / 2) * t))
            env = np.linspace(1, 0.2, len(t))
            a = (w * env * 6000).astype(np.int16)
            parts.append(np.column_stack((a, a)))
    return pygame.sndarray.make_sound(np.ascontiguousarray(np.concatenate(parts, axis=0)))


SFX = {
    "l1": gen_sound("saw", 600, 0.08, slide=-3000),
    "l2": gen_sound("square", 800, 0.1, slide=-4000),
    "l3": gen_sound("saw", 1100, 0.12, slide=-5000),
    "l4": gen_sound("noise", 1500, 0.15, slide=-6000),
    "explosion": gen_sound("noise", 200, 0.25),
    "powerup": gen_sound("sine", 523, 0.2, slide=2000),
    "levelup": gen_sound("square", 440, 0.4, slide=1200),
    "chat": gen_sound("sine", 880, 0.08, slide=400),
}
BGM = {
    "MENU": gen_music([261, 329, 392, 523, 392, 329, 261, 0, 220, 277, 329, 440, 329, 277], 0.18),
    "GAME": gen_music([150, 150, 300, 150, 150, 350, 150, 150, 400, 350, 300, 200], 0.11),
}
for _s in BGM.values():
    _s.set_volume(0.5)


def snd(name):
    if G.sound_on:
        SFX[name].play()


def play_bgm(which):
    if G.bgm == which:
        return
    for s in BGM.values():
        s.stop()
    if which:
        BGM[which].play(loops=-1)
    G.bgm = which


def apply_sound_setting():
    for s in BGM.values():
        s.set_volume(0.5 if G.sound_on else 0.0)


def load_font(size, bold=False):
    return pygame.font.SysFont("segoeui,arial,dejavusans,notosans,freesans", size, bold=bold)


F_TITLE = load_font(26, True)
F_LARGE = load_font(28, True)
F_MED = load_font(16, True)
F_SMALL = load_font(13)
F_TINY = load_font(11)


# ==========================================================
# DỮ LIỆU
# ==========================================================
DIFFS = {
    "EASY": {"name": "DỄ", "speed_mod": 0.7, "spawn_mod": 1.4, "coin_mod": 1.0, "color": (0, 255, 170)},
    "NORMAL": {"name": "THƯỜNG", "speed_mod": 1.0, "spawn_mod": 1.0, "coin_mod": 1.5, "color": (255, 215, 0)},
    "HARD": {"name": "KHÓ", "speed_mod": 1.4, "spawn_mod": 0.7, "coin_mod": 2.5, "color": (255, 60, 60)},
}
SKINS = {
    1: {"name": "Galaga Classic", "primary": (255, 255, 255), "wing": (200, 30, 30), "price": 0,
        "desc": "Phi thuyền cổ điển."},
    2: {"name": "Neon Fighter", "primary": (0, 255, 200), "wing": (0, 150, 255), "price": 150,
        "desc": "Lazer phát sáng."},
    3: {"name": "Chiến Hạm Vàng", "primary": (255, 215, 0), "wing": (255, 120, 0), "price": 300,
        "desc": "Giáp mạ vàng."},
    4: {"name": "Phượng Hoàng Lửa", "primary": (255, 50, 50), "wing": (255, 200, 0), "price": 500,
        "desc": "Hỏa lực tối đa."},
}
WEAPONS = [
    {"type": 2, "name": "Đạn Đôi", "cost": 150, "desc": "2 tia song song"},
    {"type": 3, "name": "Đạn Ba", "cost": 300, "desc": "3 tia thẳng"},
    {"type": 4, "name": "Đạn Bốn Tỏa", "cost": 500, "desc": "4 tia góc rộng"},
    {"type": 5, "name": "Cánh Bướm (5)", "cost": 800, "desc": "5 tia đều"},
    {"type": 10, "name": "Bão Đạn (10)", "cost": 1500, "desc": "10 hướng"},
    {"type": -1, "name": "Tăng Tốc Đạn (+4)", "cost": 100, "desc": "+4 tốc độ"},
]
POWERUP_COLORS = {"HP": (0, 255, 100), "DOUBLE": (0, 200, 255), "TRIPLE": (255, 200, 0), "HEXA": (255, 50, 200)}
POWERUP_LABELS = {"HP": "HP", "DOUBLE": "2X", "TRIPLE": "3X", "HEXA": "5X"}
POWERUP_WEAPON = {"DOUBLE": 2, "TRIPLE": 3, "HEXA": 5}


# ==========================================================
# STATE
# ==========================================================
class G:
    state = "SPLASH"
    splash = 0
    tick = 0
    bgm = None
    sound_on = True
    mouse = (0, 0)
    net = None
    user = None
    conn_lost = False
    auth_mode = "LOGIN"
    connecting = False
    auth_msg = ""
    auth_color = (255, 80, 80)
    focus = None
    difficulty = "NORMAL"
    popup = False
    friends = {"me_score": 0, "friends": [], "requests": []}
    board = {"top": [], "rank": 0, "total": 0}
    board_tab = "FRIENDS"
    scroll = 0
    invite = None
    in_room = False
    partner = ""
    W = None
    mode = "solo"
    credited = 0
    submitted = False
    got_snapshot = False
    toast_msg = ""
    toast_color = (0, 255, 150)
    toast_until = 0
    save_dirty = False
    last_save = 0.0
    last_ping = 0.0
    last_refresh = 0.0
    input_hook = None
    # chat
    chat_tab = "GLOBAL"
    chat_global = []
    chat_private = {}
    chat_target = None
    chat_unread = {}
    chat_badge_global = 0
    chat_scroll = 0


P = {"coins": 500, "unlocked": {1}, "skin": 1, "bt": 1, "bs": 13, "hs": 0}
fields = {"user": "", "pass": "", "friend": "", "chat": ""}
hits, prev_hits = [], []
particles, thrusters = [], []


def toast(msg, ok=True, secs=3.0):
    G.toast_msg = msg
    G.toast_color = (0, 255, 150) if ok else (255, 90, 90)
    G.toast_until = time.time() + secs


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        fields["user"] = str(cfg.get("user", ""))[:FIELD_MAX["user"]]
    except (OSError, ValueError):
        pass


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"user": fields["user"]}, f, indent=2)
    except OSError:
        pass


# ==========================================================
# NETWORK
# ==========================================================
class Net:
    def __init__(self):
        self.q = queue.Queue()
        self.outq = queue.Queue()
        self.sock = None
        self.closed = False

    def start(self, host, port, first_msg):
        threading.Thread(target=self._run, args=(host, port, first_msg), daemon=True).start()

    def _run(self, host, port, first):
        try:
            s = socket.create_connection((host, port), timeout=6)
            s.settimeout(None)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError as e:
            self.closed = True
            self.q.put({"t": "_error", "msg": "Không kết nối tới %s:%s (%s)" % (host, port, e.strerror or e)})
            return
        self.sock = s
        threading.Thread(target=self._writer, daemon=True).start()
        self.send(first)
        buf = b""
        try:
            while True:
                data = s.recv(65536)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        self.q.put(json.loads(line.decode("utf-8")))
                    except ValueError:
                        pass
        except OSError:
            pass
        self.closed = True
        self.q.put({"t": "_closed"})

    def _writer(self):
        while True:
            data = self.outq.get()
            if data is None:
                break
            try:
                self.sock.sendall(data)
            except OSError:
                break

    def send(self, msg):
        if not self.closed:
            self.outq.put((json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8"))

    def close(self):
        self.closed = True
        self.outq.put(None)
        try:
            if self.sock:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
        except OSError:
            pass


def net_send(msg):
    if G.net and not G.net.closed:
        G.net.send(msg)


def parse_server(text):
    text = text.strip()
    if not text:
        raise ValueError("Địa chỉ server trống!")
    if text.startswith("["):
        end = text.find("]")
        if end == -1:
            raise ValueError("IPv6 thiếu ']'!")
        host = text[1:end]
        rest = text[end + 1:]
        port = DEFAULT_PORT
        if rest.startswith(":"):
            p = rest[1:]
            if not p.isdigit() or not (0 < int(p) < 65536):
                raise ValueError("Port không hợp lệ!")
            port = int(p)
        return host, port
    host, port = text, DEFAULT_PORT
    if ":" in text:
        host, p = text.rsplit(":", 1)
        if not p.isdigit() or not (0 < int(p) < 65536):
            raise ValueError("Port không hợp lệ!")
        port = int(p)
    if not host:
        raise ValueError("Địa chỉ server không hợp lệ!")
    return host, port


def submit_auth():
    if G.connecting:
        return
    user, pw = fields["user"].strip(), fields["pass"]
    if not user or not pw:
        G.auth_msg, G.auth_color = "Nhập đầy đủ Tên & Mật khẩu!", (255, 80, 80)
        return
    try:
        host, port = parse_server(SERVER_ADDR)
    except ValueError as e:
        G.auth_msg, G.auth_color = str(e), (255, 80, 80)
        return
    if G.net:
        G.net.close()
    G.net = Net()
    G.conn_lost = False
    G.connecting = True
    G.auth_msg, G.auth_color = "Đang kết nối tới %s..." % SERVER_ADDR, (255, 215, 0)
    G.net.start(host, port, {"t": "auth", "mode": G.auth_mode.lower(), "user": user, "pass": pw})


def send_save():
    G.save_dirty = False
    G.last_save = time.time()
    net_send({"t": "save", "data": {"coins": P["coins"], "unlocked_skins": sorted(P["unlocked"]),
                                    "current_skin": P["skin"], "bullet_type": P["bt"],
                                    "bullet_speed": P["bs"]}})


def mark_dirty():
    G.save_dirty = True


def refresh_social():
    G.last_refresh = time.time()
    net_send({"t": "friends_get"})
    net_send({"t": "board_get"})


def go_login(msg=""):
    old = G.net
    G.net = None
    if old:
        old.close()
    G.user = None
    G.W = None
    G.in_room = False
    G.invite = None
    G.connecting = False
    G.popup = False
    G.chat_global.clear()
    G.chat_private.clear()
    G.chat_unread.clear()
    G.chat_target = None
    G.chat_badge_global = 0
    G.auth_msg, G.auth_color = msg, (255, 80, 80)
    fields["pass"] = ""
    set_state("LOGIN")


def _push_chat(bucket, entry):
    bucket.append(entry)
    if len(bucket) > CHAT_KEEP:
        del bucket[:-CHAT_KEEP]


def handle_net(m):
    t = m.get("t")
    if t == "auth_ok":
        d = m["data"]
        P.update(coins=d["coins"], unlocked=set(d["unlocked_skins"]), skin=d["current_skin"],
                 bt=d["bullet_type"], bs=d["bullet_speed"], hs=d["high_score"])
        G.user = m["user"]
        G.connecting = False
        G.auth_msg = ""
        G.last_ping = time.time()
        fields["pass"] = ""
        save_config()
        set_state("MENU")
        snd("levelup")
    elif t == "auth_fail":
        G.connecting = False
        G.auth_msg, G.auth_color = m.get("msg", "Đăng nhập thất bại"), (255, 80, 80)
        if G.net:
            G.net.close()
            G.net = None
    elif t == "_error":
        G.connecting = False
        G.auth_msg, G.auth_color = m.get("msg", "Lỗi kết nối"), (255, 80, 80)
    elif t == "_closed":
        if G.connecting:
            G.connecting = False
            G.auth_msg, G.auth_color = "Server đã đóng kết nối", (255, 80, 80)
        elif G.user:
            G.conn_lost = True
    elif t == "profile":
        P["hs"] = max(P["hs"], m.get("high_score", 0))
    elif t == "friends":
        G.friends = {"me_score": m.get("me_score", 0), "friends": m.get("friends", []),
                     "requests": m.get("requests", [])}
    elif t == "board":
        G.board = m
    elif t == "notice":
        toast(m.get("msg", ""), m.get("ok", True))
        if m.get("ok", True):
            snd("powerup")
    elif t == "invited":
        G.invite = {"from": m["from"], "t": time.time()}
        snd("powerup")
    elif t == "room_start":
        start_coop(m["role"], m["partner"])
    elif t == "room_msg":
        handle_room_msg(m.get("d") or {})
    elif t == "room_end":
        handle_room_end()
    elif t == "chat_history":
        G.chat_global.clear()
        for e in m.get("global", []):
            G.chat_global.append({"from": e.get("from", "?"), "msg": e.get("msg", ""), "ts": e.get("ts", 0)})
    elif t == "chat":
        scope = m.get("scope")
        if scope == "global":
            e = {"from": m.get("from", "?"), "msg": m.get("msg", ""), "ts": time.time()}
            _push_chat(G.chat_global, e)
            if G.state == "CHAT" and G.chat_tab == "GLOBAL":
                snd("chat")
                G.chat_scroll = 0
            elif m.get("from") != G.user:
                G.chat_badge_global += 1
                toast("[Tổng] %s: %s" % (e["from"][:12], e["msg"][:40]), True, 3.0)
        elif scope == "private":
            other = m.get("to") if m.get("echo") else m.get("from")
            if other is None:
                return
            e = {"from": m.get("from", "?"), "msg": m.get("msg", ""), "ts": time.time()}
            _push_chat(G.chat_private.setdefault(other, []), e)
            if not m.get("echo"):
                if not (G.state == "CHAT" and G.chat_tab == "PRIVATE" and G.chat_target == other):
                    G.chat_unread[other] = G.chat_unread.get(other, 0) + 1
                    snd("chat")
                    toast("[%s] %s" % (other[:12], e["msg"][:40]), True, 3.0)
                else:
                    snd("chat")
                    G.chat_scroll = 0


def pump_net():
    net = G.net
    if not net:
        return
    for _ in range(300):
        try:
            m = net.q.get_nowait()
        except queue.Empty:
            break
        handle_net(m)
        if G.net is not net:
            break


# ==========================================================
# HIỆU ỨNG
# ==========================================================
def create_explosion(x, y, color=(255, 150, 50), count=18, sound=True):
    if sound:
        snd("explosion")
    if len(particles) > 500:
        return
    for _ in range(count):
        a = random.uniform(0, math.pi * 2)
        sp = random.uniform(2, 7)
        particles.append({"x": x, "y": y, "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                          "size": random.randint(3, 6), "color": tuple(color), "life": 1.0})


def apply_event(ev):
    if ev[0] == "snd":
        snd(ev[1])
    elif ev[0] == "ex":
        create_explosion(ev[1], ev[2], ev[3], ev[4], ev[5])


def update_draw_particles():
    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["life"] -= 0.04
        if p["life"] <= 0:
            particles.remove(p)
            continue
        s = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(s, (*p["color"], int(p["life"] * 255)), (6, 6), max(1, int(p["size"] * p["life"])))
        screen.blit(s, (p["x"] - 6, p["y"] - 6))


def update_draw_thrusters():
    for t in thrusters[:]:
        t["y"] += t["vy"]
        t["life"] -= 0.08
        if t["life"] <= 0:
            thrusters.remove(t)
            continue
        s = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 150, 0, int(t["life"] * 255)), (6, 6), max(1, int(t["size"] * t["life"])))
        screen.blit(s, (t["x"] - 6, t["y"]))


# ==========================================================
# GAME WORLD
# ==========================================================
class Player:
    def __init__(self, name, skin, bt=1, bs=13, x=0, y=0):
        self.name, self.skin, self.bt, self.bs = name, skin, bt, bs
        self.x, self.y = float(x), float(y)
        self.hp = 3
        self.alive = True
        self.connected = True
        self.inv = 0
        self.tmp_type = 0
        self.tmp_frames = 0
        self.cool = FIRE_DELAY
        self.fire = False

    @property
    def weapon(self):
        return max(self.bt, self.tmp_type)


class World:
    def __init__(self, diff, players, coop):
        self.diff = diff
        self.players = players
        self.coop = coop
        self.bullets, self.ebullets, self.enemies, self.powerups = [], [], [], []
        self.boss = None
        self.score = 0
        self.level = 1
        self.level_start = 0
        self.spawn_timer = 0
        self.coins_total = 0
        self.tick = 0
        self.state = "PLAYING"
        self.events = []

    def emit(self, *ev):
        apply_event(ev)
        if self.coop:
            self.events.append(list(ev))

    def spawn_powerup(self, x, y):
        if random.random() < 0.35:
            kind = random.choices(["HP", "DOUBLE", "TRIPLE", "HEXA"], weights=[0.3, 0.3, 0.25, 0.15])[0]
            self.powerups.append({"x": float(x), "y": float(y), "kind": kind})

    def fire(self, p):
        cx, cy, sp, t = p.x + 25, p.y, p.bs, p.weapon

        def add(x, y, vx, vy, w=8, h=22, big=0):
            self.bullets.append({"x": float(x), "y": float(y), "vx": vx, "vy": vy, "w": w, "h": h, "big": big})

        if t == 1:
            add(cx - 4, cy, 0, -sp)
            s = "l1"
        elif t == 2:
            add(p.x + 8, cy, 0, -sp)
            add(p.x + 34, cy, 0, -sp)
            s = "l2"
        elif t == 3:
            add(p.x, cy + 10, 0, -sp)
            add(cx - 4, cy - 5, 0, -sp)
            add(p.x + 42, cy + 10, 0, -sp)
            s = "l3"
        else:
            angles = {4: [-0.25, -0.08, 0.08, 0.25],
                      5: [-0.4, -0.2, 0, 0.2, 0.4],
                      10: [-0.6, -0.45, -0.3, -0.15, -0.05, 0.05, 0.15, 0.3, 0.45, 0.6]}[t]
            for a in angles:
                add(cx - 3, cy, sp * math.sin(a), -sp * math.cos(a), 6, 20, 1)
            s = "l4"
        self.emit("snd", s)

    def hurt(self, p, color=(255, 0, 0), count=25):
        if p.inv > 0 or not p.alive:
            return
        p.hp -= 1
        p.inv = 90
        self.emit("ex", p.x + 25, p.y + 25, list(color), count, True)
        if p.hp <= 0:
            p.alive = False

    def kill_boss(self, d):
        b = self.boss
        self.emit("ex", b["x"] + 60, b["y"] + 45, [255, 215, 0], 60, True)
        self.emit("snd", "levelup")
        self.coins_total += int(100 * self.level * d["coin_mod"])
        self.score += 100
        self.spawn_powerup(b["x"] + 60, b["y"] + 45)
        self.boss = None
        self.enemies.clear()
        self.ebullets.clear()
        if self.level >= MAX_LEVELS:
            self.state = "VICTORY"
            return
        self.level += 1
        self.level_start = self.score
        for p in self.players:
            if p.connected and not p.alive:
                p.alive, p.hp, p.inv = True, 2, 120

    def step(self):
        d = DIFFS[self.diff]
        self.tick += 1
        for p in self.players:
            if not (p.alive and p.connected):
                continue
            p.inv = max(0, p.inv - 1)
            if p.tmp_frames > 0:
                p.tmp_frames -= 1
                if p.tmp_frames == 0:
                    p.tmp_type = 0
            p.cool += 1
            if p.fire and p.cool >= FIRE_DELAY:
                p.cool = 0
                self.fire(p)
        actors = [(p, pygame.Rect(int(p.x) + 8, int(p.y) + 6, 34, 38))
                  for p in self.players if p.alive and p.connected]

        if self.boss is None and (self.score - self.level_start) >= SCORE_PER_LEVEL:
            hp = 150 + self.level * 50
            self.boss = {"x": WIDTH / 2 - 60.0, "y": -120.0, "hp": hp, "max_hp": hp, "vx": 3.0, "shoot": 0}
        if self.boss:
            b = self.boss
            if b["y"] < 50:
                b["y"] += 2
            else:
                b["x"] += b["vx"]
                if b["x"] <= 10 or b["x"] + 120 >= WIDTH - 10:
                    b["vx"] *= -1
                    b["x"] = clamp(b["x"], 10, WIDTH - 130)
            b["shoot"] += 1
            if b["shoot"] >= max(12, 40 - self.level):
                b["shoot"] = 0
                bottom = b["y"] + 90
                self.ebullets.append({"x": b["x"] + 45.0, "y": bottom})
                self.ebullets.append({"x": b["x"] + 68.0, "y": bottom})

        keep = []
        for eb in self.ebullets:
            eb["y"] += 7
            if eb["y"] > HEIGHT:
                continue
            r = pygame.Rect(int(eb["x"]), int(eb["y"]), 8, 20)
            hit = False
            for p, pr in actors:
                if p.alive and pr.colliderect(r):
                    self.hurt(p)
                    hit = True
                    break
            if not hit:
                keep.append(eb)
        self.ebullets = keep

        speed = min(9.0, (2.2 + self.level * 0.1) * d["speed_mod"])
        if self.boss is None:
            self.spawn_timer += 1
            rate = max(10, int((35 - self.level * 0.2) * d["spawn_mod"]))
            if self.spawn_timer >= rate and len(self.enemies) < 40:
                self.spawn_timer = 0
                self.enemies.append({"x": 0.0, "y": -40.0, "init_x": random.randint(60, WIDTH - 100),
                                     "off": random.uniform(0, math.pi * 2),
                                     "type": random.choice([1, 2]), "seed": random.randint(0, 1000)})
        alive_enemies = []
        for e in self.enemies:
            e["y"] += speed
            e["x"] = e["init_x"] + math.sin(e["y"] * 0.03 + e["off"]) * 40
            if e["y"] > HEIGHT:
                continue
            er = pygame.Rect(int(e["x"]), int(e["y"]), 40, 40)
            rammed = False
            for p, pr in actors:
                if p.alive and pr.colliderect(er):
                    self.hurt(p, (255, 50, 50), 18)
                    rammed = True
                    break
            if not rammed:
                alive_enemies.append(e)
        self.enemies = alive_enemies

        keep = []
        for bl in self.bullets:
            bl["x"] += bl["vx"]
            bl["y"] += bl["vy"]
            if bl["y"] + bl["h"] < 0 or bl["x"] + bl["w"] < 0 or bl["x"] > WIDTH or bl["y"] > HEIGHT:
                continue
            br = pygame.Rect(int(bl["x"]), int(bl["y"]), bl["w"], bl["h"])
            if self.boss and br.colliderect(pygame.Rect(int(self.boss["x"]), int(self.boss["y"]), 120, 90)):
                self.boss["hp"] -= 10
                self.emit("ex", bl["x"], bl["y"], [0, 255, 255], 4, False)
                if self.boss["hp"] <= 0:
                    self.kill_boss(d)
                continue
            target = None
            for e in self.enemies:
                if br.colliderect(pygame.Rect(int(e["x"]), int(e["y"]), 40, 40)):
                    target = e
                    break
            if target:
                self.enemies.remove(target)
                self.score += 15
                self.coins_total += max(1, int(5 * d["coin_mod"]))
                self.emit("ex", target["x"] + 18, target["y"] + 18, [0, 255, 200], 18, True)
                self.spawn_powerup(target["x"] + 18, target["y"] + 18)
                continue
            keep.append(bl)
        self.bullets = keep

        keep = []
        for pu in self.powerups:
            pu["y"] += 2
            if pu["y"] > HEIGHT:
                continue
            pr = pygame.Rect(int(pu["x"]), int(pu["y"]), 26, 26)
            taken = False
            for p, ar in actors:
                if p.alive and ar.colliderect(pr):
                    self.emit("snd", "powerup")
                    if pu["kind"] == "HP":
                        p.hp = min(MAX_HP, p.hp + 1)
                    else:
                        p.tmp_type = max(p.tmp_type, POWERUP_WEAPON[pu["kind"]])
                        p.tmp_frames = TMP_FRAMES
                    taken = True
                    break
            if not taken:
                keep.append(pu)
        self.powerups = keep

        if not any(p.alive and p.connected for p in self.players) and self.state == "PLAYING":
            self.state = "GAME_OVER"

    def snapshot(self):
        s = {"k": "st",
             "p": [[round(p.x), round(p.y), p.hp, p.skin, int(p.alive), p.inv, int(p.connected), p.tmp_frames]
                   for p in self.players],
             "e": [[round(e["x"]), round(e["y"]), e["type"], e["seed"]] for e in self.enemies],
             "b": [[round(b["x"]), round(b["y"]), b["w"], b["h"], b["big"]] for b in self.bullets],
             "eb": [[round(e["x"]), round(e["y"])] for e in self.ebullets],
             "pu": [[round(p["x"]), round(p["y"]), p["kind"]] for p in self.powerups],
             "bo": [round(self.boss["x"]), round(self.boss["y"]), self.boss["hp"], self.boss["max_hp"]]
             if self.boss else None,
             "sc": self.score, "lv": self.level, "co": self.coins_total, "ev": self.events,
             "stt": self.state}
        self.events = []
        return s

    def apply_snapshot(self, s, local_idx):
        for i, pd in enumerate(s["p"][:len(self.players)]):
            p = self.players[i]
            if i != local_idx:
                p.x, p.y = pd[0], pd[1]
                p.skin = pd[3]
            p.hp, p.alive, p.inv, p.connected, p.tmp_frames = pd[2], bool(pd[4]), pd[5], bool(pd[6]), pd[7]
        self.enemies = [{"x": e[0], "y": e[1], "type": e[2], "seed": e[3]} for e in s["e"]]
        self.bullets = [{"x": b[0], "y": b[1], "w": b[2], "h": b[3], "big": b[4]} for b in s["b"]]
        self.ebullets = [{"x": e[0], "y": e[1]} for e in s["eb"]]
        self.powerups = [{"x": p[0], "y": p[1], "kind": p[2]} for p in s["pu"]]
        bo = s["bo"]
        self.boss = {"x": bo[0], "y": bo[1], "hp": bo[2], "max_hp": bo[3]} if bo else None
        self.score, self.level, self.coins_total, self.state = s["sc"], s["lv"], s["co"], s["stt"]
        for ev in s["ev"]:
            apply_event(ev)


# ==========================================================
# VẼ
# ==========================================================
_ship_cache = {}


def ship_surface(skin_id):
    if skin_id not in _ship_cache:
        sk = SKINS.get(skin_id, SKINS[1])
        c_main, c_wing = sk["primary"], sk["wing"]
        s = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.polygon(s, c_wing, [(25, 12), (0, 38), (10, 46), (25, 30)])
        pygame.draw.polygon(s, c_wing, [(25, 12), (50, 38), (40, 46), (25, 30)])
        pygame.draw.polygon(s, c_main, [(25, 2), (15, 34), (25, 44), (35, 34)])
        pygame.draw.ellipse(s, (0, 220, 255), (21, 15, 8, 15))
        pygame.draw.ellipse(s, (255, 255, 255), (23, 17, 3, 6))
        pygame.draw.rect(s, (180, 180, 180), (2, 30, 3, 12))
        pygame.draw.rect(s, (180, 180, 180), (45, 30, 3, 12))
        _ship_cache[skin_id] = s
    return _ship_cache[skin_id]


def draw_ship(x, y, skin_id):
    screen.blit(ship_surface(skin_id), (int(x), int(y)))


def draw_enemy(x, y, e_type, seed):
    w = h = 40
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    wing = math.sin((pygame.time.get_ticks() + seed) * 0.02) * 6
    if e_type == 1:
        pygame.draw.ellipse(s, (200, 220, 255, 200), (0, int(8 + wing), 14, 18))
        pygame.draw.ellipse(s, (200, 220, 255, 200), (w - 14, int(8 + wing), 14, 18))
        pygame.draw.ellipse(s, (230, 30, 50), (8, 6, 22, 28))
        pygame.draw.circle(s, (255, 200, 0), (19, 8), 5)
    else:
        pygame.draw.ellipse(s, (255, 255, 200, 200), (2, int(4 - wing), 12, 15))
        pygame.draw.ellipse(s, (255, 255, 200, 200), (w - 14, int(4 - wing), 12, 15))
        pygame.draw.circle(s, (0, 220, 100), (w // 2, h // 2 + 2), 14)
        pygame.draw.circle(s, (0, 150, 60), (w // 2, h // 2 + 2), 9)
    screen.blit(s, (int(x), int(y)))


def draw_boss(b, level):
    w, h = 120, 90
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    t = pygame.time.get_ticks()
    wa = int(math.sin(t * 0.015) * 8)
    pygame.draw.polygon(s, (150, 0, 200, 200), [(w // 2, 35), (0, 8 + wa), (18, 60)])
    pygame.draw.polygon(s, (150, 0, 200, 200), [(w // 2, 35), (w, 8 + wa), (w - 18, 60)])
    pygame.draw.ellipse(s, (80, 10, 40), (18, 18, w - 36, h - 26))
    pygame.draw.ellipse(s, (180, 20, 60), (30, 26, w - 60, h - 42))
    glow = int(180 + math.sin(t * 0.01) * 75)
    pygame.draw.circle(s, (255, glow, 0), (w // 2 - 20, 50), 8)
    pygame.draw.circle(s, (255, glow, 0), (w // 2 + 20, 50), 8)
    screen.blit(s, (int(b["x"]), int(b["y"])))
    bw = 300
    ratio = clamp(b["hp"] / b["max_hp"], 0.0, 1.0)
    x0 = WIDTH // 2 - bw // 2
    pygame.draw.rect(screen, (40, 40, 50), (x0, 15, bw, 14), border_radius=7)
    pygame.draw.rect(screen, (255, 40, 60), (x0, 15, int(bw * ratio), 14), border_radius=7)
    pygame.draw.rect(screen, (255, 255, 255), (x0, 15, bw, 14), width=2, border_radius=7)
    T("TRÙM MÀN %d - HP: %d" % (level, max(0, int(b["hp"]))), F_SMALL, (255, 255, 255), WIDTH // 2, 32, "midtop")


def draw_heart(cx, cy, r, color):
    pygame.draw.circle(screen, color, (cx - r // 2, cy - r // 4), r // 2 + 1)
    pygame.draw.circle(screen, color, (cx + r // 2, cy - r // 4), r // 2 + 1)
    pygame.draw.polygon(screen, color, [(cx - r, cy), (cx + r, cy), (cx, cy + r + 1)])


def draw_hearts(x, y, hp):
    for i in range(MAX_HP):
        draw_heart(x + i * 20, y, 7, (0, 230, 110) if i < hp else (45, 60, 60))


def draw_gear(cx, cy, radius=11, color=(0, 255, 220), teeth=8):
    for i in range(teeth):
        a = i * (2 * math.pi / teeth)
        pygame.draw.circle(screen, color, (int(cx + (radius + 4) * math.cos(a)), int(cy + (radius + 4) * math.sin(a))), 3)
    pygame.draw.circle(screen, color, (cx, cy), radius, width=3)
    pygame.draw.circle(screen, color, (cx, cy), 4)


def draw_bullet_preview(x, y, b_type, width=80, height=55):
    box = pygame.Rect(x, y, width, height)
    pygame.draw.rect(screen, (15, 25, 45), box, border_radius=8)
    pygame.draw.rect(screen, (0, 200, 255), box, width=1, border_radius=8)
    cx, cy = x + width // 2, y + height - 8
    table = {1: [0], 2: [-0.1, 0.1], 3: [-0.2, 0, 0.2], 4: [-0.4, -0.15, 0.15, 0.4],
             5: [-0.5, -0.25, 0, 0.25, 0.5], 10: [-0.8, -0.6, -0.4, -0.2, -0.05, 0.05, 0.2, 0.4, 0.6, 0.8],
             -1: [0]}
    col = (255, 50, 200) if b_type >= 4 else (0, 255, 255)
    for rad in table.get(b_type, [0]):
        ex, ey = cx + 30 * math.sin(rad), cy - 30 * math.cos(rad)
        pygame.draw.line(screen, col, (cx, cy), (ex, ey), 2)
        pygame.draw.circle(screen, (255, 255, 255), (int(ex), int(ey)), 2)


# ==========================================================
# UI helpers
# ==========================================================
def T(txt, font, color, x, y, anchor="topleft"):
    s = font.render(str(txt), True, color)
    r = s.get_rect(**{anchor: (x, y)})
    screen.blit(s, r)
    return r


def draw_card(rect, border=(0, 255, 200), fill=(15, 20, 35, 210), radius=16):
    card = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(card, fill, (0, 0, rect.width, rect.height), border_radius=radius)
    pygame.draw.rect(card, border, (0, 0, rect.width, rect.height), width=2, border_radius=radius)
    screen.blit(card, rect.topleft)


def button(rect, label, fn, base=(25, 35, 60), hov=(40, 60, 95), border=(0, 220, 255),
           color=(255, 255, 255), font=None, enabled=True, bw=2):
    font = font or F_SMALL
    hover = enabled and rect.collidepoint(G.mouse)
    bg = hov if hover else base
    if not enabled:
        bg, border, color = (28, 30, 38), (70, 75, 90), (120, 125, 140)
    pygame.draw.rect(screen, bg, rect, border_radius=10)
    pygame.draw.rect(screen, border, rect, width=bw + (1 if hover else 0), border_radius=10)
    T(label, font, color, rect.centerx, rect.centery, "center")
    if enabled:
        hits.append((rect, fn))
    return hover


def click_area(rect, fn):
    hits.append((rect, fn))


def field(rect, key, label="", masked=False, hint=""):
    if label:
        T(label, F_SMALL, (200, 220, 255), rect.x, rect.y - 20)
    focused = G.focus == key
    pygame.draw.rect(screen, (35, 50, 80) if focused else (20, 30, 50), rect, border_radius=8)
    pygame.draw.rect(screen, (0, 255, 220) if focused else (80, 100, 140), rect, width=2, border_radius=8)
    txt = ("*" * len(fields[key])) if masked else fields[key]
    caret = "|" if focused and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
    if not txt and not focused and hint:
        T(hint, F_SMALL, (110, 125, 150), rect.x + 10, rect.centery, "midleft")
    else:
        shown = txt + caret
        while F_MED.size(shown)[0] > rect.width - 20 and len(shown) > 1:
            shown = shown[1:]
        T(shown, F_MED, (255, 255, 255), rect.x + 10, rect.centery, "midleft")

    def focus():
        G.focus = key
    click_area(rect, focus)


def set_state(s):
    G.state = s
    G.popup = False
    G.scroll = 0
    G.chat_scroll = 0
    G.focus = {"LOGIN": "user" if not fields["user"] else "pass",
               "FRIENDS": "friend",
               "CHAT": "chat"}.get(s)
    if s in ("FRIENDS", "BOARD"):
        refresh_social()
    elif s == "MENU":
        net_send({"t": "friends_get"})
    elif s == "CHAT":
        if G.chat_tab == "GLOBAL":
            G.chat_badge_global = 0
        elif G.chat_target:
            G.chat_unread[G.chat_target] = 0
        fields["chat"] = ""


def back_button(label="QUAY LẠI MENU", y=None):
    button(pygame.Rect(50, y or HEIGHT - 60, WIDTH - 100, 40), label, lambda: set_state("MENU"),
           base=(40, 20, 20), hov=(60, 30, 30), border=(255, 100, 100), color=(255, 200, 200))


# ==========================================================
# HÀNH ĐỘNG
# ==========================================================
def buy_skin(sid):
    if sid in P["unlocked"]:
        P["skin"] = sid
        snd("powerup")
    elif P["coins"] >= SKINS[sid]["price"]:
        P["coins"] -= SKINS[sid]["price"]
        P["unlocked"].add(sid)
        P["skin"] = sid
        snd("levelup")
    else:
        toast("Không đủ xu!", False)
        return
    send_save()


def buy_weapon(item):
    t, cost = item["type"], item["cost"]
    if t == -1:
        if P["bs"] >= MAX_BULLET_SPEED:
            return toast("Tốc độ đạn đã tối đa!", False)
        if P["coins"] < cost:
            return toast("Không đủ xu!", False)
        P["coins"] -= cost
        P["bs"] = min(MAX_BULLET_SPEED, P["bs"] + 4)
        snd("powerup")
    else:
        if P["bt"] >= t:
            return
        if P["coins"] < cost:
            return toast("Không đủ xu!", False)
        P["coins"] -= cost
        P["bt"] = t
        snd("levelup")
    send_save()


def add_friend():
    name = fields["friend"].strip()
    if not name:
        return toast("Nhập tên tài khoản!", False)
    net_send({"t": "friend_add", "name": name})
    fields["friend"] = ""


def invite_friend(name):
    net_send({"t": "invite", "name": name})


def accept_invite():
    if G.invite:
        net_send({"t": "invite_accept", "from": G.invite["from"]})
        G.invite = None


def decline_invite():
    if G.invite:
        net_send({"t": "invite_decline"})
        G.invite = None


def quit_game():
    leave_match()
    if G.user:
        send_save()
    if G.net:
        deadline = time.time() + 1.5
        while time.time() < deadline and not G.net.outq.empty():
            time.sleep(0.02)
        time.sleep(0.1)
    pygame.event.post(pygame.event.Event(pygame.QUIT))


def toggle_sound():
    G.sound_on = not G.sound_on
    apply_sound_setting()


def send_chat():
    text = fields["chat"].strip()
    if not text:
        return
    text = text[:FIELD_MAX["chat"]]
    if G.chat_tab == "GLOBAL":
        net_send({"t": "chat_global", "msg": text})
    else:
        if not G.chat_target:
            return toast("Chọn bạn để chat!", False)
        net_send({"t": "chat_private", "to": G.chat_target, "msg": text})
    fields["chat"] = ""
    G.focus = "chat"
    G.chat_scroll = 0


# ==========================================================
# VÁN CHƠI
# ==========================================================
def spawn_pos(idx, total):
    return WIDTH // 2 - 25 + (idx - (total - 1) / 2) * 90, HEIGHT - 100


def begin_match(world, mode):
    G.W, G.mode = world, mode
    G.credited = 0
    G.submitted = False
    G.got_snapshot = (mode != "guest")
    particles.clear()
    thrusters.clear()
    G.state = "PLAYING"
    G.focus = None
    G.popup = False


def start_solo():
    x, y = spawn_pos(0, 1)
    me = Player(G.user, P["skin"], P["bt"], P["bs"], x, y)
    begin_match(World(G.difficulty, [me], False), "solo")


def start_coop(role, partner):
    G.in_room = True
    G.partner = partner
    G.invite = None
    x0, y0 = spawn_pos(0, 2)
    x1, y1 = spawn_pos(1, 2)
    host = Player(G.user if role == "host" else partner, P["skin"] if role == "host" else 1,
                  P["bt"] if role == "host" else 1, P["bs"] if role == "host" else 13, x0, y0)
    guest = Player(G.user if role == "guest" else partner, P["skin"] if role == "guest" else 1,
                   P["bt"] if role == "guest" else 1, P["bs"] if role == "guest" else 13, x1, y1)
    guest.inv = 120
    host.inv = 60
    begin_match(World(G.difficulty, [host, guest], True), role)
    toast("Vào phòng với %s!" % partner)


def leave_match():
    if G.W is not None and not G.submitted and G.W.score > 0:
        submit_score()
    if G.in_room:
        net_send({"t": "room_leave"})
        G.in_room = False
    G.W = None


def submit_score():
    if G.W is None:
        return
    G.submitted = True
    sc = max(0, int(G.W.score))
    P["hs"] = max(P["hs"], sc)
    net_send({"t": "score", "score": sc})
    send_save()


def end_match(result):
    G.state = result
    if not G.submitted:
        submit_score()


def handle_room_msg(d):
    w = G.W
    if w is None:
        return
    k = d.get("k")
    if k == "in" and G.mode == "host" and len(w.players) > 1:
        g = w.players[1]
        try:
            g.x = clamp(float(d["x"]), 0, WIDTH - 50)
            g.y = clamp(float(d["y"]), 0, HEIGHT - 50)
            g.fire = bool(d.get("f"))
            skin, bt, bs = int(d.get("s", 1)), int(d.get("bt", 1)), int(d.get("bs", 13))
        except (KeyError, TypeError, ValueError):
            return
        g.skin = skin if skin in SKINS else 1
        g.bt = bt if bt in VALID_BULLETS else 1
        g.bs = clamp(bs, 13, MAX_BULLET_SPEED)
    elif k == "st" and G.mode == "guest":
        try:
            w.apply_snapshot(d, 1)
        except (KeyError, IndexError, TypeError, ValueError):
            return
        G.got_snapshot = True


def handle_room_end():
    G.in_room = False
    toast("Đồng đội đã rời phòng.", False)
    w = G.W
    if w is None:
        return
    if G.mode == "host" and G.state in ("PLAYING", "PAUSED"):
        w.coop = False
        if len(w.players) > 1:
            w.players[1].connected = False
            w.players[1].alive = False
        G.mode = "solo"
    elif G.mode == "guest" and G.state == "PLAYING":
        leave_match()
        set_state("MENU")


def read_input(p):
    if G.input_hook:
        dx, dy, fire = G.input_hook()
    else:
        k = pygame.key.get_pressed()
        dx = (1 if (k[pygame.K_RIGHT] or k[pygame.K_d]) else 0) - (1 if (k[pygame.K_LEFT] or k[pygame.K_a]) else 0)
        dy = (1 if (k[pygame.K_DOWN] or k[pygame.K_s]) else 0) - (1 if (k[pygame.K_UP] or k[pygame.K_w]) else 0)
        fire = pygame.mouse.get_pressed()[0] or k[pygame.K_j] or k[pygame.K_k]
    p.x = clamp(p.x + dx * PLAYER_SPEED, 0, WIDTH - 50)
    p.y = clamp(p.y + dy * PLAYER_SPEED, 0, HEIGHT - 50)
    p.fire = bool(fire)


def update_play():
    w = G.W
    if w is None:
        return
    li = 1 if G.mode == "guest" else 0
    me = w.players[li]
    if me.alive:
        read_input(me)
    else:
        me.fire = False
    for p in w.players:
        if p.alive and p.connected:
            thrusters.append({"x": p.x + 25, "y": p.y + 44, "vy": random.uniform(3, 6),
                              "size": random.randint(3, 5), "life": 1.0})

    delta = w.coins_total - G.credited
    if delta > 0:
        P["coins"] += delta
        G.credited = w.coins_total
        mark_dirty()

    if G.mode == "guest":
        if G.tick % 2 == 0:
            net_send({"t": "room_msg", "d": {"k": "in", "x": round(me.x), "y": round(me.y), "f": int(me.fire),
                                             "s": P["skin"], "bt": P["bt"], "bs": P["bs"]}})
        if w.state != "PLAYING":
            end_match(w.state)
        return

    w.step()
    if G.mode == "host" and w.coop and (w.tick % 2 == 0 or w.state != "PLAYING"):
        net_send({"t": "room_msg", "d": w.snapshot()})
    delta = w.coins_total - G.credited
    if delta > 0:
        P["coins"] += delta
        G.credited = w.coins_total
        mark_dirty()
    if w.state != "PLAYING":
        end_match(w.state)


# ==========================================================
# VẼ MÀN HÌNH
# ==========================================================
STARS = []
for _ in range(120):
    _l = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
    STARS.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), _l, _l * 1.5, random.randint(150, 255)])

SPLASH_FRAMES = 150
menu_rocket = {"x": -100.0, "y": HEIGHT // 2 - 20.0, "vx": 6.0, "vy": -1.2}


def draw_stars():
    screen.fill((8, 10, 22))
    for st in STARS:
        st[1] += st[3]
        if st[1] > HEIGHT:
            st[1], st[0] = 0, random.randint(0, WIDTH)
        b = st[4]
        pygame.draw.circle(screen, (b, b, min(255, b + 50)), (int(st[0]), int(st[1])), st[2])


def draw_splash():
    G.splash += 1
    t = G.splash
    screen.fill((18, 18, 22))
    alpha = 255
    if t < 30:
        alpha = int((t / 30) * 255)
    elif t > SPLASH_FRAMES - 30:
        alpha = int(((SPLASH_FRAMES - t) / 30) * 255)
    alpha = clamp(alpha, 0, 255)

    cx, cy = WIDTH // 2, HEIGHT // 2 - 50
    scale = 1.0 + (t / SPLASH_FRAMES) * 0.08
    r_outer = int(45 * scale)
    r_inner = int(20 * scale)

    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pts_outer, pts_inner = [], []
    for i in range(6):
        angle = math.radians(i * 60 - 30)
        pts_outer.append((cx + r_outer * math.cos(angle), cy + r_outer * math.sin(angle)))
        pts_inner.append((cx + r_inner * math.cos(angle), cy + r_inner * math.sin(angle)))
    pygame.draw.polygon(layer, (255, 255, 255, alpha), pts_outer, width=5)
    for i in range(3):
        idx = i * 2
        pygame.draw.line(layer, (255, 255, 255, alpha), pts_inner[idx], pts_outer[idx], 4)
    pygame.draw.circle(layer, (255, 255, 255, alpha), (cx, cy), int(8 * scale))

    lbl_sub = F_SMALL.render("Made with", True, (180, 180, 180))
    lbl_unity = F_LARGE.render("Unity", True, (255, 255, 255))
    lbl_sub.set_alpha(alpha)
    lbl_unity.set_alpha(alpha)
    layer.blit(lbl_sub, (cx - lbl_sub.get_width() // 2, cy + r_outer + 15))
    layer.blit(lbl_unity, (cx - lbl_unity.get_width() // 2, cy + r_outer + 38))

    prog = min(1.0, t / SPLASH_FRAMES)
    bar_w, bar_h = 280, 12
    bar_x = WIDTH // 2 - bar_w // 2
    bar_y = cy + r_outer + 100
    pygame.draw.rect(layer, (50, 55, 70, alpha), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
    fw = int(bar_w * prog)
    if fw > 0:
        pygame.draw.rect(layer, (0, 220, 255, alpha), (bar_x, bar_y, fw, bar_h), border_radius=6)
    pygame.draw.rect(layer, (120, 130, 160, alpha), (bar_x, bar_y, bar_w, bar_h), width=2, border_radius=6)
    pct = F_SMALL.render("Đang tải... %d%%" % int(prog * 100), True, (200, 210, 230))
    pct.set_alpha(alpha)
    layer.blit(pct, (WIDTH // 2 - pct.get_width() // 2, bar_y + 18))
    screen.blit(layer, (0, 0))
    if t >= SPLASH_FRAMES:
        set_state("LOGIN")


def draw_login():
    draw_card(pygame.Rect(40, 50, WIDTH - 80, 600))
    title = "ĐĂNG NHẬP" if G.auth_mode == "LOGIN" else "ĐĂNG KÝ"
    T(title, F_LARGE, (0, 255, 220), WIDTH // 2, 100, "midtop")
    T("Server: %s" % SERVER_ADDR, F_TINY, (120, 200, 220), WIDTH // 2, 145, "midtop")

    field(pygame.Rect(90, 200, WIDTH - 180, 40), "user", "Tên tài khoản (3-16 chữ/số/_):")
    field(pygame.Rect(90, 290, WIDTH - 180, 40), "pass", "Mật khẩu:", masked=True)

    label = "ĐĂNG NHẬP" if G.auth_mode == "LOGIN" else "TẠO TÀI KHOẢN"
    if G.connecting:
        label = "Đang kết nối..."
    button(pygame.Rect(90, 370, WIDTH - 180, 45), label, submit_auth, base=(0, 150, 110), hov=(0, 200, 150),
           border=(0, 255, 200), font=F_MED, enabled=not G.connecting)

    def switch():
        G.auth_mode = "REGISTER" if G.auth_mode == "LOGIN" else "LOGIN"
        G.auth_msg = ""
    sw = "Chưa có tài khoản? Đăng ký" if G.auth_mode == "LOGIN" else "Đã có? Đăng nhập"
    rect = pygame.Rect(90, 430, WIDTH - 180, 35)
    T(sw, F_SMALL, (0, 220, 255) if rect.collidepoint(G.mouse) else (150, 180, 220),
      rect.centerx, rect.centery, "center")
    click_area(rect, switch)
    if G.auth_msg:
        T(G.auth_msg, F_SMALL, G.auth_color, WIDTH // 2, 490, "midtop")
    T("TAB đổi ô | ENTER xác nhận", F_TINY, (120, 135, 160), WIDTH // 2, 580, "midtop")


def draw_menu_rocket():
    r = menu_rocket
    r["x"] += r["vx"]
    r["y"] += r["vy"]
    if r["x"] > WIDTH + 150:
        r["x"] = -150.0
        r["y"] = float(random.randint(HEIGHT // 2 - 60, HEIGHT // 2 + 60))
    if random.random() < 0.8 and len(particles) < 300:
        particles.append({"x": r["x"] - 20, "y": r["y"] + random.uniform(-4, 4), "vx": -random.uniform(3, 6),
                          "vy": random.uniform(-1, 1), "size": random.randint(3, 6),
                          "color": (255, random.randint(100, 200), 0), "life": 0.8})
    s = pygame.Surface((60, 26), pygame.SRCALPHA)
    pygame.draw.polygon(s, (220, 220, 230), [(0, 8), (38, 4), (55, 13), (38, 22), (0, 17)])
    pygame.draw.polygon(s, (255, 60, 60), [(38, 4), (55, 13), (38, 22)])
    pygame.draw.polygon(s, (0, 200, 255), [(8, 4), (20, 0), (25, 7)])
    pygame.draw.polygon(s, (0, 200, 255), [(8, 21), (20, 25), (25, 18)])
    pygame.draw.ellipse(s, (0, 255, 255), (30, 8, 10, 8))
    screen.blit(s, (int(r["x"]), int(r["y"])))


def draw_menu():
    T("ĐẠI CHIẾN KHÔNG GIAN", F_TITLE, (0, 255, 220), WIDTH // 2, 25, "midtop")
    d = DIFFS[G.difficulty]
    r = pygame.Rect(20, 80, 140, 45)
    hv = r.collidepoint(G.mouse)
    pygame.draw.rect(screen, (30, 40, 65), r, border_radius=10)
    pygame.draw.rect(screen, d["color"] if hv else (100, 120, 160), r, width=2, border_radius=10)
    T("ĐỘ KHÓ", F_TINY, (180, 200, 230), r.centerx, r.top + 4, "midtop")
    T(d["name"], F_MED, d["color"], r.centerx, r.top + 20, "midtop")
    click_area(r, lambda: set_state("DIFF"))

    r = pygame.Rect(WIDTH // 2 - 100, 80, 200, 45)
    hv = r.collidepoint(G.mouse)
    pygame.draw.rect(screen, (25, 35, 60), r, border_radius=10)
    pygame.draw.rect(screen, (0, 255, 200) if hv else (80, 120, 180), r, width=2, border_radius=10)
    pygame.draw.circle(screen, (0, 200, 255), (WIDTH // 2 - 75, 102), 12)
    pygame.draw.circle(screen, (255, 255, 255), (WIDTH // 2 - 75, 98), 5)
    name = (G.user[:9] + "..") if len(G.user) > 9 else G.user
    T(name.upper(), F_SMALL, (255, 255, 255), WIDTH // 2 - 55, 85)
    T("Xu: %d | Kỷ lục: %d" % (P["coins"], P["hs"]), F_TINY, (255, 215, 0), WIDTH // 2 - 55, 103)
    click_area(r, lambda: set_state("PROFILE"))

    r = pygame.Rect(WIDTH - 65, 80, 45, 45)
    hv = r.collidepoint(G.mouse)
    pygame.draw.rect(screen, (40, 50, 80) if hv else (25, 30, 50), r, border_radius=10)
    pygame.draw.rect(screen, (0, 255, 220) if hv else (100, 120, 160), r, width=2, border_radius=10)
    draw_gear(r.centerx, r.centery, 11, (0, 255, 220) if hv else (200, 220, 240))

    def toggle_popup():
        G.popup = not G.popup
    click_area(r, toggle_popup)

    draw_menu_rocket()
    pygame.draw.circle(screen, (0, 255, 200), (WIDTH // 2, HEIGHT // 2 + 10), 50, width=1)
    draw_ship(WIDTH // 2 - 25, HEIGHT // 2 - 15, P["skin"])

    nreq = len(G.friends["requests"])
    total_unread = sum(G.chat_unread.values()) + G.chat_badge_global

    button(pygame.Rect(20, HEIGHT - 165, 180, 40), "Bạn Bè (%d)" % len(G.friends["friends"]),
           lambda: set_state("FRIENDS"), border=(0, 220, 255))
    if nreq:
        pygame.draw.circle(screen, (255, 60, 60), (190, HEIGHT - 165), 11)
        T(str(nreq), F_TINY, (255, 255, 255), 190, HEIGHT - 165, "center")
    button(pygame.Rect(210, HEIGHT - 165, 180, 40), "Xếp Hạng", lambda: set_state("BOARD"),
           border=(255, 215, 0), color=(255, 235, 150))
    button(pygame.Rect(400, HEIGHT - 165, 180, 40), "Chat", lambda: set_state("CHAT"),
           border=(200, 140, 255), color=(235, 200, 255))
    if total_unread:
        pygame.draw.circle(screen, (255, 60, 60), (570, HEIGHT - 165), 11)
        T(str(min(total_unread, 99)), F_TINY, (255, 255, 255), 570, HEIGHT - 165, "center")

    button(pygame.Rect(30, HEIGHT - 100, 130, 45), "Shop Skin", lambda: set_state("SHOP_SKIN"),
           border=(120, 80, 160), color=(255, 180, 220))

    def play():
        start_solo()
    button(pygame.Rect(WIDTH // 2 - 90, HEIGHT - 110, 180, 55), "BẮT ĐẦU", play, base=(0, 140, 100),
           hov=(0, 200, 150), border=(0, 255, 200), font=F_LARGE, bw=3)
    button(pygame.Rect(WIDTH - 160, HEIGHT - 100, 130, 45), "Shop Vũ Khí", lambda: set_state("SHOP_WEAPON"),
           border=(80, 140, 160), color=(180, 255, 220))

    if G.popup:
        pop = pygame.Rect(WIDTH - 185, 132, 175, 135)
        click_area(pop, lambda: None)
        draw_card(pop, fill=(20, 25, 45, 245), radius=10)

        def logout():
            leave_match()
            send_save()
            go_login("")
        button(pygame.Rect(pop.x + 10, pop.y + 8, 155, 35), "Đổi Tài Khoản", logout, base=(30, 35, 60), font=F_SMALL)
        button(pygame.Rect(pop.x + 10, pop.y + 50, 155, 35), "Âm thanh: %s" % ("BẬT" if G.sound_on else "TẮT"),
               toggle_sound, base=(30, 35, 60), font=F_SMALL)
        button(pygame.Rect(pop.x + 10, pop.y + 92, 155, 35), "Thoát", quit_game, base=(120, 30, 30),
               hov=(200, 50, 50), border=(255, 100, 100), font=F_SMALL)


def draw_diff():
    draw_card(pygame.Rect(40, 60, WIDTH - 80, HEIGHT - 120), (255, 215, 0))
    T("CHỌN ĐỘ KHÓ", F_LARGE, (255, 215, 0), WIDTH // 2, 90, "midtop")
    for i, k in enumerate(("EASY", "NORMAL", "HARD")):
        d = DIFFS[k]

        def pick(key=k):
            G.difficulty = key
            set_state("MENU")
        button(pygame.Rect(70, 180 + i * 90, WIDTH - 140, 60), d["name"], pick, border=d["color"], color=d["color"],
               font=F_MED, bw=3 if k == G.difficulty else 2)
        T("Tốc độ x%.1f | Xu x%.1f" % (d["speed_mod"], d["coin_mod"]), F_TINY, (150, 170, 200),
          WIDTH // 2, 180 + i * 90 + 48, "midtop")
    back_button(y=HEIGHT - 80)


def draw_shop_weapon():
    draw_card(pygame.Rect(20, 20, WIDTH - 40, HEIGHT - 40), (0, 255, 200))
    T("SHOP VŨ KHÍ", F_LARGE, (0, 255, 200), WIDTH // 2, 35, "midtop")
    T("XU: %d" % P["coins"], F_MED, (255, 215, 0), WIDTH // 2, 72, "midtop")
    for i, it in enumerate(WEAPONS):
        y = 110 + i * 72
        r = pygame.Rect(35, y, WIDTH - 170, 62)
        t = it["type"]
        owned = (t != -1 and P["bt"] >= t)
        maxed = (t == -1 and P["bs"] >= MAX_BULLET_SPEED)
        col = (100, 255, 100) if (owned or maxed) else (255, 255, 255)
        hv = r.collidepoint(G.mouse)
        pygame.draw.rect(screen, (40, 55, 80) if hv else (25, 35, 55), r, border_radius=10)
        pygame.draw.rect(screen, (0, 255, 200) if hv else col, r, width=2 if hv else 1, border_radius=10)
        title = it["name"] + (" (ĐÃ CÓ)" if owned else " (MAX)" if maxed else " - %d Xu" % it["cost"])
        T(title, F_MED, col, 45, y + 10)
        T(it["desc"], F_TINY, (170, 190, 210), 45, y + 36)
        draw_bullet_preview(WIDTH - 125, y, t, 80, 62)
        click_area(r, lambda item=it: buy_weapon(item))
    button(pygame.Rect(50, HEIGHT - 110, WIDTH - 100, 40), "→ SHOP SKIN",
           lambda: set_state("SHOP_SKIN"), border=(255, 100, 200), color=(255, 180, 220))
    back_button()


def draw_shop_skin():
    draw_card(pygame.Rect(20, 20, WIDTH - 40, HEIGHT - 40), (255, 100, 200))
    T("SHOP SKIN", F_LARGE, (255, 100, 200), WIDTH // 2, 35, "midtop")
    T("XU: %d" % P["coins"], F_MED, (255, 215, 0), WIDTH // 2, 72, "midtop")
    for sid, sk in SKINS.items():
        y = 110 + (sid - 1) * 105
        r = pygame.Rect(40, y, WIDTH - 80, 95)
        owned = sid in P["unlocked"]
        active = sid == P["skin"]
        border = (0, 255, 150) if active else ((255, 255, 255) if owned else (255, 200, 0))
        hv = r.collidepoint(G.mouse)
        pygame.draw.rect(screen, (35, 40, 70) if hv else (20, 25, 45), r, border_radius=12)
        pygame.draw.rect(screen, border, r, width=3 if (active or hv) else 1, border_radius=12)
        draw_ship(WIDTH - 110, y + 22, sid)
        status = "ĐANG DÙNG" if active else ("SỞ HỮU - CLICK CHỌN" if owned else "GIÁ: %d XU" % sk["price"])
        T(sk["name"], F_MED, border, 55, y + 10)
        T(status, F_SMALL, (0, 255, 150) if owned else (255, 215, 0), 55, y + 36)
        T(sk["desc"], F_TINY, (170, 180, 200), 55, y + 62)
        click_area(r, lambda s=sid: buy_skin(s))
    button(pygame.Rect(50, HEIGHT - 110, WIDTH - 100, 40), "→ SHOP VŨ KHÍ",
           lambda: set_state("SHOP_WEAPON"), border=(0, 255, 200), color=(180, 255, 220))
    back_button()


def draw_profile():
    draw_card(pygame.Rect(40, 50, WIDTH - 80, HEIGHT - 100))
    T("CÁ NHÂN", F_LARGE, (0, 255, 220), WIDTH // 2, 70, "midtop")
    pygame.draw.circle(screen, (0, 200, 255), (WIDTH // 2, 150), 35)
    pygame.draw.circle(screen, (255, 255, 255), (WIDTH // 2, 138), 14)
    T(G.user.upper(), F_LARGE, (255, 255, 255), WIDTH // 2, 195, "midtop")
    box = pygame.Rect(60, 245, WIDTH - 120, 290)
    draw_card(box, (0, 220, 255), (25, 35, 55, 200), 12)
    rank = G.board.get("rank") or "-"
    rows = [("Tiền xu", str(P["coins"])), ("Kỷ lục", str(P["hs"])),
            ("Hạng", "#%s / %s" % (rank, G.board.get("total", "-"))),
            ("Skin", SKINS[P["skin"]]["name"]), ("Cấp đạn", "Lv %d" % P["bt"]),
            ("Tốc độ đạn", str(P["bs"])), ("Độ khó", DIFFS[G.difficulty]["name"]),
            ("Bạn bè", str(len(G.friends["friends"])))]
    for i, (k, v) in enumerate(rows):
        T(k, F_SMALL, (170, 190, 220), 85, 262 + i * 33)
        T(v, F_SMALL, (255, 235, 150), WIDTH - 85, 262 + i * 33, "topright")
    back_button(y=HEIGHT - 70)


def draw_friends():
    draw_card(pygame.Rect(30, 30, WIDTH - 60, HEIGHT - 60), (0, 200, 255))
    T("BẠN BÈ", F_LARGE, (0, 255, 220), WIDTH // 2, 45, "midtop")
    field(pygame.Rect(50, 112, 370, 40), "friend", "Thêm bạn:", hint="Tên rồi Gửi")
    button(pygame.Rect(430, 112, 120, 40), "Gửi", add_friend, base=(0, 150, 100), hov=(0, 190, 130),
           border=(0, 255, 160))
    reqs = G.friends["requests"]
    y = 170
    T("Lời mời (%d):" % len(reqs), F_SMALL, (255, 215, 0), 50, y)
    y += 24
    if not reqs:
        T("Không có.", F_TINY, (150, 160, 180), 65, y)
        y += 24
    else:
        for name in reqs[:3]:
            row = pygame.Rect(50, y, 500, 34)
            pygame.draw.rect(screen, (30, 40, 60), row, border_radius=6)
            T(name, F_SMALL, (255, 255, 255), 62, y + 17, "midleft")
            button(pygame.Rect(row.right - 196, y + 3, 90, 28), "OK",
                   lambda n=name: net_send({"t": "friend_accept", "name": n}),
                   base=(0, 150, 90), hov=(0, 190, 120), border=(0, 255, 150), font=F_TINY)
            button(pygame.Rect(row.right - 100, y + 3, 90, 28), "Từ chối",
                   lambda n=name: net_send({"t": "friend_decline", "name": n}),
                   base=(100, 35, 35), hov=(150, 50, 50), border=(255, 100, 100), font=F_TINY)
            y += 38
        if len(reqs) > 3:
            T("... +%d nữa" % (len(reqs) - 3), F_TINY, (150, 160, 180), 65, y)
            y += 18
    y += 10
    fr = G.friends["friends"]
    T("Bạn (%d) - kỷ lục & chat & mời:" % len(fr), F_SMALL, (0, 255, 150), 50, y)
    y += 26
    area = pygame.Rect(50, y, 500, HEIGHT - 80 - y)
    if not fr:
        T("Chưa có bạn. Kết bạn ngay!", F_TINY, (150, 160, 180), 65, y + 4)
    else:
        row_h = 48
        G.scroll = clamp(G.scroll, 0, max(0, len(fr) * row_h - area.height))
        screen.set_clip(area)
        for i, f in enumerate(fr):
            ry = area.y + i * row_h - G.scroll
            row = pygame.Rect(area.x, ry, area.width, 42)
            if row.bottom < area.top or row.top > area.bottom:
                continue
            pygame.draw.rect(screen, (20, 30, 50), row, border_radius=8)
            pygame.draw.rect(screen, (0, 150, 200), row, width=1, border_radius=8)
            pygame.draw.circle(screen, (0, 230, 110) if f["online"] else (100, 105, 120),
                               (row.x + 16, row.centery), 5)
            T(f["name"], F_SMALL, (255, 255, 255), row.x + 30, row.centery, "midleft")
            T("%d" % f["high_score"], F_SMALL, (255, 215, 0), row.x + 175, row.centery, "midleft")

            cbtn = pygame.Rect(row.right - 216, row.y + 6, 90, 30)

            def open_pm(n=f["name"]):
                G.chat_tab = "PRIVATE"
                G.chat_target = n
                G.chat_unread[n] = 0
                set_state("CHAT")
            button(cbtn, "Chat", open_pm, base=(40, 60, 110), hov=(60, 90, 150),
                   border=(120, 180, 255), font=F_TINY, enabled=area.contains(cbtn))

            btn = pygame.Rect(row.right - 118, row.y + 6, 110, 30)
            can = f["online"] and not G.in_room and area.contains(btn)
            if f["online"]:
                button(btn, "Mời chơi", lambda n=f["name"]: invite_friend(n),
                       base=(60, 40, 110), hov=(90, 60, 150), border=(200, 140, 255), font=F_TINY, enabled=can)
            else:
                T("Offline", F_TINY, (120, 125, 140), btn.centerx, btn.centery, "center")
        screen.set_clip(None)
    back_button(y=HEIGHT - 70)


def draw_board():
    draw_card(pygame.Rect(30, 30, WIDTH - 60, HEIGHT - 60), (255, 215, 0))
    T("BẢNG XẾP HẠNG", F_LARGE, (255, 215, 0), WIDTH // 2, 45, "midtop")
    for i, (key, label) in enumerate((("FRIENDS", "BẠN BÈ"), ("SERVER", "TOÀN SERVER"))):
        sel = G.board_tab == key

        def pick(k=key):
            G.board_tab = k
        button(pygame.Rect(50 + i * 255, 100, 245, 38), label, pick,
               base=(60, 50, 10) if sel else (25, 30, 50), border=(255, 215, 0) if sel else (90, 100, 130),
               color=(255, 235, 150) if sel else (170, 180, 200), font=F_MED)
    if G.board_tab == "FRIENDS":
        rows = [(f["name"], f["high_score"]) for f in G.friends["friends"]] + \
               [(G.user, max(P["hs"], G.friends["me_score"]))]
        rows.sort(key=lambda r: (-r[1], r[0]))
    else:
        rows = [(r["name"], r["score"]) for r in G.board.get("top", [])]
    area = pygame.Rect(50, 155, 500, HEIGHT - 155 - 120)
    if not rows:
        T("Chưa có dữ liệu.", F_SMALL, (150, 160, 180), WIDTH // 2, 200, "midtop")
    rh = 40
    G.scroll = clamp(G.scroll, 0, max(0, len(rows) * rh - area.height))
    screen.set_clip(area)
    for i, (name, sc) in enumerate(rows):
        r = pygame.Rect(area.x, area.y + i * rh - G.scroll, area.width, 34)
        me = (name == G.user)
        pygame.draw.rect(screen, (50, 45, 15) if me else (20, 30, 50), r, border_radius=8)
        pygame.draw.rect(screen, (255, 215, 0) if me else (60, 90, 130), r, width=1, border_radius=8)
        medal = [(255, 215, 0), (200, 205, 215), (205, 127, 50)]
        if i < 3:
            pygame.draw.circle(screen, medal[i], (r.x + 22, r.centery), 12)
            T(str(i + 1), F_SMALL, (20, 20, 20), r.x + 22, r.centery, "center")
        else:
            T("#%d" % (i + 1), F_SMALL, (170, 180, 200), r.x + 22, r.centery, "center")
        T(name + ("  (bạn)" if me else ""), F_SMALL, (255, 255, 255), r.x + 50, r.centery, "midleft")
        T("%d" % sc, F_MED, (255, 215, 0), r.right - 15, r.centery, "midright")
    screen.set_clip(None)
    if G.board_tab == "SERVER" and G.board.get("rank"):
        T("Hạng: #%d / %d" % (G.board["rank"], G.board["total"]), F_SMALL, (0, 255, 200),
          WIDTH // 2, HEIGHT - 105, "midtop")
    back_button(y=HEIGHT - 70)


def draw_chat():
    draw_card(pygame.Rect(20, 20, WIDTH - 40, HEIGHT - 40), (0, 200, 255))
    T("PHÒNG CHAT", F_LARGE, (0, 255, 220), WIDTH // 2, 30, "midtop")

    for i, (key, lbl) in enumerate((("GLOBAL", "TỔNG"), ("PRIVATE", "RIÊNG"))):
        sel = G.chat_tab == key
        r = pygame.Rect(30 + i * 135, 68, 130, 32)

        def switch(k=key):
            G.chat_tab = k
            G.chat_scroll = 0
            if k == "GLOBAL":
                G.chat_badge_global = 0
            if k == "PRIVATE" and G.chat_target:
                G.chat_unread[G.chat_target] = 0
            G.focus = "chat"
        button(r, lbl, switch,
               base=(20, 60, 60) if sel else (25, 30, 50),
               border=(0, 255, 200) if sel else (80, 100, 140),
               color=(180, 255, 240) if sel else (170, 180, 200),
               font=F_MED, bw=3 if sel else 2)
        if key == "GLOBAL" and G.chat_badge_global:
            pygame.draw.circle(screen, (255, 60, 60), (r.right - 8, r.top + 8), 9)
            T(str(min(G.chat_badge_global, 99)), F_TINY, (255, 255, 255),
              r.right - 8, r.top + 8, "center")

    msg_top = 110
    if G.chat_tab == "PRIVATE":
        T("Chọn bạn:", F_TINY, (170, 190, 220), 32, msg_top - 2)
        fr = G.friends["friends"]
        if not fr:
            T("Bạn chưa có bạn bè.", F_SMALL, (170, 180, 200), WIDTH // 2, 180, "midtop")
        else:
            bar_y = msg_top + 14
            x = 32
            for f in fr:
                w = max(70, F_SMALL.size(f["name"])[0] + 22)
                if x + w > WIDTH - 32:
                    break
                sel = G.chat_target == f["name"]
                r = pygame.Rect(x, bar_y, w, 26)
                hover = r.collidepoint(G.mouse)
                bg = (0, 120, 90) if sel else ((45, 60, 90) if hover else (28, 38, 60))
                bd = (0, 255, 180) if sel else (80, 120, 160)
                pygame.draw.rect(screen, bg, r, border_radius=6)
                pygame.draw.rect(screen, bd, r, width=1, border_radius=6)
                T(f["name"], F_SMALL, (255, 255, 255), r.centerx, r.centery, "center")
                un = G.chat_unread.get(f["name"], 0)
                if un and not sel:
                    pygame.draw.circle(screen, (255, 60, 60), (r.right - 4, r.top + 4), 8)
                    T(str(min(un, 9)), F_TINY, (255, 255, 255), r.right - 4, r.top + 4, "center")

                def pick(n=f["name"]):
                    G.chat_target = n
                    G.chat_unread[n] = 0
                    G.chat_scroll = 0
                click_area(r, pick)
                x += w + 6
            msg_top = bar_y + 34

    area = pygame.Rect(30, msg_top, WIDTH - 60, HEIGHT - msg_top - 130)
    pygame.draw.rect(screen, (10, 16, 28), area, border_radius=8)
    pygame.draw.rect(screen, (0, 120, 160), area, width=1, border_radius=8)

    if G.chat_tab == "GLOBAL":
        msgs = G.chat_global
    elif G.chat_target:
        msgs = G.chat_private.get(G.chat_target, [])
    else:
        msgs = []

    if not msgs:
        if G.chat_tab == "GLOBAL":
            T("Chưa có tin. Chào mọi người đi!", F_SMALL, (140, 155, 180),
              WIDTH // 2, msg_top + 30, "midtop")
        elif not G.chat_target:
            T("Chọn bạn để chat.", F_SMALL, (140, 155, 180), WIDTH // 2, msg_top + 30, "midtop")
        else:
            T("Chưa có tin với %s." % G.chat_target, F_SMALL, (140, 155, 180),
              WIDTH // 2, msg_top + 30, "midtop")

    screen.set_clip(area)
    line_h = 20
    pad = 8
    inner_w = area.width - 2 * pad - 4
    rendered = []
    for e in msgs:
        who = e.get("from", "?")
        text = e.get("msg", "")
        prefix = "%s: " % who
        max_chars = max(12, inner_w // 7)
        words = text.split()
        lines, cur = [], prefix
        for w_ in words:
            if len(cur) + len(w_) + 1 > max_chars:
                lines.append(cur)
                cur = "    " + w_
            else:
                cur = cur + (" " if cur and not cur.endswith(" ") else "") + w_
        lines.append(cur)
        rendered.append((who, lines))

    total_h = sum(len(l) for _, l in rendered) * line_h + 12
    max_scroll = max(0, total_h - area.height + 10)
    G.chat_scroll = clamp(G.chat_scroll, 0, max_scroll)
    y = area.bottom - pad - total_h + G.chat_scroll
    for who, lines in rendered:
        for i, ln in enumerate(lines):
            col = (255, 255, 255)
            if i == 0:
                is_me = (who == G.user)
                col = (120, 255, 200) if is_me else (255, 220, 140)
            T(ln, F_SMALL, col, area.x + pad, y)
            y += line_h
    screen.set_clip(None)

    target = G.chat_target if G.chat_tab == "PRIVATE" else "mọi người"
    hint = "Nhập tin gửi %s..." % target
    field(pygame.Rect(30, HEIGHT - 92, WIDTH - 140, 42), "chat", "", hint=hint)
    button(pygame.Rect(WIDTH - 100, HEIGHT - 92, 70, 42), "GỬI", send_chat,
           base=(0, 130, 90), hov=(0, 180, 120), border=(0, 255, 180), font=F_MED)
    button(pygame.Rect(50, HEIGHT - 50, WIDTH - 100, 32), "QUAY LẠI MENU",
           lambda: set_state("MENU"),
           base=(40, 20, 20), hov=(60, 30, 30), border=(255, 100, 100), color=(255, 200, 200))


def draw_world(w):
    li = 1 if G.mode == "guest" else 0
    update_draw_thrusters()
    update_draw_particles()
    for pu in w.powerups:
        c = POWERUP_COLORS[pu["kind"]]
        ctr = (int(pu["x"]) + 13, int(pu["y"]) + 13)
        pygame.draw.circle(screen, c, ctr, 13)
        pygame.draw.circle(screen, (255, 255, 255), ctr, 13, 2)
        T(POWERUP_LABELS[pu["kind"]], F_TINY, (10, 10, 10), ctr[0], ctr[1], "center")
    for b in w.bullets:
        col = (255, 50, 200) if b["big"] else (0, 255, 255)
        pygame.draw.rect(screen, col, (int(b["x"]), int(b["y"]), b["w"], b["h"]), border_radius=4)
    for eb in w.ebullets:
        pygame.draw.rect(screen, (255, 30, 30), (int(eb["x"]), int(eb["y"]), 8, 20), border_radius=3)
    for e in w.enemies:
        draw_enemy(e["x"], e["y"], e["type"], e["seed"])
    if w.boss:
        draw_boss(w.boss, w.level)
    for i, p in enumerate(w.players):
        if not (p.alive and p.connected):
            continue
        if p.inv > 0 and (p.inv // 4) % 2 == 0:
            continue
        draw_ship(p.x, p.y, p.skin)
        if len(w.players) > 1:
            T(p.name[:10], F_TINY, (0, 255, 200) if i == li else (255, 200, 120),
              p.x + 25, p.y - 12, "midtop")
    T("SCORE: %d" % w.score, F_MED, (255, 255, 255), 15, 15)
    T("COIN: %d" % P["coins"], F_MED, (255, 215, 0), 15, 40)
    me = w.players[li]
    T("BẠN" if len(w.players) > 1 else "HP", F_TINY, (0, 255, 100), 15, 66)
    draw_hearts(60, 74, me.hp if me.alive else 0)
    if len(w.players) > 1 and w.players[1 - li].connected:
        o = w.players[1 - li]
        T(o.name[:8].upper(), F_TINY, (255, 200, 120), 15, 88)
        draw_hearts(60, 96, o.hp if o.alive else 0)
    if me.tmp_frames > 0:
        T("VK tạm: %ds" % (me.tmp_frames // 60 + 1), F_TINY, (255, 200, 0), 15, 112)
    T("MÀN: %d/%d" % (w.level, MAX_LEVELS), F_MED, (0, 255, 200), WIDTH - 15, 15, "topright")
    if len(w.players) > 1:
        T("CHƠI ĐÔI", F_TINY, (200, 150, 255), WIDTH - 15, 40, "topright")
    if not me.alive and w.state == "PLAYING":
        T("Bạn đã gục - chờ đồng đội qua màn", F_SMALL, (255, 120, 120),
          WIDTH // 2, HEIGHT // 2 - 20, "midtop")
    if G.mode == "guest" and not G.got_snapshot:
        T("Đang đồng bộ...", F_MED, (255, 255, 255), WIDTH // 2, HEIGHT // 2, "midtop")


def draw_pause():
    r = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 100, 360, 200)
    click_area(pygame.Rect(0, 0, WIDTH, HEIGHT), lambda: None)
    draw_card(r, (255, 215, 0), (10, 15, 30, 235))
    T("TẠM DỪNG", F_LARGE, (255, 215, 0), WIDTH // 2, HEIGHT // 2 - 70, "midtop")
    button(pygame.Rect(140, HEIGHT // 2, 140, 40), "TIẾP TỤC", lambda: set_play_state("PLAYING"),
           base=(0, 140, 80), hov=(0, 200, 120), border=(0, 255, 150))

    def to_menu():
        leave_match()
        set_state("MENU")
    button(pygame.Rect(320, HEIGHT // 2, 140, 40), "MENU", to_menu, base=(140, 40, 40),
           hov=(200, 60, 60), border=(255, 100, 100))


def set_play_state(s):
    G.state = s


def draw_end():
    w = G.W
    win = G.state == "VICTORY"
    col = (0, 255, 150) if win else (255, 60, 60)
    click_area(pygame.Rect(0, 0, WIDTH, HEIGHT), lambda: None)
    draw_card(pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 160, 440, 320), col, (15, 20, 35, 240))
    T("CHIẾN THẮNG!" if win else "GAME OVER", F_LARGE, col, WIDTH // 2, HEIGHT // 2 - 125, "midtop")
    T("Điểm: %d" % (w.score if w else 0), F_MED, (255, 255, 255), WIDTH // 2, HEIGHT // 2 - 65, "midtop")
    T("Kỷ lục: %d" % P["hs"], F_MED, (255, 215, 0), WIDTH // 2, HEIGHT // 2 - 35, "midtop")
    T("Xu: %d" % P["coins"], F_SMALL, (255, 235, 150), WIDTH // 2, HEIGHT // 2 - 5, "midtop")

    def to_menu():
        leave_match()
        set_state("MENU")
    coop_over = (G.mode in ("host", "guest")) or (w is not None and len(w.players) > 1)
    if coop_over:
        button(pygame.Rect(WIDTH // 2 - 90, HEIGHT // 2 + 60, 180, 50), "MENU", to_menu, font=F_MED,
               base=(40, 55, 85), hov=(60, 80, 120))
    else:
        button(pygame.Rect(100, HEIGHT // 2 + 50, 180, 50), "CHƠI LẠI", start_solo, font=F_MED,
               base=(0, 140, 100), hov=(0, 200, 150), border=(0, 255, 200))
        button(pygame.Rect(320, HEIGHT // 2 + 50, 180, 50), "MENU", to_menu, font=F_MED,
               base=(40, 55, 85), hov=(60, 80, 120))


def draw_overlays():
    if G.invite:
        if time.time() - G.invite["t"] > 30:
            G.invite = None
        elif G.state not in ("PLAYING", "PAUSED", "SPLASH", "LOGIN"):
            click_area(pygame.Rect(0, 0, WIDTH, HEIGHT), lambda: None)
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            screen.blit(shade, (0, 0))
            box = pygame.Rect(60, 250, WIDTH - 120, 190)
            draw_card(box, (200, 140, 255), (20, 15, 40, 250))
            T("LỜI MỜI CHƠI ĐÔI", F_MED, (200, 140, 255), WIDTH // 2, box.y + 18, "midtop")
            T("%s mời bạn!" % G.invite["from"], F_MED, (255, 255, 255), WIDTH // 2, box.y + 58, "midtop")
            button(pygame.Rect(box.x + 40, box.bottom - 60, 150, 42), "Đồng ý", accept_invite,
                   base=(0, 140, 80), hov=(0, 200, 120), border=(0, 255, 150), font=F_MED)
            button(pygame.Rect(box.right - 190, box.bottom - 60, 150, 42), "Từ chối", decline_invite,
                   base=(120, 35, 35), hov=(180, 55, 55), border=(255, 100, 100), font=F_MED)
    if G.toast_msg and time.time() < G.toast_until:
        s = F_SMALL.render(G.toast_msg, True, (255, 255, 255))
        r = pygame.Rect(0, 0, s.get_width() + 30, 30)
        r.midtop = (WIDTH // 2, 6)
        pygame.draw.rect(screen, (10, 14, 28), r, border_radius=8)
        pygame.draw.rect(screen, G.toast_color, r, width=2, border_radius=8)
        screen.blit(s, s.get_rect(center=r.center))


# ==========================================================
# SỰ KIỆN
# ==========================================================
def handle_text_key(ev):
    """CHỈ xử lý phím điều khiển. Chữ thường do pygame.TEXTINPUT lo."""
    key = G.focus
    if key not in fields or ev.key == pygame.K_ESCAPE:
        return False

    # UniKey dùng DELETE (0x7F) để xoá khi compose — coi như BACKSPACE
    if ev.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
        fields[key] = fields[key][:-1]
        return True

    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        if G.state == "LOGIN":
            submit_auth()
        elif G.state == "FRIENDS":
            add_friend()
        elif G.state == "CHAT":
            send_chat()
        return True

    if ev.key == pygame.K_TAB and G.state == "LOGIN":
        order = ["user", "pass"]
        G.focus = order[(order.index(key) + 1) % 2]
        return True

    # Không xử lý ev.unicode ở đây — chờ TEXTINPUT
    return True


def handle_event(ev):
    if ev.type == pygame.QUIT:
        return False

    if G.state == "SPLASH":
        if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            set_state("LOGIN")
        return True

    # === TEXTINPUT: IME đẩy chuỗi tiếng Việt đã compose xong ===
    if ev.type == pygame.TEXTINPUT:
        key = G.focus
        if key in fields:
            ch = ev.text or ""
            ch = "".join(c for c in ch if c.isprintable())
            if ch:
                if key in ("user", "friend"):
                    ch = "".join(c for c in ch if c.isascii() and (c.isalnum() or c == "_"))
                room = FIELD_MAX[key] - len(fields[key])
                if room > 0:
                    fields[key] += ch[:room]
        return True
    # ==========================================================

    if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        for rect, fn in reversed(prev_hits):
            if rect.collidepoint(ev.pos):
                fn()
                break
    elif ev.type == pygame.MOUSEWHEEL:
        if G.state in ("FRIENDS", "BOARD"):
            G.scroll -= ev.y * 30
        elif G.state == "CHAT":
            G.chat_scroll += ev.y * 30
    elif ev.type == pygame.KEYDOWN:
        if G.state == "CHAT" and not G.focus:
            if ev.key == pygame.K_UP:
                G.chat_scroll += 40
                return True
            elif ev.key == pygame.K_DOWN:
                G.chat_scroll -= 40
                return True
        if handle_text_key(ev):
            return True
        if G.state == "LOGIN" and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            submit_auth()
        elif ev.key == pygame.K_SPACE or ev.key == pygame.K_ESCAPE:
            if G.state == "PLAYING" and G.mode == "solo":
                G.state = "PAUSED"
            elif G.state == "PAUSED":
                G.state = "PLAYING"
            elif ev.key == pygame.K_ESCAPE and G.state in (
                    "DIFF", "SHOP_WEAPON", "SHOP_SKIN", "PROFILE", "FRIENDS", "BOARD", "CHAT"):
                set_state("MENU")
    return True


# ==========================================================
# VÒNG LẶP
# ==========================================================
def frame():
    global hits, prev_hits
    prev_hits, hits = hits, []
    G.mouse = pygame.mouse.get_pos()
    G.tick += 1

    pump_net()
    for ev in pygame.event.get():
        if not handle_event(ev):
            leave_match()
            if G.user:
                send_save()
            return False

    if G.conn_lost and G.state not in ("LOGIN", "SPLASH"):
        if not (G.mode == "solo" and G.state in ("PLAYING", "PAUSED", "GAME_OVER", "VICTORY")):
            go_login("Mất kết nối. Đăng nhập lại.")

    now = time.time()
    if G.user and G.net and not G.net.closed:
        if now - G.last_ping > 25:
            G.last_ping = now
            net_send({"t": "ping"})
        if G.save_dirty and now - G.last_save > 3:
            send_save()
        if G.state in ("FRIENDS", "BOARD") and now - G.last_refresh > 5:
            refresh_social()

    if G.state in ("MENU", "LOGIN", "DIFF", "SHOP_WEAPON", "SHOP_SKIN", "PROFILE",
                   "FRIENDS", "BOARD", "GAME_OVER", "VICTORY", "SPLASH", "CHAT"):
        play_bgm("MENU")
    elif G.state in ("PLAYING", "PAUSED"):
        play_bgm("GAME")

    if G.state == "SPLASH":
        draw_splash()
        pygame.display.flip()
        clock.tick(60)
        return True

    if G.state == "PLAYING":
        update_play()

    draw_stars()
    if G.state in ("PLAYING", "PAUSED", "GAME_OVER", "VICTORY") and G.W is not None:
        draw_world(G.W)
        if G.state == "PAUSED":
            draw_pause()
        elif G.state in ("GAME_OVER", "VICTORY"):
            draw_end()
    else:
        update_draw_particles()
        {"LOGIN": draw_login, "MENU": draw_menu, "DIFF": draw_diff,
         "SHOP_WEAPON": draw_shop_weapon, "SHOP_SKIN": draw_shop_skin, "PROFILE": draw_profile,
         "FRIENDS": draw_friends, "BOARD": draw_board, "CHAT": draw_chat}.get(G.state, lambda: None)()
    draw_overlays()
    pygame.display.flip()
    clock.tick(60)
    return True


def main():
    load_config()
    while frame():
        pass
    if G.net:
        time.sleep(0.15)
        G.net.close()
    pygame.quit()


if __name__ == "__main__":
    main()
