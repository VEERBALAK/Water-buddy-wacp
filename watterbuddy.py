import json
import os
import re
from datetime import date, datetime, timedelta
from html import escape

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="WaterBuddy", page_icon="💧", layout="centered")

DONE_KEY = "waterbuddy_reminderSetupDone"
USERS_KEY = "waterbuddy_users"
PROFILE_KEY = "waterbuddy_profile"
HISTORY_KEY = "waterbuddy_history"
REMINDERS_KEY = "waterbuddy_reminders"
INTERVALS = [30, 45, 60, 90, 120]
DEFAULT_GLASS_ML = 250
STORE_FILE = "waterbuddy_state.json"  # stands in for window.localStorage

PAGES = [("Home", "🏠"), ("Tips", "💡"), ("Board", "🏆"), ("Profile", "👤")]

# (name, emoji, range, suggested daily goal in ml)
AGE_GROUPS = [
    ("Children", "🧒", "4-6 yrs", 1200),
    ("Kids", "👦", "7-12 yrs", 1600),
    ("Teens", "🧑‍🎓", "13-17 yrs", 2200),
    ("Adults", "👨‍💼", "18-64 yrs", 2500),
    ("Seniors", "👴", "65+ yrs", 2000),
]
AGE_GOAL = {name: goal for name, _, _, goal in AGE_GROUPS}

# (xp needed, title)  -  1 XP for every 2 ml logged
LEVELS = [
    (0, "Sipper"),
    (500, "Splasher"),
    (1500, "Wave Rider"),
    (3500, "Hydro Hero"),
    (7000, "Aqua Legend"),
]

BENEFITS = [
    ("⚡", "Energy", "Water keeps your energy steady - no afternoon slump."),
    ("✨", "Skin", "Hydration helps your skin stay fresh and glowing."),
    ("😊", "Mood", "Drinking enough water is linked to feeling happier."),
    ("🎯", "Focus", "Your brain is ~75% water - sip to think clearly."),
]

TIPS = [
    "Start your day with a glass of water to wake up your body.",
    "Carry a reusable bottle everywhere - out of sight is out of mind.",
    "Add a slice of lemon or cucumber for a refreshing twist.",
    "Drink a glass of water before each meal to aid digestion.",
    "Set a gentle reminder every hour to take a few sips.",
    "Eat water-rich foods like watermelon, cucumber and oranges.",
    "Hydrate before, during and after any exercise.",
    "Don't wait until you're thirsty - thirst means you're already low.",
    "A splash of mint makes plain water feel like a treat.",
    "Track your intake - what gets measured gets improved.",
]

_HAS_DIALOG = hasattr(st, "dialog") or hasattr(st, "experimental_dialog")


# ---------- small helpers ----------
def _html(s):
    # Strip indentation and blank lines so Markdown never turns the HTML into a code block
    return "\n".join(line.strip() for line in s.splitlines() if line.strip())


def keyed_container(key):
    # container(key=...) needs a recent Streamlit; fall back to a plain container
    try:
        return st.container(key=key)
    except TypeError:
        return st.container()


