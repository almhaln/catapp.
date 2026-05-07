"""
Cat Health Tracker — Haku · Kuro · Sonic
All analysis is data-driven from logged entries. No AI calls.
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
# VET SCHEDULE — hardcoded from known dates
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
    'Haku':  {'next_checkup':  str(_add_months(_LAST_CHECKUP,  12)),
              'next_vaccines': str(_add_months(_LAST_VACCINES, 12)),
              'next_deworming':str(_add_months(_LAST_DEWORMING, 3)),
              'next_vet_visit':str(_add_months(_LAST_VET,       4))},
    'Kuro':  {'next_checkup':  str(_add_months(_LAST_CHECKUP,  12)),
              'next_vaccines': str(_add_months(_LAST_VACCINES, 12)),
              'next_deworming':str(_add_months(_LAST_DEWORMING, 4)),
              'next_vet_visit':str(_add_months(_LAST_VET,       4))},
    'Sonic': {'next_checkup':  str(_add_months(_LAST_CHECKUP,  12)),
              'next_vaccines': str(_add_months(_LAST_VACCINES, 12)),
              'next_deworming':str(_add_months(_LAST_DEWORMING, 3)),
              'next_vet_visit':str(_add_months(_LAST_VET,       4))},
}

# ══════════════════════════════════════════════════════════════════════════════
# DEFAULT FOOD LIBRARY  (pre-loaded for Haku/Kuro/Sonic's actual foods)
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_FOOD_LIBRARY = [
    {
        "name":         "Pro Plan Adult Wet",
        "type":         "Wet",
        "protein_pct":  11.0,
        "fat_pct":       4.0,
        "fibre_pct":     1.0,
        "moisture_pct": 78.0,
        "phosphorus_pct": 0.20,
        "sodium_pct":   0.15,
        "taurine":      True,
        "calories_per_100g": 85,
        "notes": "Main wet food. High moisture = excellent kidney and urinary protection. Low phosphorus is ideal for cats on kidney watch."
    },
    {
        "name":         "Pro Plan Adult Dry",
        "type":         "Dry",
        "protein_pct":  42.0,
        "fat_pct":      16.0,
        "fibre_pct":     3.0,
        "moisture_pct": 12.0,
        "phosphorus_pct": 1.00,
        "sodium_pct":   0.49,
        "taurine":      True,
        "calories_per_100g": 375,
        "notes": "High protein, good taurine levels. Phosphorus at 1.0% — monitor for kidney cats. Always supplement with wet food and water."
    },
    {
        "name":         "Unseasoned Boiled Chicken",
        "type":         "Wet",
        "protein_pct":  31.0,
        "fat_pct":       3.5,
        "fibre_pct":     0.0,
        "moisture_pct": 65.0,
        "phosphorus_pct": 0.22,
        "sodium_pct":   0.07,
        "taurine":      False,
        "calories_per_100g": 165,
        "notes": "Excellent lean protein source. Low sodium and phosphorus. Does NOT contain taurine in significant amounts — must not replace complete food. Great as a supplement or appetite booster."
    },
    {
        "name":         "Freeze-Dried Treats",
        "type":         "Treat",
        "protein_pct":  60.0,
        "fat_pct":       8.0,
        "fibre_pct":     1.0,
        "moisture_pct":  5.0,
        "phosphorus_pct": 0.60,
        "sodium_pct":   0.30,
        "taurine":      False,
        "calories_per_100g": 350,
        "notes": "High protein but very low moisture (5%). Fine as occasional treats — keep to <10% of daily calories. Not a meal replacement. No added taurine."
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH REFERENCE RANGES
# ══════════════════════════════════════════════════════════════════════════════
HEALTH_RANGES = {
    'water_drinks': {
        'label':   'Daily Water Drinks',
        'unit':    'times/day',
        'ideal':   (3, 8),
        'ok':      (1, 10),
        'low_msg': (
            "**Too low.** Cats are naturally poor drinkers — they evolved to get moisture from prey. "
            "Chronic low intake is the #1 cause of kidney disease and urinary crystals. "
            "**Action:** Add a water fountain, increase wet food, place extra water bowls away from food bowls."),
        'high_msg': (
            "**Very high water intake.** While hydration is good, dramatically increased thirst "
            "can signal early kidney disease, diabetes, or hyperthyroidism. "
            "**Action:** Book a vet visit for blood and urine tests if this is a new change."),
        'ideal_msg': (
            "**Excellent.** Good daily hydration protects the kidneys and urinary tract, "
            "prevents crystal formation, and keeps organs functioning well. Keep it up."),
        'ok_msg': (
            "**Acceptable.** Could be higher. Aim for 3+ logged drinks/day. "
            "Add wet food and a fountain to encourage more drinking."),
    },
    'food_eats': {
        'label':   'Daily Meals',
        'unit':    'meals/day',
        'ideal':   (3, 5),
        'ok':      (2, 6),
        'low_msg': (
            "**Too low — this needs attention.** Not eating is one of the most important warning signs in cats. "
            "Within 48-72 hours of not eating, cats can develop hepatic lipidosis (fatty liver disease) "
            "which is life-threatening. **If not eating for 24+ hours: contact your vet today.**"),
        'high_msg': (
            "**High meal count.** This is only a concern if portions are also large — "
            "multiple small meals are actually ideal for cats. Monitor total calorie intake."),
        'ideal_msg': (
            "**Great.** 3-5 small meals per day perfectly matches a cat's natural hunting rhythm "
            "(cats naturally catch and eat 8-16 small prey daily). This keeps blood sugar stable, "
            "reduces hunger stress, and prevents vomiting from an empty stomach."),
        'ok_msg': (
            "**Acceptable.** 2 meals/day works but 12-hour gaps can cause morning bile vomiting. "
            "Try adding a small meal before bed if vomiting yellow bile in the morning."),
    },
    'litter_box_times': {
        'label':   'Litter Box Uses',
        'unit':    'times/day',
        'ideal':   (2, 4),
        'ok':      (1, 6),
        'low_msg': (
            "**Too low.** A cat who hasn't urinated in 24+ hours needs urgent vet attention — "
            "possible blockage, which is fatal without treatment. Also check if the box is clean."),
        'high_msg': (
            "**Frequent litter box use.** This can signal a UTI, urinary crystals, stress (FLUTD), "
            "or early kidney disease. **Watch for:** straining with no urine (emergency), blood, or crying. "
            "**Action:** Vet check within a few days unless straining — then emergency immediately."),
        'ideal_msg': (
            "**Normal range.** 2-4 litter box visits/day indicates healthy kidney function and good hydration. "
            "This is an important kidney health baseline — note if it changes significantly."),
        'ok_msg': (
            "**Borderline.** Within acceptable range but worth monitoring. "
            "Note any changes in frequency, amount, or appearance."),
    },
}

DIET_ANALYSIS_RULES = {
    'protein_pct': {
        'label': 'Protein',
        'ideal_wet': (8, 15),
        'ideal_dry': (35, 50),
        'ideal_treat': (40, 80),
        'why': (
            "Cats are obligate carnivores — protein is their primary energy source AND essential for "
            "organ function, immune system, muscle maintenance, and enzyme production. "
            "Unlike dogs, cats CANNOT reduce protein catabolism when intake drops — "
            "they will break down their own muscle tissue instead."),
        'deficiency': "Muscle wasting, poor immunity, organ damage, liver disease",
        'excess': "Generally safe in healthy cats. High protein with low water = higher urinary load — always pair with good hydration.",
    },
    'moisture_pct': {
        'label': 'Moisture',
        'ideal_wet': (70, 85),
        'ideal_dry': (8, 14),
        'ideal_treat': (0, 15),
        'why': (
            "Cats evolved in deserts and have a very low thirst drive — "
            "they are biologically designed to get 70-80% of their water from food (prey is ~70% water). "
            "Dry food at 10-12% moisture means a cat eating only dry food is chronically mildly dehydrated. "
            "This is the #1 driver of kidney disease and urinary problems in domestic cats."),
        'deficiency': "Chronic dehydration → kidney disease → urinary crystals and blockages",
        'excess': "Cannot have too much moisture — more is better for kidneys and urinary tract",
    },
    'phosphorus_pct': {
        'label': 'Phosphorus',
        'ideal_wet': (0.1, 0.4),
        'ideal_dry': (0.5, 0.9),
        'ideal_treat': (0.0, 1.0),
        'why': (
            "Phosphorus is essential for bones and energy, but excess phosphorus must be filtered by the kidneys. "
            "Over time, high-phosphorus diets damage the kidneys even in healthy cats. "
            "For cats on kidney watch, this is the MOST important dietary number to control. "
            "Phosphorus in wet food is naturally much lower than in dry food."),
        'deficiency': "Bone disease (very rare with commercial food)",
        'excess': "⚠️ KIDNEY DAMAGE — accelerates CKD progression significantly. For kidney-monitored cats: <0.5% in wet, <0.8% in dry",
    },
    'taurine': {
        'label': 'Taurine',
        'why': (
            "Cats CANNOT synthesize taurine — it must come entirely from diet. "
            "Taurine is found only in animal tissue (not plants). It is critical for: "
            "heart muscle function (deficiency causes dilated cardiomyopathy — DCM), "
            "vision (retinal degeneration without it), reproduction, and immune function. "
            "Complete commercial cat foods always supplement taurine. "
            "Home-cooked food or treats alone are NOT adequate taurine sources."),
        'deficiency': "Heart disease (DCM), blindness, reproductive failure — all irreversible without early treatment",
    },
    'fat_pct': {
        'label': 'Fat',
        'ideal_wet': (3, 8),
        'ideal_dry': (10, 20),
        'ideal_treat': (5, 20),
        'why': (
            "Fat is a concentrated energy source and carries fat-soluble vitamins (A, D, E, K). "
            "It also provides essential fatty acids for skin, coat, and brain function. "
            "Cats handle fat well — unlike carbohydrates, fat is a natural part of their carnivore diet."),
        'deficiency': "Poor coat, dry skin, vitamin deficiencies, low energy",
        'excess': "Weight gain, pancreatitis in prone cats",
    },
}


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
            'daily': ['Clean food bowl', 'Add water', 'Clean litter box',
                      'Let them out my room', 'Pray for them', 'Play with them'],
            'weekly': ['Clean water fountain', 'Clean room', 'Clean air purifier'],
            'monthly': ['Deep clean litter box', 'Buy food', 'Buy wet food',
                        'Buy litter', 'Buy treats', 'Buy toys',
                        'Clean cat tree', 'Clean bedding', 'Clean air purifier filter'],
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

    # Food library — shared across all cats
    if 'food_library' not in st.session_state:
        st.session_state.food_library = [dict(f) for f in DEFAULT_FOOD_LIBRARY]

    # Diet settings per cat
    if 'diet_settings' not in st.session_state:
        st.session_state.diet_settings = {
            cat: {'meals_per_day': 3, 'notes': '',
                  'active_foods': ['Pro Plan Adult Wet', 'Pro Plan Adult Dry',
                                   'Unseasoned Boiled Chicken', 'Freeze-Dried Treats']}
            for cat in ['Haku', 'Kuro', 'Sonic']
        }

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
# PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════
def save_data():
    try:
        blobs = {
            'health_data.json':   json.dumps(st.session_state.health_data,   default=str),
            'task_logs.json':     json.dumps(st.session_state.task_logs,     default=str),
            'cat_profiles.json':  json.dumps(st.session_state.cat_profiles,  default=str),
            'diet_settings.json': json.dumps(st.session_state.diet_settings, default=str),
            'food_library.json':  json.dumps(st.session_state.food_library,  default=str),
        }
        for fname, data_str in blobs.items():
            if AUTH_ENABLED:
                try: data_str = encrypt_data(data_str)
                except: pass
            with open(fname, 'w') as f:
                f.write(data_str)
    except Exception as e:
        st.error(f"Error saving: {e}")


def _read(fname):
    if not os.path.exists(fname): return None
    with open(fname, 'r') as f: raw = f.read()
    if AUTH_ENABLED and raw:
        try: raw = decrypt_data(raw)
        except: pass
    return raw or None


def load_data():
    if st.session_state.data_loaded: return
    try:
        s = _read('health_data.json')
        if s: st.session_state.health_data = json.loads(s)

        s = _read('task_logs.json')
        if s: st.session_state.task_logs = json.loads(s)

        s = _read('cat_profiles.json')
        if s:
            loaded = json.loads(s)
            for cat, profile in loaded.items():
                if 'vet_visits' in profile and isinstance(profile['vet_visits'], list):
                    if profile['vet_visits'] and isinstance(profile['vet_visits'][0], str):
                        profile['vet_visits'] = []
                for key, val in DEFAULT_VET_SCHEDULE.get(cat, {}).items():
                    if not profile.get(key): profile[key] = val
                profile.setdefault('birthdate', '')
            st.session_state.cat_profiles = loaded

        s = _read('diet_settings.json')
        if s:
            ld = json.loads(s)
            for cat in st.session_state.cats:
                if cat in ld: st.session_state.diet_settings[cat].update(ld[cat])

        s = _read('food_library.json')
        if s:
            loaded_lib = json.loads(s)
            # Merge: keep defaults, add any custom entries
            existing_names = {f['name'] for f in loaded_lib}
            for default in DEFAULT_FOOD_LIBRARY:
                if default['name'] not in existing_names:
                    loaded_lib.append(dict(default))
            st.session_state.food_library = loaded_lib

        st.session_state.data_loaded = True
    except Exception as e:
        st.error(f"Error loading: {e}")
        st.session_state.data_loaded = True


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
    return {ds: logs for ds, logs in st.session_state.task_logs.items()
            if _valid_date(ds) and start_date <= date.fromisoformat(ds) <= end_date}


def _valid_date(s):
    try: date.fromisoformat(s); return True
    except: return False


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
        if entry.get('pooped'):       d['pooped'] = True
        if entry.get('mood'):         d['moods'].append(entry['mood'])
        if entry.get('food_eaten'):   d['food_log'].append(entry['food_eaten'])
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
# HEALTH ANALYSIS — data-driven with ranges and explanations
# ══════════════════════════════════════════════════════════════════════════════
def _rate_metric(value, rng):
    lo_ideal, hi_ideal = rng['ideal']
    lo_ok,   hi_ok    = rng['ok']
    if lo_ideal <= value <= hi_ideal: return 'ideal',    '🟢', rng['ideal_msg']
    if lo_ok    <= value <= hi_ok:    return 'ok',       '🟡', rng['ok_msg']
    if value < lo_ok:                 return 'low',      '🔴', rng['low_msg']
    return 'high', '🟠', rng['high_msg']


def analyze_cat_health(cat_name: str) -> Dict:
    today    = date.today()
    week_ago = today - timedelta(days=7)
    daily    = get_daily_aggregated(cat_name, week_ago, today)

    base = {
        'cat':         cat_name,
        'profile':     st.session_state.cat_profiles.get(cat_name, {}),
        'vet_history': st.session_state.cat_profiles.get(cat_name, {}).get('vet_visits', []),
        'daily':       daily
    }

    if not daily:
        return {**base, 'status': 'no_data', 'total_entries': 0, 'total_days': 0,
                'water_avg': 0, 'food_avg': 0, 'litter_avg': 0, 'poop_days': 0,
                'mood_trend': 'unknown', 'litter_issues': [],
                'metric_ratings': {}, 'concerns': [], 'positives': []}

    total_days    = len(daily)
    total_entries = sum(d['entry_count'] for d in daily.values())
    water_avg     = sum(d['water_drinks']     for d in daily.values()) / total_days
    food_avg      = sum(d['food_eats']        for d in daily.values()) / total_days
    litter_avg    = sum(d['litter_box_times'] for d in daily.values()) / total_days
    poop_days     = sum(1 for d in daily.values() if d.get('pooped'))

    all_moods = [m for d in daily.values() for m in d['moods']]
    mood_trend = 'stable'
    if all_moods:
        poor = sum(1 for m in all_moods if m in ['Very Poor', 'Poor'])
        good = sum(1 for m in all_moods if m in ['Good', 'Excellent'])
        if poor > len(all_moods) / 2:   mood_trend = 'declining'
        elif good > len(all_moods) / 2: mood_trend = 'good'

    litter_issues = [
        (str(ed), iss)
        for ed, d in daily.items()
        for iss in d['litter_quality_issues']
        if any(kw in iss.lower() for kw in ['blood','diarrhea','diarrhoea','abnormal','mucus','black','red'])
    ]

    # Rate each metric
    w_status, w_icon, w_msg = _rate_metric(water_avg,  HEALTH_RANGES['water_drinks'])
    f_status, f_icon, f_msg = _rate_metric(food_avg,   HEALTH_RANGES['food_eats'])
    l_status, l_icon, l_msg = _rate_metric(litter_avg, HEALTH_RANGES['litter_box_times'])

    metric_ratings = {
        'water':  {'avg': water_avg,  'status': w_status, 'icon': w_icon, 'msg': w_msg,
                   'ideal': '3-8 times/day', 'ok': '1-10 times/day'},
        'food':   {'avg': food_avg,   'status': f_status, 'icon': f_icon, 'msg': f_msg,
                   'ideal': '3-5 meals/day', 'ok': '2-6 meals/day'},
        'litter': {'avg': litter_avg, 'status': l_status, 'icon': l_icon, 'msg': l_msg,
                   'ideal': '2-4 times/day', 'ok': '1-6 times/day'},
    }

    concerns, positives = [], []

    for key, mr in metric_ratings.items():
        if mr['status'] == 'ideal': positives.append((key, mr))
        elif mr['status'] in ('low', 'high'): concerns.append((key, mr))

    # Mood
    mood_analysis = {
        'good':     ('🟢', 'ideal',
                     "Consistent good mood. Happy cats have lower cortisol, stronger immunity, and lower FLUTD risk."),
        'stable':   ('🟡', 'ok',
                     "Stable mood. Normal baseline — watch for any downward trend over multiple days."),
        'declining':('🔴', 'concern',
                     "Declining mood. In cats this is often the earliest sign of physical illness — before other symptoms appear. "
                     "Cats hide pain. Check for subtle physical signs. Vet visit if it persists 2-3 days."),
        'unknown':  ('⬜', 'unknown', "No mood data logged. Add mood in health entries to track this."),
    }
    mood_icon, mood_status, mood_msg = mood_analysis.get(mood_trend, mood_analysis['unknown'])

    # Poop
    poop_pct  = poop_days / total_days if total_days > 0 else 0
    if poop_pct >= 0.8:
        poop_icon, poop_msg = '🟢', f"Regular bowel movements ({poop_days}/{total_days} days). Healthy digestion and good gut motility."
    elif poop_pct >= 0.4:
        poop_icon, poop_msg = '🟡', f"Moderate poop days logged ({poop_days}/{total_days}). May be incomplete logging or mild irregularity — monitor."
    elif total_days >= 3:
        poop_icon, poop_msg = '🔴', (f"Few/no poop days logged ({poop_days}/{total_days}). "
                                      "If genuinely not pooping: cats should poop every 24-36 hrs. "
                                      "Constipation causes toxin buildup and pain. Increase wet food and water. Vet if 48+ hrs.")
    else:
        poop_icon, poop_msg = '⬜', "Not enough data yet."

    return {
        **base,
        'status':          'healthy' if not concerns else 'warning',
        'total_entries':   total_entries,
        'total_days':      total_days,
        'water_avg':       water_avg,
        'food_avg':        food_avg,
        'litter_avg':      litter_avg,
        'poop_days':       poop_days,
        'mood_trend':      mood_trend,
        'mood_icon':       mood_icon,
        'mood_msg':        mood_msg,
        'poop_icon':       poop_icon,
        'poop_msg':        poop_msg,
        'litter_issues':   litter_issues,
        'metric_ratings':  metric_ratings,
        'concerns':        concerns,
        'positives':       positives,
    }


def get_active_medications_today():
    today = date.today()
    active, seen = [], set()
    for cat in st.session_state.cats:
        for entry in get_health_entries(cat, today - timedelta(days=90), today):
            mn = entry.get('medication_name', '').strip()
            ss = entry.get('medication_start_date', '')
            es = entry.get('medication_end_date', '')
            if not all([mn, ss, es]): continue
            try: ms, me = date.fromisoformat(ss), date.fromisoformat(es)
            except: continue
            key = f"{cat}_{mn}_{es}"
            if key in seen: continue
            seen.add(key)
            if ms <= today <= me:
                active.append({'cat': cat, 'name': mn,
                               'type':      entry.get('medication_type', 'Oral'),
                               'dosage':    entry.get('medication_dosage', ''),
                               'frequency': entry.get('medication_frequency', ''),
                               'end_date':  es, 'days_left': (me - today).days})
    return active


# ══════════════════════════════════════════════════════════════════════════════
# VET REMINDERS
# ══════════════════════════════════════════════════════════════════════════════
def get_vet_reminders():
    today = date.today()
    reminders = []
    labels = {
        'next_checkup':   'Annual Checkup (Blood, Dental, Chest X-ray, Breathing)',
        'next_vaccines':  'Annual Vaccines',
        'next_deworming': 'Deworming',
        'next_vet_visit': 'Routine Vet Visit',
    }
    for cat in st.session_state.cats:
        profile = st.session_state.cat_profiles.get(cat, {})
        for key, label in labels.items():
            val = profile.get(key, '')
            if val:
                try:
                    nd = date.fromisoformat(val)
                    reminders.append({'cat': cat, 'label': label, 'next_date': val,
                                      'days_away': (nd - today).days, 'overdue': nd < today})
                except:
                    reminders.append({'cat': cat, 'label': label, 'next_date': 'Invalid',
                                      'days_away': None, 'overdue': False})
            else:
                reminders.append({'cat': cat, 'label': label, 'next_date': 'Not set',
                                  'days_away': None, 'overdue': False})
    return reminders


# ══════════════════════════════════════════════════════════════════════════════
# DIET ANALYSIS — data-driven from food library + logged foods
# ══════════════════════════════════════════════════════════════════════════════
def analyze_diet(cat_name: str) -> Dict:
    """
    Analyze a cat's diet based on their active foods in the food library.
    Returns per-food analysis and overall diet assessment.
    """
    ds = st.session_state.diet_settings.get(cat_name, {})
    active_food_names = ds.get('active_foods', [])
    lib = {f['name']: f for f in st.session_state.food_library}
    active_foods = [lib[n] for n in active_food_names if n in lib]

    if not active_foods:
        return {'has_data': False}

    meals = int(ds.get('meals_per_day', 3))

    # Separate by type
    wet_foods   = [f for f in active_foods if f['type'] == 'Wet']
    dry_foods   = [f for f in active_foods if f['type'] == 'Dry']
    treats      = [f for f in active_foods if f['type'] == 'Treat']

    # Taurine check
    has_taurine_source = any(f['taurine'] for f in active_foods)
    complete_food      = any(f['taurine'] and f['type'] in ('Wet','Dry') for f in active_foods)

    # Phosphorus concern
    dry_phosphorus  = [f['phosphorus_pct'] for f in dry_foods]
    wet_phosphorus  = [f['phosphorus_pct'] for f in wet_foods]
    high_phos_dry   = [f for f in dry_foods  if f['phosphorus_pct'] > 0.9]
    safe_phos_wet   = [f for f in wet_foods  if f['phosphorus_pct'] <= 0.4]

    # Moisture
    wet_moisture_avg = sum(f['moisture_pct'] for f in wet_foods) / len(wet_foods) if wet_foods else 0
    has_good_moisture= bool(wet_foods) and wet_moisture_avg >= 70

    # Weight and water needs
    weight_str = st.session_state.cat_profiles.get(cat_name, {}).get('weight', '4')
    try:    weight_kg = float(weight_str) if weight_str else 4.0
    except: weight_kg = 4.0
    water_needed = weight_kg * 60

    findings = []
    warnings = []
    positives = []

    # Taurine
    if complete_food:
        positives.append("✅ **Taurine covered** — complete commercial food in diet ensures adequate taurine for heart and eye health.")
    elif has_taurine_source:
        warnings.append("⚠️ **Taurine source present but check dosage** — ensure the taurine-containing food is a substantial part of the diet, not just a treat.")
    else:
        warnings.append("🔴 **No taurine source detected!** Cats CANNOT make their own taurine. Without it: heart disease (DCM) and blindness develop. Add a complete commercial cat food immediately.")

    # Moisture
    if has_good_moisture:
        positives.append(f"✅ **Good moisture from wet food** ({wet_moisture_avg:.0f}% moisture). This is the single most important kidney and urinary protection you can give. Prey animals are ~70-75% water — wet food mimics this.")
    elif wet_foods:
        warnings.append(f"🟡 **Moisture from wet food is lower than ideal** ({wet_moisture_avg:.0f}%). Aim for wet food with ≥70% moisture.")
    else:
        warnings.append("🔴 **No wet food detected!** Cats eating only dry food are chronically mildly dehydrated. This is the #1 cause of kidney disease and urinary blockages. Add wet food to every meal.")

    # Phosphorus
    if high_phos_dry:
        for f in high_phos_dry:
            warnings.append(f"⚠️ **{f['name']} has high phosphorus ({f['phosphorus_pct']}%)** — above the 0.9% threshold. For kidney-monitored cats, this accelerates CKD. Balance with low-phosphorus wet food and monitor kidney bloodwork annually.")
    if safe_phos_wet:
        positives.append(f"✅ **Low-phosphorus wet food present** — {', '.join(f['name'] for f in safe_phos_wet)} keeps kidney load low. Excellent choice for kidney health monitoring.")

    # Boiled chicken
    chicken_foods = [f for f in active_foods if 'chicken' in f['name'].lower()]
    if chicken_foods:
        findings.append("🍗 **Unseasoned boiled chicken** — excellent lean protein supplement. Does NOT contain significant taurine and is NOT a complete meal. Use as a supplement or appetite booster only. If a cat refuses all food but will eat chicken: this is fine short-term but needs investigation.")

    # Treats
    if treats:
        findings.append(f"🍬 **Treats ({', '.join(f['name'] for f in treats)})** — high protein but low moisture and no taurine. Keep treats to <10% of daily calories. Freeze-dried treats are among the best treat options — single ingredient, no fillers.")

    # Meal frequency analysis
    if meals >= 3:
        positives.append(f"✅ **{meals} meals/day** — ideal. Matches natural hunting rhythm, stabilizes blood sugar, reduces vomiting risk from empty stomach.")
    elif meals == 2:
        findings.append("🟡 **2 meals/day** — acceptable but 12-hour gaps can cause morning bile vomiting. Try adding a small wet food meal before bed.")
    else:
        warnings.append(f"🔴 **{meals} meal/day** — too infrequent. Cats have small stomachs and fast metabolisms. One large meal causes hunger stress and increases vomiting risk.")

    return {
        'has_data':        True,
        'active_foods':    active_foods,
        'wet_foods':       wet_foods,
        'dry_foods':       dry_foods,
        'treats':          treats,
        'positives':       positives,
        'warnings':        warnings,
        'findings':        findings,
        'has_taurine':     complete_food,
        'has_good_moisture': has_good_moisture,
        'water_needed':    water_needed,
        'meals':           meals,
        'weight_kg':       weight_kg,
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
    if done_set: st.success("Done: " + ", ".join(sorted(done_set)))
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
             HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7'), spaceAfter=10)]

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
                  ["Water/Day",  f"{a['water_avg']:.1f}",  mr.get('water',{}).get('icon',''),  "Ideal: 3-8/day"],
                  ["Food/Day",   f"{a['food_avg']:.1f}",   mr.get('food',{}).get('icon',''),   "Ideal: 3-5/day"],
                  ["Litter/Day", f"{a['litter_avg']:.1f}", mr.get('litter',{}).get('icon',''), "Ideal: 2-4/day"],
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
        story += [Spacer(1,12), HRFlowable(width="100%",thickness=0.5,
                  color=colors.HexColor('#bdc3c7'),spaceAfter=10)]

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
            with ci:
                st.markdown("## 🐱"); st.markdown(f"**{cat}**")
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
                    st.text_input("Next Annual Checkup", value=profile.get('next_checkup',''),  key=f"edit_nc_{cat}",  placeholder="YYYY-MM-DD")
                    st.text_input("Next Vaccines",       value=profile.get('next_vaccines',''), key=f"edit_nv_{cat}",  placeholder="YYYY-MM-DD")
                with vc2:
                    st.text_input("Next Deworming",      value=profile.get('next_deworming',''),key=f"edit_nd_{cat}",  placeholder="YYYY-MM-DD")
                    st.text_input("Next Vet Visit",      value=profile.get('next_vet_visit',''),key=f"edit_nvv_{cat}", placeholder="YYYY-MM-DD")
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
                        save_data()
                        st.success("✅ Profile saved!")
                        st.session_state[f'edit_basic_{cat}'] = False
                        st.rerun()
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
                    if to_del and st.button("🗑️ Delete", key=f"del_vis_btn_{cat}", type="secondary"):
                        vv.pop(opts.index(to_del))
                        st.session_state.cat_profiles[cat]['vet_visits'] = vv
                        save_data(); st.success("Deleted!"); st.rerun()
                st.markdown("---")
                c1,c2 = st.columns(2)
                with c1:
                    st.date_input("Date",   key=f"v_date_{cat}")
                    st.text_input("Doctor", key=f"v_doc_{cat}",    placeholder="Dr. Smith")
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
                          'food_eaten': food_eaten, 'litter_quality': lq.split('\n') if lq else [],
                          'notes': notes, 'grooming_tasks': {t: c for t,c in gt.items() if c}}
                    if mn:
                        ed.update({'medication_name': mn, 'medication_type': mty,
                                   'medication_dosage': md_, 'medication_frequency': mf,
                                   'medication_reason': mr, 'medication_start_date': str(ms),
                                   'medication_end_date': str(me)})
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
            mr  = st.text_input("Reason",    placeholder="e.g., Respiratory support",   key="form_med_reason")
            cs1,ce1 = st.columns(2)
            with cs1: ms = st.date_input("Start", value=date.today(),                   key="form_med_start")
            with ce1: me = st.date_input("End",   value=date.today()+timedelta(days=7), key="form_med_end")
        st.markdown("---")
        notes = st.text_area("📝 Additional Notes", height=70,
                             placeholder="Any other observations...", key="form_notes")
        st.markdown("---")
        st.subheader("🪥 Grooming Tasks")
        st.caption("Check only if performed today (grooming reminder appears Thu & Fri).")
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
                           'medication_reason': mr, 'medication_start_date': str(ms),
                           'medication_end_date': str(me)})
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
    if not entries:
        st.info(f"No data found for {sel} in this range."); return

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
                   "Log grooming in the **Add Health Entry** page under Grooming Tasks.")
    else:
        st.caption(f"🪥 Grooming reminder appears Thu & Fri. Log grooming in Add Health Entry. Today: {today.strftime('%A')}.")
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
        else: st.write(f"Monthly tasks appear on the 1st. Remaining: {len(pending_m)}/{len(st.session_state.tasks.get('monthly',[]))}")
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

    # ── Food Library Manager ──
    with st.expander("📚 Food Library — Add / Edit Foods", expanded=False):
        st.write("All foods here are available to assign to any cat. Your actual cats' foods are pre-loaded.")

        lib = st.session_state.food_library
        food_names = [f['name'] for f in lib]

        st.markdown("#### Add a New Food")
        with st.form("add_food_form"):
            fc1, fc2 = st.columns(2)
            with fc1:
                new_name     = st.text_input("Food Name", placeholder="e.g., Royal Canin Indoor Wet")
                new_type     = st.selectbox("Type", ["Wet", "Dry", "Treat"])
                new_protein  = st.number_input("Protein %",   0.0, 100.0, 10.0, step=0.5)
                new_fat      = st.number_input("Fat %",       0.0, 100.0,  4.0, step=0.5)
            with fc2:
                new_moisture = st.number_input("Moisture %",  0.0, 100.0, 78.0, step=1.0)
                new_fibre    = st.number_input("Fibre %",     0.0,  20.0,  1.0, step=0.5)
                new_phos     = st.number_input("Phosphorus %",0.0,   5.0,  0.2, step=0.05)
                new_sodium   = st.number_input("Sodium %",    0.0,   5.0,  0.15,step=0.01)
                new_taurine  = st.checkbox("Contains added Taurine?", value=True)
                new_cal      = st.number_input("Calories per 100g", 0, 600, 85)
            new_notes = st.text_input("Notes (optional)", placeholder="Any notes about this food")

            if st.form_submit_button("➕ Add Food to Library", type="primary"):
                if new_name and new_name not in food_names:
                    st.session_state.food_library.append({
                        'name': new_name, 'type': new_type,
                        'protein_pct': new_protein, 'fat_pct': new_fat,
                        'fibre_pct': new_fibre, 'moisture_pct': new_moisture,
                        'phosphorus_pct': new_phos, 'sodium_pct': new_sodium,
                        'taurine': new_taurine, 'calories_per_100g': new_cal,
                        'notes': new_notes
                    })
                    save_data(); st.success(f"✅ {new_name} added to library!"); st.rerun()
                elif new_name in food_names:
                    st.warning("A food with this name already exists.")
                else:
                    st.warning("Please enter a food name.")

        st.markdown("#### Current Food Library")
        if lib:
            lib_df = pd.DataFrame([{
                'Name': f['name'], 'Type': f['type'],
                'Protein%': f['protein_pct'], 'Fat%': f['fat_pct'],
                'Moisture%': f['moisture_pct'], 'Phosphorus%': f['phosphorus_pct'],
                'Taurine': '✅' if f['taurine'] else '❌',
                'Cal/100g': f['calories_per_100g']
            } for f in lib])
            st.dataframe(lib_df, use_container_width=True, hide_index=True)

            to_del = st.selectbox("Remove a food from library", [""]+food_names, key="del_food")
            if to_del and st.button("🗑️ Remove", key="del_food_btn", type="secondary"):
                # Don't remove default foods
                st.session_state.food_library = [f for f in lib if f['name'] != to_del]
                # Also remove from any cat's active foods
                for cat in st.session_state.cats:
                    af = st.session_state.diet_settings[cat].get('active_foods', [])
                    st.session_state.diet_settings[cat]['active_foods'] = [f for f in af if f != to_del]
                save_data(); st.success(f"Removed {to_del}"); st.rerun()

    st.markdown("---")

    # ── Per-cat diet settings and analysis ──
    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            ds  = st.session_state.diet_settings.get(cat, {})
            lib = st.session_state.food_library

            # ── Assign foods to this cat ──
            with st.expander(f"⚙️ {cat}'s Diet Settings", expanded=True):
                all_food_names = [f['name'] for f in lib]
                current_active = ds.get('active_foods', [])
                # Clean up any invalid entries
                current_active = [f for f in current_active if f in all_food_names]

                selected_foods = st.multiselect(
                    f"Foods {cat} is eating (select all that apply)",
                    options=all_food_names,
                    default=current_active,
                    key=f"diet_foods_{cat}"
                )
                meals = st.number_input("Meals per day", 1, 8,
                                        int(ds.get('meals_per_day', 3)), key=f"diet_meals_{cat}")
                diet_notes = st.text_area("Diet notes", value=ds.get('notes',''),
                                          key=f"diet_notes_{cat}", height=60)

                if st.button("💾 Save Diet Settings", key=f"save_diet_{cat}", type="primary"):
                    st.session_state.diet_settings[cat].update({
                        'active_foods':  st.session_state[f"diet_foods_{cat}"],
                        'meals_per_day': st.session_state[f"diet_meals_{cat}"],
                        'notes':         st.session_state[f"diet_notes_{cat}"],
                    })
                    save_data(); st.success("✅ Saved!"); st.rerun()

            st.markdown("---")

            # ── Diet Analysis ──
            st.subheader(f"🔬 {cat}'s Diet Analysis")
            da = analyze_diet(cat)

            if not da['has_data']:
                st.info("No foods assigned yet. Select foods above and save.")
                continue

            # Positives
            if da['positives']:
                st.markdown("**✅ What's good:**")
                for p in da['positives']: st.success(p)

            # Warnings
            if da['warnings']:
                st.markdown("**⚠️ Concerns:**")
                for w in da['warnings']:
                    if w.startswith("🔴"): st.error(w)
                    else: st.warning(w)

            # Findings
            if da['findings']:
                st.markdown("**ℹ️ Notes:**")
                for f in da['findings']: st.info(f)

            # ── Per-food nutritional breakdown ──
            st.markdown("---")
            st.subheader("📊 Per-Food Nutritional Breakdown")
            st.caption("All values are as-fed (not dry matter). Normal ranges shown for each nutrient.")

            for food in da['active_foods']:
                food_type = food['type']
                with st.expander(f"{'🥣' if food_type=='Wet' else '🥫' if food_type=='Dry' else '🎁'} {food['name']} ({food_type})", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**📋 Nutritional Values:**")

                        def show_nutrient(label, value, ideal_lo, ideal_hi, ok_lo, ok_hi, unit="%"):
                            if ideal_lo <= value <= ideal_hi:
                                icon = "🟢"
                                status = f"Ideal range: {ideal_lo}–{ideal_hi}{unit}"
                            elif ok_lo <= value <= ok_hi:
                                icon = "🟡"
                                status = f"Acceptable. Ideal: {ideal_lo}–{ideal_hi}{unit}"
                            else:
                                icon = "🔴" if value < ok_lo else "🟠"
                                status = f"Outside ideal ({ideal_lo}–{ideal_hi}{unit})"
                            st.write(f"{icon} **{label}:** {value}{unit} — {status}")

                        if food_type == 'Wet':
                            show_nutrient("Protein",    food['protein_pct'],   8,  15, 5,  20)
                            show_nutrient("Moisture",   food['moisture_pct'],  70, 85, 60, 90)
                            show_nutrient("Fat",        food['fat_pct'],        3,   8, 2,  12)
                            show_nutrient("Phosphorus", food['phosphorus_pct'],0.1, 0.4, 0.0, 0.7)
                        elif food_type == 'Dry':
                            show_nutrient("Protein",    food['protein_pct'],   35, 50, 25, 60)
                            show_nutrient("Moisture",   food['moisture_pct'],   8, 14,  5, 18)
                            show_nutrient("Fat",        food['fat_pct'],        10, 20,  6, 25)
                            show_nutrient("Phosphorus", food['phosphorus_pct'], 0.5, 0.9, 0.3, 1.2)
                        else:  # Treat
                            show_nutrient("Protein",    food['protein_pct'],   40, 80, 20, 90)
                            show_nutrient("Moisture",   food['moisture_pct'],   0, 15,  0, 30)
                            show_nutrient("Fat",        food['fat_pct'],         5, 20,  2, 30)
                            show_nutrient("Phosphorus", food['phosphorus_pct'],  0.0, 1.0, 0.0, 1.5)

                        st.write(f"{'🟢' if food['taurine'] else '🔴'} **Taurine:** {'Added ✅' if food['taurine'] else 'Not added ❌ — ensure complete food is primary diet'}")
                        st.write(f"⚡ **Calories:** {food['calories_per_100g']} kcal/100g")
                        if food.get('sodium_pct'):
                            icon = "🟢" if food['sodium_pct'] < 0.3 else "🟡" if food['sodium_pct'] < 0.5 else "🟠"
                            st.write(f"{icon} **Sodium:** {food['sodium_pct']}% — {'Low (heart-friendly)' if food['sodium_pct'] < 0.3 else 'Moderate' if food['sodium_pct'] < 0.5 else 'Higher — monitor for heart conditions'}")

                    with c2:
                        st.markdown("**🔬 Why each nutrient matters:**")
                        for rule_key, rule in DIET_ANALYSIS_RULES.items():
                            if rule_key == 'taurine': continue  # shown inline above
                            val = food.get(rule_key.replace('_pct','') + '_pct', None)
                            if val is None: continue
                            with st.container():
                                st.markdown(f"**{rule['label']}:** {rule['why'][:200]}...")
                                if 'excess' in rule:
                                    st.caption(f"⚠️ Excess risk: {rule['excess'][:120]}")

                    if food.get('notes'):
                        st.info(f"📝 {food['notes']}")

            # ── Essential nutrients cats need ──
            st.markdown("---")
            st.subheader("🐾 What Cats Must Get Daily")
            with st.expander("Click to expand full nutrients guide", expanded=False):
                for nutrient, rule in DIET_ANALYSIS_RULES.items():
                    st.markdown(f"**🔬 {rule['label']}**")
                    st.write(rule['why'])
                    if 'deficiency' in rule: st.error(f"Deficiency: {rule['deficiency']}")
                    if 'excess' in rule:     st.warning(f"Excess risk: {rule['excess']}")
                    st.markdown("---")

            # ── Recent food log ──
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
# PAGE: CAT HEALTH GUIDE
# ══════════════════════════════════════════════════════════════════════════════
def cat_health_guide_page():
    st.header("🏥 Cat Health Guide")
    st.write("Reference guide for Haku, Kuro & Sonic. All ranges and explanations are data-based.")

    # ── Data-driven reference analysis from their actual logs ──
    st.subheader("📊 Current Status vs Normal Ranges")
    st.caption("Based on their health entries from the past 7 days.")

    today    = date.today()
    week_ago = today - timedelta(days=7)

    for cat in st.session_state.cats:
        a = analyze_cat_health(cat)
        if a['status'] == 'no_data':
            st.info(f"**{cat}:** No data logged yet.")
            continue
        mr = a.get('metric_ratings', {})
        st.markdown(f"**🐱 {cat}** — {a['total_days']} days tracked")
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            w = mr.get('water',{})
            st.metric(f"Water {w.get('icon','')}", f"{a['water_avg']:.1f}/day",
                      help=f"Normal: {w.get('ideal','3-8/day')} | Status: {w.get('status','')}")
        with c2:
            f = mr.get('food',{})
            st.metric(f"Food {f.get('icon','')}", f"{a['food_avg']:.1f}/day",
                      help=f"Normal: {f.get('ideal','3-5/day')} | Status: {f.get('status','')}")
        with c3:
            l = mr.get('litter',{})
            st.metric(f"Litter {l.get('icon','')}", f"{a['litter_avg']:.1f}/day",
                      help=f"Normal: {l.get('ideal','2-4/day')} | Status: {l.get('status','')}")
        with c4:
            st.metric(f"Mood {a.get('mood_icon','')}", a.get('mood_trend','—').title())
        if a['concerns']:
            for _, cr in a['concerns']:
                st.warning(f"⚠️ **{cat} — {HEALTH_RANGES.get(_, {}).get('label', '')}:** {cr['msg'][:150]}...")
    st.markdown("---")

    # ── Visual guides ──
    with st.expander("💩 Poop Guide — Normal vs Abnormal + What Each Means", expanded=False):
        st.success(
            "**✅ Normal:**  \n"
            "Shape: Log-shaped, holds together  \n"
            "Colour: Medium to dark brown  \n"
            "Consistency: Firm, not rock hard, not mushy  \n"
            "Frequency: Once daily or once every 36 hours  \n"
            "**Normal range: 1 bowel movement per 24-36 hours**")

        st.markdown("**What abnormal poop tells you:**")
        col1,col2 = st.columns(2)
        with col1:
            st.error("**Liquid/watery (diarrhoea):** Infection, parasites, food intolerance, stress, or IBD. If >24hrs or blood present: vet visit same day.")
            st.error("**Bright red blood:** Fresh — lower GI bleed. Colitis, polyps, or parasites. Single episode: monitor. Recurring: vet.")
            st.error("**Black tarry stool:** Digested blood — upper GI bleed (stomach or small intestine). Vet same day.")
        with col2:
            st.warning("**Mucus coating:** Small amounts are normal. Large amounts consistently = colitis or IBD.")
            st.warning("**Hard dry pellets:** Constipation — increase wet food and water. Vet if no poop in 48+ hours.")
            st.warning("**Yellow or green-tinted:** Food moving too fast, or bile issue. Monitor closely. Vet if persistent.")
            st.warning("**Very pale or white:** Possible liver or pancreas issue — vet check needed.")

    with st.expander("🚽 Urine Guide — Normal vs Abnormal + What Each Means", expanded=False):
        st.success(
            "**✅ Normal:**  \n"
            "Colour: Pale to medium yellow  \n"
            "Smell: Mild ammonia, not overwhelming  \n"
            "Consistency: Clear, no cloudiness  \n"
            "**Normal range: 2-4 litter box trips per day, decent puddle each time**")

        col1,col2 = st.columns(2)
        with col1:
            st.error("**Pink / red / orange:** Blood in urine — UTI, crystals, stones, or blockage. If also straining: EMERGENCY NOW.")
            st.error("**No urine + straining:** Blockage — fatal within 24-48 hrs without emergency vet care. Do not wait.")
            st.warning("**Cloudy or milky:** Infection, crystals, or protein in urine. Vet check within 24-48 hrs.")
        with col2:
            st.warning("**Very dark yellow + strong smell:** Dehydration — increase water and wet food urgently.")
            st.warning("**Very pale, large amounts, frequent:** Possible diabetes or kidney disease. Blood test needed.")
            st.warning("**Tiny drops, many trips:** Partial blockage or UTI. Vet same day.")

    with st.expander("🤮 Vomit Colour Guide — What Each Colour Means", expanded=False):
        col1,col2 = st.columns(2)
        with col1:
            st.info("**Clear/foamy white:** Empty stomach — fasting too long. Add a small meal before bed. If daily: vet check.")
            st.info("**Yellow/yellow-green (bile):** Stomach empty too long, or bile reflux. Increase meal frequency. Morning bile after overnight fast = add a late-night snack.")
            st.success("**Brown with food chunks:** Ate too fast or too much. Use puzzle feeder. Single episode is normal.")
            st.warning("**Brown liquid, no food:** Old blood or bile + digested matter. Coffee-ground texture = upper GI bleed. Vet today.")
        with col2:
            st.error("**Bright red:** Fresh blood. More than a tiny streak = vet immediately.")
            st.error("**Dark red / black:** Digested blood. Upper GI bleed — urgent vet visit.")
            st.warning("**Green:** Ate grass, OR bile with digested material. Single episode usually fine. Recurring = vet check.")
            st.warning("**White, foamy, recurring:** GI issue if no hairball produced. Monitor — vet if ongoing.")

        st.markdown("**🚨 Vet NOW if vomiting is:**")
        st.error("Any blood · More than 2-3 times per day · Combined with lethargy or not eating · Combined with diarrhoea · Possible foreign object ingested")

    # ── Conditions reference ──
    diseases = [
        {
            "name": "Feline Herpesvirus (FHV-1) — Haku",
            "icon": "🦠",
            "who":  "Haku has this. Lifelong — virus stays dormant and reactivates with stress",
            "signs": ["Sneezing — mild or severe during flare-ups",
                      "Eye discharge — watery to thick, one or both eyes",
                      "Conjunctivitis — red, swollen, goopy eyes",
                      "Nasal discharge", "Loss of appetite (can't smell food)",
                      "Corneal ulcers in severe cases — squinting or pawing at eye",
                      "Flare triggers: stress, vet visits, illness, routine changes"],
            "prevention": ["Minimize stress — routine is the #1 management tool",
                           "L-Lysine supplement — ask vet about dosage",
                           "Keep eye area clean — warm damp cloth",
                           "FVRCP vaccine reduces flare severity",
                           "Air purifier already helping ✅"],
            "urgency": "🟠 Chronic lifelong condition. Corneal ulcers = urgent vet. Flares managed with supportive care."
        },
        {
            "name": "Kidney Disease (CKD) — All cats on kidney watch",
            "icon": "🫘",
            "who":  "All three cats. Key monitoring priority. Becomes more common from age 5-7.",
            "signs": ["Increased thirst — drinking noticeably more",
                      "Increased urination — larger litter clumps",
                      "Weight loss despite eating", "Ammonia/metallic bad breath",
                      "Morning vomiting on empty stomach", "Lethargy, hiding more",
                      "Rough unkempt coat", "Muscle wasting over spine"],
            "prevention": ["Wet food as main diet — hydration is #1 kidney protector",
                           "Fresh water always available",
                           "Annual bloodwork — SDMA catches CKD before symptoms ✅",
                           "Low phosphorus diet — Pro Plan Wet is safer than dry",
                           "Log daily water intake and litter frequency — changes are early indicators"],
            "urgency": "🟠 Silent early on. Annual bloodwork + your daily logging = best early detection."
        },
        {
            "name": "Urinary Tract Infection / FLUTD",
            "icon": "🚽",
            "who":  "Any cat — males especially (risk of blockage)",
            "signs": ["Straining with little or no urine", "Crying while urinating",
                      "Blood in urine", "Urinating outside litter box",
                      "Excessive genital licking", "Many litter trips with no result"],
            "prevention": ["Fresh water — fountain preferred", "Wet food as main diet",
                           "Clean litter box daily", "Reduce stress — FIC is stress-triggered",
                           "Urinary formula food if recurrent"],
            "urgency": "🔴 Emergency if producing no urine — fatal within 24-48 hrs without treatment"
        },
        {
            "name": "Heart Disease (HCM)",
            "icon": "❤️",
            "who":  "Any cat — all three on 4-monthly vet visits for monitoring",
            "signs": ["Rapid or laboured breathing at rest",
                      "Breathing >30 breaths/min while sleeping",
                      "Sudden hind leg paralysis (aortic thromboembolism — extreme emergency)",
                      "Fluid in chest", "Often NO early symptoms — detected by vet only"],
            "prevention": ["4-monthly vet visits — includes cardiac auscultation ✅",
                           "Echocardiogram if murmur detected",
                           "Taurine-adequate diet — Pro Plan supplemented ✅",
                           "Count resting breathing rate at home — normal <30/min"],
            "urgency": "🔴 Hind leg paralysis or open-mouth breathing = emergency NOW. Scheduled checkups are critical."
        },
        {
            "name": "Feline Asthma / Breathing Difficulty",
            "icon": "💨",
            "who":  "Any cat — you already use a nebulizer so you're managing this",
            "signs": ["Hunched posture, neck extended, head low — looks like bringing up hairball but nothing comes",
                      "Wheezing", "Faster breathing at rest", "Coughing that sounds like retching",
                      "Open-mouth breathing after exertion"],
            "prevention": ["No aerosol sprays or heavy perfumes near cats",
                           "Unscented litter — dust worsens asthma",
                           "Air purifier running ✅", "Consistent nebulizer protocol"],
            "urgency": "🟠 Acute attacks = emergency. Open-mouth breathing or blue gums = immediate vet."
        },
        {
            "name": "Mold / Environmental Toxins",
            "icon": "🍄",
            "who":  "Indoor cats — any home with dampness, poor ventilation, or old buildings",
            "signs": ["Sneezing/coughing that started after cleaning or moving furniture",
                      "Multiple cats showing similar symptoms simultaneously",
                      "Eye and nose irritation without obvious cause",
                      "Skin irritation, scratching without fleas found",
                      "Breathing changes linked to specific rooms"],
            "prevention": ["Air purifier — already running ✅",
                           "Check damp areas — under sinks, bathroom corners, behind appliances",
                           "Replace HVAC/purifier filters regularly (in your monthly tasks ✅)",
                           "Avoid aerosol cleaners and scented candles near cats",
                           "Good ventilation — open windows regularly"],
            "urgency": "🟡 Chronic exposure causes real health issues. Environmental check if multiple cats symptomatic."
        },
        {
            "name": "Stress / Anxiety (FIC)",
            "icon": "😰",
            "who":  "All three — indoor, multi-cat, routine-sensitive",
            "signs": ["Hiding more than usual", "Overgrooming — licking until bald patches",
                      "Inter-cat aggression", "Litter box avoidance",
                      "Stress-triggered UTI symptoms", "Loss of appetite during changes"],
            "prevention": ["Consistent routine", "Vertical space and hiding spots",
                           "One litter box per cat + one extra", "Daily play sessions ✅",
                           "Feliway diffuser if inter-cat tension increases"],
            "urgency": "🟡 Chronic stress causes physical disease — FLUTD, reduced immunity, poor appetite."
        },
        {
            "name": "Red / Inflamed Gums (Stomatitis / Gingivitis)",
            "icon": "🦷",
            "who":  "Any cat — dental disease affects 70% of cats over age 3",
            "signs": ["Bright red or purple gum line", "Reluctance to eat or dropping food",
                      "Drooling (sometimes bloody)", "Pawing at mouth",
                      "Strong bad breath", "Weight loss from pain"],
            "prevention": ["Annual dental check in your annual checkup ✅",
                           "Brush teeth 2-3x per week",
                           "Dental treats and water additives"],
            "urgency": "🟠 Not eating due to mouth pain = vet within 24-48 hrs."
        },
        {
            "name": "Intestinal Parasites",
            "icon": "🐛",
            "who":  "All cats — on deworming schedule",
            "signs": ["Visible worm segments in stool", "Bloated belly",
                      "Weight loss despite eating", "Scooting", "Vomiting or diarrhoea"],
            "prevention": ["Haku/Sonic: every 3 months (next: 26-Jul-2026)",
                           "Kuro: every 4 months (next: 26-Aug-2026)",
                           "Monthly flea prevention — fleas carry tapeworms"],
            "urgency": "🟡 Follow schedule — worsens without treatment."
        },
        {
            "name": "Fleas",
            "icon": "🦟",
            "who":  "Any cat — even indoor-only",
            "signs": ["Scratching neck and tail base", "Black specks in fur (flea dirt)",
                      "Red bumps, hair loss from scratching"],
            "prevention": ["Monthly flea prevention", "Vacuum and wash bedding monthly ✅",
                           "Treat all cats simultaneously"],
            "urgency": "🟡 Not dangerous for adults but causes anemia in kittens and carries tapeworms."
        },
        {
            "name": "Ear Mites",
            "icon": "👂",
            "who":  "Any cat",
            "signs": ["Head shaking and ear scratching", "Dark coffee-ground discharge in ears",
                      "Smell from ears", "Redness inside ear flap"],
            "prevention": ["Monthly ear checks during grooming (Thursday sessions) ✅",
                           "Treat all cats together if one has mites"],
            "urgency": "🟠 Very uncomfortable — secondary infections develop if untreated."
        },
    ]

    st.markdown("---")
    ucol, scol = st.columns(2)
    with ucol: uf = st.selectbox("Filter by urgency", ["All","🔴 Emergency","🟠 See vet soon","🟡 Monitor / Treat"])
    with scol: search = st.text_input("🔍 Search", placeholder="e.g., sneezing, kidney, breathing")

    def ulvl(u):
        if "🔴" in u: return "🔴 Emergency"
        if "🟠" in u: return "🟠 See vet soon"
        return "🟡 Monitor / Treat"

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

    # ── Symptom checker ──
    st.markdown("---")
    st.subheader("🔍 Symptom Checker")
    symptom_map = {
        "Not eating / loss of appetite":         ["Feline Herpesvirus","Red / Inflamed Gums","Heart Disease","Kidney Disease","Urinary Tract Infection"],
        "Vomiting":                              ["Intestinal Parasites","Kidney Disease","Feline Asthma"],
        "Diarrhoea":                             ["Intestinal Parasites","Stress / Anxiety"],
        "Straining to urinate / no urine":       ["Urinary Tract Infection"],
        "Blood in urine":                        ["Urinary Tract Infection","Kidney Disease"],
        "Increased thirst":                      ["Kidney Disease"],
        "Open-mouth breathing":                  ["Feline Asthma","Heart Disease"],
        "Fast breathing at rest (>30/min)":      ["Feline Asthma","Heart Disease"],
        "Hind leg weakness/paralysis":           ["Heart Disease"],
        "Sneezing / eye discharge":              ["Feline Herpesvirus"],
        "Red inflamed gums":                     ["Red / Inflamed Gums"],
        "Hiding / lethargy":                     ["Stress / Anxiety","Kidney Disease","Heart Disease"],
        "Hair loss / overgrooming":              ["Stress / Anxiety","Fleas"],
        "Scratching ears":                       ["Ear Mites"],
        "Weight loss despite eating":            ["Intestinal Parasites","Kidney Disease"],
        "Sneezing after room/furniture changes": ["Mold / Environmental Toxins"],
        "Multiple cats sneezing at same time":   ["Mold / Environmental Toxins"],
        "Scooting on floor":                     ["Intestinal Parasites"],
        "Litter box avoidance":                  ["Urinary Tract Infection","Stress / Anxiety"],
        "Bloated belly":                         ["Intestinal Parasites"],
    }
    selected = []
    cols = st.columns(2)
    for i, sym in enumerate(symptom_map):
        with cols[i % 2]:
            if st.checkbox(sym, key=f"sym_{i}"): selected.append(sym)

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

    # ── Vet reminders ──
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
            st.warning(f"⚠️ **{r['cat']}** — {r['label']}: date not set. Update in Cat Profiles.")
        st.markdown("---")

    # ── Weekly task reminder (Thu/Fri) ──
    week_start = today - timedelta(days=weekday)
    week_end   = week_start + timedelta(days=6)
    wc         = get_task_completions(week_start, week_end)
    done_week  = set(l['task'] for logs in wc.values() for l in logs
                     if l['task'] in st.session_state.tasks.get('weekly',[]))
    pending_w  = [t for t in st.session_state.tasks.get('weekly',[]) if t not in done_week]

    if (is_thu or is_fri) and pending_w:
        st.warning(f"🗓️ **{'Thursday' if is_thu else 'Friday'} — Weekly tasks pending:** {', '.join(pending_w)}")
        st.markdown("---")
    elif (is_thu or is_fri) and not pending_w:
        st.success("✅ All weekly tasks done this week!")
        st.markdown("---")

    # ── Monthly task reminder (1st) ──
    mstart  = date(today.year, today.month, 1)
    mend    = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    mc      = get_task_completions(mstart, mend)
    done_m  = set(l['task'] for logs in mc.values() for l in logs
                  if l['task'] in st.session_state.tasks.get('monthly',[]))
    pend_m  = [t for t in st.session_state.tasks.get('monthly',[]) if t not in done_m]
    if is_first and pend_m:
        st.warning(f"📆 **First of the month — monthly tasks due:** {', '.join(pend_m[:5])}"
                   + (f" and {len(pend_m)-5} more..." if len(pend_m) > 5 else ""))
        st.markdown("---")

    # ── Active meds ──
    active_meds = get_active_medications_today()
    if active_meds:
        st.subheader("💊 Active Medicines / Treatments Today")
        for m in active_meds:
            dl = m['days_left']
            urg = "🔴" if dl == 0 else "🟠" if dl <= 2 else "🟢"
            note = "**Last dose today!**" if dl == 0 else f"**{dl} day(s) left**" if dl <= 2 else f"{dl} days left"
            st.info(f"{urg} **{m['cat']}** — **{m['name']}** [{m['type']}]"
                    + (f" ({m['dosage']})" if m['dosage'] else "")
                    + (f" · {m['frequency']}" if m['frequency'] else "")
                    + f" · Until {m['end_date']} · {note}")
        st.markdown("---")

    # ── Quick stats ──
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

    # ── Quick summary: all cats at a glance ──
    st.markdown("---")
    st.subheader("📋 This Week at a Glance")
    week_ago  = today - timedelta(days=7)
    comp_rows = []
    concerns_summary = []

    for cat in st.session_state.cats:
        a  = analyze_cat_health(cat)
        mr = a.get('metric_ratings', {})
        if a['status'] == 'no_data':
            comp_rows.append({'Cat': cat, 'Status': '⬜ No data',
                              'Water': '—', 'Food': '—', 'Litter': '—', 'Mood': '—', 'Poop': '—'})
        else:
            status_icon = '✅ Healthy' if not a['concerns'] else f"⚠️ {len(a['concerns'])} concern(s)"
            comp_rows.append({
                'Cat':    cat,
                'Status': status_icon,
                'Water':  f"{mr.get('water',{}).get('icon','')} {a['water_avg']:.1f}/day",
                'Food':   f"{mr.get('food',{}).get('icon','')} {a['food_avg']:.1f}/day",
                'Litter': f"{mr.get('litter',{}).get('icon','')} {a['litter_avg']:.1f}/day",
                'Mood':   f"{a.get('mood_icon','')} {a.get('mood_trend','').title()}",
                'Poop':   f"{a.get('poop_icon','')} {a.get('poop_days',0)}/{a['total_days']}d"
            })
            if a['concerns']:
                concerns_summary.append((cat, a['concerns']))

    st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

    if concerns_summary:
        st.markdown("**⚠️ Active concerns this week:**")
        for cat, concerns in concerns_summary:
            for _, cr in concerns:
                st.warning(f"**{cat}:** {cr['msg'][:180]}...")
    else:
        st.success("✅ All three cats look healthy based on this week's logged data!")

    # ── Comparison chart ──
    st.markdown("---")
    st.subheader("📊 Weekly Comparison Chart")
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
        fig.add_trace(go.Bar(name='Avg Water',  x=cdf['Cat'], y=cdf['Avg Water'],  marker_color='#4fc3f7'))
        fig.add_trace(go.Bar(name='Avg Food',   x=cdf['Cat'], y=cdf['Avg Food'],   marker_color='#81c784'))
        fig.add_trace(go.Bar(name='Avg Litter', x=cdf['Cat'], y=cdf['Avg Litter'], marker_color='#ffb74d'))
        # Add normal range reference lines
        fig.add_hline(y=3, line_dash="dot", line_color="#4fc3f7", opacity=0.5, annotation_text="Water ideal min (3)")
        fig.add_hline(y=3, line_dash="dot", line_color="#81c784", opacity=0.5)
        fig.add_hline(y=2, line_dash="dot", line_color="#ffb74d", opacity=0.5, annotation_text="Litter ideal min (2)")
        fig.update_layout(barmode='group', height=300, margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Dotted lines = minimum ideal values. 🟢 Above ideal · 🟡 Acceptable · 🔴 Below ideal")
    else:
        st.info("No data logged this week.")

    # ── PDF ──
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

    # ── In-depth per-cat analysis ──
    st.markdown("---")
    st.subheader("🔬 In-Depth Analysis — Per Cat")
    st.caption("Each metric is rated against normal ranges with explanations of what it means and what to do.")
    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            a = analyze_cat_health(cat)
            if a['status'] == 'no_data':
                st.info(f"No data logged yet for {cat}.")
                continue

            profile = a.get('profile', {})
            info = []
            if profile.get('age'):    info.append(f"Age: {profile['age']}")
            if profile.get('breed'):  info.append(f"Breed: {profile['breed']}")
            if profile.get('weight'): info.append(f"Weight: {profile['weight']} kg")
            if info: st.markdown(" · ".join(info))
            st.markdown(f"**{a['total_days']} days tracked · {a['total_entries']} total entries**")

            mr = a.get('metric_ratings', {})
            st.markdown("---")
            st.markdown("#### 📊 Metric Analysis")

            for key, rng_key, label in [
                ('water',  'water_drinks',     '💧 Water Intake'),
                ('food',   'food_eats',        '🍽️ Food Intake'),
                ('litter', 'litter_box_times', '🚽 Litter Box Usage'),
            ]:
                m   = mr.get(key, {})
                rng = HEALTH_RANGES.get(rng_key, {})
                st.markdown(f"**{m.get('icon','')} {label}**")
                col1,col2 = st.columns([1,2])
                with col1:
                    st.metric("Current avg",    f"{m.get('avg',0):.1f}/day")
                    st.write(f"Ideal: {m.get('ideal','—')}  \nOk: {m.get('ok','—')}")
                with col2:
                    st.write(m.get('msg',''))
                st.markdown("")

            # Mood
            st.markdown(f"**{a.get('mood_icon','')} Mood Trend**")
            st.write(a.get('mood_msg',''))

            # Poop
            st.markdown(f"**{a.get('poop_icon','')} Bowel Movements**")
            st.write(a.get('poop_msg',''))

            # Litter quality alerts
            if a.get('litter_issues'):
                st.markdown("---")
                st.markdown("**🚨 Litter Quality Alerts:**")
                for dd, iss in a['litter_issues'][:5]: st.error(f"- {dd}: {iss}")

            # Active meds
            meds = [m for m in get_active_medications_today() if m['cat'] == cat]
            if meds:
                st.markdown("---")
                st.markdown("**💊 Active Medicines/Treatments:**")
                for m in meds:
                    st.info(f"{m['name']} [{m['type']}]"
                            + (f" — {m['dosage']}" if m['dosage'] else "")
                            + f" · until {m['end_date']} · {m['days_left']} days left")

            # Day breakdown
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

            # Vet
            if a.get('vet_history'):
                recent = sorted(a['vet_history'], key=lambda x: x.get('date',''), reverse=True)[:2]
                if recent:
                    st.markdown("---")
                    st.markdown("**🏥 Recent Vet Visits:**")
                    for v in recent:
                        st.write(f"- {v.get('date','?')}: {v.get('reason','Checkup')} — Dr. {v.get('doctor','?')}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DATA MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def data_management_page():
    st.header("⚙️ Data Management")
    st.warning("⚠️ Actions here permanently delete data.")

    st.subheader("📥 Export")
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
    st.subheader("🗑️ Delete Specific Data")
    c1,c2 = st.columns(2)
    with c1:
        ctd = st.selectbox("Delete health data for:", [""]+st.session_state.cats, key="del_cat_h")
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
                    del st.session_state.task_logs[str(cur)]; n += 1
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
                'active_foods':['Pro Plan Adult Wet','Pro Plan Adult Dry','Unseasoned Boiled Chicken','Freeze-Dried Treats']}
            for c in st.session_state.cats
        }
        st.session_state.food_library  = [dict(f) for f in DEFAULT_FOOD_LIBRARY]
        st.session_state.last_entries  = {c: None for c in st.session_state.cats}
        st.session_state.data_loaded   = False
        for f in ['health_data.json','task_logs.json','cat_profiles.json',
                  'diet_settings.json','food_library.json']:
            try:
                if os.path.exists(f): os.remove(f)
            except: pass
        st.success("Reset complete!"); time.sleep(1); st.rerun()

    st.markdown("---")
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Health Entries",   sum(len(v) for cd in st.session_state.health_data.values() for v in cd.values()))
    with c2: st.metric("Task Completions", sum(len(l) for l in st.session_state.task_logs.values()))
    with c3: st.metric("Vet Visits",       sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))


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

        if date.today().weekday() in [3, 4]:
            st.info("🪥 Thursday/Friday — grooming day! Log grooming in Add Health Entry.")

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
        "🏥 Cat Health Guide",
        "⚙️ Data Management"
    ])

    if AUTH_ENABLED: st.sidebar.success("🔐 Security: Enabled")
    else:            st.sidebar.warning("⚠️ Security: Disabled")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Need Help?")
    st.sidebar.markdown(
        "[Ask the AI Assistant 🤖]"
        "(https://thaura.ai/?chatId=eb1bb2bf-acf0-4f6c-99c4-660a0a4fd728)")

    check_reminders()

    if   page == "🎯 Dashboard":        dashboard_page()
    elif page == "🐱 Cat Profiles":     cat_profiles_page()
    elif page == "📝 Add Health Entry": add_health_entry_page()
    elif page == "📊 View Health Data": view_health_data_page()
    elif page == "📋 Task Management":  task_management_page()
    elif page == "🥗 Diet Planning":    diet_planning_page()
    elif page == "🏥 Cat Health Guide": cat_health_guide_page()
    elif page == "⚙️ Data Management":  data_management_page()


if __name__ == "__main__":
    main()
