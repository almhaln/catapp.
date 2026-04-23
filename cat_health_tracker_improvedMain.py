import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import json
import os
import io
import calendar
from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# ReportLab for PDF export
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Import authentication module
try:
    from auth_module import (
        check_authentication,
        login_page,
        logout,
        encrypt_data,
        decrypt_data
    )
    AUTH_ENABLED = True
except ImportError:
    AUTH_ENABLED = False


# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
def init_session_state():
    if 'cats' not in st.session_state:
        st.session_state.cats = ['Haku', 'Kuro', 'Sonic']

    if 'health_data' not in st.session_state:
        st.session_state.health_data = {}

    if 'tasks' not in st.session_state:
        st.session_state.tasks = {
            'daily': [
                'Clean food bowl', 'Add water', 'Clean litter box',
                'Let them out my room', 'Pray for them'
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
            'quarterly': []
        }
    else:
        weekly = st.session_state.tasks.get('weekly', [])
        if 'Clean air purifier' not in weekly:
            weekly.append('Clean air purifier')
            st.session_state.tasks['weekly'] = weekly
        monthly = st.session_state.tasks.get('monthly', [])
        if 'Clean air purifier filter' not in monthly:
            monthly.append('Clean air purifier filter')
            st.session_state.tasks['monthly'] = monthly

    if 'task_schedules' not in st.session_state:
        st.session_state.task_schedules = {
            'daily': {
                'Clean food bowl': 1, 'Add water': 1, 'Clean litter box': 2,
                'Let them out my room': 2, 'Pray for them': 1
            },
            'weekly': {
                'Clean water fountain': 1, 'Clean room': 2, 'Clean air purifier': 1
            },
            'monthly': {
                'Deep clean litter box': 1, 'Buy food': 1, 'Buy wet food': 1,
                'Buy litter': 1, 'Buy treats': 1, 'Buy toys': 1,
                'Clean eyes': 1, 'Clean chin': 1, 'Clean cat tree': 1,
                'Clean bedding': 1, 'Clean air purifier filter': 1
            }
        }

    if 'last_entries' not in st.session_state:
        st.session_state.last_entries = {cat: None for cat in st.session_state.cats}

    if 'task_logs' not in st.session_state:
        st.session_state.task_logs = {}

    if 'last_reminder' not in st.session_state:
        st.session_state.last_reminder = None

    if 'cat_profiles' not in st.session_state:
        st.session_state.cat_profiles = {
            cat: {'age': '', 'breed': '', 'weight': '', 'vet_visits': [], 'notes': ''}
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


# ─────────────────────────────────────────────
# Data persistence
# ─────────────────────────────────────────────
def save_data():
    try:
        health_data_str = json.dumps(st.session_state.health_data, default=str)
        task_logs_str   = json.dumps(st.session_state.task_logs,   default=str)
        profiles_str    = json.dumps(st.session_state.cat_profiles, default=str)

        if AUTH_ENABLED:
            health_data_str = encrypt_data(health_data_str)
            task_logs_str   = encrypt_data(task_logs_str)
            profiles_str    = encrypt_data(profiles_str)

        with open('health_data.json',  'w') as f: f.write(health_data_str)
        with open('task_logs.json',    'w') as f: f.write(task_logs_str)
        with open('cat_profiles.json', 'w') as f: f.write(profiles_str)

    except Exception as e:
        st.error(f"Error saving data: {e}")


def load_data():
    """Only runs once per browser session — guards against overwriting live state on every rerun."""
    if st.session_state.data_loaded:
        return

    try:
        if os.path.exists('health_data.json'):
            with open('health_data.json', 'r') as f:
                data_str = f.read()
            if AUTH_ENABLED and data_str:
                try: data_str = decrypt_data(data_str)
                except: pass
            if data_str:
                st.session_state.health_data = json.loads(data_str)

        if os.path.exists('task_logs.json'):
            with open('task_logs.json', 'r') as f:
                data_str = f.read()
            if AUTH_ENABLED and data_str:
                try: data_str = decrypt_data(data_str)
                except: pass
            if data_str:
                st.session_state.task_logs = json.loads(data_str)

        if os.path.exists('cat_profiles.json'):
            with open('cat_profiles.json', 'r') as f:
                data_str = f.read()
            if AUTH_ENABLED and data_str:
                try: data_str = decrypt_data(data_str)
                except: pass
            if data_str:
                loaded_profiles = json.loads(data_str)
                for cat, profile in loaded_profiles.items():
                    if 'vet_visits' in profile and isinstance(profile['vet_visits'], list):
                        if profile['vet_visits'] and isinstance(profile['vet_visits'][0], str):
                            profile['vet_visits'] = []
                st.session_state.cat_profiles = loaded_profiles

        st.session_state.data_loaded = True

    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.session_state.task_logs    = {}
        st.session_state.cat_profiles = {
            cat: {'age': '', 'breed': '', 'weight': '', 'vet_visits': [], 'notes': ''}
            for cat in st.session_state.cats
        }
        st.session_state.data_loaded = True


# ─────────────────────────────────────────────
# Health entry functions
# ─────────────────────────────────────────────
def add_health_entry(cat_name: str, entry_data: Dict):
    if cat_name not in st.session_state.health_data:
        st.session_state.health_data[cat_name] = {}

    timestamp = datetime.now().isoformat()
    if timestamp not in st.session_state.health_data[cat_name]:
        st.session_state.health_data[cat_name][timestamp] = []

    entry_data['timestamp'] = timestamp
    st.session_state.health_data[cat_name][timestamp].append(entry_data)
    st.session_state.last_entries[cat_name] = datetime.now()
    save_data()


def get_health_entries(cat_name: str, start_date: date, end_date: date) -> List[Dict]:
    entries = []
    if cat_name in st.session_state.health_data:
        for timestamp, date_entries in st.session_state.health_data[cat_name].items():
            try:
                entry_date = datetime.fromisoformat(timestamp).date()
                if start_date <= entry_date <= end_date:
                    for entry in date_entries:
                        entry_copy = dict(entry)
                        entry_copy['timestamp'] = timestamp
                        entries.append(entry_copy)
            except:
                continue
    return entries


def update_health_entry(cat_name: str, timestamp: str, entry_index: int, updated_data: Dict):
    if cat_name in st.session_state.health_data and timestamp in st.session_state.health_data[cat_name]:
        if entry_index < len(st.session_state.health_data[cat_name][timestamp]):
            st.session_state.health_data[cat_name][timestamp][entry_index].update(updated_data)
            save_data()


def delete_health_entry(cat_name: str, timestamp: str, entry_index: int):
    if cat_name in st.session_state.health_data and timestamp in st.session_state.health_data[cat_name]:
        if entry_index < len(st.session_state.health_data[cat_name][timestamp]):
            st.session_state.health_data[cat_name][timestamp].pop(entry_index)
            if not st.session_state.health_data[cat_name][timestamp]:
                del st.session_state.health_data[cat_name][timestamp]
            save_data()


# ─────────────────────────────────────────────
# Task management
# ─────────────────────────────────────────────
def add_task_completion(task_name: str, cat_name: str = None, notes: str = ""):
    today = str(date.today())
    if today not in st.session_state.task_logs:
        st.session_state.task_logs[today] = []
    st.session_state.task_logs[today].append({
        'task': task_name,
        'cat': cat_name,
        'completed_at': datetime.now().isoformat(),
        'notes': notes
    })
    save_data()


def get_task_completions(start_date: date, end_date: date) -> Dict:
    completions = {}
    for date_str, day_logs in st.session_state.task_logs.items():
        try:
            log_date = date.fromisoformat(date_str)
            if start_date <= log_date <= end_date:
                completions[date_str] = day_logs
        except:
            continue
    return completions


# ─────────────────────────────────────────────
# Daily aggregation
# ─────────────────────────────────────────────
def get_daily_aggregated(cat_name: str, start_date: date, end_date: date) -> Dict:
    entries = get_health_entries(cat_name, start_date, end_date)
    daily = {}

    for entry in entries:
        try:
            entry_date = datetime.fromisoformat(entry['timestamp']).date()
        except:
            continue

        if entry_date not in daily:
            daily[entry_date] = {
                'water_drinks': 0, 'food_eats': 0, 'litter_box_times': 0,
                'moods': [], 'general_appearances': [], 'medications': [],
                'grooming_tasks': set(), 'litter_quality_issues': [],
                'notes': [], 'entry_count': 0
            }

        d = daily[entry_date]
        d['water_drinks']     += entry.get('water_drinks', 0)
        d['food_eats']        += entry.get('food_eats', 0)
        d['litter_box_times'] += entry.get('litter_box_times', 0)
        d['entry_count']      += 1

        if entry.get('mood'):               d['moods'].append(entry['mood'])
        if entry.get('general_appearance'): d['general_appearances'].append(entry['general_appearance'])
        if entry.get('medication_name'):
            d['medications'].append({
                'name':       entry['medication_name'],
                'dosage':     entry.get('medication_dosage', ''),
                'frequency':  entry.get('medication_frequency', ''),
                'reason':     entry.get('medication_reason', ''),
                'start_date': entry.get('medication_start_date', ''),
                'end_date':   entry.get('medication_end_date', '')
            })
        if entry.get('grooming_tasks'):
            for task, done in entry['grooming_tasks'].items():
                if done: d['grooming_tasks'].add(task)
        if entry.get('litter_quality'):
            for q in entry['litter_quality']:
                if q and q.strip(): d['litter_quality_issues'].append(q.strip())
        if entry.get('notes') and entry['notes'].strip():
            d['notes'].append(entry['notes'].strip())

    return daily


# ─────────────────────────────────────────────
# Health analysis
# ─────────────────────────────────────────────
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
                'concerns': [], 'recommendations': ['Start logging health data']}

    total_days    = len(daily)
    total_entries = sum(d['entry_count'] for d in daily.values())
    water_avg     = sum(d['water_drinks']     for d in daily.values()) / total_days
    food_avg      = sum(d['food_eats']        for d in daily.values()) / total_days
    litter_avg    = sum(d['litter_box_times'] for d in daily.values()) / total_days

    all_moods  = [m for d in daily.values() for m in d['moods']]
    mood_trend = 'stable'
    if all_moods:
        poor = sum(1 for m in all_moods if m in ['Very Poor', 'Poor'])
        good = sum(1 for m in all_moods if m in ['Good', 'Excellent'])
        if poor > len(all_moods) / 2:   mood_trend = 'declining'
        elif good > len(all_moods) / 2: mood_trend = 'good'

    all_litter_issues = [
        (str(d_date), issue)
        for d_date, d in daily.items()
        for issue in d['litter_quality_issues']
        if any(kw in issue.lower() for kw in ['blood', 'diarrhea', 'abnormal'])
    ]

    concerns, recommendations = [], []
    if water_avg < 2:
        concerns.append(f'Low water intake (avg {water_avg:.1f}/day)')
        recommendations.append('Add more water sources or try wet food')
    if food_avg < 1:
        concerns.append(f'Low food intake (avg {food_avg:.1f}/day)')
        recommendations.append('Monitor appetite — consult vet if it persists')
    if litter_avg > 6:
        concerns.append(f'High litter box usage (avg {litter_avg:.1f}/day)')
        recommendations.append('Monitor for urinary tract issues or stress')
    if all_litter_issues:
        concerns.append(f'Litter quality issues ({len(all_litter_issues)} instance(s))')
        recommendations.append('URGENT: Consult vet about litter abnormalities')
    if mood_trend == 'declining':
        concerns.append('Mood has been declining this week')
        recommendations.append('Check for illness, stress, or environmental changes')
    if not concerns:
        recommendations = ['No concerns — keep up the great care!']

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
        'recommendations': recommendations
    }


