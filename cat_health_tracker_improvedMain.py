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
    st.warning("⚠️ auth_module.py not found. Authentication disabled. Upload auth_module.py to enable security.")

# Hugging Face AI Integration
try:
    import requests
    HF_API_KEY = st.secrets.get("HF_API_KEY", None)
    if HF_API_KEY:
        HF_BASE_URL = "https://api-inference.huggingface.co/models"
        # Using a more reliable chat/instruction model on the free HF API
        HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
    else:
        HF_API_KEY = None
except ImportError:
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
                'Let them out my room', 'Leave them alone', 'Pray for them'
            ],
            'weekly': ['Clean water fountain', 'Clean room'],
            'monthly': [
                'Deep clean litter box', 'Buy food', 'Buy wet food', 
                'Buy litter', 'Buy treats', 'Buy toys'
            ],
            'quarterly': []
        }
    
    if 'task_schedules' not in st.session_state:
        st.session_state.task_schedules = {
            'daily': {'Clean food bowl': 1, 'Add water': 1, 'Clean litter box': 2, 
                     'Let them out my room': 2, 'Leave them alone': 1, 'Pray for them': 1},
            'weekly': {'Clean water fountain': 1, 'Clean room': 2},
            'monthly': {'Deep clean litter box': 1, 'Buy food': 1, 'Buy wet food': 1, 
                       'Buy litter': 1, 'Buy treats': 1, 'Buy toys': 1}
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
        st.session_state.task_logs = {}
        st.session_state.cat_profiles = {
            cat: {
                'age': '', 'breed': '', 'weight': '', 
                'vet_visits': [], 'notes': ''
            } for cat in st.session_state.cats
        }

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
            entry_date = datetime.fromisoformat(timestamp).date()
            if start_date <= entry_date <= end_date:
                for entry in date_entries:
                    entry['timestamp'] = timestamp
                    entries.append(entry)
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
        log_date = date.fromisoformat(date_str)
        if start_date <= log_date <= end_date:
            completions[date_str] = day_logs
    return completions

# ─────────────────────────────────────────────
# AI Integration — FIXED response parsing
# ─────────────────────────────────────────────
def call_huggingface_ai(user_message: str, chat_history: list, cat_data: Dict = None) -> str:
    """
    Call Hugging Face Inference API using the instruct format.
    Passes full chat history so the model doesn't repeat itself.
    Falls back to rule-based replies if API is unavailable.
    """
    if not HF_API_KEY:
        return get_fallback_ai_response(user_message, cat_data)

    # Build the [INST] prompt with history for Mistral-style models
    system_prompt = (
        "You are a helpful, concise cat care assistant. "
        "You have access to data about the user's cats: "
        f"Names: {cat_data.get('cats', [])}. "
        "Give short, specific answers. Never repeat what you said before. "
        "If asked the same question twice, add new useful details."
    )

    # Build conversation turns from history (last 6 messages to stay concise)
    history_turns = chat_history[-6:] if len(chat_history) > 6 else chat_history
    conversation = ""
    for msg in history_turns:
        if msg["role"] == "user":
            conversation += f"[INST] {msg['content']} [/INST]\n"
        else:
            conversation += f"{msg['content']}\n"

    prompt = f"<s>[INST] {system_prompt} [/INST]\n{conversation}[INST] {user_message} [/INST]"

    try:
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 300,
                "temperature": 0.7,
                "repetition_penalty": 1.3,   # ← prevents word-level repetition
                "do_sample": True,
                "return_full_text": False     # ← CRITICAL: only return the new text
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
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated = result[0].get('generated_text', '').strip()
                # Extra safety: strip any leaked prompt fragments
                if '[/INST]' in generated:
                    generated = generated.split('[/INST]')[-1].strip()
                if generated:
                    return generated
            return get_fallback_ai_response(user_message, cat_data)

        elif response.status_code == 503:
            return "⏳ The AI model is loading — this takes about 20 seconds on the free tier. Please try again shortly!"

        else:
            return get_fallback_ai_response(user_message, cat_data)

    except requests.exceptions.Timeout:
        return "⏱️ The AI took too long to respond. Try a shorter question or try again."
    except Exception:
        return get_fallback_ai_response(user_message, cat_data)


def get_fallback_ai_response(user_message: str, cat_data: Dict = None) -> str:
    """Rule-based fallback when HF API is unavailable"""
    message_lower = user_message.lower()

    if any(w in message_lower for w in ['water', 'drink', 'hydration']):
        return "💧 Cats need fresh water at all times. A fountain encourages drinking. Aim for ~50 ml per kg of body weight daily."
    elif any(w in message_lower for w in ['food', 'eat', 'feeding', 'hungry']):
        return "🍽️ Feed high-quality food suited to their age. Most adults do well with 2–3 small meals daily. Monitor weight and adjust portions."
    elif any(w in message_lower for w in ['litter', 'box', 'poop', 'pee']):
        return "🚽 Scoop at least twice daily and deep-clean monthly. One box per cat plus one extra is the standard rule."
    elif any(w in message_lower for w in ['vet', 'doctor', 'sick', 'health', 'medicine']):
        return "🏥 Annual checkups are minimum. See a vet promptly for changes in appetite, litter habits, energy, or behaviour."
    elif any(w in message_lower for w in ['groom', 'brush', 'fur', 'hair', 'nail']):
        return "🪥 Brush short-haired cats 2–3×/week, long-haired daily. Trim nails every 2–3 weeks and check ears monthly."
    elif any(w in message_lower for w in ['play', 'exercise', 'bored', 'toy']):
        return "🎾 Two 15-minute play sessions daily keeps cats active and mentally sharp. Rotate toys to keep things interesting."
    elif any(w in message_lower for w in ['buy', 'shop', 'purchase', 'need']):
        return "🛒 Monthly essentials: dry food, wet food, litter, treats, and a new toy. Check expiry dates and store food sealed."
    elif any(w in message_lower for w in ['pray', 'blessing', 'dua']):
        return "🙏 May Allah grant Haku, Kuro, and Sonic health, happiness, and long life. Ameen."
    else:
        return "🐱 I can help with feeding, water, litter, grooming, vet care, or shopping. What would you like to know?"


# Health Analysis Functions
def analyze_cat_health(cat_name: str) -> Dict:
    if cat_name not in st.session_state.health_data:
        return {'status': 'no_data', 'message': 'No health data available'}
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    week_entries = get_health_entries(cat_name, week_ago, today)
    month_entries = get_health_entries(cat_name, month_ago, today)
    
    if not week_entries:
        return {'status': 'warning', 'message': 'No entries for the past week'}
    
    profile = st.session_state.cat_profiles.get(cat_name, {})
    
    analysis = {
        'cat': cat_name,
        'profile': profile,
        'period': 'week',
        'total_entries': len(week_entries),
        'water_avg': 0,
        'food_avg': 0,
        'litter_usage': 0,
        'litter_quality_issues': [],
        'mood_trend': 'stable',
        'medications': [],
        'concerns': [],
        'recommendations': [],
        'vet_history': profile.get('vet_visits', [])
    }
    
    water_amounts = [entry.get('water_drinks', 0) for entry in week_entries if entry.get('water_drinks')]
    food_amounts = [entry.get('food_eats', 0) for entry in week_entries if entry.get('food_eats')]
    litter_uses = [entry.get('litter_box_times', 0) for entry in week_entries if entry.get('litter_box_times')]
    
    if water_amounts:
        analysis['water_avg'] = sum(water_amounts) / len(water_amounts)
    if food_amounts:
        analysis['food_avg'] = sum(food_amounts) / len(food_amounts)
    if litter_uses:
        analysis['litter_usage'] = sum(litter_uses) / len(litter_uses)
    
    for entry in week_entries:
        qualities = entry.get('litter_quality', [])
        if isinstance(qualities, list):
            for quality in qualities:
                if quality and ('blood' in quality.lower() or 'diarrhea' in quality.lower() or 'abnormal' in quality.lower()):
                    analysis['litter_quality_issues'].append({
                        'date': entry.get('timestamp', '').split('T')[0],
                        'issue': quality
                    })
    
    moods = [entry.get('mood', 'Normal') for entry in week_entries]
    poor_moods = sum(1 for m in moods if m in ['Poor', 'Very Poor'])
    if poor_moods > len(moods) / 2:
        analysis['mood_trend'] = 'declining'
    elif 'Excellent' in moods and moods.count('Excellent') > len(moods) / 2:
        analysis['mood_trend'] = 'improving'
    
    if analysis['water_avg'] < 3:
        analysis['concerns'].append('Low water intake detected')
        analysis['recommendations'].append('Consider adding more water sources or wet food')
    
    if analysis['food_avg'] < 2:
        analysis['concerns'].append('Low food intake detected')
        analysis['recommendations'].append('Monitor appetite and consider vet consultation if persists')
    
    if analysis['litter_usage'] > 5:
        analysis['concerns'].append('Frequent litter box usage')
        analysis['recommendations'].append('Monitor for urinary tract issues or stress')
    
    if analysis['litter_quality_issues']:
        analysis['concerns'].append(f'Litter quality issues detected ({len(analysis["litter_quality_issues"])} instances)')
        analysis['recommendations'].append('⚠️ URGENT: Consult vet immediately about litter abnormalities')
    
    if analysis['mood_trend'] == 'declining':
        analysis['concerns'].append('Declining mood trend detected')
        analysis['recommendations'].append('Monitor for stress, illness, or environmental changes')
    
    medications = set()
    for entry in week_entries:
        if entry.get('medication_name'):
            medications.add(f"{entry['medication_name']} ({entry.get('medication_dosage', 'unknown dose')}) - {entry.get('medication_reason', 'Unknown reason')}")
    analysis['medications'] = list(medications)
    
    return analysis

def generate_cat_summary(cat_name: str) -> str:
    analysis = analyze_cat_health(cat_name)
    
    if analysis.get('status') == 'no_data':
        return f"No health data available for {cat_name}. Please start tracking their health."
    
    if analysis.get('status') == 'warning':
        return f"Only limited data available for {cat_name}. Please add more entries for better analysis."
    
    profile = analysis.get('profile', {})
    
    summary = f"## {cat_name}'s Health Summary\n\n"
    
    if profile.get('age') or profile.get('breed'):
        summary += "**Profile:**\n"
        if profile.get('age'):
            summary += f"- Age: {profile['age']}\n"
        if profile.get('breed'):
            summary += f"- Breed: {profile['breed']}\n"
        summary += "\n"
    
    summary += f"**Tracking Period:** Past 7 days\n"
    summary += f"**Total Entries:** {analysis['total_entries']}\n\n"
    
    summary += "**Average Daily Activity:**\n"
    summary += f"- Water Drinks: {analysis['water_avg']:.1f} times/day\n"
    summary += f"- Food Eats: {analysis['food_avg']:.1f} times/day\n"
    summary += f"- Litter Box Uses: {analysis['litter_usage']:.1f} times/day\n"
    summary += f"- Mood Trend: {analysis['mood_trend'].title()}\n\n"
    
    if analysis['medications']:
        summary += "**Current Medications:**\n"
        for med in analysis['medications']:
            summary += f"- {med}\n"
        summary += "\n"
    
    if analysis['litter_quality_issues']:
        summary += "**🚨 CRITICAL - Litter Quality Issues:**\n"
        for issue in analysis['litter_quality_issues'][:3]:
            summary += f"- {issue['date']}: {issue['issue']}\n"
        summary += "\n"
    
    if analysis['concerns']:
        summary += "**⚠️ Concerns Detected:**\n"
        for concern in analysis['concerns']:
            summary += f"- {concern}\n"
        summary += "\n"
        
        summary += "**💡 Recommendations:**\n"
        for rec in analysis['recommendations']:
            summary += f"- {rec}\n"
        summary += "\n"
    else:
        summary += "**✅ No major concerns detected. Keep up the good care!**\n\n"
    
    if analysis.get('vet_history'):
        recent_visits = sorted(analysis['vet_history'], key=lambda x: x.get('date', ''), reverse=True)[:2]
        if recent_visits:
            summary += "**Recent Vet Visits:**\n"
            for visit in recent_visits:
                summary += f"- {visit.get('date', 'Unknown')}: {visit.get('reason', 'Checkup')} (Dr. {visit.get('doctor', 'Unknown')})\n"
            summary += "\n"
    
    return summary

# ─────────────────────────────────────────────
# Page: Cat Profiles — FIXED broken HTML
# ─────────────────────────────────────────────
def cat_profiles_page():
    st.header("🐱 Cat Profiles")

    for cat in st.session_state.cats:
        profile = st.session_state.cat_profiles.get(cat, {})

        # ── Profile card (native Streamlit, no broken HTML) ──
        with st.container(border=True):
            col_icon, col_info = st.columns([1, 4])

            with col_icon:
                st.markdown(f"## 🐱")
                st.markdown(f"**{cat}**")

            with col_info:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Age", profile.get('age') or "—")
                c2.metric("Breed", profile.get('breed') or "—")
                c3.metric("Weight", f"{profile.get('weight') or '—'} kg")
                c4.metric("Vet Visits", len(profile.get('vet_visits', [])))

                if profile.get('notes'):
                    st.caption(f"📝 {profile['notes']}")

            btn1, btn2, _ = st.columns([1, 1, 4])
            with btn1:
                if st.button(f"✏️ Edit Profile", key=f"open_edit_{cat}"):
                    st.session_state[f'edit_basic_{cat}'] = not st.session_state.get(f'edit_basic_{cat}', False)
                    st.rerun()
            with btn2:
                if st.button(f"🏥 Add Visit", key=f"open_visit_{cat}"):
                    st.session_state[f'edit_{cat}'] = not st.session_state.get(f'edit_{cat}', False)
                    st.rerun()

        # ── Edit basic profile ──
        if st.session_state.get(f'edit_basic_{cat}', False):
            with st.expander(f"✏️ Edit {cat}'s Basic Info", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    age   = st.text_input("Age",         value=profile.get('age', ''),   key=f"age_{cat}")
                    breed = st.text_input("Breed",       value=profile.get('breed', ''), key=f"breed_{cat}")
                with col2:
                    weight = st.text_input("Weight (kg)", value=profile.get('weight', ''), key=f"weight_{cat}")
                    notes  = st.text_area("Notes",        value=profile.get('notes', ''),  key=f"notes_{cat}", height=80)

                s1, s2 = st.columns([1, 5])
                with s1:
                    if st.button("💾 Save", key=f"save_basic_{cat}", type="primary"):
                        st.session_state.cat_profiles[cat].update(
                            {'age': age, 'breed': breed, 'weight': weight, 'notes': notes}
                        )
                        save_data()
                        st.success("✅ Profile updated!")
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
                    vet_df = pd.DataFrame(vet_visits)
                    display_cols = [c for c in ['date', 'doctor', 'reason', 'medication'] if c in vet_df.columns]
                    st.dataframe(vet_df[display_cols], use_container_width=True, hide_index=True)

                    visit_options = [f"{v['date']} — {v['reason']}" for v in vet_visits]
                    to_delete = st.selectbox("Select visit to delete", [""] + visit_options, key=f"del_vis_{cat}")
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
                    v_date   = st.date_input("Visit Date",  key=f"v_date_{cat}")
                    v_doctor = st.text_input("Doctor Name", key=f"v_doc_{cat}", placeholder="Dr. Smith")
                with col2:
                    v_reason = st.text_input("Reason",      key=f"v_reason_{cat}", placeholder="Annual checkup")
                    v_med    = st.text_input("Medication",  key=f"v_med_{cat}",    placeholder="None")

                a1, a2 = st.columns([1, 5])
                with a1:
                    if st.button("💾 Save Visit", key=f"save_visit_{cat}", type="primary"):
                        st.session_state.cat_profiles[cat]['vet_visits'].append({
                            'date': str(v_date), 'doctor': v_doctor,
                            'reason': v_reason, 'medication': v_med
                        })
                        save_data()
                        st.success("✅ Visit added!")
                        st.rerun()
                with a2:
                    if st.button("❌ Close", key=f"close_visit_{cat}"):
                        st.session_state[f'edit_{cat}'] = False
                        st.rerun()

        st.markdown("")  # spacing


# ─────────────────────────────────────────────
# Page: Add Health Entry
# ─────────────────────────────────────────────
def add_health_entry_page():
    st.header("📝 Add Health Entry")
    
    if st.session_state.editing_health_entry and st.session_state.edit_entry_data:
        st.subheader("✏️ Edit Health Entry")
        
        edit_cat = st.session_state.edit_entry_cat
        edit_timestamp = st.session_state.edit_entry_data.get('timestamp', '')
        edit_entry_index = st.session_state.edit_entry_data.get('index', 0)
        
        original_entry = None
        if edit_cat in st.session_state.health_data:
            if edit_timestamp in st.session_state.health_data[edit_cat]:
                if edit_entry_index < len(st.session_state.health_data[edit_cat][edit_timestamp]):
                    original_entry = st.session_state.health_data[edit_cat][edit_timestamp][edit_entry_index]
        
        if original_entry:
            with st.form("edit_health_entry_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    water_drinks    = st.number_input("Water Drinks",    min_value=0, max_value=20, value=original_entry.get('water_drinks', 0))
                    food_eats       = st.number_input("Food Eats",       min_value=0, max_value=10, value=original_entry.get('food_eats', 0))
                    litter_box_times= st.number_input("Litter Box Times",min_value=0, max_value=15, value=original_entry.get('litter_box_times', 0))
                
                with col2:
                    mood = st.selectbox("Mood", ["Very Poor", "Poor", "Normal", "Good", "Excellent"],
                                       index=["Very Poor", "Poor", "Normal", "Good", "Excellent"].index(original_entry.get('mood', 'Normal')))
                    general_appearance = st.selectbox("General Appearance", ["Poor", "Fair", "Good", "Excellent"],
                                                     index=["Poor", "Fair", "Good", "Excellent"].index(original_entry.get('general_appearance', 'Good')))
                    litter_quality = st.text_area("Litter Quality Issues", value='\n'.join(original_entry.get('litter_quality', [])))
                
                st.markdown("---")
                st.subheader("💊 Medication (Optional)")
                with st.expander("Add/Edit Medication"):
                    medication_name      = st.text_input("Medication Name",  value=original_entry.get('medication_name', ''))
                    medication_dosage    = st.text_input("Dosage",           value=original_entry.get('medication_dosage', ''))
                    medication_frequency = st.text_input("Frequency",        value=original_entry.get('medication_frequency', ''))
                    medication_reason    = st.text_input("Reason",           value=original_entry.get('medication_reason', ''))
                
                st.markdown("---")
                notes = st.text_area("Additional Notes", height=100, value=original_entry.get('notes', ''))
                
                st.markdown("---")
                st.subheader("🪥 Grooming Tasks")
                grooming_tasks = {
                    "Brush Fur":  st.checkbox("Brush Fur",  value=original_entry.get('grooming_tasks', {}).get('Brush Fur', False)),
                    "Trim Nails": st.checkbox("Trim Nails", value=original_entry.get('grooming_tasks', {}).get('Trim Nails', False)),
                    "Clean Ears": st.checkbox("Clean Ears", value=original_entry.get('grooming_tasks', {}).get('Clean Ears', False)),
                    "Dental Care":st.checkbox("Dental Care",value=original_entry.get('grooming_tasks', {}).get('Dental Care', False))
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
                            'medication_frequency': medication_frequency, 'medication_reason': medication_reason
                        })
                    update_health_entry(edit_cat, edit_timestamp, edit_entry_index, entry_data)
                    st.success(f"✅ Health entry updated for {edit_cat}!")
                    st.session_state.editing_health_entry = False
                    st.session_state.edit_entry_data = {}
                    st.rerun()
        
        if st.button("❌ Cancel Edit"):
            st.session_state.editing_health_entry = False
            st.session_state.edit_entry_data = {}
            st.rerun()
        return
    
    # NEW ENTRY
    st.subheader("🆕 Add New Health Entry")
    selected_cat = st.selectbox("Select Cat", st.session_state.cats, key="cat_selector")
    entry_mode   = st.radio("Entry Mode", ["🚀 Quick Entry", "📋 Detailed Entry"])
    
    if entry_mode == "🚀 Quick Entry":
        st.markdown("### Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💧 Water Drank"):
                add_health_entry(selected_cat, {
                    'water_drinks': 1, 'food_eats': 0, 'litter_box_times': 0,
                    'mood': 'Good', 'general_appearance': 'Good',
                    'litter_quality': [], 'notes': 'Quick entry: Water drank', 'grooming_tasks': {}
                })
                st.success(f"✅ Water entry added for {selected_cat}!")
                st.rerun()
        
        with col2:
            if st.button("🍽️ Food Eaten"):
                add_health_entry(selected_cat, {
                    'water_drinks': 0, 'food_eats': 1, 'litter_box_times': 0,
                    'mood': 'Good', 'general_appearance': 'Good',
                    'litter_quality': [], 'notes': 'Quick entry: Food eaten', 'grooming_tasks': {}
                })
                st.success(f"✅ Food entry added for {selected_cat}!")
                st.rerun()
        
        with col3:
            if st.button("🚽 Litter Box Used"):
                add_health_entry(selected_cat, {
                    'water_drinks': 0, 'food_eats': 0, 'litter_box_times': 1,
                    'mood': 'Good', 'general_appearance': 'Good',
                    'litter_quality': [], 'notes': 'Quick entry: Litter box used', 'grooming_tasks': {}
                })
                st.success(f"✅ Litter entry added for {selected_cat}!")
                st.rerun()
        
        st.markdown("---")
    
    st.markdown("### 📋 Detailed Health Entry")
    
    with st.form("health_entry_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            water_drinks     = st.number_input("Water Drinks",     min_value=0, max_value=20, value=0)
            food_eats        = st.number_input("Food Eats",        min_value=0, max_value=10, value=0)
            litter_box_times = st.number_input("Litter Box Times", min_value=0, max_value=15, value=0)
        
        with col2:
            mood               = st.selectbox("Mood", ["Very Poor", "Poor", "Normal", "Good", "Excellent"])
            general_appearance = st.selectbox("General Appearance", ["Poor", "Fair", "Good", "Excellent"])
            litter_quality     = st.text_area("Litter Quality Issues", placeholder="e.g., Blood, diarrhea, abnormal color...")
        
        st.markdown("---")
        st.subheader("💊 Medication (Optional)")
        with st.expander("Add Medication"):
            medication_name      = st.text_input("Medication Name", placeholder="e.g., Amoxicillin")
            medication_dosage    = st.text_input("Dosage",          placeholder="e.g., 50mg")
            medication_frequency = st.text_input("Frequency",       placeholder="e.g., Twice daily")
            medication_reason    = st.text_input("Reason",          placeholder="e.g., Antibiotic treatment")
        
        st.markdown("---")
        notes = st.text_area("Additional Notes", height=100, placeholder="Any other observations or concerns...")
        
        st.markdown("---")
        st.subheader("🪥 Grooming Tasks")
        st.write("*Grooming is not a daily task. Check these if performed today.*")
        grooming_tasks = {
            "Brush Fur":  st.checkbox("Brush Fur"),
            "Trim Nails": st.checkbox("Trim Nails"),
            "Clean Ears": st.checkbox("Clean Ears"),
            "Dental Care":st.checkbox("Dental Care")
        }
        
        if st.form_submit_button("💾 Save Health Entry"):
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
                    'medication_frequency': medication_frequency, 'medication_reason': medication_reason
                })
            add_health_entry(selected_cat, entry_data)
            st.success(f"✅ Health entry saved for {selected_cat}!")
            st.rerun()


# ─────────────────────────────────────────────
# Page: View Health Data
# ─────────────────────────────────────────────
def view_health_data_page():
    st.header("📊 View Health Data")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_cat = st.selectbox("Select Cat", st.session_state.cats)
    with col2:
        date_range = st.date_input("Date Range",
                                   value=(date.today() - timedelta(days=30), date.today()),
                                   max_value=date.today())
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date.today()
    
    entries = get_health_entries(selected_cat, start_date, end_date)
    
    if not entries:
        st.info(f"No health data found for {selected_cat} in the selected date range.")
        return
    
    df = pd.DataFrame(entries)
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df['time'] = pd.to_datetime(df['timestamp']).dt.time
    df = df.sort_values('timestamp', ascending=False)
    
    st.subheader(f"📈 {selected_cat}'s Health Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_water = df['water_drinks'].mean() if 'water_drinks' in df.columns else 0
        st.metric("Avg Water/Day", f"{avg_water:.1f}")
    with col2:
        avg_food = df['food_eats'].mean() if 'food_eats' in df.columns else 0
        st.metric("Avg Food/Day", f"{avg_food:.1f}")
    with col3:
        avg_litter = df['litter_box_times'].mean() if 'litter_box_times' in df.columns else 0
        st.metric("Avg Litter/Day", f"{avg_litter:.1f}")
    with col4:
        if 'mood' in df.columns:
            mood_counts = df['mood'].value_counts()
            dominant_mood = mood_counts.idxmax() if not mood_counts.empty else "N/A"
            st.metric("Dominant Mood", dominant_mood)
    
    st.subheader("📋 Health Entries")
    df['date_only'] = df['timestamp'].str.split('T').str[0]
    grouped_entries = df.groupby('date_only')
    
    for date_str, date_group in grouped_entries:
        with st.expander(f"📅 {date_str} ({len(date_group)} entries)"):
            for idx, entry in date_group.iterrows():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Time:** {entry['time']}")
                    st.write(f"**Water:** {entry.get('water_drinks', 'N/A')}")
                    st.write(f"**Food:** {entry.get('food_eats', 'N/A')}")
                    st.write(f"**Litter Box:** {entry.get('litter_box_times', 'N/A')} times")
                    st.write(f"**Mood:** {entry.get('mood', 'N/A')}")
                    st.write(f"**Appearance:** {entry.get('general_appearance', 'N/A')}")
                    if entry.get('litter_quality'):
                        qualities = '\n'.join(entry['litter_quality'])
                        if qualities.strip():
                            st.write(f"**Litter Issues:** {qualities}")
                    if entry.get('notes'):
                        st.write(f"**Notes:** {entry['notes']}")
                    if entry.get('medication_name'):
                        st.write(f"**Medication:** {entry['medication_name']} ({entry.get('medication_dosage', 'N/A')})")
                    grooming_done = [t for t, done in entry.get('grooming_tasks', {}).items() if done]
                    if grooming_done:
                        st.write(f"**Grooming:** {', '.join(grooming_done)}")
                with col2:
                    if st.button("✏️ Edit", key=f"edit_entry_{idx}"):
                        st.session_state.editing_health_entry = True
                        st.session_state.edit_entry_data = {'timestamp': entry['timestamp'], 'index': idx}
                        st.session_state.edit_entry_cat = selected_cat
                        st.rerun()
                    if st.button("🗑️ Delete", key=f"delete_entry_{idx}"):
                        delete_health_entry(selected_cat, entry['timestamp'], idx)
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


# ─────────────────────────────────────────────
# Page: Task Management — REMOVED edit/delete
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# Page: AI Chat — FIXED with history passing
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# Page: Dashboard
# ─────────────────────────────────────────────
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
            st.markdown(generate_cat_summary(cat))


# ─────────────────────────────────────────────
# Page: Data Management
# ─────────────────────────────────────────────
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
            st.warning(f"⚠️ Reminder: No health entries for {', '.join(missing)} today!")
        
        today_str = str(date.today())
        if today_str not in st.session_state.task_logs:
            st.session_state.task_logs[today_str] = []
        
        done = [log['task'] for log in st.session_state.task_logs[today_str]]
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
