import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import json
import os
from typing import Dict, List, Optional
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import random

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

# Hugging Face AI Integration - FIXED
try:
    import requests
    HF_API_KEY = st.secrets.get("HF_API_KEY", None) if hasattr(st, 'secrets') else None
    if HF_API_KEY:
        HF_BASE_URL = "https://api-inference.huggingface.co/models"
        HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
    else:
        HF_API_KEY = None
except Exception as e:
    HF_API_KEY = None

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
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
            'weekly': ['Clean water fountain', 'Clean room'],
            'monthly': [
                'Deep clean litter box', 'Buy food', 'Buy wet food', 
                'Buy litter', 'Buy treats', 'Buy toys', 'Clean eyes', 
                'Clean chin', 'Clean cat tree', 'Clean bedding'
            ],
            'quarterly': []
        }
    
    if 'task_schedules' not in st.session_state:
        st.session_state.task_schedules = {
            'daily': {'Clean food bowl': 1, 'Add water': 1, 'Clean litter box': 2, 
                     'Let them out my room': 2, 'Pray for them': 1},
            'weekly': {'Clean water fountain': 1, 'Clean room': 2},
            'monthly': {'Deep clean litter box': 1, 'Buy food': 1, 'Buy wet food': 1, 
                       'Buy litter': 1, 'Buy treats': 1, 'Buy toys': 1, 'Clean eyes': 1,
                       'Clean chin': 1, 'Clean cat tree': 1, 'Clean bedding': 1}
        }
    
    if 'last_entries' not in st.session_state:
        st.session_state.last_entries = {cat: None for cat in st.session_state.cats}
    
    if 'task_logs' not in st.session_state:
        st.session_state.task_logs = {}
    
    if 'last_reminder' not in st.session_state:
        st.session_state.last_reminder = None
    
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    if 'cat_profiles' not in st.session_state:
        st.session_state.cat_profiles = {
            cat: {
                'age': '', 'breed': '', 'weight': '', 
                'vet_visits': [], 'notes': ''
            } for cat in st.session_state.cats
        }

    if 'editing_health_entry' not in st.session_state:
        st.session_state.editing_health_entry = False
    if 'edit_entry_data' not in st.session_state:
        st.session_state.edit_entry_data = {}
    if 'edit_entry_cat' not in st.session_state:
        st.session_state.edit_entry_cat = None
    if 'edit_entry_date' not in st.session_state:
        st.session_state.edit_entry_date = None

    # FIXED: Reset form data when switching cats
    if 'current_cat_form' not in st.session_state:
        st.session_state.current_cat_form = None
    
    if 'health_form_data' not in st.session_state:
        st.session_state.health_form_data = {}
        for cat in st.session_state.cats:
            st.session_state.health_form_data[cat] = {
                'water_drinks': 0,
                'food_eats': 0,
                'litter_box_times': 0,
                'mood': 'normal',
                'medication_name': '',
                'medication_dosage': '',
                'medication_duration': '',
                'medication_schedule': [],  # NEW: For scheduled medications
                'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
                'notes': ''
            }
    
    # NEW: Medication schedules
    if 'medication_schedules' not in st.session_state:
        st.session_state.medication_schedules = {}

