import streamlit as st import pandas as pd import numpy as np from datetime import datetime, timedelta, date import json import os from typing import Dict, List, Optional import plotly.express as px import plotly.graph_objects as go from plotly.subplots import make_subplots import time import random

Import authentication module
try: from auth_module import ( check_authentication, login_page, logout, encrypt_data, decrypt_data ) AUTH_ENABLED = True except ImportError: AUTH_ENABLED = False st.warning("⚠️ auth_module.py not found. Authentication disabled. Upload auth_module.py to enable security.")

Hugging Face AI Integration - LINE 62-72
try: import requests HF_API_KEY = st.secrets.get("HF_API_KEY", None) # LINE 64 if HF_API_KEY: HF_BASE_URL = "https://api-inference.huggingface.co/models" HF_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct" # LINE 68 else: HF_API_KEY = None st.warning("⚠️ Hugging Face API key not found. AI chat will use basic responses.") except ImportError: HF_API_KEY = None

Initialize session state
def init_session_state(): """Initialize all session state variables""" if 'cats' not in st.session_state: st.session_state.cats = ['Haku', 'Kuro', 'Sonic']

Code

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
Data persistence functions
def save_data(): """Save all data to files with encryption""" try: # Prepare data for saving health_data_str = json.dumps(st.session_state.health_data, default=str) task_logs_str = json.dumps(st.session_state.task_logs, default=str) profiles_str = json.dumps(st.session_state.cat_profiles, default=str)

Code

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
def load_data(): """Load data from files with decryption""" try: if os.path.exists('health_data.json'): with open('health_data.json', 'r') as f: data_str = f.read() if AUTH_ENABLED and data_str: try: data_str = decrypt_data(data_str) except: pass # Data might not be encrypted yet if data_str: st.session_state.health_data = json.loads(data_str)

Code

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
Health entry functions - NEW IMPROVED SYSTEM
def add_health_entry(cat_name: str, entry_data: Dict): """Add a health entry for a specific cat with timestamp""" if cat_name not in st.session_state.health_data: st.session_state.health_data[cat_name] = {}

Code

# Use current timestamp as unique key
timestamp = datetime.now().isoformat()

if timestamp not in st.session_state.health_data[cat_name]:
    st.session_state.health_data[cat_name][timestamp] = []

entry_data['timestamp'] = timestamp
st.session_state.health_data[cat_name][timestamp].append(entry_data)
st.session_state.last_entries[cat_name] = datetime.now()
save_data()
def get_health_entries(cat_name: str, start_date: date, end_date: date) -> List[Dict]: """Get health entries for a cat within date range""" entries = [] if cat_name in st.session_state.health_data: for timestamp, date_entries in st.session_state.health_data[cat_name].items(): entry_date = datetime.fromisoformat(timestamp).date() if start_date <= entry_date <= end_date: for entry in date_entries: entry['timestamp'] = timestamp entries.append(entry) return entries

def update_health_entry(cat_name: str, timestamp: str, entry_index: int, updated_data: Dict): """Update a specific health entry""" if cat_name in st.session_state.health_data and timestamp in st.session_state.health_data[cat_name]: if entry_index < len(st.session_state.health_data[cat_name][timestamp]): st.session_state.health_data[cat_name][timestamp][entry_index].update(updated_data) save_data()

def delete_health_entry(cat_name: str, timestamp: str, entry_index: int): """Delete a specific health entry""" if cat_name in st.session_state.health_data and timestamp in st.session_state.health_data[cat_name]: if entry_index < len(st.session_state.health_data[cat_name][timestamp]): st.session_state.health_data[cat_name][timestamp].pop(entry_index) if not st.session_state.health_data[cat_name][timestamp]: del st.session_state.health_data[cat_name][timestamp] save_data()

Task management functions
def add_task_completion(task_name: str, cat_name: str = None, notes: str = ""): """Add a task completion entry""" today = str(date.today()) if today not in st.session_state.task_logs: st.session_state.task_logs[today] = []

