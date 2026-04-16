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

# Color scheme
COLORS = {
    'primary': '#222831',
    'secondary': '#393E46', 
    'accent': '#948979',
    'background': '#F5F5F5',
    'text': '#333333',
    'card_bg': '#FFFFFF'
}

def get_styles():
    """Return CSS styles for consistent theming"""
    return f"""
    <style>
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 1rem;
        }}
        .stButton > button {{
            background-color: {COLORS['primary']};
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.25rem;
            font-weight: 500;
        }}
        .stButton > button:hover {{
            background-color: {COLORS['secondary']};
            color: white;
        }}
        .stTextInput > div > div > input, .stNumberInput > div > div > input {{
            border-color: {COLORS['accent']};
        }}
        .stSelectbox > div > div > select {{
            border-color: {COLORS['accent']};
        }}
        .stTabs > div > div > div > button {{
            background-color: {COLORS['secondary']};
            color: white;
        }}
        .stTabs > div > div > div > button[data-selected="true"] {{
            background-color: {COLORS['primary']};
            color: white;
        }}
        .metric-value {{
            color: {COLORS['accent']};
            font-weight: bold;
        }}
        .metric-label {{
            color: {COLORS['text']};
        }}
        .card {{
            background-color: {COLORS['card_bg']};
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid {COLORS['accent']};
        }}
        .cat-card {{
            background: linear-gradient(135deg, {COLORS['card_bg']} 0%, {COLORS['background']} 100%);
            border-radius: 0.75rem;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: 1px solid {COLORS['accent']};
            transition: transform 0.2s ease-in-out;
        }}
        .cat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}
        .cat-name {{
            color: {COLORS['primary']};
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        .cat-info {{
            color: {COLORS['text']};
            margin-bottom: 0.25rem;
        }}
        .cat-details {{
            background-color: {COLORS['background']};
            padding: 1rem;
            border-radius: 0.5rem;
            margin-top: 1rem;
        }}
        .vet-visit {{
            background-color: {COLORS['card_bg']};
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-radius: 0.25rem;
            border-left: 3px solid {COLORS['accent']};
        }}
        .section-title {{
            color: {COLORS['primary']};
            font-size: 1.25rem;
            font-weight: bold;
            margin: 1rem 0 0.5rem 0;
            padding-bottom: 0.25rem;
            border-bottom: 2px solid {COLORS['accent']};
        }}
        .health-summary {{
            background-color: {COLORS['card_bg']};
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            border: 1px solid {COLORS['accent']};
        }}
        .health-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #EEEEEE;
        }}
        .health-item:last-child {{
            border-bottom: none;
        }}
        .health-label {{
            color: {COLORS['text']};
            font-weight: 500;
        }}
        .health-value {{
            color: {COLORS['accent']};
            font-weight: bold;
        }}
        .trend-up {{
            color: #E74C3C;
        }}
        .trend-down {{
            color: #27AE60;
        }}
        .trend-neutral {{
            color: {COLORS['accent']};
        }}
    </style>
    """

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
                            if profile['vet_visits'] and isinstance(profile['vet_visits'], str):
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
    """Proper Hugging Face API call with better error handling"""
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
                generated = result.get('generated_text', '').strip()
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
    """Proper error handling and default values"""
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
    
    # Combine entries from the same date into daily summaries
    daily_summary = {}
    for entry in week_entries:
        entry_date = datetime.fromisoformat(entry['timestamp']).date()
        if entry_date not in daily_summary:
            daily_summary[entry_date] = {
                'water': 0, 'food': 0, 'litter': 0,
                'mood': 'normal', 'medications': [], 'grooming': [], 'notes': []
            }
        
        daily_summary[entry_date]['water'] += entry.get('water_drinks', 0)
        daily_summary[entry_date]['food'] += entry.get('food_eats', 0)
        daily_summary[entry_date]['litter'] += entry.get('litter_box_times', 0)
        
        if entry.get('mood'):
            daily_summary[entry_date]['mood'] = entry['mood']
        
        if entry.get('medication_name'):
            daily_summary[entry_date]['medications'].append(entry['medication_name'])
        
        if entry.get('grooming_tasks'):
            grooming_done = [t for t, done in entry['grooming_tasks'].items() if done]
            daily_summary[entry_date]['grooming'].extend(grooming_done)
        
        if entry.get('notes'):
            daily_summary[entry_date]['notes'].append(entry['notes'])
    
    # Calculate averages
    total_days = len(daily_summary)
    total_water = sum(day['water'] for day in daily_summary.values())
    total_food = sum(day['food'] for day in daily_summary.values())
    total_litter = sum(day['litter'] for day in daily_summary.values())
    
    water_avg = total_water / total_days if total_days > 0 else 0
    food_avg = total_food / total_days if total_days > 0 else 0
    litter_avg = total_litter / total_days if total_days > 0 else 0
    
    # Check for concerns
    concerns = []
    recommendations = []
    
    if water_avg < 2:
        concerns.append('Low water intake detected')
        recommendations.append('Consider adding a water fountain or multiple water sources')
    
    if food_avg < 1:
        concerns.append('Low food intake detected')
        recommendations.append('Monitor appetite and consider feeding schedule adjustments')
    
    if litter_avg > 6:
        concerns.append('High litter box usage detected')
        recommendations.append('Possible digestive issues - monitor for changes')
    
    if total_days < 5:
        concerns.append('Inconsistent health logging')
        recommendations.append('Try to log daily for better health tracking')
    
    # Add profile-specific recommendations
    age = profile.get('age', '')
    if age and 'senior' in age.lower():
        recommendations.append('Senior cats may need more frequent health monitoring')
    
    # Vet history analysis
    vet_history = profile.get('vet_visits', [])
    recent_vet = any(datetime.fromisoformat(visit['date']) > today - timedelta(days=180) for visit in vet_history)
    
    if not recent_vet and total_days > 7:
        concerns.append('No recent vet visits')
        recommendations.append('Schedule a check-up for comprehensive health assessment')
    
    return {
        'status': 'good' if not concerns else 'warning',
        'cat': cat_name,
        'total_entries': len(week_entries),
        'total_days': total_days,
        'water_avg': round(water_avg, 1),
        'food_avg': round(food_avg, 1),
        'litter_usage': round(litter_avg, 1),
        'concerns': concerns,
        'recommendations': recommendations,
        'daily_breakdown': daily_summary,
        'profile': profile,
        'vet_history': vet_history
    }

