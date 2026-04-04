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
        HF_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"  # Ethical and powerful model
    else:
        HF_API_KEY = None
        st.warning("⚠️ Hugging Face API key not found. AI chat will use basic responses.")
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
        # Updated task structure - monthly tasks include shopping
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
            'quarterly': []  # Removed quarterly tasks as requested
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

    # Initialize task editing state
    if 'editing_tasks' not in st.session_state:
        st.session_state.editing_tasks = False
    if 'new_task_name' not in st.session_state:
        st.session_state.new_task_name = ''
    if 'new_task_frequency' not in st.session_state:
        st.session_state.new_task_frequency = 'daily'

    # Initialize health entry editing state
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
    """Save all data to files with encryption"""
    try:
        # Prepare data for saving
        health_data_str = json.dumps(st.session_state.health_data, default=str)
        task_logs_str = json.dumps(st.session_state.task_logs, default=str)
        profiles_str = json.dumps(st.session_state.cat_profiles, default=str)
        
        # Encrypt if authentication is enabled
        if AUTH_ENABLED:
            health_data_str = encrypt_data(health_data_str)
            task_logs_str = encrypt_data(task_logs_str)
            profiles_str = encrypt_data(profiles_str)
        
        # Save encrypted data
        with open('health_data.json', 'w') as f:
            f.write(health_data_str)
        with open('task_logs.json', 'w') as f:
            f.write(task_logs_str)
        with open('cat_profiles.json', 'w') as f:
            f.write(profiles_str)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def load_data():
    """Load data from files with decryption"""
    try:
        if os.path.exists('health_data.json'):
            with open('health_data.json', 'r') as f:
                data_str = f.read()
                if AUTH_ENABLED and data_str:
                    try:
                        data_str = decrypt_data(data_str)
                    except:
                        pass  # Data might not be encrypted yet
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
                    # Ensure vet_visits is a list of dicts
                    for cat, profile in loaded_profiles.items():
                        if 'vet_visits' in profile and isinstance(profile['vet_visits'], list):
                            if profile['vet_visits'] and isinstance(profile['vet_visits'][0], str):
                                # Convert old format to new format
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

# Health entry functions - NEW IMPROVED SYSTEM
def add_health_entry(cat_name: str, entry_data: Dict):
    """Add a health entry for a specific cat with timestamp"""
    if cat_name not in st.session_state.health_data:
        st.session_state.health_data[cat_name] = {}
    
    # Use current timestamp as unique key
    timestamp = datetime.now().isoformat()
    
    if timestamp not in st.session_state.health_data[cat_name]:
        st.session_state.health_data[cat_name][timestamp] = []
    
    entry_data['timestamp'] = timestamp
    st.session_state.health_data[cat_name][timestamp].append(entry_data)
    st.session_state.last_entries[cat_name] = datetime.now()
    save_data()

def get_health_entries(cat_name: str, start_date: date, end_date: date) -> List[Dict]:
    """Get health entries for a cat within date range"""
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
    """Update a specific health entry"""
    if cat_name in st.session_state.health_data and timestamp in st.session_state.health_data[cat_name]:
        if entry_index < len(st.session_state.health_data[cat_name][timestamp]):
            st.session_state.health_data[cat_name][timestamp][entry_index].update(updated_data)
            save_data()

def delete_health_entry(cat_name: str, timestamp: str, entry_index: int):
    """Delete a specific health entry"""
    if cat_name in st.session_state.health_data and timestamp in st.session_state.health_data[cat_name]:
        if entry_index < len(st.session_state.health_data[cat_name][timestamp]):
            st.session_state.health_data[cat_name][timestamp].pop(entry_index)
            if not st.session_state.health_data[cat_name][timestamp]:
                del st.session_state.health_data[cat_name][timestamp]
            save_data()

# Task management functions
def add_task_completion(task_name: str, cat_name: str = None, notes: str = ""):
    """Add a task completion entry"""
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
    """Get task completions within date range"""
    completions = {}
    for date_str, day_logs in st.session_state.task_logs.items():
        log_date = datetime.fromisoformat(date_str).date()
        if start_date <= log_date <= end_date:
            completions[date_str] = day_logs
    return completions

# Hugging Face AI Integration Functions
def call_huggingface_ai(user_message: str, cat_data: Dict = None) -> str:
    """Call Hugging Face API for intelligent responses"""
    if not HF_API_KEY:
        return get_fallback_ai_response(user_message, cat_data)
    
    try:
        # Prepare prompt with context
        context = f"""You are an ethical AI assistant specializing in cat care and health. You have access to the following cat data:
        
Cats: {cat_data.get('cats', [])}
Health Data: {cat_data.get('health_data', {})}
Profiles: {cat_data.get('profiles', {})}

User Question: {user_message}

Please provide helpful, ethical, and accurate advice about cat care. Focus on the wellbeing of the cats and responsible pet ownership. If you don't have specific information about the cats, provide general best practices for cat care.

Response:"""

        payload = {"inputs": context, "parameters": {"max_new_tokens": 500, "temperature": 0.7}}
        
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
                return result[0].get('generated_text', '').split('Response:')[1].strip() if 'Response:' in result[0].get('generated_text', '') else result[0].get('generated_text', 'I apologize, but I could not generate a response.')
            else:
                return get_fallback_ai_response(user_message, cat_data)
        else:
            return get_fallback_ai_response(user_message, cat_data)
            
    except Exception as e:
        return get_fallback_ai_response(user_message, cat_data)

