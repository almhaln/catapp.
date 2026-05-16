"""
Cat Health Tracker — Haku · Kuro · Sonic
Data-driven analysis only. No AI calls.

PERSISTENCE FIX:
  On Streamlit Cloud, the working directory resets on every server restart/redeploy,
  wiping all JSON files. This version saves to a fixed absolute path that persists,
  and also offers one-click backup download + restore so data is never truly lost.
  The app also auto-saves a backup JSON bundle that you can download and re-import.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import json
import os
import io
import calendar
from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# ── ReportLab ──
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ── Auth ──
try:
    from auth_module import (check_authentication, login_page, logout,
                             encrypt_data, decrypt_data)
    AUTH_ENABLED = True
except ImportError:
    AUTH_ENABLED = False

# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENT STORAGE PATH
# ══════════════════════════════════════════════════════════════════════════════
# On Streamlit Cloud the app directory resets on restarts.
# We use /tmp which survives across reruns within the same server session,
# AND we offer a full backup bundle download + re-import so data is never lost
# across server restarts/redeploys.
# For production, replace DATA_DIR with a mounted volume or external DB path.
DATA_DIR = os.environ.get("CAT_DATA_DIR", os.path.join(os.path.expanduser("~"), ".cattracker_data"))
os.makedirs(DATA_DIR, exist_ok=True)

def _data_path(fname: str) -> str:
    return os.path.join(DATA_DIR, fname)


# ══════════════════════════════════════════════════════════════════════════════
# VET SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════
def _add_months(d: date, months: int) -> date:
    m    = d.month - 1 + months
    year = d.year + m // 12
    mon  = m % 12 + 1
    day  = min(d.day, calendar.monthrange(year, mon)[1])
    return date(year, mon, day)

_LAST_DEWORMING = date(2026, 4, 26)
_LAST_CHECKUP   = date(2026, 4, 26)
_LAST_VACCINES  = date(2025, 12, 3)
_LAST_VET       = date(2026, 4, 26)

DEFAULT_VET_SCHEDULE = {
    'Haku':  {'next_checkup': str(_add_months(_LAST_CHECKUP, 12)),
              'next_vaccines': str(_add_months(_LAST_VACCINES, 12)),
              'next_deworming': str(_add_months(_LAST_DEWORMING, 3)),
              'next_vet_visit': str(_add_months(_LAST_VET, 4))},
    'Kuro':  {'next_checkup': str(_add_months(_LAST_CHECKUP, 12)),
              'next_vaccines': str(_add_months(_LAST_VACCINES, 12)),
              'next_deworming': str(_add_months(_LAST_DEWORMING, 4)),
              'next_vet_visit': str(_add_months(_LAST_VET, 4))},
    'Sonic': {'next_checkup': str(_add_months(_LAST_CHECKUP, 12)),
              'next_vaccines': str(_add_months(_LAST_VACCINES, 12)),
              'next_deworming': str(_add_months(_LAST_DEWORMING, 3)),
              'next_vet_visit': str(_add_months(_LAST_VET, 4))},
}

# ══════════════════════════════════════════════════════════════════════════════
# DEFAULT FOOD LIBRARY  — your cats' actual foods pre-loaded
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_FOOD_LIBRARY = [
    {"name": "Pro Plan Adult Wet", "type": "Wet",
     "protein_pct": 11.0, "fat_pct": 4.0, "fibre_pct": 1.0,
     "moisture_pct": 78.0, "phosphorus_pct": 0.20, "sodium_pct": 0.15,
     "taurine": True, "calories_per_100g": 85,
     "notes": "Main wet food. High moisture = excellent kidney and urinary protection. Low phosphorus ideal for kidney watch."},
    {"name": "Pro Plan Adult Dry", "type": "Dry",
     "protein_pct": 42.0, "fat_pct": 16.0, "fibre_pct": 3.0,
     "moisture_pct": 12.0, "phosphorus_pct": 1.00, "sodium_pct": 0.49,
     "taurine": True, "calories_per_100g": 375,
     "notes": "High protein, good taurine. Phosphorus at 1.0% — monitor for kidney cats. Supplement with wet food."},
    {"name": "Unseasoned Boiled Chicken", "type": "Wet",
     "protein_pct": 31.0, "fat_pct": 3.5, "fibre_pct": 0.0,
     "moisture_pct": 65.0, "phosphorus_pct": 0.22, "sodium_pct": 0.07,
     "taurine": False, "calories_per_100g": 165,
     "notes": "Excellent lean protein supplement. Low sodium, low phosphorus. No significant taurine — NOT a complete food. Great appetite booster or supplement only."},
    {"name": "Freeze-Dried Treats", "type": "Treat",
     "protein_pct": 60.0, "fat_pct": 8.0, "fibre_pct": 1.0,
     "moisture_pct": 5.0, "phosphorus_pct": 0.60, "sodium_pct": 0.30,
     "taurine": False, "calories_per_100g": 350,
     "notes": "High protein but very low moisture. Fine as occasional treats — keep to <10% of daily calories. No added taurine."},
    {"name": "KitKat Topper", "type": "Wet",
     "protein_pct": 9.0, "fat_pct": 3.0, "fibre_pct": 0.5,
     "moisture_pct": 80.0, "phosphorus_pct": 0.18, "sodium_pct": 0.12,
     "taurine": True, "calories_per_100g": 70,
     "notes": "Cat food topper/complement. High moisture (80%) — good for hydration and palatability. Low phosphorus — good for kidney health. Use to encourage eating or add variety on top of main food."},
]

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH REFERENCE RANGES
# ══════════════════════════════════════════════════════════════════════════════
HEALTH_RANGES = {
    'water_drinks': {
        'label': 'Daily Water Drinks', 'unit': 'times/day',
        'ideal': (3, 8), 'ok': (1, 10),
        'low_msg': ("**Too low.** Cats have a naturally low thirst drive — they evolved to get moisture from prey. "
                    "Chronic low intake is the #1 cause of kidney disease and urinary crystals. "
                    "**Normal:** 3-8 drinks/day. **Worried when:** consistently below 1-2/day. "
                    "**What to do:** Water fountain, more wet food, extra water bowls away from food."),
        'high_msg': ("**Increased thirst.** Higher than usual water intake can signal early kidney disease, "
                     "diabetes, or hyperthyroidism — especially if this is a new change. "
                     "**Normal:** 3-8 drinks/day. **Worried when:** sudden large increase. "
                     "**What to do:** Note if this is a new pattern. Vet blood/urine test if persists."),
        'ideal_msg': ("**Excellent hydration.** This directly protects the kidneys and urinary tract, "
                      "prevents crystal formation, and keeps organs functioning well. "
                      "**Normal range:** 3-8 drinks/day. Keep it up."),
        'ok_msg': ("**Acceptable but could be better.** "
                   "**Normal:** 3-8 drinks/day. Aim higher with a water fountain and wet food."),
    },
    'food_eats': {
        'label': 'Daily Meals', 'unit': 'meals/day',
        'ideal': (3, 5), 'ok': (2, 6),
        'low_msg': ("**Low food intake — needs attention.** Not eating is one of the most important warning signs. "
                    "Within 48-72 hrs cats can develop hepatic lipidosis (fatty liver disease) — life-threatening. "
                    "**Normal:** 3-5 meals/day. **Worried when:** below 1/day or not eating at all. "
                    "**What to do:** If not eating 24+ hrs: contact vet today."),
        'high_msg': ("**High meal count.** Multiple small meals are actually ideal — only a concern if total calories are too high. "
                     "**Normal:** 3-5 meals/day. Monitor weight if eating 6+/day."),
        'ideal_msg': ("**Great eating pattern.** 3-5 meals/day matches a cat's natural hunting rhythm, "
                      "keeps blood sugar stable, reduces hunger stress, prevents bile vomiting. "
                      "**Normal range:** 3-5 meals/day."),
        'ok_msg': ("**Acceptable.** 2 meals/day works but 12-hour gaps can cause morning bile vomiting. "
                   "**Normal:** 3-5/day. Try adding a small meal before bed."),
    },
    'litter_box_times': {
        'label': 'Litter Box Uses', 'unit': 'times/day',
        'ideal': (2, 4), 'ok': (1, 6),
        'low_msg': ("**Too low.** A cat who hasn't urinated in 24+ hrs needs urgent vet attention — possible blockage. "
                    "**Normal:** 2-4 times/day. **Worried when:** 0 trips in 24 hrs — this is an emergency. "
                    "**What to do:** Check if box is clean. Emergency vet if truly no urination."),
        'high_msg': ("**Frequent litter use.** Can signal UTI, crystals, stress (FLUTD), or early kidney disease. "
                     "**Normal:** 2-4 times/day. **Worried when:** straining with no urine = emergency. "
                     "**What to do:** Watch for blood, straining, crying. Vet check within a few days."),
        'ideal_msg': ("**Normal litter usage.** 2-4 trips/day indicates healthy kidney function and good hydration. "
                      "This is an important baseline — note any significant changes. **Normal range:** 2-4/day."),
        'ok_msg': ("**Borderline.** Within acceptable range. **Normal:** 2-4/day. "
                   "Monitor for any changes in frequency, amount, or appearance."),
    },
}

DIET_ANALYSIS_RULES = {
    'protein': {
        'label': 'Protein',
        'ideal_wet': (8, 15), 'ideal_dry': (35, 50), 'ideal_treat': (40, 80),
        'why': ("Cats are obligate carnivores — protein is their primary energy source AND essential for "
                "organs, immunity, muscle, and enzymes. Unlike dogs, cats CANNOT reduce protein metabolism "
                "when intake drops — they break down their own muscle tissue instead."),
        'deficiency': "Muscle wasting, poor immunity, organ damage, liver disease",
        'excess': "Generally safe. High protein + low water = higher urinary load — always pair with good hydration.",
    },
    'moisture': {
        'label': 'Moisture',
        'ideal_wet': (70, 85), 'ideal_dry': (8, 14), 'ideal_treat': (0, 15),
        'why': ("Cats evolved in deserts with very low thirst drive — biologically designed to get 70-80% "
                "of water from food (prey is ~70% water). Dry food at 10-12% moisture = chronic mild dehydration. "
                "This is the #1 driver of kidney disease and urinary problems in domestic cats."),
        'deficiency': "Chronic dehydration → kidney disease → urinary crystals and blockages",
        'excess': "Cannot have too much moisture — more is always better for kidneys and urinary tract",
    },
    'phosphorus': {
        'label': 'Phosphorus',
        'ideal_wet': (0.1, 0.4), 'ideal_dry': (0.5, 0.9), 'ideal_treat': (0.0, 1.0),
        'why': ("Phosphorus is essential for bones but excess must be filtered by kidneys. "
                "High-phosphorus diets damage kidneys over time even in healthy cats. "
                "For kidney-monitored cats, this is the MOST important dietary number. "
                "Wet food has naturally much lower phosphorus than dry food."),
        'deficiency': "Bone disease (very rare with commercial food)",
        'excess': "KIDNEY DAMAGE — accelerates CKD. Kidney cats: aim <0.5% wet, <0.8% dry",
    },
    'fat': {
        'label': 'Fat',
        'ideal_wet': (3, 8), 'ideal_dry': (10, 20), 'ideal_treat': (5, 20),
        'why': ("Fat is a concentrated energy source and carries fat-soluble vitamins (A, D, E, K). "
                "Also provides essential fatty acids for skin, coat, and brain function. "
                "Cats handle fat well — it's a natural part of their carnivore diet."),
        'deficiency': "Poor coat, dry skin, vitamin deficiencies, low energy",
        'excess': "Weight gain, pancreatitis in prone cats",
    },
}

TAURINE_WHY = ("Cats CANNOT synthesize taurine — must come entirely from diet. Found only in animal tissue. "
               "Critical for: heart muscle (deficiency causes DCM — dilated cardiomyopathy), vision (retinal "
               "degeneration), reproduction, and immune function. Complete commercial foods always supplement it. "
               "Home-cooked food or treats alone are NOT adequate taurine sources.")


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def init_session_state():
    if 'cats' not in st.session_state:
        st.session_state.cats = ['Haku', 'Kuro', 'Sonic']

    if 'health_data' not in st.session_state:
        st.session_state.health_data = {}

    if 'tasks' not in st.session_state:
        st.session_state.tasks = {
            'daily':    ['Clean food bowl', 'Add water', 'Clean litter box',
                         'Let them out my room', 'Pray for them', 'Play with them'],
            'weekly':   ['Clean water fountain', 'Clean room', 'Clean air purifier'],
            'monthly':  ['Deep clean litter box', 'Buy food', 'Buy wet food', 'Buy litter',
                         'Buy treats', 'Buy toys', 'Clean cat tree', 'Clean bedding',
                         'Clean air purifier filter'],
            'quarterly': []
        }
    else:
        daily = st.session_state.tasks.get('daily', [])
        if 'Play with them' not in daily:
            daily.append('Play with them')
            st.session_state.tasks['daily'] = daily

    if 'task_logs' not in st.session_state:
        st.session_state.task_logs = {}

    if 'last_entries' not in st.session_state:
        st.session_state.last_entries = {cat: None for cat in st.session_state.cats}

    if 'last_reminder' not in st.session_state:
        st.session_state.last_reminder = None

    if 'cat_profiles' not in st.session_state:
        st.session_state.cat_profiles = {
            cat: {'age': '', 'breed': '', 'weight': '', 'vet_visits': [],
                  'notes': '', 'birthdate': '', **DEFAULT_VET_SCHEDULE[cat]}
            for cat in ['Haku', 'Kuro', 'Sonic']
        }
    else:
        for cat in st.session_state.cats:
            p = st.session_state.cat_profiles.get(cat, {})
            for key, val in DEFAULT_VET_SCHEDULE.get(cat, {}).items():
                if not p.get(key): p[key] = val
            p.setdefault('birthdate', '')
            st.session_state.cat_profiles[cat] = p

    if 'food_library' not in st.session_state:
        st.session_state.food_library = [dict(f) for f in DEFAULT_FOOD_LIBRARY]
    else:
        # Ensure KitKat topper is in the library
        existing = {f['name'] for f in st.session_state.food_library}
        for default in DEFAULT_FOOD_LIBRARY:
            if default['name'] not in existing:
                st.session_state.food_library.append(dict(default))

    if 'diet_settings' not in st.session_state:
        st.session_state.diet_settings = {
            cat: {'meals_per_day': 3, 'notes': '',
                  'active_foods': ['Pro Plan Adult Wet', 'KitKat Topper',
                                   'Unseasoned Boiled Chicken', 'Freeze-Dried Treats']}
            for cat in ['Haku', 'Kuro', 'Sonic']
        }

    # New features
    if 'breathing_logs' not in st.session_state:
        st.session_state.breathing_logs = {cat: [] for cat in ['Haku', 'Kuro', 'Sonic']}

    if 'symptom_patterns' not in st.session_state:
        st.session_state.symptom_patterns = {}

    if 'cat_journal' not in st.session_state:
        st.session_state.cat_journal = {cat: [] for cat in ['Haku', 'Kuro', 'Sonic']}

    if 'editing_health_entry' not in st.session_state:
        st.session_state.editing_health_entry = False
    if 'edit_entry_data' not in st.session_state:
        st.session_state.edit_entry_data = {}
    if 'edit_entry_cat' not in st.session_state:
        st.session_state.edit_entry_cat = None
    if 'health_form_cat' not in st.session_state:
        st.session_state.health_form_cat = None
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False


# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE  — THE FIX
# ══════════════════════════════════════════════════════════════════════════════
def _get_full_bundle() -> dict:
    """All app data as a single dict for backup/restore."""
    return {
        'health_data':     st.session_state.health_data,
        'task_logs':       st.session_state.task_logs,
        'cat_profiles':    st.session_state.cat_profiles,
        'diet_settings':   st.session_state.diet_settings,
        'food_library':    st.session_state.food_library,
        'breathing_logs':  st.session_state.breathing_logs,
        'cat_journal':     st.session_state.cat_journal,
        'backup_version':  2,
        'backup_date':     str(date.today()),
    }


def save_data():
    """
    Save to DATA_DIR (persists across reruns within the same server).
    Also writes a single bundle file used for backup download.
    """
    try:
        files = {
            'health_data.json':    st.session_state.health_data,
            'task_logs.json':      st.session_state.task_logs,
            'cat_profiles.json':   st.session_state.cat_profiles,
            'diet_settings.json':  st.session_state.diet_settings,
            'food_library.json':   st.session_state.food_library,
            'breathing_logs.json': st.session_state.breathing_logs,
            'cat_journal.json':    st.session_state.cat_journal,
        }
        for fname, data in files.items():
            raw = json.dumps(data, default=str)
            if AUTH_ENABLED:
                try: raw = encrypt_data(raw)
                except: pass
            with open(_data_path(fname), 'w') as f:
                f.write(raw)
        # Always write plain bundle for easy backup download (no encryption on bundle)
        with open(_data_path('backup_bundle.json'), 'w') as f:
            json.dump(_get_full_bundle(), f, default=str, indent=2)
    except Exception as e:
        st.error(f"Save error: {e}")


def _read_file(fname: str):
    path = _data_path(fname)
    if not os.path.exists(path): return None
    with open(path, 'r') as f: raw = f.read()
    if AUTH_ENABLED and raw:
        try: raw = decrypt_data(raw)
        except: pass
    return raw or None


def load_data():
    """
    Loads from DATA_DIR. Runs only once per server session (guarded by data_loaded).
    On a cold server restart, DATA_DIR may be empty — in that case session_state
    keeps the in-memory defaults, and user can restore from a backup bundle.
    """
    if st.session_state.data_loaded:
        return
    try:
        s = _read_file('health_data.json')
        if s: st.session_state.health_data = json.loads(s)

        s = _read_file('task_logs.json')
        if s: st.session_state.task_logs = json.loads(s)

        s = _read_file('cat_profiles.json')
        if s:
            loaded = json.loads(s)
            for cat, profile in loaded.items():
                if isinstance(profile.get('vet_visits'), list):
                    if profile['vet_visits'] and isinstance(profile['vet_visits'][0], str):
                        profile['vet_visits'] = []
                for key, val in DEFAULT_VET_SCHEDULE.get(cat, {}).items():
                    if not profile.get(key): profile[key] = val
                profile.setdefault('birthdate', '')
            st.session_state.cat_profiles = loaded

        s = _read_file('diet_settings.json')
        if s:
            ld = json.loads(s)
            for cat in st.session_state.cats:
                if cat in ld: st.session_state.diet_settings[cat].update(ld[cat])

        s = _read_file('food_library.json')
        if s:
            lib = json.loads(s)
            existing = {f['name'] for f in lib}
            for default in DEFAULT_FOOD_LIBRARY:
                if default['name'] not in existing:
                    lib.append(dict(default))
            st.session_state.food_library = lib

        s = _read_file('breathing_logs.json')
        if s:
            bl = json.loads(s)
            for cat in st.session_state.cats:
                st.session_state.breathing_logs.setdefault(cat, [])
                if cat in bl: st.session_state.breathing_logs[cat] = bl[cat]

        s = _read_file('cat_journal.json')
        if s:
            jl = json.loads(s)
            for cat in st.session_state.cats:
                st.session_state.cat_journal.setdefault(cat, [])
                if cat in jl: st.session_state.cat_journal[cat] = jl[cat]

        st.session_state.data_loaded = True
    except Exception as e:
        st.error(f"Load error: {e}")
        st.session_state.data_loaded = True


def restore_from_bundle(bundle: dict):
    """Restore all session state from a backup bundle dict."""
    if bundle.get('health_data'):
        st.session_state.health_data = bundle['health_data']
    if bundle.get('task_logs'):
        st.session_state.task_logs = bundle['task_logs']
    if bundle.get('cat_profiles'):
        loaded = bundle['cat_profiles']
        for cat, profile in loaded.items():
            for key, val in DEFAULT_VET_SCHEDULE.get(cat, {}).items():
                if not profile.get(key): profile[key] = val
            profile.setdefault('birthdate', '')
        st.session_state.cat_profiles = loaded
    if bundle.get('diet_settings'):
        for cat in st.session_state.cats:
            if cat in bundle['diet_settings']:
                st.session_state.diet_settings[cat].update(bundle['diet_settings'][cat])
    if bundle.get('food_library'):
        lib = bundle['food_library']
        existing = {f['name'] for f in lib}
        for default in DEFAULT_FOOD_LIBRARY:
            if default['name'] not in existing:
                lib.append(dict(default))
        st.session_state.food_library = lib
    if bundle.get('breathing_logs'):
        st.session_state.breathing_logs.update(bundle['breathing_logs'])
    if bundle.get('cat_journal'):
        st.session_state.cat_journal.update(bundle['cat_journal'])
    save_data()


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH ENTRIES
# ══════════════════════════════════════════════════════════════════════════════
def add_health_entry(cat_name: str, entry_data: Dict):
    st.session_state.health_data.setdefault(cat_name, {})
    ts = datetime.now().isoformat()
    st.session_state.health_data[cat_name].setdefault(ts, [])
    entry_data['timestamp'] = ts
    st.session_state.health_data[cat_name][ts].append(entry_data)
    st.session_state.last_entries[cat_name] = datetime.now()
    save_data()


def get_health_entries(cat_name: str, start_date: date, end_date: date) -> List[Dict]:
    out = []
    for ts, entries in st.session_state.health_data.get(cat_name, {}).items():
        try:
            ed = datetime.fromisoformat(ts).date()
            if start_date <= ed <= end_date:
                for e in entries:
                    ec = dict(e); ec['timestamp'] = ts; out.append(ec)
        except: continue
    return out


def update_health_entry(cat_name, ts, idx, data):
    arr = st.session_state.health_data.get(cat_name, {}).get(ts, [])
    if idx < len(arr): arr[idx].update(data); save_data()


def delete_health_entry(cat_name, ts, idx):
    arr = st.session_state.health_data.get(cat_name, {}).get(ts, [])
    if idx < len(arr):
        arr.pop(idx)
        if not arr: del st.session_state.health_data[cat_name][ts]
        save_data()


# ══════════════════════════════════════════════════════════════════════════════
# TASKS
# ══════════════════════════════════════════════════════════════════════════════
def add_task_completion(task_name, cat_name=None, notes=""):
    today = str(date.today())
    st.session_state.task_logs.setdefault(today, [])
    st.session_state.task_logs[today].append({
        'task': task_name, 'cat': cat_name,
        'completed_at': datetime.now().isoformat(), 'notes': notes
    })
    save_data()


def get_task_completions(start_date, end_date):
    out = {}
    for ds, logs in st.session_state.task_logs.items():
        try:
            if start_date <= date.fromisoformat(ds) <= end_date:
                out[ds] = logs
        except: continue
    return out


# ══════════════════════════════════════════════════════════════════════════════
# AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════
def get_daily_aggregated(cat_name, start_date, end_date):
    daily = {}
    for entry in get_health_entries(cat_name, start_date, end_date):
        try:
            ed = datetime.fromisoformat(entry['timestamp']).date()
        except: continue
        if ed not in daily:
            daily[ed] = {
                'water_drinks': 0, 'food_eats': 0, 'litter_box_times': 0,
                'moods': [], 'medications': [], 'grooming_tasks': set(),
                'litter_quality_issues': [], 'notes': [],
                'entry_count': 0, 'pooped': False, 'food_log': []
            }
        d = daily[ed]
        d['water_drinks']     += entry.get('water_drinks', 0)
        d['food_eats']        += entry.get('food_eats', 0)
        d['litter_box_times'] += entry.get('litter_box_times', 0)
        d['entry_count']      += 1
        if entry.get('pooped'):     d['pooped'] = True
        if entry.get('mood'):       d['moods'].append(entry['mood'])
        if entry.get('food_eaten'): d['food_log'].append(entry['food_eaten'])
        if entry.get('medication_name'):
            d['medications'].append({
                'name':       entry['medication_name'],
                'type':       entry.get('medication_type', 'Oral'),
                'dosage':     entry.get('medication_dosage', ''),
                'frequency':  entry.get('medication_frequency', ''),
                'start_date': entry.get('medication_start_date', ''),
                'end_date':   entry.get('medication_end_date', '')
            })
        if entry.get('grooming_tasks'):
            for t, done in entry['grooming_tasks'].items():
                if done: d['grooming_tasks'].add(t)
        if entry.get('litter_quality'):
            for q in entry['litter_quality']:
                if q and q.strip(): d['litter_quality_issues'].append(q.strip())
        if entry.get('notes') and entry['notes'].strip():
            d['notes'].append(entry['notes'].strip())
    return daily


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
def _rate(value, rng):
    lo_i, hi_i = rng['ideal']
    lo_o, hi_o = rng['ok']
    if lo_i <= value <= hi_i: return 'ideal',   '🟢', rng['ideal_msg']
    if lo_o <= value <= hi_o: return 'ok',      '🟡', rng['ok_msg']
    if value < lo_o:          return 'low',     '🔴', rng['low_msg']
    return                           'high',    '🟠', rng['high_msg']


def analyze_cat_health(cat_name: str) -> Dict:
    today    = date.today()
    week_ago = today - timedelta(days=7)
    daily    = get_daily_aggregated(cat_name, week_ago, today)

    base = {'cat': cat_name,
            'profile':     st.session_state.cat_profiles.get(cat_name, {}),
            'vet_history': st.session_state.cat_profiles.get(cat_name, {}).get('vet_visits', []),
            'daily': daily}

    if not daily:
        return {**base, 'status': 'no_data', 'total_entries': 0, 'total_days': 0,
                'water_avg': 0, 'food_avg': 0, 'litter_avg': 0, 'poop_days': 0,
                'mood_trend': 'unknown', 'litter_issues': [],
                'metric_ratings': {}, 'concerns': [], 'positives': [],
                'mood_icon': '⬜', 'mood_msg': 'No data logged.',
                'poop_icon': '⬜', 'poop_msg': 'No data logged.'}

    n         = len(daily)
    total_e   = sum(d['entry_count'] for d in daily.values())
    w_avg     = sum(d['water_drinks']     for d in daily.values()) / n
    f_avg     = sum(d['food_eats']        for d in daily.values()) / n
    l_avg     = sum(d['litter_box_times'] for d in daily.values()) / n
    poop_days = sum(1 for d in daily.values() if d.get('pooped'))

    all_moods = [m for d in daily.values() for m in d['moods']]
    mood_trend = 'stable'
    if all_moods:
        poor = sum(1 for m in all_moods if m in ['Very Poor','Poor'])
        good = sum(1 for m in all_moods if m in ['Good','Excellent'])
        if poor > len(all_moods)/2:   mood_trend = 'declining'
        elif good > len(all_moods)/2: mood_trend = 'good'

    litter_issues = [
        (str(ed), iss) for ed, d in daily.items()
        for iss in d['litter_quality_issues']
        if any(kw in iss.lower() for kw in ['blood','diarrhea','diarrhoea','abnormal','mucus','black','red'])
    ]

    w_s, w_i, w_m = _rate(w_avg, HEALTH_RANGES['water_drinks'])
    f_s, f_i, f_m = _rate(f_avg, HEALTH_RANGES['food_eats'])
    l_s, l_i, l_m = _rate(l_avg, HEALTH_RANGES['litter_box_times'])

    mr = {
        'water':  {'avg': w_avg, 'status': w_s, 'icon': w_i, 'msg': w_m, 'ideal': '3-8/day', 'ok': '1-10/day'},
        'food':   {'avg': f_avg, 'status': f_s, 'icon': f_i, 'msg': f_m, 'ideal': '3-5/day', 'ok': '2-6/day'},
        'litter': {'avg': l_avg, 'status': l_s, 'icon': l_i, 'msg': l_m, 'ideal': '2-4/day', 'ok': '1-6/day'},
    }

    mood_info = {
        'good':     ('🟢', "Consistent good mood this week. Happy cats have lower cortisol, stronger immunity, and lower FLUTD risk."),
        'stable':   ('🟡', "Stable mood. Normal baseline — watch for any downward trend over multiple consecutive days."),
        'declining':('🔴', "Declining mood. In cats this is often the earliest sign of physical illness — before other symptoms appear. Check for subtle physical signs. Vet visit if it persists 2-3 days."),
        'unknown':  ('⬜', "No mood data logged. Add mood in health entries to track this important early indicator."),
    }
    mood_icon, mood_msg = mood_info.get(mood_trend, mood_info['unknown'])

    poop_pct  = poop_days / n if n > 0 else 0
    if poop_pct >= 0.8:
        poop_icon, poop_msg = '🟢', f"Regular bowel movements ({poop_days}/{n} days). Healthy digestion. Normal: at least 1/day."
    elif poop_pct >= 0.4:
        poop_icon, poop_msg = '🟡', f"Moderate poop days logged ({poop_days}/{n}). May be incomplete logging or mild irregularity — monitor."
    elif n >= 3:
        poop_icon, poop_msg = '🔴', (f"Few/no poop days ({poop_days}/{n}). Normal: every 24-36 hrs. "
                                      "Worried when: nothing for 48+ hrs. Increase wet food and water. Vet if truly constipated.")
    else:
        poop_icon, poop_msg = '⬜', "Not enough data yet."

    concerns  = [(k, mr[k]) for k in ['water','food','litter'] if mr[k]['status'] in ('low','high')]
    positives = [(k, mr[k]) for k in ['water','food','litter'] if mr[k]['status'] == 'ideal']

    # ── Pattern detection ──
    patterns = []
    # 3+ consecutive poor mood days
    sorted_dates = sorted(daily.keys())
    consecutive_poor = 0
    for dd in sorted_dates[-5:]:
        d = daily[dd]
        if d['moods'] and all(m in ['Very Poor','Poor'] for m in d['moods']):
            consecutive_poor += 1
        else:
            consecutive_poor = 0
    if consecutive_poor >= 3:
        patterns.append(f"⚠️ **{cat_name}** has had poor mood for {consecutive_poor} consecutive days — consider a vet check.")

    # Litter issues on consecutive days
    issue_days = sum(1 for d in daily.values() if d['litter_quality_issues'])
    if issue_days >= 2:
        patterns.append(f"⚠️ **{cat_name}** has had litter quality issues on {issue_days} days this week — vet visit recommended.")

    return {
        **base,
        'status':          'healthy' if not concerns else 'warning',
        'total_entries':   total_e,
        'total_days':      n,
        'water_avg':       w_avg,
        'food_avg':        f_avg,
        'litter_avg':      l_avg,
        'poop_days':       poop_days,
        'mood_trend':      mood_trend,
        'mood_icon':       mood_icon,
        'mood_msg':        mood_msg,
        'poop_icon':       poop_icon,
        'poop_msg':        poop_msg,
        'litter_issues':   litter_issues,
        'metric_ratings':  mr,
        'concerns':        concerns,
        'positives':       positives,
        'patterns':        patterns,
    }


def get_active_medications_today():
    today = date.today()
    active, seen = [], set()
    for cat in st.session_state.cats:
        for entry in get_health_entries(cat, today - timedelta(days=90), today):
            mn = entry.get('medication_name','').strip()
            ss = entry.get('medication_start_date','')
            es = entry.get('medication_end_date','')
            if not all([mn,ss,es]): continue
            try: ms, me = date.fromisoformat(ss), date.fromisoformat(es)
            except: continue
            key = f"{cat}_{mn}_{es}"
            if key in seen: continue
            seen.add(key)
            if ms <= today <= me:
                active.append({'cat': cat, 'name': mn,
                               'type':      entry.get('medication_type','Oral'),
                               'dosage':    entry.get('medication_dosage',''),
                               'frequency': entry.get('medication_frequency',''),
                               'end_date':  es, 'days_left': (me-today).days})
    return active


def get_vet_reminders():
    today = date.today()
    labels = {'next_checkup': 'Annual Checkup (Blood, Dental, Chest X-ray, Breathing)',
              'next_vaccines': 'Annual Vaccines',
              'next_deworming': 'Deworming',
              'next_vet_visit': 'Routine Vet Visit'}
    reminders = []
    for cat in st.session_state.cats:
        p = st.session_state.cat_profiles.get(cat, {})
        for key, label in labels.items():
            val = p.get(key,'')
            if val:
                try:
                    nd = date.fromisoformat(val)
                    reminders.append({'cat': cat, 'label': label, 'next_date': val,
                                      'days_away': (nd-today).days, 'overdue': nd < today})
                except:
                    reminders.append({'cat': cat, 'label': label, 'next_date': 'Invalid',
                                      'days_away': None, 'overdue': False})
            else:
                reminders.append({'cat': cat, 'label': label, 'next_date': 'Not set',
                                  'days_away': None, 'overdue': False})
    return reminders


# ══════════════════════════════════════════════════════════════════════════════
# DIET ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
def analyze_diet(cat_name: str) -> Dict:
    ds = st.session_state.diet_settings.get(cat_name, {})
    active_names = ds.get('active_foods', [])
    lib = {f['name']: f for f in st.session_state.food_library}
    active_foods = [lib[n] for n in active_names if n in lib]
    if not active_foods:
        return {'has_data': False}

    wet_foods  = [f for f in active_foods if f['type'] == 'Wet']
    dry_foods  = [f for f in active_foods if f['type'] == 'Dry']
    treats     = [f for f in active_foods if f['type'] == 'Treat']
    meals      = int(ds.get('meals_per_day', 3))

    complete_food     = any(f['taurine'] and f['type'] in ('Wet','Dry') for f in active_foods)
    has_taurine       = any(f['taurine'] for f in active_foods)
    wet_moisture_avg  = sum(f['moisture_pct'] for f in wet_foods)/len(wet_foods) if wet_foods else 0
    has_good_moisture = bool(wet_foods) and wet_moisture_avg >= 70
    high_phos_dry     = [f for f in dry_foods if f['phosphorus_pct'] > 0.9]
    safe_phos_wet     = [f for f in wet_foods if f['phosphorus_pct'] <= 0.4]

    weight_str = st.session_state.cat_profiles.get(cat_name,{}).get('weight','4')
    try:    weight_kg = float(weight_str) if weight_str else 4.0
    except: weight_kg = 4.0
    water_needed = weight_kg * 60

    positives, warnings, findings = [], [], []

    if complete_food:
        positives.append("✅ **Taurine covered** — complete commercial food ensures adequate taurine for heart and eye health.")
    elif has_taurine:
        warnings.append("⚠️ **Taurine source present but check dosage** — ensure taurine-containing food is a substantial portion.")
    else:
        warnings.append("🔴 **No taurine source!** Cats cannot make taurine. Without it: heart disease (DCM) and blindness. Add complete commercial food immediately.")

    if has_good_moisture:
        positives.append(f"✅ **Good moisture from wet food** ({wet_moisture_avg:.0f}%). Best kidney and urinary protection. Prey is ~70-75% water — this mimics it.")
    elif wet_foods:
        warnings.append(f"🟡 **Moisture lower than ideal** ({wet_moisture_avg:.0f}%). Aim for ≥70% in wet food.")
    else:
        warnings.append("🔴 **No wet food!** Cats on only dry food are chronically mildly dehydrated — the #1 cause of kidney disease.")

    for f in high_phos_dry:
        warnings.append(f"⚠️ **{f['name']}: phosphorus {f['phosphorus_pct']}%** — high for kidney-monitored cats (ideal <0.9%). Balance with low-phosphorus wet food.")
    if safe_phos_wet:
        positives.append(f"✅ **Low-phosphorus wet food** ({', '.join(f['name'] for f in safe_phos_wet)}) — kidney-safe. Excellent choice.")

    chicken_foods = [f for f in active_foods if 'chicken' in f['name'].lower()]
    if chicken_foods:
        findings.append("🍗 **Boiled chicken** — lean protein supplement. Does NOT contain significant taurine and is NOT complete. Good for appetite or as supplement only.")

    if treats:
        findings.append(f"🍬 **Treats ({', '.join(f['name'] for f in treats)})** — high protein but low moisture, no taurine. Keep to <10% of daily calories.")

    topper_foods = [f for f in active_foods if 'topper' in f['name'].lower() or 'kitkat' in f['name'].lower()]
    if topper_foods:
        findings.append(f"🍲 **Topper ({', '.join(f['name'] for f in topper_foods)})** — great for palatability and adding hydration. Use on top of main food to encourage eating. Contains taurine ✅")

    if meals >= 3:
        positives.append(f"✅ **{meals} meals/day** — ideal. Matches natural hunting rhythm, stable blood sugar, reduces vomiting.")
    elif meals == 2:
        findings.append("🟡 **2 meals/day** — acceptable. 12-hour gaps can cause morning bile vomiting. Try a small meal before bed.")
    else:
        warnings.append(f"🔴 **{meals} meal/day** — too infrequent. Causes hunger stress, increases vomiting risk.")

    return {
        'has_data': True, 'active_foods': active_foods,
        'wet_foods': wet_foods, 'dry_foods': dry_foods, 'treats': treats,
        'positives': positives, 'warnings': warnings, 'findings': findings,
        'has_good_moisture': has_good_moisture, 'water_needed': water_needed,
        'meals': meals, 'weight_kg': weight_kg,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MONTHLY CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
def monthly_task_calendar(year, month):
    monthly_tasks = st.session_state.tasks.get('monthly', [])
    if not monthly_tasks: return
    first = date(year, month, 1)
    last  = date(year, month, calendar.monthrange(year, month)[1])
    comps = get_task_completions(first, last)
    done_dates = {ds: [l['task'] for l in logs if l['task'] in monthly_tasks]
                  for ds, logs in comps.items()
                  if any(l['task'] in monthly_tasks for l in logs)}

    cols = st.columns(7)
    for i, n in enumerate(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']):
        cols[i].markdown(f"**{n}**")
    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0: cols[i].write(""); continue
            d = date(year, month, day); ds = str(d)
            label = (f"**{day}** ✅" if ds in done_dates
                     else f"**{day}** 📍" if d == date.today() else str(day))
            if day == 1: label = "🔔 " + label
            cols[i].markdown(label)

    done_set = set(t for tl in done_dates.values() for t in tl)
    st.markdown(f"**Completed:** {len(done_set)}/{len(monthly_tasks)}")
    if done_set:   st.success("Done: " + ", ".join(sorted(done_set)))
    rem = [t for t in monthly_tasks if t not in done_set]
    if rem: st.warning("Still needed: " + ", ".join(rem))


# ══════════════════════════════════════════════════════════════════════════════
# PDF REPORT
# ══════════════════════════════════════════════════════════════════════════════
def generate_pdf_report(cat_name=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    ts_ = ParagraphStyle('T', parent=styles['Title'],   fontSize=17, spaceAfter=4, textColor=colors.HexColor('#2c3e50'))
    hs_ = ParagraphStyle('H', parent=styles['Heading2'],fontSize=12, spaceAfter=3, textColor=colors.HexColor('#2980b9'))
    ss_ = ParagraphStyle('S', parent=styles['Heading3'],fontSize=10, spaceAfter=2, textColor=colors.HexColor('#555'))
    ns_ = ParagraphStyle('N', parent=styles['Normal'],  fontSize=9,  leading=13)
    cs_ = ParagraphStyle('C', parent=styles['Normal'],  fontSize=7,  textColor=colors.grey)

    def tbl(data, widths, hcol):
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),hcol),('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),
            ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8f9fa')]),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
        ]))
        return t

    story = [Paragraph("Cat Health Report", ts_),
             Paragraph(f"Generated: {date.today().strftime('%B %d, %Y')}", cs_),
             HRFlowable(width="100%",thickness=1,color=colors.HexColor('#bdc3c7'),spaceAfter=10)]

    for cat in ([cat_name] if cat_name else st.session_state.cats):
        a = analyze_cat_health(cat)
        p = a.get('profile', {})
        story.append(Paragraph(f"Cat: {cat}", hs_))
        pd_ = [["Field","Value"]]
        for lbl, key in [("Age","age"),("Breed","breed"),("Weight","weight"),("Notes","notes")]:
            if p.get(key): pd_.append([lbl, f"{p[key]} kg" if key=='weight' else p[key]])
        if len(pd_) > 1:
            story += [tbl(pd_,[5*cm,11*cm],colors.HexColor('#2980b9')), Spacer(1,6)]

        story.append(Paragraph("Weekly Health Summary", ss_))
        if a['status'] == 'no_data':
            story.append(Paragraph("No data recorded.", ns_))
        else:
            mr = a.get('metric_ratings', {})
            sd = [["Metric","Value","Status","Normal Range"],
                  ["Water/Day",  f"{a['water_avg']:.1f}", mr.get('water',{}).get('icon',''),  "Ideal: 3-8/day"],
                  ["Food/Day",   f"{a['food_avg']:.1f}",  mr.get('food',{}).get('icon',''),   "Ideal: 3-5/day"],
                  ["Litter/Day", f"{a['litter_avg']:.1f}",mr.get('litter',{}).get('icon',''), "Ideal: 2-4/day"],
                  ["Poop Days",  f"{a.get('poop_days',0)}/{a['total_days']}", "", "≥80% of days"],
                  ["Mood",       a.get('mood_trend','—').title(), a.get('mood_icon',''), "Good/Stable"],
                  ["Status",     a['status'].title(), "", ""]]
            story += [tbl(sd,[5*cm,2*cm,1.5*cm,7.5*cm],colors.HexColor('#27ae60')), Spacer(1,6)]

        vv = p.get('vet_visits', [])
        if vv:
            story.append(Paragraph("Vet History", ss_))
            vd = [["Date","Doctor","Reason","Medication"]]
            for v in sorted(vv, key=lambda x: x.get('date',''), reverse=True):
                vd.append([v.get('date','-'),f"Dr. {v.get('doctor','-')}",
                           v.get('reason','-'),v.get('medication','-')])
            story += [tbl(vd,[3*cm,4*cm,5*cm,4*cm],colors.HexColor('#8e44ad'))]

        # Breathing logs
        bl = st.session_state.breathing_logs.get(cat, [])
        if bl:
            recent_bl = sorted(bl, key=lambda x: x.get('date',''), reverse=True)[:5]
            story.append(Paragraph("Recent Resting Breathing Rate", ss_))
            bd = [["Date","Breaths/min","Status","Notes"]]
            for entry in recent_bl:
                bpm   = entry.get('bpm', 0)
                status= "Normal" if bpm <= 30 else "ELEVATED"
                bd.append([entry.get('date','-'), str(bpm), status, entry.get('notes','-')])
            story += [tbl(bd,[3*cm,3*cm,3*cm,7*cm],colors.HexColor('#e74c3c')), Spacer(1,6)]

        story += [Spacer(1,12),
                  HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#bdc3c7'),spaceAfter=10)]

    story.append(Paragraph("Cat Health Tracker — Always consult your vet for medical advice.", cs_))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CAT PROFILES
# ══════════════════════════════════════════════════════════════════════════════
def cat_profiles_page():
    st.header("🐱 Cat Profiles")
    for cat in st.session_state.cats:
        profile = st.session_state.cat_profiles.get(cat, {})
        with st.container(border=True):
            ci, cinfo = st.columns([1,4])
            with ci: st.markdown("## 🐱"); st.markdown(f"**{cat}**")
            with cinfo:
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Age",    profile.get('age')   or "—")
                c2.metric("Breed",  profile.get('breed') or "—")
                c3.metric("Weight", f"{profile.get('weight') or '—'} kg")
                c4.metric("Vet Visits", len(profile.get('vet_visits',[])))
                if profile.get('notes'): st.caption(f"📝 {profile['notes']}")
            b1, b2, _ = st.columns([1,1,4])
            with b1:
                if st.button("✏️ Edit Profile", key=f"open_edit_{cat}"):
                    st.session_state[f'edit_basic_{cat}'] = not st.session_state.get(f'edit_basic_{cat}', False)
                    st.rerun()
            with b2:
                if st.button("🏥 Add Visit", key=f"open_visit_{cat}"):
                    st.session_state[f'edit_{cat}'] = not st.session_state.get(f'edit_{cat}', False)
                    st.rerun()

        if st.session_state.get(f'edit_basic_{cat}', False):
            with st.expander(f"✏️ Edit {cat}", expanded=True):
                c1,c2 = st.columns(2)
                with c1:
                    st.text_input("Age",         value=profile.get('age',''),      key=f"edit_age_{cat}")
                    st.text_input("Breed",       value=profile.get('breed',''),    key=f"edit_breed_{cat}")
                    st.text_input("Weight (kg)", value=profile.get('weight',''),   key=f"edit_weight_{cat}")
                    st.text_input("Birthdate",   value=profile.get('birthdate',''),key=f"edit_bd_{cat}", placeholder="YYYY-MM-DD")
                with c2:
                    st.text_area("Notes", value=profile.get('notes',''), key=f"edit_notes_{cat}", height=70)
                st.markdown("**📅 Next Scheduled Appointments**")
                vc1,vc2 = st.columns(2)
                with vc1:
                    st.text_input("Next Annual Checkup", value=profile.get('next_checkup',''),   key=f"edit_nc_{cat}",  placeholder="YYYY-MM-DD")
                    st.text_input("Next Vaccines",       value=profile.get('next_vaccines',''),  key=f"edit_nv_{cat}",  placeholder="YYYY-MM-DD")
                with vc2:
                    st.text_input("Next Deworming",      value=profile.get('next_deworming',''), key=f"edit_nd_{cat}",  placeholder="YYYY-MM-DD")
                    st.text_input("Next Vet Visit",      value=profile.get('next_vet_visit',''), key=f"edit_nvv_{cat}", placeholder="YYYY-MM-DD")
                s1,s2 = st.columns([1,5])
                with s1:
                    if st.button("💾 Save", key=f"save_basic_{cat}", type="primary"):
                        st.session_state.cat_profiles[cat].update({
                            'age':            st.session_state[f"edit_age_{cat}"],
                            'breed':          st.session_state[f"edit_breed_{cat}"],
                            'weight':         st.session_state[f"edit_weight_{cat}"],
                            'notes':          st.session_state[f"edit_notes_{cat}"],
                            'birthdate':      st.session_state[f"edit_bd_{cat}"],
                            'next_checkup':   st.session_state[f"edit_nc_{cat}"],
                            'next_vaccines':  st.session_state[f"edit_nv_{cat}"],
                            'next_deworming': st.session_state[f"edit_nd_{cat}"],
                            'next_vet_visit': st.session_state[f"edit_nvv_{cat}"],
                        })
                        save_data(); st.success("✅ Profile saved!")
                        st.session_state[f'edit_basic_{cat}'] = False; st.rerun()
                with s2:
                    if st.button("❌ Cancel", key=f"cancel_basic_{cat}"):
                        st.session_state[f'edit_basic_{cat}'] = False; st.rerun()

        if st.session_state.get(f'edit_{cat}', False):
            with st.expander(f"🏥 Vet Visits — {cat}", expanded=True):
                vv = profile.get('vet_visits', [])
                if vv:
                    vdf = pd.DataFrame(vv)
                    dc  = [c for c in ['date','doctor','reason','medication'] if c in vdf.columns]
                    st.dataframe(vdf[dc], use_container_width=True, hide_index=True)
                    opts   = [f"{v['date']} — {v['reason']}" for v in vv]
                    to_del = st.selectbox("Select to delete", [""]+opts, key=f"del_vis_{cat}")
                    if to_del and st.button("🗑️ Delete Visit", key=f"del_vis_btn_{cat}", type="secondary"):
                        vv.pop(opts.index(to_del))
                        st.session_state.cat_profiles[cat]['vet_visits'] = vv
                        save_data(); st.success("Deleted!"); st.rerun()
                st.markdown("---")
                c1,c2 = st.columns(2)
                with c1:
                    st.date_input("Date",   key=f"v_date_{cat}")
                    st.text_input("Doctor", key=f"v_doc_{cat}", placeholder="Dr. Smith")
                with c2:
                    st.text_input("Reason",     key=f"v_reason_{cat}", placeholder="Annual checkup")
                    st.text_input("Medication", key=f"v_med_{cat}",    placeholder="None")
                a1,a2 = st.columns([1,5])
                with a1:
                    if st.button("💾 Save Visit", key=f"save_visit_{cat}", type="primary"):
                        st.session_state.cat_profiles[cat]['vet_visits'].append({
                            'date':       str(st.session_state[f"v_date_{cat}"]),
                            'doctor':     st.session_state[f"v_doc_{cat}"],
                            'reason':     st.session_state[f"v_reason_{cat}"],
                            'medication': st.session_state[f"v_med_{cat}"]})
                        save_data(); st.success("✅ Visit added!"); st.rerun()
                with a2:
                    if st.button("❌ Close", key=f"close_visit_{cat}"):
                        st.session_state[f'edit_{cat}'] = False; st.rerun()
        st.markdown("")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADD HEALTH ENTRY
# ══════════════════════════════════════════════════════════════════════════════
def add_health_entry_page():
    st.header("📝 Add Health Entry")

    if st.session_state.editing_health_entry and st.session_state.edit_entry_data:
        st.subheader("✏️ Edit Health Entry")
        ec  = st.session_state.edit_entry_cat
        ets = st.session_state.edit_entry_data.get('timestamp','')
        ei  = st.session_state.edit_entry_data.get('index',0)
        arr = st.session_state.health_data.get(ec,{}).get(ets,[])
        oe  = arr[ei] if ei < len(arr) else None

        if oe:
            with st.form("edit_form"):
                c1,c2 = st.columns(2)
                with c1:
                    wd  = st.number_input("Water Drinks",     0, 20, oe.get('water_drinks',0))
                    fe  = st.number_input("Food Eats",        0, 10, oe.get('food_eats',0))
                    lbt = st.number_input("Litter Box Times", 0, 15, oe.get('litter_box_times',0))
                    poo = st.checkbox("💩 Pooped today?", value=oe.get('pooped',False))
                with c2:
                    mopts = ["Very Poor","Poor","Normal","Good","Excellent"]
                    mood  = st.selectbox("Mood", mopts, index=mopts.index(oe.get('mood','Normal')))
                    aopts = ["Poor","Fair","Good","Excellent"]
                    ga    = st.selectbox("General Appearance", aopts, index=aopts.index(oe.get('general_appearance','Good')))
                    lq    = st.text_area("Litter Quality Issues", value='\n'.join(oe.get('litter_quality',[])))
                    food_eaten = st.text_input("Food eaten", value=oe.get('food_eaten',''))
                st.markdown("---")
                st.subheader("💊 Medicine / Treatment")
                with st.expander("Edit"):
                    mn  = st.text_input("Name",  value=oe.get('medication_name',''))
                    mty_opts = ["Oral","Nebulizer","Injection","Topical","Eye drops","Ear drops","Other"]
                    mty = st.selectbox("Type", mty_opts, index=mty_opts.index(oe.get('medication_type','Oral')))
                    md_ = st.text_input("Dosage",    value=oe.get('medication_dosage',''))
                    mf  = st.text_input("Frequency", value=oe.get('medication_frequency',''))
                    mr  = st.text_input("Reason",    value=oe.get('medication_reason',''))
                    cs1,ce1 = st.columns(2)
                    with cs1:
                        ms_s = oe.get('medication_start_date','')
                        ms   = st.date_input("Start", value=date.fromisoformat(ms_s) if ms_s else date.today(), key="edit_ms")
                    with ce1:
                        me_s = oe.get('medication_end_date','')
                        me   = st.date_input("End",   value=date.fromisoformat(me_s) if me_s else date.today(), key="edit_me")
                st.markdown("---")
                notes = st.text_area("Additional Notes", height=70, value=oe.get('notes',''))
                st.markdown("---")
                st.subheader("🪥 Grooming Tasks")
                gt = {t: st.checkbox(t, value=oe.get('grooming_tasks',{}).get(t,False))
                      for t in ["Brush Fur","Trim Nails","Clean Ears","Clean Eyes","Clean Chin","Dental Care"]}
                if st.form_submit_button("💾 Update"):
                    ed = {'water_drinks': wd, 'food_eats': fe, 'litter_box_times': lbt,
                          'mood': mood, 'general_appearance': ga, 'pooped': poo,
                          'food_eaten': food_eaten,
                          'litter_quality': lq.split('\n') if lq else [],
                          'notes': notes, 'grooming_tasks': {t: c for t,c in gt.items() if c}}
                    if mn:
                        ed.update({'medication_name': mn, 'medication_type': mty,
                                   'medication_dosage': md_, 'medication_frequency': mf,
                                   'medication_reason': mr,
                                   'medication_start_date': str(ms), 'medication_end_date': str(me)})
                    update_health_entry(ec, ets, ei, ed)
                    st.success(f"✅ Updated for {ec}!")
                    st.session_state.editing_health_entry = False
                    st.session_state.edit_entry_data = {}; st.rerun()
        if st.button("❌ Cancel Edit"):
            st.session_state.editing_health_entry = False
            st.session_state.edit_entry_data = {}; st.rerun()
        return

    st.subheader("🆕 Add New Health Entry")
    selected_cat = st.selectbox("Select Cat", st.session_state.cats, key="cat_selector")
    if st.session_state.health_form_cat != selected_cat:
        for k in [k for k in st.session_state if k.startswith("form_")]:
            del st.session_state[k]
        st.session_state.health_form_cat = selected_cat

    ds          = st.session_state.diet_settings.get(selected_cat, {})
    active_names= ds.get('active_foods', [])
    default_food= active_names[0] if active_names else 'Pro Plan Adult Wet'
    entry_mode  = st.radio("Entry Mode", ["🚀 Quick Entry", "📋 Detailed Entry"])

    if entry_mode == "🚀 Quick Entry":
        st.markdown("### Quick Actions")
        c1,c2,c3,c4 = st.columns(4)
        base_q = {'water_drinks':0,'food_eats':0,'litter_box_times':0,'pooped':False,
                  'mood':'Good','general_appearance':'Good','litter_quality':[],'grooming_tasks':{},'food_eaten':''}
        with c1:
            if st.button("💧 Water Drank"):
                add_health_entry(selected_cat, {**base_q,'water_drinks':1,'notes':'Quick: Water drank'})
                st.success("✅"); st.rerun()
        with c2:
            if st.button("🍽️ Food Eaten"):
                add_health_entry(selected_cat, {**base_q,'food_eats':1,'food_eaten':default_food,
                                                'notes':f'Quick: Food eaten ({default_food})'})
                st.success("✅"); st.rerun()
        with c3:
            if st.button("🚽 Litter Used"):
                add_health_entry(selected_cat, {**base_q,'litter_box_times':1,'notes':'Quick: Litter used'})
                st.success("✅"); st.rerun()
        with c4:
            if st.button("💩 Pooped"):
                add_health_entry(selected_cat, {**base_q,'litter_box_times':1,'pooped':True,'notes':'Quick: Pooped'})
                st.success("✅"); st.rerun()
        st.markdown("---")

    st.markdown("### 📋 Detailed Entry")
    with st.form("health_entry_form"):
        c1,c2 = st.columns(2)
        with c1:
            wd  = st.number_input("💧 Water Drinks",     0, 20, 0, key="form_water")
            fe  = st.number_input("🍽️ Food Eats",        0, 10, 0, key="form_food")
            lbt = st.number_input("🚽 Litter Box Times", 0, 15, 0, key="form_litter")
            poo = st.checkbox("💩 Pooped today?", key="form_poop")
        with c2:
            mood        = st.selectbox("😊 Mood",              ["Very Poor","Poor","Normal","Good","Excellent"], key="form_mood")
            ga          = st.selectbox("✨ General Appearance", ["Poor","Fair","Good","Excellent"],               key="form_appearance")
            lq          = st.text_area("🚨 Litter Quality Issues",
                                       placeholder="e.g., Blood, diarrhea, mucus...", key="form_lq")
            food_eaten  = st.text_input("🥣 Food eaten today", value=default_food, key="form_food_eaten")

        st.markdown("---")
        st.subheader("💊 Medicine / Treatment (Optional)")
        with st.expander("Add"):
            mn  = st.text_input("Name",      placeholder="e.g., Amoxicillin / Nebulizer session", key="form_med_name")
            mty = st.selectbox("Type", ["Oral","Nebulizer","Injection","Topical","Eye drops","Ear drops","Other"], key="form_med_type")
            md_ = st.text_input("Dosage",    placeholder="e.g., 50mg / 10 min session", key="form_med_dosage")
            mf  = st.text_input("Frequency", placeholder="e.g., Twice daily",           key="form_med_freq")
            mr2 = st.text_input("Reason",    placeholder="e.g., Respiratory support",   key="form_med_reason")
            cs1,ce1 = st.columns(2)
            with cs1: ms = st.date_input("Start", value=date.today(),                   key="form_med_start")
            with ce1: me = st.date_input("End",   value=date.today()+timedelta(days=7), key="form_med_end")

        st.markdown("---")
        notes = st.text_area("📝 Additional Notes", height=70,
                             placeholder="Any other observations...", key="form_notes")

        st.markdown("---")
        st.subheader("🪥 Grooming Tasks")
        st.caption("Check only if performed today. (Reminder appears Thu & Fri)")
        g1,g2,g3 = st.columns(3)
        with g1: gb = st.checkbox("Brush Fur",  key="form_g_brush"); gn = st.checkbox("Trim Nails", key="form_g_nails")
        with g2: ge = st.checkbox("Clean Ears", key="form_g_ears");  gy = st.checkbox("Clean Eyes", key="form_g_eyes")
        with g3: gc = st.checkbox("Clean Chin", key="form_g_chin");  gd = st.checkbox("Dental Care",key="form_g_dental")
        gt = {"Brush Fur":gb,"Trim Nails":gn,"Clean Ears":ge,"Clean Eyes":gy,"Clean Chin":gc,"Dental Care":gd}

        if st.form_submit_button("💾 Save Health Entry", type="primary", use_container_width=True):
            ed = {'water_drinks': wd, 'food_eats': fe, 'litter_box_times': lbt,
                  'mood': mood, 'general_appearance': ga, 'pooped': poo, 'food_eaten': food_eaten,
                  'litter_quality': lq.split('\n') if lq else [], 'notes': notes,
                  'grooming_tasks': {t: c for t,c in gt.items() if c}}
            if mn:
                ed.update({'medication_name': mn, 'medication_type': mty,
                           'medication_dosage': md_, 'medication_frequency': mf,
                           'medication_reason': mr2,
                           'medication_start_date': str(ms), 'medication_end_date': str(me)})
            add_health_entry(selected_cat, ed)
            st.success(f"✅ Entry saved for {selected_cat}!"); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: VIEW HEALTH DATA
# ══════════════════════════════════════════════════════════════════════════════
def view_health_data_page():
    st.header("📊 View Health Data")
    c1,c2 = st.columns(2)
    with c1: sel = st.selectbox("Select Cat", st.session_state.cats)
    with c2:
        dr = st.date_input("Date Range", value=(date.today()-timedelta(days=30), date.today()), max_value=date.today())
    sd, ed = (dr[0],dr[1]) if len(dr)==2 else (date.today(),date.today())

    entries = get_health_entries(sel, sd, ed)
    if not entries: st.info(f"No data found for {sel} in this range."); return

    df    = pd.DataFrame(entries)
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df['time'] = pd.to_datetime(df['timestamp']).dt.time
    df    = df.sort_values('timestamp', ascending=False)
    daily = get_daily_aggregated(sel, sd, ed)

    st.subheader(f"📈 {sel}'s Combined Daily Totals")
    if daily:
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Avg Water/Day",  f"{sum(d['water_drinks'] for d in daily.values())/len(daily):.1f}")
        c2.metric("Avg Food/Day",   f"{sum(d['food_eats'] for d in daily.values())/len(daily):.1f}")
        c3.metric("Avg Litter/Day", f"{sum(d['litter_box_times'] for d in daily.values())/len(daily):.1f}")
        c4.metric("Days Tracked",   len(daily))
        c5.metric("Poop Days",      f"{sum(1 for d in daily.values() if d.get('pooped'))}/{len(daily)}")

    df['date_only'] = df['timestamp'].str.split('T').str[0]
    for ds, grp in df.groupby('date_only'):
        dd  = date.fromisoformat(ds)
        dt  = daily.get(dd, {})
        pts = []
        if dt.get('water_drinks'):     pts.append(f"💧{dt['water_drinks']}")
        if dt.get('food_eats'):        pts.append(f"🍽️{dt['food_eats']}")
        if dt.get('litter_box_times'): pts.append(f"🚽{dt['litter_box_times']}")
        if dt.get('pooped'):           pts.append("💩✅")
        with st.expander(f"📅 {ds} ({len(grp)} entries)" + (f" — {' '.join(pts)}" if pts else "")):
            for idx, row in grp.iterrows():
                st.markdown(f"**⏰ {row['time']}**")
                ca,cb = st.columns([3,1])
                with ca:
                    st.write(f"Water: {row.get('water_drinks','N/A')} · Food: {row.get('food_eats','N/A')} · Litter: {row.get('litter_box_times','N/A')}")
                    if row.get('food_eaten'): st.write(f"🥣 {row['food_eaten']}")
                    st.write(f"💩 Pooped: {'✅ Yes' if row.get('pooped') else '—'}")
                    st.write(f"Mood: {row.get('mood','N/A')} · Appearance: {row.get('general_appearance','N/A')}")
                    if row.get('litter_quality'):
                        q = '\n'.join(row['litter_quality'])
                        if q.strip(): st.write(f"⚠️ Litter: {q}")
                    if row.get('notes'): st.write(f"📝 {row['notes']}")
                    if row.get('medication_name'):
                        ms_ = f"💊 {row['medication_name']} [{row.get('medication_type','Oral')}] ({row.get('medication_dosage','N/A')})"
                        if row.get('medication_start_date') and row.get('medication_end_date'):
                            ms_ += f" · {row['medication_start_date']} → {row['medication_end_date']}"
                        st.write(ms_)
                    gd = [t for t,done in row.get('grooming_tasks',{}).items() if done]
                    if gd: st.write(f"🪥 {', '.join(gd)}")
                with cb:
                    if st.button("✏️", key=f"edit_{idx}"):
                        st.session_state.editing_health_entry = True
                        st.session_state.edit_entry_data = {'timestamp': row['timestamp'], 'index': idx}
                        st.session_state.edit_entry_cat  = sel; st.rerun()
                    if st.button("🗑️", key=f"del_{idx}"):
                        delete_health_entry(sel, row['timestamp'], idx)
                        st.success("Deleted!"); st.rerun()
                st.markdown("---")

    st.subheader("📊 Trends")
    if daily and len(daily) > 1:
        sd2 = sorted(daily.keys())
        fig = make_subplots(rows=2, cols=2, subplot_titles=('Water','Food','Litter Box','Entries/Day'))
        fig.add_trace(go.Bar(x=sd2, y=[daily[d]['water_drinks']     for d in sd2], marker_color='#4fc3f7'), row=1,col=1)
        fig.add_trace(go.Bar(x=sd2, y=[daily[d]['food_eats']        for d in sd2], marker_color='#81c784'), row=1,col=2)
        fig.add_trace(go.Bar(x=sd2, y=[daily[d]['litter_box_times'] for d in sd2], marker_color='#ffb74d'), row=2,col=1)
        fig.add_trace(go.Bar(x=sd2, y=[daily[d]['entry_count']      for d in sd2], marker_color='#ce93d8'), row=2,col=2)
        fig.update_layout(height=480, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TASK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def task_management_page():
    st.header("📋 Task Management")
    today     = date.today()
    today_str = str(today)
    weekday   = today.weekday()
    is_thu    = weekday == 3
    is_fri    = weekday == 4
    is_first  = today.day == 1
    completed_today = [l['task'] for l in st.session_state.task_logs.get(today_str, [])]

    if is_thu or is_fri:
        st.warning(f"🪥 **{'Thursday' if is_thu else 'Friday'} — Grooming day!** "
                   "Log grooming in **Add Health Entry** under Grooming Tasks.")
    else:
        st.caption(f"🪥 Grooming reminder: Thu & Fri. Log in Add Health Entry. Today: {today.strftime('%A')}.")
    st.markdown("---")

    st.subheader("📅 Daily Tasks")
    for task in st.session_state.tasks.get('daily', []):
        done    = task in completed_today
        checked = st.checkbox(task, value=done, key=f"task_daily_{task}")
        if checked and not done:
            add_task_completion(task); st.rerun()

    st.markdown("---")
    st.subheader("🗓️ Weekly Tasks")
    week_start = today - timedelta(days=weekday)
    week_end   = week_start + timedelta(days=6)
    wc         = get_task_completions(week_start, week_end)
    done_week  = set(l['task'] for logs in wc.values() for l in logs
                     if l['task'] in st.session_state.tasks.get('weekly',[]))
    if is_thu or is_fri:
        st.info(f"🔔 Weekly tasks due — it's {'Thursday' if is_thu else 'Friday'}!")
        for task in st.session_state.tasks.get('weekly', []):
            if task in done_week: st.success(f"✅ {task} — done this week!")
            else:
                if st.checkbox(task, value=False, key=f"task_weekly_{task}"):
                    add_task_completion(task); st.rerun()
    else:
        pending = [t for t in st.session_state.tasks.get('weekly',[]) if t not in done_week]
        if not pending: st.success("✅ All weekly tasks done this week!")
        else: st.write(f"Weekly tasks appear Thu & Fri. Remaining: {', '.join(pending)}")
        for t in done_week: st.success(f"✅ {t} — done this week!")

    st.markdown("---")
    st.subheader("📆 Monthly Tasks")
    mstart = date(today.year, today.month, 1)
    mend   = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    mc     = get_task_completions(mstart, mend)
    done_m = set(l['task'] for logs in mc.values() for l in logs
                 if l['task'] in st.session_state.tasks.get('monthly',[]))
    if is_first:
        st.warning("🔔 **First of the month** — monthly tasks due!")
        for task in st.session_state.tasks.get('monthly', []):
            if task in done_m: st.success(f"✅ {task} — done this month!")
            else:
                if st.checkbox(task, value=False, key=f"task_monthly_{task}"):
                    add_task_completion(task); st.rerun()
    else:
        pending_m = [t for t in st.session_state.tasks.get('monthly',[]) if t not in done_m]
        if not pending_m: st.success("✅ All monthly tasks done this month!")
        else: st.write(f"Monthly tasks appear on 1st. Remaining: {len(pending_m)}/{len(st.session_state.tasks.get('monthly',[]))}")
        for t in done_m: st.success(f"✅ {t} — done this month!")

    st.markdown("---")
    st.subheader("📅 Monthly Calendar")
    c1,c2 = st.columns([1,3])
    with c1:
        cm = st.selectbox("Month", range(1,13), index=today.month-1, format_func=lambda m: calendar.month_name[m])
        cy = st.number_input("Year", 2024, 2030, today.year, step=1)
    with c2:
        monthly_task_calendar(int(cy), int(cm))

    st.markdown("---")
    st.subheader("📋 History")
    c1,c2 = st.columns(2)
    with c1: hs = st.date_input("Start", today-timedelta(days=7))
    with c2: he = st.date_input("End",   today)
    comps = get_task_completions(hs, he)
    if not comps: st.info("No completions found."); return
    rows = [{'date': ds, 'task': l['task'], 'cat': l.get('cat',''), 'completed_at': l['completed_at']}
            for ds, logs in comps.items() for l in logs]
    df = pd.DataFrame(rows); df['date'] = pd.to_datetime(df['date'])
    st.dataframe(df.sort_values('date'), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DIET PLANNING
# ══════════════════════════════════════════════════════════════════════════════
def diet_planning_page():
    st.header("🥗 Diet Planning")
    st.write("Manage your food library, assign foods per cat, and get data-driven nutritional analysis.")

    # ── Food Library ──
    with st.expander("📚 Food Library — Add / View Foods", expanded=False):
        lib = st.session_state.food_library
        food_names = [f['name'] for f in lib]

        st.markdown("#### ➕ Add a New Food")
        with st.form("add_food_form"):
            fc1,fc2 = st.columns(2)
            with fc1:
                new_name     = st.text_input("Food Name", placeholder="e.g., Royal Canin Indoor Wet")
                new_type     = st.selectbox("Type", ["Wet","Dry","Treat"])
                new_protein  = st.number_input("Protein %",    0.0, 100.0, 10.0, step=0.5)
                new_fat      = st.number_input("Fat %",        0.0, 100.0,  4.0, step=0.5)
            with fc2:
                new_moisture = st.number_input("Moisture %",   0.0, 100.0, 78.0, step=1.0)
                new_fibre    = st.number_input("Fibre %",      0.0,  20.0,  1.0, step=0.5)
                new_phos     = st.number_input("Phosphorus %", 0.0,   5.0,  0.2, step=0.05)
                new_sodium   = st.number_input("Sodium %",     0.0,   5.0, 0.15, step=0.01)
                new_taurine  = st.checkbox("Contains added Taurine?", value=True)
                new_cal      = st.number_input("Calories per 100g", 0, 600, 85)
            new_notes = st.text_input("Notes (optional)")
            if st.form_submit_button("➕ Add to Library", type="primary"):
                if new_name and new_name not in food_names:
                    st.session_state.food_library.append({
                        'name': new_name, 'type': new_type,
                        'protein_pct': new_protein, 'fat_pct': new_fat,
                        'fibre_pct': new_fibre, 'moisture_pct': new_moisture,
                        'phosphorus_pct': new_phos, 'sodium_pct': new_sodium,
                        'taurine': new_taurine, 'calories_per_100g': new_cal,
                        'notes': new_notes
                    })
                    save_data(); st.success(f"✅ {new_name} added!"); st.rerun()
                elif new_name in food_names:
                    st.warning("A food with this name already exists.")
                else:
                    st.warning("Please enter a food name.")

        st.markdown("#### Current Library")
        if lib:
            lib_df = pd.DataFrame([{
                'Name': f['name'], 'Type': f['type'],
                'Protein%': f['protein_pct'], 'Fat%': f['fat_pct'],
                'Moisture%': f['moisture_pct'], 'Phosphorus%': f['phosphorus_pct'],
                'Taurine': '✅' if f['taurine'] else '❌',
                'Cal/100g': f['calories_per_100g']
            } for f in lib])
            st.dataframe(lib_df, use_container_width=True, hide_index=True)

            to_del = st.selectbox("Remove food from library", [""]+food_names, key="del_food")
            if to_del and st.button("🗑️ Remove", key="del_food_btn", type="secondary"):
                st.session_state.food_library = [f for f in lib if f['name'] != to_del]
                for cat in st.session_state.cats:
                    af = st.session_state.diet_settings[cat].get('active_foods', [])
                    st.session_state.diet_settings[cat]['active_foods'] = [f for f in af if f != to_del]
                save_data(); st.success(f"Removed {to_del}"); st.rerun()

    st.markdown("---")

    # ── Per-cat ──
    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            ds  = st.session_state.diet_settings.get(cat, {})
            lib = st.session_state.food_library
            all_food_names   = [f['name'] for f in lib]
            current_active   = [f for f in ds.get('active_foods', []) if f in all_food_names]

            with st.expander(f"⚙️ {cat}'s Diet Settings", expanded=True):
                selected_foods = st.multiselect(
                    f"Foods {cat} is currently eating",
                    options=all_food_names,
                    default=current_active,
                    key=f"diet_foods_{cat}"
                )
                meals      = st.number_input("Meals per day", 1, 8, int(ds.get('meals_per_day',3)), key=f"diet_meals_{cat}")
                diet_notes = st.text_area("Diet notes", value=ds.get('notes',''), key=f"diet_notes_{cat}", height=60)
                if st.button("💾 Save Diet Settings", key=f"save_diet_{cat}", type="primary"):
                    st.session_state.diet_settings[cat].update({
                        'active_foods':  st.session_state[f"diet_foods_{cat}"],
                        'meals_per_day': st.session_state[f"diet_meals_{cat}"],
                        'notes':         st.session_state[f"diet_notes_{cat}"],
                    })
                    save_data(); st.success("✅ Saved!"); st.rerun()

            st.markdown("---")
            st.subheader(f"🔬 {cat}'s Diet Analysis")
            da = analyze_diet(cat)
            if not da['has_data']:
                st.info("Select foods above and save to see analysis."); continue

            if da['positives']:
                st.markdown("**✅ What's good:**")
                for p in da['positives']: st.success(p)
            if da['warnings']:
                st.markdown("**⚠️ Concerns:**")
                for w in da['warnings']:
                    if w.startswith("🔴"): st.error(w)
                    else: st.warning(w)
            if da['findings']:
                st.markdown("**ℹ️ Notes:**")
                for f in da['findings']: st.info(f)

            st.markdown("---")
            st.subheader("📊 Per-Food Nutritional Breakdown")
            st.caption("🟢 Ideal range · 🟡 Acceptable · 🔴/🟠 Outside ideal. Ranges differ by food type (wet/dry/treat).")

            lib_map = {f['name']: f for f in st.session_state.food_library}

            for fname in selected_foods:
                food = lib_map.get(fname)
                if not food: continue
                ftype = food['type']
                icon  = {'Wet':'🥣','Dry':'🥫','Treat':'🎁'}.get(ftype, '🍽️')

                with st.expander(f"{icon} {fname} ({ftype})", expanded=True):
                    c1,c2 = st.columns(2)

                    def show_n(label, value, il, ih, ol, oh, unit="%"):
                        if il <= value <= ih:   ico, txt = "🟢", f"Ideal ({il}–{ih}{unit})"
                        elif ol <= value <= oh: ico, txt = "🟡", f"Acceptable (ideal {il}–{ih}{unit})"
                        elif value < ol:        ico, txt = "🔴", f"Low — ideal {il}–{ih}{unit}"
                        else:                   ico, txt = "🟠", f"High — ideal {il}–{ih}{unit}"
                        st.write(f"{ico} **{label}:** {value}{unit} — {txt}")

                    with c1:
                        st.markdown("**📋 Nutritional values:**")
                        ranges = {
                            'Wet':   {'p':(8,15,5,20), 'm':(70,85,60,90), 'f':(3,8,2,12),   'ph':(0.10,0.40,0.0,0.7)},
                            'Dry':   {'p':(35,50,25,60),'m':(8,14,5,18),  'f':(10,20,6,25),  'ph':(0.50,0.90,0.3,1.2)},
                            'Treat': {'p':(40,80,20,90),'m':(0,15,0,30),  'f':(5,20,2,30),   'ph':(0.0,1.0,0.0,1.5)},
                        }.get(ftype, {'p':(8,15,5,20),'m':(70,85,60,90),'f':(3,8,2,12),'ph':(0.1,0.4,0.0,0.7)})
                        show_n("Protein",    food['protein_pct'],   *ranges['p'])
                        show_n("Moisture",   food['moisture_pct'],  *ranges['m'])
                        show_n("Fat",        food['fat_pct'],       *ranges['f'])
                        show_n("Phosphorus", food['phosphorus_pct'],*ranges['ph'])
                        t_icon = "🟢" if food['taurine'] else "🔴"
                        st.write(f"{t_icon} **Taurine:** {'Added ✅' if food['taurine'] else 'Not added ❌ — ensure complete food is primary diet'}")
                        if food.get('sodium_pct'):
                            s_icon = "🟢" if food['sodium_pct'] < 0.3 else "🟡" if food['sodium_pct'] < 0.5 else "🟠"
                            st.write(f"{s_icon} **Sodium:** {food['sodium_pct']}% — {'Heart-friendly' if food['sodium_pct']<0.3 else 'Moderate' if food['sodium_pct']<0.5 else 'Higher — monitor'}")
                        st.write(f"⚡ **Calories:** {food['calories_per_100g']} kcal/100g")

                    with c2:
                        st.markdown("**🔬 Why each nutrient matters:**")
                        st.markdown(f"**Protein:** {DIET_ANALYSIS_RULES['protein']['why'][:200]}...")
                        st.markdown(f"**Moisture:** {DIET_ANALYSIS_RULES['moisture']['why'][:200]}...")
                        st.markdown(f"**Phosphorus:** {DIET_ANALYSIS_RULES['phosphorus']['why'][:200]}...")
                        st.markdown(f"**Taurine:** {TAURINE_WHY[:200]}...")

                    if food.get('notes'):
                        st.info(f"📝 {food['notes']}")

            # Essential nutrients guide
            st.markdown("---")
            with st.expander("🐾 What cats must get every day & why", expanded=False):
                for key, rule in DIET_ANALYSIS_RULES.items():
                    st.markdown(f"**🔬 {rule['label']}**")
                    st.write(rule['why'])
                    if 'deficiency' in rule: st.error(f"If deficient: {rule['deficiency']}")
                    if 'excess' in rule:     st.warning(f"Excess risk: {rule['excess']}")
                    st.markdown("---")
                st.markdown("**🔬 Taurine**")
                st.write(TAURINE_WHY)
                st.error("If deficient: Heart disease (DCM), blindness, reproductive failure — all irreversible without early treatment")

            # Recent food log
            st.markdown("---")
            st.subheader("📋 Recent Food Log (7 days)")
            today = date.today()
            d7 = get_daily_aggregated(cat, today-timedelta(days=7), today)
            if d7:
                rows = [{'Date': str(dd), 'Meals Logged': d['food_eats'],
                         'Foods': ', '.join(set(d['food_log'])) or '—',
                         'Water Drinks': d['water_drinks'],
                         'Pooped': '✅' if d['pooped'] else '—'}
                        for dd, d in sorted(d7.items(), reverse=True)]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No food entries logged yet this week.")


# ══════════════════════════════════════════════════════════════════════════════
# NEW FEATURE 1: BREATHING RATE TRACKER
# ══════════════════════════════════════════════════════════════════════════════
def breathing_tracker_page():
    st.header("🫁 Resting Breathing Rate Tracker")
    st.write(
        "Count breaths per minute while your cat is **sleeping** (not purring, not moving). "
        "**Normal: 15-30 breaths/min at rest.** "
        "🔴 **Above 30 = alert your vet.** This is one of the earliest detectable signs of heart or lung problems.")

    st.info(
        "**How to count:** Watch the chest rise and fall. Count each rise as 1 breath. "
        "Count for 30 seconds and multiply by 2. Or count for 60 seconds. "
        "Do this when they are fully relaxed and asleep — not after playing.")

    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            bl = st.session_state.breathing_logs.get(cat, [])

            # ── Log a new reading ──
            st.subheader(f"Log a reading for {cat}")
            with st.form(f"breathing_form_{cat}"):
                bc1, bc2 = st.columns(2)
                with bc1:
                    b_date = st.date_input("Date", value=date.today(), key=f"b_date_{cat}")
                    b_bpm  = st.number_input("Breaths per minute", min_value=1, max_value=80,
                                             value=20, key=f"b_bpm_{cat}")
                with bc2:
                    b_context = st.selectbox("When measured", ["Sleeping","Resting awake","After light activity"],
                                             key=f"b_ctx_{cat}")
                    b_notes   = st.text_input("Notes", placeholder="Any observations?", key=f"b_notes_{cat}")
                if st.form_submit_button("💾 Save Reading", type="primary"):
                    st.session_state.breathing_logs.setdefault(cat, [])
                    st.session_state.breathing_logs[cat].append({
                        'date':    str(b_date),
                        'bpm':     b_bpm,
                        'context': b_context,
                        'notes':   b_notes
                    })
                    save_data()
                    if b_bpm > 30 and b_context == "Sleeping":
                        st.error(f"🔴 **{cat}'s resting breathing rate is {b_bpm} bpm — above the 30 bpm threshold. "
                                 "Contact your vet, especially given the cardiac monitoring already in place.**")
                    elif b_bpm > 25 and b_context == "Sleeping":
                        st.warning(f"🟡 {cat}'s breathing rate is {b_bpm} bpm — in the upper normal range. Monitor closely and log again tomorrow.")
                    else:
                        st.success(f"✅ Saved — {b_bpm} bpm. Normal range.")
                    st.rerun()

            st.markdown("---")

            # ── History and chart ──
            if bl:
                st.subheader("📊 Breathing Rate History")
                sleeping_only = [e for e in bl if e.get('context') == 'Sleeping']
                all_sorted    = sorted(bl, key=lambda x: x.get('date',''), reverse=True)

                # Summary stats
                if sleeping_only:
                    bpms   = [e['bpm'] for e in sleeping_only]
                    avg_bpm = sum(bpms) / len(bpms)
                    max_bpm = max(bpms)
                    last_e  = sorted(sleeping_only, key=lambda x: x.get('date',''))[-1]

                    c1,c2,c3 = st.columns(3)
                    c1.metric("Last reading (sleeping)", f"{last_e['bpm']} bpm",
                              delta=None)
                    c2.metric("Average (sleeping)", f"{avg_bpm:.1f} bpm")
                    c3.metric("Highest recorded", f"{max_bpm} bpm",
                              delta="⚠️ Alert" if max_bpm > 30 else "✅ Normal")

                    if avg_bpm > 30:
                        st.error(f"🔴 **Average resting breathing rate ({avg_bpm:.1f} bpm) is above normal.** "
                                 "Normal: 15-30 bpm while sleeping. Please discuss with your vet at the next visit.")
                    elif avg_bpm > 25:
                        st.warning(f"🟡 Average rate ({avg_bpm:.1f} bpm) is in the upper normal range. "
                                   "Keep monitoring. Alert: if any reading exceeds 30 bpm while sleeping, contact vet.")
                    else:
                        st.success(f"✅ Average resting breathing rate ({avg_bpm:.1f} bpm) is within normal range (15-30 bpm).")

                # Chart
                if len(sleeping_only) >= 2:
                    chart_data = sorted(sleeping_only, key=lambda x: x.get('date',''))
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=[e['date'] for e in chart_data],
                        y=[e['bpm']  for e in chart_data],
                        mode='lines+markers',
                        name='Breaths/min',
                        line=dict(color='#e74c3c', width=2),
                        marker=dict(size=8)
                    ))
                    fig.add_hline(y=30, line_dash="dash", line_color="red",
                                  annotation_text="Alert threshold (30 bpm)")
                    fig.add_hline(y=20, line_dash="dot", line_color="green",
                                  annotation_text="Ideal (20 bpm)")
                    fig.update_layout(
                        title=f"{cat} — Resting Breathing Rate Over Time",
                        yaxis_title="Breaths per minute",
                        yaxis=dict(range=[0, max(40, max(e['bpm'] for e in chart_data)+5)]),
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Table
                df_bl = pd.DataFrame(all_sorted)
                df_bl['status'] = df_bl['bpm'].apply(
                    lambda x: "🟢 Normal" if x <= 25 else "🟡 Upper normal" if x <= 30 else "🔴 ELEVATED")
                st.dataframe(df_bl[['date','bpm','context','status','notes']],
                             use_container_width=True, hide_index=True)
            else:
                st.info(f"No breathing readings logged for {cat} yet. Log one above.")

            st.markdown("")


# ══════════════════════════════════════════════════════════════════════════════
# NEW FEATURE 2: WEIGHT TRACKER (at vet visits)
# ══════════════════════════════════════════════════════════════════════════════
def weight_tracker_page():
    st.header("⚖️ Weight Tracker")
    st.write(
        "Weights are recorded at each vet visit since vet scales are accurate. "
        "Tracking weight over time helps detect early illness — unexplained weight loss is often the first sign.")

    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            profile  = st.session_state.cat_profiles.get(cat, {})
            vv       = profile.get('vet_visits', [])
            wt_visits = [v for v in vv if v.get('weight_kg')]

            # Also include manual weight logs
            weight_logs = profile.get('weight_logs', [])

            st.subheader(f"Log a weight for {cat}")
            with st.form(f"weight_form_{cat}"):
                wc1, wc2 = st.columns(2)
                with wc1:
                    w_date = st.date_input("Date", value=date.today(), key=f"w_date_{cat}")
                    w_kg   = st.number_input("Weight (kg)", min_value=0.5, max_value=15.0,
                                             value=float(profile.get('weight','4.0') or 4.0),
                                             step=0.1, key=f"w_kg_{cat}")
                with wc2:
                    w_source = st.selectbox("Measured at", ["Vet clinic","Home scale","Estimated"],
                                            key=f"w_src_{cat}")
                    w_notes  = st.text_input("Notes", placeholder="e.g., After deworming",
                                             key=f"w_notes_{cat}")
                if st.form_submit_button("💾 Save Weight", type="primary"):
                    if 'weight_logs' not in st.session_state.cat_profiles[cat]:
                        st.session_state.cat_profiles[cat]['weight_logs'] = []
                    st.session_state.cat_profiles[cat]['weight_logs'].append({
                        'date':   str(w_date),
                        'kg':     w_kg,
                        'source': w_source,
                        'notes':  w_notes
                    })
                    # Update current weight in profile
                    st.session_state.cat_profiles[cat]['weight'] = str(w_kg)
                    save_data(); st.success(f"✅ Weight logged: {w_kg}kg"); st.rerun()

            st.markdown("---")

            # ── History and chart ──
            all_weights = profile.get('weight_logs', [])
            if all_weights:
                st.subheader("📊 Weight History")
                sorted_w = sorted(all_weights, key=lambda x: x.get('date',''))

                if len(sorted_w) >= 1:
                    first_w = sorted_w[0]['kg']
                    last_w  = sorted_w[-1]['kg']
                    change  = last_w - first_w
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Current Weight", f"{last_w}kg")
                    c2.metric("First Recorded",  f"{first_w}kg")
                    c3.metric("Total Change",    f"{change:+.1f}kg",
                              delta=f"{'⚠️ Loss' if change < -0.2 else '✅ Stable' if abs(change) <= 0.2 else '⚠️ Gain'}")

                    if change < -0.5:
                        st.error(f"🔴 **{cat} has lost {abs(change):.1f}kg** since first recorded. "
                                 "Unexplained weight loss >0.5kg is a significant warning sign — "
                                 "kidney disease, hyperthyroidism, dental pain, or other illness. Vet check.")
                    elif change < -0.2:
                        st.warning(f"🟡 {cat} has lost {abs(change):.1f}kg. Monitor closely.")
                    elif change > 0.5:
                        st.warning(f"🟡 {cat} has gained {change:.1f}kg. Monitor for obesity risk.")
                    else:
                        st.success(f"✅ {cat}'s weight is stable.")

                if len(sorted_w) >= 2:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=[w['date'] for w in sorted_w],
                        y=[w['kg']   for w in sorted_w],
                        mode='lines+markers',
                        name='Weight (kg)',
                        line=dict(color='#2ecc71', width=2),
                        marker=dict(size=8)
                    ))
                    fig.update_layout(
                        title=f"{cat} — Weight Over Time",
                        yaxis_title="Weight (kg)",
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)

                wdf = pd.DataFrame(sorted_w)
                st.dataframe(wdf[['date','kg','source','notes']], use_container_width=True, hide_index=True)
            else:
                st.info(f"No weight records for {cat} yet. Log one above.")

            # Also note weights from vet visits if any
            visit_weights = [{'date': v['date'], 'kg': v.get('weight_kg','?'),
                              'reason': v.get('reason','Vet visit')}
                             for v in vv if v.get('weight_kg')]
            if visit_weights:
                st.caption("Weights recorded at vet visits (from Cat Profiles):")
                st.dataframe(pd.DataFrame(visit_weights), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# NEW FEATURE 3: CAT JOURNAL
# ══════════════════════════════════════════════════════════════════════════════
def cat_journal_page():
    st.header("📓 Cat Journal")
    st.write(
        "A freeform daily log for observations that don't fit health entry fields. "
        "'Sonic was extra clingy today', 'Haku sneezed 10 times this afternoon', 'Kuro ignored the KitKat topper'. "
        "These small observations over time can reveal important patterns.")

    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            journal = st.session_state.cat_journal.get(cat, [])

            # ── Add entry ──
            st.subheader(f"Add a note for {cat}")
            with st.form(f"journal_form_{cat}"):
                j_date = st.date_input("Date", value=date.today(), key=f"j_date_{cat}")
                j_mood = st.selectbox("Overall feeling about today",
                                      ["😊 Good day","😐 Normal day","😟 Concerning","🤔 Something felt off","🎉 Great day!"],
                                      key=f"j_mood_{cat}")
                j_text = st.text_area("Notes", height=120,
                                      placeholder="Write anything you noticed — behaviour, eating habits, interactions with other cats, anything unusual or cute...",
                                      key=f"j_text_{cat}")
                j_tags = st.multiselect("Tags (optional)",
                                        ["sneezing","eye discharge","lethargy","not eating","extra playful",
                                         "hiding","vomited","litter issue","groomed","cuddly","aggressive",
                                         "breathing","lost weight","gained weight"],
                                        key=f"j_tags_{cat}")
                if st.form_submit_button("💾 Save Note", type="primary"):
                    if j_text.strip():
                        st.session_state.cat_journal.setdefault(cat, [])
                        st.session_state.cat_journal[cat].append({
                            'date':  str(j_date),
                            'mood':  j_mood,
                            'text':  j_text.strip(),
                            'tags':  j_tags
                        })
                        save_data(); st.success("✅ Note saved!"); st.rerun()
                    else:
                        st.warning("Please write something before saving.")

            st.markdown("---")

            # ── Filter and view ──
            if journal:
                st.subheader(f"📋 {cat}'s Journal")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filter_tag = st.selectbox("Filter by tag", ["All"]+
                                              ["sneezing","eye discharge","lethargy","not eating","extra playful",
                                               "hiding","vomited","litter issue","groomed","cuddly","aggressive",
                                               "breathing","lost weight","gained weight"],
                                              key=f"j_filter_{cat}")
                with col_f2:
                    search_j = st.text_input("Search notes", key=f"j_search_{cat}", placeholder="e.g., sneeze, KitKat")

                # Pattern detection on journal
                concern_tags = {"sneezing","eye discharge","lethargy","not eating","hiding","vomited","litter issue","breathing"}
                recent_concern = [e for e in journal[-7:] if any(t in concern_tags for t in e.get('tags',[]))]
                if len(recent_concern) >= 3:
                    st.warning(f"⚠️ **Pattern detected:** {cat} has had {len(recent_concern)} entries with concerning tags in the past 7 journal entries. Review entries below and consider a vet check.")

                filtered = journal
                if filter_tag != "All":
                    filtered = [e for e in filtered if filter_tag in e.get('tags',[])]
                if search_j:
                    sl = search_j.lower()
                    filtered = [e for e in filtered if sl in e.get('text','').lower()]

                for entry in sorted(filtered, key=lambda x: x.get('date',''), reverse=True):
                    with st.container():
                        col1, col2 = st.columns([4,1])
                        with col1:
                            st.markdown(f"**{entry['date']}** — {entry['mood']}")
                            if entry.get('tags'):
                                st.caption("Tags: " + " · ".join(entry['tags']))
                            st.write(entry['text'])
                        with col2:
                            idx = journal.index(entry)
                            if st.button("🗑️", key=f"del_journal_{cat}_{idx}"):
                                st.session_state.cat_journal[cat].pop(idx)
                                save_data(); st.rerun()
                        st.markdown("---")
            else:
                st.info(f"No journal entries for {cat} yet.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CAT HEALTH GUIDE
# ══════════════════════════════════════════════════════════════════════════════
def cat_health_guide_page():
    st.header("🏥 Cat Health Guide")

    # Data analysis from logs
    st.subheader("📊 Current Status vs Normal Ranges")
    st.caption("Based on their health entries from the past 7 days.")
    today    = date.today()
    week_ago = today - timedelta(days=7)

    for cat in st.session_state.cats:
        a = analyze_cat_health(cat)
        if a['status'] == 'no_data':
            st.info(f"**{cat}:** No data logged yet."); continue
        mr = a.get('metric_ratings', {})
        st.markdown(f"**🐱 {cat}** — {a['total_days']} days tracked")
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            w = mr.get('water',{})
            st.metric(f"Water {w.get('icon','')}", f"{a['water_avg']:.1f}/day",
                      help=f"Normal: 3-8/day | Status: {w.get('status','')}")
        with c2:
            f = mr.get('food',{})
            st.metric(f"Food {f.get('icon','')}", f"{a['food_avg']:.1f}/day",
                      help=f"Normal: 3-5/day | Status: {f.get('status','')}")
        with c3:
            l = mr.get('litter',{})
            st.metric(f"Litter {l.get('icon','')}", f"{a['litter_avg']:.1f}/day",
                      help=f"Normal: 2-4/day | Status: {l.get('status','')}")
        with c4:
            st.metric(f"Mood {a.get('mood_icon','')}", a.get('mood_trend','—').title())
        with c5:
            # Latest breathing if available
            bl = st.session_state.breathing_logs.get(cat, [])
            sleeping_bl = [e for e in bl if e.get('context')=='Sleeping']
            if sleeping_bl:
                last_bpm = sorted(sleeping_bl, key=lambda x: x.get('date',''))[-1]['bpm']
                bpm_icon = "🟢" if last_bpm <= 25 else "🟡" if last_bpm <= 30 else "🔴"
                st.metric(f"Breathing {bpm_icon}", f"{last_bpm} bpm", help="Normal: 15-30 bpm while sleeping")
            else:
                st.metric("Breathing", "No data", help="Log in Breathing Tracker")
        if a['concerns']:
            for _, cr in a['concerns']:
                st.warning(f"⚠️ **{cat}:** {cr['msg'][:150]}...")
        if a.get('patterns'):
            for p in a['patterns']: st.error(p)
    st.markdown("---")

    # Visual guides
    with st.expander("💩 Poop Guide — Normal vs Abnormal", expanded=False):
        st.success("**✅ Normal:** Log-shaped · Medium to dark brown · Firm · Once per 24-36 hrs · Mild smell")
        c1,c2 = st.columns(2)
        with c1:
            st.error("**Liquid/watery (diarrhoea):** Infection, parasites, food intolerance, stress, IBD. >24 hrs or blood = vet.")
            st.error("**Bright red blood:** Fresh lower GI bleed. Recurring = vet.")
            st.error("**Black tarry:** Digested blood — upper GI bleed. Vet same day.")
        with c2:
            st.warning("**Mucus coating:** Large amounts = colitis or IBD.")
            st.warning("**Hard dry pellets:** Constipation — increase wet food and water.")
            st.warning("**Yellow or pale:** Food moving too fast or liver issue. Monitor.")

    with st.expander("🚽 Urine Guide — Normal vs Abnormal", expanded=False):
        st.success("**✅ Normal:** Pale to medium yellow · Clear · Mild ammonia smell · 2-4 trips/day · Decent puddle each time")
        c1,c2 = st.columns(2)
        with c1:
            st.error("**Pink/red/orange:** Blood in urine. If straining = EMERGENCY NOW.")
            st.error("**No urine + straining:** Blockage — fatal within 24-48 hrs. Emergency vet.")
            st.warning("**Cloudy/milky:** Infection or crystals. Vet within 48 hrs.")
        with c2:
            st.warning("**Very dark + strong smell:** Dehydration. Increase water and wet food urgently.")
            st.warning("**Very pale + high volume:** Possible diabetes or kidney disease. Blood test needed.")
            st.warning("**Tiny drops, many trips:** Partial blockage or UTI. Vet same day.")

    with st.expander("🤮 Vomit Colour Guide", expanded=False):
        c1,c2 = st.columns(2)
        with c1:
            st.info("**Clear/foamy white:** Empty stomach. Add meal before bed if happening daily.")
            st.info("**Yellow/green (bile):** Empty stomach too long. Increase meal frequency.")
            st.success("**Brown with food chunks:** Ate too fast. Try puzzle feeder.")
            st.warning("**Brown liquid:** Old blood or bile. Coffee-ground texture = upper GI bleed. Vet today.")
        with c2:
            st.error("**Bright red:** Fresh blood. More than a tiny streak = vet immediately.")
            st.error("**Dark red/black:** Digested blood. Urgent.")
            st.warning("**Green:** Ate grass or bile. Single episode usually fine.")
            st.warning("**White foamy, recurring:** GI issue if no hairball. Monitor.")
        st.error("Vet NOW if: Any blood · >2-3 times/day · With lethargy or not eating · With diarrhoea · Possible foreign object")

    # Conditions
    diseases = [
        {"name":"Feline Herpesvirus (FHV-1) — Haku","icon":"🦠","who":"Haku has this. Lifelong — reactivates with stress.",
         "signs":["Sneezing — mild or severe during flares","Eye discharge — watery to thick","Conjunctivitis — red swollen eyes","Nasal discharge","Loss of appetite (can't smell)","Corneal ulcers — squinting/pawing eye","Triggers: stress, vet visits, illness, routine changes"],
         "prevention":["Minimize stress — routine consistency is #1","L-Lysine supplement — ask vet","Keep eye area clean","FVRCP vaccine reduces severity","Air purifier ✅"],"urgency":"🟠 Lifelong. Corneal ulcers = urgent vet."},
        {"name":"Kidney Disease (CKD)","icon":"🫘","who":"All three on kidney watch. Key monitoring priority.",
         "signs":["Increased thirst — drinking more","Increased urination — larger litter clumps","Weight loss despite eating","Ammonia/metallic bad breath","Morning vomiting on empty stomach","Lethargy, hiding","Rough unkempt coat","Muscle wasting over spine"],
         "prevention":["Wet food as main diet — #1 kidney protector","Fresh water always available","Annual bloodwork ✅","Low phosphorus diet — Pro Plan Wet preferred","Log daily water + litter — changes are early indicators"],"urgency":"🟠 Silent early on. Annual bloodwork + daily logging = best early detection."},
        {"name":"Urinary Tract Infection / FLUTD","icon":"🚽","who":"Any cat — males especially (blockage risk)",
         "signs":["Straining with little/no urine","Crying while urinating","Blood in urine","Urinating outside litter box","Excessive genital licking","Many litter trips with no result"],
         "prevention":["Fresh water — fountain preferred","Wet food as main diet","Clean litter box daily","Reduce stress — FIC is stress-triggered"],"urgency":"🔴 Emergency if producing no urine — fatal within 24-48 hrs"},
        {"name":"Heart Disease (HCM)","icon":"❤️","who":"All three — 4-monthly vet visits include cardiac monitoring",
         "signs":["Rapid/laboured breathing at rest",">30 breaths/min while sleeping","Sudden hind leg paralysis (EMERGENCY)","Fluid in chest causing breathing difficulty","Often NO early symptoms — only detectable by vet"],
         "prevention":["4-monthly vet visits ✅","Echocardiogram if murmur detected","Taurine-adequate diet ✅","Count resting breathing rate at home — normal <30/min","Log in Breathing Tracker page"],"urgency":"🔴 Hind leg paralysis or open-mouth breathing = emergency NOW"},
        {"name":"Feline Asthma / Breathing Difficulty","icon":"💨","who":"You use a nebulizer — managing this already",
         "signs":["Hunched posture, neck extended — like trying to bring up hairball with nothing coming","Wheezing","Faster breathing at rest","Coughing that sounds like retching"],
         "prevention":["No aerosol sprays near cats","Unscented litter","Air purifier ✅","Consistent nebulizer protocol"],"urgency":"🟠 Acute attacks = emergency. Open-mouth breathing or blue gums = immediate vet."},
        {"name":"Mold / Environmental Toxins","icon":"🍄","who":"Indoor cats in any home with dampness or poor ventilation",
         "signs":["Sneezing/coughing that started after cleaning/furniture moving","Multiple cats with similar symptoms simultaneously","Eye and nose irritation without obvious cause","Breathing changes linked to specific rooms"],
         "prevention":["Air purifier ✅","Check under sinks, bathroom corners, behind appliances","Replace purifier filters monthly ✅","Good ventilation — open windows regularly","No aerosol cleaners or scented candles near cats"],"urgency":"🟡 Chronic exposure causes respiratory and immune issues over time."},
        {"name":"Stress / Anxiety (FIC)","icon":"😰","who":"All three — indoor, multi-cat, routine-sensitive",
         "signs":["Hiding more than usual","Overgrooming — licking until bald patches","Inter-cat aggression","Litter box avoidance","Stress-triggered UTI symptoms"],
         "prevention":["Consistent routine","Vertical space and hiding spots","One litter box per cat + one extra","Daily play ✅","Feliway diffuser if tension increases"],"urgency":"🟡 Chronic stress causes real physical disease — FLUTD, reduced immunity."},
        {"name":"Red / Inflamed Gums (Stomatitis)","icon":"🦷","who":"Any cat — 70% of cats over age 3 have dental disease",
         "signs":["Bright red/purple gum line","Reluctance to eat or dropping food","Drooling (sometimes bloody)","Pawing at mouth","Strong bad breath"],
         "prevention":["Annual dental check ✅","Brush teeth 2-3x per week","Dental treats and water additives"],"urgency":"🟠 Not eating due to mouth pain = vet within 24-48 hrs."},
        {"name":"Intestinal Parasites","icon":"🐛","who":"All cats — on deworming schedule",
         "signs":["Visible worm segments in stool","Bloated belly","Weight loss despite eating","Scooting","Vomiting/diarrhoea"],
         "prevention":["Haku/Sonic: every 3 months (next: 26-Jul-2026)","Kuro: every 4 months (next: 26-Aug-2026)","Monthly flea prevention — fleas carry tapeworms"],"urgency":"🟡 Follow schedule — worsens without treatment."},
        {"name":"Fleas","icon":"🦟","who":"Any cat — even indoor-only",
         "signs":["Scratching neck and tail base","Black specks in fur (flea dirt)","Red bumps, hair loss from scratching"],
         "prevention":["Monthly flea prevention","Wash bedding monthly ✅","Treat all cats simultaneously"],"urgency":"🟡 Carries tapeworms — treat promptly."},
        {"name":"Ear Mites","icon":"👂","who":"Any cat",
         "signs":["Head shaking and ear scratching","Dark coffee-ground discharge in ears","Smell from ears"],
         "prevention":["Monthly ear checks during grooming ✅","Treat all cats together if one has mites"],"urgency":"🟠 Very uncomfortable — secondary infections develop if untreated."},
        {"name":"Obesity","icon":"⚖️","who":"Indoor/neutered cats",
         "signs":["Cannot feel ribs without pressing hard","Hanging belly when walking","Reluctant to play or groom lower back"],
         "prevention":["Measure portions — 3 meals/day ✅","Wet food: fewer calories per gram than dry","Daily play ✅","Puzzle feeders slow eating"],"urgency":"🟡 Slow damage — diabetes, joint disease, heart disease, shorter lifespan."},
    ]

    st.markdown("---")
    uf = st.selectbox("Filter by urgency", ["All","🔴 Emergency","🟠 See vet soon","🟡 Monitor"])
    search = st.text_input("🔍 Search", placeholder="e.g., sneezing, kidney, breathing")

    def ulvl(u):
        if "🔴" in u: return "🔴 Emergency"
        if "🟠" in u: return "🟠 See vet soon"
        return "🟡 Monitor"

    filtered = diseases
    if uf != "All": filtered = [d for d in filtered if ulvl(d["urgency"]) == uf]
    if search:
        sl = search.lower()
        filtered = [d for d in filtered
                    if sl in d["name"].lower()
                    or any(sl in s.lower() for s in d["signs"])
                    or any(sl in p.lower() for p in d["prevention"])]
    if not filtered: st.info("No conditions match."); return

    st.write(f"Showing **{len(filtered)}** of {len(diseases)} conditions")
    for dis in filtered:
        with st.expander(f"{dis['icon']} {dis['name']}", expanded=False):
            c1,c2 = st.columns(2)
            with c1:
                st.markdown(f"**👥 Who:** {dis['who']}")
                st.markdown("**🚨 Signs:**")
                for s in dis["signs"]: st.write(f"- {s}")
            with c2:
                st.markdown("**✅ Prevention:**")
                for p in dis["prevention"]: st.write(f"- {p}")
            u = dis["urgency"]
            if "🔴" in u:   st.error(u)
            elif "🟠" in u: st.warning(u)
            else:            st.info(u)

    # Symptom checker
    st.markdown("---")
    st.subheader("🔍 Symptom Checker")
    symptom_map = {
        "Not eating":                          ["Feline Herpesvirus","Red / Inflamed Gums","Heart Disease","Kidney Disease","Urinary Tract Infection"],
        "Vomiting":                            ["Intestinal Parasites","Kidney Disease","Feline Asthma"],
        "Diarrhoea":                           ["Intestinal Parasites","Stress / Anxiety"],
        "Straining to urinate / no urine":     ["Urinary Tract Infection"],
        "Blood in urine":                      ["Urinary Tract Infection","Kidney Disease"],
        "Increased thirst":                    ["Kidney Disease"],
        "Open-mouth breathing":                ["Feline Asthma","Heart Disease"],
        "Breathing >30 bpm at rest":           ["Feline Asthma","Heart Disease"],
        "Hind leg weakness/paralysis":         ["Heart Disease"],
        "Sneezing / eye discharge":            ["Feline Herpesvirus"],
        "Red inflamed gums":                   ["Red / Inflamed Gums"],
        "Hiding / lethargy":                   ["Stress / Anxiety","Kidney Disease","Heart Disease"],
        "Hair loss / overgrooming":            ["Stress / Anxiety","Fleas"],
        "Scratching ears":                     ["Ear Mites"],
        "Weight loss despite eating":          ["Intestinal Parasites","Kidney Disease"],
        "Sneezing after room changes":         ["Mold / Environmental Toxins"],
        "Multiple cats sneezing at same time": ["Mold / Environmental Toxins"],
        "Scooting on floor":                   ["Intestinal Parasites"],
        "Litter box avoidance":                ["Urinary Tract Infection","Stress / Anxiety"],
    }
    selected = []
    cols = st.columns(2)
    for i2, sym in enumerate(symptom_map):
        with cols[i2 % 2]:
            if st.checkbox(sym, key=f"sym_{i2}"): selected.append(sym)

    if selected:
        st.markdown("---"); st.markdown("**Possible conditions:**")
        scores = {}
        for sym in selected:
            for dn in symptom_map.get(sym, []):
                scores[dn] = scores.get(dn, 0) + 1
        for dn, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            md = next((d for d in diseases if any(p.strip().lower() in d["name"].lower()
                       for p in dn.split("/"))), None)
            if md:
                u   = md["urgency"]
                msg = f"**{md['icon']} {md['name']}** — {sc} symptom(s) match · {u}"
                if "🔴" in u:   st.error(msg)
                elif "🟠" in u: st.warning(msg)
                else:            st.info(msg)
        st.caption("Reference only — always consult your vet for diagnosis.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def dashboard_page():
    st.header("🎯 Dashboard")
    today    = date.today()
    weekday  = today.weekday()
    is_thu   = weekday == 3
    is_fri   = weekday == 4
    is_first = today.day == 1

    # Vet reminders
    reminders = get_vet_reminders()
    urgent    = [r for r in reminders if r['days_away'] is not None and (r['overdue'] or r['days_away'] <= 30)]
    not_set   = [r for r in reminders if r['next_date'] in ('Not set','Invalid')]
    if urgent or not_set:
        st.subheader("📅 Vet Appointment Reminders")
        for r in urgent:
            if r['overdue']:
                st.error(f"🔴 **{r['cat']}** — {r['label']}: **{abs(r['days_away'])} days overdue!** (was due {r['next_date']})")
            elif r['days_away'] <= 7:
                st.error(f"🟠 **{r['cat']}** — {r['label']} in **{r['days_away']} days** ({r['next_date']})")
            elif r['days_away'] <= 14:
                st.warning(f"🟡 **{r['cat']}** — {r['label']} in {r['days_away']} days ({r['next_date']})")
            else:
                st.info(f"🟢 **{r['cat']}** — {r['label']} in {r['days_away']} days ({r['next_date']})")
        for r in not_set:
            st.warning(f"⚠️ **{r['cat']}** — {r['label']}: not set. Update in Cat Profiles.")
        st.markdown("---")

    # Weekly task reminder
    week_start = today - timedelta(days=weekday)
    week_end   = week_start + timedelta(days=6)
    wc         = get_task_completions(week_start, week_end)
    done_week  = set(l['task'] for logs in wc.values() for l in logs
                     if l['task'] in st.session_state.tasks.get('weekly',[]))
    pending_w  = [t for t in st.session_state.tasks.get('weekly',[]) if t not in done_week]
    if (is_thu or is_fri) and pending_w:
        st.warning(f"🗓️ **{'Thu' if is_thu else 'Fri'} — Weekly tasks pending:** {', '.join(pending_w)}")
    elif (is_thu or is_fri) and not pending_w:
        st.success("✅ All weekly tasks done!")
    if is_thu or is_fri: st.markdown("---")

    # Monthly task reminder
    mstart = date(today.year, today.month, 1)
    mend   = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    mc     = get_task_completions(mstart, mend)
    done_m = set(l['task'] for logs in mc.values() for l in logs
                 if l['task'] in st.session_state.tasks.get('monthly',[]))
    pend_m = [t for t in st.session_state.tasks.get('monthly',[]) if t not in done_m]
    if is_first and pend_m:
        st.warning(f"📆 **First of the month — {len(pend_m)} monthly tasks due:** {', '.join(pend_m[:4])}"
                   + (" ..." if len(pend_m) > 4 else ""))
        st.markdown("---")

    # Active medicines
    active_meds = get_active_medications_today()
    if active_meds:
        st.subheader("💊 Active Medicines / Treatments Today")
        for m in active_meds:
            dl   = m['days_left']
            urg  = "🔴" if dl == 0 else "🟠" if dl <= 2 else "🟢"
            note = "**Last dose today!**" if dl==0 else f"**{dl} day(s) left**" if dl<=2 else f"{dl} days left"
            st.info(f"{urg} **{m['cat']}** — **{m['name']}** [{m['type']}]"
                    + (f" ({m['dosage']})" if m['dosage'] else "")
                    + (f" · {m['frequency']}" if m['frequency'] else "")
                    + f" · Until {m['end_date']} · {note}")
        st.markdown("---")

    # Breathing alerts
    any_breathing_alert = False
    for cat in st.session_state.cats:
        bl = [e for e in st.session_state.breathing_logs.get(cat,[]) if e.get('context')=='Sleeping']
        if bl:
            last = sorted(bl, key=lambda x: x.get('date',''))[-1]
            if last['bpm'] > 30:
                st.error(f"🔴 **{cat} breathing alert:** Last resting reading was {last['bpm']} bpm (normal: ≤30). Contact vet.")
                any_breathing_alert = True
    if any_breathing_alert: st.markdown("---")

    # Quick stats
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        te = sum(len(v) for cd in st.session_state.health_data.values() for v in cd.values())
        st.metric("Total Entries", te)
    with c2:
        ts_  = str(today)
        tsk  = [l['task'] for l in st.session_state.task_logs.get(ts_, [])]
        st.metric("Today's Tasks", f"{len(tsk)}/{len(st.session_state.tasks.get('daily',[]))}")
    with c3:
        st.metric("Vet Visits", sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))
    with c4:
        ac = sum(1 for c in st.session_state.cats
                 if c in st.session_state.health_data and st.session_state.health_data[c])
        st.metric("Active Cats", f"{ac}/{len(st.session_state.cats)}")

    # At-a-glance summary
    st.markdown("---")
    st.subheader("📋 This Week at a Glance")
    week_ago = today - timedelta(days=7)
    comp_rows, concerns_summary, patterns_all = [], [], []

    for cat in st.session_state.cats:
        a  = analyze_cat_health(cat)
        mr = a.get('metric_ratings', {})
        if a['status'] == 'no_data':
            comp_rows.append({'Cat': cat, 'Status': '⬜ No data',
                              'Water': '—', 'Food': '—', 'Litter': '—', 'Mood': '—', 'Poop': '—', 'Breathing': '—'})
        else:
            # Breathing
            bl = [e for e in st.session_state.breathing_logs.get(cat,[]) if e.get('context')=='Sleeping']
            last_bpm = sorted(bl, key=lambda x: x.get('date',''))[-1]['bpm'] if bl else None
            bpm_str  = f"{'🔴' if last_bpm and last_bpm>30 else '🟢'} {last_bpm}bpm" if last_bpm else "—"

            comp_rows.append({
                'Cat':       cat,
                'Status':    '✅ Healthy' if not a['concerns'] else f"⚠️ {len(a['concerns'])} concern(s)",
                'Water':     f"{mr.get('water',{}).get('icon','')} {a['water_avg']:.1f}/day",
                'Food':      f"{mr.get('food',{}).get('icon','')} {a['food_avg']:.1f}/day",
                'Litter':    f"{mr.get('litter',{}).get('icon','')} {a['litter_avg']:.1f}/day",
                'Mood':      f"{a.get('mood_icon','')} {a.get('mood_trend','').title()}",
                'Poop':      f"{a.get('poop_icon','')} {a.get('poop_days',0)}/{a['total_days']}d",
                'Breathing': bpm_str
            })
            if a['concerns']:
                concerns_summary.append((cat, a['concerns']))
            if a.get('patterns'):
                patterns_all.extend(a['patterns'])

    st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

    if patterns_all:
        st.markdown("**🔍 Detected patterns:**")
        for p in patterns_all: st.error(p)
    if concerns_summary:
        st.markdown("**⚠️ Active concerns:**")
        for cat, concerns in concerns_summary:
            for _, cr in concerns:
                st.warning(f"**{cat}:** {cr['msg'][:180]}...")
    elif not patterns_all:
        st.success("✅ All three cats look healthy based on this week's logged data!")

    # Chart
    st.markdown("---")
    st.subheader("📊 Weekly Comparison")
    cdata = []
    for cat in st.session_state.cats:
        daily = get_daily_aggregated(cat, week_ago, today)
        if daily:
            cdata.append({'Cat': cat,
                          'Avg Water': round(sum(d['water_drinks']     for d in daily.values())/len(daily),1),
                          'Avg Food':  round(sum(d['food_eats']        for d in daily.values())/len(daily),1),
                          'Avg Litter':round(sum(d['litter_box_times'] for d in daily.values())/len(daily),1)})
    if cdata:
        cdf = pd.DataFrame(cdata)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Water',  x=cdf['Cat'], y=cdf['Avg Water'],  marker_color='#4fc3f7'))
        fig.add_trace(go.Bar(name='Food',   x=cdf['Cat'], y=cdf['Avg Food'],   marker_color='#81c784'))
        fig.add_trace(go.Bar(name='Litter', x=cdf['Cat'], y=cdf['Avg Litter'], marker_color='#ffb74d'))
        fig.add_hline(y=3, line_dash="dot", line_color="#4fc3f7", opacity=0.4, annotation_text="Water min ideal")
        fig.add_hline(y=2, line_dash="dot", line_color="#ffb74d", opacity=0.4, annotation_text="Litter min ideal")
        fig.update_layout(barmode='group', height=300, margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Dotted lines = minimum ideal values.")

    # PDF
    st.markdown("---")
    st.subheader("📄 Export Vet Report")
    c1,c2 = st.columns(2)
    with c1: pdf_cat = st.selectbox("Report for", ["All Cats"]+st.session_state.cats)
    with c2:
        st.write(""); st.write("")
        if REPORTLAB_AVAILABLE:
            pdf_bytes = generate_pdf_report(None if pdf_cat=="All Cats" else pdf_cat)
            st.download_button("📥 Download PDF", data=pdf_bytes,
                               file_name=f"cat_report_{today}.pdf",
                               mime="application/pdf", type="primary", use_container_width=True)
        else: st.warning("Install: pip install reportlab")

    # Per-cat in-depth
    st.markdown("---")
    st.subheader("🔬 In-Depth Analysis — Per Cat")
    st.caption("Each metric rated against normal ranges with explanations.")
    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            a = analyze_cat_health(cat)
            if a['status'] == 'no_data':
                st.info(f"No data logged yet for {cat}."); continue

            profile = a.get('profile', {})
            info = []
            if profile.get('age'):    info.append(f"Age: {profile['age']}")
            if profile.get('breed'):  info.append(f"Breed: {profile['breed']}")
            if profile.get('weight'): info.append(f"Weight: {profile['weight']} kg")
            if info: st.markdown(" · ".join(info))
            st.markdown(f"**{a['total_days']} days tracked · {a['total_entries']} total entries**")

            mr = a.get('metric_ratings', {})
            st.markdown("---")

            for key, rng_key, label in [
                ('water',  'water_drinks',     '💧 Water Intake'),
                ('food',   'food_eats',        '🍽️ Food Intake'),
                ('litter', 'litter_box_times', '🚽 Litter Box Usage'),
            ]:
                m = mr.get(key, {})
                st.markdown(f"**{m.get('icon','')} {label}**")
                col1,col2 = st.columns([1,2])
                with col1:
                    st.metric("Current avg", f"{m.get('avg',0):.1f}/day")
                    st.write(f"Ideal: {m.get('ideal','—')}  \nOk: {m.get('ok','—')}")
                with col2:
                    st.write(m.get('msg',''))
                st.markdown("")

            st.markdown(f"**{a.get('mood_icon','')} Mood**")
            st.write(a.get('mood_msg',''))
            st.markdown(f"**{a.get('poop_icon','')} Bowel Movements**")
            st.write(a.get('poop_msg',''))

            if a.get('patterns'):
                st.markdown("---")
                for p in a['patterns']: st.error(p)

            if a.get('litter_issues'):
                st.markdown("---")
                st.markdown("**🚨 Litter Quality Alerts:**")
                for dd, iss in a['litter_issues'][:5]: st.error(f"- {dd}: {iss}")

            meds = [m for m in get_active_medications_today() if m['cat'] == cat]
            if meds:
                st.markdown("---")
                st.markdown("**💊 Active Medicines:**")
                for m in meds:
                    st.info(f"{m['name']} [{m['type']}]"
                            + (f" — {m['dosage']}" if m['dosage'] else "")
                            + f" · until {m['end_date']} · {m['days_left']} days left")

            if a['daily']:
                st.markdown("---")
                st.markdown("**📅 Day-by-day (past 7 days):**")
                for dd in sorted(a['daily'].keys(), reverse=True):
                    d = a['daily'][dd]
                    pts = []
                    if d['water_drinks']:     pts.append(f"💧{d['water_drinks']}x")
                    if d['food_eats']:        pts.append(f"🍽️{d['food_eats']}x")
                    if d['litter_box_times']: pts.append(f"🚽{d['litter_box_times']}x")
                    if d['pooped']:           pts.append("💩✅")
                    if d['grooming_tasks']:   pts.append(f"🪥{', '.join(d['grooming_tasks'])}")
                    if d['food_log']:         pts.append(f"🥣{', '.join(set(d['food_log']))}")
                    lbl = f"({d['entry_count']} {'entry' if d['entry_count']==1 else 'entries'})"
                    st.write(f"**{dd}** {lbl}: {' · '.join(pts) if pts else 'Nothing logged'}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DATA MANAGEMENT  (now includes backup/restore)
# ══════════════════════════════════════════════════════════════════════════════
def data_management_page():
    st.header("⚙️ Data Management")

    # ── BACKUP / RESTORE (the persistence fix) ──
    st.subheader("💾 Backup & Restore — IMPORTANT")
    st.info(
        "**Why this matters:** Streamlit Cloud resets its file system on every server restart or redeploy. "
        "Download a backup regularly and re-upload it after any restart to restore your data. "
        "**Tip:** Download a backup after every session.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📥 Download full backup**")
        bundle_bytes = json.dumps(_get_full_bundle(), default=str, indent=2).encode()
        st.download_button(
            "⬇️ Download Backup Bundle",
            data=bundle_bytes,
            file_name=f"cattracker_backup_{date.today()}.json",
            mime="application/json",
            type="primary",
            use_container_width=True
        )
        st.caption("Download this after every session. Keep it somewhere safe.")

    with c2:
        st.markdown("**📤 Restore from backup**")
        uploaded = st.file_uploader("Upload a backup bundle (.json)", type=['json'], key="restore_upload")
        if uploaded:
            try:
                bundle = json.loads(uploaded.read().decode())
                if 'health_data' in bundle or 'cat_profiles' in bundle:
                    if st.button("✅ Confirm Restore", type="primary", use_container_width=True):
                        restore_from_bundle(bundle)
                        st.success("✅ Data restored successfully!")
                        st.rerun()
                else:
                    st.error("This doesn't look like a valid backup file.")
            except Exception as e:
                st.error(f"Failed to read backup: {e}")

    st.markdown("---")
    st.warning("⚠️ Actions below permanently delete data.")

    st.subheader("📥 Export Individual Files")
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("Export Health Data", use_container_width=True):
            st.download_button("💾 Download", data=json.dumps(st.session_state.health_data, indent=2, default=str),
                               file_name=f"health_data_{date.today()}.json", mime="application/json")
    with c2:
        if st.button("Export Task Logs", use_container_width=True):
            st.download_button("💾 Download", data=json.dumps(st.session_state.task_logs, indent=2, default=str),
                               file_name=f"task_logs_{date.today()}.json", mime="application/json")
    with c3:
        if st.button("Export Profiles", use_container_width=True):
            st.download_button("💾 Download", data=json.dumps(st.session_state.cat_profiles, indent=2, default=str),
                               file_name=f"profiles_{date.today()}.json", mime="application/json")

    st.markdown("---")
    st.subheader("🗑️ Delete")
    c1,c2 = st.columns(2)
    with c1:
        ctd = st.selectbox("Cat to delete health data for:", [""]+st.session_state.cats, key="del_cat_h")
        if ctd and st.button(f"Delete {ctd}'s health data", type="secondary"):
            if ctd in st.session_state.health_data:
                del st.session_state.health_data[ctd]
                save_data(); st.success("Deleted!"); st.rerun()
    with c2:
        ds1 = st.date_input("Task logs start", key="del_ts")
        ds2 = st.date_input("Task logs end",   key="del_te")
        if st.button("Delete task logs in range", type="secondary"):
            cur, n = ds1, 0
            while cur <= ds2:
                if str(cur) in st.session_state.task_logs:
                    del st.session_state.task_logs[str(cur)]; n+=1
                cur += timedelta(days=1)
            save_data(); st.success(f"Deleted {n} days"); st.rerun()

    st.markdown("---")
    st.error("**DANGER ZONE**")
    conf = st.checkbox("I understand this is permanent", key="conf_del")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Delete ALL health data", type="secondary", disabled=not conf):
            st.session_state.health_data  = {}
            st.session_state.last_entries = {c: None for c in st.session_state.cats}
            save_data(); st.success("Deleted!"); st.rerun()
    with c2:
        if st.button("Delete ALL task logs", type="secondary", disabled=not conf):
            st.session_state.task_logs = {}
            save_data(); st.success("Deleted!"); st.rerun()

    st.markdown("---")
    conf2 = st.checkbox("Reset EVERYTHING", key="conf_reset")
    if st.button("🔄 RESET EVERYTHING", type="secondary", disabled=not conf2):
        st.session_state.health_data   = {}
        st.session_state.task_logs     = {}
        st.session_state.cat_profiles  = {
            cat: {'age':'','breed':'','weight':'','vet_visits':[],'notes':'',
                  'birthdate':'', **DEFAULT_VET_SCHEDULE[cat]}
            for cat in ['Haku','Kuro','Sonic']
        }
        st.session_state.diet_settings = {
            c: {'meals_per_day':3,'notes':'',
                'active_foods':['Pro Plan Adult Wet','KitKat Topper',
                                'Unseasoned Boiled Chicken','Freeze-Dried Treats']}
            for c in st.session_state.cats
        }
        st.session_state.food_library  = [dict(f) for f in DEFAULT_FOOD_LIBRARY]
        st.session_state.breathing_logs= {cat: [] for cat in st.session_state.cats}
        st.session_state.cat_journal   = {cat: [] for cat in st.session_state.cats}
        st.session_state.last_entries  = {c: None for c in st.session_state.cats}
        st.session_state.data_loaded   = False
        for f in ['health_data.json','task_logs.json','cat_profiles.json',
                  'diet_settings.json','food_library.json',
                  'breathing_logs.json','cat_journal.json','backup_bundle.json']:
            try:
                path = _data_path(f)
                if os.path.exists(path): os.remove(path)
            except: pass
        st.success("Reset complete!"); time.sleep(1); st.rerun()

    st.markdown("---")
    st.subheader("📊 Stats")
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Health Entries",   sum(len(v) for cd in st.session_state.health_data.values() for v in cd.values()))
    with c2: st.metric("Task Completions", sum(len(l) for l in st.session_state.task_logs.values()))
    with c3: st.metric("Vet Visits",       sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))
    st.caption(f"Data stored in: {DATA_DIR}")


# ══════════════════════════════════════════════════════════════════════════════
# REMINDERS
# ══════════════════════════════════════════════════════════════════════════════
def check_reminders():
    now = datetime.now()
    if (st.session_state.last_reminder is None or
            (now - st.session_state.last_reminder).days >= 1):
        missing = [c for c in st.session_state.cats
                   if (st.session_state.last_entries.get(c) is None or
                       (now - st.session_state.last_entries[c]).days >= 1)]
        if missing: st.warning(f"⚠️ No health entries today for: {', '.join(missing)}")

        ts_  = str(date.today())
        done = [l['task'] for l in st.session_state.task_logs.get(ts_, [])]
        inc  = [t for t in st.session_state.tasks.get('daily',[]) if t not in done]
        if inc: st.info(f"📝 Incomplete daily tasks: {', '.join(inc)}")

        if date.today().weekday() in [3,4]:
            st.info("🪥 Thursday/Friday — grooming day! Log in Add Health Entry.")

        st.session_state.last_reminder = now


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if AUTH_ENABLED:
        if not check_authentication():
            login_page(); return

    st.set_page_config(page_title="Cat Health Tracker",
                       page_icon="🐱", layout="wide",
                       initial_sidebar_state="expanded")

    init_session_state()
    load_data()

    st.title("🐱 Cat Health Tracker — Haku · Kuro · Sonic")

    if AUTH_ENABLED:
        c1,c2 = st.columns([5,1])
        with c1: st.write("Comprehensive health, diet and care management")
        with c2:
            st.write(f"👤 {st.session_state.get('username','User')}")
            if st.button("🚪 Logout", key="logout_btn"): logout()
    else:
        st.write("Comprehensive health, diet and care management")

    st.sidebar.title("🧭 Navigation")
    page = st.sidebar.selectbox("Go to", [
        "🎯 Dashboard",
        "🐱 Cat Profiles",
        "📝 Add Health Entry",
        "📊 View Health Data",
        "📋 Task Management",
        "🥗 Diet Planning",
        "🫁 Breathing Tracker",
        "⚖️ Weight Tracker",
        "📓 Cat Journal",
        "🏥 Cat Health Guide",
        "⚙️ Data Management"
    ])

    if AUTH_ENABLED: st.sidebar.success("🔐 Security: Enabled")
    else:            st.sidebar.warning("⚠️ Security: Disabled")

    st.sidebar.markdown("---")
    # Quick backup reminder in sidebar
    st.sidebar.markdown("### 💾 Data Backup")
    bundle_bytes = json.dumps(_get_full_bundle(), default=str, indent=2).encode()
    st.sidebar.download_button(
        "⬇️ Download Backup",
        data=bundle_bytes,
        file_name=f"cattracker_backup_{date.today()}.json",
        mime="application/json",
        use_container_width=True,
        help="Download this regularly so your data survives server restarts"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Need Help?")
    st.sidebar.markdown(
        "[Ask the AI Assistant 🤖]"
        "(https://thaura.ai/?chatId=eb1bb2bf-acf0-4f6c-99c4-660a0a4fd728)")

    check_reminders()

    if   page == "🎯 Dashboard":           dashboard_page()
    elif page == "🐱 Cat Profiles":        cat_profiles_page()
    elif page == "📝 Add Health Entry":    add_health_entry_page()
    elif page == "📊 View Health Data":    view_health_data_page()
    elif page == "📋 Task Management":     task_management_page()
    elif page == "🥗 Diet Planning":       diet_planning_page()
    elif page == "🫁 Breathing Tracker":   breathing_tracker_page()
    elif page == "⚖️ Weight Tracker":      weight_tracker_page()
    elif page == "📓 Cat Journal":         cat_journal_page()
    elif page == "🏥 Cat Health Guide":    cat_health_guide_page()
    elif page == "⚙️ Data Management":     data_management_page()


if __name__ == "__main__":
    main()
