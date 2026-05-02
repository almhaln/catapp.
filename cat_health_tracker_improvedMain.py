"""
Cat Health Tracker — Full Featured
Haku · Kuro · Sonic
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

# ── ReportLab ──────────────────────────────────────────────────────────────────
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

# ── Auth ───────────────────────────────────────────────────────────────────────
try:
    from auth_module import (check_authentication, login_page, logout,
                             encrypt_data, decrypt_data)
    AUTH_ENABLED = True
except ImportError:
    AUTH_ENABLED = False


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
            'weekly': [
                'Clean water fountain', 'Clean room', 'Clean air purifier'
            ],
            'monthly': [
                'Deep clean litter box', 'Buy food', 'Buy wet food',
                'Buy litter', 'Buy treats', 'Buy toys',
                'Clean eyes', 'Clean chin', 'Clean cat tree', 'Clean bedding',
                'Clean air purifier filter'
            ],
            'quarterly': [],
            'grooming': [
                'Brush Fur', 'Trim Nails', 'Clean Ears',
                'Clean Eyes', 'Clean Chin', 'Dental Care'
            ]
        }
    else:
        # Patch missing tasks on existing sessions
        daily = st.session_state.tasks.get('daily', [])
        if 'Play with them' not in daily:
            daily.append('Play with them')
            st.session_state.tasks['daily'] = daily
        weekly = st.session_state.tasks.get('weekly', [])
        if 'Clean air purifier' not in weekly:
            weekly.append('Clean air purifier')
            st.session_state.tasks['weekly'] = weekly
        monthly = st.session_state.tasks.get('monthly', [])
        if 'Clean air purifier filter' not in monthly:
            monthly.append('Clean air purifier filter')
            st.session_state.tasks['monthly'] = monthly
        if 'grooming' not in st.session_state.tasks:
            st.session_state.tasks['grooming'] = [
                'Brush Fur', 'Trim Nails', 'Clean Ears',
                'Clean Eyes', 'Clean Chin', 'Dental Care'
            ]

    if 'task_logs' not in st.session_state:
        st.session_state.task_logs = {}

    if 'last_entries' not in st.session_state:
        st.session_state.last_entries = {cat: None for cat in st.session_state.cats}

    if 'last_reminder' not in st.session_state:
        st.session_state.last_reminder = None

    if 'cat_profiles' not in st.session_state:
        st.session_state.cat_profiles = {
            cat: {'age': '', 'breed': '', 'weight': '', 'vet_visits': [], 'notes': '',
                  'birthdate': '', 'next_checkup': '', 'next_vaccines': '',
                  'next_deworming': '', 'next_heart_checkup': ''}
            for cat in st.session_state.cats
        }

    # Diet settings
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
            for cat in st.session_state.cats
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
            'health_data.json':  json.dumps(st.session_state.health_data,    default=str),
            'task_logs.json':    json.dumps(st.session_state.task_logs,      default=str),
            'cat_profiles.json': json.dumps(st.session_state.cat_profiles,   default=str),
            'diet_settings.json':json.dumps(st.session_state.diet_settings,  default=str),
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
        data_str = f.read()
    if AUTH_ENABLED and data_str:
        try: data_str = decrypt_data(data_str)
        except: pass
    return data_str or None


def load_data():
    """Runs only once per browser session."""
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
                # ensure new keys exist
                for key in ['birthdate','next_checkup','next_vaccines',
                             'next_deworming','next_heart_checkup']:
                    profile.setdefault(key, '')
            st.session_state.cat_profiles = loaded

        s = _read_file('diet_settings.json')
        if s:
            loaded_diet = json.loads(s)
            for cat in st.session_state.cats:
                if cat in loaded_diet:
                    st.session_state.diet_settings[cat].update(loaded_diet[cat])

        st.session_state.data_loaded = True
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.session_state.data_loaded = True


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH ENTRIES
# ══════════════════════════════════════════════════════════════════════════════
def add_health_entry(cat_name: str, entry_data: Dict):
    if cat_name not in st.session_state.health_data:
        st.session_state.health_data[cat_name] = {}
    ts = datetime.now().isoformat()
    st.session_state.health_data[cat_name].setdefault(ts, [])
    entry_data['timestamp'] = ts
    st.session_state.health_data[cat_name][ts].append(entry_data)
    st.session_state.last_entries[cat_name] = datetime.now()
    save_data()


def get_health_entries(cat_name: str, start_date: date, end_date: date) -> List[Dict]:
    entries = []
    if cat_name not in st.session_state.health_data:
        return entries
    for ts, ts_entries in st.session_state.health_data[cat_name].items():
        try:
            ed = datetime.fromisoformat(ts).date()
            if start_date <= ed <= end_date:
                for e in ts_entries:
                    ec = dict(e); ec['timestamp'] = ts
                    entries.append(ec)
        except:
            continue
    return entries


def update_health_entry(cat_name, ts, idx, data):
    if cat_name in st.session_state.health_data and ts in st.session_state.health_data[cat_name]:
        if idx < len(st.session_state.health_data[cat_name][ts]):
            st.session_state.health_data[cat_name][ts][idx].update(data)
            save_data()


def delete_health_entry(cat_name, ts, idx):
    if cat_name in st.session_state.health_data and ts in st.session_state.health_data[cat_name]:
        if idx < len(st.session_state.health_data[cat_name][ts]):
            st.session_state.health_data[cat_name][ts].pop(idx)
            if not st.session_state.health_data[cat_name][ts]:
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
    return {
        ds: logs for ds, logs in st.session_state.task_logs.items()
        if (lambda d: start_date <= d <= end_date)(
            date.fromisoformat(ds) if _valid_date(ds) else date.min
        )
    }


def _valid_date(s):
    try: date.fromisoformat(s); return True
    except: return False


# ══════════════════════════════════════════════════════════════════════════════
# DAILY AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════
def get_daily_aggregated(cat_name: str, start_date: date, end_date: date) -> Dict:
    daily = {}
    for entry in get_health_entries(cat_name, start_date, end_date):
        try:
            ed = datetime.fromisoformat(entry['timestamp']).date()
        except:
            continue
        if ed not in daily:
            daily[ed] = {
                'water_drinks': 0, 'food_eats': 0, 'litter_box_times': 0,
                'moods': [], 'medications': [], 'grooming_tasks': set(),
                'litter_quality_issues': [], 'notes': [], 'entry_count': 0,
                'pooped': False, 'food_log': []
            }
        d = daily[ed]
        d['water_drinks']     += entry.get('water_drinks', 0)
        d['food_eats']        += entry.get('food_eats', 0)
        d['litter_box_times'] += entry.get('litter_box_times', 0)
        d['entry_count']      += 1
        if entry.get('pooped'): d['pooped'] = True
        if entry.get('mood'):   d['moods'].append(entry['mood'])
        if entry.get('food_eaten'):
            d['food_log'].append(entry['food_eaten'])
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

    all_moods = [m for d in daily.values() for m in d['moods']]
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
        if any(kw in iss.lower() for kw in ['blood', 'diarrhea', 'abnormal', 'mucus', 'black', 'red'])
    ]

    concerns = []
    recommendations = []
    positives = []

    # Water
    if water_avg >= 3:
        positives.append(f"💧 Great hydration! Averaging {water_avg:.1f} drinks/day. "
                         "Good water intake protects the kidneys and urinary tract and keeps organs functioning well.")
    elif water_avg >= 1:
        concerns.append(f"💧 Moderate water intake (avg {water_avg:.1f}/day).")
        recommendations.append("Try a water fountain — running water encourages cats to drink more. "
                                "Add wet food to boost hydration. Aim for 3+ drinks logged per day.")
    else:
        concerns.append(f"💧 Low water intake (avg {water_avg:.1f}/day) — this is a concern.")
        recommendations.append("Low hydration is a major risk factor for kidney disease and urinary blockages. "
                                "Add a fountain, offer wet food at every meal, and check that all water bowls are clean.")

    # Food
    if food_avg >= 3:
        positives.append(f"🍽️ Eating well — {food_avg:.1f} meals/day on average. "
                         "Regular feeding keeps metabolism stable and prevents hunger-related stress.")
    elif food_avg >= 2:
        positives.append(f"🍽️ Food intake looks normal at {food_avg:.1f} meals/day.")
    elif food_avg >= 1:
        concerns.append(f"🍽️ Lower than expected food intake (avg {food_avg:.1f}/day).")
        recommendations.append("If appetite has dropped, watch for other signs of illness. "
                                "Try warming wet food slightly to make it more appealing. If it persists 48h, see a vet.")
    else:
        concerns.append(f"🍽️ Very low food intake (avg {food_avg:.1f}/day) — needs attention.")
        recommendations.append("Not eating is a serious warning sign in cats. It can quickly lead to hepatic lipidosis "
                                "(fatty liver disease). Consult a vet if not eating for more than 24-48 hours.")

    # Litter
    if 2 <= litter_avg <= 5:
        positives.append(f"🚽 Litter box usage is normal ({litter_avg:.1f}x/day). "
                         "Healthy cats typically use the litter box 2-5 times per day.")
    elif litter_avg > 5:
        concerns.append(f"🚽 High litter box usage ({litter_avg:.1f}x/day).")
        recommendations.append("Frequent litter box trips can signal a urinary tract infection, stress, or early kidney issues. "
                                "Watch for straining, blood, or crying — those are emergency signs. Book a vet check.")
    elif litter_avg < 1 and total_days >= 3:
        concerns.append(f"🚽 Very low litter box usage ({litter_avg:.1f}x/day).")
        recommendations.append("Infrequent litter use could mean constipation or that the cat is avoiding the box. "
                                "Check litter cleanliness and watch for signs of discomfort.")

    # Mood
    if mood_trend == 'good':
        positives.append("😊 Mood has been consistently good this week. Happy cats have lower stress hormones, "
                          "stronger immune systems, and are less prone to FLUTD.")
    elif mood_trend == 'declining':
        concerns.append("😟 Mood has been declining this week.")
        recommendations.append("A consistently poor mood can indicate pain, illness, or environmental stress. "
                                "Check for changes in the home, new animals, or physical symptoms. Consider a vet visit.")

    # Litter quality
    if all_litter_issues:
        concerns.append(f"⚠️ Litter quality issues detected ({len(all_litter_issues)} time(s)).")
        recommendations.append("Abnormal stool or urine (blood, unusual color, diarrhea) always warrants a vet visit. "
                                "Don't wait — these can escalate quickly in cats.")

    # Pooping
    poop_days = sum(1 for d in daily.values() if d.get('pooped'))
    if poop_days >= total_days * 0.7:
        positives.append(f"✅ Regular bowel movements logged ({poop_days}/{total_days} days). "
                         "Daily pooping is a good sign of a healthy digestive system.")
    elif total_days >= 3 and poop_days == 0:
        concerns.append("🚽 No bowel movements logged in the past week.")
        recommendations.append("Cats should poop at least once every 24-48 hours. If there's genuinely no stool, "
                                "this could be constipation — see your vet.")

    if not concerns:
        recommendations.append("Everything looks great! Keep up the consistent monitoring. "
                                "Early detection of any change is the best health tool you have.")

    return {
        **base,
        'status':          'healthy' if not concerns else 'warning',
        'total_entries':   total_entries,
        'total_days':      total_days,
        'water_avg':       water_avg,
        'food_avg':        food_avg,
        'litter_avg':      litter_avg,
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
            med_name  = entry.get('medication_name', '').strip()
            start_str = entry.get('medication_start_date', '')
            end_str   = entry.get('medication_end_date', '')
            if not all([med_name, start_str, end_str]): continue
            try:
                ms, me = date.fromisoformat(start_str), date.fromisoformat(end_str)
            except: continue
            key = f"{cat}_{med_name}_{end_str}"
            if key in seen: continue
            seen.add(key)
            if ms <= today <= me:
                active.append({
                    'cat':       cat,
                    'name':      med_name,
                    'type':      entry.get('medication_type', 'Oral'),
                    'dosage':    entry.get('medication_dosage', ''),
                    'frequency': entry.get('medication_frequency', ''),
                    'end_date':  end_str,
                    'days_left': (me - today).days
                })
    return active


# ══════════════════════════════════════════════════════════════════════════════
# VET REMINDERS
# ══════════════════════════════════════════════════════════════════════════════
def get_vet_reminders() -> List[Dict]:
    today = date.today()
    reminders = []

    schedules = {
        'Haku':  [('Annual Checkup', 'next_checkup', 365),
                  ('Vaccines',       'next_vaccines', 365),
                  ('Deworming',      'next_deworming', 90)],
        'Kuro':  [('Annual Checkup', 'next_checkup', 365),
                  ('Vaccines',       'next_vaccines', 365),
                  ('Deworming',      'next_deworming', 120),
                  ('Heart Checkup',  'next_heart_checkup', 120)],
        'Sonic': [('Annual Checkup', 'next_checkup', 365),
                  ('Vaccines',       'next_vaccines', 365),
                  ('Deworming',      'next_deworming', 90)],
    }

    for cat, items in schedules.items():
        profile = st.session_state.cat_profiles.get(cat, {})
        for label, key, interval_days in items:
            next_date_str = profile.get(key, '')
            if next_date_str:
                try:
                    nd = date.fromisoformat(next_date_str)
                    days_away = (nd - today).days
                    reminders.append({
                        'cat': cat, 'label': label,
                        'next_date': next_date_str,
                        'days_away': days_away,
                        'overdue': days_away < 0
                    })
                except:
                    pass
            else:
                # No date set — remind to set one
                reminders.append({
                    'cat': cat, 'label': label,
                    'next_date': 'Not set',
                    'days_away': None,
                    'overdue': False
                })
    return reminders


# ══════════════════════════════════════════════════════════════════════════════
# CAT SUMMARY TEXT (for dashboard)
# ══════════════════════════════════════════════════════════════════════════════
def generate_cat_summary(cat_name: str) -> str:
    a       = analyze_cat_health(cat_name)
    profile = a.get('profile', {})

    if a['status'] == 'no_data':
        return (f"No health data recorded yet for **{cat_name}**. "
                "Start adding entries to see a detailed analysis here.")

    lines = [f"### 🐱 {cat_name}"]
    info = []
    if profile.get('age'):    info.append(f"Age: {profile['age']}")
    if profile.get('breed'):  info.append(f"Breed: {profile['breed']}")
    if profile.get('weight'): info.append(f"Weight: {profile['weight']} kg")
    if info: lines.append(" · ".join(info))

    lines.append(f"\n**Period:** Past 7 days | **Days tracked:** {a['total_days']} "
                 f"| **Total entries:** {a['total_entries']}")

    lines.append("\n**Daily averages:**")
    lines.append(f"- 💧 Water: **{a['water_avg']:.1f}** times/day")
    lines.append(f"- 🍽️ Food: **{a['food_avg']:.1f}** meals/day")
    lines.append(f"- 🚽 Litter box: **{a['litter_avg']:.1f}** times/day")
    lines.append(f"- 😊 Mood trend: **{a.get('mood_trend','unknown').title()}**")

    # Day breakdown
    if a['daily']:
        lines.append("\n**Day-by-day breakdown:**")
        for dd in sorted(a['daily'].keys(), reverse=True)[:5]:
            d = a['daily'][dd]
            parts = []
            if d['water_drinks']:     parts.append(f"💧 {d['water_drinks']}x water")
            if d['food_eats']:        parts.append(f"🍽️ {d['food_eats']}x food")
            if d['litter_box_times']: parts.append(f"🚽 {d['litter_box_times']}x litter")
            if d['pooped']:           parts.append("✅ pooped")
            if d['grooming_tasks']:   parts.append(f"🪥 {', '.join(d['grooming_tasks'])}")
            if d['food_log']:         parts.append(f"🥣 {', '.join(set(d['food_log']))}")
            lbl = f"({d['entry_count']} {'entry' if d['entry_count']==1 else 'entries'})"
            lines.append(f"- **{dd}** {lbl}: {' · '.join(parts) if parts else 'No activity logged'}")

    # Positives
    if a['positives']:
        lines.append("\n**✅ What's going well:**")
        for p in a['positives']: lines.append(f"- {p}")

    # Concerns + explanations
    if a['concerns']:
        lines.append("\n**⚠️ Concerns:**")
        for c in a['concerns']: lines.append(f"- {c}")
        lines.append("\n**💡 What to do & why:**")
        for r in a['recommendations']: lines.append(f"- {r}")
    else:
        lines.append("\n**✅ No concerns this week. Keep it up!**")

    # Litter alerts
    if a.get('litter_issues'):
        lines.append("\n**🚨 Litter quality alerts:**")
        for dd, iss in a['litter_issues'][:5]: lines.append(f"- {dd}: {iss}")

    # Active meds
    meds = [m for m in get_active_medications_today() if m['cat'] == cat_name]
    if meds:
        lines.append("\n**💊 Active medications/treatments:**")
        for m in meds:
            lines.append(f"- {m['name']} ({m['type']}) — {m.get('dosage','')} "
                         f"· until {m['end_date']} · {m['days_left']} days left")

    # Recent vet
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
    ts = ParagraphStyle('T', parent=styles['Title'],   fontSize=18, spaceAfter=4, textColor=colors.HexColor('#2c3e50'))
    hs = ParagraphStyle('H', parent=styles['Heading2'],fontSize=12, spaceAfter=3, textColor=colors.HexColor('#2980b9'))
    ss = ParagraphStyle('S', parent=styles['Heading3'],fontSize=10, spaceAfter=2, textColor=colors.HexColor('#555'))
    ns = ParagraphStyle('N', parent=styles['Normal'],  fontSize=9,  leading=13)
    cs = ParagraphStyle('C', parent=styles['Normal'],  fontSize=7,  textColor=colors.grey)

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

    story = [Paragraph("Cat Health Report", ts),
             Paragraph(f"Generated: {date.today().strftime('%B %d, %Y')}", cs),
             HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7'), spaceAfter=10)]

    for cat in ([cat_name] if cat_name else st.session_state.cats):
        a = analyze_cat_health(cat)
        profile = a.get('profile', {})
        story.append(Paragraph(f"Cat: {cat}", hs))

        pdata = [["Field","Value"]]
        for lbl, key in [("Age","age"),("Breed","breed"),("Weight","weight"),("Notes","notes")]:
            if profile.get(key):
                pdata.append([lbl, f"{profile[key]} kg" if key=='weight' else profile[key]])
        if len(pdata) > 1:
            story += [tbl(pdata,[5*cm,11*cm],colors.HexColor('#2980b9')), Spacer(1,6)]

        story.append(Paragraph("Weekly Summary", ss))
        if a['status'] == 'no_data':
            story.append(Paragraph("No data recorded.", ns))
        else:
            sdata = [["Metric","Value"],
                     ["Days Tracked", str(a['total_days'])],
                     ["Total Entries", str(a['total_entries'])],
                     ["Avg Water/Day", f"{a['water_avg']:.1f}"],
                     ["Avg Food/Day",  f"{a['food_avg']:.1f}"],
                     ["Avg Litter/Day",f"{a['litter_avg']:.1f}"],
                     ["Mood Trend",    a.get('mood_trend','unknown').title()],
                     ["Status",        a['status'].title()]]
            story += [tbl(sdata,[7*cm,9*cm],colors.HexColor('#27ae60')), Spacer(1,6)]

            if a['concerns']:
                story.append(Paragraph("Concerns & Recommendations", ss))
                for c in a['concerns']:   story.append(Paragraph(f"⚠ {c}", ns))
                for r in a['recommendations']: story.append(Paragraph(f"→ {r}", ns))
                story.append(Spacer(1,4))

            meds = [m for m in get_active_medications_today() if m['cat']==cat]
            if meds:
                story.append(Paragraph("Active Medications/Treatments", ss))
                md = [["Name","Type","Dosage","Frequency","Until"]]
                for m in meds:
                    md.append([m['name'],m.get('type','Oral'),m.get('dosage','-'),
                               m.get('frequency','-'),m['end_date']])
                story += [tbl(md,[3*cm,2*cm,2.5*cm,3*cm,5.5*cm],colors.HexColor('#e74c3c')), Spacer(1,6)]

        vv = profile.get('vet_visits', [])
        if vv:
            story.append(Paragraph("Vet Visit History", ss))
            vd = [["Date","Doctor","Reason","Medication"]]
            for v in sorted(vv, key=lambda x: x.get('date',''), reverse=True):
                vd.append([v.get('date','-'),f"Dr. {v.get('doctor','-')}",
                           v.get('reason','-'),v.get('medication','-')])
            story += [tbl(vd,[3*cm,4*cm,5*cm,4*cm],colors.HexColor('#8e44ad'))]

        story += [Spacer(1,12),
                  HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#bdc3c7'),spaceAfter=10)]

    story.append(Paragraph("Cat Health Tracker — Always consult your vet for medical advice.", cs))
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
    st.markdown(f"**Completed:** {len(done_set)}/{len(monthly_tasks)}")
    if done_set: st.success("Done: " + ", ".join(sorted(done_set)))
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
            ci, cinfo = st.columns([1, 4])
            with ci:
                st.markdown("## 🐱")
                st.markdown(f"**{cat}**")
            with cinfo:
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Age",        profile.get('age')   or "—")
                c2.metric("Breed",      profile.get('breed') or "—")
                c3.metric("Weight",     f"{profile.get('weight') or '—'} kg")
                c4.metric("Vet Visits", len(profile.get('vet_visits', [])))
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

        # ── Edit profile ──
        if st.session_state.get(f'edit_basic_{cat}', False):
            with st.expander(f"✏️ Edit {cat}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Age",         value=profile.get('age',''),   key=f"edit_age_{cat}")
                    st.text_input("Breed",       value=profile.get('breed',''), key=f"edit_breed_{cat}")
                    st.text_input("Weight (kg)", value=profile.get('weight',''),key=f"edit_weight_{cat}")
                with c2:
                    st.text_input("Birthdate (YYYY-MM-DD)", value=profile.get('birthdate',''), key=f"edit_bd_{cat}")
                    st.text_area("Notes",        value=profile.get('notes',''), key=f"edit_notes_{cat}", height=68)

                st.markdown("**📅 Vet Appointment Dates** (set next scheduled date)")
                vc1, vc2 = st.columns(2)
                with vc1:
                    st.text_input("Next Annual Checkup",  value=profile.get('next_checkup',''),       key=f"edit_nc_{cat}",  placeholder="YYYY-MM-DD")
                    st.text_input("Next Vaccines",        value=profile.get('next_vaccines',''),       key=f"edit_nv_{cat}",  placeholder="YYYY-MM-DD")
                with vc2:
                    st.text_input("Next Deworming",       value=profile.get('next_deworming',''),      key=f"edit_nd_{cat}",  placeholder="YYYY-MM-DD")
                    if cat == 'Kuro':
                        st.text_input("Next Heart Checkup", value=profile.get('next_heart_checkup',''), key=f"edit_nhc_{cat}", placeholder="YYYY-MM-DD")

                s1, s2 = st.columns([1,5])
                with s1:
                    if st.button("💾 Save", key=f"save_basic_{cat}", type="primary"):
                        update = {
                            'age':    st.session_state[f"edit_age_{cat}"],
                            'breed':  st.session_state[f"edit_breed_{cat}"],
                            'weight': st.session_state[f"edit_weight_{cat}"],
                            'notes':  st.session_state[f"edit_notes_{cat}"],
                            'birthdate':    st.session_state[f"edit_bd_{cat}"],
                            'next_checkup': st.session_state[f"edit_nc_{cat}"],
                            'next_vaccines':st.session_state[f"edit_nv_{cat}"],
                            'next_deworming':st.session_state[f"edit_nd_{cat}"],
                        }
                        if cat == 'Kuro':
                            update['next_heart_checkup'] = st.session_state.get(f"edit_nhc_{cat}", '')
                        st.session_state.cat_profiles[cat].update(update)
                        save_data()
                        st.success("✅ Profile saved!")
                        st.session_state[f'edit_basic_{cat}'] = False
                        st.rerun()
                with s2:
                    if st.button("❌ Cancel", key=f"cancel_basic_{cat}"):
                        st.session_state[f'edit_basic_{cat}'] = False
                        st.rerun()

        # ── Vet visits ──
        if st.session_state.get(f'edit_{cat}', False):
            with st.expander(f"🏥 Vet Visits — {cat}", expanded=True):
                vv = profile.get('vet_visits', [])
                if vv:
                    vdf = pd.DataFrame(vv)
                    dc  = [c for c in ['date','doctor','reason','medication'] if c in vdf.columns]
                    st.dataframe(vdf[dc], use_container_width=True, hide_index=True)
                    opts = [f"{v['date']} — {v['reason']}" for v in vv]
                    to_del = st.selectbox("Select visit to delete", [""]+opts, key=f"del_vis_{cat}")
                    if to_del and st.button("🗑️ Delete Visit", key=f"del_vis_btn_{cat}", type="secondary"):
                        vv.pop(opts.index(to_del))
                        st.session_state.cat_profiles[cat]['vet_visits'] = vv
                        save_data(); st.success("Deleted!"); st.rerun()

                st.markdown("---")
                st.markdown("#### ➕ Add Visit")
                c1, c2 = st.columns(2)
                with c1:
                    st.date_input("Date",        key=f"v_date_{cat}")
                    st.text_input("Doctor Name", key=f"v_doc_{cat}",    placeholder="Dr. Smith")
                with c2:
                    st.text_input("Reason",      key=f"v_reason_{cat}", placeholder="Annual checkup")
                    st.text_input("Medication",  key=f"v_med_{cat}",    placeholder="None")

                a1, a2 = st.columns([1,5])
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
        ei  = st.session_state.edit_entry_data.get('index', 0)
        oe  = None
        if ec in st.session_state.health_data and ets in st.session_state.health_data[ec]:
            arr = st.session_state.health_data[ec][ets]
            if ei < len(arr): oe = arr[ei]

        if oe:
            with st.form("edit_form"):
                c1, c2 = st.columns(2)
                with c1:
                    wd  = st.number_input("Water Drinks",     0, 20,  oe.get('water_drinks',0))
                    fe  = st.number_input("Food Eats",        0, 10,  oe.get('food_eats',0))
                    lbt = st.number_input("Litter Box Times", 0, 15,  oe.get('litter_box_times',0))
                    poo = st.checkbox("Pooped today?", value=oe.get('pooped', False))
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
                    mty = st.selectbox("Type", ["Oral","Nebulizer","Injection","Topical","Eye drops","Ear drops","Other"],
                                       index=["Oral","Nebulizer","Injection","Topical","Eye drops","Ear drops","Other"].index(oe.get('medication_type','Oral')))
                    md  = st.text_input("Dosage",    value=oe.get('medication_dosage',''))
                    mf  = st.text_input("Frequency", value=oe.get('medication_frequency',''))
                    mr  = st.text_input("Reason",    value=oe.get('medication_reason',''))
                    cs1,ce1 = st.columns(2)
                    with cs1:
                        ms_str = oe.get('medication_start_date','')
                        ms = st.date_input("Start", value=date.fromisoformat(ms_str) if ms_str else date.today(), key="edit_ms")
                    with ce1:
                        me_str = oe.get('medication_end_date','')
                        me = st.date_input("End",   value=date.fromisoformat(me_str) if me_str else date.today(), key="edit_me")

                st.markdown("---")
                notes = st.text_area("Additional Notes", height=80, value=oe.get('notes',''))

                st.markdown("---")
                st.subheader("🪥 Grooming Tasks")
                gt = {t: st.checkbox(t, value=oe.get('grooming_tasks',{}).get(t,False))
                      for t in ["Brush Fur","Trim Nails","Clean Ears","Clean Eyes","Clean Chin","Dental Care"]}

                if st.form_submit_button("💾 Update"):
                    ed = {
                        'water_drinks': wd, 'food_eats': fe,
                        'litter_box_times': lbt, 'mood': mood,
                        'general_appearance': ga, 'pooped': poo,
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

    # Diet default food for quick reference
    ds = st.session_state.diet_settings.get(selected_cat, {})
    default_food = ds.get('default_dry_food', 'Pro Plan Adult')

    entry_mode = st.radio("Entry Mode", ["🚀 Quick Entry", "📋 Detailed Entry"])

    if entry_mode == "🚀 Quick Entry":
        st.markdown("### Quick Actions")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("💧 Water Drank"):
                add_health_entry(selected_cat, {
                    'water_drinks':1,'food_eats':0,'litter_box_times':0,'pooped':False,
                    'mood':'Good','general_appearance':'Good','litter_quality':[],
                    'notes':'Quick: Water drank','grooming_tasks':{},'food_eaten':''})
                st.success("✅ Water logged!"); st.rerun()
        with c2:
            if st.button("🍽️ Food Eaten"):
                add_health_entry(selected_cat, {
                    'water_drinks':0,'food_eats':1,'litter_box_times':0,'pooped':False,
                    'mood':'Good','general_appearance':'Good','litter_quality':[],
                    'notes':f'Quick: Food eaten ({default_food})',
                    'grooming_tasks':{},'food_eaten':default_food})
                st.success("✅ Meal logged!"); st.rerun()
        with c3:
            if st.button("🚽 Litter Used"):
                add_health_entry(selected_cat, {
                    'water_drinks':0,'food_eats':0,'litter_box_times':1,'pooped':False,
                    'mood':'Good','general_appearance':'Good','litter_quality':[],
                    'notes':'Quick: Litter used','grooming_tasks':{},'food_eaten':''})
                st.success("✅ Litter logged!"); st.rerun()
        with c4:
            if st.button("💩 Pooped"):
                add_health_entry(selected_cat, {
                    'water_drinks':0,'food_eats':0,'litter_box_times':1,'pooped':True,
                    'mood':'Good','general_appearance':'Good','litter_quality':[],
                    'notes':'Quick: Pooped','grooming_tasks':{},'food_eaten':''})
                st.success("✅ Poop logged!"); st.rerun()
        st.markdown("---")

    st.markdown("### 📋 Detailed Health Entry")
    with st.form("health_entry_form"):
        c1, c2 = st.columns(2)
        with c1:
            wd  = st.number_input("💧 Water Drinks",     0, 20, 0, key="form_water")
            fe  = st.number_input("🍽️ Food Eats",        0, 10, 0, key="form_food")
            lbt = st.number_input("🚽 Litter Box Times", 0, 15, 0, key="form_litter")
            poo = st.checkbox("💩 Pooped today?",         key="form_poop")
        with c2:
            mood = st.selectbox("😊 Mood", ["Very Poor","Poor","Normal","Good","Excellent"], key="form_mood")
            ga   = st.selectbox("✨ General Appearance",  ["Poor","Fair","Good","Excellent"],  key="form_appearance")
            lq   = st.text_area("🚨 Litter Quality Issues",
                                 placeholder="e.g., Blood, diarrhea, mucus, abnormal color...",
                                 key="form_litter_quality")
            food_eaten = st.text_input("🥣 Food eaten today",
                                        value=default_food,
                                        key="form_food_eaten")

        st.markdown("---")
        st.subheader("💊 Medicine / Treatment (Optional)")
        with st.expander("Add Medicine/Treatment"):
            mn  = st.text_input("Name",      placeholder="e.g., Amoxicillin / Nebulizer session", key="form_med_name")
            mty = st.selectbox("Type", ["Oral","Nebulizer","Injection","Topical","Eye drops","Ear drops","Other"], key="form_med_type")
            md  = st.text_input("Dosage",    placeholder="e.g., 50mg / 10 min session", key="form_med_dosage")
            mf  = st.text_input("Frequency", placeholder="e.g., Twice daily",  key="form_med_freq")
            mr  = st.text_input("Reason",    placeholder="e.g., Respiratory support", key="form_med_reason")
            cs1, ce1 = st.columns(2)
            with cs1: ms = st.date_input("Start Date", value=date.today(),                   key="form_med_start")
            with ce1: me = st.date_input("End Date",   value=date.today()+timedelta(days=7), key="form_med_end")

        st.markdown("---")
        notes = st.text_area("📝 Additional Notes", height=80,
                             placeholder="Any other observations...", key="form_notes")

        st.markdown("---")
        st.subheader("🪥 Grooming Tasks")
        st.caption("Check only if performed today.")
        g1, g2, g3 = st.columns(3)
        with g1:
            gb = st.checkbox("Brush Fur",  key="form_g_brush")
            gn = st.checkbox("Trim Nails", key="form_g_nails")
        with g2:
            ge = st.checkbox("Clean Ears", key="form_g_ears")
            gy = st.checkbox("Clean Eyes", key="form_g_eyes")
        with g3:
            gc = st.checkbox("Clean Chin", key="form_g_chin")
            gd = st.checkbox("Dental Care",key="form_g_dental")
        gt = {"Brush Fur":gb,"Trim Nails":gn,"Clean Ears":ge,
              "Clean Eyes":gy,"Clean Chin":gc,"Dental Care":gd}

        if st.form_submit_button("💾 Save Health Entry", type="primary", use_container_width=True):
            ed = {
                'water_drinks': wd, 'food_eats': fe, 'litter_box_times': lbt,
                'mood': mood, 'general_appearance': ga, 'pooped': poo,
                'food_eaten': food_eaten,
                'litter_quality': lq.split('\n') if lq else [],
                'notes': notes,
                'grooming_tasks': {t: c for t, c in gt.items() if c}
            }
            if mn:
                ed.update({'medication_name': mn, 'medication_type': mty,
                           'medication_dosage': md, 'medication_frequency': mf,
                           'medication_reason': mr,
                           'medication_start_date': str(ms),
                           'medication_end_date':   str(me)})
            add_health_entry(selected_cat, ed)
            st.success(f"✅ Entry saved for {selected_cat}!")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: VIEW HEALTH DATA
# ══════════════════════════════════════════════════════════════════════════════
def view_health_data_page():
    st.header("📊 View Health Data")
    c1, c2 = st.columns(2)
    with c1: sel = st.selectbox("Select Cat", st.session_state.cats)
    with c2:
        dr = st.date_input("Date Range",
                           value=(date.today()-timedelta(days=30), date.today()),
                           max_value=date.today())
    sd, ed = (dr[0], dr[1]) if len(dr)==2 else (date.today(), date.today())

    entries = get_health_entries(sel, sd, ed)
    if not entries:
        st.info(f"No health data found for {sel} in this range."); return

    df = pd.DataFrame(entries)
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df['time'] = pd.to_datetime(df['timestamp']).dt.time
    df = df.sort_values('timestamp', ascending=False)
    daily = get_daily_aggregated(sel, sd, ed)

    st.subheader(f"📈 {sel}'s Combined Daily Totals")
    if daily:
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Avg Water/Day",  f"{sum(d['water_drinks'] for d in daily.values())/len(daily):.1f}")
        c2.metric("Avg Food/Day",   f"{sum(d['food_eats'] for d in daily.values())/len(daily):.1f}")
        c3.metric("Avg Litter/Day", f"{sum(d['litter_box_times'] for d in daily.values())/len(daily):.1f}")
        c4.metric("Days Tracked",   len(daily))
        poop_days = sum(1 for d in daily.values() if d.get('pooped'))
        c5.metric("Poop Days",      f"{poop_days}/{len(daily)}")

    df['date_only'] = df['timestamp'].str.split('T').str[0]
    for ds, grp in df.groupby('date_only'):
        dd = date.fromisoformat(ds)
        dt = daily.get(dd, {})
        parts = []
        if dt.get('water_drinks'):     parts.append(f"💧{dt['water_drinks']}")
        if dt.get('food_eats'):        parts.append(f"🍽️{dt['food_eats']}")
        if dt.get('litter_box_times'): parts.append(f"🚽{dt['litter_box_times']}")
        if dt.get('pooped'):           parts.append("💩✅")
        lbl = f" — {' '.join(parts)}" if parts else ""

        with st.expander(f"📅 {ds} ({len(grp)} entries){lbl}"):
            for idx, row in grp.iterrows():
                st.markdown(f"**⏰ {row['time']}**")
                ca, cb = st.columns([3,1])
                with ca:
                    st.write(f"Water: {row.get('water_drinks','N/A')} · Food: {row.get('food_eats','N/A')} · Litter: {row.get('litter_box_times','N/A')}")
                    if row.get('food_eaten'): st.write(f"🥣 Food: {row['food_eaten']}")
                    pooped_str = "✅ Yes" if row.get('pooped') else "❌ Not logged"
                    st.write(f"💩 Pooped: {pooped_str}")
                    st.write(f"Mood: {row.get('mood','N/A')} · Appearance: {row.get('general_appearance','N/A')}")
                    if row.get('litter_quality'):
                        q = '\n'.join(row['litter_quality'])
                        if q.strip(): st.write(f"⚠️ Litter: {q}")
                    if row.get('notes'): st.write(f"📝 {row['notes']}")
                    if row.get('medication_name'):
                        ms = (f"💊 {row['medication_name']} [{row.get('medication_type','Oral')}] "
                              f"({row.get('medication_dosage','N/A')})")
                        if row.get('medication_start_date') and row.get('medication_end_date'):
                            ms += f" · {row['medication_start_date']} → {row['medication_end_date']}"
                        st.write(ms)
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
        sdates = sorted(daily.keys())
        fig = make_subplots(rows=2, cols=2,
                            subplot_titles=('Water','Food','Litter Box','Entries/Day'))
        fig.add_trace(go.Bar(x=sdates, y=[daily[d]['water_drinks']     for d in sdates], marker_color='#4fc3f7'), row=1,col=1)
        fig.add_trace(go.Bar(x=sdates, y=[daily[d]['food_eats']        for d in sdates], marker_color='#81c784'), row=1,col=2)
        fig.add_trace(go.Bar(x=sdates, y=[daily[d]['litter_box_times'] for d in sdates], marker_color='#ffb74d'), row=2,col=1)
        fig.add_trace(go.Bar(x=sdates, y=[daily[d]['entry_count']      for d in sdates], marker_color='#ce93d8'), row=2,col=2)
        fig.update_layout(height=480, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TASK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def task_management_page():
    st.header("📋 Task Management")
    today      = date.today()
    today_str  = str(today)
    weekday    = today.weekday()   # 0=Mon … 3=Thu … 6=Sun
    is_thursday= weekday == 3
    is_friday  = weekday == 4
    is_first   = today.day == 1
    completed_today = [log['task'] for log in st.session_state.task_logs.get(today_str, [])]

    # ── Daily tasks ──
    st.markdown("### 📅 Daily Tasks")
    if today_str == str(today) and is_thursday:
        st.info("🪥 **Thursday** — Grooming day! Don't forget to groom the cats today.")
    for task in st.session_state.tasks.get('daily', []):
        done = task in completed_today
        checked = st.checkbox(task, value=done, key=f"task_daily_{task}")
        if checked and not done:
            add_task_completion(task); st.rerun()

    # ── Grooming tasks (special Thursday reminder) ──
    st.markdown("---")
    st.markdown("### 🪥 Grooming Tasks")
    if is_thursday:
        st.warning("🔔 **Today is Thursday** — Grooming day for Haku, Kuro & Sonic!")
    else:
        st.caption(f"Grooming tasks are highlighted on Thursdays. Today is {today.strftime('%A')}.")

    grooming_tasks = st.session_state.tasks.get('grooming', [])
    for task in grooming_tasks:
        done = task in completed_today
        checked = st.checkbox(task, value=done, key=f"task_grooming_{task}",
                              disabled=(not is_thursday and not done))
        if checked and not done:
            add_task_completion(task); st.rerun()
    if not is_thursday:
        st.caption("Grooming checkboxes are locked — they unlock every Thursday.")

    # ── Weekly tasks (show reminder Thu/Fri; hide when done until next week) ──
    st.markdown("---")
    st.markdown("### 🗓️ Weekly Tasks")
    if is_thursday or is_friday:
        st.warning(f"🔔 Weekly task reminder — it's {'Thursday' if is_thursday else 'Friday'}!")

    # Find start of current week (Monday)
    week_start = today - timedelta(days=weekday)
    week_end   = week_start + timedelta(days=6)
    week_comps = get_task_completions(week_start, week_end)
    done_this_week = set(
        log['task']
        for logs in week_comps.values()
        for log in logs
        if log['task'] in st.session_state.tasks.get('weekly', [])
    )

    for task in st.session_state.tasks.get('weekly', []):
        if task in done_this_week:
            st.success(f"✅ {task} — done this week!")
        elif is_thursday or is_friday:
            checked = st.checkbox(task, value=False, key=f"task_weekly_{task}")
            if checked:
                add_task_completion(task); st.rerun()
        else:
            st.write(f"⬜ {task} *(available Thu–Fri)*")

    # ── Monthly tasks (show only on 1st; hide when done) ──
    st.markdown("---")
    st.markdown("### 📆 Monthly Tasks")
    month_start = date(today.year, today.month, 1)
    month_end   = date(today.year, today.month,
                       calendar.monthrange(today.year, today.month)[1])
    month_comps = get_task_completions(month_start, month_end)
    done_this_month = set(
        log['task']
        for logs in month_comps.values()
        for log in logs
        if log['task'] in st.session_state.tasks.get('monthly', [])
    )

    if is_first:
        st.warning("🔔 **First of the month** — time for your monthly tasks!")

    for task in st.session_state.tasks.get('monthly', []):
        if task in done_this_month:
            st.success(f"✅ {task} — done this month!")
        elif is_first:
            checked = st.checkbox(task, value=False, key=f"task_monthly_{task}")
            if checked:
                add_task_completion(task); st.rerun()
        else:
            st.write(f"⬜ {task} *(appears on the 1st of each month)*")

    # ── Monthly calendar ──
    st.markdown("---")
    st.subheader("📅 Monthly Task Calendar")
    c1, c2 = st.columns([1,3])
    with c1:
        cm = st.selectbox("Month", range(1,13), index=today.month-1,
                          format_func=lambda m: calendar.month_name[m])
        cy = st.number_input("Year", 2024, 2030, today.year, step=1)
    with c2:
        monthly_task_calendar(int(cy), int(cm))

    # ── History ──
    st.markdown("---")
    st.subheader("📋 Completion History")
    c1, c2 = st.columns(2)
    with c1: hs = st.date_input("Start", today-timedelta(days=7))
    with c2: he = st.date_input("End",   today)
    comps = get_task_completions(hs, he)
    if not comps:
        st.info("No completions found."); return
    rows = [{'date': ds, 'task': l['task'], 'cat': l.get('cat',''),
             'completed_at': l['completed_at']}
            for ds, logs in comps.items() for l in logs]
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    st.dataframe(df.sort_values('date'), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DIET PLANNING
# ══════════════════════════════════════════════════════════════════════════════
def diet_planning_page():
    st.header("🥗 Diet Planning")
    st.write("Manage food defaults, understand feeding science, and track what your cats ate.")

    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            ds = st.session_state.diet_settings.get(cat, {})

            # ── Current settings ──
            with st.expander("⚙️ Diet Settings", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.text_input("Default Dry Food", value=ds.get('default_dry_food','Pro Plan Adult'),
                                  key=f"diet_dry_{cat}")
                    st.text_input("Default Wet Food", value=ds.get('default_wet_food','Pro Plan Adult Wet'),
                                  key=f"diet_wet_{cat}")
                    st.number_input("Meals per day", 1, 6,
                                    value=int(ds.get('meals_per_day', 3)),
                                    key=f"diet_meals_{cat}")
                with c2:
                    st.number_input("Dry grams per meal", 5, 200,
                                    value=int(ds.get('dry_grams_per_meal', 30)),
                                    key=f"diet_dry_g_{cat}")
                    st.number_input("Wet grams per meal", 10, 400,
                                    value=int(ds.get('wet_grams_per_meal', 85)),
                                    key=f"diet_wet_g_{cat}")
                    st.text_area("Diet notes", value=ds.get('notes',''),
                                 key=f"diet_notes_{cat}", height=68)

                if st.button("💾 Save Diet Settings", key=f"save_diet_{cat}", type="primary"):
                    st.session_state.diet_settings[cat].update({
                        'default_dry_food':    st.session_state[f"diet_dry_{cat}"],
                        'default_wet_food':    st.session_state[f"diet_wet_{cat}"],
                        'meals_per_day':       st.session_state[f"diet_meals_{cat}"],
                        'dry_grams_per_meal':  st.session_state[f"diet_dry_g_{cat}"],
                        'wet_grams_per_meal':  st.session_state[f"diet_wet_g_{cat}"],
                        'notes':               st.session_state[f"diet_notes_{cat}"]
                    })
                    save_data()
                    st.success("✅ Diet settings saved!")

            meals     = int(ds.get('meals_per_day', 3))
            dry_g     = int(ds.get('dry_grams_per_meal', 30))
            wet_g     = int(ds.get('wet_grams_per_meal', 85))
            daily_dry = meals * dry_g
            daily_wet = meals * wet_g

            # ── Feeding science ──
            st.markdown("---")
            st.subheader("🔬 Why This Feeding Plan Works")

            st.info(
                f"**{cat}'s current plan:** {meals} meals/day · "
                f"{dry_g}g dry per meal ({daily_dry}g/day) · "
                f"{wet_g}g wet per meal ({daily_wet}g/day)"
            )

            if meals == 1:
                st.warning(
                    "**1 meal/day is not recommended.** Cats have small stomachs and fast metabolisms. "
                    "One large meal can cause hunger stress, begging behaviour, and increases the risk of "
                    "vomiting from eating too fast. It also causes long fasting periods which stress the liver.")
            elif meals == 2:
                st.info(
                    "**2 meals/day is acceptable** and works for many adult cats. It keeps hunger at bay "
                    "and is manageable. The gap between meals (12 hours) is long — watch for vomiting yellow "
                    "bile in the morning, which means the stomach is too empty.")
            elif meals == 3:
                st.success(
                    "**3 meals/day is ideal for adult cats.** It matches their natural hunting rhythm "
                    "(cats naturally eat 10-20 small meals in the wild). It keeps blood sugar stable, "
                    "reduces hunger stress, lowers the risk of vomiting, and helps maintain a healthy weight "
                    "since portions stay small and digestible.")
            elif meals >= 4:
                st.success(
                    f"**{meals} meals/day** is excellent for cats prone to vomiting or with digestive sensitivity. "
                    "Small, frequent meals are gentle on the stomach and keep energy levels steady all day.")

            st.markdown("**Why wet food matters:**")
            st.write(
                "Cats evolved from desert animals and have a naturally low thirst drive — they're designed to "
                "get most of their moisture from prey. Wet food is 70-80% water, which directly supports "
                "kidney health and prevents urinary crystals. Aim for at least 50% of calories from wet food. "
                f"At {wet_g}g per meal × {meals} meals = **{daily_wet}g wet food daily** — "
                + ("✅ great hydration support!" if daily_wet >= 150
                   else "⚠️ consider increasing wet food for better hydration."))

            st.markdown("**Why dry food in moderation:**")
            st.write(
                f"Dry food at {dry_g}g × {meals} meals = **{daily_dry}g/day**. "
                "Dry food is calorie-dense and convenient, but low in moisture. "
                + ("✅ This is a moderate amount — balanced well with wet food."
                   if daily_dry <= 60
                   else "⚠️ This is on the higher side. Make sure wet food and water intake are high to compensate.")
            )

            st.markdown("**Pro Plan Adult — why it's a good choice:**")
            st.write(
                "Pro Plan is a veterinary-recommended brand with high protein content, real meat as the "
                "first ingredient, and scientifically balanced nutrients. It has strong evidence for "
                "supporting urinary health (especially the urinary formula), coat quality, and digestion. "
                "It's one of the most studied cat food brands — a solid default choice.")

            # ── Recent food log ──
            st.markdown("---")
            st.subheader("📋 Recent Food Log (past 7 days)")
            today = date.today()
            daily = get_daily_aggregated(cat, today-timedelta(days=7), today)
            if daily:
                rows = []
                for dd in sorted(daily.keys(), reverse=True):
                    d = daily[dd]
                    foods = list(set(d['food_log'])) if d['food_log'] else ['—']
                    rows.append({
                        'Date':   str(dd),
                        'Meals Logged': d['food_eats'],
                        'Foods': ', '.join(foods),
                        'Water Drinks': d['water_drinks'],
                        'Pooped': '✅' if d['pooped'] else '—'
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No food entries logged yet this week.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CAT HEALTH GUIDE (expanded)
# ══════════════════════════════════════════════════════════════════════════════
def cat_health_guide_page():
    st.header("🏥 Cat Health Guide")
    st.write("Common conditions, warning signs, prevention, pee/poop/vomit visual guides.")

    diseases = [
        {
            "name": "Urinary Tract Infection (UTI)",
            "icon": "🚽",
            "who":  "Any cat, more common in males (risk of blockage)",
            "signs": [
                "Straining in litter box with little or no urine produced",
                "Crying or vocalising while trying to urinate",
                "Blood in urine (pink, red, or orange tint)",
                "Urinating outside the litter box",
                "Licking the genital area excessively",
                "Visiting the litter box many times without result"
            ],
            "prevention": [
                "Fresh water always available — fountains encourage drinking",
                "Wet food as a major part of diet dilutes urine",
                "Clean litter box daily — dirty boxes cause stress and holding urine",
                "Reduce environmental stress (FLUTD is largely stress-triggered)",
                "Consider urinary formula food (e.g. Pro Plan Urinary)"
            ],
            "urgency": "🔴 Emergency if cat cannot urinate — fatal within 24-48 hours without treatment"
        },
        {
            "name": "Urinary / Kidney Issues (CKD, Crystals, Stones)",
            "icon": "🫘",
            "who":  "Adult to senior cats, more common over age 5-7",
            "signs": [
                "Increased thirst and urination (early kidney disease)",
                "Decreased urination or no urination (blockage / late CKD)",
                "Weight loss over time despite eating",
                "Bad breath with ammonia or metallic smell",
                "Vomiting — especially in the morning on an empty stomach",
                "Lethargy, weakness, hiding",
                "Rough, dull coat"
            ],
            "prevention": [
                "High-quality wet food diet — hydration is the #1 kidney protector",
                "Annual blood and urine tests after age 5",
                "Maintain healthy weight — obese cats have higher CKD risk",
                "Avoid NSAIDs and human medications — toxic to cat kidneys",
                "Fresh water in multiple locations around the house"
            ],
            "urgency": "🟠 Chronic — early detection with annual bloodwork is key. Sudden changes = urgent vet visit"
        },
        {
            "name": "Red / Inflamed Gums (Stomatitis / Gingivitis)",
            "icon": "🦷",
            "who":  "Any cat, more severe in some breeds (e.g. Siamese, Persians)",
            "signs": [
                "Bright red or purple gums — especially along the gum line",
                "Extreme reluctance to eat or dropping food from mouth",
                "Drooling, sometimes with blood in saliva",
                "Pawing at the mouth",
                "Strong bad breath (different from normal cat breath)",
                "Weight loss from pain when eating"
            ],
            "prevention": [
                "Regular dental checks — at least once per year",
                "Brush teeth 2-3x per week",
                "Dental treats, enzymatic toothpaste, water additives",
                "Feline stomatitis may require tooth extraction in severe cases — don't delay"
            ],
            "urgency": "🟠 Painful condition that worsens fast — if cat is not eating due to mouth pain, see vet within 24-48 hrs"
        },
        {
            "name": "Stress / Anxiety (FIC — Feline Idiopathic Cystitis)",
            "icon": "😰",
            "who":  "Indoor cats, cats in multi-cat households, routine-sensitive cats",
            "signs": [
                "Hiding more than usual",
                "Overgrooming or licking until bald patches appear",
                "Aggression between cats that normally get along",
                "Litter box avoidance or accidents outside the box",
                "Vomiting without obvious cause",
                "Sudden onset of UTI-like symptoms (FIC is stress-induced)",
                "Loss of appetite during stressful events"
            ],
            "prevention": [
                "Keep routine consistent — feeding times, play times, your schedule",
                "Provide hiding spots and vertical space (cat trees, shelves)",
                "One litter box per cat plus one extra",
                "Feliway diffusers (synthetic pheromone) can help multi-cat tension",
                "Daily interactive play sessions — at least 15 mins reduces stress significantly",
                "Avoid introducing new animals or major changes without gradual transition"
            ],
            "urgency": "🟡 Rarely life-threatening on its own, but chronic stress causes real physical disease — treat seriously"
        },
        {
            "name": "Breathing Difficulty / Dyspnea",
            "icon": "🫁",
            "who":  "Any cat — causes include heart disease, asthma, fluid, infection",
            "signs": [
                "Open-mouth breathing (cats almost never breathe with mouth open normally)",
                "Belly moving significantly with each breath (abdominal breathing)",
                "Breathing faster than 30 breaths per minute at rest",
                "Crouching with elbows out and neck extended (trying to breathe)",
                "Blue or grey gums or tongue (oxygen deprivation — emergency)",
                "Wheezing or crackling sounds when breathing",
                "Extreme lethargy combined with any breathing change"
            ],
            "prevention": [
                "Annual heart exam for all cats (especially Kuro — every 4 months)",
                "Avoid aerosol sprays, scented candles, strong cleaning products near cats",
                "Keep cats away from cigarette smoke and incense",
                "Watch for early signs — subtle faster breathing at rest",
                "Know your cat's normal resting breath rate so you notice changes"
            ],
            "urgency": "🔴 Any breathing difficulty is an emergency — do not wait. Open-mouth breathing or blue gums = immediate vet"
        },
        {
            "name": "Heart Disease (HCM — Hypertrophic Cardiomyopathy)",
            "icon": "❤️",
            "who":  "Any cat, but Kuro has scheduled heart monitoring — take seriously",
            "signs": [
                "Fast or laboured breathing, especially at rest",
                "Sudden hind leg paralysis or weakness (aortic thromboembolism — emergency)",
                "Rapid heart rate (can sometimes be felt at the chest)",
                "Fluid in the chest causing breathing difficulty",
                "Lethargy, collapse",
                "Often NO early symptoms — detected only by vet with stethoscope or echo"
            ],
            "prevention": [
                "Regular cardiac checks — Kuro: every 4 months as scheduled",
                "Echocardiogram is the gold standard for HCM diagnosis",
                "Taurine-adequate diet (deficiency can cause dilated cardiomyopathy)",
                "Maintain healthy weight — obesity worsens heart strain",
                "Medication if diagnosed (e.g. atenolol, clopidogrel) — follow vet instructions strictly"
            ],
            "urgency": "🔴 Any cardiac event is an emergency. Scheduled checkups for Kuro are critical for early detection"
        },
        {
            "name": "Feline Asthma / Chronic Bronchitis",
            "icon": "💨",
            "who":  "Any cat, especially those exposed to irritants",
            "signs": [
                "Coughing — especially a hunched posture with head low, neck extended (looks like hairball but nothing comes up)",
                "Wheezing when breathing",
                "Breathing faster than normal at rest",
                "Exercise intolerance — gets out of breath quickly",
                "Occasional open-mouth breathing after exertion"
            ],
            "prevention": [
                "No aerosol products near cats — sprays, deodorants, cleaning sprays",
                "Unscented litter — dusty or scented litter is a common trigger",
                "No cigarette smoke indoors",
                "Air purifier helps — you're already doing this",
                "Nebulizer treatment is often used for asthma management — you're experienced with this"
            ],
            "urgency": "🟠 Chronic condition — acute attacks can be emergencies. Inhaler/nebulizer protocol from vet is important"
        },
        {
            "name": "Upper Respiratory Infection (Cat Cold)",
            "icon": "🤧",
            "who":  "Very common, especially herpesvirus (lifelong, stress reactivates it)",
            "signs": [
                "Sneezing, sometimes in fits",
                "Runny nose — clear (viral) or coloured (secondary bacterial infection)",
                "Eye discharge — watery or crusty",
                "Loss of appetite (can't smell food)",
                "Lethargy and fever",
                "Mouth ulcers (calicivirus)"
            ],
            "prevention": [
                "FVRCP vaccine covers herpesvirus and calicivirus",
                "Reduce stress — the #1 herpesvirus flare trigger",
                "Good ventilation in sleeping areas",
                "L-lysine supplement (ask vet) may help herpesvirus cats"
            ],
            "urgency": "🟠 See vet if not eating 24+ hrs or if discharge turns yellow/green (bacterial infection needs antibiotics)"
        },
        {
            "name": "Intestinal Parasites (Worms)",
            "icon": "🐛",
            "who":  "Any cat — deworming every 3 months (Haku/Sonic) or 4 months (Kuro)",
            "signs": [
                "Visible worm segments in stool or fur around tail",
                "Bloated belly",
                "Weight loss despite eating",
                "Scooting on the floor",
                "Vomiting or diarrhoea"
            ],
            "prevention": [
                "Stick to the deworming schedule: Haku/Sonic every 3 months, Kuro every 4 months",
                "Monthly flea prevention — fleas carry tapeworms",
                "Clean litter box daily",
                "Wash hands after handling litter"
            ],
            "urgency": "🟡 Not emergency but worsens without treatment — follow deworming schedule"
        },
        {
            "name": "Obesity & Metabolic Issues",
            "icon": "⚖️",
            "who":  "Indoor/neutered cats, cats fed freely",
            "signs": [
                "Cannot feel ribs without pressing hard",
                "Hanging belly swings when walking",
                "Reluctant to play or groom lower back",
                "Heavy breathing after light activity",
                "Weight above ideal for their frame"
            ],
            "prevention": [
                "Measure portions — use scale, not cups",
                "3 small meals/day is better than free-feeding",
                "Wet food has fewer calories per gram than dry",
                "Daily play — at least 2 × 15 min sessions",
                "Puzzle feeders slow eating and add mental enrichment"
            ],
            "urgency": "🟡 Slow damage but serious — linked to diabetes, joint pain, heart disease, shorter life"
        },
        {
            "name": "Ear Mites",
            "icon": "👂",
            "who":  "Any cat — treat all cats at same time if one has them",
            "signs": [
                "Head shaking and ear scratching",
                "Dark crumbly discharge in ear canal (like coffee grounds)",
                "Smell from ears",
                "Redness inside ear flap",
                "Scabs around ears from scratching"
            ],
            "prevention": [
                "Monthly ear checks during grooming",
                "Treat all cats together if one has mites",
                "Vet-recommended ear mite prevention"
            ],
            "urgency": "🟠 Not life-threatening but very uncomfortable — secondary infections can develop if untreated"
        },
        {
            "name": "Ringworm (Fungal Skin Infection)",
            "icon": "🔵",
            "who":  "Highly contagious to other cats and humans",
            "signs": [
                "Circular bald patches with scaly, red skin",
                "Brittle broken hairs around patch",
                "Itching (may or may not be present)"
            ],
            "prevention": [
                "Isolate new cats before mixing",
                "Wash bedding and grooming tools regularly",
                "Treat all cats in household if one is positive"
            ],
            "urgency": "🟠 Spreads fast to people and other cats — treat promptly"
        },
        {
            "name": "Fleas",
            "icon": "🦟",
            "who":  "Any cat — even indoor-only cats can get them",
            "signs": [
                "Scratching especially around neck and tail base",
                "Black specks in fur (flea dirt — looks like pepper)",
                "Red bumps or skin irritation",
                "Hair loss from over-grooming",
                "Visible tiny fast-moving insects"
            ],
            "prevention": [
                "Monthly vet-approved flea prevention for all cats",
                "Vacuum carpets and cat beds regularly",
                "Wash bedding monthly on hot cycle",
                "Treat all pets and the environment simultaneously"
            ],
            "urgency": "🟡 Not immediately dangerous for adults but causes anemia in kittens and carries tapeworms"
        },
        {
            "name": "Feline Panleukopenia (Cat Parvovirus)",
            "icon": "⚠️",
            "who":  "Unvaccinated cats, kittens highest risk",
            "signs": [
                "Sudden high fever",
                "Severe vomiting and bloody diarrhoea",
                "Extreme lethargy — barely moves",
                "Hiding and appearing to be in pain",
                "Not eating at all"
            ],
            "prevention": [
                "FVRCP vaccination — annual boosters",
                "Virus survives months on surfaces — disinfect thoroughly if exposed"
            ],
            "urgency": "🔴 Life-threatening — requires immediate emergency vet care. Very high mortality without treatment"
        },
        {
            "name": "Hyperthyroidism",
            "icon": "🔬",
            "who":  "Middle-aged to senior cats (8+ years)",
            "signs": [
                "Weight loss despite increased appetite",
                "Increased thirst and urination",
                "Hyperactivity, restlessness, vocalising at night",
                "Vomiting or diarrhoea",
                "Dull, greasy, unkempt coat"
            ],
            "prevention": [
                "Annual blood tests after age 7 catch it early",
                "Use BPA-free food packaging where possible",
                "Early treatment prevents heart and kidney damage"
            ],
            "urgency": "🟠 Progresses — damages heart and kidneys if untreated. Annual bloods are essential"
        },
    ]

    # ── Visual guides ──
    with st.expander("💩 Poop Guide — What's Normal vs Abnormal", expanded=False):
        st.markdown("#### Normal poop")
        st.success(
            "**Shape:** Log-shaped, holds together  \n"
            "**Colour:** Medium to dark brown  \n"
            "**Consistency:** Firm but not rock hard — shouldn't crumble or smear  \n"
            "**Smell:** Unpleasant but not overwhelmingly foul  \n"
            "**Frequency:** Once daily or once every 36 hours")

        st.markdown("#### Abnormal poop — what it means")
        cols = st.columns(2)
        with cols[0]:
            st.error("**Diarrhoea (liquid/loose):** Intestinal irritation, parasites, food intolerance, stress, infection, or IBD. "
                     "If it lasts more than 24 hrs or contains blood, see a vet.")
            st.error("**Blood in stool (red):** Fresh blood = lower intestinal issue. Could be colitis, polyps, or parasites. "
                     "Single episode may resolve; recurring = vet visit.")
            st.error("**Black tarry stool:** This is digested blood — indicates bleeding in the upper GI tract (stomach, small intestine). "
                     "Urgent — needs vet same day.")
        with cols[1]:
            st.warning("**Mucus in stool:** A small amount is normal. Large amounts = colitis or inflammatory bowel disease.")
            st.warning("**Very dry/hard pellets:** Constipation — increase wet food and water. Watch for straining.")
            st.warning("**Yellow or greenish:** Food moving through too quickly, or bile issue. "
                       "Monitor — if ongoing, vet check.")
            st.warning("**White or very pale:** Possible liver or pancreatic issue. See vet.")

    with st.expander("🚽 Urine Guide — What's Normal vs Abnormal", expanded=False):
        st.markdown("#### Normal urine")
        st.success(
            "**Colour:** Pale to medium yellow  \n"
            "**Smell:** Mild ammonia, not overwhelming  \n"
            "**Consistency:** Clear, no cloudiness or particles  \n"
            "**Frequency:** 2-4 times daily  \n"
            "**Amount:** A decent puddle each time — not tiny drops")

        st.markdown("#### Abnormal urine — what it means")
        cols = st.columns(2)
        with cols[0]:
            st.error("**Pink, red, or orange urine:** Blood in urine — UTI, crystals, stones, or blockage. "
                     "If cat is also straining: EMERGENCY.")
            st.error("**No urine at all:** Blockage — life-threatening. Go to emergency vet immediately.")
            st.warning("**Cloudy or milky urine:** Infection, crystals, or protein in urine. Vet check needed.")
        with cols[1]:
            st.warning("**Very dark yellow / strong smell:** Dehydration — increase water and wet food urgently.")
            st.warning("**Very pale / large amounts frequently:** Possible diabetes or kidney disease. "
                       "Blood test needed.")
            st.warning("**Tiny amounts, many trips:** Partial blockage or UTI — see vet same day.")

    with st.expander("🤮 Vomit Guide — What the Colour Means", expanded=False):
        st.markdown("#### Vomit colour guide")
        cols = st.columns(2)
        with cols[0]:
            st.info("**Clear / foamy white:** Empty stomach — cat vomited on an empty stomach. "
                    "Try feeding smaller, more frequent meals. If daily, see vet.")
            st.info("**Yellow / yellow-green:** Bile — vomited on an empty stomach, OR bile reflux. "
                    "Common in cats who go 12+ hours without food. Add a small meal before bed.")
            st.success("**Brown with food chunks:** Undigested food — ate too fast or too much at once. "
                       "Try puzzle feeder or smaller portions.")
            st.warning("**Brown liquid (no food):** Could be old blood or digested matter. "
                       "If dark and coffee-ground-like: see vet — upper GI bleeding.")
        with cols[1]:
            st.error("**Red / bright red:** Fresh blood. If more than a tiny streak: vet immediately.")
            st.error("**Dark red / black:** Digested blood (like coffee grounds). Upper GI bleeding — urgent.")
            st.warning("**Green:** Ate something green (grass) OR bile with digested material. "
                       "Single episode usually fine; recurring = vet check.")
            st.warning("**White and foamy repeatedly:** Could be hairballs, but if no hairball comes up and it "
                       "recurs — could be GI issue. Monitor and vet if ongoing.")

        st.markdown("#### When to see a vet for vomiting")
        st.error(
            "- Vomiting blood (any colour red or dark brown)  \n"
            "- Vomiting more than 2-3 times per day  \n"
            "- Vomiting combined with lethargy, not eating, or hiding  \n"
            "- Vomiting combined with diarrhoea (risk of dehydration)  \n"
            "- Foreign object suspected (toy parts, string, etc.)")

    # ── Filter ──
    st.markdown("---")
    urgency_filter = st.selectbox("Filter by urgency",
        ["All","🔴 Emergency","🟠 See vet soon","🟡 Monitor / Treat"])
    search = st.text_input("🔍 Search symptoms or conditions",
                           placeholder="e.g., vomiting, breathing, kidney")

    def ulvl(u):
        if "🔴" in u: return "🔴 Emergency"
        if "🟠" in u: return "🟠 See vet soon"
        return "🟡 Monitor / Treat"

    filtered = diseases
    if urgency_filter != "All":
        filtered = [d for d in filtered if ulvl(d["urgency"]) == urgency_filter]
    if search:
        sl = search.lower()
        filtered = [d for d in filtered
                    if sl in d["name"].lower()
                    or any(sl in s.lower() for s in d["signs"])
                    or any(sl in p.lower() for p in d["prevention"])]

    if not filtered:
        st.info("No conditions match your search."); return

    st.write(f"Showing **{len(filtered)}** of {len(diseases)} conditions")
    for dis in filtered:
        with st.expander(f"{dis['icon']} {dis['name']}", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**👥 Who:** {dis['who']}")
                st.markdown("**🚨 Warning signs:**")
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
        "Not eating / loss of appetite":       ["Upper Respiratory Infection","Red / Inflamed Gums","Feline Panleukopenia","Hyperthyroidism","Urinary Tract Infection","Kidney Issues","Breathing Difficulty"],
        "Vomiting":                            ["Intestinal Parasites","Feline Panleukopenia","Hyperthyroidism","Kidney Issues","Feline Asthma"],
        "Diarrhoea":                           ["Intestinal Parasites","Feline Panleukopenia","Hyperthyroidism","Stress / Anxiety"],
        "Straining to urinate / no urine":     ["Urinary Tract Infection","Urinary / Kidney Issues"],
        "Blood in urine":                      ["Urinary Tract Infection","Urinary / Kidney Issues"],
        "Increased thirst and urination":      ["Hyperthyroidism","Urinary / Kidney Issues"],
        "Sneezing / runny nose or eyes":       ["Upper Respiratory Infection"],
        "Open-mouth breathing":                ["Breathing Difficulty","Heart Disease","Feline Asthma"],
        "Fast breathing at rest":              ["Breathing Difficulty","Heart Disease","Feline Asthma"],
        "Wheezing / coughing":                 ["Feline Asthma","Breathing Difficulty"],
        "Hind leg weakness / paralysis":       ["Heart Disease"],
        "Red or inflamed gums":                ["Red / Inflamed Gums"],
        "Hiding more than usual":              ["Stress / Anxiety","Upper Respiratory Infection","Feline Panleukopenia"],
        "Hair loss / bald patches":            ["Ringworm","Fleas","Stress / Anxiety"],
        "Scratching ears / head shaking":      ["Ear Mites"],
        "Weight loss despite eating":          ["Intestinal Parasites","Hyperthyroidism","Kidney Issues"],
        "Weight gain / belly hanging":         ["Obesity & Metabolic Issues"],
        "Lethargy / barely moves":             ["Feline Panleukopenia","Breathing Difficulty","Heart Disease","Urinary Tract Infection","Kidney Issues"],
        "Bad breath or mouth pain":            ["Red / Inflamed Gums"],
        "Scratching body / restless":          ["Fleas","Ringworm","Stress / Anxiety"],
        "Dark ear discharge":                  ["Ear Mites"],
        "Scooting on floor":                   ["Intestinal Parasites"],
        "Pot belly / bloated":                 ["Intestinal Parasites"],
        "Overgrooming / licking bald patches": ["Stress / Anxiety","Fleas"],
        "Litter box avoidance":                ["Urinary Tract Infection","Stress / Anxiety"],
    }

    selected = []
    cols = st.columns(2)
    for i, sym in enumerate(symptom_map):
        with cols[i % 2]:
            if st.checkbox(sym, key=f"sym_{i}"): selected.append(sym)

    if selected:
        st.markdown("---")
        st.markdown("**Possible conditions:**")
        scores = {}
        for sym in selected:
            for dn in symptom_map.get(sym, []):
                scores[dn] = scores.get(dn, 0) + 1
        for dn, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            md = next((d for d in diseases if dn.split("(")[0].strip().lower() in d["name"].lower()), None)
            if md:
                u = md["urgency"]
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

    # ── Vet appointment reminders ──
    reminders = get_vet_reminders()
    urgent_reminders = [r for r in reminders
                        if r['days_away'] is not None and (r['overdue'] or r['days_away'] <= 30)]
    not_set = [r for r in reminders if r['next_date'] == 'Not set']

    if urgent_reminders or not_set:
        st.subheader("📅 Vet Appointment Reminders")
        for r in urgent_reminders:
            if r['overdue']:
                st.error(f"🔴 **{r['cat']}** — {r['label']} was due on {r['next_date']} "
                         f"({abs(r['days_away'])} days overdue!)")
            elif r['days_away'] <= 7:
                st.error(f"🟠 **{r['cat']}** — {r['label']} in **{r['days_away']} days** ({r['next_date']})")
            elif r['days_away'] <= 14:
                st.warning(f"🟡 **{r['cat']}** — {r['label']} in {r['days_away']} days ({r['next_date']})")
            else:
                st.info(f"🟢 **{r['cat']}** — {r['label']} coming up in {r['days_away']} days ({r['next_date']})")
        for r in not_set:
            st.warning(f"⚠️ **{r['cat']}** — {r['label']} date not set. Update in Cat Profiles.")
        st.markdown("---")

    # ── Active medications ──
    active_meds = get_active_medications_today()
    if active_meds:
        st.subheader("💊 Active Medicines/Treatments Today")
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

    # ── Stats ──
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        te = sum(len(v) for cd in st.session_state.health_data.values() for v in cd.values())
        st.metric("Total Entries", te)
    with c2:
        ts  = str(date.today())
        tsk = [l['task'] for l in st.session_state.task_logs.get(ts, [])]
        st.metric("Today's Tasks", f"{len(tsk)}/{len(st.session_state.tasks.get('daily',[]))}")
    with c3:
        st.metric("Vet Visits", sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))
    with c4:
        ac = sum(1 for c in st.session_state.cats
                 if c in st.session_state.health_data and st.session_state.health_data[c])
        st.metric("Active Cats", f"{ac}/{len(st.session_state.cats)}")

    # ── Weekly comparison ──
    st.markdown("---")
    st.subheader("📊 Weekly Comparison — All Cats")
    today    = date.today()
    week_ago = today - timedelta(days=7)
    comp = []
    for cat in st.session_state.cats:
        daily = get_daily_aggregated(cat, week_ago, today)
        if daily:
            comp.append({
                'Cat':            cat,
                'Avg Water/Day':  round(sum(d['water_drinks']     for d in daily.values())/len(daily),1),
                'Avg Food/Day':   round(sum(d['food_eats']        for d in daily.values())/len(daily),1),
                'Avg Litter/Day': round(sum(d['litter_box_times'] for d in daily.values())/len(daily),1),
                'Poop Days':      sum(1 for d in daily.values() if d.get('pooped')),
                'Days Tracked':   len(daily)
            })
    if comp:
        cdf = pd.DataFrame(comp)
        st.dataframe(cdf, use_container_width=True, hide_index=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Water',  x=cdf['Cat'], y=cdf['Avg Water/Day'],  marker_color='#4fc3f7'))
        fig.add_trace(go.Bar(name='Food',   x=cdf['Cat'], y=cdf['Avg Food/Day'],   marker_color='#81c784'))
        fig.add_trace(go.Bar(name='Litter', x=cdf['Cat'], y=cdf['Avg Litter/Day'], marker_color='#ffb74d'))
        fig.update_layout(barmode='group', height=280, margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet this week.")

    # ── PDF export ──
    st.markdown("---")
    st.subheader("📄 Export Vet Report")
    c1, c2 = st.columns(2)
    with c1: pdf_cat = st.selectbox("Report for", ["All Cats"] + st.session_state.cats)
    with c2:
        st.write(""); st.write("")
        if REPORTLAB_AVAILABLE:
            pdf_bytes = generate_pdf_report(None if pdf_cat=="All Cats" else pdf_cat)
            st.download_button("📥 Download PDF", data=pdf_bytes,
                               file_name=f"cat_report_{date.today()}.pdf",
                               mime="application/pdf", type="primary",
                               use_container_width=True)
        else:
            st.warning("Install reportlab: pip install reportlab")

    # ── Per-cat summaries with full analysis explanations ──
    st.markdown("---")
    st.subheader("🐱 Individual Cat Analysis")
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

    st.markdown("---")
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
    st.subheader("🗑️ Delete")
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
            c: {'age':'','breed':'','weight':'','vet_visits':[],'notes':'',
                'birthdate':'','next_checkup':'','next_vaccines':'',
                'next_deworming':'','next_heart_checkup':''}
            for c in st.session_state.cats
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
    with c1: st.metric("Health Entries",    sum(len(v) for cd in st.session_state.health_data.values() for v in cd.values()))
    with c2: st.metric("Task Completions",  sum(len(l) for l in st.session_state.task_logs.values()))
    with c3: st.metric("Vet Visits",        sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))


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

        ts   = str(date.today())
        done = [l['task'] for l in st.session_state.task_logs.get(ts, [])]
        inc  = [t for t in st.session_state.tasks['daily'] if t not in done]
        if inc: st.info(f"📝 Incomplete daily tasks: {', '.join(inc)}")

        # Thursday grooming reminder
        if date.today().weekday() == 3:
            st.info("🪥 It's Thursday — grooming day for the cats!")

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

    st.title("🐱 Cat Health Tracker")

    if AUTH_ENABLED:
        c1, c2 = st.columns([5,1])
        with c1: st.write("Comprehensive health and task management for Haku, Kuro & Sonic")
        with c2:
            st.write(f"👤 {st.session_state.get('username','User')}")
            if st.button("🚪 Logout", key="logout_btn"): logout()
    else:
        st.write("Comprehensive health and task management for Haku, Kuro & Sonic")

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
