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

# Hugging Face AI Integration
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

    # Form state management for different cats
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
                'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
                'notes': ''
            }

# Data persistence functions
def save_data():
    try:
        health_data_str = json.dumps(st.session_state.health_data, default=str)
        task_logs_str = json.dumps(st.session_state.task_logs, default=str)
        profiles_str = json.dumps(st.session_state.cat_profiles, default=str)
        
        if AUTH_ENABLED:
            health_data_str = encrypt_data(health_data_str)
            task_logs_str = encrypt_data(task_logs_str)
            profiles_str = encrypt_data(profiles_str)
        
        with open('health_data.json', 'w') as f:
            f.write(health_data_str)
        with open('task_logs.json', 'w') as f:
            f.write(task_logs_str)
        with open('cat_profiles.json', 'w') as f:
            f.write(profiles_str)
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

# AI Integration
def call_huggingface_ai(user_message: str, chat_history: list, cat_data: Dict = None) -> str:
    """FIXED: Proper Hugging Face API call with better error handling"""
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
    
    # Add specific responses for your cats
    if 'haku' in msg_lower:
        responses[('haku',)] = "🐱 Haku is your 1.7-year-old domestic shorthair. Monitor his FHV-1 symptoms and watch for eye discharge or sneezing."
    if 'kuro' in msg_lower:
        responses[('kuro',)] = "🐱 Kuro is your 1.7-year-old domestic shorthair. Keep track of his daily habits and litter box usage."
    if 'sonic' in msg_lower:
        responses[('sonic',)] = "🐱 Sonic is your 11-month-old domestic longhair. Regular grooming is important for his long fur."
    
    for keywords, response in responses.items():
        if any(word in msg_lower for word in keywords):
            return response
    
    return "🐱 I can help with feeding, water, litter, grooming, vet care, or play. What would you like to know about your cats?"

# Health Analysis Functions
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
    
    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h4 style="margin: 0 0 10px 0; color: #495057;">📋 Profile Information</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>strong>Age:</<strong> {profile.get('age', 'Not set')}</div>
            <div>strong>Breed:</<strong> {profile.get('breed', 'Not set')}</div>
            <div><strong>Weight:</strong> {profile.get('weight', 'Not set')}</div>
            <div><strong>Vet Visits:</strong> {len(profile.get('vet_visits', []))}</div>
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