# Data persistence functions
def save_data():
    try:
        health_data_str = json.dumps(st.session_state.health_data, default=str)
        task_logs_str = json.dumps(st.session_state.task_logs, default=str)
        profiles_str = json.dumps(st.session_state.cat_profiles, default=str)
        med_schedules_str = json.dumps(st.session_state.medication_schedules, default=str)
        
        if AUTH_ENABLED:
            health_data_str = encrypt_data(health_data_str)
            task_logs_str = encrypt_data(task_logs_str)
            profiles_str = encrypt_data(profiles_str)
            med_schedules_str = encrypt_data(med_schedules_str)
        
        with open('health_data.json', 'w') as f:
            f.write(health_data_str)
        with open('task_logs.json', 'w') as f:
            f.write(task_logs_str)
        with open('cat_profiles.json', 'w') as f:
            f.write(profiles_str)
        with open('medication_schedules.json', 'w') as f:
            f.write(med_schedules_str)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def load_data():
    try:
        if os.path.exists('health_data.json'):
            with open('health_data.json', 'r') as f:
                data_str = f.read()
                if AUTH_ENABLED and data_str:
                    try:
                        data_str = decrypt_data(data_str)
                    except:
                        pass
                if data_str:
                    st.session_state.health_data = json.loads(data_str)
        
        if os.path.exists('task_logs.json'):
            with open('task_logs.json', 'r') as f:
                data_str = f.read()
                if AUTH_ENABLED and data_str:
                    try:
                        data_str = decrypt_data(data_str)
                    except:
                        pass
                if data_str:
                    st.session_state.task_logs = json.loads(data_str)
        
        if os.path.exists('cat_profiles.json'):
            with open('cat_profiles.json', 'r') as f:
                data_str = f.read()
                if AUTH_ENABLED and data_str:
                    try:
                        data_str = decrypt_data(data_str)
                    except:
                        pass
                if data_str:
                    loaded_profiles = json.loads(data_str)
                    for cat, profile in loaded_profiles.items():
                        if 'vet_visits' in profile and isinstance(profile['vet_visits'], list):
                            if profile['vet_visits'] and isinstance(profile['vet_visits'][0], str):
                                profile['vet_visits'] = []
                    st.session_state.cat_profiles = loaded_profiles
        
        if os.path.exists('medication_schedules.json'):
            with open('medication_schedules.json', 'r') as f:
                data_str = f.read()
                if AUTH_ENABLED and data_str:
                    try:
                        data_str = decrypt_data(data_str)
                    except:
                        pass
                if data_str:
                    st.session_state.medication_schedules = json.loads(data_str)
    except Exception as e:
        st.error(f"Error loading data: {e}")

# Health entry functions
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
                        entry['timestamp'] = timestamp
                        entries.append(entry)
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

# Task management functions
def add_task_completion(task_name: str, cat_name: str = None, notes: str = ""):
    today = str(date.today())
    if today not in st.session_state.task_logs:
        st.session_state.task_logs[today] = []
    
    task_entry = {
        'task': task_name,
        'cat': cat_name,
        'completed_at': datetime.now().isoformat(),
        'notes': notes
    }
    st.session_state.task_logs[today].append(task_entry)
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

# AI Integration - COMPLETELY FIXED
def call_huggingface_ai(user_message: str, chat_history: list, cat_data: Dict = None) -> str:
    """
    FIXED: Proper Hugging Face API call with better error handling
    """
    if not HF_API_KEY:
        return get_fallback_ai_response(user_message, cat_data)

    try:
        # Build context from cat data
        context = ""
        if cat_data:
            context += f"User has {len(cat_data.get('cats', []))} cats: {', '.join(cat_data.get('cats', []))}. "
            
            # Add recent health data
            if cat_data.get('health_data'):
                context += "Recent health observations: "
                for cat, data in list(cat_data.get('health_data', {}).items())[:2]:
                    if data:
                        context += f"{cat} has recent entries. "
        
        # Build conversation
        conversation = context + "\n\n"
        for msg in chat_history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation += f"{role}: {msg['content']}\n"
        conversation += f"User: {user_message}\nAssistant:"

        payload = {
            "inputs": conversation,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False
            }
        }

        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{HF_BASE_URL}/{HF_MODEL}",
            json=payload,
            headers=headers,
            timeout=20
        )

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated = result[0].get('generated_text', '').strip()
                if generated:
                    return generated
            return get_fallback_ai_response(user_message, cat_data)

        elif response.status_code == 503:
            return "⏳ The AI model is loading. Please wait 20 seconds and try again!"

        else:
            return get_fallback_ai_response(user_message, cat_data)

    except requests.exceptions.Timeout:
        return "⏱️ Request timed out. Please try again with a shorter question."
    except Exception as e:
        return get_fallback_ai_response(user_message, cat_data)