def inject_css():
    st.markdown(
        _html(
            """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

html, body, .stApp, button, input, textarea, select {
  font-family: 'Space Grotesk', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}
.stApp {
  background-color: #040a14;
  background-image: radial-gradient(rgba(16,224,255,.07) 1px, transparent 1px);
  background-size: 26px 26px;
  color: #eaf6ff;
}
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp li, .stApp span {
  color: #eaf6ff;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #8a9bb4 !important; }
header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"],
[data-testid="stSidebar"], [data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.block-container { max-width: 430px !important; padding: 1.2rem 1rem 9rem !important; }

/* inputs */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div {
  background: #08121f !important; border-color: #123049 !important; border-radius: 14px !important;
}
input, textarea { background: transparent !important; color: #eaf6ff !important; }
[data-testid="stNumberInput"] button { background: #0b1a2b !important; color: #8fb4cc !important; border: none !important; }
[data-testid="stWidgetLabel"] p, label p {
  color: #8a9bb4 !important; font-size: 12px; font-weight: 700; letter-spacing: .06em;
}
div[role="dialog"] { background: #07111f !important; border: 1px solid rgba(16,224,255,.35); border-radius: 26px; }
[data-testid="stToast"], div[data-baseweb="toast"] {
  background: #0a1626 !important; border: 1px solid rgba(16,224,255,.3); border-radius: 14px;
}
[data-testid="stForm"] { border: none !important; padding: 0 !important; }

/* bordered containers = cards */
[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid rgba(16,224,255,.22) !important; border-radius: 22px !important;
  background: rgba(7,18,34,.92); padding: .4rem .35rem;
}

/* buttons: default = dark card, primary = neon cyan */
.stButton > button, .stFormSubmitButton > button {
  background: #08121f; color: #cfe8ff; border: 1px solid #123049;
  border-radius: 14px; font-weight: 600; white-space: pre-line;
}
.stButton > button p { color: inherit; }
.stButton > button:hover { border-color: #10e0ff; color: #10e0ff; }
button[kind="primary"], button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: #10e0ff !important; color: #031923 !important; border: none !important;
  box-shadow: 0 0 26px rgba(16,224,255,.35);
}
button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p { color: #031923 !important; font-weight: 700; }

/* selectable chips + age cards (primary = selected, but outlined not solid) */
[class*="st-key-chips"] [data-testid="stHorizontalBlock"],
[class*="st-key-agegrid"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .45rem !important; }
[class*="st-key-chips"] [data-testid="stColumn"], [class*="st-key-agegrid"] [data-testid="stColumn"],
[class*="st-key-chips"] [data-testid="column"], [class*="st-key-agegrid"] [data-testid="column"] {
  min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;
}
[class*="st-key-chips"] button { border-radius: 999px; padding: .15rem 0; min-height: 2.1rem; font-size: 13px; }
[class*="st-key-agegrid"] button { min-height: 104px; border-radius: 18px; line-height: 1.5; background: #07142a; }
[class*="st-key-chips"] button[kind="primary"], [class*="st-key-chips"] button[data-testid="stBaseButton-primary"],
[class*="st-key-agegrid"] button[kind="primary"], [class*="st-key-agegrid"] button[data-testid="stBaseButton-primary"] {
  background: rgba(16,224,255,.16) !important; color: #10e0ff !important;
  border: 1px solid #10e0ff !important; box-shadow: 0 0 22px rgba(16,224,255,.25);
}
[class*="st-key-chips"] button[kind="primary"] p, [class*="st-key-chips"] button[data-testid="stBaseButton-primary"] p,
[class*="st-key-agegrid"] button[kind="primary"] p, [class*="st-key-agegrid"] button[data-testid="stBaseButton-primary"] p {
  color: #10e0ff !important;
}

/* big Log Water button, sound button, danger button */
.st-key-logwater button { height: 64px; font-size: 20px; border-radius: 20px; }
.st-key-logwater button p { font-size: 20px; font-weight: 700; }
.st-key-getstarted button { height: 56px; border-radius: 18px; }
.st-key-getstarted button p, .st-key-survey_next button p { font-size: 18px; }
.st-key-survey_next button { height: 58px; border-radius: 18px; }
.st-key-soundbtn button, .st-key-boardrefresh button, .st-key-backbtn button {
  border-radius: 999px; width: 46px; height: 46px; padding: 0; border-color: #123049;
}
.st-key-dangerbtn button { color: #ff5d73; border-color: rgba(255,93,115,.45); }
.st-key-dangerbtn button p { color: #ff5d73 !important; }

/* header */
.wb-head { display: flex; align-items: center; gap: 12px; }
.wb-logo {
  width: 52px; height: 52px; border-radius: 16px; background: #10e0ff; flex: 0 0 auto;
  display: flex; align-items: center; justify-content: center; font-size: 25px;
  box-shadow: 0 0 22px rgba(16,224,255,.45);
}
.wb-title { font-size: 19px; font-weight: 700; color: #fff; line-height: 1.1; }
.wb-sub { font-size: 12px; color: #8a9bb4; display: flex; gap: 8px; align-items: center; margin-top: 4px; }
.wb-badge {
  border: 1px solid #e8dc4a; color: #f6ec5c; border-radius: 999px;
  padding: 0 8px; font-size: 11px; font-weight: 700; background: rgba(232,220,74,.06);
}

/* page headers (Tips / Board / Profile) */
.wb-phead { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.wb-phead .wb-logo { width: 42px; height: 42px; border-radius: 13px; font-size: 20px; }
.wb-phead b { font-size: 21px; color: #fff; display: block; line-height: 1.1; }
.wb-phead span.s { font-size: 13px; color: #8a9bb4; }
.wb-ptitle { font-size: 28px; font-weight: 700; color: #fff; margin: 0; line-height: 1.1; }
.wb-psub { font-size: 14px; color: #8a9bb4; margin: 4px 0 14px; }

/* main card */
.wb-card {
  position: relative; text-align: center; margin-top: 12px; padding: 24px 14px 20px;
  border: 1px solid rgba(16,224,255,.38); border-radius: 28px;
  background: linear-gradient(180deg, #06142a 0%, #040e1d 100%);
  box-shadow: 0 0 36px rgba(16,224,255,.12), inset 0 0 36px rgba(16,224,255,.04);
}
.wb-mascot { position: absolute; top: 14px; right: 18px; filter: drop-shadow(0 0 10px rgba(16,224,255,.55)); }
.wb-ring { position: relative; width: 210px; margin: 8px auto 12px; }
.wb-ring svg { width: 100%; height: auto; display: block; }
.wb-ring-text {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.wb-big { font-size: 46px; font-weight: 700; color: #fff; line-height: 1; }
.wb-big span { font-size: 18px; color: #8a9bb4; margin-left: 4px; }
.wb-of { font-size: 15px; color: #8a9bb4; margin-top: 8px; }
.wb-pct { font-size: 13px; color: #10e0ff; font-weight: 700; margin-top: 6px; letter-spacing: 2px; }
.wb-hey { font-size: 21px; font-weight: 700; color: #fff; margin-top: 10px; }
.wb-msg { font-size: 16px; font-weight: 700; color: #10e0ff; margin-top: 6px; }
.wb-remind { text-align: center; color: #8a9bb4; font-size: 13px; margin: 12px 0 12px; }

/* stat tiles */
.wb-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.wb-grid2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 14px; }
.wb-stat {
  border: 1px solid #12304a; border-radius: 18px; background: #06142a;
  padding: 12px 6px; text-align: center;
}
.wb-stat .ic { font-size: 18px; }
.wb-stat b { display: block; color: #fff; font-size: 18px; margin-top: 2px; }
.wb-stat small { color: #8a9bb4; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
.wb-stat i { display: block; font-style: normal; color: #5f7590; font-size: 11px; margin-top: 2px; }

/* generic panel */
.wb-panel {
  border: 1px solid rgba(16,224,255,.22); border-radius: 22px; background: rgba(7,18,34,.92);
  padding: 16px; margin-bottom: 14px;
}
.wb-ph { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 4px; }
.wb-ph .i { color: #10e0ff; }
.wb-note { color: #8a9bb4; font-size: 12px; margin: 0 0 10px; }
.wb-mini {
  border: 1px solid #123049; border-radius: 14px; background: #06142a;
  padding: 12px; margin-top: 10px;
}
.wb-mini .e { font-size: 18px; }
.wb-mini b { display: block; color: #10e0ff; font-size: 15px; margin: 6px 0 4px; }
.wb-mini span { color: #8a9bb4; font-size: 12.5px; line-height: 1.4; }
.wb-tip {
  display: flex; gap: 10px; align-items: flex-start; border: 1px solid #123049; border-radius: 14px;
  background: #06142a; padding: 12px 14px; margin-top: 10px; color: #fff; font-size: 14.5px; line-height: 1.35;
}
.wb-tip .d { color: #10e0ff; }

/* hero (profile) */
.wb-hero {
  display: flex; align-items: center; gap: 14px; margin-bottom: 12px; padding: 14px;
  border: 1px solid rgba(16,224,255,.35); border-radius: 24px;
  background: linear-gradient(180deg, #06142a 0%, #040e1d 100%);
  box-shadow: 0 0 30px rgba(16,224,255,.1);
}
.wb-hero b { color: #fff; font-size: 18px; display: block; }
.wb-hero .lv { color: #f6ec5c; font-weight: 700; font-size: 14px; margin-top: 4px; }
.wb-hero .sm { color: #8a9bb4; font-size: 13px; margin-top: 3px; }

/* bars + weekly chart */
.wb-bar { margin: 8px 0; }
.wb-bar .t { display: flex; justify-content: space-between; color: #8a9bb4; font-size: 12px; margin-bottom: 4px; }
.wb-bar .t b { color: #fff; }
.wb-track { height: 8px; border-radius: 999px; background: #0c1b2e; overflow: hidden; }
.wb-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #0a9fb8, #10e0ff); }
.wb-week { display: flex; align-items: flex-end; justify-content: space-between; gap: 8px; height: 110px; margin-top: 10px; }
.wb-col { flex: 1; text-align: center; }
.wb-colbar { width: 100%; border-radius: 8px 8px 3px 3px; background: linear-gradient(180deg, #10e0ff, #0a8fa8); }
.wb-col small { color: #8a9bb4; font-size: 11px; display: block; margin-top: 4px; }
.wb-goalrow {
  display: flex; align-items: center; gap: 12px; border: 1px solid rgba(16,224,255,.3);
  border-radius: 16px; background: rgba(16,224,255,.05); padding: 12px 14px; margin: 12px 0;
}
.wb-goalrow .ic { font-size: 22px; }
.wb-goalrow small { color: #8a9bb4; font-size: 10px; font-weight: 700; letter-spacing: 1px; display: block; }
.wb-goalrow b { color: #10e0ff; font-size: 20px; }
.wb-goalrow em { color: #8a9bb4; font-size: 12px; font-style: normal; margin-left: 4px; }

/* list rows (board / sips) */
.wb-row {
  display: flex; align-items: center; gap: 12px; margin-bottom: 10px; padding: 12px 14px;
  border: 1px solid #12304a; border-radius: 16px; background: #06142a;
}
.wb-row .ic { font-size: 22px; min-width: 30px; text-align: center; }
.wb-row b { color: #fff; }
.wb-row .end { margin-left: auto; color: #10e0ff; font-weight: 700; white-space: nowrap; }
.wb-empty { text-align: center; padding: 22px 10px 8px; }
.wb-empty b { color: #fff; display: block; font-size: 16px; margin-top: 10px; }
.wb-empty span { color: #8a9bb4; font-size: 13px; }

/* welcome + survey */
.wb-welcome { text-align: center; padding-top: 18px; }
.wb-welcome .mascot { filter: drop-shadow(0 0 22px rgba(16,224,255,.6)); }
.wb-brand { display: flex; justify-content: center; align-items: center; gap: 12px; margin: 14px 0 8px; }
.wb-brand .wb-logo { width: 46px; height: 46px; font-size: 22px; }
.wb-brand b { font-size: 34px; color: #fff; }
.wb-tag { color: #10e0ff; font-weight: 700; font-size: 16px; margin-bottom: 12px; }
.wb-desc { color: #8a9bb4; font-size: 15px; line-height: 1.55; margin: 0 6px 18px; }
.wb-foot { text-align: center; color: #8a9bb4; font-size: 12px; margin-top: 14px; }
.wb-kicker { color: #10e0ff; font-weight: 700; font-size: 12px; letter-spacing: .2em; margin-top: 4px; }
.wb-h1 { color: #fff; font-size: 27px; font-weight: 700; margin: 4px 0 4px; }
.wb-goalbox {
  border: 1px solid rgba(16,224,255,.25); border-radius: 22px; background: rgba(7,18,34,.92);
  padding: 16px; margin: 14px 0 4px;
}
.wb-goalbox small { color: #8a9bb4; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
.wb-goalbox b { display: block; color: #10e0ff; font-size: 30px; margin: 4px 0 10px; }

/* bottom navigation */
.st-key-bottomnav {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 999;
  background: #060f1c; border-top: 1px solid #12304a; padding: .35rem 0 .6rem;
}
.st-key-bottomnav > div { max-width: 430px; margin: 0 auto; padding: 0 .5rem; }
.st-key-bottomnav [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .2rem !important; }
.st-key-bottomnav [data-testid="stColumn"], .st-key-bottomnav [data-testid="column"] {
  min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;
}
.st-key-bottomnav button, .st-key-bottomnav button[kind="primary"],
.st-key-bottomnav button[data-testid="stBaseButton-primary"] {
  background: transparent !important; border: none !important; box-shadow: none !important;
  color: #8a9bb4 !important; padding: .2rem 0; line-height: 1.3;
}
.st-key-bottomnav button p { color: #8a9bb4 !important; font-size: 12px; font-weight: 700; }
.st-key-bottomnav button[kind="primary"] p,
.st-key-bottomnav button[data-testid="stBaseButton-primary"] p { color: #10e0ff !important; }
</style>
"""
        ),
        unsafe_allow_html=True,
    )