def generate_cat_summary(cat_name: str) -> str:
    """Generate a comprehensive HTML summary for a cat"""
    analysis = analyze_cat_health(cat_name)
    profile = analysis['profile']
    
    # Cat emoji based on name
    cat_emojis = {'haku': '🐱', 'kuro': '🐈', 'sonic': '🐈‍⬛'}
    cat_emoji = cat_emojis.get(cat_name.lower(), '🐱')
    
    profile_info = []
    if profile.get('age'):
        profile_info.append(f"Age: {profile['age']}")
    if profile.get('breed'):
        profile_info.append(f"Breed: {profile['breed']}")
    if profile.get('weight'):
        profile_info.append(f"Weight: {profile['weight']}")
    
    profile_text = " | ".join(profile_info) if profile_info else "No profile info available"
    
    status_color = COLORS['accent'] if analysis['status'] == 'good' else '#E74C3C'
    
    summary = f"""
    <div class="health-summary">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
            <h3 style="color: {COLORS['primary']}; margin: 0; font-size: 1.5rem;">{cat_emoji} {cat_name}</h3>
            <span style="color: {status_color}; font-weight: bold; padding: 0.25rem 0.75rem; border-radius: 1rem; background-color: {'#D5F4E6' if analysis['status'] == 'good' else '#FDEDEC'};">
                {analysis['status'].title()}
            </span>
        </div>
        <p style="color: {COLORS['text']}; margin-bottom: 1rem;">{profile_text}</p>
        
        <div class="health-item">
            <span class="health-label">📊 Health Entries</span>
            <span class="health-value">{analysis['total_entries']} total</span>
        </div>
        <div class="health-item">
            <span class="health-label">💧 Water Intake</span>
            <span class="health-value">{analysis['water_avg']} cups/day</span>
        </div>
        <div class="health-item">
            <span class="health-label">🍽️ Food Consumption</span>
            <span class="health-value">{analysis['food_avg']} cups/day</span>
        </div>
        <div class="health-item">
            <span class="health-label">🚽 Litter Usage</span>
            <span class="health-value">{analysis['litter_usage']} uses/day</span>
        </div>
        
        <div style="margin-top: 1rem;">
            <h4 style="color: {COLORS['primary']}; margin-bottom: 0.5rem; font-size: 1.1rem;">🏥 Vet History</h4>
    """
    
    if analysis['vet_history']:
        for visit in analysis['vet_history'][-3:]:  # Show last 3 visits
            visit_date = datetime.fromisoformat(visit['date']).strftime('%Y-%m-%d')
            summary += f"""
            <div class="vet-visit">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: {COLORS['text']}; font-weight: 500;">{visit_date}</span>
                    <span style="color: {COLORS['accent']}; font-size: 0.9rem;">{visit.get('purpose', 'Checkup')}</span>
                </div>
                {f'<p style="color: {COLORS['text']}; font-size: 0.9rem; margin: 0.25rem 0 0 0;">{visit.get("notes", "")}</p>' if visit.get('notes') else ''}
            </div>
            """
    else:
        summary += '<p style="color: #999; font-style: italic;">No vet visits recorded</p>'
    
    summary += """
        </div>
    </div>
    """
    
    return summary