def get_fallback_ai_response(user_message: str, cat_data: Dict = None) -> str:
    """Fallback AI response using basic logic"""
    message_lower = user_message.lower()
    
    # Cat care advice based on message content
    if any(word in message_lower for word in ['water', 'drink', 'hydration']):
        return "💧 Cats need fresh water available at all times. Consider using a water fountain to encourage drinking. Most cats should drink about 50-60ml of water per kg of body weight daily."
    
    elif any(word in message_lower for word in ['food', 'eat', 'feeding']):
        return "🍽️ Feed your cat high-quality food appropriate for their age and health. Most adult cats eat 2-3 small meals daily. Monitor their weight and adjust portions accordingly."
    
    elif any(word in message_lower for word in ['litter', 'box', 'clean']):
        return "🚽 Clean the litter box daily and scoop waste at least twice daily. Most cats prefer a clean box. If you notice changes in litter habits, monitor for health issues."
    
    elif any(word in message_lower for word in ['vet', 'doctor', 'health']):
        return "🏥 Schedule regular vet checkups (at least annually). Contact your vet immediately if you notice changes in behavior, appetite, litter habits, or any concerning symptoms."
    
    elif any(word in message_lower for word in ['groom', 'brush', 'fur']):
        return "🪥 Regular grooming helps reduce hairballs and keeps their coat healthy. Brush long-haired cats daily, short-haired cats 2-3 times weekly. Check for fleas, ticks, and skin issues."
    
    elif any(word in message_lower for word in ['play', 'exercise', 'activity']):
        return "🎾 Play with your cats daily to keep them physically and mentally stimulated. Use interactive toys and engage them for 15-30 minutes, 2-3 times daily."
    
    elif any(word in message_lower for word in ['shopping', 'buy', 'purchase']):
        return "🛒 Monthly shopping should include: high-quality cat food, wet food, litter, treats, and toys. Check expiration dates and store food properly."
    
    elif any(word in message_lower for word in ['pray', 'blessing', 'dua']):
        return "🙏 Praying for your cats is a beautiful way to show love and care. May Allah bless them with health, happiness, and long life. Ameen."
    
    else:
        return "🐱 I'm here to help with your cat care! Ask about feeding, litter box care, vet visits, grooming, or any other cat-related questions. For urgent health concerns, always consult your veterinarian."

# AI Analysis Functions
def analyze_cat_health(cat_name: str) -> Dict:
    """Analyze health data for a specific cat with profile integration"""
    if cat_name not in st.session_state.health_data:
        return {'status': 'no_data', 'message': 'No health data available'}
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    week_entries = get_health_entries(cat_name, week_ago, today)
    month_entries = get_health_entries(cat_name, month_ago, today)
    
    if not week_entries:
        return {'status': 'warning', 'message': 'No entries for the past week'}
    
    # Get cat profile for context
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
    
    # Calculate averages
    water_amounts = [entry.get('water_drinks', 0) for entry in week_entries if entry.get('water_drinks')]
    food_amounts = [entry.get('food_eats', 0) for entry in week_entries if entry.get('food_eats')]
    litter_uses = [entry.get('litter_box_times', 0) for entry in week_entries if entry.get('litter_box_times')]
    
    if water_amounts:
        analysis['water_avg'] = sum(water_amounts) / len(water_amounts)
    if food_amounts:
        analysis['food_avg'] = sum(food_amounts) / len(food_amounts)
    if litter_uses:
        analysis['litter_usage'] = sum(litter_uses) / len(litter_uses)
    
    # Check litter quality for issues
    for entry in week_entries:
        qualities = entry.get('litter_quality', [])
        if isinstance(qualities, list):
            for quality in qualities:
                if quality and ('blood' in quality.lower() or 'diarrhea' in quality.lower() or 'abnormal' in quality.lower()):
                    analysis['litter_quality_issues'].append({
                        'date': entry.get('timestamp', '').split('T')[0],
                        'issue': quality
                    })
    
    # Mood analysis
    moods = [entry.get('mood', 'Normal') for entry in week_entries]
    poor_moods = sum(1 for m in moods if m in ['Poor', 'Very Poor'])
    if poor_moods > len(moods) / 2:
        analysis['mood_trend'] = 'declining'
    elif 'Excellent' in moods and moods.count('Excellent') > len(moods) / 2:
        analysis['mood_trend'] = 'improving'
    
    # Check for concerns with profile context
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
    
    # Collect medications
    medications = set()
    for entry in week_entries:
        if entry.get('medication_name'):
            medications.add(f"{entry['medication_name']} ({entry.get('medication_dosage', 'unknown dose')}) - {entry.get('medication_reason', 'Unknown reason')}")
    analysis['medications'] = list(medications)
    
    return analysis