# ---------- stand-ins for the imports used in the React version ----------

# window.localStorage
def _load_store():
    store = dict(st.session_state.get("_local_storage", {}))
    if not store and os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r") as f:
                store = json.load(f)
        except (json.JSONDecodeError, OSError):
            store = {}
    return store


def _save_store(store):
    st.session_state["_local_storage"] = store
    try:
        with open(STORE_FILE, "w") as f:
            json.dump(store, f)
    except OSError:
        pass  # file system not writable (e.g. in-browser sandbox)


class local_storage:
    @staticmethod
    def get_item(key):
        return _load_store().get(key)

    @staticmethod
    def set_item(key, value):
        store = _load_store()
        store[key] = value
        _save_store(store)

    @staticmethod
    def remove_item(key):
        store = _load_store()
        store.pop(key, None)
        _save_store(store)


# @/hooks/useReminders  (kept per user)
def use_reminders():
    user = st.session_state.get("user")
    uid = user["id"] if user else "guest"
    key = f"{REMINDERS_KEY}_{uid}"
    if st.session_state.get("_reminders_for") != uid:
        defaults = {"enabled": False, "intervalMinutes": 30, "from": 8, "to": 22}
        st.session_state["reminders"] = {**defaults, **(local_storage.get_item(key) or {})}
        st.session_state["_reminders_for"] = uid
    reminders = st.session_state["reminders"]

    def update(changes):
        reminders.update(changes)
        local_storage.set_item(key, dict(reminders))

    return reminders, update


# @/lib/AuthContext  (demo auth: just a name, kept on this device)
def use_auth():
    user = st.session_state.get("user")
    is_loading_auth = False
    return user, is_loading_auth


