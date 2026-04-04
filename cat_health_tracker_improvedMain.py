```python
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

# Thaura AI integration (replacing other AI providers)
try:
    import requests
    THAURA_API_KEY = st.secrets.get("THAURA_API_KEY", None)
    if THAURA_API_KEY:
        THAURA_BASE_URL = "https://api.thaura.ai/v1"
    else:
        THAURA_API_KEY = None
        st.warning("⚠️ Thaura API key not found. AI chat will use basic responses.")
except ImportError:
    THAURA_API_KEY = None

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
                'Let them out my room', 'Leave them alone'
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
                     'Let them out my room': 2, 'Leave them alone': 1},
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

# Health entry functions
def add_health_entry(cat_name: str, date: date, entry_data: Dict):
    """Add a health entry for a specific cat"""
    if cat_name not in st.session_state.health_data:
        st.session_state.health_data[cat_name] = {}
    
    if str(date) not in st.session_state.health_data[cat_name]:
        st.session_state.health_data[cat_name][str(date)] = []
    
    entry_data['timestamp'] = datetime.now().isoformat()
    st.session_state.health_data[cat_name][str(date)].append(entry_data)
    st.session_state.last_entries[cat_name] = datetime.now()
    save_data()

def get_health_entries(cat_name: str, start_date: date, end_date: date) -> List[Dict]:
    """Get health entries for a cat within date range"""
    entries = []
    if cat_name in st.session_state.health_data:
        for date_str, date_entries in st.session_state.health_data[cat_name].items():
            entry_date = datetime.fromisoformat(date_str).date()
            if start_date <= entry_date <= end_date:
                for entry in date_entries:
                    entry['date'] = date_str
                    entries.append(entry)
    return entries

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

# Thaura AI Integration Functions
def call_thaura_ai(user_message: str, cat_data: Dict = None) -> str:
    """Call Thaura AI API for intelligent responses"""
    if not THAURA_API_KEY:
        return get_fallback_ai_response(user_message, cat_data)
    
    try:
        # Prepare context for Thaura
        context = {
            "user_message": user_message,
            "cat_data": cat_data,
            "app_purpose": "cat health tracking and management"
        }
        
        headers = {
            "Authorization": f"Bearer {THAURA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{THAURA_BASE_URL}/chat",
            json={"message": user_message, "context": context},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "I'm sorry, I couldn't process your request.")
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
                        'date': entry.get('date'),
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
        weight = profile.get('weight', '')
        if weight:
            analysis['recommendations'].append(f"Cat should drink ~{float(weight) * 50 if weight.replace('.', '').isdigit() else 150}ml of water daily. Consider adding water fountains or wet food.")
        else:
            analysis['recommendations'].append('Consider adding more water sources or wet food')
    
    if analysis['food_avg'] < 2:
        analysis['concerns'].append('Low food intake detected')
        analysis['recommendations'].append('Monitor appetite and consider vet consultation if persists')
    
    if analysis['litter_usage'] > 5:
        analysis['concerns'].append('Frequent litter box usage')
        analysis['recommendations'].append('Monitor for urinary tract issues or stress. Check recent vet visits.')
    
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
    if profile.get('age') or profile.get('breed') or profile.get('weight'):
        summary += "**Profile:**\n"
        if profile.get('age'):
            summary += f"- Age: {profile['age']}\n"
        if profile.get('breed'):
            summary += f"- Breed: {profile['breed']}\n"
        if profile.get('weight'):
            summary += f"- Weight: {profile['weight']} kg\n"
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
    """Page for managing cat profiles"""
    st.header("🐱 Cat Profiles")
    
    # Display cat profiles
    for cat in st.session_state.cats:
        profile = st.session_state.cat_profiles[cat]
        
        with st.expander(f"🐱 {cat}", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                age = st.text_input("Age", value=profile.get('age', ''), placeholder="e.g., 3 years", key=f"age_{cat}")
                breed = st.text_input("Breed", value=profile.get('breed', ''), placeholder="e.g., Persian", key=f"breed_{cat}")
                weight = st.text_input("Weight (kg)", value=profile.get('weight', ''), placeholder="e.g., 4.5", key=f"weight_{cat}")
            
            with col2:
                st.write("**Vet Visits:**")
                vet_count = len(profile.get('vet_visits', []))
                st.write(f"**Vet Visits:** {vet_count}")
                
                if st.button(f"✏️ Edit Profile", key=f"edit_{cat}", use_container_width=True):
                    st.session_state.editing_cat = cat
                    st.rerun()
                
                st.markdown("---")
    
    # Edit form in expandable section (cleaner layout)
    if 'editing_cat' in st.session_state:
        selected_cat = st.session_state.editing_cat
        
        st.markdown("---")
        st.markdown(f"## ✏️ Editing: **{selected_cat}**")
        
        profile = st.session_state.cat_profiles[selected_cat]
        
        # Create tabs for better organization
        tab1, tab2 = st.tabs(["📋 Basic Info", "🏥 Vet Visits"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                age = st.text_input("Age", value=profile.get('age', ''), placeholder="e.g., 3 years", key="edit_age")
                breed = st.text_input("Breed", value=profile.get('breed', ''), placeholder="e.g., Persian", key="edit_breed")
            
            with col2:
                weight = st.text_input("Weight (kg)", value=profile.get('weight', ''), placeholder="e.g., 4.5", key="edit_weight")
                notes = st.text_area("Additional Notes", value=profile.get('notes', ''), 
                                   placeholder="Any special notes about your cat...", key="edit_notes", height=100)
        
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
                visit_to_delete = st.selectbox("Select visit to delete", [""] + visit_options, key="delete_visit_select")
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if visit_to_delete and st.button("🗑️ Delete", type="secondary"):
                        idx = visit_options.index(visit_to_delete)
                        vet_visits.pop(idx)
                        st.session_state.cat_profiles[selected_cat]['vet_visits'] = vet_visits
                        save_data()
                        st.success("Visit deleted!")
                        st.rerun()
            else:
                st.info("No vet visits recorded yet.")
            
            st.markdown("---")
            st.markdown("### ➕ Add New Vet Visit")
            
            col1, col2 = st.columns(2)
            
            with col1:
                visit_date = st.date_input("Visit Date", key="new_visit_date")
                visit_doctor = st.text_input("Doctor Name", key="new_visit_doctor", placeholder="Dr. Smith")
            
            with col2:
                visit_reason = st.text_input("Reason for Visit", key="new_visit_reason", 
                                            placeholder="Annual checkup, vaccination, etc.")
                visit_medication = st.text_input("Medication Prescribed (optional)", 
                                               key="new_visit_medication", 
                                               placeholder="e.g., Antibiotics 5mg")
            
            if st.button("➕ Add Vet Visit", type="secondary", use_container_width=True):
                if visit_doctor and visit_reason:
                    new_visit = {
                        'date': str(visit_date),
                        'doctor': visit_doctor,
                        'reason': visit_reason,
                        'medication': visit_medication if visit_medication else None
                    }
                    
                    if 'vet_visits' not in st.session_state.cat_profiles[selected_cat]:
                        st.session_state.cat_profiles[selected_cat]['vet_visits'] = []
                    
                    st.session_state.cat_profiles[selected_cat]['vet_visits'].append(new_visit)
                    save_data()
                    st.success("✅ Vet visit added!")
                    st.rerun()
                else:
                    st.error("Please fill in doctor name and reason.")
        
        # Save and Cancel buttons at the bottom
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("💾 Save Profile", type="primary", use_container_width=True):
                st.session_state.cat_profiles[selected_cat]['age'] = age
                st.session_state.cat_profiles[selected_cat]['breed'] = breed
                st.session_state.cat_profiles[selected_cat]['weight'] = weight
                st.session_state.cat_profiles[selected_cat]['notes'] = notes
                save_data()
                st.success(f"✅ Profile updated for {selected_cat}!")
                time.sleep(0.5)
                del st.session_state.editing_cat
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                del st.session_state.editing_cat
                st.rerun()

def add_health_entry_page():
    """Page for adding health entries"""
    st.header("📝 Add Health Entry")
    
    # Date selection
    entry_date = st.date_input("Entry Date", date.today())
    
    # Cat selection
    selected_cat = st.selectbox("Select Cat", st.session_state.cats)
    
    # Health entry form
    with st.form("health_entry_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Basic health metrics
            water_drinks = st.number_input("Water Drinks", min_value=0, max_value=20, value=0)
            food_eats = st.number_input("Food Eats", min_value=0, max_value=10, value=0)
            weight = st.number_input("Weight (kg)", min_value=0.0, max_value=20.0, value=0.0, step=0.1)
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
        
        # Grooming tasks (NOT daily)
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
                'weight': weight,
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
            add_health_entry(selected_cat, entry_date, entry_data)
            st.success(f"✅ Health entry saved for {selected_cat}!")
            st.rerun()

def view_health_data_page():
    """Page for viewing health data"""
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
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
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
        
        if 'weight' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['date'], y=df['weight'], name='Weight (kg)'),
                row=2, col=2
            )
        
        fig.update_layout(height=600, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table view
    st.subheader("📋 Detailed Entries")
    
    # Display entries in a nice table
    display_df = df.copy()
    
    # Convert lists to strings for display
    if 'litter_quality' in display_df.columns:
        display_df['litter_quality'] = display_df['litter_quality'].apply(
            lambda x: ', '.join(x) if isinstance(x, list) else str(x)
        )
    
    # Select important columns for display
    important_cols = ['date', 'water_drinks', 'food_eats', 'litter_box_times', 'mood', 'notes']
    available_cols = [col for col in important_cols if col in display_df.columns]
    
    if available_cols:
        st.dataframe(display_df[available_cols], use_container_width=True, hide_index=True)
    else:
        st.dataframe(display_df, use_container_width=True, hide_index=True)

def task_management_page():
    """Page for managing tasks"""
    st.header("📋 Task Management")
    
    # Task editing section
    st.subheader("✏️ Manage Tasks")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.session_state.new_task_name = st.text_input("New Task Name", 
                                                     placeholder="e.g., Clean toys",
                                                     key="new_task_input")
    
    with col2:
        st.session_state.new_task_frequency = st.selectbox(
            "Frequency", 
            ["daily", "weekly", "monthly"], 
            key="new_task_frequency"
        )
    
    with col3:
        if st.button("➕ Add Task", type="primary", use_container_width=True):
            if st.session_state.new_task_name.strip():
                task_name = st.session_state.new_task_name.strip()
                frequency = st.session_state.new_task_frequency
                
                if task_name not in st.session_state.tasks[frequency]:
                    st.session_state.tasks[frequency].append(task_name)
                    st.session_state.task_schedules[frequency][task_name] = 1
                    save_data()
                    st.success(f"✅ Added '{task_name}' to {frequency} tasks!")
                    st.rerun()
                else:
                    st.warning(f"'{task_name}' already exists in {frequency} tasks!")
            else:
                st.error("Please enter a task name!")
    
    # Display tasks by frequency
    frequencies = ['daily', 'weekly', 'monthly']
    freq_names = ['📅 Daily', '🗓️ Weekly', '📆 Monthly']
    
    for freq, freq_name in zip(frequencies, freq_names):
        st.markdown(f"### {freq_name}")
        
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
    """AI chat page using Thaura"""
    st.header("💬 AI Chat - Thaura")
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
        
        ai_response = call_thaura_ai(prompt, cat_data)
        
        # Add AI response
        st.session_state.chat_messages.append({"role": "assistant", "content": ai_response})
        
        # Rerun to display the message
        st.rerun()

def dashboard_page():
    """Dashboard page with cat health preview only"""
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
    
    # Cat health preview
    st.subheader("🐱 Cat Health Preview")
    
    # Tabs for each cat
    cat_tabs = st.tabs(st.session_state.cats)
    
    for i, cat in enumerate(st.session_state.cats):
        with cat_tabs[i]:
            # Get cat analysis
            analysis = analyze_cat_health(cat)
            
            if analysis.get('status') == 'no_data':
                st.info(f"No health data available for {cat}.")
                st.write("📝 Go to 'Add Health Entry' to start tracking!")
                continue
            
            # Cat profile summary
            profile = analysis.get('profile', {})
            with st.expander("📋 Profile", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Age:** {profile.get('age', 'Not set')}")
                    st.write(f"**Breed:** {profile.get('breed', 'Not set')}")
                
                with col2:
                    st.write(f"**Weight:** {profile.get('weight', 'Not set')}")
                    st.write(f"**Vet Visits:** {len(profile.get('vet_visits', []))}")
            
            # Health stats
            with st.expander("📈 Health Stats"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Water/Day", f"{analysis['water_avg']:.1f}")
                
                with col2:
                    st.metric("Food/Day", f"{analysis['food_avg']:.1f}")
                
                with col3:
                    st.metric("Litter/Day", f"{analysis['litter_usage']:.1f}")
            
            # Mood indicator
            mood_color = {
                'improving': '✅',
                'stable': '🟡',
                'declining': '⚠️'
            }.get(analysis['mood_trend'], '🟡')
            
            st.write(f"{mood_color} **Mood Trend:** {analysis['mood_trend'].title()}")
            
            # Recent concerns
            if analysis['concerns']:
                st.warning(f"⚠️ **Concerns:** {', '.join(analysis['concerns'][:2])}")
            else:
                st.success("✅ No major concerns detected")
            
            # Quick actions
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(f"📝 Add Entry", key=f"add_entry_{cat}", use_container_width=True):
                    st.session_state.selected_cat = cat
                    st.switch_page("pages/1_Add_Health_Entry.py")
            
            with col2:
                if st.button(f"📊 View Details", key=f"view_details_{cat}", use_container_width=True):
                    st.session_state.selected_cat = cat
                    st.switch_page("pages/2_View_Health_Data.py")

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