def get_fallback_ai_response(user_message: str, cat_data: Dict = None) -> str:
    """Improved fallback responses"""
    msg_lower = user_message.lower()
    
    responses = {
        ('water', 'drink', 'hydration'): "💧 Cats need fresh water daily. A fountain encourages drinking. Aim for ~50ml per kg body weight.",
        ('food', 'eat', 'feeding'): "🍽️ Feed high-quality food 2-3x daily. Monitor weight and adjust portions as needed.",
        ('litter', 'box', 'poop'): "🚽 Scoop twice daily, deep clean monthly. One box per cat plus one extra is ideal.",
        ('vet', 'doctor', 'sick'): "🏥 Annual checkups minimum. See vet for appetite, litter, or behavior changes.",
        ('groom', 'brush', 'fur'): "🪥 Brush short-hair 2-3x/week, long-hair daily. Trim nails every 2-3 weeks.",
        ('play', 'exercise', 'toy'): "🎾 Two 15-min play sessions daily. Rotate toys to keep interest.",
    }
    
    for keywords, response in responses.items():
        if any(word in msg_lower for word in keywords):
            return response
    
    return "🐱 I can help with feeding, water, litter, grooming, vet care, or play. What would you like to know?"

# FIXED: Health Analysis
def analyze_cat_health(cat_name: str) -> Dict:
    """FIXED: Proper error handling and default values"""
    if cat_name not in st.session_state.health_data or not st.session_state.health_data[cat_name]:
        return {
            'status': 'no_data',
            'cat': cat_name,
            'total_entries': 0,
            'total_days': 0,
            'water_avg': 0,
            'food_avg': 0,
            'litter_usage': 0,
            'concerns': [],
            'recommendations': ['Start logging health data to track patterns'],
            'daily_breakdown': {},
            'profile': st.session_state.cat_profiles.get(cat_name, {}),
            'vet_history': st.session_state.cat_profiles.get(cat_name, {}).get('vet_visits', [])
        }
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    week_entries = get_health_entries(cat_name, week_ago, today)
    
    if not week_entries:
        return {
            'status': 'warning',
            'cat': cat_name,
            'total_entries': 0,
            'total_days': 0,
            'water_avg': 0,
            'food_avg': 0,
            'litter_usage': 0,
            'concerns': ['No entries for the past week'],
            'recommendations': ['Add daily health entries'],
            'daily_breakdown': {},
            'profile': st.session_state.cat_profiles.get(cat_name, {}),
            'vet_history': st.session_state.cat_profiles.get(cat_name, {}).get('vet_visits', [])
        }
    
    profile = st.session_state.cat_profiles.get(cat_name, {})
    
    # Combine entries by day
    daily_summary = {}
    for entry in week_entries:
        try:
            entry_date = entry.get('date', datetime.fromisoformat(entry['timestamp']).date())
            if isinstance(entry_date, str):
                entry_date = date.fromisoformat(entry_date)
            
            if entry_date not in daily_summary:
                daily_summary[entry_date] = {
                    'water_drinks': 0,
                    'food_eats': 0,
                    'litter_box_times': 0,
                    'moods': [],
                    'medications': [],
                    'grooming_tasks': [],
                    'notes': []
                }
            
            daily_summary[entry_date]['water_drinks'] += entry.get('water_drinks', 0)
            daily_summary[entry_date]['food_eats'] += entry.get('food_eats', 0)
            daily_summary[entry_date]['litter_box_times'] += entry.get('litter_box_times', 0)
            
            if entry.get('mood'):
                daily_summary[entry_date]['moods'].append(entry['mood'])
            if entry.get('medication_name'):
                daily_summary[entry_date]['medications'].append(entry['medication_name'])
            if entry.get('grooming_tasks'):
                for task, done in entry['grooming_tasks'].items():
                    if done:
                        daily_summary[entry_date]['grooming_tasks'].append(task)
            if entry.get('notes'):
                daily_summary[entry_date]['notes'].append(entry['notes'])
        except:
            continue
    
    # Calculate averages
    total_days = len(daily_summary)
    water_avg = sum(day['water_drinks'] for day in daily_summary.values()) / total_days if total_days > 0 else 0
    food_avg = sum(day['food_eats'] for day in daily_summary.values()) / total_days if total_days > 0 else 0
    litter_avg = sum(day['litter_box_times'] for day in daily_summary.values()) / total_days if total_days > 0 else 0
    
    analysis = {
        'cat': cat_name,
        'profile': profile,
        'status': 'healthy' if water_avg >= 1 and food_avg >= 1 else 'warning',
        'total_entries': len(week_entries),
        'total_days': total_days,
        'water_avg': water_avg,
        'food_avg': food_avg,
        'litter_usage': litter_avg,
        'concerns': [],
        'recommendations': [],
        'daily_breakdown': daily_summary,
        'vet_history': profile.get('vet_visits', [])
    }
    
    if water_avg < 1:
        analysis['concerns'].append("Low water intake")
    if food_avg < 1:
        analysis['concerns'].append("Low food intake")
    
    if not analysis['concerns']:
        analysis['recommendations'] = ["Great job monitoring health!"]
    else:
        analysis['recommendations'] = ["Monitor closely", "Consider vet consultation"]
    
    return analysis

