"""
Cat Health Tracker — Haku · Kuro · Sonic
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
# Last events:
#   Deworming:       26-Apr-2026
#   Annual checkup:  26-Apr-2026
#   Vaccines:        03-Dec-2025
#   Vet visit:       26-Apr-2026
#
# Intervals:
#   Haku/Sonic deworming: every 3 months
#   Kuro deworming:       every 4 months
#   All annual checkup:   every 12 months
#   All vaccines:         every 12 months
#   All vet visits:       every 4 months

def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    import calendar as cal
    day = min(d.day, cal.monthrange(year, month)[1])
    return date(year, month, day)

_LAST_DEWORMING  = date(2026, 4, 26)
_LAST_CHECKUP    = date(2026, 4, 26)
_LAST_VACCINES   = date(2025, 12, 3)
_LAST_VET_VISIT  = date(2026, 4, 26)

DEFAULT_VET_SCHEDULE = {
    'Haku':  {
        'next_checkup':       str(_add_months(_LAST_CHECKUP,   12)),
        'next_vaccines':      str(_add_months(_LAST_VACCINES,  12)),
        'next_deworming':     str(_add_months(_LAST_DEWORMING,  3)),
        'next_vet_visit':     str(_add_months(_LAST_VET_VISIT,  4)),
    },
    'Kuro':  {
        'next_checkup':       str(_add_months(_LAST_CHECKUP,   12)),
        'next_vaccines':      str(_add_months(_LAST_VACCINES,  12)),
        'next_deworming':     str(_add_months(_LAST_DEWORMING,  4)),
        'next_vet_visit':     str(_add_months(_LAST_VET_VISIT,  4)),
    },
    'Sonic': {
        'next_checkup':       str(_add_months(_LAST_CHECKUP,   12)),
        'next_vaccines':      str(_add_months(_LAST_VACCINES,  12)),
        'next_deworming':     str(_add_months(_LAST_DEWORMING,  3)),
        'next_vet_visit':     str(_add_months(_LAST_VET_VISIT,  4)),
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
            'daily': [
                'Clean food bowl', 'Add water', 'Clean litter box',
                'Let them out my room', 'Pray for them', 'Play with them'
            ],
            'weekly': ['Clean water fountain', 'Clean room', 'Clean air purifier'],
            'monthly': [
                'Deep clean litter box', 'Buy food', 'Buy wet food',
                'Buy litter', 'Buy treats', 'Buy toys',
                'Clean cat tree', 'Clean bedding', 'Clean air purifier filter'
            ],
            'quarterly': []
        }
    else:
        daily = st.session_state.tasks.get('daily', [])
        if 'Play with them' not in daily:
            daily.append('Play with them')
            st.session_state.tasks['daily'] = daily
        # Remove grooming from tasks if it crept in
        for freq in ['daily', 'weekly', 'monthly']:
            grooming_items = ['Clean eyes', 'Clean chin', 'Brush Fur', 'Trim Nails',
                              'Clean Ears', 'Clean Eyes', 'Clean Chin', 'Dental Care',
                              'Clean air purifier', 'Clean air purifier filter',
                              'Clean bedding', 'Clean cat tree']
            # Only keep the ones that belong
            pass  # keep as-is

    if 'task_logs' not in st.session_state:
        st.session_state.task_logs = {}

    if 'last_entries' not in st.session_state:
        st.session_state.last_entries = {cat: None for cat in st.session_state.cats}

    if 'last_reminder' not in st.session_state:
        st.session_state.last_reminder = None

    if 'cat_profiles' not in st.session_state:
        st.session_state.cat_profiles = {
            cat: {
                'age': '', 'breed': '', 'weight': '', 'vet_visits': [], 'notes': '',
                'birthdate': '',
                **DEFAULT_VET_SCHEDULE[cat]
            }
            for cat in ['Haku', 'Kuro', 'Sonic']
        }
    else:
        # Ensure vet schedule keys exist and are pre-filled if empty
        for cat in st.session_state.cats:
            profile = st.session_state.cat_profiles.get(cat, {})
            for key, val in DEFAULT_VET_SCHEDULE.get(cat, {}).items():
                if not profile.get(key):
                    profile[key] = val
            st.session_state.cat_profiles[cat] = profile

    if 'diet_settings' not in st.session_state:
        st.session_state.diet_settings = {
            cat: {
                'default_dry_food': 'Pro Plan Adult',
                'default_wet_food': 'Pro Plan Adult Wet',
                'meals_per_day': 3,
                'dry_grams_per_meal': 30,
                'wet_grams_per_meal': 85,
                'notes': ''
            }
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
        }
        for fname, data_str in blobs.items():
            if AUTH_ENABLED:
                try: data_str = encrypt_data(data_str)
                except: pass
            with open(fname, 'w') as f:
                f.write(data_str)
    except Exception as e:
        st.error(f"Error saving data: {e}")


def _read_file(fname):
    if not os.path.exists(fname):
        return None
    with open(fname, 'r') as f:
        raw = f.read()
    if AUTH_ENABLED and raw:
        try: raw = decrypt_data(raw)
        except: pass
    return raw or None


def load_data():
    """Runs only once per browser session — never overwrites live state."""
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
                if 'vet_visits' in profile and isinstance(profile['vet_visits'], list):
                    if profile['vet_visits'] and isinstance(profile['vet_visits'][0], str):
                        profile['vet_visits'] = []
                # Ensure vet schedule keys pre-filled
                for key, val in DEFAULT_VET_SCHEDULE.get(cat, {}).items():
                    if not profile.get(key):
                        profile[key] = val
                profile.setdefault('birthdate', '')
            st.session_state.cat_profiles = loaded

        s = _read_file('diet_settings.json')
        if s:
            loaded_d = json.loads(s)
            for cat in st.session_state.cats:
                if cat in loaded_d:
                    st.session_state.diet_settings[cat].update(loaded_d[cat])

        st.session_state.data_loaded = True
    except Exception as e:
        st.error(f"Error loading data: {e}")
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
    if idx < len(arr):
        arr[idx].update(data); save_data()


def delete_health_entry(cat_name, ts, idx):
    arr = st.session_state.health_data.get(cat_name, {}).get(ts, [])
    if idx < len(arr):
        arr.pop(idx)
        if not arr:
            del st.session_state.health_data[cat_name][ts]
        save_data()


# ══════════════════════════════════════════════════════════════════════════════
# TASKS
# ══════════════════════════════════════════════════════════════════════════════
def add_task_completion(task_name: str, cat_name: str = None, notes: str = ""):
    today = str(date.today())
    st.session_state.task_logs.setdefault(today, [])
    st.session_state.task_logs[today].append({
        'task': task_name, 'cat': cat_name,
        'completed_at': datetime.now().isoformat(), 'notes': notes
    })
    save_data()


def get_task_completions(start_date: date, end_date: date) -> Dict:
    out = {}
    for ds, logs in st.session_state.task_logs.items():
        try:
            if start_date <= date.fromisoformat(ds) <= end_date:
                out[ds] = logs
        except: continue
    return out


# ══════════════════════════════════════════════════════════════════════════════
# DAILY AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════
def get_daily_aggregated(cat_name: str, start_date: date, end_date: date) -> Dict:
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
                'reason':     entry.get('medication_reason', ''),
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
                'water_avg': 0, 'food_avg': 0, 'litter_avg': 0,
                'mood_trend': 'unknown', 'litter_issues': [],
                'concerns': [], 'recommendations': [], 'positives': []}

    total_days    = len(daily)
    total_entries = sum(d['entry_count'] for d in daily.values())
    water_avg     = sum(d['water_drinks']     for d in daily.values()) / total_days
    food_avg      = sum(d['food_eats']        for d in daily.values()) / total_days
    litter_avg    = sum(d['litter_box_times'] for d in daily.values()) / total_days
    poop_days     = sum(1 for d in daily.values() if d.get('pooped'))

    all_moods  = [m for d in daily.values() for m in d['moods']]
    mood_trend = 'stable'
    if all_moods:
        poor = sum(1 for m in all_moods if m in ['Very Poor', 'Poor'])
        good = sum(1 for m in all_moods if m in ['Good', 'Excellent'])
        if poor > len(all_moods) / 2:   mood_trend = 'declining'
        elif good > len(all_moods) / 2: mood_trend = 'good'

    all_litter_issues = [
        (str(ed), iss)
        for ed, d in daily.items()
        for iss in d['litter_quality_issues']
        if any(kw in iss.lower() for kw in ['blood', 'diarrhea', 'diarrhoea',
                                              'abnormal', 'mucus', 'black', 'red'])
    ]

    concerns, recommendations, positives = [], [], []

    # ── Water ──
    if water_avg >= 3:
        positives.append(
            f"💧 **Excellent hydration** — {water_avg:.1f} drinks/day. "
            "This directly protects the kidneys and urinary tract. "
            "Cats who drink well have dramatically lower risk of CKD and urinary blockages. Keep it up.")
    elif water_avg >= 1:
        concerns.append(f"💧 Moderate water intake ({water_avg:.1f}/day).")
        recommendations.append(
            "**Why this matters:** Cats naturally have low thirst drive — they evolved to get moisture from prey. "
            "Low water intake is the #1 cause of kidney disease and urinary crystals in domestic cats. "
            "**What to do:** Add a water fountain (running water is far more appealing), increase wet food, "
            "and place water bowls away from food bowls (cats avoid water near their food instinctively).")
    else:
        concerns.append(f"💧 Very low water intake ({water_avg:.1f}/day) — this needs immediate attention.")
        recommendations.append(
            "**This is a serious concern.** Chronic dehydration is the leading cause of kidney disease in cats. "
            "**Action steps:** 1) Add wet food to every meal immediately. 2) Get a water fountain. "
            "3) Try adding a tiny amount of low-sodium chicken broth to water. "
            "4) If this persists more than 3-4 days, vet check — dehydration can spiral quickly.")

    # ── Food ──
    if food_avg >= 3:
        positives.append(
            f"🍽️ **Great eating pattern** — {food_avg:.1f} meals/day. "
            "Three or more small meals matches a cat's natural rhythm, keeps metabolism stable, "
            "prevents hunger-induced vomiting of bile, and reduces food-obsession behaviour.")
    elif food_avg >= 2:
        positives.append(
            f"🍽️ Food intake is normal ({food_avg:.1f} meals/day). "
            "Consistent eating is a strong health indicator.")
    elif food_avg >= 1:
        concerns.append(f"🍽️ Below-expected food intake ({food_avg:.1f} meals/day).")
        recommendations.append(
            "**Why this matters:** Reduced appetite is often the first sign of illness in cats. "
            "It can indicate dental pain, nausea, respiratory issues (can't smell food), or systemic illness. "
            "**What to do:** Try warming wet food slightly, offer a different texture, and monitor for 48 hours. "
            "If appetite doesn't improve: vet visit.")
    else:
        concerns.append(f"🍽️ Very low food intake ({food_avg:.1f} meals/day) — urgent.")
        recommendations.append(
            "**Not eating is an emergency in cats.** Within 48-72 hours of not eating, cats can develop "
            "hepatic lipidosis (fatty liver disease) — a life-threatening condition. "
            "Do NOT wait — if a cat hasn't eaten in 24+ hours, contact your vet today.")

    # ── Litter ──
    if 2 <= litter_avg <= 5:
        positives.append(
            f"🚽 Normal litter usage ({litter_avg:.1f}x/day). "
            "This range suggests healthy kidney function and normal hydration. "
            "For kidney monitoring, this is an important baseline to track.")
    elif litter_avg > 5:
        concerns.append(f"🚽 High litter box usage ({litter_avg:.1f}x/day).")
        recommendations.append(
            "**Why this matters:** Frequent urination can signal a UTI, urinary crystals, stress-induced FLUTD, "
            "early kidney disease, or diabetes. Watch for: straining, blood, crying in the box. "
            "**If straining with no urine produced: this is an emergency.** "
            "Otherwise, book a vet check within a few days.")
    elif litter_avg < 1 and total_days >= 3:
        concerns.append(f"🚽 Infrequent litter usage ({litter_avg:.1f}x/day).")
        recommendations.append(
            "**Why this matters:** Cats who don't urinate frequently may be dehydrated or avoiding the box. "
            "A cat who hasn't urinated in 24+ hours needs urgent vet attention — possible blockage.")

    # ── Poop ──
    if poop_days >= total_days * 0.8:
        positives.append(
            f"✅ Regular bowel movements ({poop_days}/{total_days} days logged). "
            "Consistent daily pooping indicates healthy digestion, good hydration, and a working gut.")
    elif total_days >= 3 and poop_days == 0:
        concerns.append("💩 No poop logged this week.")
        recommendations.append(
            "**This could mean** the poop checkbox isn't being used, OR actual constipation. "
            "If genuinely not pooping, cats should have a bowel movement at least every 24-36 hours. "
            "Constipation can cause toxin build-up and significant discomfort. "
            "Increase wet food, water, and movement. Vet visit if it's been 48+ hours.")

    # ── Mood ──
    if mood_trend == 'good':
        positives.append(
            "😊 Mood has been consistently good this week. "
            "A happy, engaged cat has lower cortisol (stress hormone), stronger immune function, "
            "and is less prone to stress-induced FLUTD. This is a real health indicator, not just a nice-to-have.")
    elif mood_trend == 'declining':
        concerns.append("😟 Mood has been declining this week.")
        recommendations.append(
            "**Why this matters:** In cats, a declining mood is often the earliest signal of physical illness — "
            "before any other symptoms appear. Cats hide pain well. "
            "**What to check:** Look for subtle signs — is the cat less playful? Eating slower? "
            "Sleeping in different spots? Any physical changes? Book a vet check if it persists 2-3 days.")

    # ── Litter quality ──
    if all_litter_issues:
        concerns.append(f"⚠️ Litter quality issues detected ({len(all_litter_issues)} times).")
        recommendations.append(
            "**Any abnormality in stool or urine always warrants a vet visit.** "
            "Blood in urine = possible UTI or blockage (emergency if straining). "
            "Blood in stool = possible GI issue. Diarrhoea for 24+ hrs = vet check. "
            "Don't wait — these can escalate rapidly in cats.")

    if not concerns:
        recommendations.append(
            "All key health indicators look good this week. "
            "Your consistent monitoring is exactly what allows early detection of any changes. "
            "Keep logging daily — the baseline data you're building is invaluable for future vet consultations.")

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
        'litter_issues':   all_litter_issues,
        'concerns':        concerns,
        'recommendations': recommendations,
        'positives':       positives
    }


def get_active_medications_today() -> List[Dict]:
    today = date.today()
    active, seen = [], set()
    for cat in st.session_state.cats:
        for entry in get_health_entries(cat, today - timedelta(days=90), today):
            mn  = entry.get('medication_name', '').strip()
            ss  = entry.get('medication_start_date', '')
            es  = entry.get('medication_end_date', '')
            if not all([mn, ss, es]): continue
            try: ms, me = date.fromisoformat(ss), date.fromisoformat(es)
            except: continue
            key = f"{cat}_{mn}_{es}"
            if key in seen: continue
            seen.add(key)
            if ms <= today <= me:
                active.append({
                    'cat': cat, 'name': mn,
                    'type':      entry.get('medication_type', 'Oral'),
                    'dosage':    entry.get('medication_dosage', ''),
                    'frequency': entry.get('medication_frequency', ''),
                    'end_date':  es,
                    'days_left': (me - today).days
                })
    return active


# ══════════════════════════════════════════════════════════════════════════════
# VET REMINDERS
# ══════════════════════════════════════════════════════════════════════════════
def get_vet_reminders() -> List[Dict]:
    today = date.today()
    reminders = []
    labels = {
        'next_checkup':   'Annual Checkup (Blood work, Dental, Chest X-ray, Breathing)',
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
                    reminders.append({
                        'cat':       cat,
                        'label':     label,
                        'next_date': val,
                        'days_away': (nd - today).days,
                        'overdue':   nd < today
                    })
                except:
                    reminders.append({'cat': cat, 'label': label,
                                      'next_date': 'Invalid date', 'days_away': None, 'overdue': False})
            else:
                reminders.append({'cat': cat, 'label': label,
                                  'next_date': 'Not set', 'days_away': None, 'overdue': False})
    return reminders


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD SUMMARY TEXT
# ══════════════════════════════════════════════════════════════════════════════
def generate_cat_summary(cat_name: str) -> str:
    a = analyze_cat_health(cat_name)
    profile = a.get('profile', {})

    if a['status'] == 'no_data':
        return (f"No health data recorded yet for **{cat_name}**. "
                "Start adding entries to see a full analysis here.")

    lines = [f"### 🐱 {cat_name}"]
    info = []
    if profile.get('age'):    info.append(f"Age: {profile['age']}")
    if profile.get('breed'):  info.append(f"Breed: {profile['breed']}")
    if profile.get('weight'): info.append(f"Weight: {profile['weight']} kg")
    if info: lines.append(" · ".join(info))

    lines.append(
        f"\n**Period:** Past 7 days &nbsp;|&nbsp; "
        f"**Days tracked:** {a['total_days']} &nbsp;|&nbsp; "
        f"**Total entries:** {a['total_entries']}")

    lines.append("\n**📊 Daily averages:**")
    lines.append(f"- 💧 Water: **{a['water_avg']:.1f}** drinks/day")
    lines.append(f"- 🍽️ Food: **{a['food_avg']:.1f}** meals/day")
    lines.append(f"- 🚽 Litter box: **{a['litter_avg']:.1f}** times/day")
    lines.append(f"- 💩 Poop days: **{a.get('poop_days',0)}/{a['total_days']}** days")
    lines.append(f"- 😊 Mood trend: **{a.get('mood_trend','unknown').title()}**")

    # Day breakdown
    if a['daily']:
        lines.append("\n**📅 Day-by-day breakdown:**")
        for dd in sorted(a['daily'].keys(), reverse=True)[:7]:
            d = a['daily'][dd]
            parts = []
            if d['water_drinks']:     parts.append(f"💧{d['water_drinks']}x water")
            if d['food_eats']:        parts.append(f"🍽️{d['food_eats']}x food")
            if d['litter_box_times']: parts.append(f"🚽{d['litter_box_times']}x litter")
            if d['pooped']:           parts.append("💩✅")
            if d['grooming_tasks']:   parts.append(f"🪥{', '.join(d['grooming_tasks'])}")
            if d['food_log']:         parts.append(f"🥣{', '.join(set(d['food_log']))}")
            lbl = f"({d['entry_count']} {'entry' if d['entry_count']==1 else 'entries'})"
            lines.append(f"- **{dd}** {lbl}: {' · '.join(parts) if parts else 'Nothing logged'}")

    # Positives
    if a['positives']:
        lines.append("\n**✅ What's going well:**")
        for p in a['positives']: lines.append(f"- {p}")

    # Concerns + deep explanations
    if a['concerns']:
        lines.append("\n**⚠️ Concerns:**")
        for c in a['concerns']: lines.append(f"- {c}")
        lines.append("\n**💡 In-depth recommendations:**")
        for r in a['recommendations']: lines.append(f"- {r}")
    else:
        lines.append("\n**✅ No concerns this week.**")
        for r in a['recommendations']: lines.append(f"- {r}")

    # Litter alerts
    if a.get('litter_issues'):
        lines.append("\n**🚨 Litter quality alerts:**")
        for dd, iss in a['litter_issues'][:5]: lines.append(f"- {dd}: {iss}")

    # Active meds
    meds = [m for m in get_active_medications_today() if m['cat'] == cat_name]
    if meds:
        lines.append("\n**💊 Active medicines/treatments:**")
        for m in meds:
            lines.append(f"- {m['name']} [{m['type']}]"
                         + (f" — {m['dosage']}" if m['dosage'] else "")
                         + f" · until {m['end_date']} · {m['days_left']} days left")

    # Vet
    if a.get('vet_history'):
        recent = sorted(a['vet_history'], key=lambda x: x.get('date',''), reverse=True)[:2]
        if recent:
            lines.append("\n**🏥 Recent vet visits:**")
            for v in recent:
                lines.append(f"- {v.get('date','?')}: {v.get('reason','Checkup')} — Dr. {v.get('doctor','?')}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# PDF REPORT
# ══════════════════════════════════════════════════════════════════════════════
def generate_pdf_report(cat_name: str = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    ts_ = ParagraphStyle('T', parent=styles['Title'],   fontSize=18, spaceAfter=4, textColor=colors.HexColor('#2c3e50'))
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
            if p.get(key):
                pd_.append([lbl, f"{p[key]} kg" if key=='weight' else p[key]])
        if len(pd_) > 1:
            story += [tbl(pd_,[5*cm,11*cm],colors.HexColor('#2980b9')), Spacer(1,6)]

        story.append(Paragraph("Weekly Health Summary", ss_))
        if a['status'] == 'no_data':
            story.append(Paragraph("No data recorded.", ns_))
        else:
            sd = [["Metric","Value"],
                  ["Days Tracked",   str(a['total_days'])],
                  ["Total Entries",  str(a['total_entries'])],
                  ["Avg Water/Day",  f"{a['water_avg']:.1f}"],
                  ["Avg Food/Day",   f"{a['food_avg']:.1f}"],
                  ["Avg Litter/Day", f"{a['litter_avg']:.1f}"],
                  ["Poop Days",      f"{a.get('poop_days',0)}/{a['total_days']}"],
                  ["Mood Trend",     a.get('mood_trend','unknown').title()],
                  ["Status",         a['status'].title()]]
            story += [tbl(sd,[7*cm,9*cm],colors.HexColor('#27ae60')), Spacer(1,6)]
            if a['concerns']:
                story.append(Paragraph("Concerns", ss_))
                for c in a['concerns']:   story.append(Paragraph(f"- {c}", ns_))
                story.append(Paragraph("Recommendations", ss_))
                for r in a['recommendations']: story.append(Paragraph(f"- {r}", ns_))
                story.append(Spacer(1,4))
            meds = [m for m in get_active_medications_today() if m['cat']==cat]
            if meds:
                story.append(Paragraph("Active Medicines/Treatments", ss_))
                md = [["Name","Type","Dosage","Frequency","Until"]]
                for m in meds:
                    md.append([m['name'],m.get('type','Oral'),m.get('dosage','-'),
                               m.get('frequency','-'),m['end_date']])
                story += [tbl(md,[3*cm,2*cm,2.5*cm,3*cm,5.5*cm],colors.HexColor('#e74c3c')), Spacer(1,6)]

        vv = p.get('vet_visits', [])
        if vv:
            story.append(Paragraph("Vet History", ss_))
            vd = [["Date","Doctor","Reason","Medication"]]
            for v in sorted(vv, key=lambda x: x.get('date',''), reverse=True):
                vd.append([v.get('date','-'),f"Dr. {v.get('doctor','-')}",
                           v.get('reason','-'),v.get('medication','-')])
            story += [tbl(vd,[3*cm,4*cm,5*cm,4*cm],colors.HexColor('#8e44ad'))]

        story += [Spacer(1,12),
                  HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#bdc3c7'),spaceAfter=10)]

    story.append(Paragraph("Cat Health Tracker — Always consult your vet for medical advice.", cs_))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# MONTHLY CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
def monthly_task_calendar(year: int, month: int):
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
                     else f"**{day}** 📍" if d == date.today()
                     else str(day))
            if day == 1: label = "🔔 " + label
            cols[i].markdown(label)

    done_set = set(t for tl in done_dates.values() for t in tl)
    st.markdown(f"**Completed this month:** {len(done_set)}/{len(monthly_tasks)}")
    if done_set:   st.success("Done: " + ", ".join(sorted(done_set)))
    rem = [t for t in monthly_tasks if t not in done_set]
    if rem: st.warning("Still needed: " + ", ".join(rem))


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
                st.markdown("## 🐱")
                st.markdown(f"**{cat}**")
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
            with st.expander(f"✏️ Edit {cat}'s Profile", expanded=True):
                c1,c2 = st.columns(2)
                with c1:
                    st.text_input("Age",          value=profile.get('age',''),      key=f"edit_age_{cat}")
                    st.text_input("Breed",        value=profile.get('breed',''),    key=f"edit_breed_{cat}")
                    st.text_input("Weight (kg)",  value=profile.get('weight',''),   key=f"edit_weight_{cat}")
                    st.text_input("Birthdate",    value=profile.get('birthdate',''),key=f"edit_bd_{cat}",
                                  placeholder="YYYY-MM-DD")
                with c2:
                    st.text_area("Notes", value=profile.get('notes',''), key=f"edit_notes_{cat}", height=70)

                st.markdown("**📅 Next Scheduled Vet Appointments**")
                vc1,vc2 = st.columns(2)
                with vc1:
                    st.text_input("Next Annual Checkup", value=profile.get('next_checkup',''),
                                  key=f"edit_nc_{cat}", placeholder="YYYY-MM-DD")
                    st.text_input("Next Vaccines",       value=profile.get('next_vaccines',''),
                                  key=f"edit_nv_{cat}", placeholder="YYYY-MM-DD")
                with vc2:
                    st.text_input("Next Deworming",      value=profile.get('next_deworming',''),
                                  key=f"edit_nd_{cat}", placeholder="YYYY-MM-DD")
                    st.text_input("Next Vet Visit",      value=profile.get('next_vet_visit',''),
                                  key=f"edit_nvv_{cat}", placeholder="YYYY-MM-DD")

                s1,s2 = st.columns([1,5])
                with s1:
                    if st.button("💾 Save", key=f"save_basic_{cat}", type="primary"):
                        st.session_state.cat_profiles[cat].update({
                            'age':           st.session_state[f"edit_age_{cat}"],
                            'breed':         st.session_state[f"edit_breed_{cat}"],
                            'weight':        st.session_state[f"edit_weight_{cat}"],
                            'notes':         st.session_state[f"edit_notes_{cat}"],
                            'birthdate':     st.session_state[f"edit_bd_{cat}"],
                            'next_checkup':  st.session_state[f"edit_nc_{cat}"],
                            'next_vaccines': st.session_state[f"edit_nv_{cat}"],
                            'next_deworming':st.session_state[f"edit_nd_{cat}"],
                            'next_vet_visit':st.session_state[f"edit_nvv_{cat}"],
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
                    if to_del and st.button("🗑️ Delete Visit", key=f"del_vis_btn_{cat}", type="secondary"):
                        vv.pop(opts.index(to_del))
                        st.session_state.cat_profiles[cat]['vet_visits'] = vv
                        save_data(); st.success("Deleted!"); st.rerun()

                st.markdown("---")
                st.markdown("#### ➕ Add Visit")
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
                            'medication': st.session_state[f"v_med_{cat}"]
                        })
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

    # ── Edit mode ──
    if st.session_state.editing_health_entry and st.session_state.edit_entry_data:
        st.subheader("✏️ Edit Health Entry")
        ec  = st.session_state.edit_entry_cat
        ets = st.session_state.edit_entry_data.get('timestamp','')
        ei  = st.session_state.edit_entry_data.get('index',0)
        oe  = None
        arr = st.session_state.health_data.get(ec,{}).get(ets,[])
        if ei < len(arr): oe = arr[ei]

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
                st.subheader("💊 Medicine / Treatment (Optional)")
                with st.expander("Edit Medicine/Treatment"):
                    mn  = st.text_input("Name",      value=oe.get('medication_name',''))
                    mty_opts = ["Oral","Nebulizer","Injection","Topical","Eye drops","Ear drops","Other"]
                    mty = st.selectbox("Type", mty_opts,
                                       index=mty_opts.index(oe.get('medication_type','Oral')))
                    md  = st.text_input("Dosage",    value=oe.get('medication_dosage',''))
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
                    ed = {
                        'water_drinks': wd, 'food_eats': fe, 'litter_box_times': lbt,
                        'mood': mood, 'general_appearance': ga, 'pooped': poo,
                        'food_eaten': food_eaten,
                        'litter_quality': lq.split('\n') if lq else [],
                        'notes': notes,
                        'grooming_tasks': {t: c for t,c in gt.items() if c}
                    }
                    if mn:
                        ed.update({'medication_name': mn, 'medication_type': mty,
                                   'medication_dosage': md, 'medication_frequency': mf,
                                   'medication_reason': mr,
                                   'medication_start_date': str(ms),
                                   'medication_end_date':   str(me)})
                    update_health_entry(ec, ets, ei, ed)
                    st.success(f"✅ Updated for {ec}!")
                    st.session_state.editing_health_entry = False
                    st.session_state.edit_entry_data = {}
                    st.rerun()

        if st.button("❌ Cancel Edit"):
            st.session_state.editing_health_entry = False
            st.session_state.edit_entry_data = {}
            st.rerun()
        return

    # ── New entry ──
    st.subheader("🆕 Add New Health Entry")
    selected_cat = st.selectbox("Select Cat", st.session_state.cats, key="cat_selector")

    if st.session_state.health_form_cat != selected_cat:
        for k in [k for k in st.session_state if k.startswith("form_")]:
            del st.session_state[k]
        st.session_state.health_form_cat = selected_cat

    ds          = st.session_state.diet_settings.get(selected_cat, {})
    default_food= ds.get('default_dry_food', 'Pro Plan Adult')
    entry_mode  = st.radio("Entry Mode", ["🚀 Quick Entry", "📋 Detailed Entry"])

    if entry_mode == "🚀 Quick Entry":
        st.markdown("### Quick Actions")
        c1,c2,c3,c4 = st.columns(4)
        base_q = {'water_drinks':0,'food_eats':0,'litter_box_times':0,'pooped':False,
                  'mood':'Good','general_appearance':'Good','litter_quality':[],'grooming_tasks':{},'food_eaten':''}
        with c1:
            if st.button("💧 Water Drank"):
                add_health_entry(selected_cat, {**base_q,'water_drinks':1,'notes':'Quick: Water drank'})
                st.success("✅ Water logged!"); st.rerun()
        with c2:
            if st.button("🍽️ Food Eaten"):
                add_health_entry(selected_cat, {**base_q,'food_eats':1,'food_eaten':default_food,
                                                'notes':f'Quick: Food eaten ({default_food})'})
                st.success("✅ Meal logged!"); st.rerun()
        with c3:
            if st.button("🚽 Litter Used"):
                add_health_entry(selected_cat, {**base_q,'litter_box_times':1,'notes':'Quick: Litter used'})
                st.success("✅ Litter logged!"); st.rerun()
        with c4:
            if st.button("💩 Pooped"):
                add_health_entry(selected_cat, {**base_q,'litter_box_times':1,'pooped':True,'notes':'Quick: Pooped'})
                st.success("✅ Poop logged!"); st.rerun()
        st.markdown("---")

    st.markdown("### 📋 Detailed Health Entry")
    with st.form("health_entry_form"):
        c1,c2 = st.columns(2)
        with c1:
            wd  = st.number_input("💧 Water Drinks",     0, 20, 0, key="form_water")
            fe  = st.number_input("🍽️ Food Eats",        0, 10, 0, key="form_food")
            lbt = st.number_input("🚽 Litter Box Times", 0, 15, 0, key="form_litter")
            poo = st.checkbox("💩 Pooped today?",        key="form_poop")
        with c2:
            mood        = st.selectbox("😊 Mood",              ["Very Poor","Poor","Normal","Good","Excellent"], key="form_mood")
            ga          = st.selectbox("✨ General Appearance", ["Poor","Fair","Good","Excellent"],               key="form_appearance")
            lq          = st.text_area("🚨 Litter Quality Issues",
                                       placeholder="e.g., Blood, diarrhea, mucus, abnormal color...",
                                       key="form_litter_quality")
            food_eaten  = st.text_input("🥣 Food eaten", value=default_food, key="form_food_eaten")

        st.markdown("---")
        st.subheader("💊 Medicine / Treatment (Optional)")
        with st.expander("Add Medicine/Treatment"):
            mn  = st.text_input("Name",  placeholder="e.g., Amoxicillin / Nebulizer session", key="form_med_name")
            mty = st.selectbox("Type", ["Oral","Nebulizer","Injection","Topical","Eye drops","Ear drops","Other"], key="form_med_type")
            md  = st.text_input("Dosage",    placeholder="e.g., 50mg / 10 min session", key="form_med_dosage")
            mf  = st.text_input("Frequency", placeholder="e.g., Twice daily",           key="form_med_freq")
            mr  = st.text_input("Reason",    placeholder="e.g., Respiratory support",   key="form_med_reason")
            cs1,ce1 = st.columns(2)
            with cs1: ms = st.date_input("Start Date", value=date.today(),                   key="form_med_start")
            with ce1: me = st.date_input("End Date",   value=date.today()+timedelta(days=7), key="form_med_end")

        st.markdown("---")
        notes = st.text_area("📝 Additional Notes", height=70,
                             placeholder="Any other observations...", key="form_notes")

        st.markdown("---")
        st.subheader("🪥 Grooming Tasks")
        st.caption("Check only if performed today.")
        g1,g2,g3 = st.columns(3)
        with g1: gb = st.checkbox("Brush Fur",  key="form_g_brush"); gn = st.checkbox("Trim Nails", key="form_g_nails")
        with g2: ge = st.checkbox("Clean Ears", key="form_g_ears");  gy = st.checkbox("Clean Eyes", key="form_g_eyes")
        with g3: gc = st.checkbox("Clean Chin", key="form_g_chin");  gd = st.checkbox("Dental Care",key="form_g_dental")
        gt = {"Brush Fur":gb,"Trim Nails":gn,"Clean Ears":ge,"Clean Eyes":gy,"Clean Chin":gc,"Dental Care":gd}

        if st.form_submit_button("💾 Save Health Entry", type="primary", use_container_width=True):
            ed = {
                'water_drinks': wd, 'food_eats': fe, 'litter_box_times': lbt,
                'mood': mood, 'general_appearance': ga, 'pooped': poo,
                'food_eaten': food_eaten,
                'litter_quality': lq.split('\n') if lq else [],
                'notes': notes,
                'grooming_tasks': {t: c for t,c in gt.items() if c}
            }
            if mn:
                ed.update({'medication_name': mn, 'medication_type': mty,
                           'medication_dosage': md, 'medication_frequency': mf,
                           'medication_reason': mr,
                           'medication_start_date': str(ms),
                           'medication_end_date':   str(me)})
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
        dr = st.date_input("Date Range",
                           value=(date.today()-timedelta(days=30), date.today()),
                           max_value=date.today())
    sd,ed = (dr[0],dr[1]) if len(dr)==2 else (date.today(),date.today())

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
        lbl = f" — {' '.join(pts)}" if pts else ""
        with st.expander(f"📅 {ds} ({len(grp)} entries){lbl}"):
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
                        ms_ = (f"💊 {row['medication_name']} [{row.get('medication_type','Oral')}]"
                               f" ({row.get('medication_dosage','N/A')})")
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
# PAGE: TASK MANAGEMENT  (no grooming section — grooming is in health entry)
# ══════════════════════════════════════════════════════════════════════════════
def task_management_page():
    st.header("📋 Task Management")
    today     = date.today()
    today_str = str(today)
    weekday   = today.weekday()  # 0=Mon … 3=Thu … 4=Fri
    is_thu    = weekday == 3
    is_fri    = weekday == 4
    is_first  = today.day == 1
    completed_today = [l['task'] for l in st.session_state.task_logs.get(today_str, [])]

    # ── Grooming reminder banner (Thu/Fri only, no checkboxes here) ──
    if is_thu or is_fri:
        st.warning(
            f"🪥 **{'Thursday' if is_thu else 'Friday'} reminder — Grooming day!** "
            "Log grooming tasks in the **Add Health Entry** page under Grooming Tasks.")
    else:
        st.caption(f"🪥 Grooming reminder appears on Thursdays & Fridays. Today is {today.strftime('%A')}. "
                   "Log grooming in Add Health Entry.")

    st.markdown("---")

    # ── Daily tasks ──
    st.subheader("📅 Daily Tasks")
    for task in st.session_state.tasks.get('daily', []):
        done    = task in completed_today
        checked = st.checkbox(task, value=done, key=f"task_daily_{task}")
        if checked and not done:
            add_task_completion(task); st.rerun()

    st.markdown("---")

    # ── Weekly tasks — show Thu & Fri, disappear when done until next week ──
    st.subheader("🗓️ Weekly Tasks")
    week_start = today - timedelta(days=weekday)
    week_end   = week_start + timedelta(days=6)
    wc         = get_task_completions(week_start, week_end)
    done_week  = set(l['task'] for logs in wc.values() for l in logs
                     if l['task'] in st.session_state.tasks.get('weekly',[]))

    if is_thu or is_fri:
        st.info(f"🔔 Weekly tasks are due — it's {'Thursday' if is_thu else 'Friday'}!")
        for task in st.session_state.tasks.get('weekly', []):
            if task in done_week:
                st.success(f"✅ {task} — done this week!")
            else:
                if st.checkbox(task, value=False, key=f"task_weekly_{task}"):
                    add_task_completion(task); st.rerun()
    else:
        remaining = [t for t in st.session_state.tasks.get('weekly',[]) if t not in done_week]
        if not remaining:
            st.success("✅ All weekly tasks done this week!")
        else:
            st.write(f"Weekly tasks appear on Thursday & Friday. Remaining: {', '.join(remaining)}")
        done_list = [t for t in st.session_state.tasks.get('weekly',[]) if t in done_week]
        if done_list:
            for t in done_list: st.success(f"✅ {t} — done this week!")

    st.markdown("---")

    # ── Monthly tasks — show on 1st, disappear when done ──
    st.subheader("📆 Monthly Tasks")
    mstart = date(today.year, today.month, 1)
    mend   = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    mc     = get_task_completions(mstart, mend)
    done_m = set(l['task'] for logs in mc.values() for l in logs
                 if l['task'] in st.session_state.tasks.get('monthly',[]))

    if is_first:
        st.warning("🔔 **First of the month** — monthly tasks are due!")
        for task in st.session_state.tasks.get('monthly', []):
            if task in done_m:
                st.success(f"✅ {task} — done this month!")
            else:
                if st.checkbox(task, value=False, key=f"task_monthly_{task}"):
                    add_task_completion(task); st.rerun()
    else:
        remaining_m = [t for t in st.session_state.tasks.get('monthly',[]) if t not in done_m]
        if not remaining_m:
            st.success("✅ All monthly tasks done this month!")
        else:
            st.write(f"Monthly tasks appear on the 1st. Remaining this month: {len(remaining_m)}/{len(st.session_state.tasks.get('monthly',[]))}")
        for t in done_m: st.success(f"✅ {t} — done this month!")

    # ── Monthly calendar ──
    st.markdown("---")
    st.subheader("📅 Monthly Task Calendar")
    c1,c2 = st.columns([1,3])
    with c1:
        cm = st.selectbox("Month", range(1,13), index=today.month-1,
                          format_func=lambda m: calendar.month_name[m])
        cy = st.number_input("Year", 2024, 2030, today.year, step=1)
    with c2:
        monthly_task_calendar(int(cy), int(cm))

    # ── History ──
    st.markdown("---")
    st.subheader("📋 Completion History")
    c1,c2 = st.columns(2)
    with c1: hs = st.date_input("Start", today-timedelta(days=7))
    with c2: he = st.date_input("End",   today)
    comps = get_task_completions(hs, he)
    if not comps:
        st.info("No completions found."); return
    rows = [{'date': ds, 'task': l['task'], 'cat': l.get('cat',''), 'completed_at': l['completed_at']}
            for ds, logs in comps.items() for l in logs]
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    st.dataframe(df.sort_values('date'), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DIET PLANNING  (full nutritional breakdown)
# ══════════════════════════════════════════════════════════════════════════════

# Nutritional database for common cat foods
FOOD_NUTRITION = {
    'Pro Plan Adult': {
        'brand': 'Purina Pro Plan',
        'type': 'Dry',
        'protein_pct': 42,
        'fat_pct': 16,
        'fiber_pct': 3,
        'moisture_pct': 12,
        'ash_pct': 7.5,
        'phosphorus_pct': 1.0,
        'sodium_pct': 0.49,
        'calories_per_100g': 375,
        'taurine': 'Yes — added',
        'omega3': 'Yes — moderate (fish oil)',
        'omega6': 'Yes — good levels',
        'vitamins': 'A, D3, E, B complex — all added',
        'probiotics': 'Yes — Live cultures',
        'notes': (
            "One of the most researched cat foods on the market. "
            "High protein from chicken/turkey as first ingredients. "
            "The phosphorus level (1.0%) is on the moderate-higher side — "
            "cats with early kidney disease should monitor this. "
            "Good for healthy adult cats. Taurine is supplemented which is critical for heart health. "
            "Relatively low in moisture — always supplement with wet food and fresh water."
        ),
        'watch_out': [
            "Phosphorus at 1.0% — higher than ideal for cats with kidney issues (ideal <0.8% for CKD cats)",
            "Low moisture (12%) — must supplement with wet food",
            "Sodium at 0.49% — moderate; watch for cats with heart conditions",
        ],
        'strengths': [
            "High protein (42%) — excellent for muscle maintenance",
            "Taurine added — essential for heart and eye health",
            "Omega-3 from fish oil — supports skin, coat, and inflammation",
            "Probiotics — good for gut health and immune function",
            "Real meat as first ingredient",
        ]
    },
    'Pro Plan Adult Wet': {
        'brand': 'Purina Pro Plan',
        'type': 'Wet',
        'protein_pct': 11,
        'fat_pct': 4,
        'fiber_pct': 1,
        'moisture_pct': 78,
        'ash_pct': 2,
        'phosphorus_pct': 0.2,
        'sodium_pct': 0.15,
        'calories_per_100g': 85,
        'taurine': 'Yes — added',
        'omega3': 'Yes — good levels',
        'omega6': 'Yes',
        'vitamins': 'A, D3, E, B complex — all added',
        'probiotics': 'No',
        'notes': (
            "Excellent hydration source — 78% moisture closely mirrors a cat's natural prey diet (~70-75% water). "
            "Lower phosphorus (0.2%) is much safer for kidney health than dry food. "
            "Lower in calories per gram — good for weight management. "
            "Protein on a dry-matter basis is actually very high (~50%). "
            "Highly recommended as the primary food source for cats, especially those with urinary or kidney concerns."
        ),
        'watch_out': [
            "Lower calorie density — cats may need more volume to meet energy needs",
            "Spoils quickly once opened — refrigerate and use within 24-48 hours",
            "Can cause loose stools in cats with sensitive digestion if introduced too quickly",
        ],
        'strengths': [
            "78% moisture — best kidney and urinary protection",
            "Low phosphorus (0.2%) — ideal for kidney health monitoring",
            "High palatability — most cats prefer wet over dry",
            "Low sodium — heart-friendly",
            "Taurine added — essential for heart and eye health",
        ]
    }
}

# What cats need daily
CAT_DAILY_NEEDS = {
    'Protein': {
        'amount': '5-7g per kg body weight',
        'why': 'Cats are obligate carnivores — protein is their primary energy source AND essential for organ function, immune system, muscle maintenance, and enzyme production. Unlike dogs, cats cannot reduce protein use when intake drops.',
        'deficiency': 'Muscle wasting, poor immune function, liver disease',
        'sources': 'Chicken, turkey, fish, beef — any quality meat',
        'found_in': 'Pro Plan Adult: 42% (excellent)'
    },
    'Taurine': {
        'amount': '200-500mg per day',
        'why': 'Cats cannot synthesize taurine themselves — it must come from diet. Critical for heart muscle function (deficiency causes dilated cardiomyopathy), vision (retinal degeneration without it), reproduction, and immune system.',
        'deficiency': 'Heart disease (DCM), blindness, reproductive failure',
        'sources': 'Heart muscle, dark meat, shellfish — only in animal tissue',
        'found_in': 'Pro Plan: Yes — supplemented to safe levels ✅'
    },
    'Arachidonic Acid': {
        'amount': '~200mg per day',
        'why': 'Another nutrient cats cannot make themselves. Essential for skin integrity, blood clotting, and reproduction.',
        'deficiency': 'Poor coat, skin issues, reproductive problems',
        'sources': 'Animal fat — only found in animal tissue, not plants',
        'found_in': 'Pro Plan: Present in animal fat ✅'
    },
    'Vitamin A': {
        'amount': '3,300-10,000 IU per day',
        'why': 'Cats cannot convert beta-carotene (from plants) to Vitamin A like humans can. Must consume preformed Vitamin A from animal sources. Critical for vision, immune system, skin health.',
        'deficiency': 'Night blindness, skin problems, poor immunity',
        'sources': 'Liver, fish oil, fortified foods',
        'found_in': 'Pro Plan: Added ✅'
    },
    'Vitamin D3': {
        'amount': '280-750 IU per day',
        'why': 'Unlike humans, cats cannot synthesize Vitamin D from sunlight. Must come entirely from diet. Controls calcium absorption and bone density.',
        'deficiency': 'Bone disease, poor calcium absorption',
        'sources': 'Fatty fish, liver, fortified foods',
        'found_in': 'Pro Plan: Added ✅'
    },
    'Omega-3 (EPA/DHA)': {
        'amount': '~50-100mg EPA+DHA per day',
        'why': 'Anti-inflammatory — reduces joint inflammation, supports skin, coat quality, brain function, and cardiovascular health. Especially important for cats with heart conditions (like Kuro\'s monitoring) and those on kidney watch.',
        'deficiency': 'Dull coat, dry skin, increased inflammation',
        'sources': 'Fatty fish (salmon, sardines), fish oil supplements',
        'found_in': 'Pro Plan: Moderate — fish oil added ✅'
    },
    'Phosphorus': {
        'amount': '125-750mg per day (AAFCO minimum)',
        'why': 'Essential for bone health and energy metabolism. However, excess phosphorus is one of the main drivers of kidney disease progression in cats. The kidneys must process excess phosphorus, causing damage over time.',
        'deficiency': 'Bone disease (rare with commercial food)',
        'excess_warning': '⚠️ HIGH PRIORITY — excess phosphorus accelerates CKD. For kidney-monitored cats: aim for <0.8% in dry food',
        'sources': 'All meat and fish — naturally present',
        'found_in': 'Pro Plan Adult (dry): 1.0% — MONITOR FOR KIDNEY CATS | Pro Plan Wet: 0.2% — ✅ kidney safe'
    },
    'Water': {
        'amount': '50-70ml per kg body weight per day',
        'why': 'For a 4kg cat: ~200-280ml daily. Cats evolved in deserts with low thirst drive — they should get most water from food. Chronic dehydration is the #1 cause of kidney disease and urinary crystals in domestic cats.',
        'deficiency': 'Kidney disease, urinary crystals/blockages, organ failure',
        'sources': 'Wet food (78% moisture), fresh water, water fountains',
        'found_in': 'Dry food only = insufficient. Wet food = critical supplement'
    },
    'Niacin (Vitamin B3)': {
        'amount': '~4mg per day',
        'why': 'Cats cannot synthesize niacin from tryptophan the way other mammals do. Must come from diet. Used in energy metabolism in every cell.',
        'deficiency': 'Weight loss, mouth sores, anorexia',
        'sources': 'Meat, fish, liver',
        'found_in': 'Pro Plan: B complex added ✅'
    },
}

def diet_planning_page():
    st.header("🥗 Diet Planning")
    st.write("Food defaults, full nutritional breakdown, and daily needs guide.")

    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            ds = st.session_state.diet_settings.get(cat, {})

            # ── Settings ──
            with st.expander("⚙️ Diet Settings", expanded=True):
                c1,c2 = st.columns(2)
                with c1:
                    st.text_input("Default Dry Food",  value=ds.get('default_dry_food','Pro Plan Adult'),   key=f"diet_dry_{cat}")
                    st.text_input("Default Wet Food",  value=ds.get('default_wet_food','Pro Plan Adult Wet'),key=f"diet_wet_{cat}")
                    st.number_input("Meals per day",   1, 6, int(ds.get('meals_per_day',3)),                key=f"diet_meals_{cat}")
                with c2:
                    st.number_input("Dry grams/meal",  5, 200, int(ds.get('dry_grams_per_meal',30)),        key=f"diet_dry_g_{cat}")
                    st.number_input("Wet grams/meal",  10, 400, int(ds.get('wet_grams_per_meal',85)),       key=f"diet_wet_g_{cat}")
                    st.text_area("Diet notes",         value=ds.get('notes',''),                            key=f"diet_notes_{cat}", height=60)
                if st.button("💾 Save Diet Settings", key=f"save_diet_{cat}", type="primary"):
                    st.session_state.diet_settings[cat].update({
                        'default_dry_food':   st.session_state[f"diet_dry_{cat}"],
                        'default_wet_food':   st.session_state[f"diet_wet_{cat}"],
                        'meals_per_day':      st.session_state[f"diet_meals_{cat}"],
                        'dry_grams_per_meal': st.session_state[f"diet_dry_g_{cat}"],
                        'wet_grams_per_meal': st.session_state[f"diet_wet_g_{cat}"],
                        'notes':              st.session_state[f"diet_notes_{cat}"]
                    })
                    save_data()
                    st.success("✅ Diet settings saved!")
                    ds = st.session_state.diet_settings[cat]  # refresh

            meals     = int(ds.get('meals_per_day', 3))
            dry_g     = int(ds.get('dry_grams_per_meal', 30))
            wet_g     = int(ds.get('wet_grams_per_meal', 85))
            daily_dry = meals * dry_g
            daily_wet = meals * wet_g
            dry_name  = ds.get('default_dry_food', 'Pro Plan Adult')
            wet_name  = ds.get('default_wet_food', 'Pro Plan Adult Wet')
            weight_str= st.session_state.cat_profiles.get(cat, {}).get('weight', '4')
            try:    weight_kg = float(weight_str) if weight_str else 4.0
            except: weight_kg = 4.0

            # ── Feeding plan science ──
            st.markdown("---")
            st.subheader("🔬 Why This Feeding Plan Works for " + cat)
            st.info(
                f"**Current plan:** {meals} meals/day · "
                f"{dry_g}g {dry_name} per meal ({daily_dry}g/day) · "
                f"{wet_g}g {wet_name} per meal ({daily_wet}g/day) · "
                f"Estimated body weight: {weight_kg}kg")

            if meals == 1:
                st.error("**1 meal/day is not recommended.** See explanation above.")
            elif meals == 2:
                st.warning("**2 meals/day** works but 12-hour gaps can cause morning bile vomiting.")
            elif meals == 3:
                st.success("**3 meals/day is ideal.** Matches natural hunting rhythm, keeps blood sugar stable, reduces stress and vomiting.")
            else:
                st.success(f"**{meals} meals/day** — excellent for sensitive digestion. Small frequent meals are easiest on the gut.")

            # Hydration calc
            water_from_wet  = daily_wet * 0.78
            water_needed    = weight_kg * 60
            hydration_pct   = (water_from_wet / water_needed) * 100
            st.markdown(f"**💧 Hydration from wet food:** {water_from_wet:.0f}ml/day "
                        f"(need ~{water_needed:.0f}ml/day · covered: **{min(hydration_pct,100):.0f}%**)")
            if hydration_pct < 60:
                st.warning("Wet food covers less than 60% of daily water needs — ensure fresh water is always available.")
            elif hydration_pct >= 80:
                st.success("Wet food covers 80%+ of water needs — excellent kidney protection.")

            # ── Food-specific nutritional analysis ──
            st.markdown("---")
            st.subheader("📊 Nutritional Analysis of Your Cat's Food")

            for food_name, food_key in [(dry_name, dry_name), (wet_name, wet_name)]:
                # Match to known foods (partial match)
                info = None
                for k, v in FOOD_NUTRITION.items():
                    if k.lower() in food_name.lower() or food_name.lower() in k.lower():
                        info = v; break

                if info:
                    daily_g = daily_dry if info['type'] == 'Dry' else daily_wet
                    daily_cal = (daily_g / 100) * info['calories_per_100g']

                    with st.expander(f"🥣 {food_name} — Full Breakdown", expanded=True):
                        c1,c2 = st.columns(2)
                        with c1:
                            st.markdown("**📋 Guaranteed Analysis (per 100g as-fed):**")
                            metrics_data = [
                                ("Protein",     f"{info['protein_pct']}%",     "✅ Excellent" if info['protein_pct'] >= 35 else "⚠️ Low"),
                                ("Fat",         f"{info['fat_pct']}%",         "✅ Good" if 10 <= info['fat_pct'] <= 20 else "⚠️ Check"),
                                ("Fibre",       f"{info['fiber_pct']}%",       "✅ Normal"),
                                ("Moisture",    f"{info['moisture_pct']}%",    "✅ Ideal" if info['moisture_pct'] >= 70 else "⚠️ Low — add wet food"),
                                ("Ash (minerals)",f"{info['ash_pct']}%",       "✅ Normal" if info['ash_pct'] <= 8 else "⚠️ High"),
                                ("Phosphorus",  f"{info['phosphorus_pct']}%",  "⚠️ Monitor for kidney cats" if info['phosphorus_pct'] >= 0.8 else "✅ Kidney safe"),
                                ("Sodium",      f"{info['sodium_pct']}%",      "⚠️ Monitor for heart" if info['sodium_pct'] >= 0.4 else "✅ Low"),
                                ("Calories",    f"{daily_cal:.0f} kcal/day",   f"from {daily_g}g daily"),
                            ]
                            for label, value, status in metrics_data:
                                st.write(f"- **{label}:** {value} — {status}")

                        with c2:
                            st.markdown("**🧬 Essential Nutrients:**")
                            st.write(f"- Taurine: {info['taurine']}")
                            st.write(f"- Omega-3: {info['omega3']}")
                            st.write(f"- Omega-6: {info['omega6']}")
                            st.write(f"- Vitamins: {info['vitamins']}")
                            st.write(f"- Probiotics: {info['probiotics']}")

                        st.markdown("**✅ Strengths:**")
                        for s in info['strengths']: st.write(f"- {s}")

                        st.markdown("**⚠️ Watch out for:**")
                        for w in info['watch_out']: st.warning(f"- {w}")

                        st.info(f"📝 **Overall assessment:** {info['notes']}")
                else:
                    st.info(f"No detailed nutritional data found for '{food_name}'. "
                            "Update the food name to match 'Pro Plan Adult' or 'Pro Plan Adult Wet' "
                            "for full breakdown, or add your food's nutritional details manually.")

            # ── What cats need daily ──
            st.markdown("---")
            st.subheader("🐾 What Cats Must Get Every Day — And Why")
            st.write(
                "Cats are **obligate carnivores** — unlike dogs or humans, they have no biological ability "
                "to substitute plant-based nutrients for animal-based ones. Several nutrients are "
                "**absolutely critical** and cannot be synthesized by their bodies at all.")

            for nutrient, info in CAT_DAILY_NEEDS.items():
                with st.expander(f"🔬 {nutrient}", expanded=False):
                    c1,c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Daily amount needed:** {info['amount']}")
                        st.markdown(f"**Why it's essential:** {info['why']}")
                        st.markdown(f"**Best sources:** {info['sources']}")
                    with c2:
                        st.markdown(f"**In your cat's food:** {info['found_in']}")
                        if 'deficiency' in info:
                            st.error(f"**If deficient:** {info['deficiency']}")
                        if 'excess_warning' in info:
                            st.warning(f"**Excess risk:** {info['excess_warning']}")

            # ── Recent food log ──
            st.markdown("---")
            st.subheader("📋 Recent Food Log (past 7 days)")
            today = date.today()
            d7    = get_daily_aggregated(cat, today-timedelta(days=7), today)
            if d7:
                rows = []
                for dd in sorted(d7.keys(), reverse=True):
                    d = d7[dd]
                    foods = ', '.join(set(d['food_log'])) if d['food_log'] else '—'
                    rows.append({'Date': str(dd), 'Meals Logged': d['food_eats'],
                                 'Foods': foods, 'Water Drinks': d['water_drinks'],
                                 'Pooped': '✅' if d['pooped'] else '—'})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No food entries logged yet this week.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CAT HEALTH GUIDE (expanded)
# ══════════════════════════════════════════════════════════════════════════════
def cat_health_guide_page():
    st.header("🏥 Cat Health Guide")
    st.write("Conditions to watch for, visual guides for pee/poop/vomit, and symptom checker.")

    diseases = [
        {
            "name": "Feline Herpesvirus (FHV-1) — Haku",
            "icon": "🦠",
            "who":  "Haku has this. FHV-1 is lifelong — the virus stays dormant and reactivates with stress",
            "signs": [
                "Sneezing — can be mild or severe during flare-ups",
                "Eye discharge — watery or thick, one or both eyes",
                "Conjunctivitis — red, swollen, goopy eyes",
                "Nasal discharge — clear to coloured",
                "Loss of appetite (can't smell food during flare)",
                "Corneal ulcers in severe cases — squinting or pawing at eye",
                "Flare-ups triggered by: stress, illness, vet visits, changes in routine"
            ],
            "prevention": [
                "Minimize stress — routine consistency is the #1 management tool",
                "L-Lysine supplement — ask vet about dosage (reduces virus replication)",
                "Keep eye area clean — gently wipe discharge with warm damp cloth",
                "FVRCP vaccine — doesn't eliminate virus but reduces flare severity",
                "Air purifier helps — clean air reduces secondary respiratory irritation (you already have this)",
                "Monitor for stress triggers and pre-empt if possible"
            ],
            "urgency": "🟠 Chronic lifelong condition — flare-ups need monitoring. Corneal ulcers = urgent vet"
        },
        {
            "name": "Urinary Tract Infection (UTI) / FLUTD",
            "icon": "🚽",
            "who":  "Any cat — especially stress-prone cats and males (blockage risk)",
            "signs": [
                "Straining in litter box with little or no urine",
                "Crying while trying to urinate",
                "Blood in urine (pink, red, orange tint)",
                "Urinating outside litter box",
                "Licking genitals excessively",
                "Many litter box trips with no result"
            ],
            "prevention": [
                "Fresh water always available — fountain preferred",
                "Wet food as main diet component",
                "Clean litter box daily — dirty box = stress = FLUTD",
                "Reduce environmental stress",
                "Urinary formula food if recurrent"
            ],
            "urgency": "🔴 Emergency if no urine produced — fatal within 24-48 hours without treatment"
        },
        {
            "name": "Kidney Disease (CKD — Chronic Kidney Disease)",
            "icon": "🫘",
            "who":  "All cats are on kidney watch — becomes more common over age 5-7. A key monitoring priority",
            "signs": [
                "Increased thirst — drinking noticeably more",
                "Increased urination — large clumps in litter box",
                "Decreased urination in late stages",
                "Weight loss despite eating",
                "Bad breath — ammonia or metallic smell",
                "Vomiting especially on empty stomach (morning)",
                "Lethargy, weakness, hiding more",
                "Rough, dull, unkempt coat",
                "Muscle wasting — loss of muscle over the spine",
                "Mouth ulcers in advanced stages"
            ],
            "prevention": [
                "High-quality wet food as primary diet — hydration is the #1 kidney protector",
                "Fresh water always available — fountains encourage drinking",
                "Annual blood and urine tests — creatinine, BUN, SDMA (catches CKD before symptoms)",
                "Low phosphorus diet if early CKD detected — Pro Plan Wet is much safer than dry",
                "Avoid NSAIDs, human medications, toxic plants",
                "Maintain healthy weight",
                "Log daily water intake and litter box frequency — changes are early indicators"
            ],
            "urgency": "🟠 Silent early on — your annual bloodwork is the best early detection tool. Log water and litter carefully"
        },
        {
            "name": "Mold / Environmental Toxin Exposure",
            "icon": "🍄",
            "who":  "Indoor cats — any home with poor ventilation, dampness, or old buildings",
            "signs": [
                "Sneezing or coughing that doesn't resolve — especially if it started after moving furniture or cleaning",
                "Eye and nose irritation — discharge, rubbing face",
                "Skin irritation, excessive scratching with no fleas/mites found",
                "Lethargy and reduced appetite without obvious illness",
                "Breathing changes — wheezing, laboured breathing",
                "Vomiting or diarrhoea linked to environment rather than food change",
                "Multiple cats showing similar symptoms at the same time"
            ],
            "prevention": [
                "Air purifier — you already have this, it's excellent for removing airborne mold spores",
                "Check for visible mold in damp areas — under sinks, bathroom corners, behind furniture",
                "Good ventilation — open windows regularly when possible",
                "Replace HVAC filters regularly — mold grows on old filters",
                "Clean cat bedding and trees monthly — dust and mold can accumulate",
                "If sneezing/coughing starts without obvious cause, check the environment first",
                "Avoid aerosol cleaners, air fresheners, scented candles near cats — these are also respiratory irritants"
            ],
            "urgency": "🟡 Chronic low-level exposure causes respiratory and immune issues over time — environment check is important"
        },
        {
            "name": "Heart Disease (HCM — Hypertrophic Cardiomyopathy)",
            "icon": "❤️",
            "who":  "Any cat — all three on routine 4-monthly vet visits which will include cardiac monitoring",
            "signs": [
                "Rapid or laboured breathing at rest",
                "Breathing faster than 30 breaths per minute while sleeping",
                "Sudden hind leg paralysis (aortic thromboembolism — extreme emergency)",
                "Collapse or extreme weakness",
                "Fluid in the chest causing breathing difficulty",
                "Often NO early symptoms — detected only by vet with stethoscope or echocardiogram"
            ],
            "prevention": [
                "Routine vet visits every 4 months — includes heart auscultation",
                "Echocardiogram if a murmur is detected",
                "Taurine-adequate diet — Pro Plan supplemented ✅",
                "Maintain healthy weight — obesity worsens cardiac strain",
                "Know their resting breathing rate at home — count breaths per minute while sleeping (normal <30)"
            ],
            "urgency": "🔴 Sudden hind leg paralysis or open-mouth breathing = emergency. Scheduled checkups are critical"
        },
        {
            "name": "Feline Asthma / Chronic Bronchitis",
            "icon": "💨",
            "who":  "Any cat — you already use a nebulizer, so you're managing this",
            "signs": [
                "Hunched posture, neck extended, head down — like trying to bring up a hairball but nothing comes",
                "Wheezing when breathing",
                "Faster breathing than normal",
                "Open-mouth breathing after light activity",
                "Coughing that sounds like retching"
            ],
            "prevention": [
                "No aerosol sprays, scented candles, or heavy perfumes near cats",
                "Unscented litter — dusty or clay litter worsens asthma",
                "Air purifier — already doing this ✅",
                "No cigarette smoke indoors",
                "Nebulizer protocol as directed by vet — consistent treatment prevents flare-ups"
            ],
            "urgency": "🟠 Acute attacks are emergencies — open-mouth breathing or blue gums = immediate vet"
        },
        {
            "name": "Breathing Difficulty / Dyspnea",
            "icon": "🫁",
            "who":  "Any cat — causes include heart disease, asthma, fluid, pleural effusion, infection",
            "signs": [
                "Open-mouth breathing — cats almost never do this normally",
                "Belly heaving with each breath (abdominal breathing)",
                ">30 breaths per minute at rest",
                "Crouching with elbows out, head forward and low",
                "Blue, grey, or white gums (oxygen deprivation — critical emergency)",
                "Refusing to lie down — staying sitting upright to breathe",
                "Any combination of lethargy + breathing change"
            ],
            "prevention": [
                "Know each cat's normal resting breathing rate (count at home — normal is 15-30/min while sleeping)",
                "Annual chest X-ray as part of checkup — you already have this scheduled ✅",
                "Remove respiratory irritants from environment",
                "Keep air purifier running"
            ],
            "urgency": "🔴 Any breathing difficulty = emergency vet immediately. Do not wait to see if it improves"
        },
        {
            "name": "Red / Inflamed Gums (Stomatitis / Gingivitis)",
            "icon": "🦷",
            "who":  "Any cat — dental disease affects 70% of cats over age 3",
            "signs": [
                "Bright red or purple gum line — especially where teeth meet gums",
                "Extreme reluctance to eat, or dropping food",
                "Drooling, sometimes bloody",
                "Pawing at mouth repeatedly",
                "Strong unpleasant breath",
                "Weight loss from pain when eating"
            ],
            "prevention": [
                "Annual dental check (already in your annual checkup) ✅",
                "Brush teeth 2-3 times per week",
                "Dental treats and enzymatic water additives",
                "Feline stomatitis may require tooth extraction — early treatment prevents this"
            ],
            "urgency": "🟠 If not eating due to mouth pain: vet within 24-48 hours"
        },
        {
            "name": "Stress / Anxiety (FIC — Feline Idiopathic Cystitis)",
            "icon": "😰",
            "who":  "Indoor cats, multi-cat households, routine-sensitive cats (Haku/Kuro/Sonic all qualify)",
            "signs": [
                "Hiding more than usual",
                "Overgrooming — licking until bald patches appear",
                "Inter-cat tension or sudden aggression",
                "Litter box avoidance",
                "Stress-induced UTI symptoms",
                "Loss of appetite during stressful events"
            ],
            "prevention": [
                "Consistent routine for feeding, play, and your schedule",
                "Vertical space and hiding spots",
                "One litter box per cat plus one extra",
                "Daily play sessions — minimum 15 mins per cat",
                "Feliway diffuser if inter-cat tension increases"
            ],
            "urgency": "🟡 Chronic stress causes real physical disease — it's not just behavioural"
        },
        {
            "name": "Intestinal Parasites (Worms)",
            "icon": "🐛",
            "who":  "All cats — on a deworming schedule already",
            "signs": [
                "Visible worm segments in stool or around tail",
                "Bloated belly",
                "Weight loss despite eating",
                "Scooting on floor",
                "Vomiting or diarrhoea"
            ],
            "prevention": [
                "Haku/Sonic: deworming every 3 months (next: 26-Jul-2026)",
                "Kuro: deworming every 4 months (next: 26-Aug-2026)",
                "Monthly flea prevention — fleas carry tapeworms"
            ],
            "urgency": "🟡 Follow schedule — worms worsen without treatment"
        },
        {
            "name": "Upper Respiratory Infection",
            "icon": "🤧",
            "who":  "Any cat — Haku is especially susceptible due to FHV-1",
            "signs": [
                "Sneezing, runny nose",
                "Eye discharge",
                "Loss of appetite (can't smell food)",
                "Lethargy and fever",
                "Mouth ulcers (calicivirus)"
            ],
            "prevention": [
                "FVRCP vaccine annually — already scheduled ✅",
                "Reduce stress for Haku — stress triggers herpes flares",
                "Isolate sick cats",
                "Good air quality — purifier helps ✅"
            ],
            "urgency": "🟠 See vet if not eating 24+ hrs or discharge turns yellow/green"
        },
        {
            "name": "Fleas",
            "icon": "🦟",
            "who":  "Any cat — even indoor-only",
            "signs": [
                "Scratching especially neck and tail base",
                "Black specks in fur (flea dirt)",
                "Red bumps or irritated skin",
                "Hair loss from over-scratching"
            ],
            "prevention": [
                "Monthly vet-approved flea prevention for all cats",
                "Vacuum and wash bedding monthly (already in your task list) ✅",
                "Treat all cats simultaneously if one has fleas"
            ],
            "urgency": "🟡 Not dangerous for adults but carries tapeworms — treat promptly"
        },
        {
            "name": "Ear Mites",
            "icon": "👂",
            "who":  "Any cat",
            "signs": [
                "Head shaking and ear scratching",
                "Dark coffee-ground discharge in ears",
                "Smell from ears",
                "Redness inside ear flap"
            ],
            "prevention": [
                "Monthly ear checks during grooming (Thursday grooming sessions) ✅",
                "Treat all cats together if one has mites"
            ],
            "urgency": "🟠 Very uncomfortable — treat promptly to prevent secondary infection"
        },
        {
            "name": "Obesity",
            "icon": "⚖️",
            "who":  "Indoor/neutered cats",
            "signs": [
                "Cannot feel ribs without pressing hard",
                "Belly hangs and swings when walking",
                "Reluctant to play or groom lower back"
            ],
            "prevention": [
                "Measure portions — 3 meals/day with weighed portions",
                "Wet food: fewer calories per gram than dry",
                "Daily play sessions ✅",
                "Puzzle feeders slow eating"
            ],
            "urgency": "🟡 Slow damage — leads to diabetes, joint disease, heart disease, shorter lifespan"
        },
    ]

    # ── Visual guides ──
    with st.expander("💩 Poop Visual Guide — Normal vs Abnormal", expanded=False):
        st.success(
            "**✅ Normal poop:**  \n"
            "**Shape:** Log-shaped, holds together  \n"
            "**Colour:** Medium to dark brown  \n"
            "**Consistency:** Firm but not rock hard, doesn't crumble or smear  \n"
            "**Frequency:** Once daily or once every 36 hours  \n"
            "**Smell:** Unpleasant but not overwhelming")

        st.markdown("#### Abnormal — What it means:")
        c1,c2 = st.columns(2)
        with c1:
            st.error("**Liquid / watery (diarrhoea):** Infection, parasites, food intolerance, stress, IBD. Over 24 hrs or with blood = vet.")
            st.error("**Bright red blood:** Fresh — lower GI bleed. Colitis, polyps, parasites. Recurring = vet.")
            st.error("**Black tarry stool:** Digested blood — upper GI bleed (stomach/small intestine). Same-day vet visit.")
        with c2:
            st.warning("**Mucus coating:** Small amounts normal. Large amounts = colitis or IBD.")
            st.warning("**Hard dry pellets:** Constipation — increase wet food and water. Watch for straining.")
            st.warning("**Yellow or pale:** Food moving too fast, or liver/pancreas issue. Monitor closely.")

    with st.expander("🚽 Urine Visual Guide — Normal vs Abnormal", expanded=False):
        st.success(
            "**✅ Normal urine:**  \n"
            "**Colour:** Pale to medium yellow  \n"
            "**Smell:** Mild ammonia  \n"
            "**Consistency:** Clear, no cloudiness  \n"
            "**Frequency:** 2-4 times daily  \n"
            "**Amount:** Decent puddle each time")

        c1,c2 = st.columns(2)
        with c1:
            st.error("**Pink/red/orange:** Blood — UTI, crystals, stones. If straining: EMERGENCY.")
            st.error("**No urine at all:** Blockage — life-threatening. Emergency vet NOW.")
            st.warning("**Cloudy or milky:** Infection, crystals, or protein. Vet check needed.")
        with c2:
            st.warning("**Very dark yellow / strong smell:** Dehydration — increase water and wet food urgently.")
            st.warning("**Very pale + frequent large amounts:** Possible diabetes or kidney disease. Blood test needed.")
            st.warning("**Tiny amounts, many trips:** Partial blockage or UTI — vet same day.")

    with st.expander("🤮 Vomit Colour Guide — What Each Colour Means", expanded=False):
        c1,c2 = st.columns(2)
        with c1:
            st.info("**Clear/foamy white:** Empty stomach. Common if fasting 12+ hours. Add a small meal before bed.")
            st.info("**Yellow/yellow-green:** Bile — empty stomach or bile reflux. Increase meal frequency.")
            st.success("**Brown with food chunks:** Ate too fast. Try puzzle feeder or smaller portions.")
            st.warning("**Brown liquid (no food):** Old blood or digested matter — coffee-ground appearance = upper GI bleed. Vet today.")
        with c2:
            st.error("**Bright red:** Fresh blood. More than a tiny streak = vet immediately.")
            st.error("**Dark red/black:** Digested blood. Upper GI bleed — urgent.")
            st.warning("**Green:** Ate grass, OR bile with digested material. Single episode usually fine.")
            st.warning("**White foamy + recurring:** GI issue if no hairball produced. Monitor and vet if ongoing.")

        st.markdown("**When to vet for vomiting:**")
        st.error("- Any blood · More than 2-3 times/day · Combined with lethargy or not eating "
                 "· Combined with diarrhoea · Suspected foreign object (string, toy parts)")

    # ── Filter & search ──
    st.markdown("---")
    ucol, scol = st.columns(2)
    with ucol:
        uf = st.selectbox("Filter by urgency", ["All","🔴 Emergency","🟠 See vet soon","🟡 Monitor / Treat"])
    with scol:
        search = st.text_input("🔍 Search", placeholder="e.g., sneezing, kidney, breathing")

    def ulvl(u):
        if "🔴" in u: return "🔴 Emergency"
        if "🟠" in u: return "🟠 See vet soon"
        return "🟡 Monitor / Treat"

    filtered = diseases
    if uf != "All":
        filtered = [d for d in filtered if ulvl(d["urgency"]) == uf]
    if search:
        sl = search.lower()
        filtered = [d for d in filtered
                    if sl in d["name"].lower()
                    or any(sl in s.lower() for s in d["signs"])
                    or any(sl in p.lower() for p in d["prevention"])]
    if not filtered:
        st.info("No conditions match."); return

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
    st.subheader("🔍 Quick Symptom Checker")
    symptom_map = {
        "Not eating / loss of appetite":       ["Upper Respiratory Infection","Red / Inflamed Gums","Heart Disease","Kidney Disease","Urinary Tract Infection"],
        "Vomiting":                            ["Intestinal Parasites","Kidney Disease","Feline Asthma","Stress / Anxiety"],
        "Diarrhoea":                           ["Intestinal Parasites","Stress / Anxiety"],
        "Straining to urinate / no urine":     ["Urinary Tract Infection"],
        "Blood in urine":                      ["Urinary Tract Infection","Kidney Disease"],
        "Increased thirst":                    ["Kidney Disease"],
        "Open-mouth breathing":                ["Breathing Difficulty","Heart Disease","Feline Asthma"],
        "Fast breathing at rest":              ["Breathing Difficulty","Heart Disease","Feline Asthma"],
        "Wheezing or coughing":                ["Feline Asthma","Breathing Difficulty"],
        "Hind leg weakness/paralysis":         ["Heart Disease"],
        "Sneezing / eye discharge":            ["Feline Herpesvirus","Upper Respiratory Infection"],
        "Red or inflamed gums":                ["Red / Inflamed Gums"],
        "Hiding / lethargy":                   ["Stress / Anxiety","Upper Respiratory Infection","Kidney Disease","Heart Disease"],
        "Hair loss / bald patches":            ["Stress / Anxiety","Fleas"],
        "Scratching ears":                     ["Ear Mites"],
        "Weight loss despite eating":          ["Intestinal Parasites","Kidney Disease"],
        "Weight gain / pot belly":             ["Obesity","Intestinal Parasites"],
        "Scratching body / restless":          ["Fleas","Stress / Anxiety"],
        "Sneezing after room changes":         ["Mold / Environmental Toxins"],
        "Multiple cats sneezing simultaneously":["Mold / Environmental Toxins"],
        "Scooting on floor":                   ["Intestinal Parasites"],
        "Overgrooming":                        ["Stress / Anxiety","Fleas"],
        "Litter box avoidance":                ["Urinary Tract Infection","Stress / Anxiety"],
        "Excessive eye discharge":             ["Feline Herpesvirus","Upper Respiratory Infection"],
        "Weight loss + increased thirst":      ["Kidney Disease"],
    }

    selected = []
    cols = st.columns(2)
    for i, sym in enumerate(symptom_map):
        with cols[i % 2]:
            if st.checkbox(sym, key=f"sym_{i}"): selected.append(sym)

    if selected:
        st.markdown("---")
        st.markdown("**Possible conditions based on symptoms:**")
        scores = {}
        for sym in selected:
            for dn in symptom_map.get(sym, []):
                scores[dn] = scores.get(dn, 0) + 1
        for dn, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            md = next((d for d in diseases
                       if any(part.strip().lower() in d["name"].lower()
                              for part in dn.split("/"))), None)
            if md:
                u = md["urgency"]
                msg = f"**{md['icon']} {md['name']}** — {sc} symptom(s) match · {u}"
                if "🔴" in u:   st.error(msg)
                elif "🟠" in u: st.warning(msg)
                else:            st.info(msg)
        st.caption("Reference only — always consult your vet for a proper diagnosis.")


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

    # ── Vet appointment reminders ──
    reminders = get_vet_reminders()
    urgent    = [r for r in reminders if r['days_away'] is not None and (r['overdue'] or r['days_away'] <= 30)]
    not_set   = [r for r in reminders if r['next_date'] in ('Not set', 'Invalid date')]

    if urgent or not_set:
        st.subheader("📅 Vet Appointment Reminders")
        for r in urgent:
            if r['overdue']:
                st.error(f"🔴 **{r['cat']}** — {r['label']} was due {r['next_date']} "
                         f"({abs(r['days_away'])} days overdue!)")
            elif r['days_away'] <= 7:
                st.error(f"🟠 **{r['cat']}** — {r['label']} in **{r['days_away']} days** ({r['next_date']})")
            elif r['days_away'] <= 14:
                st.warning(f"🟡 **{r['cat']}** — {r['label']} in {r['days_away']} days ({r['next_date']})")
            else:
                st.info(f"🟢 **{r['cat']}** — {r['label']} in {r['days_away']} days ({r['next_date']})")
        for r in not_set:
            st.warning(f"⚠️ **{r['cat']}** — {r['label']} not set. Update in Cat Profiles.")
        st.markdown("---")

    # ── Weekly task reminder (Thu/Fri) ──
    week_start = today - timedelta(days=weekday)
    week_end   = week_start + timedelta(days=6)
    wc         = get_task_completions(week_start, week_end)
    done_week  = set(l['task'] for logs in wc.values() for l in logs
                     if l['task'] in st.session_state.tasks.get('weekly',[]))
    pending_w  = [t for t in st.session_state.tasks.get('weekly',[]) if t not in done_week]

    if (is_thu or is_fri) and pending_w:
        st.warning(f"🗓️ **{'Thursday' if is_thu else 'Friday'} — weekly tasks pending:** {', '.join(pending_w)}  "
                   f"→ Go to Task Management to complete them.")
        st.markdown("---")
    elif (is_thu or is_fri) and not pending_w:
        st.success("✅ All weekly tasks done this week!")
        st.markdown("---")

    # ── Monthly task reminder (1st of month) ──
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

    # ── Active medicines ──
    active_meds = get_active_medications_today()
    if active_meds:
        st.subheader("💊 Active Medicines / Treatments Today")
        for m in active_meds:
            dl = m['days_left']
            if dl == 0:   urg, note = "🔴", "**Last dose today!**"
            elif dl <= 2: urg, note = "🟠", f"**{dl} day(s) left**"
            else:         urg, note = "🟢", f"{dl} days left"
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

    # ── Quick summary for all cats ──
    st.markdown("---")
    st.subheader("📋 This Week at a Glance")
    week_ago = today - timedelta(days=7)
    comp, any_concerns = [], []
    for cat in st.session_state.cats:
        a = analyze_cat_health(cat)
        if a['status'] == 'no_data':
            comp.append({'Cat': cat, 'Status': '⬜ No data', 'Water/Day': '—',
                         'Food/Day': '—', 'Litter/Day': '—', 'Mood': '—', 'Poop Days': '—'})
        else:
            status_icon = '✅ Healthy' if not a['concerns'] else f"⚠️ {len(a['concerns'])} concern(s)"
            comp.append({
                'Cat':        cat,
                'Status':     status_icon,
                'Water/Day':  f"{a['water_avg']:.1f}",
                'Food/Day':   f"{a['food_avg']:.1f}",
                'Litter/Day': f"{a['litter_avg']:.1f}",
                'Mood':       a['mood_trend'].title(),
                'Poop Days':  f"{a.get('poop_days',0)}/{a['total_days']}"
            })
            if a['concerns']:
                any_concerns.append((cat, a['concerns']))

    st.dataframe(pd.DataFrame(comp), use_container_width=True, hide_index=True)

    if any_concerns:
        st.markdown("**⚠️ Summary of current concerns:**")
        for cat, concerns in any_concerns:
            st.warning(f"**{cat}:** " + " · ".join(concerns))
    else:
        st.success("✅ All three cats look good this week based on logged data!")

    # ── Weekly comparison chart ──
    st.markdown("---")
    st.subheader("📊 Weekly Comparison")
    cdata = []
    for cat in st.session_state.cats:
        daily = get_daily_aggregated(cat, week_ago, today)
        if daily:
            cdata.append({
                'Cat':            cat,
                'Avg Water/Day':  round(sum(d['water_drinks']     for d in daily.values())/len(daily),1),
                'Avg Food/Day':   round(sum(d['food_eats']        for d in daily.values())/len(daily),1),
                'Avg Litter/Day': round(sum(d['litter_box_times'] for d in daily.values())/len(daily),1),
                'Poop Days':      sum(1 for d in daily.values() if d.get('pooped')),
                'Days Tracked':   len(daily)
            })
    if cdata:
        cdf = pd.DataFrame(cdata)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Water',  x=cdf['Cat'], y=cdf['Avg Water/Day'],  marker_color='#4fc3f7'))
        fig.add_trace(go.Bar(name='Food',   x=cdf['Cat'], y=cdf['Avg Food/Day'],   marker_color='#81c784'))
        fig.add_trace(go.Bar(name='Litter', x=cdf['Cat'], y=cdf['Avg Litter/Day'], marker_color='#ffb74d'))
        fig.update_layout(barmode='group', height=280, margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)

    # ── PDF export ──
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
                               mime="application/pdf", type="primary",
                               use_container_width=True)
        else:
            st.warning("Install: pip install reportlab")

    # ── In-depth per-cat analysis ──
    st.markdown("---")
    st.subheader("🔬 In-Depth Cat Analysis")
    st.caption("Full analysis with explanations of what each metric means and why it matters.")
    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            st.markdown(generate_cat_summary(cat))


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
            st.download_button("💾 Download",
                data=json.dumps(st.session_state.health_data, indent=2, default=str),
                file_name=f"health_data_{date.today()}.json", mime="application/json")
    with c2:
        if st.button("Export Task Logs", use_container_width=True):
            st.download_button("💾 Download",
                data=json.dumps(st.session_state.task_logs, indent=2, default=str),
                file_name=f"task_logs_{date.today()}.json", mime="application/json")
    with c3:
        if st.button("Export Profiles", use_container_width=True):
            st.download_button("💾 Download",
                data=json.dumps(st.session_state.cat_profiles, indent=2, default=str),
                file_name=f"profiles_{date.today()}.json", mime="application/json")

    st.markdown("---")
    st.subheader("🗑️ Delete Specific Data")
    c1,c2 = st.columns(2)
    with c1:
        ctd = st.selectbox("Cat health data to delete:", [""]+st.session_state.cats, key="del_cat_h")
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
    conf2 = st.checkbox("Reset EVERYTHING including profiles", key="conf_reset")
    if st.button("🔄 RESET EVERYTHING", type="secondary", disabled=not conf2):
        st.session_state.health_data   = {}
        st.session_state.task_logs     = {}
        st.session_state.cat_profiles  = {
            cat: {'age':'','breed':'','weight':'','vet_visits':[],'notes':'',
                  'birthdate':'', **DEFAULT_VET_SCHEDULE[cat]}
            for cat in ['Haku','Kuro','Sonic']
        }
        st.session_state.diet_settings = {
            c: {'default_dry_food':'Pro Plan Adult','default_wet_food':'Pro Plan Adult Wet',
                'meals_per_day':3,'dry_grams_per_meal':30,'wet_grams_per_meal':85,'notes':''}
            for c in st.session_state.cats
        }
        st.session_state.last_entries  = {c: None for c in st.session_state.cats}
        st.session_state.data_loaded   = False
        for f in ['health_data.json','task_logs.json','cat_profiles.json','diet_settings.json']:
            try:
                if os.path.exists(f): os.remove(f)
            except: pass
        st.success("Reset complete!"); time.sleep(1); st.rerun()

    st.markdown("---")
    st.subheader("📊 Stats")
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
        if missing:
            st.warning(f"⚠️ No health entries today for: {', '.join(missing)}")

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

    st.set_page_config(
        page_title="Cat Health Tracker",
        page_icon="🐱",
        layout="wide",
        initial_sidebar_state="expanded"
    )

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
        "(https://thaura.ai/?chatId=eb1bb2bf-acf0-4f6c-99c4-660a0a4fd728)"
    )

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