# ─────────────────────────────────────────────
# Active medication helper
# ─────────────────────────────────────────────
def get_active_medications_today() -> List[Dict]:
    today  = date.today()
    active = []

    for cat in st.session_state.cats:
        entries = get_health_entries(cat, today - timedelta(days=90), today)
        seen = set()
        for entry in entries:
            med_name  = entry.get('medication_name', '').strip()
            start_str = entry.get('medication_start_date', '')
            end_str   = entry.get('medication_end_date', '')
            if not med_name or not start_str or not end_str:
                continue
            try:
                med_start = date.fromisoformat(start_str)
                med_end   = date.fromisoformat(end_str)
            except:
                continue
            key = f"{cat}_{med_name}_{end_str}"
            if key in seen: continue
            seen.add(key)
            if med_start <= today <= med_end:
                active.append({
                    'cat':       cat,
                    'name':      med_name,
                    'dosage':    entry.get('medication_dosage', ''),
                    'frequency': entry.get('medication_frequency', ''),
                    'reason':    entry.get('medication_reason', ''),
                    'end_date':  end_str,
                    'days_left': (med_end - today).days
                })
    return active


# ─────────────────────────────────────────────
# Cat summary text
# ─────────────────────────────────────────────
def generate_cat_summary(cat_name: str) -> str:
    a       = analyze_cat_health(cat_name)
    profile = a.get('profile', {})

    if a['status'] == 'no_data':
        return f"No health data recorded yet for **{cat_name}**. Start adding entries to see a summary here."

    lines = [f"### 🐱 {cat_name}"]
    info_parts = []
    if profile.get('age'):    info_parts.append(f"Age: {profile['age']}")
    if profile.get('breed'):  info_parts.append(f"Breed: {profile['breed']}")
    if profile.get('weight'): info_parts.append(f"Weight: {profile['weight']} kg")
    if info_parts: lines.append(" · ".join(info_parts))

    lines.append(f"\n**Period:** Past 7 days | **Days tracked:** {a['total_days']} | **Total entries:** {a['total_entries']}")
    lines.append("\n**Daily averages (all entries combined):**")
    lines.append(f"- 💧 Water: **{a['water_avg']:.1f}** times/day")
    lines.append(f"- 🍽️ Food: **{a['food_avg']:.1f}** times/day")
    lines.append(f"- 🚽 Litter box: **{a['litter_avg']:.1f}** times/day")
    lines.append(f"- 😊 Mood trend: **{a.get('mood_trend', 'unknown').title()}**")

    if a['daily']:
        lines.append("\n**Day-by-day breakdown:**")
        for d_date in sorted(a['daily'].keys(), reverse=True)[:5]:
            d = a['daily'][d_date]
            parts = []
            if d['water_drinks']:     parts.append(f"💧 {d['water_drinks']}x water")
            if d['food_eats']:        parts.append(f"🍽️ {d['food_eats']}x food")
            if d['litter_box_times']: parts.append(f"🚽 {d['litter_box_times']}x litter")
            if d['grooming_tasks']:   parts.append(f"🪥 {', '.join(d['grooming_tasks'])}")
            label = f"({d['entry_count']} {'entry' if d['entry_count'] == 1 else 'entries'})"
            lines.append(f"- **{d_date}** {label}: {' · '.join(parts) if parts else 'No activity logged'}")

    all_meds = {}
    for d in a['daily'].values():
        for med in d['medications']:
            if med['name']: all_meds[med['name']] = med
    if all_meds:
        lines.append("\n**💊 Medications this week:**")
        for name, med in all_meds.items():
            s = f"- {name}"
            if med.get('dosage'):    s += f" — {med['dosage']}"
            if med.get('frequency'): s += f" · {med['frequency']}"
            if med.get('start_date') and med.get('end_date'):
                s += f" ({med['start_date']} → {med['end_date']})"
            lines.append(s)

    if a.get('litter_issues'):
        lines.append("\n**🚨 Litter quality alerts:**")
        for d_date, issue in a['litter_issues'][:5]:
            lines.append(f"- {d_date}: {issue}")

    if a['concerns']:
        lines.append("\n**⚠️ Concerns:**")
        for c in a['concerns']: lines.append(f"- {c}")
        lines.append("\n**💡 Recommendations:**")
        for r in a['recommendations']: lines.append(f"- {r}")
    else:
        lines.append("\n**✅ No concerns detected. Keep up the great care!**")

    if a.get('vet_history'):
        recent = sorted(a['vet_history'], key=lambda x: x.get('date', ''), reverse=True)[:2]
        if recent:
            lines.append("\n**🏥 Recent vet visits:**")
            for v in recent:
                lines.append(f"- {v.get('date','?')}: {v.get('reason','Checkup')} — Dr. {v.get('doctor','?')}")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# PDF report