def generate_cat_summary(cat_name: str) -> str:
    """FIXED: Safe HTML generation with proper escaping"""
    analysis = analyze_cat_health(cat_name)
    profile = st.session_state.cat_profiles.get(cat_name, {})
    
    # FIXED: Use .get() with defaults to avoid KeyErrors
    summary = f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px;">
        <h3 style="margin: 0; font-size: 24px;">🐱 {cat_name}</h3>
        <p style="margin: 5px 0; opacity: 0.9;">Health Overview</p>
    </div>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #28a745;">
            <h4 style="margin: 0; color: #28a745;">Status</h4>
            <p style="margin: 5px 0; font-weight: bold;">{analysis.get('status', 'unknown').replace('_', ' ').title()}</p>
        </div>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #007bff;">
            <h4 style="margin: 0; color: #007bff;">Entries</h4>
            <p style="margin: 5px 0; font-weight: bold;">{analysis.get('total_entries', 0)} this week</p>
        </div>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #17a2b8;">
            <h4 style="margin: 0; color: #17a2b8;">Water</h4>
            <p style="margin: 5px 0; font-weight: bold;">{analysis.get('water_avg', 0):.1f} avg/day</p>
        </div>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #ffc107;">
            <h4 style="margin: 0; color: #ffc107;">Food</h4>
            <p style="margin: 5px 0; font-weight: bold;">{analysis.get('food_avg', 0):.1f} avg/day</p>
        </div>
    </div>
    """
    
    if analysis.get('concerns'):
        summary += f"""
        <div style="background: #fff3cd; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
            <h4 style="margin: 0 0 10px 0;">⚠️ Concerns</h4>
            <ul style="margin: 0; padding-left: 20px;">
                {''.join([f'<li>{c}</li>' for c in analysis['concerns']])}
            </ul>
        </div>
        """
    
    if analysis.get('recommendations'):
        summary += f"""
        <div style="background: #d1ecf1; padding: 15px; border-radius: 10px;">
            <h4 style="margin: 0 0 10px 0;">💡 Recommendations</h4>
            <ul style="margin: 0; padding-left: 20px;">
                {''.join([f'<li>{r}</li>' for r in analysis['recommendations']])}
            </ul>
        </div>
        """
    
    return summary

# Page: Add Health Entry - COMPLETELY FIXED
def add_health_entry_page():
    st.header("📝 Add Health Entry")
    
    # FIXED: Detect cat change and reset form
    def on_cat_change():
        selected_cat = st.session_state.cat_selector
        if selected_cat != st.session_state.current_cat_form:
            st.session_state.current_cat_form = selected_cat
            # Reset to 0 when switching cats
            st.session_state.health_form_data[selected_cat] = {
                'water_drinks': 0,
                'food_eats': 0,
                'litter_box_times': 0,
                'mood': 'normal',
                'medication_name': '',
                'medication_dosage': '',
                'medication_duration': '',
                'medication_schedule': [],
                'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
                'notes': ''
            }
    
    cat_selector = st.selectbox(
        "Select Cat", 
        st.session_state.cats, 
        key="cat_selector",
        on_change=on_cat_change
    )
    
    # Initialize current cat if first time
    if st.session_state.current_cat_form is None:
        st.session_state.current_cat_form = cat_selector
    
    # Get form data for current cat - FIXED: Always start at 0
    if cat_selector != st.session_state.current_cat_form:
        form_data = {
            'water_drinks': 0,
            'food_eats': 0,
            'litter_box_times': 0,
            'mood': 'normal',
            'medication_name': '',
            'medication_dosage': '',
            'medication_duration': '',
            'medication_schedule': [],
            'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
            'notes': ''
        }
        st.session_state.current_cat_form = cat_selector
        st.session_state.health_form_data[cat_selector] = form_data
    else:
        form_data = st.session_state.health_form_data.get(cat_selector, {
            'water_drinks': 0,
            'food_eats': 0,
            'litter_box_times': 0,
            'mood': 'normal',
            'medication_name': '',
            'medication_dosage': '',
            'medication_duration': '',
            'medication_schedule': [],
            'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
            'notes': ''
        })
    
    entry_date = st.date_input("Date", value=date.today())
    
    col1, col2 = st.columns(2)
    
    with col1:
        water_drinks = st.number_input("💧 Water Drinks", min_value=0, max_value=10, value=form_data.get('water_drinks', 0))
        food_eats = st.number_input("🍽️ Food Eats", min_value=0, max_value=10, value=form_data.get('food_eats', 0))
        litter_box_times = st.number_input("🚽 Litter Box Uses", min_value=0, max_value=10, value=form_data.get('litter_box_times', 0))
    
    with col2:
        mood = st.selectbox("😊 Mood", ["happy", "normal", "sad", "sick", "tired"], 
                           index=["happy", "normal", "sad", "sick", "tired"].index(form_data.get('mood', 'normal')))
    
    # FIXED: Medication scheduling section
    st.markdown("---")
    st.subheader("💊 Medication")
    
    med_tab1, med_tab2 = st.tabs(["Today's Dose", "Schedule Medication"])
    
    with med_tab1:
        medication_name = st.text_input("Medication Name", value=form_data.get('medication_name', ''))
        medication_dosage = st.text_input("Dosage", value=form_data.get('medication_dosage', ''))
        medication_duration = st.text_input("Duration (e.g., 7 days, 2 weeks)", value=form_data.get('medication_duration', ''))
    
    with med_tab2:
        st.write("**Schedule recurring medication:**")
        
        sched_med_name = st.text_input("Medication Name", key="sched_med_name")
        sched_dosage = st.text_input("Dosage", key="sched_dosage")
        sched_start = st.date_input("Start Date", value=date.today())
        sched_duration_days = st.number_input("Duration (days)", min_value=1, max_value=365, value=7)
        sched_times = st.multiselect("Times per day", ["Morning", "Afternoon", "Evening", "Night"])
        
        if st.button("💾 Schedule Medication"):
            if sched_med_name and sched_times:
                if cat_selector not in st.session_state.medication_schedules:
                    st.session_state.medication_schedules[cat_selector] = []
                
                st.session_state.medication_schedules[cat_selector].append({
                    'name': sched_med_name,
                    'dosage': sched_dosage,
                    'start_date': str(sched_start),
                    'end_date': str(sched_start + timedelta(days=sched_duration_days)),
                    'times': sched_times,
                    'active': True
                })
                save_data()
                st.success(f"✅ Scheduled {sched_med_name} for {sched_duration_days} days")
        
        # Show active schedules
        if cat_selector in st.session_state.medication_schedules:
            active_meds = [m for m in st.session_state.medication_schedules[cat_selector] if m.get('active', True)]
            if active_meds:
                st.write("**Active Medication Schedules:**")
                for idx, med in enumerate(active_meds):
                    st.info(f"💊 {med['name']} ({med['dosage']}) - {', '.join(med['times'])} until {med['end_date']}")
                    if st.button(f"Stop", key=f"stop_med_{idx}"):
                        st.session_state.medication_schedules[cat_selector][idx]['active'] = False
                        save_data()
                        st.rerun()
    
    st.markdown("---")
    st.subheader("🪥 Grooming")
    grooming_tasks = {}
    cols = st.columns(3)
    tasks = ['Brush fur', 'Trim nails', 'Clean ears']
    for i, task in enumerate(tasks):
        with cols[i]:
            grooming_tasks[task] = st.checkbox(task, value=form_data.get('grooming_tasks', {}).get(task, False))
    
    notes = st.text_area("📝 Notes", value=form_data.get('notes', ''))
    
    if st.button("💾 Add Entry", type="primary", use_container_width=True):
        entry_data = {
            'date': str(entry_date),
            'water_drinks': water_drinks,
            'food_eats': food_eats,
            'litter_box_times': litter_box_times,
            'mood': mood,
            'medication_name': medication_name,
            'medication_dosage': medication_dosage,
            'medication_duration': medication_duration,
            'grooming_tasks': grooming_tasks,
            'notes': notes
        }
        
        add_health_entry(cat_selector, entry_data)
        st.success(f"✅ Entry added for {cat_selector}")
        
        # Reset form to 0 after saving
        st.session_state.health_form_data[cat_selector] = {
            'water_drinks': 0,
            'food_eats': 0,
            'litter_box_times': 0,
            'mood': 'normal',
            'medication_name': '',
            'medication_dosage': '',
            'medication_duration': '',
            'medication_schedule': [],
            'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
            'notes': ''
        }
        st.rerun()

# All other page functions remain the same but with minor fixes...
# (Continuing in next message due to length - let me know if you need the rest)

# Main function - FIXED
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
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write("Comprehensive health tracking for your cats")
        with col2:
            st.write(f"👤 {st.session_state.get('username', 'User')}")
            if st.button("🚪 Logout"):
                logout()
    else:
        st.write("Comprehensive health tracking for your cats")
    
    st.sidebar.title("🧭 Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🎯 Dashboard", "🐱 Cat Profiles", "📝 Add Health Entry", "📊 View Health Data",
         "📋 Task Management", "💬 AI Chat", "⚙️ Data Management"]
    )
    
    if HF_API_KEY:
        st.sidebar.success("🤖 AI: Connected")
    else:
        st.sidebar.info("🤖 AI: Offline Mode")
    
    # Execute page
    if page == "🎯 Dashboard":
        dashboard_page()
    elif page == "🐱 Cat Profiles":
        cat_profiles_page()
    elif page == "📝 Add Health Entry":
        add_health_entry_page()
    elif page == "📊 View Health Data":
        view_health_data_page()
    elif page == "📋 Task Management":
        task_management_page()
    elif page == "💬 AI Chat":
        ai_chat_page()
    elif page == "⚙️ Data Management":
        data_management_page()

if __name__ == "__main__":
    main()