def generate_cat_summary(cat_name: str) -> str:
    """Generate a comprehensive summary for a cat"""
    analysis = analyze_cat_health(cat_name)
    
    if analysis.get('status') == 'no_data':
        return f"No health data available for {cat_name}. Please start tracking their health."
    
    if analysis.get('status') == 'warning':
        return f"Only limited data available for {cat_name}. Please add more entries for better analysis."
    
    profile = analysis.get('profile', {})
    
    summary = f"## {cat_name}'s Health Summary\n\n"
    
    # Profile info
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
        for issue in analysis['litter_quality_issues'][:3]:  # Show first 3
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
    
    # Recent vet visits
    if analysis.get('vet_history'):
        recent_visits = sorted(analysis['vet_history'], key=lambda x: x.get('date', ''), reverse=True)[:2]
        if recent_visits:
            summary += "**Recent Vet Visits:**\n"
            for visit in recent_visits:
                summary += f"- {visit.get('date', 'Unknown')}: {visit.get('reason', 'Checkup')} (Dr. {visit.get('doctor', 'Unknown')})\n"
            summary += "\n"
    
    return summary

# Page Functions
def cat_profiles_page():
    """Page for managing cat profiles with improved card layout"""
    st.header("🐱 Cat Profiles")
    
    # Display cat profiles in card layout
    for cat in st.session_state.cats:
        profile = st.session_state.cat_profiles[cat]
        
        with st.container():
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 20px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                <h3 style='color: #2c3e50; margin-bottom: 15px;'>🐱 {cat}</h3>
                
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;'>
                    div>
                        strong>Age:</<strong> {profile.get('age', 'Not set')}
                    </div>
                    div>
                        strong>Breed:</<strong> {profile.get('breed', 'Not set')}
                    </div>
                    div>
                        <strong>Vet Visits:</strong> {len(profile.get('vet_visits', []))}
                    </div>
                    <div>
                        <strong>Weight:</strong> {profile.get('weight', 'Not set')} kg
                    </div>
                </div>
                
                <div style='margin-bottom: 15px;'>
                    strong>Notes:</<strong> {profile.get('notes', 'No notes')}
                </div>
                
                <div style='display: flex; gap: 10px;'>
                    <button onclick='window.location.href="#add_visit"' style='background: #3498db; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;'>🏥 Add Visit</button>
                    <button onclick='window.location.href="#edit_profile"' style='background: #2ecc71; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;'>✏️ Edit Profile</button>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Edit form (initially hidden)
        if st.session_state.get(f'edit_{cat}', False):
            st.markdown(f"## ✏️ Editing: **{cat}**")
            
            profile = st.session_state.cat_profiles[cat]
            
            # Create tabs for better organization
            tab1, tab2 = st.tabs(["📋 Basic Info", "🏥 Vet Visits"])
            
            with tab1:
                col1, col2 = st.columns(2)
                
                with col1:
                    age = st.text_input("Age", value=profile.get('age', ''), key=f"edit_age_{cat}")
                    breed = st.text_input("Breed", value=profile.get('breed', ''), key=f"edit_breed_{cat}")
                
                with col2:
                    notes = st.text_area("Additional Notes", value=profile.get('notes', ''), 
                                       key=f"edit_notes_{cat}", height=100)
            
            with tab2:
                # Display existing vet visits in a nice table
                vet_visits = profile.get('vet_visits', [])
                
                if vet_visits:
                    st.markdown("### 📊 Recorded Visits")
                    
                    # Create DataFrame for better display
                    vet_df = pd.DataFrame(vet_visits)
                    vet_df = vet_df[['date', 'doctor', 'reason', 'medication']]
                    vet_df.columns = ['Date', 'Doctor', 'Reason', 'Medication']
                    vet_df['Medication'] = vet_df['Medication'].fillna('None')
                    
                    st.dataframe(vet_df, use_container_width=True, hide_index=True)
                    
                    # Delete visit option
                    st.markdown("##### Delete a Visit")
                    visit_options = [f"{v['date']} - {v['reason']}" for v in vet_visits]
                    visit_to_delete = st.selectbox("Select visit to delete", [""] + visit_options, key=f"delete_visit_select_{cat}")
                    
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if visit_to_delete and st.button("🗑️ Delete", type="secondary"):
                            idx = visit_options.index(visit_to_delete)
                            vet_visits.pop(idx)
                            st.session_state.cat_profiles[cat]['vet_visits'] = vet_visits
                            save_data()
                            st.success("Visit deleted!")
                            st.rerun()
                else:
                    st.info("No vet visits recorded yet.")
                
                st.markdown("---")
                st.markdown("### ➕ Add New Vet Visit")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    visit_date = st.date_input("Visit Date", key=f"new_visit_date_{cat}")
                    visit_doctor = st.text_input("Doctor Name", key=f"new_visit_doctor_{cat}", placeholder="Dr. Smith")
                
                with col2:
                    visit_reason = st.text_input("Reason for Visit", key=f"new_visit_reason_{cat}", placeholder="Annual checkup")
                    visit_medication = st.text_input("Medication Prescribed", key=f"new_visit_medication_{cat}", placeholder="None")
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("💾 Save Visit", type="primary"):
                        new_visit = {
                            'date': str(visit_date),
                            'doctor': visit_doctor,
                            'reason': visit_reason,
                            'medication': visit_medication
                        }
                        st.session_state.cat_profiles[cat]['vet_visits'].append(new_visit)
                        save_data()
                        st.success("✅ Vet visit added!")
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", type="secondary"):
                        st.session_state[f'edit_{cat}'] = False
                        st.rerun()
        
        # Edit profile form
        if st.session_state.get(f'edit_basic_{cat}', False):
            st.markdown(f"## ✏️ Edit Basic Info: **{cat}**")
            
            profile = st.session_state.cat_profiles[cat]
            
            col1, col2 = st.columns(2)
            
            with col1:
                age = st.text_input("Age", value=profile.get('age', ''), key=f"edit_age_basic_{cat}")
                breed = st.text_input("Breed", value=profile.get('breed', ''), key=f"edit_breed_basic_{cat}")
            
            with col2:
                weight = st.text_input("Weight (kg)", value=profile.get('weight', ''), key=f"edit_weight_basic_{cat}")
                notes = st.text_area("Additional Notes", value=profile.get('notes', ''), 
                                   key=f"edit_notes_basic_{cat}", height=100)
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("💾 Save Changes", type="primary"):
                    st.session_state.cat_profiles[cat].update({
                        'age': age, 'breed': breed, 'weight': weight, 'notes': notes
                    })
                    save_data()
                    st.success("✅ Profile updated!")
                    st.session_state[f'edit_basic_{cat}'] = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", type="secondary"):
                    st.session_state[f'edit_basic_{cat}'] = False
                    st.rerun()
        
        # Add vet visit button
        if st.button(f"🏥 Add Visit to {cat}", key=f"add_visit_{cat}"):
            st.session_state[f'edit_{cat}'] = True
            st.rerun()
        
        # Edit profile button
        if st.button(f"✏️ Edit {cat}'s Profile", key=f"edit_profile_{cat}"):
            st.session_state[f'edit_basic_{cat}'] = True
            st.rerun()