# Page: Cat Profiles
def cat_profiles_page():
    st.markdown(get_styles(), unsafe_allow_html=True)
    st.header("🐱 Cat Profiles")
    
    # Add new cat section
    st.subheader("➕ Add New Cat")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        new_cat_name = st.text_input("Cat Name", key="new_cat_name")
    with col2:
        new_cat_age = st.text_input("Age", key="new_cat_age")
    with col3:
        if st.button("Add Cat", key="add_cat_btn"):
            if new_cat_name and new_cat_name not in st.session_state.cats:
                st.session_state.cats.append(new_cat_name)
                st.session_state.cat_profiles[new_cat_name] = {
                    'age': new_cat_age, 'breed': '', 'weight': '', 
                    'vet_visits': [], 'notes': ''
                }
                st.session_state.health_form_data[new_cat_name] = {
                    'water_drinks': 0, 'food_eats': 0, 'litter_box_times': 0,
                    'mood': 'normal', 'medication_name': '', 'medication_dosage': '',
                    'medication_duration': '', 'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
                    'notes': ''
                }
                st.session_state.last_entries[new_cat_name] = None
                save_data()
                st.success(f"Added {new_cat_name}!")
                st.rerun()
    
    st.markdown("---")
    st.subheader("📋 Current Cat Profiles")
    
    # Display cat profiles in cards
    cols = st.columns(1 if len(st.session_state.cats) == 1 else 2 if len(st.session_state.cats) <= 2 else 3)
    
    for i, cat in enumerate(st.session_state.cats):
        col = cols[i % len(cols)]
        
        with col:
            profile = st.session_state.cat_profiles[cat]
            
            st.markdown(f"""
            <div class="cat-card">
                <div class="cat-name">{cat}</div>
                <div class="cat-info">📝 Age: {profile['age'] or 'Not specified'}</div>
                <div class="cat-info">🧬 Breed: {profile['breed'] or 'Not specified'}</div>
                <div class="cat-info">⚖️ Weight: {profile['weight'] or 'Not specified'}</div>
                
                <div class="section-title">🏥 Vet Visits</div>
            """, unsafe_allow_html=True)
            
            if profile['vet_visits']:
                for visit in profile['vet_visits']:
                    visit_date = datetime.fromisoformat(visit['date']).strftime('%Y-%m-%d')
                    st.markdown(f"""
                    <div class="vet-visit">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: {COLORS['text']}; font-weight: 500;">{visit_date}</span>
                            <span style="color: {COLORS['accent']}; font-size: 0.9rem;">{visit.get('purpose', 'Checkup')}</span>
                        </div>
                        {f'<p style="color: {COLORS['text']}; font-size: 0.9rem; margin: 0.25rem 0 0 0;">{visit.get("notes", "")}</p>' if visit.get('notes') else ''}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #999; font-style: italic;">No vet visits recorded</p>', unsafe_allow_html=True)
            
            st.markdown("""
                <div class="section-title">📝 Notes</div>
                <div class="cat-details">
            """, unsafe_allow_html=True)
            
            if profile.get('notes'):
                st.markdown(f'<p style="color: {COLORS['text']}; margin: 0;">{profile["notes"]}</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #999; font-style: italic;">No notes added</p>', unsafe_allow_html=True)
            
            st.markdown("""
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Edit profile button
            if st.button("✏️ Edit Profile", key=f"edit_profile_{cat}"):
                st.session_state.editing_cat = cat
                st.session_state.edit_profile_data = profile.copy()
                st.rerun()
    
    # Handle profile editing
    if 'editing_cat' in st.session_state and st.session_state.editing_cat:
        cat = st.session_state.editing_cat
        profile_data = st.session_state.edit_profile_data
        
        st.subheader(f"✏️ Edit {cat}'s Profile")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            new_age = st.text_input("Age", value=profile_data['age'], key=f"edit_age_{cat}")
        with col2:
            new_breed = st.text_input("Breed", value=profile_data['breed'], key=f"edit_breed_{cat}")
        with col3:
            new_weight = st.text_input("Weight", value=profile_data['weight'], key=f"edit_weight_{cat}")
        
        st.subheader("🏥 Add Vet Visit")
        col1, col2 = st.columns(2)
        with col1:
            visit_date = st.date_input("Visit Date", value=date.today(), key=f"visit_date_{cat}")
        with col2:
            visit_purpose = st.text_input("Purpose", key=f"visit_purpose_{cat}")
        
        visit_notes = st.text_area("Visit Notes", key=f"visit_notes_{cat}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Add Vet Visit", key=f"add_visit_{cat}"):
                if visit_purpose:
                    new_visit = {
                        'date': visit_date.isoformat(),
                        'purpose': visit_purpose,
                        'notes': visit_notes
                    }
                    st.session_state.cat_profiles[cat]['vet_visits'].append(new_visit)
                    save_data()
                    st.success("Added vet visit!")
                    st.rerun()
        
        with col2:
            if st.button("Cancel", key=f"cancel_edit_{cat}"):
                del st.session_state.editing_cat
                del st.session_state.edit_profile_data
                st.rerun()
        
        st.subheader("📝 Profile Notes")
        new_notes = st.text_area("Notes", value=profile_data.get('notes', ''), key=f"edit_notes_{cat}")
        
        if st.button("Save Profile", key=f"save_profile_{cat}"):
            st.session_state.cat_profiles[cat].update({
                'age': new_age,
                'breed': new_breed,
                'weight': new_weight,
                'notes': new_notes
            })
            save_data()
            st.success(f"Updated {cat}'s profile!")
            del st.session_state.editing_cat
            del st.session_state.edit_profile_data
            st.rerun()

# Page: Add Health Entry
def add_health_entry_page():
    st.header("📝 Add Health Entry")
    
    # Cat selection
    selected_cat = st.selectbox("Select Cat", st.session_state.cats)
    
    # Get current form data or initialize
    if selected_cat not in st.session_state.health_form_data:
        st.session_state.health_form_data[selected_cat] = {
            'water_drinks': 0, 'food_eats': 0, 'litter_box_times': 0,
            'mood': 'normal', 'medication_name': '', 'medication_dosage': '',
            'medication_duration': '', 'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
            'notes': ''
        }
    
    form_data = st.session_state.health_form_data[selected_cat]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Basic Metrics")
        water = st.number_input("Water Drinks", min_value=0, value=form_data['water_drinks'])
        food = st.number_input("Food Eats", min_value=0, value=form_data['food_eats'])
        litter = st.number_input("Litter Box Times", min_value=0, value=form_data['litter_box_times'])
        mood = st.selectbox("Mood", ['normal', 'happy', 'sad', 'sick', 'aggressive'], 
                           index=['normal', 'happy', 'sad', 'sick', 'aggressive'].index(form_data['mood']))
    
    with col2:
        st.subheader("💊 Medication")
        med_name = st.text_input("Medication Name", value=form_data['medication_name'])
        med_dosage = st.text_input("Dosage", value=form_data['medication_dosage'])
        med_duration = st.text_input("Duration (days)", value=form_data['medication_duration'])
    
    st.subheader("🪥 Grooming Tasks")
    grooming_tasks = {}
    col1, col2, col3 = st.columns(3)
    with col1:
        grooming_tasks['Brush fur'] = st.checkbox("Brush fur", value=form_data['grooming_tasks']['Brush fur'])
    with col2:
        grooming_tasks['Trim nails'] = st.checkbox("Trim nails", value=form_data['grooming_tasks']['Trim nails'])
    with col3:
        grooming_tasks['Clean ears'] = st.checkbox("Clean ears", value=form_data['grooming_tasks']['Clean ears'])
    
    st.subheader("📝 Notes")
    notes = st.text_area("Additional Notes", value=form_data['notes'])
    
    if st.button("Save Health Entry", key="save_health_entry"):
        entry_data = {
            'cat': selected_cat,
            'water_drinks': water,
            'food_eats': food,
            'litter_box_times': litter,
            'mood': mood,
            'medication_name': med_name,
            'medication_dosage': med_dosage,
            'medication_duration': med_duration,
            'grooming_tasks': grooming_tasks,
            'notes': notes
        }
        
        add_health_entry(selected_cat, entry_data)
        
        # Reset form data for this cat
        st.session_state.health_form_data[selected_cat] = {
            'water_drinks': 0, 'food_eats': 0, 'litter_box_times': 0,
            'mood': 'normal', 'medication_name': '', 'medication_dosage': '',
            'medication_duration': '', 'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
            'notes': ''
        }
        
        st.success(f"Health entry saved for {selected_cat}!")
        st.rerun()

# Page: View Health Data
def view_health_data_page():
    st.header("📊 View Health Data")
    
    # Cat selection and date range
    col1, col2 = st.columns(2)
    with col1:
        selected_cat = st.selectbox("Select Cat", st.session_state.cats)
    with col2:
        date_range = st.date_input(
            "Select Date Range",
            [date.today() - timedelta(days=30), date.today()],
            key="health_date_range"
        )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        st.error("Please select both start and end dates")
        return
    
    # Get health entries for the selected cat and date range
    entries = get_health_entries(selected_cat, start_date, end_date)
    
    if not entries:
        st.info(f"No health entries found for {selected_cat} in the selected date range.")
        return
    
    # Convert to DataFrame for better display
    df_data = []
    for entry in entries:
        entry_date = datetime.fromisoformat(entry['timestamp']).date()
        df_data.append({
            'date': entry_date,
            'water_drinks': entry.get('water_drinks', 0),
            'food_eats': entry.get('food_eats', 0),
            'litter_box_times': entry.get('litter_box_times', 0),
            'mood': entry.get('mood', 'normal'),
            'medication_name': entry.get('medication_name', ''),
            'medication_dosage': entry.get('medication_dosage', ''),
            'medication_duration': entry.get('medication_duration', ''),
            'grooming_tasks': entry.get('grooming_tasks', {}),
            'notes': entry.get('notes', '')
        })
    
    df = pd.DataFrame(df_data)
    df = df.sort_values('date')
    
    # Display summary statistics
    st.subheader(f"📈 {selected_cat} - Health Summary ({start_date} to {end_date})")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Water", f"{df['water_drinks'].mean():.1f} cups/day")
    with col2:
        st.metric("Average Food", f"{df['food_eats'].mean():.1f} cups/day")
    with col3:
        st.metric("Average Litter", f"{df['litter_box_times'].mean():.1f} uses/day")
    
    # Display entries in a styled table
    st.subheader("📋 Detailed Entries")
    
    for idx, entry in enumerate(entries):
        entry_date = datetime.fromisoformat(entry['timestamp']).date()
        
        st.markdown(f"""
        <div class="card">
            <h4 style="color: {COLORS['primary']}; margin: 0 0 0.5rem 0;">{entry_date}</h4>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns()
        
        with col1:
            st.write(f"💧 Water: {entry.get('water_drinks', 0)} cups")
            st.write(f"🍽️ Food: {entry.get('food_eats', 0)} cups")
            st.write(f"🚽 Litter: {entry.get('litter_box_times', 0)} uses")
            st.write(f"😊 Mood: {entry.get('mood', 'normal')}")
            
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
        
        st.markdown("</div>", unsafe_allow_html=True)
    
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

# Page: Dashboard - Enhanced with AI integration
def dashboard_page():
    st.markdown(get_styles(), unsafe_allow_html=True)
    st.header("🎯 Dashboard")
    
    # AI Summary Section
    st.subheader("🤖 AI Health Summary")
    
    # Prepare data for AI analysis
    cat_data = {
        'cats': st.session_state.cats,
        'health_data': st.session_state.health_data,
        'profiles': st.session_state.cat_profiles
    }
    
    # Generate AI-powered comprehensive summary
    ai_prompt = f"""
    Provide a comprehensive health summary for {len(st.session_state.cats)} cats: {', '.join(st.session_state.cats)}.
    Include overall health assessment, trends, concerns, and recommendations.
    Focus on:
    - Overall health status of each cat
    - Any concerning patterns in health data
    - Positive observations and improvements
    - Specific recommendations for each cat based on their profile and recent data
    - General cat care tips that might be helpful
    
    Keep it concise but informative, like a vet summary.
    """
    
    if HF_API_KEY:
        with st.spinner("Generating AI summary..."):
            ai_summary = call_huggingface_ai(ai_prompt, st.session_state.chat_messages, cat_data)
    else:
        ai_summary = "🤖 AI summary unavailable - add HF_API_KEY to enable intelligent health insights."
    
    st.markdown(f"""
    <div class="card">
        <h4 style="color: {COLORS['primary']}; margin: 0 0 1rem 0;">📋 Overall Health Assessment</h4>
        <p style="color: {COLORS['text']}; line-height: 1.6; margin: 0;">{ai_summary}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Quick Overview Metrics
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
    
    st.markdown("---")
    
    # Detailed Cat Health Summaries
    st.subheader("🐱 Detailed Cat Health Reports")
    
    # Analysis for each cat
    cat_analyses = {}
    for cat in st.session_state.cats:
        cat_analyses[cat] = analyze_cat_health(cat)
    
    # Display comprehensive summaries
    for cat, analysis in cat_analyses.items():
        st.markdown(generate_cat_summary(cat), unsafe_allow_html=True)
        
        # Add detailed insights
        if analysis['daily_breakdown']:
            st.markdown(f"""
            <div class="card">
                <h4 style="color: {COLORS['primary']}; margin: 0 0 1rem 0;">📈 Recent Daily Breakdown</h4>
                <div style="max-height: 200px; overflow-y: auto;">
            """, unsafe_allow_html=True)
            
            for day, data in list(analysis['daily_breakdown'].items())[-7:]:  # Show last 7 days
                day_str = day.strftime('%Y-%m-%d')
                st.markdown(f"""
                <div style="background-color: {COLORS['background']}; padding: 0.5rem; margin-bottom: 0.25rem; border-radius: 0.25rem;">
                    <strong style="color: {COLORS['primary']};">{day_str}</strong><br>
                    <span style="color: {COLORS['text']};">💧 {data['water']} cups | 🍽️ {data['food']} cups | 🚽 {data['litter']} uses</span>
                    {f'<br><span style="color: {COLORS['accent']};">🏥 {", ".join(set(data["medications"]))}</span>' if data['medications'] else ''}
                    {f'br><span< style="color: {COLORS['accent']};">🪥 {", ".join(set(data["grooming"]))}</span>' if data['grooming'] else ''}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True)
        
        # Show concerns and recommendations
        if analysis['concerns'] or analysis['recommendations']:
            st.markdown(f"""
            <div class="card">
                <h4 style="color: {COLORS['primary']}; margin: 0 0 1rem 0;">⚠️ Health Insights</h4>
            """, unsafe_allow_html=True)
            
            if analysis['concerns']:
                st.markdown("<strong style='color: #E74C3C;'>Concerns:</strong>", unsafe_allow_html=True)
                for concern in analysis['concerns']:
                    st.markdown(f"• {concern}", unsafe_allow_html=True)
            
            if analysis['recommendations']:
                st.markdown("<br><strong style='color: {COLORS['accent']};'>Recommendations:</strong>", unsafe_allow_html=True)
                for rec in analysis['recommendations']:
                    st.markdown(f"• {rec}", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Overall statistics
    st.subheader("📊 Overall Statistics")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        total_water_avg = sum(anal['water_avg'] for anal in cat_analyses.values()) / len(cat_analyses)
        st.metric("Avg Water Intake", f"{total_water_avg:.1f} cups/day")
    with col2:
        total_food_avg = sum(anal['food_avg'] for anal in cat_analyses.values()) / len(cat_analyses)
        st.metric("Avg Food Consumption", f"{total_food_avg:.1f} cups/day")
    with col3:
        total_litter_avg = sum(anal['litter_usage'] for anal in cat_analyses.values()) / len(cat_analyses)
        st.metric("Avg Litter Usage", f"{total_litter_avg:.1f} uses/day")

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
                'water_drinks': 0, 'food_eats': 0, 'litter_box_times': 0,
                'mood': 'normal', 'medication_name': '', 'medication_dosage': '',
                'medication_duration': '', 'grooming_tasks': {'Brush fur': False, 'Trim nails': False, 'Clean ears': False},
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
        col1, col2 = st.columns()
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
         "📋 Task Management", "🎯 Dashboard", "⚙️ Data Management"]
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
    elif page == "🎯 Dashboard":
        dashboard_page()
    elif page == "⚙️ Data Management":
        data_management_page()

if __name__ == "__main__":
    main()