Code

task_entry = {
    'task': task_name,
    'cat': cat_name,
    'completed_at': datetime.now().isoformat(),
    'notes': notes
}
st.session_state.task_logs[today].append(task_entry)
save_data()
def get_task_completions(start_date: date, end_date: date) -> Dict: """Get task completions within date range""" completions = {} for date_str, day_logs in st.session_state.task_logs.items(): log_date = datetime.fromisoformat(date_str).date() if start_date <= log_date <= end_date: completions[date_str] = day_logs return completions

Hugging Face AI Integration Functions - LINE 392-422
def call_huggingface_ai(user_message: str, cat_data: Dict = None) -> str: """Call Hugging Face API for intelligent responses""" if not HF_API_KEY: # LINE 394 return get_fallback_ai_response(user_message, cat_data) # LINE 395

Code

try:
    # Prepare prompt with context
    context = f"""You are an ethical AI assistant specializing in cat care and health. You have access to the following cat data:
    
Cats: {cat_data.get('cats', [])} Health Data: {cat_data.get('health_data', {})} Profiles: {cat_data.get('profiles', {})}

User Question: {user_message}

Please provide helpful, ethical, and accurate advice about cat care. Focus on the wellbeing of the cats and responsible pet ownership. If you don't have specific information about the cats, provide general best practices for cat care.

Response:"""

Code

    payload = {"inputs": context, "parameters": {"max_new_tokens": 500, "temperature": 0.7}}
    
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",  # LINE 413
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{HF_BASE_URL}/{HF_MODEL}",  # LINE 417
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
def get_fallback_ai_response(user_message: str, cat_data: Dict = None) -> str: """Fallback AI response using basic logic""" message_lower = user_message.lower()

Code

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
AI Analysis Functions
def analyze_cat_health(cat_name: str) -> Dict: """Analyze health data for a specific cat with profile integration""" if cat_name not in st.session_state.health_data: return {'status': 'no_data', 'message': 'No health data available'}

Code

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
    'recommendations': []
}

# Analyze week entries
water_total = 0
food_total = 0
litter_count = 0

for entry in week_entries:
    if 'water_mls' in entry:
        water_total += entry['water_mls']
    if 'food_grams' in entry:
        food_total += entry['food_grams']
    if 'litter_changes' in entry:
        litter_count += entry['litter_changes']
    if 'medication' in entry and entry['medication']:
        analysis['medications'].append(entry['medication'])
    if 'mood' in entry and entry['mood'] in ['sad', 'sick', 'tired']:
        analysis['concerns'].append(f"Unusual mood: {entry['mood']}")
    if 'litter_quality' in entry and entry['litter_quality'] == 'poor':
        analysis['litter_quality_issues'].append(f"Poor litter quality on {entry['timestamp']}")

# Calculate averages
if week_entries:
    analysis['water_avg'] = water_total / len(week_entries)
    analysis['food_avg'] = food_total / len(week_entries)
    analysis['litter_usage'] = litter_count

# Check for concerns
if analysis['water_avg'] < 30:
    analysis['concerns'].append("Low water intake detected")
if analysis['food_avg'] < 20:
    analysis['concerns'].append("Low food intake detected")

# Generate recommendations
if not analysis['concerns']:
    analysis['recommendations'] = ["Great job monitoring your cat's health!"]
else:
    analysis['recommendations'] = [
        "Monitor water intake more closely",
        "Consider wet food for hydration",
        "Check litter box cleanliness daily"
    ]

return analysis
def generate_cat_summary(cat_name: str) -> str: """Generate a comprehensive cat health summary""" analysis = analyze_cat_health(cat_name) profile = st.session_state.cat_profiles.get(cat_name, {})

Code