def add_health_entry_page():
    """Page for adding health entries with improved system"""
    st.header("📝 Add Health Entry")
    
    # Check if we're editing an existing entry
    if st.session_state.editing_health_entry and st.session_state.edit_entry_data:
        st.subheader("✏️ Edit Health Entry")
        
        edit_cat = st.session_state.edit_entry_cat
        edit_timestamp = st.session_state.edit_entry_data.get('timestamp', '')
        edit_entry_index = st.session_state.edit_entry_data.get('index', 0)
        
        # Get the original entry data
        original_entry = None
        if edit_cat in st.session_state.health_data:
            if edit_timestamp in st.session_state.health_data[edit_cat]:
                if edit_entry_index < len(st.session_state.health_data[edit_cat][edit_timestamp]):
                    original_entry = st.session_state.health_data[edit_cat][edit_timestamp][edit_entry_index]
        
        if original_entry:
            with st.form("edit_health_entry_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Basic health metrics
                    water_drinks = st.number_input("Water Drinks", min_value=0, max_value=20, value=original_entry.get('water_drinks', 0))
                    food_eats = st.number_input("Food Eats", min_value=0, max_value=10, value=original_entry.get('food_eats', 0))
                    litter_box_times = st.number_input("Litter Box Times", min_value=0, max_value=15, value=original_entry.get('litter_box_times', 0))
                
                with col2:
                    # Mood and appearance
                    mood = st.selectbox("Mood", ["Very Poor", "Poor", "Normal", "Good", "Excellent"], 
                                      index=["Very Poor", "Poor", "Normal", "Good", "Excellent"].index(original_entry.get('mood', 'Normal')))
                    general_appearance = st.selectbox("General Appearance", 
                                                    ["Poor", "Fair", "Good", "Excellent"],
                                                    index=["Poor", "Fair", "Good", "Excellent"].index(original_entry.get('general_appearance', 'Good')))
                    litter_quality = st.text_area("Litter Quality Issues", 
                                                value='\n'.join(original_entry.get('litter_quality', [])),
                                                help="Note any concerning changes in litter")
                
                # Medication info
                st.markdown("---")
                st.subheader("💊 Medication (Optional)")
                with st.expander("Add/Edit Medication"):
                    medication_name = st.text_input("Medication Name", value=original_entry.get('medication_name', ''), placeholder="e.g., Amoxicillin")
                    medication_dosage = st.text_input("Dosage", value=original_entry.get('medication_dosage', ''), placeholder="e.g., 50mg")
                    medication_frequency = st.text_input("Frequency", value=original_entry.get('medication_frequency', ''), placeholder="e.g., Twice daily")
                    medication_reason = st.text_input("Reason", value=original_entry.get('medication_reason', ''), placeholder="e.g., Antibiotic treatment")
                
                # Notes
                st.markdown("---")
                notes = st.text_area("Additional Notes", height=100, 
                                   value=original_entry.get('notes', ''),
                                   placeholder="Any other observations or concerns...")
                
                # Grooming tasks
                st.markdown("---")
                st.subheader("🪥 Grooming Tasks")
                st.write("*Grooming is not a daily task. Check these if performed today.*")
                
                grooming_tasks = {
                    "Brush Fur": st.checkbox("Brush Fur", value=original_entry.get('grooming_tasks', {}).get('Brush Fur', False)),
                    "Trim Nails": st.checkbox("Trim Nails", value=original_entry.get('grooming_tasks', {}).get('Trim Nails', False)),
                    "Clean Ears": st.checkbox("Clean Ears", value=original_entry.get('grooming_tasks', {}).get('Clean Ears', False)),
                    "Dental Care": st.checkbox("Dental Care", value=original_entry.get('grooming_tasks', {}).get('Dental Care', False))
                }
                
                # Submit button
                submitted = st.form_submit_button("💾 Update Health Entry")
                
                if submitted:
                    # Prepare entry data
                    entry_data = {
                        'water_drinks': water_drinks,
                        'food_eats': food_eats,
                        'litter_box_times': litter_box_times,
                        'mood': mood,
                        'general_appearance': general_appearance,
                        'litter_quality': litter_quality.split('\n') if litter_quality else [],
                        'notes': notes,
                        'grooming_tasks': {task: checked for task, checked in grooming_tasks.items() if checked}
                    }
                    
                    # Add medication if provided
                    if medication_name:
                        entry_data.update({
                            'medication_name': medication_name,
                            'medication_dosage': medication_dosage,
                            'medication_frequency': medication_frequency,
                            'medication_reason': medication_reason
                        })
                    
                    # Update the entry
                    update_health_entry(edit_cat, edit_timestamp, edit_entry_index, entry_data)
                    st.success(f"✅ Health entry updated for {edit_cat}!")
                    st.session_state.editing_health_entry = False
                    st.session_state.edit_entry_data = {}
                    st.rerun()
        
        with st.columns([1, 3])[0]:
            if st.button("❌ Cancel Edit", use_container_width=True):
                st.session_state.editing_health_entry = False
                st.session_state.edit_entry_data = {}
                st.rerun()
        
        return
    
    # NEW ENTRY FORM
    st.subheader("🆕 Add New Health Entry")
    
    # Cat selection
    selected_cat = st.selectbox("Select Cat", st.session_state.cats, key="cat_selector")
    
    # Quick entry mode vs detailed entry mode
    entry_mode = st.radio("Entry Mode", ["🚀 Quick Entry", "📋 Detailed Entry"])
    
    if entry_mode == "🚀 Quick Entry":
        # Quick entry for common tasks
        st.markdown("### Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💧 Water Drank", help="Cat drank water"):
                entry_data = {
                    'water_drinks': 1,
                    'food_eats': 0,
                    'litter_box_times': 0,
                    'mood': 'Good',
                    'general_appearance': 'Good',
                    'litter_quality': [],
                    'notes': 'Quick entry: Water drank',
                    'grooming_tasks': {}
                }
                add_health_entry(selected_cat, entry_data)
                st.success(f"✅ Water entry added for {selected_cat}!")
                st.rerun()
        
        with col2:
            if st.button("🍽️ Food Eaten", help="Cat ate food"):
                entry_data = {
                    'water_drinks': 0,
                    'food_eats': 1,
                    'litter_box_times': 0,
                    'mood': 'Good',
                    'general_appearance': 'Good',
                    'litter_quality': [],
                    'notes': 'Quick entry: Food eaten',
                    'grooming_tasks': {}
                }
                add_health_entry(selected_cat, entry_data)
                st.success(f"✅ Food entry added for {selected_cat}!")
                st.rerun()
        
        with col3:
            if st.button("🚽 Litter Box Used", help="Cat used litter box"):
                entry_data = {
                    'water_drinks': 0,
                    'food_eats': 0,
                    'litter_box_times': 1,
                    'mood': 'Good',
                    'general_appearance': 'Good',
                    'litter_quality': [],
                    'notes': 'Quick entry: Litter box used',
                    'grooming_tasks': {}
                }
                add_health_entry(selected_cat, entry_data)
                st.success(f"✅ Litter entry added for {selected_cat}!")
                st.rerun()
        
        st.markdown("---")
    
    # Detailed entry form
    st.markdown("### 📋 Detailed Health Entry")
    
    with st.form("health_entry_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Basic health metrics
            water_drinks = st.number_input("Water Drinks", min_value=0, max_value=20, value=0)
            food_eats = st.number_input("Food Eats", min_value=0, max_value=10, value=0)
            litter_box_times = st.number_input("Litter Box Times", min_value=0, max_value=15, value=0)
        
        with col2:
            # Mood and appearance
            mood = st.selectbox("Mood", ["Very Poor", "Poor", "Normal", "Good", "Excellent"])
            general_appearance = st.selectbox("General Appearance", 
                                            ["Poor", "Fair", "Good", "Excellent"])
            litter_quality = st.text_area("Litter Quality Issues", 
                                        placeholder="e.g., Blood, diarrhea, abnormal color...",
                                        help="Note any concerning changes in litter")
        
        # Medication info
        st.markdown("---")
        st.subheader("💊 Medication (Optional)")
        with st.expander("Add Medication"):
            medication_name = st.text_input("Medication Name", placeholder="e.g., Amoxicillin")
            medication_dosage = st.text_input("Dosage", placeholder="e.g., 50mg")
            medication_frequency = st.text_input("Frequency", placeholder="e.g., Twice daily")
            medication_reason = st.text_input("Reason", placeholder="e.g., Antibiotic treatment")
        
        # Notes
        st.markdown("---")
        notes = st.text_area("Additional Notes", height=100, 
                           placeholder="Any other observations or concerns...")
        
        # Grooming tasks
        st.markdown("---")
        st.subheader("🪥 Grooming Tasks")
        st.write("*Grooming is not a daily task. Check these if performed today.*")
        
        grooming_tasks = {
            "Brush Fur": st.checkbox("Brush Fur"),
            "Trim Nails": st.checkbox("Trim Nails"),
            "Clean Ears": st.checkbox("Clean Ears"),
            "Dental Care": st.checkbox("Dental Care")
        }
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Health Entry")
        
        if submitted:
            # Prepare entry data
            entry_data = {
                'water_drinks': water_drinks,
                'food_eats': food_eats,
                'litter_box_times': litter_box_times,
                'mood': mood,
                'general_appearance': general_appearance,
                'litter_quality': litter_quality.split('\n') if litter_quality else [],
                'notes': notes,
                'grooming_tasks': {task: checked for task, checked in grooming_tasks.items() if checked}
            }
            
            # Add medication if provided
            if medication_name:
                entry_data.update({
                    'medication_name': medication_name,
                    'medication_dosage': medication_dosage,
                    'medication_frequency': medication_frequency,
                    'medication_reason': medication_reason
                })
            
            # Add the entry
            add_health_entry(selected_cat, entry_data)
            st.success(f"✅ Health entry saved for {selected_cat}!")
            st.rerun()

def view_health_data_page():
    """Page for viewing health data with editing capabilities"""
    st.header("📊 View Health Data")
    
    # Cat selection and date range
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
    
    # Get health entries
    entries = get_health_entries(selected_cat, start_date, end_date)
    
    if not entries:
        st.info(f"No health data found for {selected_cat} in the selected date range.")
        return
    
    # Convert to DataFrame for better visualization
    df = pd.DataFrame(entries)
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df['time'] = pd.to_datetime(df['timestamp']).dt.time
    df = df.sort_values('timestamp', ascending=False)
    
    # Display summary statistics
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
        # Mood distribution
        if 'mood' in df.columns:
            mood_counts = df['mood'].value_counts()
            dominant_mood = mood_counts.idxmax() if not mood_counts.empty else "N/A"
            st.metric("Dominant Mood", dominant_mood)
    
    # Edit existing entries
    st.subheader("📋 Health Entries")
    
    # Group entries by date
    df['date_only'] = df['timestamp'].str.split('T').str[0]
    grouped_entries = df.groupby('date_only')
    
    for date_str, date_group in grouped_entries:
        with st.expander(f"📅 {date_str} ({len(date_group)} entries)"):
            for idx, entry in date_group.iterrows():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Display entry details
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
                        st.write(f"**Frequency:** {entry.get('medication_frequency', 'N/A')}")
                        st.write(f"**Reason:** {entry.get('medication_reason', 'N/A')}")
                    
                    # Grooming tasks
                    grooming_done = [task for task, done in entry.get('grooming_tasks', {}).items() if done]
                    if grooming_done:
                        st.write(f"**Grooming:** {', '.join(grooming_done)}")
                
                with col2:
                    # Edit and delete buttons
                    if st.button("✏️ Edit", key=f"edit_entry_{idx}"):
                        # Prepare edit data
                        edit_data = {
                            'timestamp': entry['timestamp'],
                            'index': idx,
                            'cat': selected_cat
                        }
                        st.session_state.editing_health_entry = True
                        st.session_state.edit_entry_data = edit_data
                        st.rerun()
                    
                    if st.button("🗑️ Delete", key=f"delete_entry_{idx}"):
                        delete_health_entry(selected_cat, entry['timestamp'], idx)
                        st.success("Entry deleted!")
                        st.rerun()
    
    # Plot trends
    st.subheader("📊 Health Trends")
    
    if len(df) > 1:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Water Intake', 'Food Intake', 'Litter Box Usage', 'Weight'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        if 'water_drinks' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['water_drinks'], name='Water Drinks'),
                row=1, col=1
            )
        
        if 'food_eats' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['food_eats'], name='Food Eats'),
                row=1, col=2
            )
        
        if 'litter_box_times' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['litter_box_times'], name='Litter Box Uses'),
                row=2, col=1
            )
        
        fig.update_layout(height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

def task_management_page():
    """Page for managing tasks (edit only)"""
    st.header("📋 Task Management")
    
    st.subheader("✏️ Edit Existing Tasks")
    
    frequencies = ['daily', 'weekly', 'monthly']
    freq_names = ['📅 Daily', '🗓️ Weekly', '📆 Monthly']
    
    for freq, freq_name in zip(frequencies, freq_names):
        st.markdown(f"### {freq_name}")
        
        if not st.session_state.tasks[freq]:
            st.info(f"No {freq} tasks to manage.")
            continue
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            for task in st.session_state.tasks[freq]:
                # Task completion checkbox
                today = str(date.today())
                completed = False
                
                if today in st.session_state.task_logs:
                    completed_tasks = [log['task'] for log in st.session_state.task_logs[today]]
                    completed = task in completed_tasks
                
                task_key = f"task_{freq}_{task}"
                is_completed = st.checkbox(task, value=completed, key=task_key)
                
                if is_completed and not completed:
                    add_task_completion(task)
                    st.rerun()
        
        with col2:
            # Delete task button
            if st.button(f"🗑️", key=f"delete_{freq}_{task}", help="Delete task"):
                if task in st.session_state.tasks[freq]:
                    st.session_state.tasks[freq].remove(task)
                    if task in st.session_state.task_schedules[freq]:
                        del st.session_state.task_schedules[freq][task]
                    save_data()
                    st.rerun()
    
    # Task completion history
    st.markdown("---")
    st.subheader("📋 Task Completion History")
    
    # Date range for history
    col1, col2 = st.columns(2)
    
    with col1:
        history_start = st.date_input("Start Date", date.today() - timedelta(days=7))
    
    with col2:
        history_end = st.date_input("End Date", date.today())
    
    # Get task completions
    completions = get_task_completions(history_start, history_end)
    
    if not completions:
        st.info("No task completions found in the selected date range.")
        return
    
    # Create DataFrame for better visualization
    all_completions = []
    for date_str, day_logs in completions.items():
        for log in day_logs:
            all_completions.append({
                'date': date_str,
                'task': log['task'],
                'cat': log['cat'],
                'completed_at': log['completed_at'],
                'notes': log['notes']
            })
    
    df = pd.DataFrame(all_completions)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    st.dataframe(df, use_container_width=True, hide_index=True)

def ai_chat_page():
    """AI chat page using Hugging Face"""
    st.header("💬 AI Chat - Hugging Face")
    st.write("Ask me anything about cat care, health, or behavior!")
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about cat care..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Get AI response
        cat_data = {
            'cats': st.session_state.cats,
            'health_data': st.session_state.health_data,
            'profiles': st.session_state.cat_profiles
        }
        
        ai_response = call_huggingface_ai(prompt, cat_data)
        
        # Add AI response
        st.session_state.chat_messages.append({"role": "assistant", "content": ai_response})
        
        # Rerun to display the message
        st.rerun()

def dashboard_page():
    """Dashboard page with comprehensive cat health summaries"""
    st.header("🎯 Dashboard")
    
    # Quick stats for all cats
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
        st.metric("Today's Tasks", len(today_tasks))
    
    with col3:
        total_vet_visits = sum(
            len(profile.get('vet_visits', [])) 
            for profile in st.session_state.cat_profiles.values()
        )
        st.metric("Vet Visits", total_vet_visits)
    
    with col4:
        active_cats = sum(1 for cat in st.session_state.cats 
                         if cat in st.session_state.health_data 
                         and st.session_state.health_data[cat])
        st.metric("Active Cats", active_cats)
    
    # Comprehensive cat health summaries
    st.subheader("🐱 Cat Health Summaries")
    
    # Tabs for each cat
    cat_tabs = st.tabs(st.session_state.cats)
    
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            # Display cat summary
            summary = generate_cat_summary(cat)
            st.markdown(summary, unsafe_allow_html=False)

def data_management_page():
    """Page for managing data - delete, export, import"""
    st.header("⚙️ Data Management")
    
    st.warning("⚠️ **Caution:** Actions on this page can permanently delete your data!")
    
    # Export data section
    st.markdown("---")
    st.subheader("📥 Export Data")
    st.write("Download all your data as JSON files for backup.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Export Health Data", use_container_width=True):
            health_json = json.dumps(st.session_state.health_data, indent=2, default=str)
            st.download_button(
                label="💾 Download Health Data",
                data=health_json,
                file_name=f"health_data_{date.today()}.json",
                mime="application/json",
                use_container_width=True
            )
    
    with col2:
        if st.button("📥 Export Task Logs", use_container_width=True):
            tasks_json = json.dumps(st.session_state.task_logs, indent=2, default=str)
            st.download_button(
                label="💾 Download Task Logs",
                data=tasks_json,
                file_name=f"task_logs_{date.today()}.json",
                mime="application/json",
                use_container_width=True
            )
    
    with col3:
        if st.button("📥 Export Profiles", use_container_width=True):
            profiles_json = json.dumps(st.session_state.cat_profiles, indent=2, default=str)
            st.download_button(
                label="💾 Download Profiles",
                data=profiles_json,
                file_name=f"cat_profiles_{date.today()}.json",
                mime="application/json",
                use_container_width=True
            )
    
    # Delete specific data section
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
        delete_task_start = st.date_input("Start Date", key="delete_task_start")
        delete_task_end = st.date_input("End Date", key="delete_task_end")
        
        if st.button("🗑️ Delete Task Logs", type="secondary"):
            deleted_count = 0
            current = delete_task_start
            while current <= delete_task_end:
                date_str = str(current)
                if date_str in st.session_state.task_logs:
                    del st.session_state.task_logs[date_str]
                    deleted_count += 1
                current += timedelta(days=1)
            
            save_data()
            st.success(f"✅ Deleted task logs for {deleted_count} days")
            st.rerun()
    
    # Delete ALL data section
    st.markdown("---")
    st.subheader("🚨 Delete All Data")
    st.error("**WARNING:** This will permanently delete ALL data including health entries, task logs, and cat profiles!")
    
    # Confirmation checkbox
    confirm_delete = st.checkbox("I understand this action cannot be undone", key="confirm_delete_all")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🗑️ Delete ALL Health Data", type="secondary", disabled=not confirm_delete, use_container_width=True):
            st.session_state.health_data = {}
            st.session_state.last_entries = {cat: None for cat in st.session_state.cats}
            save_data()
            st.success("✅ All health data deleted!")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Delete ALL Task Logs", type="secondary", disabled=not confirm_delete, use_container_width=True):
            st.session_state.task_logs = {}
            save_data()
            st.success("✅ All task logs deleted!")
            st.rerun()
    
    # Complete reset
    st.markdown("---")
    st.subheader("🔄 Complete Reset")
    st.error("**DANGER ZONE:** This will reset EVERYTHING including profiles!")
    
    confirm_reset = st.checkbox("I want to completely reset the application", key="confirm_reset")
    
    if st.button("🔄 RESET EVERYTHING", type="secondary", disabled=not confirm_reset):
        # Delete all session state data
        st.session_state.health_data = {}
        st.session_state.task_logs = {}
        st.session_state.cat_profiles = {
            cat: {
                'age': '', 'breed': '', 'weight': '', 
                'vet_visits': [], 'notes': ''
            } for cat in st.session_state.cats
        }
        st.session_state.last_entries = {cat: None for cat in st.session_state.cats}
        st.session_state.chat_messages = []
        
        # Delete files
        try:
            if os.path.exists('health_data.json'):
                os.remove('health_data.json')
            if os.path.exists('task_logs.json'):
                os.remove('task_logs.json')
            if os.path.exists('cat_profiles.json'):
                os.remove('cat_profiles.json')
        except:
            pass
        
        st.success("✅ Application completely reset! Reloading...")
        time.sleep(1)
        st.rerun()
    
    # Statistics
    st.markdown("---")
    st.subheader("📊 Data Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_health_entries = sum(
            len(dates) 
            for cat_data in st.session_state.health_data.values() 
            for dates in cat_data.values()
        )
        st.metric("Total Health Entries", total_health_entries)
    
    with col2:
        total_task_logs = sum(len(logs) for logs in st.session_state.task_logs.values())
        st.metric("Total Task Completions", total_task_logs)
    
    with col3:
        total_vet_visits = sum(
            len(profile.get('vet_visits', [])) 
            for profile in st.session_state.cat_profiles.values()
        )
        st.metric("Total Vet Visits", total_vet_visits)

def check_reminders():
    """Check and display reminders"""
    current_time = datetime.now()
    
    if (st.session_state.last_reminder is None or 
        (current_time - st.session_state.last_reminder).days >= 1):
        
        missing_entries = []
        for cat in st.session_state.cats:
            if st.session_state.last_entries[cat] is None:
                missing_entries.append(cat)
            else:
                time_diff = current_time - st.session_state.last_entries[cat]
                if time_diff.days >= 1:
                    missing_entries.append(cat)
        
        if missing_entries:
            st.warning(f"⚠️ Reminder: No health entries for {', '.join(missing_entries)} today. Please add entries!")
        
        today = date.today()
        today_str = str(today)
        
        if today_str not in st.session_state.task_logs:
            st.session_state.task_logs[today_str] = []
        
        today_completions = [log['task'] for log in st.session_state.task_logs[today_str]]
        
        incomplete_tasks = []
        for task in st.session_state.tasks['daily']:
            if task not in today_completions:
                incomplete_tasks.append(task)
        
        if incomplete_tasks:
            st.info(f"📝 Don't forget to complete these daily tasks: {', '.join(incomplete_tasks)}")
        
        st.session_state.last_reminder = current_time

def main():
    """Main application function"""
    
    # Check authentication first
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
    
    # Show logged in user and logout button
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
        st.warning("⚠️ Authentication disabled. Upload auth_module.py to enable security.")
    
    st.sidebar.title("🧭 Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🐱 Cat Profiles", "📝 Add Health Entry", "📊 View Health Data", 
         "📋 Task Management", "💬 AI Chat", "🎯 Dashboard", "⚙️ Data Management"]
    )
    
    # Show security status in sidebar
    if AUTH_ENABLED:
        st.sidebar.success("🔐 Security: Enabled")
        st.sidebar.caption("Data is encrypted at rest")
    else:
        st.sidebar.warning("⚠️ Security: Disabled")
        st.sidebar.caption("Upload auth_module.py")
    
    # Show AI status in sidebar
    if HF_API_KEY:
        st.sidebar.success("🤖 AI: Hugging Face Enabled")
        st.sidebar.caption("Powered by Meta-Llama-3-8B-Instruct")
    else:
        st.sidebar.info("🤖 AI: Basic Mode")
        st.sidebar.caption("Add HF_API_KEY for advanced AI")
    
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