def logout():
    st.session_state["user"] = None
    st.session_state["open"] = False
    st.session_state["askedFor"] = None
    st.session_state["tab"] = "Home"
    st.rerun()


# @/lib/sounds
class sounds:
    @staticmethod
    def blip():
        if not st.session_state.get("sound_on", True):
            return
        components.html(
            """
            <script>
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.frequency.value = 880; g.gain.value = 0.08;
            o.start(); o.stop(ctx.currentTime + 0.12);
            </script>
            """,
            height=0,
        )


def speak(text):
    if not st.session_state.get("sound_on", True):
        return
    safe = json.dumps(text)
    components.html(
        f"""
        <script>
        const u = new SpeechSynthesisUtterance({safe});
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(u);
        </script>
        """,
        height=0,
    )


# Use st.dialog if this Streamlit version has it, otherwise fall back to an inline box
def _dialog(title):
    dlg = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
    if dlg is not None:
        return dlg(title)

    def passthrough(fn):
        def wrapper(*args, **kwargs):
            with st.container(border=True):
                st.subheader(title)
                return fn(*args, **kwargs)
        return wrapper

    return passthrough


# ---------- data helpers ----------
def get_profile(user):
    return local_storage.get_item(f"{PROFILE_KEY}_{user['id']}") or {}


def save_profile(user, **changes):
    profile = get_profile(user)
    profile.update(changes)
    local_storage.set_item(f"{PROFILE_KEY}_{user['id']}", profile)


def get_age_group(user):
    return get_profile(user).get("age_group")


def get_goal(user):
    profile = get_profile(user)
    return profile.get("goal") or AGE_GOAL.get(profile.get("age_group"), 2200)


def auto_goal(user):
    return AGE_GOAL.get(get_profile(user).get("age_group"), 2200)


def get_glass(user):
    return get_profile(user).get("glass", DEFAULT_GLASS_ML)


def get_history(user):
    return local_storage.get_item(f"{HISTORY_KEY}_{user['id']}") or {}


def save_history(user, history):
    local_storage.set_item(f"{HISTORY_KEY}_{user['id']}", history)


def day_total(history, day):
    return sum(s["ml"] for s in history.get(day, []))


def get_today_ml(user):
    return day_total(get_history(user), date.today().isoformat())


def add_sip(user, ml):
    history = get_history(user)
    today = date.today().isoformat()
    history.setdefault(today, []).append({"t": datetime.now().strftime("%H:%M"), "ml": ml})
    save_history(user, history)


def undo_sip(user):
    history = get_history(user)
    today = date.today().isoformat()
    if history.get(today):
        history[today].pop()
        save_history(user, history)


def reset_today(user):
    history = get_history(user)
    history[date.today().isoformat()] = []
    save_history(user, history)


def calc_streak(history, goal):
    d = date.today()
    if day_total(history, d.isoformat()) < goal:
        d -= timedelta(days=1)
    streak = 0
    while day_total(history, d.isoformat()) >= goal:
        streak += 1
        d -= timedelta(days=1)
    return streak


def calc_stars(history, goal):
    return sum(1 for day in history if day_total(history, day) >= goal)


def calc_xp(history):
    return sum(day_total(history, day) for day in history) // 2


def level_info(xp):
    idx = 0
    for i, (need, _) in enumerate(LEVELS):
        if xp >= need:
            idx = i
    to_next = LEVELS[idx + 1][0] - xp if idx + 1 < len(LEVELS) else 0
    return idx + 1, LEVELS[idx][1], to_next


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "user"


# ---------- svg helpers ----------
def mascot_svg(mode="sleepy", w=64, h=80):
    ink = "#06364a"
    if mode == "sleepy":
        face = (
            f'<path d="M18 50 q5 4 10 0" stroke="{ink}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
            f'<path d="M36 50 q5 4 10 0" stroke="{ink}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
            f'<path d="M26 63 q6 -4 12 0" stroke="{ink}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
            '<text x="50" y="14" font-size="9" font-weight="700" fill="#7fe3ff">z</text>'
            '<text x="56" y="7" font-size="7" font-weight="700" fill="#7fe3ff">z</text>'
        )
    else:
        face = (
            f'<circle cx="23" cy="50" r="3.6" fill="{ink}"/><circle cx="41" cy="50" r="3.6" fill="{ink}"/>'
            f'<path d="M23 60 q9 9 18 0" stroke="{ink}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
        )
    return (
        f'<svg viewBox="0 0 64 80" width="{w}" height="{h}" style="overflow:visible">'
        '<defs><linearGradient id="mg" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#7ff0ff"/><stop offset="1" stop-color="#1fb4d8"/>'
        "</linearGradient></defs>"
        '<path d="M32 4 C32 4 6 36 6 54 a26 26 0 0 0 52 0 C58 36 32 4 32 4z" fill="url(#mg)"/>'
        '<path d="M16 46 C16 38 22 30 28 22" stroke="#d6faff" stroke-width="3" fill="none" '
        'stroke-linecap="round" opacity=".6"/>'
        + face
        + "</svg>"
    )


def ring_svg(pct):
    radius = 90
    circ = 2 * 3.14159265 * radius
    offset = circ * (1 - min(pct, 100) / 100)
    glow = "filter:drop-shadow(0 0 6px rgba(16,224,255,.7));" if pct > 0 else ""
    return (
        '<svg viewBox="0 0 210 210">'
        '<defs><linearGradient id="wbg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#10e0ff"/><stop offset="1" stop-color="#3b82f6"/>'
        "</linearGradient></defs>"
        f'<circle cx="105" cy="105" r="{radius}" fill="none" stroke="#0c1a2e" stroke-width="16"/>'
        f'<circle cx="105" cy="105" r="{radius}" fill="none" stroke="url(#wbg)" stroke-width="16" '
        f'stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}" '
        f'transform="rotate(-90 105 105)" style="{glow}"/>'
        "</svg>"
    )


def mode_for(pct):
    return "sleepy" if pct == 0 else "happy"