summary = f"""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px;">
    <h3 style="margin: 0; font-size: 24px;">🐱 {cat_name}</h3>
    <p style="margin: 5px 0; opacity: 0.9;">Comprehensive Health Overview</p>
</div>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #28a745;">
        <h4 style="margin: 0; color: #28a745;">✅ Status</h4>
        <p style="margin: 5px 0; font-weight: bold;">{analysis['status'].replace('_', ' ').title()}</p>
    </div>
    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #007bff;">
        <h4 style="margin: 0; color: #007bff;">📊 Entries</h4>
        <p style="margin: 5px 0; font-weight: bold;">{analysis['total_entries']} this week</p>
    </div>
    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #17a2b8;">
        <h4 style="margin: 0; color: #17a2b8;">💧 Water</h4>
        <p style="margin: 5px 0; font-weight: bold;">{analysis['water_avg']:.1f}ml avg/day</p>
    </div>
    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid #ffc107;">
        <h4 style="margin: 0; color: #ffc107;">🍽️ Food</h4>
        <p style="margin: 5px 0; font-weight: bold;">{analysis['food_avg']:.1f}g avg/day</p>
    </div>
</div>

<div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
    <h4 style="margin: 0 0 10px 0; color: #495057;">📋 Profile Information</h4>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div><strong>Age:</strong> {profile.get('age', 'Not set')}</div>
        <div><strong>Breed:</strong> {profile.get('breed', 'Not set')}</div>
        <div><strong>Weight:</strong> {profile.get('weight', 'Not set')}</div>
        <div><strong>Vet Visits:</strong> {len(profile.get('vet_visits', []))}</div>
    </div>
</div>
"""

if analysis['concerns']:
    summary += f"""
    <div style="background: #fff3cd; padding: 20px; border-radius: 10px; border-left: 4px solid #ffc107; margin-bottom: 20px;">
        <h4 style="margin: 0 0 10px 0; color: #856404;">⚠️ Concerns</h4>
        <ul style="margin: 0; padding-left: 20px;">
            {''.join([f'<li>{concern}</li>' for concern in analysis['concerns']])}
        </ul>
    </div>
    """

if analysis['recommendations']:
    summary += f"""
    <div style="background: #d1ecf1; padding: 20px; border-radius: 10px; border-left: 4px solid #17a2b8;">
        <h4 style="margin: 0 0 10px 0; color: #0c5460;">💡 Recommendations</h4>
        <ul style="margin: 0; padding-left: 20px;">
            {''.join([f'<li>{rec}</li>' for rec in analysis['recommendations']])}
        </ul>
    </div>
    """

return summary
Page Functions
def cat_profiles_page(): """Cat profiles page with improved layout and vet visit functionality""" st.header("🐱 Cat Profiles")

Code

# Add new cat button
col1, col2 = st.columns([4, 1])
with col1:
    st.subheader("Your Cats")