# Page: Cat Profiles - FIXED
def cat_profiles_page():
    st.header("🐱 Cat Profiles")
    
    # Add new cat button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("Your Cats")
    with col2:
        if len(st.session_state.cats) < 5:
            if st.button("➕ Add Cat", use_container_width=True):
                st.session_state.cats.append(f"New Cat {len(st.session_state.cats) + 1}")
                st.session_state.cat_profiles[f"New Cat {len(st.session_state.cats)}"] = {
                    'age': '', 'breed': '', 'weight': '', 
                    'vet_visits': [], 'notes': ''
                }
                # Add new cat to health form data
                st.session_state.health_form_data[f"New Cat {len(st.session_state.cats)}"] = {
                    'water_drinks': 0,
                    'food_eats': 0,
                    'litter_box_times': 0,
                    'mood': 'normal',
                    'medication_name': '',
                    'medication_dosage': '',
                    'medication_duration': '',
                    'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
                    'notes': ''
                }
                save_data()
                st.rerun()
    
    # Display cat profiles in cards
    cols = st.columns(len(st.session_state.cats))
    
    for i, cat in enumerate(st.session_state.cats):
        with cols[i]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; margin-bottom: 15px;">
                <h3 style="margin: 0; font-size: 20px;">🐱 {cat}</h3>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 15px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                    <div><strong>Age:</strong> {st.session_state.cat_profiles[cat]['age'] or 'Not set'}</div>
                    <div>strong>Breed:</<strong> {st.session_state.cat_profiles[cat]['breed'] or 'Not set'}</div>
                    <div>strong>Weight:</<strong> {st.session_state.cat_profiles[cat]['weight'] or 'Not set'}</div>
                    <div><strong>Vet Visits:</strong> {len(st.session_state.cat_profiles[cat]['vet_visits'])}</div>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <strong>Notes:</strong><br>
                    {st.session_state.cat_profiles[cat]['notes'] or 'No notes yet'}
                </div>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <button onclick="window.location.href='#edit_profile_{cat}'" style="background: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">🏥 Add Visit</button>
                <button onclick="window.location.href='#edit_profile_{cat}'" style="background: #2ecc71; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">✏️ Edit Profile</button>
            </div>
            """, unsafe_allow_html=True)
    
    # Edit profile section
    st.markdown("---")
    st.subheader("✏️ Edit Cat Profiles")
    
    cat_to_edit = st.selectbox("Select cat to edit", [""] + st.session_state.cats, key="edit_cat_select")
    
    if cat_to_edit:
        st.markdown(f"### Editing: {cat_to_edit}")
        
        with st.form(f"edit_profile_{cat_to_edit}"):
            col1, col2 = st.columns(2)
            
            with col1:
                age = st.text_input("Age", value=st.session_state.cat_profiles[cat_to_edit]['age'])
                breed = st.text_input("Breed", value=st.session_state.cat_profiles[cat_to_edit]['breed'])
                weight = st.text_input("Weight (kg)", value=st.session_state.cat_profiles[cat_to_edit]['weight'])
            
            with col2:
                notes = st.text_area("Notes", value=st.session_state.cat_profiles[cat_to_edit]['notes'])
            
            # Vet visit section
            st.subheader("🏥 Vet Visits")
            
            # Display existing vet visits
            existing_visits = st.session_state.cat_profiles[cat_to_edit]['vet_visits']
            if existing_visits:
                st.write("**Existing Visits:**")
                for j, visit in enumerate(existing_visits):
                    col_a, col_b = st.columns([2, 3])
                    with col_a:
                        st.write(f"**{visit['date']}**")
                    with col_b:
                        st.write(visit.get('notes', 'No notes'))
                    if st.button("🗑️", key=f"delete_visit_{cat_to_edit}_{j}"):
                        st.session_state.cat_profiles[cat_to_edit]['vet_visits'].pop(j)
                        save_data()
                        st.rerun()
            
            # Add new vet visit
            st.write("**Add New Visit:**")
            visit_date = st.date_input("Visit Date", value=date.today())
            visit_notes = st.text_area("Visit Notes")
            visit_cost = st.number_input("Cost (optional)", min_value=0.0, step=0.01)
            
            if st.form_submit_button("Save Profile"):
                st.session_state.cat_profiles[cat_to_edit] = {
                    'age': age,
                    'breed': breed,
                    'weight': weight,
                    'vet_visits': existing_visits,
                    'notes': notes
                }
                
                if visit_notes:
                    st.session_state.cat_profiles[cat_to_edit]['vet_visits'].append({
                        'date': str(visit_date),
                        'notes': visit_notes,
                        'cost': visit_cost
                    })
                
                save_data()
                st.success(f"✅ Profile saved for {cat_to_edit}")
                st.rerun()

# Page: Add Health Entry - FIXED
def add_health_entry_page():
    st.header("📝 Add Health Entry")
    
    # FIXED: Add callback to reset form when cat changes
    def on_cat_change():
        # Reset form data for the new cat
        st.session_state.health_form_data = st.session_state.health_form_data
    
    cat_selector = st.selectbox(
        "Select Cat", 
        st.session_state.cats, 
        key="cat_selector",
        on_change=on_cat_change
    )
    
    # FIXED: Load cat-specific form data
    form_data = st.session_state.health_form_data.get(cat_selector, {
        'water_drinks': 0,
        'food_eats': 0,
        'litter_box_times': 0,
        'mood': 'normal',
        'medication_name': '',
        'medication_dosage': '',
        'medication_duration': '',
        'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
        'notes': ''
    })
    
    # Date selection
    entry_date = st.date_input("Date", value=date.today())
    
    # Health metrics
    col1, col2 = st.columns(2)
    
    with col1:
        water_drinks = st.number_input("💧 Water Drinks", min_value=0, max_value=10, value=form_data['water_drinks'])
        food_eats = st.number_input("🍽️ Food Eats", min_value=0, max_value=10, value=form_data['food_eats'])
        litter_box_times = st.number_input("🚽 Litter Box Uses", min_value=0, max_value=10, value=form_data['litter_box_times'])
    
    with col2:
        mood = st.selectbox("😊 Mood", ["happy", "normal", "sad", "sick", "tired"], index=["happy", "normal", "sad", "sick", "tired"].index(form_data['mood']))
        medication_name = st.text_input("💊 Medication Name", value=form_data['medication_name'])
        medication_dosage = st.text_input("💊 Medication Dosage", value=form_data['medication_dosage'])
        medication_duration = st.text_input("💊 Duration (e.g., 1 week)", value=form_data['medication_duration'])
    
    # Grooming tasks
    st.subheader("🪥 Grooming Tasks")
    grooming_tasks = {}
    for task in ['Brush fur', 'Trim nails', 'Clean ears']:
        grooming_tasks[task] = st.checkbox(task, value=form_data['grooming_tasks'].get(task, False))
    
    # Additional notes
    notes = st.text_area("📝 Additional Notes", value=form_data['notes'])
    
    if st.button("💾 Add Entry", type="primary"):
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
        
        # FIXED: Update form data for this cat
        st.session_state.health_form_data[cat_selector] = {
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
        
        st.success(f"✅ Health entry added for {cat_selector}")
        st.rerun()

# Page: View Health Data
def view_health_data_page():
    st.header("📊 View Health Data")
    
    cat_selector = st.selectbox("Select Cat", ["All"] + st.session_state.cats)
    
    # Date range selection
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=7))
    
    with col2:
        end_date = st.date_input("End Date", value=date.today())
    
    # Get entries
    if cat_selector == "All":
        all_entries = []
        for cat in st.session_state.cats:
            entries = get_health_entries(cat, start_date, end_date)
            for entry in entries:
                entry['cat'] = cat
            all_entries.extend(entries)
    else:
        all_entries = get_health_entries(cat_selector, start_date, end_date)
        for entry in all_entries:
            entry['cat'] = cat_selector
    
    if not all_entries:
        st.info("No health entries found for the selected criteria.")
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_entries)
    
    # Display entries
    st.subheader(f"Health Entries ({len(all_entries)} found)")
    
    # Edit/Delete functionality
    st.write("Click on any entry to edit or delete:")
    
    for idx, entry in enumerate(all_entries):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{entry['cat']} - {entry['date']}**")
            st.write(f"💧 Water: {entry.get('water_drinks', 'N/A')} drinks | 🍽️ Food: {entry.get('food_eats', 'N/A')} eats")
            st.write(f"🚽 Litter: {entry.get('litter_box_times', 'N/A')} times | 😊 Mood: {entry.get('mood', 'N/A')}")
            if entry.get('medication_name'):
                duration = entry.get('medication_duration', entry.get('medication_dosage', 'N/A'))
                st.write(f"💊 Medication: {entry['medication_name']} ({duration})")
            grooming_done = [t for t, done in entry.get('grooming_tasks', {}).items() if done]
            if grooming_done:
                st.write(f"🪥 Grooming: {', '.join(grooming_done)}")
            if entry.get('notes'):
                st.write(f"📝 Notes: {entry['notes']}")
        
        with col2:
            if st.button("✏️ Edit", key=f"edit_entry_{idx}"):
                st.session_state.editing_health_entry = True
                st.session_state.edit_entry_data = {'timestamp': entry['timestamp'], 'index': idx}
                st.session_state.edit_entry_cat = entry['cat']
                st.rerun()
        
        with col3:
            if st.button("🗑️ Delete", key=f"delete_entry_{idx}"):
                delete_health_entry(entry['cat'], entry['timestamp'], idx)
                st.success("Entry deleted!")
                st.rerun()
    
    st.subheader("📊 Health Trends")
    if len(df) > 1:
        fig = make_subplots(rows=2, cols=2,
                            subplot_titles=('Water Intake', 'Food Intake', 'Litter Box Usage', ''),
                            specs=[[{}, {}], [{}, {}]])
        if 'water_drinks' in df.columns:
            fig.add_trace(go.Scatter(x=df['date'], y=df['water_drinks'], name='Water Drinks'), row=1, col=1)
        if 'food_eats' in df.columns:
            fig.add_trace(go.Scatter(x=df['date'], y=df['food_eats'], name='Food Eats'), row=1, col=2)
        if 'litter_box_times' in df.columns:
            fig.add_trace(go.Scatter(x=df['date'], y=df['litter_box_times'], name='Litter Box Uses'), row=2, col=1)
        fig.update_layout(height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

# Page: Task Management
def task_management_page():
    st.header("📋 Task Management")

    frequencies = ['daily', 'weekly', 'monthly']
    freq_names  = ['📅 Daily', '🗓️ Weekly', '📆 Monthly']

    for freq, freq_name in zip(frequencies, freq_names):
        st.markdown(f"### {freq_name}")

        if not st.session_state.tasks[freq]:
            st.info(f"No {freq} tasks.")
            continue

        today = str(date.today())
        completed_today = []
        if today in st.session_state.task_logs:
            completed_today = [log['task'] for log in st.session_state.task_logs[today]]

        for task in st.session_state.tasks[freq]:
            already_done = task in completed_today
            checked = st.checkbox(task, value=already_done, key=f"task_{freq}_{task}")
            if checked and not already_done:
                add_task_completion(task)
                st.rerun()

        st.markdown("")

    # ── Completion history ──
    st.markdown("---")
    st.subheader("📋 Task Completion History")

    col1, col2 = st.columns(2)
    with col1:
        history_start = st.date_input("Start Date", date.today() - timedelta(days=7))
    with col2:
        history_end = st.date_input("End Date", date.today())

    completions = get_task_completions(history_start, history_end)

    if not completions:
        st.info("No task completions found in the selected date range.")
        return

    all_completions = []
    for date_str, day_logs in completions.items():
        for log in day_logs:
            all_completions.append({
                'date': date_str, 'task': log['task'],
                'cat': log['cat'], 'completed_at': log['completed_at'],
                'notes': log['notes']
            })

    df = pd.DataFrame(all_completions)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    st.dataframe(df, use_container_width=True, hide_index=True)

# Page: AI Chat - FIXED with history passing
def ai_chat_page():
    st.header("💬 AI Cat Care Assistant")

    if HF_API_KEY:
        st.success("🤖 Connected to Hugging Face — Mistral-7B-Instruct")
    else:
        st.warning("⚠️ No HF_API_KEY found — using rule-based responses. Add your key in Streamlit Secrets.")

    st.write("Ask anything about your cats' care, health, or behaviour!")

    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_messages = []
        st.rerun()

    # Display history
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input
    if prompt := st.chat_input("Ask me about cat care..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        cat_data = {
            'cats': st.session_state.cats,
            'health_data': st.session_state.health_data,
            'profiles': st.session_state.cat_profiles
        }

        # Pass full history so model remembers context and doesn't repeat
        ai_response = call_huggingface_ai(prompt, st.session_state.chat_messages, cat_data)
        st.session_state.chat_messages.append({"role": "assistant", "content": ai_response})
        st.rerun()

# Page: Dashboard - FIXED with combined daily entries
def dashboard_page():
    st.header("🎯 Dashboard")
    st.subheader("📊 Quick Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_entries = sum(
            len(dates)
            for cat_data in st.session_state.health_data.values()
            for dates in cat_data.values()
        )
        st.metric("Total Entries", total_entries)
    with col2:
        today = str(date.today())
        today_tasks = []
        if today in st.session_state.task_logs:
            today_tasks = [log['task'] for log in st.session_state.task_logs[today]]
        st.metric("Today's Tasks Done", len(today_tasks))
    with col3:
        total_vet = sum(len(p.get('vet_visits', [])) for p in st.session_state.cat_profiles.values())
        st.metric("Vet Visits", total_vet)
    with col4:
        active = sum(1 for cat in st.session_state.cats
                     if cat in st.session_state.health_data and st.session_state.health_data[cat])
        st.metric("Active Cats", active)
    
    st.subheader("🐱 Cat Health Summaries")
    cat_tabs = st.tabs(st.session_state.cats)
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            # Use unsafe_allow_html=True to display HTML content properly
            st.markdown(generate_cat_summary(cat), unsafe_allow_html=True)

# Page: Data Management
def data_management_page():
    st.header("⚙️ Data Management")
    st.warning("⚠️ **Caution:** Actions on this page can permanently delete your data!")
    
    st.markdown("---")
    st.subheader("📥 Export Data")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📥 Export Health Data", use_container_width=True):
            health_json = json.dumps(st.session_state.health_data, indent=2, default=str)
            st.download_button("💾 Download Health Data", data=health_json,
                               file_name=f"health_data_{date.today()}.json", mime="application/json")
    with col2:
        if st.button("📥 Export Task Logs", use_container_width=True):
            tasks_json = json.dumps(st.session_state.task_logs, indent=2, default=str)
            st.download_button("💾 Download Task Logs", data=tasks_json,
                               file_name=f"task_logs_{date.today()}.json", mime="application/json")
    with col3:
        if st.button("📥 Export Profiles", use_container_width=True):
            profiles_json = json.dumps(st.session_state.cat_profiles, indent=2, default=str)
            st.download_button("💾 Download Profiles", data=profiles_json,
                               file_name=f"cat_profiles_{date.today()}.json", mime="application/json")
    
    st.markdown("---")
    st.subheader("🗑️ Delete Specific Data")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Delete Health Data for a Cat:**")
        cat_to_delete = st.selectbox("Select cat", [""] + st.session_state.cats, key="delete_cat_health")
        if cat_to_delete:
            if st.button(f"🗑️ Delete {cat_to_delete}'s Health Data", type="secondary"):
                if cat_to_delete in st.session_state.health_data:
                    del st.session_state.health_data[cat_to_delete]
                    save_data()
                    st.success(f"✅ Deleted health data for {cat_to_delete}")
                    st.rerun()
                else:
                    st.info(f"No health data found for {cat_to_delete}")
    with col2:
        st.write("**Delete Task Logs for a Date Range:**")
        del_start = st.date_input("Start Date", key="delete_task_start")
        del_end   = st.date_input("End Date",   key="delete_task_end")
        if st.button("🗑️ Delete Task Logs", type="secondary"):
            deleted = 0
            current = del_start
            while current <= del_end:
                ds = str(current)
                if ds in st.session_state.task_logs:
                    del st.session_state.task_logs[ds]
                    deleted += 1
                current += timedelta(days=1)
            save_data()
            st.success(f"✅ Deleted task logs for {deleted} days")
            st.rerun()
    
    st.markdown("---")
    st.subheader("🚨 Delete All Data")
    st.error("**WARNING:** This permanently deletes ALL data!")
    confirm_delete = st.checkbox("I understand this action cannot be undone", key="confirm_delete_all")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Delete ALL Health Data", type="secondary", disabled=not confirm_delete):
            st.session_state.health_data = {}
            st.session_state.last_entries = {cat: None for cat in st.session_state.cats}
            save_data()
            st.success("✅ All health data deleted!")
            st.rerun()
    with col2:
        if st.button("🗑️ Delete ALL Task Logs", type="secondary", disabled=not confirm_delete):
            st.session_state.task_logs = {}
            save_data()
            st.success("✅ All task logs deleted!")
            st.rerun()
    
    st.markdown("---")
    st.subheader("🔄 Complete Reset")
    st.error("**DANGER ZONE:** Resets EVERYTHING including profiles!")
    confirm_reset = st.checkbox("I want to completely reset the application", key="confirm_reset")
    if st.button("🔄 RESET EVERYTHING", type="secondary", disabled=not confirm_reset):
        st.session_state.health_data = {}
        st.session_state.task_logs = {}
        st.session_state.cat_profiles = {
            cat: {'age': '', 'breed': '', 'weight': '', 'vet_visits': [], 'notes': ''}
            for cat in st.session_state.cats
        }
        st.session_state.last_entries = {cat: None for cat in st.session_state.cats}
        st.session_state.chat_messages = []
        # Also reset health form data
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
                'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
                'notes': ''
            }
        for fname in ['health_data.json', 'task_logs.json', 'cat_profiles.json']:
            try:
                if os.path.exists(fname):
                    os.remove(fname)
            except:
                pass
        st.success("✅ Application completely reset!")
        time.sleep(1)
        st.rerun()
    
    st.markdown("---")
    st.subheader("📊 Data Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        total_health = sum(len(d) for cat_data in st.session_state.health_data.values() for d in cat_data.values())
        st.metric("Total Health Entries", total_health)
    with col2:
        total_tasks = sum(len(logs) for logs in st.session_state.task_logs.values())
        st.metric("Total Task Completions", total_tasks)
    with col3:
        total_vet = sum(len(p.get('vet_visits', [])) for p in st.session_state.cat_profiles.values())
        st.metric("Total Vet Visits", total_vet)

# Reminders
def check_reminders():
    current_time = datetime.now()
    if (st.session_state.last_reminder is None or
            (current_time - st.session_state.last_reminder).days >= 1):
        
        missing = [cat for cat in st.session_state.cats
                   if st.session_state.last_entries[cat] is None or
                   (current_time - st.session_state.last_entries[cat]).days >= 1]
        if missing:
            st.warning(f"⚠️ Reminder: No health entries for {', '.join(missing)} today!")
        
        today_str = str(date.today())
        if today_str not in st.session_state.task_logs:
            st.session_state.task_logs[today_str] = []
        
        done = [log['task'] for log in st.session_state.task_logs[today_str]]
        incomplete = [t for t in st.session_state.tasks['daily'] if t not in done]
        if incomplete:
            st.info(f"📝 Incomplete daily tasks: {', '.join(incomplete)}")
        
        st.session_state.last_reminder = current_time

# Main
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
            st.write("Comprehensive health and task management for your beloved cats")
        with col2:
            st.write(f"👤 {st.session_state.username}")
            if st.button("🚪 Logout", key="logout_button"):
                logout()
    else:
        st.write("Comprehensive health and task management for your beloved cats")
    
    st.sidebar.title("🧭 Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🐱 Cat Profiles", "📝 Add Health Entry", "📊 View Health Data",
         "📋 Task Management", "💬 AI Chat", "🎯 Dashboard", "⚙️ Data Management"]
    )
    
    if AUTH_ENABLED:
        st.sidebar.success("🔐 Security: Enabled")
    else:
        st.sidebar.warning("⚠️ Security: Disabled")
    
    if HF_API_KEY:
        st.sidebar.success("🤖 AI: Mistral-7B Connected")
        st.sidebar.caption("Hugging Face Inference API")
    else:
        st.sidebar.info("🤖 AI: Rule-based Mode")
        st.sidebar.caption("Add HF_API_KEY in secrets")
    
    check_reminders()
    
    if page == "🐱 Cat Profiles":
        cat_profiles_page()
    elif page == "📝 Add Health Entry":
        add_health_entry_page()
    elif page == "📊 View Health Data":
        view_health_data_page()
    elif page == "📋 Task Management":
        task_management_page()
    elif page == "💬 AI Chat":
        ai_chat_page()
    elif page == "🎯 Dashboard":
        dashboard_page()
    elif page == "⚙️ Data Management":
        data_management_page()

if __name__ == "__main__":
    main()