# ---------- Welcome page (name) ----------
def WelcomePage():
    st.markdown(
        _html(
            f"""
<div class="wb-welcome">
<div class="mascot">{mascot_svg("happy", 92, 115)}</div>
<div class="wb-brand"><div class="wb-logo">💧</div><b>WaterBuddy</b></div>
<div class="wb-tag">Hydration Today, Healthier Tomorrow</div>
<div class="wb-desc">Your friendly hydration companion - age-aware goals, live progress, a happy mascot and a leaderboard to keep you motivated.</div>
</div>
"""
        ),
        unsafe_allow_html=True,
    )
    name = st.text_input(
        "Your name",
        placeholder="Enter your name",
        label_visibility="collapsed",
        key="welcome_name",
    )
    with keyed_container("getstarted"):
        go = st.button("Get Started", type="primary", use_container_width=True)
    if go:
        clean = name.strip()
        if not clean:
            st.error("Please enter your name to continue.")
        else:
            uid = slug(clean)
            users = local_storage.get_item(USERS_KEY) or {}
            if uid not in users:
                users[uid] = {"name": clean}
                local_storage.set_item(USERS_KEY, users)
            st.session_state["user"] = {"id": uid, "name": users[uid]["name"]}
            st.rerun()
    st.markdown(
        '<div class="wb-foot">🔒 Your sip-by-sip log stays on your device - only today\'s total joins the leaderboard.</div>',
        unsafe_allow_html=True,
    )


# ---------- Age survey ----------
def AgeGrid(selected, on_pick, pick_args, prefix):
    with keyed_container(f"agegrid_{prefix}"):
        for row in (AGE_GROUPS[:3], AGE_GROUPS[3:]):
            cols = st.columns(3)
            for col, (name, icon, rng, _) in zip(cols, row):
                with col:
                    st.button(
                        f"{icon}  \n**{name}**  \n{rng}",
                        key=f"age_{prefix}_{name}",
                        type="primary" if selected == name else "secondary",
                        use_container_width=True,
                        on_click=on_pick,
                        args=(*pick_args, name),
                    )


def _survey_pick(name):
    st.session_state["survey_group"] = name


def SurveyPage(user):
    st.session_state.setdefault("survey_group", "Adults")
    group = st.session_state["survey_group"]

    with keyed_container("backbtn"):
        if st.button("←", key="survey_back"):
            logout()

    st.markdown(
        _html(
            """
<div class="wb-kicker">QUICK SURVEY</div>
<div class="wb-h1">Who's hydrating today?</div>
<div class="wb-psub">Pick your age group for an age-aware daily goal.</div>
"""
        ),
        unsafe_allow_html=True,
    )
    AgeGrid(group, _survey_pick, (), "survey")

    st.markdown(
        _html(
            f"""
<div class="wb-goalbox"><small>SUGGESTED DAILY GOAL</small><b>{AGE_GOAL[group]} ml</b></div>
"""
        ),
        unsafe_allow_html=True,
    )
    custom = st.text_input("Want a different goal? (optional)", placeholder="e.g. 2200", key="survey_goal")
    with keyed_container("survey_next"):
        nxt = st.button("Next", type="primary", use_container_width=True)
    if nxt:
        goal = None
        if custom.strip():
            digits = re.sub(r"\D", "", custom)
            if digits and 500 <= int(digits) <= 6000:
                goal = int(digits)
            else:
                st.error("Enter a goal between 500 and 6000 ml, or leave it empty.")
                return
        save_profile(user, age_group=group, goal=goal)
        st.session_state["askedFor"] = None  # make sure the reminder prompt shows next
        st.rerun()


# ---------- Header ----------
def toggle_sound():
    st.session_state["sound_on"] = not st.session_state.get("sound_on", True)


def Header(user):
    history = get_history(user)
    level, title, _ = level_info(calc_xp(history))
    left, right = st.columns([5, 1])
    with left:
        st.markdown(
            _html(
                f"""
<div class="wb-head">
<div class="wb-logo">💧</div>
<div>
<div class="wb-title">WaterBuddy</div>
<div class="wb-sub">{date.today().strftime("%A, %b %d")} <span class="wb-badge">Lv {level} · {title}</span></div>
</div>
</div>
"""
            ),
            unsafe_allow_html=True,
        )
    with right:
        with keyed_container("soundbtn"):
            st.button(
                "🔊" if st.session_state.get("sound_on", True) else "🔇",
                key="sound_toggle",
                on_click=toggle_sound,
            )


def PageHead(icon, title, sub):
    st.markdown(
        _html(
            f"""
<div class="wb-phead"><div class="wb-logo">{icon}</div>
<div><b>{title}</b><span class="s">{sub}</span></div></div>
"""
        ),
        unsafe_allow_html=True,
    )


# ---------- Home ----------
def _go_home():
    st.session_state["tab"] = "Home"


def HomePage(user):
    goal = get_goal(user)
    glass = get_glass(user)
    history = get_history(user)
    ml = get_today_ml(user)
    pct = min(int(ml / goal * 100), 100) if goal else 0
    remaining = max(goal - ml, 0)
    reminders = st.session_state["reminders"]

    if pct == 0:
        msg = "💧 Time to start sipping!"
    elif pct < 50:
        msg = "💦 Nice start, keep sipping!"
    elif pct < 100:
        msg = "🌊 Over halfway there!"
    else:
        msg = "🎉 Goal smashed. Great job!"

    st.markdown(
        _html(
            f"""
<div class="wb-card">
<div class="wb-mascot">{mascot_svg(mode_for(pct), 50, 62)}</div>
<div class="wb-ring">
{ring_svg(pct)}
<div class="wb-ring-text">
<div class="wb-big">{ml}<span>ml</span></div>
<div class="wb-of">of {goal} ml</div>
<div class="wb-pct">{pct}%</div>
</div>
</div>
<div class="wb-hey">Hey {escape(user['name'])}! 👋</div>
<div class="wb-msg">{msg}</div>
</div>
"""
        ),
        unsafe_allow_html=True,
    )

    st.write("")
    with keyed_container("logwater"):
        if st.button("💧  Log Water", type="primary", use_container_width=True):
            before = get_today_ml(user)
            add_sip(user, glass)
            sounds.blip()
            if before < goal <= before + glass:
                st.toast("Daily goal reached. Great job!", icon="🎉")
            else:
                st.toast(f"+{glass} ml logged", icon="💧")
            st.rerun()

    if reminders.get("enabled"):
        remind_text = (
            f"🔔 Reminders on · every {reminders['intervalMinutes']} min · "
            f"{reminders['from']}:00-{reminders['to']}:00"
        )
    else:
        remind_text = "🔕 Reminders off · turn them on in the Profile tab"
    st.markdown(f'<div class="wb-remind">{remind_text}</div>', unsafe_allow_html=True)

    st.markdown(
        _html(
            f"""
<div class="wb-stats">
<div class="wb-stat"><div class="ic">🎯</div><b>{remaining} ml</b><small>REMAINING</small></div>
<div class="wb-stat"><div class="ic">🔥</div><b>{calc_streak(history, goal)} days</b><small>STREAK</small></div>
<div class="wb-stat"><div class="ic">⭐</div><b>{calc_stars(history, goal)}</b><small>STARS</small></div>
</div>
"""
        ),
        unsafe_allow_html=True,
    )