# ─────────────────────────────────────────────
def generate_pdf_report(cat_name: str = None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles    = getSampleStyleSheet()
    ts        = ParagraphStyle('T', parent=styles['Title'],   fontSize=20, spaceAfter=6, textColor=colors.HexColor('#2c3e50'))
    hs        = ParagraphStyle('H', parent=styles['Heading2'],fontSize=13, spaceAfter=4, textColor=colors.HexColor('#2980b9'))
    ss        = ParagraphStyle('S', parent=styles['Heading3'],fontSize=11, spaceAfter=3, textColor=colors.HexColor('#555'))
    ns        = ParagraphStyle('N', parent=styles['Normal'],  fontSize=10, leading=14)
    cs        = ParagraphStyle('C', parent=styles['Normal'],  fontSize=8,  textColor=colors.grey)

    def make_table(data, col_widths, header_color):
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,0), header_color),
            ('TEXTCOLOR',  (0,0),(-1,0), colors.white),
            ('FONTNAME',   (0,0),(-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0),(-1,-1), 9),
            ('GRID',       (0,0),(-1,-1), 0.5, colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
            ('LEFTPADDING',(0,0),(-1,-1), 5),
            ('RIGHTPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING', (0,0),(-1,-1), 4),
            ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        return t

    story = []
    story.append(Paragraph("Cat Health Report", ts))
    story.append(Paragraph(f"Generated: {date.today().strftime('%B %d, %Y')}", cs))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7'), spaceAfter=12))

    for cat in ([cat_name] if cat_name else st.session_state.cats):
        a       = analyze_cat_health(cat)
        profile = a.get('profile', {})
        story.append(Paragraph(f"Cat: {cat}", hs))

        pdata = [["Field", "Value"]]
        for lbl, key in [("Age","age"),("Breed","breed"),("Last Recorded Weight","weight"),("Notes","notes")]:
            if profile.get(key):
                pdata.append([lbl, f"{profile[key]} kg" if key == 'weight' else profile[key]])
        if len(pdata) > 1:
            story.append(make_table(pdata, [5*cm, 11*cm], colors.HexColor('#2980b9')))
            story.append(Spacer(1, 8))

        story.append(Paragraph("Weekly Health Summary (past 7 days)", ss))
        if a['status'] == 'no_data':
            story.append(Paragraph("No health data recorded for this cat.", ns))
        else:
            sdata = [["Metric","Value"],
                     ["Days Tracked", str(a['total_days'])],
                     ["Total Entries", str(a['total_entries'])],
                     ["Avg Water / Day", f"{a['water_avg']:.1f} times"],
                     ["Avg Food / Day",  f"{a['food_avg']:.1f} times"],
                     ["Avg Litter / Day",f"{a['litter_avg']:.1f} times"],
                     ["Mood Trend", a.get('mood_trend','unknown').title()],
                     ["Overall Status",  a['status'].title()]]
            story.append(make_table(sdata, [7*cm, 9*cm], colors.HexColor('#27ae60')))
            story.append(Spacer(1, 8))
            if a['concerns']:
                story.append(Paragraph("Concerns", ss))
                for c in a['concerns']: story.append(Paragraph(f"- {c}", ns))
                story.append(Paragraph("Recommendations", ss))
                for r in a['recommendations']: story.append(Paragraph(f"- {r}", ns))
                story.append(Spacer(1, 8))

            today_meds = [m for m in get_active_medications_today() if m['cat'] == cat]
            if today_meds:
                story.append(Paragraph("Active Medications", ss))
                mdata = [["Medication","Dosage","Frequency","Reason","Until"]]
                for m in today_meds:
                    mdata.append([m['name'], m.get('dosage','-'), m.get('frequency','-'),
                                  m.get('reason','-'), m['end_date']])
                story.append(make_table(mdata, [3.5*cm,2.5*cm,3*cm,3.5*cm,3.5*cm], colors.HexColor('#e74c3c')))
                story.append(Spacer(1, 8))

        vet_visits = profile.get('vet_visits', [])
        if vet_visits:
            story.append(Paragraph("Vet Visit History", ss))
            vdata = [["Date","Doctor","Reason","Medication"]]
            for v in sorted(vet_visits, key=lambda x: x.get('date',''), reverse=True):
                vdata.append([v.get('date','-'), f"Dr. {v.get('doctor','-')}",
                              v.get('reason','-'), v.get('medication','-')])
            story.append(make_table(vdata, [3*cm,4*cm,5*cm,4*cm], colors.HexColor('#8e44ad')))

        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#bdc3c7'), spaceAfter=12))

    story.append(Paragraph("Generated by Cat Health Tracker. Always consult your vet for medical advice.", cs))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ─────────────────────────────────────────────
# Monthly task calendar
# ─────────────────────────────────────────────
def monthly_task_calendar(year: int, month: int):
    monthly_tasks = st.session_state.tasks.get('monthly', [])
    if not monthly_tasks:
        st.info("No monthly tasks defined.")
        return

    first_day = date(year, month, 1)
    last_day  = date(year, month, calendar.monthrange(year, month)[1])
    completions = get_task_completions(first_day, last_day)

    done_dates = {}
    for date_str, logs in completions.items():
        done = [log['task'] for log in logs if log['task'] in monthly_tasks]
        if done: done_dates[date_str] = done

    cal = calendar.monthcalendar(year, month)
    cols = st.columns(7)
    for i, name in enumerate(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']):
        cols[i].markdown(f"**{name}**")

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                d        = date(year, month, day)
                date_str = str(d)
                if date_str in done_dates:  label = f"**{day}** ✅"
                elif d == date.today():     label = f"**{day}** 📍"
                else:                       label = str(day)
                if day == 1: label = "🔔 " + label
                cols[i].markdown(label)

    done_this_month = set()
    for tasks_done in done_dates.values(): done_this_month.update(tasks_done)
    st.markdown(f"\n**Monthly tasks completed this month:** {len(done_this_month)}/{len(monthly_tasks)}")
    if done_this_month:   st.success("Done: " + ", ".join(sorted(done_this_month)))
    remaining = [t for t in monthly_tasks if t not in done_this_month]
    if remaining: st.warning("Still needed: " + ", ".join(remaining))


# ─────────────────────────────────────────────
# Page: Cat Profiles  ← PROFILE SAVE FIX
# ─────────────────────────────────────────────
def cat_profiles_page():
    st.header("🐱 Cat Profiles")

    for cat in st.session_state.cats:
        # ── FIX: always read the live profile from session_state, not a snapshot ──
        profile = st.session_state.cat_profiles.get(cat, {})

        with st.container(border=True):
            col_icon, col_info = st.columns([1, 4])
            with col_icon:
                st.markdown("## 🐱")
                st.markdown(f"**{cat}**")
            with col_info:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Age",        profile.get('age')   or "—")
                c2.metric("Breed",      profile.get('breed') or "—")
                c3.metric("Weight",     f"{profile.get('weight') or '—'} kg")
                c4.metric("Vet Visits", len(profile.get('vet_visits', [])))
                if profile.get('notes'):
                    st.caption(f"📝 {profile['notes']}")

            btn1, btn2, _ = st.columns([1, 1, 4])
            with btn1:
                if st.button("✏️ Edit Profile", key=f"open_edit_{cat}"):
                    st.session_state[f'edit_basic_{cat}'] = not st.session_state.get(f'edit_basic_{cat}', False)
                    st.rerun()
            with btn2:
                if st.button("🏥 Add Visit", key=f"open_visit_{cat}"):
                    st.session_state[f'edit_{cat}'] = not st.session_state.get(f'edit_{cat}', False)
                    st.rerun()

        # ── Edit basic profile ──
        if st.session_state.get(f'edit_basic_{cat}', False):
            with st.expander(f"✏️ Edit {cat}'s Basic Info", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    # FIX: use unique widget keys and read back from st.session_state on save
                    st.text_input("Age",         value=profile.get('age',   ''), key=f"edit_age_{cat}")
                    st.text_input("Breed",       value=profile.get('breed', ''), key=f"edit_breed_{cat}")
                with col2:
                    st.text_input("Weight (kg)", value=profile.get('weight', ''), key=f"edit_weight_{cat}")
                    st.text_area("Notes",        value=profile.get('notes',  ''), key=f"edit_notes_{cat}", height=80)

                s1, s2 = st.columns([1, 5])
                with s1:
                    if st.button("💾 Save", key=f"save_basic_{cat}", type="primary"):
                        # FIX: read directly from session_state widget keys — not local vars
                        st.session_state.cat_profiles[cat].update({
                            'age':    st.session_state[f"edit_age_{cat}"],
                            'breed':  st.session_state[f"edit_breed_{cat}"],
                            'weight': st.session_state[f"edit_weight_{cat}"],
                            'notes':  st.session_state[f"edit_notes_{cat}"]
                        })
                        save_data()
                        st.success("✅ Profile saved!")
                        st.session_state[f'edit_basic_{cat}'] = False
                        st.rerun()
                with s2:
                    if st.button("❌ Cancel", key=f"cancel_basic_{cat}"):
                        st.session_state[f'edit_basic_{cat}'] = False
                        st.rerun()

        # ── Vet visits panel ──
        if st.session_state.get(f'edit_{cat}', False):
            with st.expander(f"🏥 Vet Visits — {cat}", expanded=True):
                vet_visits = profile.get('vet_visits', [])

                if vet_visits:
                    st.markdown("#### Recorded Visits")
                    vet_df       = pd.DataFrame(vet_visits)
                    display_cols = [c for c in ['date','doctor','reason','medication'] if c in vet_df.columns]
                    st.dataframe(vet_df[display_cols], use_container_width=True, hide_index=True)

                    visit_options = [f"{v['date']} — {v['reason']}" for v in vet_visits]
                    to_delete = st.selectbox("Select visit to delete", [""]+visit_options, key=f"del_vis_{cat}")
                    if to_delete and st.button("🗑️ Delete Selected Visit", key=f"del_vis_btn_{cat}", type="secondary"):
                        idx = visit_options.index(to_delete)
                        vet_visits.pop(idx)
                        st.session_state.cat_profiles[cat]['vet_visits'] = vet_visits
                        save_data()
                        st.success("Visit deleted!")
                        st.rerun()

                st.markdown("---")
                st.markdown("#### ➕ Add New Visit")
                col1, col2 = st.columns(2)
                with col1:
                    st.date_input("Visit Date",  key=f"v_date_{cat}")
                    st.text_input("Doctor Name", key=f"v_doc_{cat}",    placeholder="Dr. Smith")
                with col2:
                    st.text_input("Reason",      key=f"v_reason_{cat}", placeholder="Annual checkup")
                    st.text_input("Medication",  key=f"v_med_{cat}",    placeholder="None")

                a1, a2 = st.columns([1, 5])
                with a1:
                    if st.button("💾 Save Visit", key=f"save_visit_{cat}", type="primary"):
                        # FIX: read from widget keys
                        st.session_state.cat_profiles[cat]['vet_visits'].append({
                            'date':       str(st.session_state[f"v_date_{cat}"]),
                            'doctor':     st.session_state[f"v_doc_{cat}"],
                            'reason':     st.session_state[f"v_reason_{cat}"],
                            'medication': st.session_state[f"v_med_{cat}"]
                        })
                        save_data()
                        st.success("✅ Visit added!")
                        st.rerun()
                with a2:
                    if st.button("❌ Close", key=f"close_visit_{cat}"):
                        st.session_state[f'edit_{cat}'] = False
                        st.rerun()

        st.markdown("")


# ─────────────────────────────────────────────
# Page: Add Health Entry
# ─────────────────────────────────────────────
def add_health_entry_page():
    st.header("📝 Add Health Entry")

    if st.session_state.editing_health_entry and st.session_state.edit_entry_data:
        st.subheader("✏️ Edit Health Entry")

        edit_cat         = st.session_state.edit_entry_cat
        edit_timestamp   = st.session_state.edit_entry_data.get('timestamp', '')
        edit_entry_index = st.session_state.edit_entry_data.get('index', 0)

        original_entry = None
        if edit_cat in st.session_state.health_data:
            if edit_timestamp in st.session_state.health_data[edit_cat]:
                entries_at_ts = st.session_state.health_data[edit_cat][edit_timestamp]
                if edit_entry_index < len(entries_at_ts):
                    original_entry = entries_at_ts[edit_entry_index]

        if original_entry:
            with st.form("edit_health_entry_form"):
                col1, col2 = st.columns(2)
                with col1:
                    water_drinks     = st.number_input("Water Drinks",     min_value=0, max_value=20, value=original_entry.get('water_drinks', 0))
                    food_eats        = st.number_input("Food Eats",        min_value=0, max_value=10, value=original_entry.get('food_eats', 0))
                    litter_box_times = st.number_input("Litter Box Times", min_value=0, max_value=15, value=original_entry.get('litter_box_times', 0))
                with col2:
                    mood_opts = ["Very Poor","Poor","Normal","Good","Excellent"]
                    mood = st.selectbox("Mood", mood_opts, index=mood_opts.index(original_entry.get('mood','Normal')))
                    app_opts = ["Poor","Fair","Good","Excellent"]
                    general_appearance = st.selectbox("General Appearance", app_opts, index=app_opts.index(original_entry.get('general_appearance','Good')))
                    litter_quality = st.text_area("Litter Quality Issues", value='\n'.join(original_entry.get('litter_quality', [])))

                st.markdown("---")
                st.subheader("💊 Medication (Optional)")
                with st.expander("Edit Medication"):
                    medication_name      = st.text_input("Medication Name", value=original_entry.get('medication_name',''))
                    medication_dosage    = st.text_input("Dosage",          value=original_entry.get('medication_dosage',''))
                    medication_frequency = st.text_input("Frequency",       value=original_entry.get('medication_frequency',''))
                    medication_reason    = st.text_input("Reason",          value=original_entry.get('medication_reason',''))
                    col_s, col_e = st.columns(2)
                    with col_s:
                        ms = original_entry.get('medication_start_date','')
                        medication_start = st.date_input("Start Date", value=date.fromisoformat(ms) if ms else date.today(), key="edit_med_start")
                    with col_e:
                        me = original_entry.get('medication_end_date','')
                        medication_end = st.date_input("End Date", value=date.fromisoformat(me) if me else date.today(), key="edit_med_end")

                st.markdown("---")
                notes = st.text_area("Additional Notes", height=100, value=original_entry.get('notes',''))

                st.markdown("---")
                st.subheader("🪥 Grooming Tasks")
                grooming_tasks = {
                    t: st.checkbox(t, value=original_entry.get('grooming_tasks',{}).get(t, False))
                    for t in ["Brush Fur","Trim Nails","Clean Ears","Clean Eyes","Clean Chin","Dental Care"]
                }

                if st.form_submit_button("💾 Update Health Entry"):
                    entry_data = {
                        'water_drinks': water_drinks, 'food_eats': food_eats,
                        'litter_box_times': litter_box_times, 'mood': mood,
                        'general_appearance': general_appearance,
                        'litter_quality': litter_quality.split('\n') if litter_quality else [],
                        'notes': notes,
                        'grooming_tasks': {t: c for t, c in grooming_tasks.items() if c}
                    }
                    if medication_name:
                        entry_data.update({
                            'medication_name': medication_name, 'medication_dosage': medication_dosage,
                            'medication_frequency': medication_frequency, 'medication_reason': medication_reason,
                            'medication_start_date': str(medication_start), 'medication_end_date': str(medication_end)
                        })
                    update_health_entry(edit_cat, edit_timestamp, edit_entry_index, entry_data)
                    st.success(f"✅ Updated entry for {edit_cat}!")
                    st.session_state.editing_health_entry = False
                    st.session_state.edit_entry_data = {}
                    st.rerun()

        if st.button("❌ Cancel Edit"):
            st.session_state.editing_health_entry = False
            st.session_state.edit_entry_data = {}
            st.rerun()
        return

    st.subheader("🆕 Add New Health Entry")
    selected_cat = st.selectbox("Select Cat", st.session_state.cats, key="cat_selector")

    if st.session_state.health_form_cat != selected_cat:
        for key in list(st.session_state.keys()):
            if key.startswith("form_"):
                del st.session_state[key]
        st.session_state.health_form_cat = selected_cat

    entry_mode = st.radio("Entry Mode", ["🚀 Quick Entry", "📋 Detailed Entry"])

    if entry_mode == "🚀 Quick Entry":
        st.markdown("### Quick Actions")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💧 Water Drank"):
                add_health_entry(selected_cat, {'water_drinks':1,'food_eats':0,'litter_box_times':0,'mood':'Good','general_appearance':'Good','litter_quality':[],'notes':'Quick entry: Water drank','grooming_tasks':{}})
                st.success(f"✅ Water entry added for {selected_cat}!"); st.rerun()
        with c2:
            if st.button("🍽️ Food Eaten"):
                add_health_entry(selected_cat, {'water_drinks':0,'food_eats':1,'litter_box_times':0,'mood':'Good','general_appearance':'Good','litter_quality':[],'notes':'Quick entry: Food eaten','grooming_tasks':{}})
                st.success(f"✅ Food entry added for {selected_cat}!"); st.rerun()
        with c3:
            if st.button("🚽 Litter Box Used"):
                add_health_entry(selected_cat, {'water_drinks':0,'food_eats':0,'litter_box_times':1,'mood':'Good','general_appearance':'Good','litter_quality':[],'notes':'Quick entry: Litter box used','grooming_tasks':{}})
                st.success(f"✅ Litter entry added for {selected_cat}!"); st.rerun()
        st.markdown("---")

    st.markdown("### 📋 Detailed Health Entry")
    with st.form("health_entry_form"):
        c1, c2 = st.columns(2)
        with c1:
            water_drinks     = st.number_input("💧 Water Drinks",     min_value=0, max_value=20, value=0, key="form_water")
            food_eats        = st.number_input("🍽️ Food Eats",        min_value=0, max_value=10, value=0, key="form_food")
            litter_box_times = st.number_input("🚽 Litter Box Times", min_value=0, max_value=15, value=0, key="form_litter")
        with c2:
            mood               = st.selectbox("😊 Mood",               ["Very Poor","Poor","Normal","Good","Excellent"], key="form_mood")
            general_appearance = st.selectbox("✨ General Appearance", ["Poor","Fair","Good","Excellent"],               key="form_appearance")
            litter_quality     = st.text_area("🚨 Litter Quality Issues", placeholder="e.g., Blood, diarrhea, abnormal color...", key="form_litter_quality")

        st.markdown("---")
        st.subheader("💊 Medication (Optional)")
        with st.expander("Add Medication"):
            medication_name      = st.text_input("Medication Name", placeholder="e.g., Amoxicillin", key="form_med_name")
            medication_dosage    = st.text_input("Dosage",          placeholder="e.g., 50mg",         key="form_med_dosage")
            medication_frequency = st.text_input("Frequency",       placeholder="e.g., Twice daily",  key="form_med_freq")
            medication_reason    = st.text_input("Reason",          placeholder="e.g., Antibiotic",    key="form_med_reason")
            cs1, ce1 = st.columns(2)
            with cs1: medication_start = st.date_input("Start Date", value=date.today(),                   key="form_med_start")
            with ce1: medication_end   = st.date_input("End Date",   value=date.today()+timedelta(days=7), key="form_med_end")

        st.markdown("---")
        notes = st.text_area("📝 Additional Notes", height=100, placeholder="Any other observations...", key="form_notes")

        st.markdown("---")
        st.subheader("🪥 Grooming Tasks")
        st.caption("Check only if performed today.")
        g1, g2, g3 = st.columns(3)
        with g1: g_brush = st.checkbox("Brush Fur",  key="form_g_brush"); g_nails = st.checkbox("Trim Nails", key="form_g_nails")
        with g2: g_ears  = st.checkbox("Clean Ears", key="form_g_ears");  g_eyes  = st.checkbox("Clean Eyes", key="form_g_eyes")
        with g3: g_chin  = st.checkbox("Clean Chin", key="form_g_chin");  g_dental= st.checkbox("Dental Care",key="form_g_dental")
        grooming_tasks = {"Brush Fur":g_brush,"Trim Nails":g_nails,"Clean Ears":g_ears,"Clean Eyes":g_eyes,"Clean Chin":g_chin,"Dental Care":g_dental}

        if st.form_submit_button("💾 Save Health Entry", type="primary", use_container_width=True):
            entry_data = {
                'water_drinks': water_drinks, 'food_eats': food_eats,
                'litter_box_times': litter_box_times, 'mood': mood,
                'general_appearance': general_appearance,
                'litter_quality': litter_quality.split('\n') if litter_quality else [],
                'notes': notes,
                'grooming_tasks': {t: c for t, c in grooming_tasks.items() if c}
            }
            if medication_name:
                entry_data.update({
                    'medication_name': medication_name, 'medication_dosage': medication_dosage,
                    'medication_frequency': medication_frequency, 'medication_reason': medication_reason,
                    'medication_start_date': str(medication_start), 'medication_end_date': str(medication_end)
                })
            add_health_entry(selected_cat, entry_data)
            st.success(f"✅ Health entry saved for {selected_cat}!")
            st.rerun()


# ─────────────────────────────────────────────
# Page: View Health Data
# ─────────────────────────────────────────────
def view_health_data_page():
    st.header("📊 View Health Data")

    c1, c2 = st.columns(2)
    with c1: selected_cat = st.selectbox("Select Cat", st.session_state.cats)
    with c2:
        date_range = st.date_input("Date Range", value=(date.today()-timedelta(days=30), date.today()), max_value=date.today())

    start_date, end_date = (date_range[0], date_range[1]) if len(date_range)==2 else (date.today(), date.today())

    entries = get_health_entries(selected_cat, start_date, end_date)
    if not entries:
        st.info(f"No health data found for {selected_cat} in the selected date range.")
        return

    df    = pd.DataFrame(entries)
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df['time'] = pd.to_datetime(df['timestamp']).dt.time
    df    = df.sort_values('timestamp', ascending=False)
    daily = get_daily_aggregated(selected_cat, start_date, end_date)

    st.subheader(f"📈 {selected_cat}'s Combined Daily Totals")
    if daily:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Avg Water/Day",  f"{sum(d['water_drinks'] for d in daily.values())/len(daily):.1f}")
        c2.metric("Avg Food/Day",   f"{sum(d['food_eats'] for d in daily.values())/len(daily):.1f}")
        c3.metric("Avg Litter/Day", f"{sum(d['litter_box_times'] for d in daily.values())/len(daily):.1f}")
        c4.metric("Days Tracked",   len(daily))

    st.subheader("📋 Health Entries by Day")
    df['date_only'] = df['timestamp'].str.split('T').str[0]
    for date_str, date_group in df.groupby('date_only'):
        d_date = date.fromisoformat(date_str)
        dt = daily.get(d_date, {})
        parts = []
        if dt.get('water_drinks'):     parts.append(f"💧{dt['water_drinks']}")
        if dt.get('food_eats'):        parts.append(f"🍽️{dt['food_eats']}")
        if dt.get('litter_box_times'): parts.append(f"🚽{dt['litter_box_times']}")
        total_label = f" — Day total: {' '.join(parts)}" if parts else ""

        with st.expander(f"📅 {date_str} ({len(date_group)} entries){total_label}"):
            for idx, entry in date_group.iterrows():
                st.markdown(f"**⏰ {entry['time']}**")
                ca, cb = st.columns([3,1])
                with ca:
                    st.write(f"Water: {entry.get('water_drinks','N/A')} · Food: {entry.get('food_eats','N/A')} · Litter: {entry.get('litter_box_times','N/A')}")
                    st.write(f"Mood: {entry.get('mood','N/A')} · Appearance: {entry.get('general_appearance','N/A')}")
                    if entry.get('litter_quality'):
                        q = '\n'.join(entry['litter_quality'])
                        if q.strip(): st.write(f"⚠️ Litter issues: {q}")
                    if entry.get('notes'): st.write(f"📝 {entry['notes']}")
                    if entry.get('medication_name'):
                        ms = f"💊 {entry['medication_name']} ({entry.get('medication_dosage','N/A')})"
                        if entry.get('medication_start_date') and entry.get('medication_end_date'):
                            ms += f" · {entry['medication_start_date']} → {entry['medication_end_date']}"
                        st.write(ms)
                    grooming_done = [t for t,done in entry.get('grooming_tasks',{}).items() if done]
                    if grooming_done: st.write(f"🪥 Grooming: {', '.join(grooming_done)}")
                with cb:
                    if st.button("✏️ Edit", key=f"edit_entry_{idx}"):
                        st.session_state.editing_health_entry = True
                        st.session_state.edit_entry_data = {'timestamp': entry['timestamp'], 'index': idx}
                        st.session_state.edit_entry_cat  = selected_cat
                        st.rerun()
                    if st.button("🗑️ Del", key=f"delete_entry_{idx}"):
                        delete_health_entry(selected_cat, entry['timestamp'], idx)
                        st.success("Entry deleted!"); st.rerun()
                st.markdown("---")

    st.subheader("📊 Health Trends")
    if daily and len(daily) > 1:
        sorted_dates = sorted(daily.keys())
        fig = make_subplots(rows=2, cols=2, subplot_titles=('Water Intake','Food Intake','Litter Box Usage','Entries per Day'))
        fig.add_trace(go.Bar(x=sorted_dates, y=[daily[d]['water_drinks']     for d in sorted_dates], name='Water',   marker_color='#4fc3f7'), row=1, col=1)
        fig.add_trace(go.Bar(x=sorted_dates, y=[daily[d]['food_eats']        for d in sorted_dates], name='Food',    marker_color='#81c784'), row=1, col=2)
        fig.add_trace(go.Bar(x=sorted_dates, y=[daily[d]['litter_box_times'] for d in sorted_dates], name='Litter',  marker_color='#ffb74d'), row=2, col=1)
        fig.add_trace(go.Bar(x=sorted_dates, y=[daily[d]['entry_count']      for d in sorted_dates], name='Entries', marker_color='#ce93d8'), row=2, col=2)
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# Page: Task Management
# ─────────────────────────────────────────────
def task_management_page():
    st.header("📋 Task Management")

    for freq, freq_name in [('daily','📅 Daily'),('weekly','🗓️ Weekly'),('monthly','📆 Monthly')]:
        st.markdown(f"### {freq_name}")
        if not st.session_state.tasks[freq]:
            st.info(f"No {freq} tasks.")
            continue
        today           = str(date.today())
        completed_today = [log['task'] for log in st.session_state.task_logs.get(today, [])]
        for task in st.session_state.tasks[freq]:
            already_done = task in completed_today
            checked = st.checkbox(task, value=already_done, key=f"task_{freq}_{task}")
            if checked and not already_done:
                add_task_completion(task)
                st.rerun()
        st.markdown("")

    st.markdown("---")
    st.subheader("📅 Monthly Task Calendar")
    st.caption("✅ = completed  |  🔔 = start of month  |  📍 = today")
    today = date.today()
    c1, c2 = st.columns([1,3])
    with c1:
        cal_month = st.selectbox("Month", list(range(1,13)), index=today.month-1, format_func=lambda m: calendar.month_name[m])
        cal_year  = st.number_input("Year", min_value=2024, max_value=2030, value=today.year, step=1)
    with c2:
        monthly_task_calendar(int(cal_year), int(cal_month))

    st.markdown("---")
    st.subheader("📋 Task Completion History")
    c1, c2 = st.columns(2)
    with c1: history_start = st.date_input("Start Date", date.today()-timedelta(days=7))
    with c2: history_end   = st.date_input("End Date",   date.today())
    completions = get_task_completions(history_start, history_end)
    if not completions:
        st.info("No task completions found in the selected date range.")
        return
    all_comp = []
    for date_str, day_logs in completions.items():
        for log in day_logs:
            all_comp.append({'date': date_str, 'task': log['task'],
                             'cat': log.get('cat',''), 'completed_at': log['completed_at']})
    df = pd.DataFrame(all_comp)
    df['date'] = pd.to_datetime(df['date'])
    st.dataframe(df.sort_values('date'), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# NEW PAGE: Cat Health Guide
# ─────────────────────────────────────────────
def cat_health_guide_page():
    st.header("🏥 Cat Health Guide")
    st.write("Common diseases, warning signs, and prevention tips for Haku, Kuro, and Sonic.")

    # ── Disease data ──
    diseases = [
        {
            "name": "Urinary Tract Infection (UTI) / FLUTD",
            "icon": "🚽",
            "who":  "Common in all cats, especially males",
            "signs": [
                "Straining or crying in the litter box",
                "Frequent trips to litter box but little or no urine",
                "Blood in urine (pink or red tint)",
                "Licking genitals excessively",
                "Urinating outside the litter box"
            ],
            "prevention": [
                "Always provide fresh water — a fountain encourages drinking",
                "Wet food keeps hydration up and dilutes urine",
                "Keep litter box very clean to reduce stress",
                "Reduce stress (a major trigger for FLUTD)"
            ],
            "urgency": "🔴 Emergency if cat cannot urinate at all — can be fatal within 24-48 hrs"
        },
        {
            "name": "Upper Respiratory Infection (Cat Cold / Herpesvirus / Calicivirus)",
            "icon": "🤧",
            "who":  "Very common, especially in cats that had early shelter exposure",
            "signs": [
                "Sneezing frequently",
                "Runny nose or eyes (clear or colored discharge)",
                "Loss of appetite or smell",
                "Lethargy or hiding",
                "Mouth ulcers (calicivirus)"
            ],
            "prevention": [
                "Keep vaccinations up to date (FVRCP covers herpesvirus and calicivirus)",
                "Reduce stress — stress triggers herpesvirus flare-ups",
                "Good air ventilation and clean environment",
                "Isolate sick cats from healthy ones"
            ],
            "urgency": "🟠 See vet if not eating for more than 24 hrs or discharge turns yellow/green"
        },
        {
            "name": "Intestinal Parasites (Worms: roundworms, tapeworms, giardia)",
            "icon": "🐛",
            "who":  "Any cat, especially younger ones or those that hunt",
            "signs": [
                "Visible worm segments in stool or around the tail area",
                "Bloated or pot-bellied appearance",
                "Weight loss despite eating",
                "Scooting on the floor",
                "Vomiting or diarrhea"
            ],
            "prevention": [
                "Regular deworming (ask your vet for a schedule)",
                "Monthly flea prevention — fleas carry tapeworms",
                "Clean litter box daily",
                "Wash hands after handling litter"
            ],
            "urgency": "🟡 Not an emergency but needs treatment — worms will persist and worsen without medication"
        },
        {
            "name": "Dental Disease (Gingivitis / Periodontal Disease)",
            "icon": "🦷",
            "who":  "Affects over 70% of cats by age 3",
            "signs": [
                "Bad breath (worse than normal cat breath)",
                "Drooling more than usual",
                "Difficulty chewing or dropping food",
                "Pawing at the mouth",
                "Red, swollen, or bleeding gums"
            ],
            "prevention": [
                "Brush teeth — even a few times a week makes a big difference",
                "Dental treats and water additives help",
                "Annual dental check at the vet",
                "Dental diet food for cats prone to buildup"
            ],
            "urgency": "🟡 Not immediately life-threatening but untreated dental disease damages kidneys, heart, and liver over time"
        },
        {
            "name": "Ringworm (Fungal Skin Infection)",
            "icon": "🔵",
            "who":  "Any cat — highly contagious to other cats and humans",
            "signs": [
                "Circular patches of hair loss",
                "Scaly, crusty, or red skin in the bald patches",
                "Itching (not always present)",
                "Brittle or broken hairs around the patch"
            ],
            "prevention": [
                "Keep new cats isolated and checked before mixing with others",
                "Wash bedding and grooming tools regularly",
                "Treat affected cats promptly — it spreads fast"
            ],
            "urgency": "🟠 Not life-threatening but spreads to humans and other pets — treat quickly"
        },
        {
            "name": "Feline Panleukopenia (Cat Parvovirus)",
            "icon": "⚠️",
            "who":  "Unvaccinated cats, kittens most at risk",
            "signs": [
                "Sudden high fever",
                "Severe vomiting and diarrhea (often bloody)",
                "Extreme lethargy — cat barely moves",
                "Loss of appetite",
                "Hiding and appearing to be in pain"
            ],
            "prevention": [
                "FVRCP vaccination — highly effective protection",
                "Keep unvaccinated cats away from unknown cats",
                "The virus survives on surfaces for months — disinfect thoroughly"
            ],
            "urgency": "🔴 Life-threatening emergency — requires immediate vet care, mortality very high without treatment"
        },
        {
            "name": "Obesity & Related Problems",
            "icon": "⚖️",
            "who":  "Indoor cats, neutered cats, cats fed freely",
            "signs": [
                "Cannot feel ribs easily when touching sides",
                "Belly hangs down or swings when walking",
                "Reluctant to play or move",
                "Difficulty grooming the lower back",
                "Heavy breathing after light activity"
            ],
            "prevention": [
                "Measure food portions — do not free-feed",
                "Use puzzle feeders to slow eating and add activity",
                "Two 15-minute play sessions per day",
                "Vet check for healthy weight range specific to their breed and size",
                "Wet food has fewer calories per gram than dry"
            ],
            "urgency": "🟡 Slow damage — leads to diabetes, joint problems, heart disease, and shorter lifespan"
        },
        {
            "name": "Ear Mites",
            "icon": "👂",
            "who":  "Very common, especially in cats that go outside or contact other animals",
            "signs": [
                "Constant scratching at ears or shaking the head",
                "Dark, crumbly discharge in the ear (looks like coffee grounds)",
                "Odor from the ears",
                "Redness or inflammation inside the ear flap",
                "Scabs or sores around the ear from scratching"
            ],
            "prevention": [
                "Regular ear checks — clean monthly as part of grooming",
                "Use vet-recommended ear mite prevention",
                "Treat all cats in the household if one has mites"
            ],
            "urgency": "🟠 Not dangerous but extremely uncomfortable — treat promptly to prevent secondary infection"
        },
        {
            "name": "Hyperthyroidism",
            "icon": "🔬",
            "who":  "Middle-aged to older cats (8+ years)",
            "signs": [
                "Weight loss despite eating a lot or more than usual",
                "Increased thirst and urination",
                "Hyperactivity or restlessness",
                "Vomiting or diarrhea",
                "Unkempt, greasy coat"
            ],
            "prevention": [
                "No guaranteed prevention — annual vet checks catch it early",
                "Some evidence that BPA-lined canned food may contribute — use BPA-free where possible",
                "Early detection makes treatment much easier"
            ],
            "urgency": "🟠 Not an emergency but progresses — heart and kidney damage if untreated"
        },
        {
            "name": "Fleas",
            "icon": "🦟",
            "who":  "Any cat, even indoor-only cats",
            "signs": [
                "Scratching, biting, or over-grooming especially around neck and tail base",
                "Small black dots (flea dirt) in the fur — looks like pepper",
                "Red, irritated skin or small bumps",
                "Hair loss in patches from over-scratching",
                "Restlessness or visible tiny jumping insects"
            ],
            "prevention": [
                "Monthly flea prevention product (ask vet for best option)",
                "Vacuum regularly, especially carpets and cat beds",
                "Wash bedding on hot cycle monthly",
                "Treat all pets in the home at the same time",
                "Fleas can survive months in the environment without a host"
            ],
            "urgency": "🟡 Not immediately dangerous but causes anemia in kittens and carries tapeworms — treat all cats and the environment"
        }
    ]

    # ── Filter controls ──
    urgency_filter = st.selectbox(
        "Filter by urgency",
        ["All", "🔴 Emergency", "🟠 See vet soon", "🟡 Monitor / Treat"],
        index=0
    )

    search = st.text_input("🔍 Search by symptom or disease name", placeholder="e.g., vomiting, ear, weight loss")

    st.markdown("---")

    def urgency_level(urgency_str: str) -> str:
        if "🔴" in urgency_str: return "🔴 Emergency"
        if "🟠" in urgency_str: return "🟠 See vet soon"
        return "🟡 Monitor / Treat"

    filtered = diseases
    if urgency_filter != "All":
        filtered = [d for d in filtered if urgency_level(d["urgency"]) == urgency_filter]
    if search:
        search_lower = search.lower()
        filtered = [
            d for d in filtered
            if search_lower in d["name"].lower()
            or any(search_lower in s.lower() for s in d["signs"])
            or any(search_lower in p.lower() for p in d["prevention"])
        ]

    if not filtered:
        st.info("No diseases match your search. Try different keywords.")
        return

    st.write(f"Showing **{len(filtered)}** of {len(diseases)} conditions")
    st.markdown("")

    for disease in filtered:
        with st.expander(f"{disease['icon']} {disease['name']}", expanded=False):
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**👥 Who is at risk:**")
                st.write(disease["who"])

                st.markdown("**🚨 Warning signs:**")
                for sign in disease["signs"]:
                    st.write(f"- {sign}")

            with c2:
                st.markdown("**✅ Prevention:**")
                for tip in disease["prevention"]:
                    st.write(f"- {tip}")

            urgency_str = disease["urgency"]
            if "🔴" in urgency_str:
                st.error(urgency_str)
            elif "🟠" in urgency_str:
                st.warning(urgency_str)
            else:
                st.info(urgency_str)

    st.markdown("---")
    # ── Quick symptom checker ──
    st.subheader("🔍 Quick Symptom Checker")
    st.caption("Tick everything you're seeing right now — we'll show what it could be.")

    symptom_map = {
        "Not eating / loss of appetite":    ["Upper Respiratory Infection","Dental Disease","Feline Panleukopenia","Hyperthyroidism","Urinary Tract Infection"],
        "Vomiting":                          ["Intestinal Parasites","Feline Panleukopenia","Hyperthyroidism","Dental Disease"],
        "Diarrhea":                          ["Intestinal Parasites","Feline Panleukopenia","Hyperthyroidism"],
        "Straining to urinate / no urine":   ["Urinary Tract Infection (UTI) / FLUTD"],
        "Blood in urine":                    ["Urinary Tract Infection (UTI) / FLUTD"],
        "Sneezing / runny nose or eyes":     ["Upper Respiratory Infection"],
        "Hair loss / bald patches":          ["Ringworm","Fleas"],
        "Scratching ears / head shaking":    ["Ear Mites"],
        "Weight loss despite eating":        ["Intestinal Parasites","Hyperthyroidism"],
        "Weight gain / belly hanging":       ["Obesity & Related Problems"],
        "Lethargy / hiding":                 ["Upper Respiratory Infection","Feline Panleukopenia","Urinary Tract Infection"],
        "Bad breath / drooling":             ["Dental Disease"],
        "Scratching body / restless":        ["Fleas","Ringworm"],
        "Dark ear discharge":                ["Ear Mites"],
        "Scooting on floor":                 ["Intestinal Parasites"],
        "Pot belly / bloated":               ["Intestinal Parasites"],
        "Increased thirst and urination":    ["Hyperthyroidism"],
    }

    selected_symptoms = []
    cols = st.columns(2)
    symptom_list = list(symptom_map.keys())
    for i, symptom in enumerate(symptom_list):
        with cols[i % 2]:
            if st.checkbox(symptom, key=f"symptom_{i}"):
                selected_symptoms.append(symptom)

    if selected_symptoms:
        st.markdown("---")
        st.markdown("**Possible conditions based on selected symptoms:**")

        disease_scores = {}
        for symptom in selected_symptoms:
            for disease_name in symptom_map.get(symptom, []):
                disease_scores[disease_name] = disease_scores.get(disease_name, 0) + 1

        sorted_diseases = sorted(disease_scores.items(), key=lambda x: x[1], reverse=True)

        for disease_name, score in sorted_diseases:
            match_pct = int((score / len(selected_symptoms)) * 100)
            matched_disease = next((d for d in diseases if d["name"].startswith(disease_name.split("(")[0].strip())), None)
            if matched_disease:
                urgency = matched_disease["urgency"]
                if "🔴" in urgency:
                    st.error(f"**{matched_disease['icon']} {disease_name}** — {score} symptom(s) match · {urgency}")
                elif "🟠" in urgency:
                    st.warning(f"**{matched_disease['icon']} {disease_name}** — {score} symptom(s) match · {urgency}")
                else:
                    st.info(f"**{matched_disease['icon']} {disease_name}** — {score} symptom(s) match · {urgency}")
            else:
                st.write(f"- **{disease_name}** — {score} symptom(s) match")

        st.markdown("")
        st.caption("This is a reference guide only. Always consult your vet for a proper diagnosis.")


# ─────────────────────────────────────────────
# Page: Dashboard
# ─────────────────────────────────────────────
def dashboard_page():
    st.header("🎯 Dashboard")

    active_meds = get_active_medications_today()
    if active_meds:
        st.subheader("💊 Active Medications Today")
        for med in active_meds:
            dl = med['days_left']
            if dl == 0:   urgency, note = "🔴", "**Last dose today!**"
            elif dl <= 2: urgency, note = "🟠", f"**{dl} day(s) left**"
            else:         urgency, note = "🟢", f"{dl} days left"
            st.info(f"{urgency} **{med['cat']}** — **{med['name']}**"
                    + (f" ({med['dosage']})" if med['dosage'] else "")
                    + (f" · {med['frequency']}" if med['frequency'] else "")
                    + f" · Until {med['end_date']} · {note}")
        st.markdown("---")

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        total_entries = sum(len(dates) for cat_data in st.session_state.health_data.values() for dates in cat_data.values())
        st.metric("Total Entries", total_entries)
    with c2:
        today_str   = str(date.today())
        today_tasks = [log['task'] for log in st.session_state.task_logs.get(today_str, [])]
        st.metric("Today's Tasks", f"{len(today_tasks)}/{len(st.session_state.tasks.get('daily',[]))}")
    with c3:
        st.metric("Vet Visits", sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))
    with c4:
        active = sum(1 for cat in st.session_state.cats if cat in st.session_state.health_data and st.session_state.health_data[cat])
        st.metric("Active Cats", f"{active}/{len(st.session_state.cats)}")

    st.markdown("---")
    st.subheader("📊 Weekly Comparison — All Cats")
    today    = date.today()
    week_ago = today - timedelta(days=7)
    comp_data = []
    for cat in st.session_state.cats:
        daily = get_daily_aggregated(cat, week_ago, today)
        if daily:
            comp_data.append({
                'Cat':            cat,
                'Avg Water/Day':  round(sum(d['water_drinks']     for d in daily.values())/len(daily),1),
                'Avg Food/Day':   round(sum(d['food_eats']        for d in daily.values())/len(daily),1),
                'Avg Litter/Day': round(sum(d['litter_box_times'] for d in daily.values())/len(daily),1),
                'Days Tracked':   len(daily)
            })

    if comp_data:
        comp_df = pd.DataFrame(comp_data)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Avg Water',  x=comp_df['Cat'], y=comp_df['Avg Water/Day'],  marker_color='#4fc3f7'))
        fig.add_trace(go.Bar(name='Avg Food',   x=comp_df['Cat'], y=comp_df['Avg Food/Day'],   marker_color='#81c784'))
        fig.add_trace(go.Bar(name='Avg Litter', x=comp_df['Cat'], y=comp_df['Avg Litter/Day'], marker_color='#ffb74d'))
        fig.update_layout(barmode='group', height=300, margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet for any cat in the past 7 days.")

    st.markdown("---")
    st.subheader("📄 Export Vet Report")
    c1, c2 = st.columns(2)
    with c1: pdf_cat = st.selectbox("Report for", ["All Cats"] + st.session_state.cats)
    with c2:
        st.write("")
        st.write("")
        if REPORTLAB_AVAILABLE:
            cat_arg   = None if pdf_cat == "All Cats" else pdf_cat
            pdf_bytes = generate_pdf_report(cat_arg)
            st.download_button("📥 Download PDF Report",
                data=pdf_bytes, file_name=f"cat_report_{date.today()}.pdf",
                mime="application/pdf", type="primary", use_container_width=True)
        else:
            st.warning("PDF export unavailable. Run: pip install reportlab")

    st.markdown("---")
    st.subheader("🐱 Individual Cat Summaries")
    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            st.markdown(generate_cat_summary(cat))


# ─────────────────────────────────────────────
# Page: Data Management
# ─────────────────────────────────────────────
def data_management_page():
    st.header("⚙️ Data Management")
    st.warning("⚠️ **Caution:** Actions on this page can permanently delete your data!")

    st.markdown("---")
    st.subheader("📥 Export Data")
    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("📥 Export Health Data", use_container_width=True):
            st.download_button("💾 Download Health Data",
                data=json.dumps(st.session_state.health_data, indent=2, default=str),
                file_name=f"health_data_{date.today()}.json", mime="application/json")
    with c2:
        if st.button("📥 Export Task Logs", use_container_width=True):
            st.download_button("💾 Download Task Logs",
                data=json.dumps(st.session_state.task_logs, indent=2, default=str),
                file_name=f"task_logs_{date.today()}.json", mime="application/json")
    with c3:
        if st.button("📥 Export Profiles", use_container_width=True):
            st.download_button("💾 Download Profiles",
                data=json.dumps(st.session_state.cat_profiles, indent=2, default=str),
                file_name=f"cat_profiles_{date.today()}.json", mime="application/json")

    st.markdown("---")
    st.subheader("🗑️ Delete Specific Data")
    c1,c2 = st.columns(2)
    with c1:
        st.write("**Delete Health Data for a Cat:**")
        cat_to_delete = st.selectbox("Select cat", [""]+st.session_state.cats, key="delete_cat_health")
        if cat_to_delete:
            if st.button(f"🗑️ Delete {cat_to_delete}'s Health Data", type="secondary"):
                if cat_to_delete in st.session_state.health_data:
                    del st.session_state.health_data[cat_to_delete]
                    save_data(); st.success(f"✅ Deleted health data for {cat_to_delete}"); st.rerun()
                else:
                    st.info(f"No health data found for {cat_to_delete}")
    with c2:
        st.write("**Delete Task Logs for a Date Range:**")
        del_start = st.date_input("Start Date", key="delete_task_start")
        del_end   = st.date_input("End Date",   key="delete_task_end")
        if st.button("🗑️ Delete Task Logs", type="secondary"):
            deleted, current = 0, del_start
            while current <= del_end:
                ds = str(current)
                if ds in st.session_state.task_logs:
                    del st.session_state.task_logs[ds]; deleted += 1
                current += timedelta(days=1)
            save_data(); st.success(f"✅ Deleted task logs for {deleted} days"); st.rerun()

    st.markdown("---")
    st.subheader("🚨 Delete All Data")
    st.error("**WARNING:** This permanently deletes ALL data!")
    confirm_delete = st.checkbox("I understand this action cannot be undone", key="confirm_delete_all")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Delete ALL Health Data", type="secondary", disabled=not confirm_delete):
            st.session_state.health_data  = {}
            st.session_state.last_entries = {cat: None for cat in st.session_state.cats}
            save_data(); st.success("✅ All health data deleted!"); st.rerun()
    with c2:
        if st.button("🗑️ Delete ALL Task Logs", type="secondary", disabled=not confirm_delete):
            st.session_state.task_logs = {}
            save_data(); st.success("✅ All task logs deleted!"); st.rerun()

    st.markdown("---")
    st.subheader("🔄 Complete Reset")
    st.error("**DANGER ZONE:** Resets EVERYTHING including profiles!")
    confirm_reset = st.checkbox("I want to completely reset the application", key="confirm_reset")
    if st.button("🔄 RESET EVERYTHING", type="secondary", disabled=not confirm_reset):
        st.session_state.health_data   = {}
        st.session_state.task_logs     = {}
        st.session_state.cat_profiles  = {
            cat: {'age':'','breed':'','weight':'','vet_visits':[],'notes':''}
            for cat in st.session_state.cats
        }
        st.session_state.last_entries  = {cat: None for cat in st.session_state.cats}
        st.session_state.data_loaded   = False
        for fname in ['health_data.json','task_logs.json','cat_profiles.json']:
            try:
                if os.path.exists(fname): os.remove(fname)
            except: pass
        st.success("✅ Application completely reset!")
        time.sleep(1); st.rerun()

    st.markdown("---")
    st.subheader("📊 Data Statistics")
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Total Health Entries", sum(len(d) for cat_data in st.session_state.health_data.values() for d in cat_data.values()))
    with c2: st.metric("Total Task Completions", sum(len(logs) for logs in st.session_state.task_logs.values()))
    with c3: st.metric("Total Vet Visits", sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))


# ─────────────────────────────────────────────
# Reminders
# ─────────────────────────────────────────────
def check_reminders():
    current_time = datetime.now()
    if (st.session_state.last_reminder is None or
            (current_time - st.session_state.last_reminder).days >= 1):

        missing = [cat for cat in st.session_state.cats
                   if st.session_state.last_entries[cat] is None or
                   (current_time - st.session_state.last_entries[cat]).days >= 1]
        if missing:
            st.warning(f"⚠️ No health entries today for: {', '.join(missing)}")

        today_str  = str(date.today())
        done       = [log['task'] for log in st.session_state.task_logs.get(today_str, [])]
        incomplete = [t for t in st.session_state.tasks['daily'] if t not in done]
        if incomplete:
            st.info(f"📝 Incomplete daily tasks: {', '.join(incomplete)}")

        st.session_state.last_reminder = current_time


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    if AUTH_ENABLED:
        if not check_authentication():
            login_page()
            return

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
        with c1: st.write("Comprehensive health and task management for your beloved cats")
        with c2:
            st.write(f"👤 {st.session_state.get('username','User')}")
            if st.button("🚪 Logout", key="logout_button"): logout()
    else:
        st.write("Comprehensive health and task management for your beloved cats")

    st.sidebar.title("🧭 Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        [
            "🎯 Dashboard",
            "🐱 Cat Profiles",
            "📝 Add Health Entry",
            "📊 View Health Data",
            "📋 Task Management",
            "🏥 Cat Health Guide",
            "⚙️ Data Management"
        ]
    )

    if AUTH_ENABLED: st.sidebar.success("🔐 Security: Enabled")
    else:            st.sidebar.warning("⚠️ Security: Disabled")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Need Help?")
    st.sidebar.markdown("[Ask the AI Assistant 🤖](https://thaura.ai/?chatId=eb1bb2bf-acf0-4f6c-99c4-660a0a4fd728)")

    check_reminders()

    if   page == "🎯 Dashboard":        dashboard_page()
    elif page == "🐱 Cat Profiles":     cat_profiles_page()
    elif page == "📝 Add Health Entry": add_health_entry_page()
    elif page == "📊 View Health Data": view_health_data_page()
    elif page == "📋 Task Management":  task_management_page()
    elif page == "🏥 Cat Health Guide": cat_health_guide_page()
    elif page == "⚙️ Data Management":  data_management_page()


if __name__ == "__main__":
    main()