with col2:
    if len(st.session_state.cats) < 5:  # Limit to 5 cats
        if st.button("➕ Add Cat", use_container_width=True):
            st.session_state.cats.append(f"New Cat {len(st.session_state.cats) + 1}")
            st.session_state.cat_profiles[f"New Cat {len(st.session_state.cats)}"] = {
                'age': '', 'breed': '', 'weight': '', 
                'vet_visits': [], 'notes': ''
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
                <div><strong>Weight:</strong> {st.session_state.cat_profiles[cat]['weight'] or 'Not set'}</div>
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
                col_a, col_b, col_c = st.columns([2, 3, 1])
                with col_a:
                    st.write(f"**{visit['date']}**")
                with col_b:
                    st.write(visit.get('notes', 'No notes'))
                with col_c:
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
def add_health_entry_page(): """Page for adding health entries""" st.header("📝 Add Health Entry")

Code

cat_selector = st.selectbox("Select Cat", st.session_state.cats)

# Date selection
entry_date = st.date_input("Date", value=date.today())

# Health metrics - FIXED: Removed weight as requested
col1, col2 = st.columns(2)

with col1:
    water_mls = st.number_input("Water (ml)", min_value=0, max_value=1000, value=100)
    food_grams = st.number_input("Food (grams)", min_value=0, max_value=500, value=50)
    litter_changes = st.number_input("Litter Changes", min_value=0, max_value=5, value=1)

with col2:
    mood = st.selectbox("Mood", ["happy", "normal", "sad", "sick", "tired"])
    medication = st.text_input("Medication (if any)")
    litter_quality = st.selectbox("Litter Quality", ["good", "fair", "poor"])

# Additional notes
notes = st.text_area("Additional Notes")

if st.button("💾 Add Entry", type="primary"):
    entry_data = {
        'date': str(entry_date),
        'water_mls': water_mls,
        'food_grams': food_grams,
        'litter_changes': litter_changes,
        'mood': mood,
        'medication': medication,
        'litter_quality': litter_quality,
        'notes': notes
    }
    
    add_health_entry(cat_selector, entry_data)
    st.success(f"✅ Health entry added for {cat_selector}")
    st.rerun()
def view_health_data_page(): """Page for viewing and managing health data""" st.header("📊 View Health Data")

Code

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

# Create a unique key for each entry
for idx, entry in enumerate(all_entries):
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.write(f"**{entry['cat']} - {entry['date']}**")
        st.write(f"💧 Water: {entry.get('water_mls', 'N/A')}ml | 🍽️ Food: {entry.get('food_grams', 'N/A')}g")
        st.write(f"🚽 Litter: {entry.get('litter_changes', 'N/A')} changes | 😊 Mood: {entry.get('mood', 'N/A')}")
        if entry.get('medication'):
            st.write(f"💊 Medication: {entry['medication']}")
        if entry.get('notes'):
            st.write(f"📝 Notes: {entry['notes']}")
    
    with col2:
        if st.button("✏️ Edit", key=f"edit_entry_{idx}"):
            st.session_state.editing_health_entry = True
            st.session_state.edit_entry_data = entry
            st.session_state.edit_entry_cat = entry['cat']
            st.session_state.edit_entry_date = entry['date']
            st.rerun()
    
    with col3:
        if st.button("🗑️ Delete", key=f"delete_entry_{idx}"):
            # Find the original timestamp and index
            for timestamp, date_entries in st.session_state.health_data[entry['cat']].items():
                for j, date_entry in enumerate(date_entries):
                    if (date_entry.get('date') == entry['date'] and 
                        date_entry.get('water_mls') == entry.get('water_mls') and
                        date_entry.get('food_grams') == entry.get('food_grams')):
                        delete_health_entry(entry['cat'], timestamp, j)
                        st.success(f"✅ Entry deleted for {entry['cat']}")
                        st.rerun()

# Edit form (appears when editing)
if st.session_state.editing_health_entry:
    st.markdown("---")
    st.subheader("✏️ Edit Health Entry")
    
    with st.form("edit_health_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            water_mls = st.number_input("Water (ml)", min_value=0, max_value=1000, 
                                      value=st.session_state.edit_entry_data.get('water_mls', 100))
            food_grams = st.number_input("Food (grams)", min_value=0, max_value=500,
                                       value=st.session_state.edit_entry_data.get('food_grams', 50))
            litter_changes = st.number_input("Litter Changes", min_value=0, max_value=5,
                                           value=st.session_state.edit_entry_data.get('litter_changes', 1))
        
        with col2:
            mood = st.selectbox("Mood", ["happy", "normal", "sad", "sick", "tired"],
                              index=["happy", "normal", "sad", "sick", "tired"].index(
                                  st.session_state.edit_entry_data.get('mood', 'normal')))
            medication = st.text_input("Medication (if any)",
                                     value=st.session_state.edit_entry_data.get('medication', ''))
            litter_quality = st.selectbox("Litter Quality", ["good", "fair", "poor"],
                                        index=["good", "fair", "poor"].index(
                                            st.session_state.edit_entry_data.get('litter_quality', 'good')))
            notes = st.text_area("Additional Notes",
                               value=st.session_state.edit_entry_data.get('notes', ''))
        
        if st.form_submit_button("Save Changes"):
            updated_data = {
                'date': st.session_state.edit_entry_date,
                'water_mls': water_mls,
                'food_grams': food_grams,
                'litter_changes': litter_changes,
                'mood': mood,
                'medication': medication,
                'litter_quality': litter_quality,
                'notes': notes
            }
            
            # Find and update the entry
            for timestamp, date_entries in st.session_state.health_data[st.session_state.edit_entry_cat].items():
                for j, date_entry in enumerate(date_entries):
                    if (date_entry.get('date') == st.session_state.edit_entry_date and 
                        date_entry.get('water_mls') == st.session_state.edit_entry_data.get('water_mls') and
                        date_entry.get('food_grams') == st.session_state.edit_entry_data.get('food_grams')):
                        update_health_entry(st.session_state.edit_entry_cat, timestamp, j, updated_data)
                        break
            
            # Reset editing state
            st.session_state.editing_health_entry = False
            st.session_state.edit_entry_data = {}
            st.session_state.edit_entry_cat = None
            st.session_state.edit_entry_date = None
            
            st.success(f"✅ Health entry updated for {st.session_state.edit_entry_cat}")
            st.rerun()
        
        if st.form_submit_button("Cancel"):
            st.session_state.editing_health_entry = False
            st.session_state.edit_entry_data = {}
            st.session_state.edit_entry_cat = None
            st.session_state.edit_entry_date = None
            st.rerun()
def task_management_page(): """Page for managing tasks (edit only)""" st.header("📋 Task Management")

Code

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
    history_start = st.date_input("Start Date", value=date.today() - timedelta(days=7))

with col2:
    history_end = st.date_input("End Date", value=date.today())

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
def ai_chat_page(): """AI chat page using Hugging Face""" st.header("💬 AI Chat - Hugging Face") st.write("Ask me anything about cat care, health, or behavior!")

Code

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
def dashboard_page(): """Dashboard page with comprehensive cat health summaries""" st.header("🎯 Dashboard")

Code

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

# Health trends chart
st.subheader("📈 Health Trends")

# Get data for the last 7 days
end_date = date.today()
start_date = end_date - timedelta(days=6)

chart_data = []
for cat in st.session_state.cats:
    entries = get_health_entries(cat, start_date, end_date)
    for entry in entries:
        chart_data.append({
            'cat': cat,
            'date': entry['date'],
            'water': entry.get('water_mls', 0),
            'food': entry.get('food_grams', 0)
        })

if chart_data:
    df = pd.DataFrame(chart_data)
    df['date'] = pd.to_datetime(df['date'])
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Water Intake (ml)', 'Food Intake (grams)'),
        vertical_spacing=0.1
    )
    
    # Water chart
    for cat in st.session_state.cats:
        cat_data = df[df['cat'] == cat]
        if not cat_data.empty:
            fig.add_trace(
                go.Scatter(x=cat_data['date'], y=cat_data['water'], 
                         name=f'{cat} - Water', mode='lines+markers'),
                row=1, col=1
            )
    
    # Food chart
    for cat in st.session_state.cats:
        cat_data = df[df['cat'] == cat]
        if not cat_data.empty:
            fig.add_trace(
                go.Scatter(x=cat_data['date'], y=cat_data['food'], 
                         name=f'{cat} - Food', mode='lines+markers'),
                row=2, col=1
            )
    
    fig.update_layout(height=600, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

# Comprehensive cat health summaries
st.subheader("🐱 Cat Health Summaries")

# Tabs for each cat
cat_tabs = st.tabs(st.session_state.cats)

for i, cat in enumerate(st.session_state.cats):
    with cat_tabs[i]:
        # Display cat summary
        summary = generate_cat_summary(cat)
        st.markdown(summary, unsafe_allow_html=False)
def data_management_page(): """Page for managing data - delete, export, import""" st.header("⚙️ Data Management")

Code

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
def check_reminders(): """Check and display reminders""" current_time = datetime.now()

Code

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
def main(): """Main application function"""

Code

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
if name == "main": main()_
