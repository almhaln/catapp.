```python
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
                'Let them out my room': 2, 'Pray for them': 1, 'Play with them': 2
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
            cat: {
                'age': '', 'breed': '', 'weight': '', 'vet_visits': [], 
                'notes': '', 'default_food': 'Pro Plan Adult', 'diet_plan': '3 meals daily'
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

    if 'vet_reminders' not in st.session_state:
        st.session_state.vet_reminders = {
            'annual_checkup': {'interval_days': 365, 'last_date': None},
            'vaccines': {'interval_days': 365, 'last_date': None},
            'deworming': {'interval_days': 90, 'last_date': None},
            'kuro_heart': {'interval_days': 120, 'last_date': None}
        }


# ─────────────────────────────────────────────
# Data persistence
# ─────────────────────────────────────────────
def save_data():
    try:
        health_data_str = json.dumps(st.session_state.health_data, default=str)
        task_logs_str   = json.dumps(st.session_state.task_logs,   default=str)
        profiles_str    = json.dumps(st.session_state.cat_profiles, default=str)
        vet_reminders_str = json.dumps(st.session_state.vet_reminders, default=str)

        if AUTH_ENABLED:
            health_data_str = encrypt_data(health_data_str)
            task_logs_str   = encrypt_data(task_logs_str)
            profiles_str    = encrypt_data(profiles_str)
            vet_reminders_str = encrypt_data(vet_reminders_str)

        with open('health_data.json',  'w') as f: f.write(health_data_str)
        with open('task_logs.json',    'w') as f: f.write(task_logs_str)
        with open('cat_profiles.json', 'w') as f: f.write(profiles_str)
        with open('vet_reminders.json', 'w') as f: f.write(vet_reminders_str)

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

        if os.path.exists('vet_reminders.json'):
            with open('vet_reminders.json', 'r') as f:
                data_str = f.read()
            if AUTH_ENABLED and data_str:
                try: data_str = decrypt_data(data_str)
                except: pass
            if data_str:
                st.session_state.vet_reminders = json.loads(data_str)

        st.session_state.data_loaded = True

    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.session_state.task_logs    = {}
        st.session_state.cat_profiles = {
            cat: {
                'age': '', 'breed': '', 'weight': '', 'vet_visits': [], 
                'notes': '', 'default_food': 'Pro Plan Adult', 'diet_plan': '3 meals daily'
            }
            for cat in st.session_state.cats
        }
        st.session_state.vet_reminders = {
            'annual_checkup': {'interval_days': 365, 'last_date': None},
            'vaccines': {'interval_days': 365, 'last_date': None},
            'deworming': {'interval_days': 90, 'last_date': None},
            'kuro_heart': {'interval_days': 120, 'last_date': None}
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
# Task management with smart scheduling
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


def get_scheduled_tasks():
    """Get tasks scheduled for today based on day of week"""
    today = date.today()
    weekday_name = calendar.day_name[today.weekday()]
    
    scheduled_tasks = []
    
    # Daily tasks
    scheduled_tasks.extend(st.session_state.tasks['daily'])
    
    # Weekly tasks (Thursday & Friday)
    if weekday_name in ['Thursday', 'Friday']:
        scheduled_tasks.extend(st.session_state.tasks['weekly'])
    
    # Monthly tasks (first day of month)
    if today.day == 1:
        scheduled_tasks.extend(st.session_state.tasks['monthly'])
    
    # Grooming tasks specifically on Thursday
    if weekday_name == 'Thursday':
        grooming_tasks = ['Clean eyes', 'Clean chin', 'Clean cat tree', 'Clean bedding']
        scheduled_tasks.extend(grooming_tasks)
    
    return scheduled_tasks


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
                'notes': [], 'entry_count': 0, 'pooped_today': False,
                'food_consumed': [], 'vomit_incidents': [], 'breathing_issues': [],
                'stress_indicators': [], 'urinary_issues': [], 'gum_issues': []
            }

        d = daily[entry_date]
        d['water_drinks']     += entry.get('water_drinks', 0)
        d['food_eats']        += entry.get('food_eats', 0)
        d['litter_box_times'] += entry.get('litter_box_times', 0)
        d['entry_count']      += 1

        if entry.get('pooped_today'): d['pooped_today'] = True

        if entry.get('food_consumed'):
            d['food_consumed'].extend(entry['food_consumed'])

        if entry.get('vomit_incidents'):
            d['vomit_incidents'].extend(entry['vomit_incidents'])

        if entry.get('breathing_issues'):
            d['breathing_issues'].extend(entry['breathing_issues'])

        if entry.get('stress_indicators'):
            d['stress_indicators'].extend(entry['stress_indicators'])

        if entry.get('urinary_issues'):
            d['urinary_issues'].extend(entry['urinary_issues'])

        if entry.get('gum_issues'):
            d['gum_issues'].extend(entry['gum_issues'])

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
# Enhanced health analysis with explanations
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

    # Additional analysis for new features
    breathing_issues_count = sum(len(d['breathing_issues']) for d in daily.values())
    stress_indicators_count = sum(len(d['stress_indicators']) for d in daily.values())
    urinary_issues_count = sum(len(d['urinary_issues']) for d in daily.values())
    gum_issues_count = sum(len(d['gum_issues']) for d in daily.values())
    vomit_incidents_count = sum(len(d['vomit_incidents']) for d in daily.values())

    days_without_poop = sum(1 for d in daily.values() if not d['pooped_today'])

    concerns, recommendations = [], []

    # Water intake analysis
    if water_avg < 2:
        concerns.append(f'Low water intake (avg {water_avg:.1f}/day)')
        recommendations.append('💧 Add more water sources or try wet food. Cats need water to prevent kidney issues.')

    # Food intake analysis
    if food_avg < 1:
        concerns.append(f'Low food intake (avg {food_avg:.1f}/day)')
        recommendations.append('🍽️ Monitor appetite — consult vet if it persists. Sudden changes can indicate illness.')

    # Litter box usage analysis
    if litter_avg > 6:
        concerns.append(f'High litter box usage (avg {litter_avg:.1f}/day)')
        recommendations.append('🚽 Monitor for urinary tract issues or stress. Frequent urination can indicate UTI or kidney problems.')

    # Pooping analysis
    if days_without_poop > 2:
        concerns.append(f'No bowel movement for {days_without_poop} days')
        recommendations.append('🚨 Monitor for constipation. Lack of pooping can indicate intestinal issues.')

    # Breathing issues
    if breathing_issues_count > 0:
        concerns.append(f'{breathing_issues_count} breathing issue(s) detected')
        recommendations.append('🫁 Check for respiratory infections, heart issues, or stress. Labored breathing requires vet attention.')

    # Stress indicators
    if stress_indicators_count > 2:
        concerns.append(f'{stress_indicators_count} stress indicators')
        recommendations.append('😿 Reduce stressors in environment. Stress can weaken immune system and cause various health issues.')

    # Urinary issues
    if urinary_issues_count > 0:
        concerns.append(f'{urinary_issues_count} urinary issue(s)')
        recommendations.append('🚨 Urgent: May indicate UTI, crystals, or kidney problems. Requires immediate veterinary attention.')

    # Gum issues
    if gum_issues_count > 0:
        concerns.append(f'{gum_issues_count} gum issue(s)')
        recommendations.append('🦷 Check for dental disease. Red gums can indicate gingivitis or infection.')

    # Vomit analysis
    if vomit_incidents_count > 2:
        concerns.append(f'{vomit_incidents_count} vomit incidents')
        recommendations.append('🤢 Monitor vomiting patterns. Chronic vomiting can indicate various underlying issues.')

    # Litter quality issues
    if all_litter_issues:
        concerns.append(f'Litter quality issues ({len(all_litter_issues)} instance(s))')
        recommendations.append('🚨 URGENT: Consult vet about litter abnormalities. Blood or diarrhea require immediate attention.')

    return {**base, 'status': 'ok', 'total_entries': total_entries, 'total_days': total_days,
            'water_avg': water_avg, 'food_avg': food_avg, 'litter_avg': litter_avg,
            'mood_trend': mood_trend, 'litter_issues': all_litter_issues,
            'breathing_issues_count': breathing_issues_count,
            'stress_indicators_count': stress_indicators_count,
            'urinary_issues_count': urinary_issues_count,
            'gum_issues_count': gum_issues_count,
            'vomit_incidents_count': vomit_incidents_count,
            'days_without_poop': days_without_poop,
            'concerns': concerns, 'recommendations': recommendations}


# ─────────────────────────────────────────────
# Diet planning features
# ─────────────────────────────────────────────
def get_diet_explanation():
    return """
    **Why 3 meals daily is recommended for cats:**
    
    🍽️ **Better Digestion**: Cats have smaller stomachs and shorter digestive tracts. Multiple small meals are easier to digest than one large meal.
    
    🩸 **Stable Blood Sugar**: Prevents blood sugar spikes and crashes, which is especially important for diabetic or pre-diabetic cats.
    
    🏃 **Energy Levels**: Provides consistent energy throughout the day rather than periods of high energy followed by lethargy.
    
    🔥 **Weight Management**: Helps maintain healthy weight by preventing overeating in single large meals.
    
    💧 **Increased Water Intake**: Wet food meals provide more hydration, supporting kidney and urinary tract health.
    
    🧠 **Reduced Stress**: Regular meal times reduce anxiety and begging behavior.
    """


# ─────────────────────────────────────────────
# Health guide with comprehensive issues
# ─────────────────────────────────────────────
def cat_health_guide_page():
    st.header("🏥 Cat Health Guide")

    # Normal vs Abnormal appearance guide
    st.subheader("🔍 Normal vs Abnormal Appearance")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ✅ **Normal**")
        st.markdown("**Urine:**")
        st.markdown("- Clear to pale yellow")
        st.markdown("- Moderate odor")
        st.markdown("- No visible particles")
        st.markdown("")
        st.markdown("**Stool:**")
        st.markdown("- Brown, formed")
        st.markdown("- Easy to scoop")
        st.markdown("- No strong odor")
        st.markdown("- Regular size and shape")

    with col2:
        st.markdown("#### ❌ **Abnormal**")
        st.markdown("**Urine:**")
        st.markdown("- **Red/Brown**: Blood - UTI, crystals, injury")
        st.markdown("- **Cloudy**: Infection, crystals")
        st.markdown("- **Strong ammonia smell**: Dehydration, UTI")
        st.markdown("- **Frequent small amounts**: UTI, stress")
        st.markdown("")
        st.markdown("**Stool:**")
        st.markdown("- **Black/tarry**: Internal bleeding")
        st.markdown("- **Red**: Blood in stool")
        st.markdown("- **Hard/pebbles**: Constipation")
        st.markdown("- **Watery/diarrhea**: Infection, stress, diet change")
        st.markdown("- **Unusually foul odor**: Infection, parasites")

    st.markdown("---")
    st.subheader("🩺 Common Health Issues")

    issues_data = {
        "Upper Respiratory Infection": {
            "symptoms": ["Sneezing", "Runny nose/eyes", "Nasal congestion", "Lethargy", "Loss of appetite", "Fever"],
            "causes": ["Viral (FHV-1, FCV)", "Bacterial", "Environmental stressors"],
            "treatment": ["Antibiotics for bacterial", " supportive care", "humidifier", "fluids"],
            "prevention": ["Vaccination", "clean environment", "stress reduction"]
        },
        "Urinary Tract Infection (UTI)": {
            "symptoms": ["Frequent urination", "Straining to urinate", "Blood in urine", "Crying in litter box", "Licking genitals"],
            "causes": ["Bacterial infection", "Crystals/stones", "Stress", "Dehydration"],
            "treatment": ["Antibiotics", "increased fluids", "diet change", "pain management"],
            "prevention": ["Plenty of water", "wet food diet", "clean litter", "stress reduction"]
        },
        "Kidney Disease": {
            "symptoms": ["Increased thirst/urination", "Weight loss", "Vomiting", "Bad breath", "Lethargy", "Poor coat"],
            "causes": ["Age", "genetics", "dehydration", "toxins", "previous infections"],
            "treatment": ["Fluid therapy", "special diet", "medications", "regular vet monitoring"],
            "prevention": ["Hydration", "regular checkups", "avoid toxins", "dental care"]
        },
        "Dental Disease": {
            "symptoms": ["Bad breath", "Red/swollen gums", "Difficulty eating", "Drooling", "Pawing at mouth"],
            "causes": ["Plaque buildup", "bacteria", "poor dental hygiene", "diet"],
            "treatment": ["Dental cleaning", "antibiotics", "dental care", "diet change"],
            "prevention": ["Regular brushing", "dental treats", "annual checkups", "quality diet"]
        },
        "Heart Disease": {
            "symptoms": ["Rapid breathing", "Coughing", "Lethargy", "Reduced appetite", "Weight loss"],
            "causes": ["Genetics", "age", "hypertension", "thyroid issues"],
            "treatment": ["Medications", "diet change", "fluid restriction", "regular monitoring"],
            "prevention": ["Regular vet checkups", "weight management", "low-sodium diet"]
        },
        "Stress/Anxiety": {
            "symptoms": ["Hiding", "Aggression", "Over-grooming", "Urination outside litter", "Loss of appetite"],
            "causes": ["Environmental changes", "new pets", "loud noises", "lack of stimulation"],
            "treatment": ["Environmental enrichment", "pharmacotherapy", "routine establishment"],
            "prevention": ["Stable environment", "playtime", "hiding spots", "routine"]
        },
        "Gastrointestinal Issues": {
            "symptoms": ["Vomiting", "Diarrhea", "Constipation", "Abdominal pain", "Blood in stool"],
            "causes": ["Diet change", "hairballs", "parasites", "infection", "foreign objects"],
            "treatment": ["Diet management", "medications", "fluid therapy", "veterinary care"],
            "prevention": ["Gradual diet changes", "regular deworming", "hairball control", "monitoring"]
        }
    }

    selected_issue = st.selectbox("Select an issue for detailed information", list(issues_data.keys()))
    
    if selected_issue:
        issue = issues_data[selected_issue]
        
        st.markdown(f"### 📋 {selected_issue}")
        
        st.markdown("**🎯 Symptoms:**")
        for symptom in issue["symptoms"]:
            st.markdown(f"- {symptom}")
        
        st.markdown("**🔍 Causes:**")
        for cause in issue["causes"]:
            st.markdown(f"- {cause}")
        
        st.markdown("**💊 Treatment:**")
        for treatment in issue["treatment"]:
            st.markdown(f"- {treatment}")
        
        st.markdown("**🛡️ Prevention:**")
        for prevention in issue["prevention"]:
            st.markdown(f"- {prevention}")

    st.markdown("---")
    st.subheader("🩺 Vomit Color Analysis")
    
    vomit_colors = {
        "Clear": "Usually hairballs or water regurgitation",
        "Yellow/Bile": "Empty stomach, hunger, bile reflux",
        "White/Foamy": "Stomach acid, hunger, stress",
        "Green": "Bile, intestinal issues, grass ingestion",
        "Red/Brown": "Blood - requires immediate vet attention",
        "Coffee Grounds": "Digested blood - serious issue",
        "Undigested Food": "Eating too fast, food intolerance"
    }
    
    for color, meaning in vomit_colors.items():
        st.markdown(f"**{color}**: {meaning}")

# ─────────────────────────────────────────────
# Dashboard with enhanced analysis
# ─────────────────────────────────────────────
def dashboard_page():
    st.header("🎯 Dashboard")

    # Vet reminders section
    st.subheader("🏥 Vet Appointment Reminders")
    today = date.today()
    reminder_text = ""
    
    for reminder_type, reminder_data in st.session_state.vet_reminders.items():
        if reminder_data['last_date']:
            last_date = datetime.fromisoformat(reminder_data['last_date']).date()
            days_since = (today - last_date).days
            next_due = days_since >= reminder_data['interval_days']
            
            if next_due:
                reminder_text += f"🚨 **{reminder_type.replace('_', ' ').title()}** is due!\n"
            else:
                days_left = reminder_data['interval_days'] - days_since
                reminder_text += f"⏰ **{reminder_type.replace('_', ' ').title()}:** {days_left} days left\n"
    
    if reminder_text:
        st.warning(reminder_text)
    else:
        st.info("All vet appointments are up to date!")

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
        scheduled_tasks = get_scheduled_tasks()
        st.metric("Today's Tasks", f"{len(today_tasks)}/{len(scheduled_tasks)}")
    with c3:
        st.metric("Vet Visits", sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))
    with c4:
        active = sum(1 for cat in st.session_state.cats if cat in st.session_state.health_data and st.session_state.health_data[cat])
        st.metric("Active Cats", f"{active}/{len(st.session_state.cats)}")

    st.markdown("---")
    st.subheader("📊 Weekly Health Analysis")
    
    # Enhanced dashboard with detailed analysis
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    for cat in st.session_state.cats:
        st.markdown(f"### 🐱 {cat}")
        analysis = analyze_cat_health(cat)
        
        if analysis['status'] == 'ok':
            # Display key metrics with explanations
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💧 Water Intake", f"{analysis['water_avg']:.1f}/day")
                if analysis['water_avg'] < 2:
                    st.warning("⚠️ Low water intake can lead to kidney issues")
                else:
                    st.success("✅ Good hydration")
            
            with col2:
                st.metric("🍽️ Food Intake", f"{analysis['food_avg']:.1f}/day")
                if analysis['food_avg'] < 1:
                    st.warning("⚠️ Monitor appetite changes")
                else:
                    st.success("✅ Normal eating")
            
            with col3:
                st.metric("🚽 Litter Box", f"{analysis['litter_avg']:.1f}/day")
                if analysis['litter_avg'] > 6:
                    st.warning("⚠️ Possible urinary issues")
                else:
                    st.success("✅ Normal litter usage")
            
            # Health concerns
            if analysis['concerns']:
                st.error("🚨 **Health Concerns:**")
                for concern in analysis['concerns']:
                    st.markdown(f"- {concern}")
            
            # Recommendations
            if analysis['recommendations']:
                st.info("💡 **Recommendations:**")
                for rec in analysis['recommendations']:
                    st.markdown(f"- {rec}")
            
            # Specific issue counts
            if analysis['breathing_issues_count'] > 0:
                st.warning(f"🫁 {analysis['breathing_issues_count']} breathing issue(s)")
            if analysis['stress_indicators_count'] > 0:
                st.warning(f"😿 {analysis['stress_indicators_count']} stress indicator(s)")
            if analysis['urinary_issues_count'] > 0:
                st.error(f"🚨 {analysis['urinary_issues_count']} urinary issue(s)")
            if analysis['gum_issues_count'] > 0:
                st.warning(f"🦷 {analysis['gum_issues_count']} gum issue(s)")
            if analysis['vomit_incidents_count'] > 0:
                st.warning(f"🤢 {analysis['vomit_incidents_count']} vomit incidents")
            if analysis['days_without_poop'] > 0:
                st.warning(f"🚨 {analysis['days_without_poop']} day(s) without poop")
        
        st.markdown("---")

    st.markdown("---")
    st.subheader("📈 Weekly Comparison — All Cats")
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


# ─────────────────────────────────────────────
# Enhanced Cat Profiles
# ─────────────────────────────────────────────
def cat_profiles_page():
    st.header("🐱 Cat Profiles")

    for cat in st.session_state.cats:
        with st.expander(f"{cat}'s Profile", expanded=False):
            profile = st.session_state.cat_profiles[cat]
            
            col1, col2 = st.columns(2)
            
            with col1:
                age = st.text_input("Age", value=profile['age'], key=f"age_{cat}")
                breed = st.text_input("Breed", value=profile['breed'], key=f"breed_{cat}")
                weight = st.text_input("Weight (kg)", value=profile['weight'], key=f"weight_{cat}")
                default_food = st.text_input("Default Food", value=profile.get('default_food', 'Pro Plan Adult'), key=f"food_{cat}")
            
            with col2:
                diet_plan = st.selectbox("Diet Plan", ["2 meals daily", "3 meals daily", "Free feeding", "Special diet"], 
                                       index=["2 meals daily", "3 meals daily", "Free feeding", "Special diet"].index(profile.get('diet_plan', '3 meals daily')), 
                                       key=f"diet_{cat}")
                
                # Diet explanation
                if st.button(f"📖 Why {diet_plan}?", key=f"why_{cat}"):
                    st.info(get_diet_explanation())
                
                notes = st.text_area("Notes", value=profile.get('notes', ''), key=f"notes_{cat}")
            
            # Vet visits
            st.subheader("🏥 Vet Visits")
            new_visit_date = st.date_input("Visit Date", key=f"visit_date_{cat}")
            new_visit_reason = st.text_input("Reason/Procedure", key=f"visit_reason_{cat}")
            new_visit_notes = st.text_area("Notes", key=f"visit_notes_{cat}")
            
            if st.button("Add Visit", key=f"add_visit_{cat}"):
                if new_visit_reason:
                    visit = {
                        'date': str(new_visit_date),
                        'reason': new_visit_reason,
                        'notes': new_visit_notes
                    }
                    profile['vet_visits'].append(visit)
                    st.session_state.cat_profiles[cat] = profile
                    save_data()
                    st.success("Visit added!")
                    st.rerun()
            
            # Display existing visits
            if profile['vet_visits']:
                st.markdown("**Previous Visits:**")
                for i, visit in enumerate(profile['vet_visits']):
                    st.markdown(f"**{visit['date']}** - {visit['reason']}")
                    if visit['notes']:
                        st.markdown(f"  Notes: {visit['notes']}")
                    if st.button("Delete", key=f"delete_visit_{cat}_{i}"):
                        profile['vet_visits'].pop(i)
                        st.session_state.cat_profiles[cat] = profile
                        save_data()
                        st.rerun()
            
            # Update profile
            if st.button("Update Profile", key=f"update_profile_{cat}"):
                profile.update({
                    'age': age, 'breed': breed, 'weight': weight,
                    'notes': notes, 'default_food': default_food, 'diet_plan': diet_plan
                })
                st.session_state.cat_profiles[cat] = profile
                save_data()
                st.success("Profile updated!")


# ─────────────────────────────────────────────
# Enhanced Health Entry Form
# ─────────────────────────────────────────────
def add_health_entry_page():
    st.header("📝 Add Health Entry")

    cat_name = st.selectbox("Select Cat", st.session_state.cats)
    st.session_state.health_form_cat = cat_name

    with st.form("health_entry_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            water_drinks = st.number_input("Water Drinks", min_value=0, step=1)
            food_eats = st.number_input("Food Eats", min_value=0, step=1)
            litter_box_times = st.number_input("Litter Box Times", min_value=0, step=1)
            pooped_today = st.checkbox("✅ Pooped Today?")
            
            # Food consumed
            st.subheader("🍽️ Food Consumed")
            default_food = st.session_state.cat_profiles[cat_name].get('default_food', 'Pro Plan Adult')
            food_options = [default_food, 'Wet Food', 'Treats', 'Other']
            selected_foods = st.multiselect("Select food types consumed", food_options, default=[default_food])
            
            # Medication/Treatment
            st.subheader("💊 Medication/Treatment")
            med_name = st.text_input("Medication/Treatment Name")
            med_dosage = st.text_input("Dosage")
            med_frequency = st.text_input("Frequency")
            med_reason = st.text_input("Reason")
            med_start_date = st.date_input("Start Date")
            med_end_date = st.date_input("End Date (leave blank if ongoing)")
        
        with col2:
            mood = st.selectbox("Mood", ["Excellent", "Good", "Fair", "Poor", "Very Poor"])
            general_appearance = st.text_area("General Appearance")
            
            # Grooming tasks
            st.subheader("🧼 Grooming Tasks Completed")
            grooming_tasks = {
                'Brushed': False, 'Nails trimmed': False, 'Ears cleaned': False,
                'Bath': False, 'Wipe face': False, 'Other': False
            }
            for task in grooming_tasks:
                grooming_tasks[task] = st.checkbox(task)
            
            # Litter quality
            st.subheader("🚽 Litter Quality")
            litter_options = ["Normal", "Blood", "Diarrhea", "Constipation", "Straining", "Other"]
            litter_issues = st.multiselect("Select litter issues", litter_options)
            
            # Vomit incidents
            st.subheader("🤢 Vomit Incidents")
            vomit_colors = st.multiselect("Vomit colors", ["Clear", "Yellow/Bile", "White/Foamy", "Green", "Red/Brown", "Coffee Grounds"])
            vomit_notes = st.text_area("Vomit notes")
            
            # Breathing issues
            st.subheader("🫁 Breathing Issues")
            breathing_issues = st.multiselect("Breathing problems", ["Wheezing", "Rapid breathing", "Coughing", "Labored breathing", "Nasal discharge"])
            breathing_notes = st.text_area("Breathing notes")
            
            # Stress indicators
            st.subheader("😿 Stress Indicators")
            stress_options = ["Hiding", "Aggression", "Over-grooming", "Lack of appetite", "Vocalization", "Other"]
            stress_indicators = st.multiselect("Stress signs", stress_options)
            stress_notes = st.text_area("Stress notes")
            
            # Urinary issues
            st.subheader("🚽 Urinary Issues")
            urinary_options = ["Straining", "Frequent urination", "Blood in urine", "Crying in litter box", "Urinating outside"]
            urinary_issues = st.multiselect("Urinary problems", urinary_options)
            urinary_notes = st.text_area("Urinary notes")
            
            # Gum issues
            st.subheader("🦷 Gum Issues")
            gum_options = ["Red gums", "Swollen gums", "Bad breath", "Drooling", "Pawing at mouth"]
            gum_issues = st.multiselect("Gum problems", gum_options)
            gum_notes = st.text_area("Gum notes")
            
            notes = st.text_area("General Notes")

        submitted = st.form_submit_button("Add Entry")
        
        if submitted:
            entry_data = {
                'water_drinks': water_drinks,
                'food_eats': food_eats,
                'litter_box_times': litter_box_times,
                'pooped_today': pooped_today,
                'food_consumed': selected_foods,
                'mood': mood,
                'general_appearance': general_appearance,
                'grooming_tasks': grooming_tasks,
                'litter_quality': litter_issues,
                'vomit_incidents': vomit_colors + ([vomit_notes] if vomit_notes else []),
                'breathing_issues': breathing_issues + ([breathing_notes] if breathing_notes else []),
                'stress_indicators': stress_indicators + ([stress_notes] if stress_notes else []),
                'urinary_issues': urinary_issues + ([urinary_notes] if urinary_notes else []),
                'gum_issues': gum_issues + ([gum_notes] if gum_notes else []),
                'notes': notes
            }
            
            if med_name:
                entry_data.update({
                    'medication_name': med_name,
                    'medication_dosage': med_dosage,
                    'medication_frequency': med_frequency,
                    'medication_reason': med_reason,
                    'medication_start_date': str(med_start_date),
                    'medication_end_date': str(med_end_date) if med_end_date else None
                })
            
            add_health_entry(cat_name, entry_data)
            st.success(f"✅ Health entry added for {cat_name}!")
            st.rerun()


# ─────────────────────────────────────────────
# Task Management with smart reminders
# ─────────────────────────────────────────────
def task_management_page():
    st.header("📋 Task Management")

    today = date.today()
    scheduled_tasks = get_scheduled_tasks()
    
    st.subheader(f"📅 Today's Tasks ({today.strftime('%A, %B %d, %Y')})")
    
    # Show scheduled tasks
    for task in scheduled_tasks:
        completed = False
        completion_note = ""
        
        # Check if task is completed
        today_str = str(today)
        if today_str in st.session_state.task_logs:
            for log in st.session_state.task_logs[today_str]:
                if log['task'] == task:
                    completed = True
                    completion_note = log.get('notes', '')
                    break
        
        task_key = f"task_{task.replace(' ', '_')}"
        
        if completed:
            st.success(f"✅ {task} - Completed")
            if completion_note:
                st.info(f"   Note: {completion_note}")
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.warning(f"⏳ {task}")
            with col2:
                if st.button("Complete", key=task_key):
                    add_task_completion(task, notes=completion_note)
                    st.rerun()

    st.markdown("---")
    st.subheader("📝 Task Completion Notes")
    
    # Allow adding notes to completed tasks
    for task in scheduled_tasks:
        if not any(log['task'] == task for log in st.session_state.task_logs.get(str(today), [])):
            continue
            
        task_key = f"note_{task.replace(' ', '_')}"
        notes = st.text_input(f"Notes for {task}", key=task_key)
        
        if st.button("Update Notes", key=f"update_{task_key}"):
            # This would need to be implemented to update existing task logs
            st.info(f"Notes updated for {task}")

    st.markdown("---")
    st.subheader("📊 Task History")
    
    # Show task completion history
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=today - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", value=today)
    
    task_completions = get_task_completions(start_date, end_date)
    
    if task_completions:
        all_tasks = []
        for date_str, logs in task_completions.items():
            for log in logs:
                all_tasks.append({
                    'Date': date_str,
                    'Task': log['task'],
                    'Cat': log.get('cat', 'N/A'),
                    'Completed': datetime.fromisoformat(log['completed_at']).strftime('%H:%M'),
                    'Notes': log.get('notes', '')
                })
        
        task_df = pd.DataFrame(all_tasks)
        st.dataframe(task_df, use_container_width=True, hide_index=True)
    else:
        st.info("No task completions found for the selected date range.")


# ─────────────────────────────────────────────
# Enhanced Data Management
# ─────────────────────────────────────────────
def data_management_page():
    st.header("⚙️ Data Management")
    st.warning("⚠️ **Caution:** Actions on this page can permanently delete your data!")

    st.markdown("---")
    st.subheader("📥 Export Data")
    c1,c2,c3,c4 = st.columns(4)
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
    with c4:
        if st.button("📥 Export Vet Reminders", use_container_width=True):
            st.download_button("💾 Download Vet Reminders",
                data=json.dumps(st.session_state.vet_reminders, indent=2, default=str),
                file_name=f"vet_reminders_{date.today()}.json", mime="application/json")

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
        del_end   = st.date_input("End Date",  key="delete_task_end")
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
            cat: {
                'age': '', 'breed': '', 'weight': '', 'vet_visits': [], 
                'notes': '', 'default_food': 'Pro Plan Adult', 'diet_plan': '3 meals daily'
            }
            for cat in st.session_state.cats
        }
        st.session_state.last_entries  = {cat: None for cat in st.session_state.cats}
        st.session_state.data_loaded   = False
        st.session_state.vet_reminders = {
            'annual_checkup': {'interval_days': 365, 'last_date': None},
            'vaccines': {'interval_days': 365, 'last_date': None},
            'deworming': {'interval_days': 90, 'last_date': None},
            'kuro_heart': {'interval_days': 120, 'last_date': None}
        }
        for fname in ['health_data.json','task_logs.json','cat_profiles.json','vet_reminders.json']:
            try:
                if os.path.exists(fname): os.remove(fname)
            except: pass
        st.success("✅ Application completely reset!")
        time.sleep(1); st.rerun()

    st.markdown("---")
    st.subheader("📊 Data Statistics")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Total Health Entries", sum(len(d) for cat_data in st.session_state.health_data.values() for d in cat_data.values()))
    with c2: st.metric("Total Task Completions", sum(len(logs) for logs in st.session_state.task_logs.values()))
    with c3: st.metric("Total Vet Visits", sum(len(p.get('vet_visits',[])) for p in st.session_state.cat_profiles.values()))
    with c4: st.metric("Days Active", len(st.session_state.task_logs))


# ─────────────────────────────────────────────
# Enhanced Reminders
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
        scheduled_tasks = get_scheduled_tasks()
        incomplete = [t for t in scheduled_tasks if t not in done]
        if incomplete:
            st.info(f"📝 Incomplete daily tasks: {', '.join(incomplete)}")

        st.session_state.last_reminder = current_time


# ─────────────────────────────────────────────
# Main Application
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
```