# ---------- Tips ----------
def _cups_changed():
    st.session_state["ml_val"] = float(round(st.session_state["cups_val"] * 240))


def _ml_changed():
    st.session_state["cups_val"] = round(st.session_state["ml_val"] / 240, 2)


def TipsPage():
    st.markdown(
        '<div class="wb-ptitle">Tips</div><div class="wb-psub">Why hydration matters - and how to win it.</div>',
        unsafe_allow_html=True,
    )

    cards = "".join(
        f'<div class="wb-mini"><div class="e">{e}</div><b>{t}</b><span>{d}</span></div>'
        for e, t, d in BENEFITS
    )
    st.markdown(
        _html(
            f"""
<div class="wb-panel"><div class="wb-ph"><span class="i">✨</span> Why hydration matters</div>
<div class="wb-grid2" style="margin:0">{cards}</div></div>
"""
        ),
        unsafe_allow_html=True,
    )

    tips = "".join(f'<div class="wb-tip"><span class="d">💧</span><span>{t}</span></div>' for t in TIPS)
    st.markdown(
        _html(
            f"""
<div class="wb-panel"><div class="wb-ph"><span class="i">💡</span> Hydration tips</div>{tips}</div>
"""
        ),
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("cups_val", 1.0)
    st.session_state.setdefault("ml_val", 240.0)
    with st.container(border=True):
        st.markdown('<div class="wb-ph"><span class="i">🔁</span> Cups ⇄ millilitres</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.number_input("CUPS", min_value=0.0, step=0.5, format="%.2f", key="cups_val", on_change=_cups_changed)
        with c2:
            st.number_input("MILLILITRES", min_value=0.0, step=10.0, format="%.0f", key="ml_val", on_change=_ml_changed)


# ---------- Board ----------
def BoardPage(user):
    left, right = st.columns([5, 1])
    with left:
        PageHead("🏆", "Leaderboard", "How everyone's sipping today")
    with right:
        with keyed_container("boardrefresh"):
            st.button("🔄", key="board_refresh")

    users = local_storage.get_item(USERS_KEY) or {}
    rows = []
    for uid, info in users.items():
        other = {"id": uid, "name": info["name"]}
        ml = get_today_ml(other)
        if ml > 0:
            rows.append((ml, info["name"], uid, get_goal(other)))
    rows.sort(reverse=True)

    if not rows:
        st.markdown(
            _html(
                """
<div class="wb-panel wb-empty"><div style="font-size:34px">💧</div>
<b>No one has logged water yet today</b><span>Be the first on the board!</span></div>
"""
            ),
            unsafe_allow_html=True,
        )
        st.button("💧  Log Water", type="primary", use_container_width=True, on_click=_go_home, key="board_log")
        return

    medals = ["🥇", "🥈", "🥉"]
    for i, (ml, name, uid, goal) in enumerate(rows):
        icon = medals[i] if i < 3 else f"#{i + 1}"
        you = " (you)" if uid == user["id"] else ""
        pct = min(int(ml / goal * 100), 100)
        st.markdown(
            _html(
                f"""
<div class="wb-row"><div class="ic">{icon}</div>
<div><b>{escape(name)}{you}</b></div><div class="end">{ml} ml · {pct}%</div></div>
"""
            ),
            unsafe_allow_html=True,
        )


# ---------- Profile ----------
def _rename(user):
    new = st.session_state.get(f"profile_name_{user['id']}", "").strip()
    if not new:
        return
    users = local_storage.get_item(USERS_KEY) or {}
    if user["id"] in users:
        users[user["id"]]["name"] = new
        local_storage.set_item(USERS_KEY, users)
    st.session_state["user"]["name"] = new


def _pick_profile_group(user, name):
    save_profile(user, age_group=name)


def _save_goal(user, goal):
    save_profile(user, goal=goal)


def _set_interval(update, minutes):
    update({"intervalMinutes": minutes})


def _rem_toggle(update, uid):
    update({"enabled": bool(st.session_state[f"rem_enabled_{uid}"])})


def _rem_hours(update, uid):
    update(
        {
            "from": int(st.session_state[f"rem_from_{uid}"]),
            "to": int(st.session_state[f"rem_to_{uid}"]),
        }
    )


def _set_glass(user, uid):
    save_profile(user, glass=int(st.session_state[f"glass_{uid}"]))


def _sound_setting():
    st.session_state["sound_on"] = bool(st.session_state["sound_setting"])


def clear_all(user):
    uid = user["id"]
    for base in (PROFILE_KEY, HISTORY_KEY, REMINDERS_KEY, DONE_KEY):
        local_storage.remove_item(f"{base}_{uid}")
    users = local_storage.get_item(USERS_KEY) or {}
    users.pop(uid, None)
    local_storage.set_item(USERS_KEY, users)
    st.session_state["_reminders_for"] = None
    st.session_state.pop("welcome_name", None)
    logout()


def ProfilePage(user):
    uid = user["id"]
    reminders, update = use_reminders()
    profile = get_profile(user)
    history = get_history(user)
    goal = get_goal(user)
    glass = get_glass(user)
    today = date.today().isoformat()
    today_ml = day_total(history, today)
    pct = min(int(today_ml / goal * 100), 100) if goal else 0
    xp = calc_xp(history)
    level, title, to_next = level_info(xp)
    next_text = f"{to_next} XP to next level" if to_next else "Max level reached"
    total_ml = sum(day_total(history, d) for d in history)
    days_logged = sum(1 for d in history if day_total(history, d) > 0)

    PageHead("👤", "Profile", "Your hydration, your rules")

    # hero
    st.markdown(
        _html(
            f"""
<div class="wb-hero">{mascot_svg(mode_for(pct), 70, 88)}
<div><b>Stay hydrated, {escape(user['name'])}! 💧</b>
<div class="lv">Level {level} · {title} · {next_text}</div>
<div class="sm">{today_ml} ml of {goal} ml today — {pct}%</div></div></div>
"""
        ),
        unsafe_allow_html=True,
    )

    # stat tiles
    st.markdown(
        _html(
            f"""
<div class="wb-grid2">
<div class="wb-stat"><div class="ic">🔥</div><b>{calc_streak(history, goal)}d</b><small>STREAK</small></div>
<div class="wb-stat"><div class="ic">⭐</div><b>{calc_stars(history, goal)}</b><small>STARS</small></div>
<div class="wb-stat"><div class="ic">💧</div><b>{today_ml} ml</b><small>TODAY</small></div>
<div class="wb-stat"><div class="ic">📈</div><b>{total_ml / 1000:.1f} L</b><small>ALL-TIME SIPS</small><i>{days_logged} days logged</i></div>
</div>
"""
        ),
        unsafe_allow_html=True,
    )

    # name
    with st.container(border=True):
        st.markdown('<div class="wb-ph"><span class="i">👤</span> Your name</div>', unsafe_allow_html=True)
        st.markdown('<div class="wb-note">This is the name friends see in the leaderboard league.</div>', unsafe_allow_html=True)
        st.text_input(
            "Name",
            value=user["name"],
            key=f"profile_name_{uid}",
            label_visibility="collapsed",
            on_change=_rename,
            args=(user,),
        )
        st.caption("Press Enter to save.")

    # last 7 days
    cols = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        total = day_total(history, d.isoformat())
        h = max(4, int(min(total / goal, 1.0) * 84)) if goal else 4
        cols.append(
            f'<div class="wb-col"><div class="wb-colbar" style="height:{h}px;'
            f'{"opacity:.25;" if total == 0 else ""}"></div><small>{d.strftime("%a")[0]}</small></div>'
        )
    st.markdown(
        _html(
            f"""
<div class="wb-panel"><div class="wb-ph"><span class="i">📊</span> Last 7 days</div>
<div class="wb-week">{"".join(cols)}</div></div>
"""
        ),
        unsafe_allow_html=True,
    )

    # age group + goal
    with st.container(border=True):
        st.markdown('<div class="wb-ph"><span class="i">ℹ️</span> Your age group</div>', unsafe_allow_html=True)
        AgeGrid(profile.get("age_group"), _pick_profile_group, (user,), "profile")
        is_auto = not profile.get("goal")
        st.markdown(
            _html(
                f"""
<div class="wb-goalrow"><div class="ic">🎯</div>
<div><small>DAILY GOAL</small><b>{goal} ml</b><em>({"auto" if is_auto else "custom"})</em></div></div>
"""
            ),
            unsafe_allow_html=True,
        )
        new_goal = st.number_input("CUSTOM DAILY GOAL (ML)", min_value=500, max_value=6000, step=100, value=int(goal))
        g1, g2 = st.columns(2)
        with g1:
            st.button("Save goal", type="primary", use_container_width=True, on_click=_save_goal, args=(user, int(new_goal)), key="goal_save")
        with g2:
            st.button("Use auto", use_container_width=True, on_click=_save_goal, args=(user, None), key="goal_auto")

        std = auto_goal(user)
        top = max(std, goal)
        st.markdown(
            _html(
                f"""
<div class="wb-ph" style="margin-top:12px"><span class="i">📊</span> Standard vs your goal</div>
<div class="wb-bar"><div class="t"><span>Standard target</span><b>{std} ml</b></div>
<div class="wb-track"><div class="wb-fill" style="width:{int(std / top * 100)}%"></div></div></div>
<div class="wb-bar"><div class="t"><span>Your goal ({"auto" if is_auto else "custom"})</span><b>{goal} ml</b></div>
<div class="wb-track"><div class="wb-fill" style="width:{int(goal / top * 100)}%"></div></div></div>
<div class="wb-note" style="margin-top:8px">{"✓ Using the age-based standard - set a custom goal to personalise." if is_auto else "✓ Using your custom goal."}</div>
"""
            ),
            unsafe_allow_html=True,
        )

    # reminders
    with st.container(border=True):
        st.markdown('<div class="wb-ph"><span class="i">🔔</span> Reminders</div>', unsafe_allow_html=True)
        toggle = getattr(st, "toggle", st.checkbox)
        toggle(
            "Hydration reminders",
            value=bool(reminders.get("enabled")),
            key=f"rem_enabled_{uid}",
            on_change=_rem_toggle,
            args=(update, uid),
        )
        st.caption("Nudges in-app while WaterBuddy is open.")
        st.markdown('<div class="wb-note" style="margin:6px 0 4px">REMIND ME EVERY</div>', unsafe_allow_html=True)
        with keyed_container("chips_interval"):
            cols = st.columns(len(INTERVALS))
            for col, m in zip(cols, INTERVALS):
                with col:
                    st.button(
                        f"{m}m",
                        key=f"chip_{m}",
                        type="primary" if reminders.get("intervalMinutes") == m else "secondary",
                        use_container_width=True,
                        on_click=_set_interval,
                        args=(update, m),
                    )
        h1, h2 = st.columns(2)
        with h1:
            st.number_input(
                "ACTIVE FROM (HOUR)", min_value=0, max_value=23, step=1,
                value=int(reminders.get("from", 8)), key=f"rem_from_{uid}",
                on_change=_rem_hours, args=(update, uid),
            )
        with h2:
            st.number_input(
                "ACTIVE UNTIL (HOUR)", min_value=1, max_value=24, step=1,
                value=int(reminders.get("to", 22)), key=f"rem_to_{uid}",
                on_change=_rem_hours, args=(update, uid),
            )
        if st.button("Preview reminder", use_container_width=True, key="rem_preview"):
            line = f"Time to drink some water, {user['name']}!"
            sounds.blip()
            speak(line)
            st.toast(line, icon="💧")
        st.caption(
            f"Nudges you between {reminders.get('from', 8)}:00 and {reminders.get('to', 22)}:00 "
            "while the app is open."
        )

    # today's sips
    sips = history.get(today, [])
    if sips:
        items = "".join(
            f'<div class="wb-row"><div class="ic">💧</div><div><b>{s["ml"]} ml</b></div>'
            f'<div class="end">{s["t"]}</div></div>'
            for s in reversed(sips)
        )
    else:
        items = (
            '<div class="wb-empty"><div style="font-size:30px">💧</div>'
            "<b>No sips logged yet today.</b><span>Head to Home to begin.</span></div>"
        )
    st.markdown(
        _html(
            f"""
<div class="wb-panel"><div class="wb-ph"><span class="i">🕒</span> Today's sips</div>{items}</div>
"""
        ),
        unsafe_allow_html=True,
    )
    if sips and st.button("↩️ Undo last sip", use_container_width=True, key="undo_sip"):
        undo_sip(user)
        st.rerun()

    # settings
    with st.container(border=True):
        st.markdown('<div class="wb-ph"><span class="i">⚙️</span> Settings</div>', unsafe_allow_html=True)
        toggle = getattr(st, "toggle", st.checkbox)
        toggle(
            "Sound effects",
            value=st.session_state.get("sound_on", True),
            key="sound_setting",
            on_change=_sound_setting,
        )
        st.select_slider(
            "GLASS SIZE (ML)",
            options=[100, 150, 200, 250, 300, 350, 500],
            value=glass if glass in [100, 150, 200, 250, 300, 350, 500] else 250,
            key=f"glass_{uid}",
            on_change=_set_glass,
            args=(user, uid),
        )
        if st.button("↺  Reset today's intake", use_container_width=True, key="reset_today"):
            reset_today(user)
            st.toast("Today's intake reset", icon="↺")
            st.rerun()
        with keyed_container("dangerbtn"):
            if st.button("🗑  Clear all data & restart", use_container_width=True, key="clear_all"):
                clear_all(user)


# One-time prompt per user (new and existing): pick how often WaterBuddy should remind you.
def ReminderSetup():
    _, update = use_reminders()
    user, is_loading_auth = use_auth()

    # useState equivalents
    st.session_state.setdefault("askedFor", None)
    st.session_state.setdefault("open", False)
    st.session_state.setdefault("minutes", 30)

    # Play sound + speech + toast after "Set reminders" was clicked
    line = st.session_state.pop("_pending_line", None)
    if line:
        sounds.blip()
        speak(line)
        st.toast(f"**Reminders on**  \n{line}", icon="✅")

    # Ask once per account, so existing users get the prompt too.
    if not is_loading_auth and user and user.get("id"):
        key = f"{DONE_KEY}_{user['id']}"
        if st.session_state["askedFor"] != key:
            st.session_state["askedFor"] = key
            if not local_storage.get_item(key):
                st.session_state["open"] = True

    if not st.session_state["open"]:
        return None

    def mark_done():
        local_storage.set_item(f"{DONE_KEY}_{user['id']}", "1")

    def confirm():
        minutes = st.session_state["minutes"]
        update({"enabled": True, "intervalMinutes": minutes})
        mark_done()
        st.session_state["open"] = False
        st.session_state.pop(f"rem_enabled_{user['id']}", None)  # keep the Profile toggle in sync
        st.session_state["_pending_line"] = (
            f"Reminder set for every {minutes} minutes. "
            "You can change it anytime in the Profile tab."
        )

    def later():
        mark_done()
        st.session_state["open"] = False

    def set_minutes(m):
        st.session_state["minutes"] = m

    @_dialog("How often should I remind you?")
    def modal():
        # BellRing icon
        st.markdown(
            "<div style='text-align:center;font-size:2.5rem;'>🔔</div>",
            unsafe_allow_html=True,
        )
        # Description
        st.caption("A gentle spoken nudge to drink water while the app is open.")

        # Interval buttons (grid of 5)
        with keyed_container("chips_dialog"):
            cols = st.columns(len(INTERVALS))
            for col, m in zip(cols, INTERVALS):
                with col:
                    st.button(
                        f"{m}m",
                        key=f"interval_{m}",
                        type="primary" if st.session_state["minutes"] == m else "secondary",
                        use_container_width=True,
                        on_click=set_minutes,
                        args=(m,),
                    )

        # Set reminders
        if st.button("Set reminders", type="primary", use_container_width=True):
            confirm()
            st.rerun()

        # Decide later
        if st.button("Decide later", use_container_width=True):
            later()
            st.rerun()

    # With a real dialog, closing it with the X must not bring it back on the next rerun
    if _HAS_DIALOG:
        st.session_state["open"] = False
    modal()


# Speaks a nudge every N minutes while the page is open (inside the active hours)
def ReminderTimer(user):
    r = st.session_state.get("reminders", {})
    if not r.get("enabled") or not st.session_state.get("sound_on", True):
        return
    line = json.dumps(f"Time to drink some water, {user['name']}!")
    components.html(
        f"""
        <script>
        (function () {{
          var every = {int(r['intervalMinutes'])} * 60 * 1000;
          var from = {int(r['from'])}, to = {int(r['to'])};
          var line = {line};
          setInterval(function () {{
            var h = new Date().getHours();
            if (h >= from && h < to) {{
              try {{
                var u = new SpeechSynthesisUtterance(line);
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(u);
              }} catch (e) {{}}
            }}
          }}, every);
        }})();
        </script>
        """,
        height=0,
    )


# ---------- bottom navigation ----------
def set_tab(name):
    st.session_state["tab"] = name


def BottomNav():
    with keyed_container("bottomnav"):
        cols = st.columns(len(PAGES))
        for col, (name, icon) in zip(cols, PAGES):
            with col:
                st.button(
                    f"{icon}  \n{name}",
                    key=f"nav_{name}",
                    type="primary" if st.session_state["tab"] == name else "secondary",
                    use_container_width=True,
                    on_click=set_tab,
                    args=(name,),
                )


# ---------- app flow: welcome -> survey -> WaterBuddy ----------
inject_css()
st.session_state.setdefault("tab", "Home")
st.session_state.setdefault("sound_on", True)
timer_slot = st.container()  # created first so the timer keeps the same position on every rerun

user, is_loading_auth = use_auth()

if not user:
    WelcomePage()
    st.stop()

use_reminders()

if get_age_group(user) is None:
    SurveyPage(user)
    st.stop()

with timer_slot:
    ReminderTimer(user)

tab = st.session_state["tab"]
if tab == "Home":
    Header(user)
    HomePage(user)
elif tab == "Tips":
    TipsPage()
elif tab == "Board":
    BoardPage(user)
else:
    ProfilePage(user)

ReminderSetup()
BottomNav()