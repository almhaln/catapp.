import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import json
import requests
from datetime import datetime, timedelta
import hashlib
import bcrypt
import os
from cryptography.fernet import Fernet
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import random
import re

# Initialize encryption
if 'encryption_key' not in st.session_state:
    # In production, you should load this from environment variables or secure storage
    st.session_state.encryption_key = Fernet.generate_key()
st.session_state.cipher = Fernet(st.session_state.encryption_key)

# Database initialization
def init_db():
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    
    # Users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Cats table
    c.execute('''
    CREATE TABLE IF NOT EXISTS cats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT NOT NULL,
        age TEXT,
        breed TEXT,
        weight REAL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Health entries table
    c.execute('''
    CREATE TABLE IF NOT EXISTS health_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cat_id INTEGER,
        entry_date DATE DEFAULT CURRENT_DATE,
        weight REAL,
        water_consumption REAL,
        food_consumption REAL,
        activity_level TEXT,
        symptoms TEXT,
        medications TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cat_id) REFERENCES cats (id)
    )
    ''')
    
    # Vet visits table
    c.execute('''
    CREATE TABLE IF NOT EXISTS vet_visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cat_id INTEGER,
        visit_date DATE,
        vet_name TEXT,
        reason TEXT,
        diagnosis TEXT,
        treatment TEXT,
        medications TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cat_id) REFERENCES cats (id)
    )
    ''')
    
    # Tasks table
    c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cat_id INTEGER,
        task_name TEXT NOT NULL,
        task_type TEXT NOT NULL,
        frequency TEXT NOT NULL,
        last_completed DATE,
        next_due DATE,
        completed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cat_id) REFERENCES cats (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Authentication functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def get_user_id(username):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# AI Integration with Hugging Face
def initialize_huggingface_agent():
    """Initialize Hugging Face agent with Mistral 7B"""
    # This is where you'd add your Hugging Face API configuration
    # For now, we'll use a mock implementation
    return True

def get_ai_response(user_input, cat_name=None, context=None):
    """Get AI response from Hugging Face Mistral 7B"""
    try:
        # Initialize agent if not done
        if 'hf_agent' not in st.session_state:
            st.session_state.hf_agent = initialize_huggingface_agent()
        
        if not st.session_state.hf_agent:
            return "AI agent is not available. Please check your API configuration."
        
        # Prepare context
        context_str = ""
        if cat_name:
            context_str += f"Cat's name: {cat_name}\n"
        if context:
            context_str += f"Context: {context}\n"
        
        # Construct prompt
        prompt = f"""
You are an expert feline health assistant. Provide helpful, accurate information about cat health and care.

{context_str}

User question: {user_input}

Please provide:
1. A clear, informative response about the specific cat health concern
2. Practical advice that can be implemented immediately
3. When to seek veterinary attention
4. General care tips related to the issue

Response:
"""
        
        # Mock response - replace with actual Hugging Face API call
        # This is where you'd integrate with Hugging Face Mistral 7B
        mock_responses = {
            "weight": "Weight monitoring is crucial for cat health. A sudden change of more than 10% can indicate health issues. Weigh your cat regularly, ideally at the same time each day. Track trends over time rather than single measurements.",
            "vomiting": " occasional vomiting can be normal, but frequent vomiting requires attention. Withhold food for 12 hours, then offer small frequent meals of bland food. If vomiting persists for more than 24 hours or is accompanied by other symptoms, consult your veterinarian.",
            "diarrhea": "Withhold food for 12 hours, then offer small frequent meals of boiled chicken and rice. Ensure your cat stays hydrated. If diarrhea persists for more than 24-48 hours, contains blood, or your cat shows other symptoms, seek veterinary care.",
            "lethargy": "Lethargy can indicate various health issues. Monitor for other symptoms like changes in appetite, vomiting, or difficulty breathing. If lethargy persists for more than 24 hours or worsens, consult your veterinarian.",
            "urination": "Changes in urination patterns can indicate urinary tract issues, kidney problems, or diabetes. Monitor frequency, volume, and color. If you notice straining, blood in urine, or increased frequency, seek veterinary attention promptly.",
            "general": "For general cat care, ensure regular veterinary check-ups, proper nutrition, fresh water, and mental stimulation. Monitor your cat's behavior and litter box habits regularly, as changes can indicate health issues."
        }
        
        # Return appropriate response based on keywords
        for keyword, response in mock_responses.items():
            if keyword.lower() in user_input.lower():
                return response
        
        return "I'd be happy to help with your cat's health. Could you provide more specific details about what you're concerned about? For example, are you noticing changes in behavior, appetite, litter box habits, or other symptoms?"
        
    except Exception as e:
        return f"Sorry, I'm experiencing technical difficulties. Please try again later. Error: {str(e)}"

# Database operations
def add_cat(name, age, breed, weight, notes, user_id):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO cats (user_id, name, age, breed, weight, notes) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, name, age, breed, weight, notes))
    conn.commit()
    conn.close()

def get_cats(user_id):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT id, name, age, breed, weight, notes FROM cats WHERE user_id = ?", (user_id,))
    cats = c.fetchall()
    conn.close()
    return cats

def get_cat_details(cat_id):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT id, name, age, breed, weight, notes FROM cats WHERE id = ?", (cat_id,))
    cat = c.fetchone()
    conn.close()
    return cat

def update_cat(cat_id, name, age, breed, weight, notes):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE cats SET name = ?, age = ?, breed = ?, weight = ?, notes = ? WHERE id = ?",
              (name, age, breed, weight, notes, cat_id))
    conn.commit()
    conn.close()

def add_health_entry(cat_id, weight, water, food, activity, symptoms, medications, notes):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO health_entries (cat_id, weight, water_consumption, food_consumption, activity_level, symptoms, medications, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (cat_id, weight, water, food, activity, symptoms, medications, notes))
    conn.commit()
    conn.close()

def get_health_entries(cat_id, days=30):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM health_entries WHERE cat_id = ? ORDER BY entry_date DESC LIMIT ?", 
              (cat_id, days))
    entries = c.fetchall()
    conn.close()
    return entries

def add_vet_visit(cat_id, visit_date, vet_name, reason, diagnosis, treatment, medications, notes):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO vet_visits (cat_id, visit_date, vet_name, reason, diagnosis, treatment, medications, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (cat_id, visit_date, vet_name, reason, diagnosis, treatment, medications, notes))
    conn.commit()
    conn.close()

def get_vet_visits(cat_id):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = cursor()
    c.execute("SELECT * FROM vet_visits WHERE cat_id = ? ORDER BY visit_date DESC", (cat_id,))
    visits = c.fetchall()
    conn.close()
    return visits

def add_task(cat_id, task_name, task_type, frequency):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    # Calculate next due date based on frequency
    if frequency == "daily":
        next_due = datetime.now().date() + timedelta(days=1)
    elif frequency == "weekly":
        next_due = datetime.now().date() + timedelta(weeks=1)
    elif frequency == "monthly":
        next_due = datetime.now().date() + timedelta(days=30)
    
    c.execute("INSERT INTO tasks (cat_id, task_name, task_type, frequency, next_due) VALUES (?, ?, ?, ?, ?)",
              (cat_id, task_name, task_type, frequency, next_due))
    conn.commit()
    conn.close()

def get_tasks(user_id, cat_id=None):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    
    if cat_id:
        c.execute("SELECT * FROM tasks t JOIN cats c ON t.cat_id = c.id WHERE c.user_id = ? AND t.cat_id = ? ORDER BY t.next_due ASC", (user_id, cat_id))
    else:
        c.execute("SELECT * FROM tasks t JOIN cats c ON t.cat_id = c.id WHERE c.user_id = ? ORDER BY t.next_due ASC", (user_id,))
    
    tasks = c.fetchall()
    conn.close()
    return tasks

def complete_task(task_id):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    
    # Get task details
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    
    if task:
        # Mark as completed
        c.execute("UPDATE tasks SET completed = 1, last_completed = ? WHERE id = ?", 
                  (datetime.now().date(), task_id))
        
        # Calculate next due date
        if task[4] == "daily":
            next_due = datetime.now().date() + timedelta(days=1)
        elif task[4] == "weekly":
            next_due = datetime.now().date() + timedelta(weeks=1)
        elif task[4] == "monthly":
            next_due = datetime.now().date() + timedelta(days=30)
        
        # Reset task for next cycle
        c.execute("UPDATE tasks SET completed = 0, next_due = ? WHERE id = ?", (next_due, task_id))
    
    conn.commit()
    conn.close()

def get_dashboard_stats(user_id):
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    
    # Get total cats
    c.execute("SELECT COUNT(*) FROM cats WHERE user_id = ?", (user_id,))
    total_cats = c.fetchone()[0]
    
    # Get total health entries for this month
    current_month = datetime.now().month
    current_year = datetime.now().year
    c.execute("""
        SELECT COUNT(*) FROM health_entries he
        JOIN cats c ON he.cat_id = c.id
        WHERE c.user_id = ? AND strftime('%m', he.entry_date) = ? AND strftime('%Y', he.entry_date) = ?
    """, (user_id, f"{current_month:02d}", str(current_year)))
    total_entries = c.fetchone()[0]
    
    # Get total vet visits
    c.execute("SELECT COUNT(*) FROM vet_visits v JOIN cats c ON v.cat_id = c.id WHERE c.user_id = ?", (user_id,))
    total_vet_visits = c.fetchone()[0]
    
    # Get today's completed tasks
    today = datetime.now().date()
    c.execute("""
        SELECT COUNT(*) FROM tasks t
        JOIN cats c ON t.cat_id = c.id
        WHERE c.user_id = ? AND t.completed = 1 AND t.last_completed = ?
    """, (user_id, today))
    tasks_completed = c.fetchone()[0]
    
    conn.close()
    
    return {
        'total_cats': total_cats,
        'total_entries': total_entries,
        'total_vet_visits': total_vet_visits,
        'tasks_completed': tasks_completed
    }

def get_today_tasks(user_id):
    today = datetime.now().date()
    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute("""
        SELECT t.id, t.task_name, t.task_type, c.name as cat_name, t.completed
        FROM tasks t
        JOIN cats c ON t.cat_id = c.id
        WHERE c.user_id = ? AND (t.next_due = ? OR (t.last_completed IS NULL AND t.created_date <= ?))
        ORDER BY t.next_due ASC
    """, (user_id, today, today))
    
    tasks = c.fetchall()
    conn.close()
    
    return tasks

# Utility functions
def get_cat_health_summary(cat_id):
    """Get health summary for a specific cat"""
    entries = get_health_entries(cat_id, days=30)
    
    if not entries:
        return {
            'status': 'No Data',
            'entries_count': 0,
            'avg_water': 0.0,
            'avg_food': 0.0,
            'last_entry': None
        }
    
    # Calculate averages
    water_values = [float(entry[3]) for entry in entries if entry[3] and entry[3] != '']
    food_values = [float(entry[4]) for entry in entries if entry[4] and entry[4] != '']
    
    avg_water = sum(water_values) / len(water_values) if water_values else 0.0
    avg_food = sum(food_values) / len(food_values) if food_values else 0.0
    
    return {
        'status': 'Active',
        'entries_count': len(entries),
        'avg_water': round(avg_water, 1),
        'avg_food': round(avg_food, 1),
        'last_entry': entries[0][1] if entries else None
    }

def get_cat_recommendations(cat_id):
    """Get AI-powered recommendations for a cat based on health data"""
    entries = get_health_entries(cat_id, days=30)
    cat_details = get_cat_details(cat_id)
    
    recommendations = []
    
    if not entries:
        recommendations.append("Start logging health data to track patterns")
    
    # Add more intelligent recommendations based on data
    if entries:
        # Check for weight trends
        weights = [float(entry[2]) for entry in entries if entry[2] and entry[2] != '']
        if len(weights) > 1:
            weight_change = weights[-1] - weights[0]
            if abs(weight_change) > 0.5:
                recommendations.append(f"Monitor weight - {weight_change:+.1f}kg change in 30 days")
    
    if not recommendations:
        recommendations.append("Keep up with regular health monitoring")
    
    return recommendations

# Page functions
def login_page():
    st.title("🐱 Cat Health Tracker - Login")
    
    # Create login form
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username and password:
                conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = c.fetchone()
                conn.close()
                
                if user and verify_password(password, user[2]):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_id = user[0]
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Please fill in all fields")
    
    # Create account link
    if st.button("Create Account"):
        st.session_state.show_register = True
        st.rerun()

def register_page():
    st.title("🐱 Cat Health Tracker - Create Account")
    
    with st.form("register_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account")
        
        if submitted:
            if username and password and confirm_password:
                if password == confirm_password:
                    conn = sqlite3.connect('cat_health_tracker.db', check_same_thread=False)
                    c = conn.cursor()
                    
                    try:
                        hashed_password = hash_password(password)
                        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                  (username, hashed_password))
                        conn.commit()
                        st.success("Account created successfully! Please login.")
                        st.session_state.show_register = False
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists")
                    finally:
                        conn.close()
                else:
                    st.error("Passwords do not match")
            else:
                st.error("Please fill in all fields")
    
    # Back to login link
    if st.button("Back to Login"):
        st.session_state.show_register = False
        st.rerun()

def dashboard_page():
    if not st.session_state.get('logged_in'):
        st.warning("Please login first")
        return
    
    st.title("🐱 Cat Health Tracker")
    
    # User greeting
    st.sidebar.header(f"👤 {st.session_state.username}")
    
    # Navigation
    page = st.sidebar.selectbox("Navigation", ["Dashboard", "Cat Profiles", "Health Entries", "Tasks", "AI Assistant"])
    
    if page == "Dashboard":
        dashboard_view()
    elif page == "Cat Profiles":
        cat_profiles_page()
    elif page == "Health Entries":
        health_entries_page()
    elif page == "Tasks":
        tasks_page()
    elif page == "AI Assistant":
        ai_assistant_page()

def dashboard_view():
    user_id = st.session_state.user_id
    
    # Get dashboard stats
    stats = get_dashboard_stats(user_id)
    
    # Quick overview cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Entries", stats['total_entries'])
    with col2:
        st.metric("Today's Tasks Done", stats['tasks_completed'])
    with col3:
        st.metric("Vet Visits", stats['total_vet_visits'])
    with col4:
        st.metric("Active Cats", stats['total_cats'])
    
    # Get all cats
    cats = get_cats(user_id)
    
    if cats:
        st.subheader("🐱 Cat Health Summaries")
        
        # Create tabs for each cat
        cat_tabs = st.tabs([cat[1] for cat in cats])
        
        for i, cat in enumerate(cats):
            with cat_tabs[i]:
                cat_id = cat[0]
                cat_name = cat[1]
                
                # Get health summary
                summary = get_cat_health_summary(cat_id)
                
                # Display cat info
                st.subheader(f"🐱 {cat_name}")
                
                # Health overview
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Health Overview**")
                    st.write(f"Status: {summary['status']}")
                    st.write(f"Entries: {summary['entries_count']} this week")
                    st.write(f"Water: {summary['avg_water']} avg/day")
                    st.write(f"Food: {summary['avg_food']} avg/day")
                
                with col2:
                    st.write("**Profile Information**")
                    st.write(f"Age: {cat[2]}")
                    st.write(f"Breed: {cat[3]}")
                    st.write(f"Weight: {cat[4]}")
                    st.write(f"Vet Visits: {len(get_vet_visits(cat_id))}")
                
                # AI recommendations
                recommendations = get_cat_recommendations(cat_id)
                if recommendations:
                    st.markdown(f"""
                    <div style="background: #d1ecf1; padding: 15px; border-radius: 10px;">
                        <h4 style="margin: 0 0 10px 0;">💡 Recommendations</h4>
                        <ul style="margin: 0; padding-left: 20px;">
                            {"".join([f"<li>{rec}</li>" for rec in recommendations])}
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Quick actions
                if st.button(f"📝 Add Health Entry for {cat_name}"):
                    st.session_state.selected_cat_id = cat_id
                    st.session_state.add_health_entry = True
                    st.rerun()
                
                if st.button(f"🏥 Add Vet Visit for {cat_name}"):
                    st.session_state.selected_cat_id = cat_id
                    st.session_state.add_vet_visit = True
                    st.rerun()
    
    else:
        st.info("No cats found. Please add your first cat in the Cat Profiles page.")

def cat_profiles_page():
    user_id = st.session_state.user_id
    
    st.subheader("🐱 Cat Profiles")
    
    # Get all cats
    cats = get_cats(user_id)
    
    if cats:
        # Display cat profiles in cards
        for cat in cats:
            cat_id, name, age, breed, weight, notes = cat
            
            with st.expander(f"🐱 {name}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Age:** {age}")
                    st.write(f"**Breed:** {breed}")
                    st.write(f"**Weight:** {weight}")
                    st.write(f"**Vet Visits:** {len(get_vet_visits(cat_id))}")
                    
                    if notes:
                        st.write(f"**Notes:** {notes}")
                    else:
                        st.write("**Notes:** No notes yet")
                
                with col2:
                    if st.button("🏥 Add Visit", key=f"visit_{cat_id}"):
                        st.session_state.selected_cat_id = cat_id
                        st.session_state.add_vet_visit = True
                        st.rerun()
                    
                    if st.button("✏️ Edit Profile", key=f"edit_{cat_id}"):
                        st.session_state.selected_cat_id = cat_id
                        st.session_state.edit_cat = True
                        st.rerun()
    
    else:
        st.info("No cats found. Please add your first cat.")
    
    # Add new cat button
    if st.button("➕ Add New Cat"):
        st.session_state.add_cat = True
        st.rerun()
    
    # Handle add/edit forms
    if st.session_state.get('add_cat'):
        add_cat_form()
    
    elif st.session_state.get('edit_cat'):
        cat_id = st.session_state.get('selected_cat_id')
        cat = get_cat_details(cat_id)
        if cat:
            edit_cat_form(cat)
    
    elif st.session_state.get('add_vet_visit'):
        cat_id = st.session_state.get('selected_cat_id')
        cat = get_cat_details(cat_id)
        if cat:
            add_vet_visit_form(cat)

def add_cat_form():
    st.subheader("➕ Add New Cat")
    
    with st.form("add_cat_form"):
        name = st.text_input("Cat Name")
        age = st.text_input("Age")
        breed = st.text_input("Breed")
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Cat")
        
        if submitted:
            if name:
                add_cat(name, age, breed, weight, notes, st.session_state.user_id)
                st.success(f"Cat '{name}' added successfully!")
                st.session_state.add_cat = False
                st.rerun()
            else:
                st.error("Please enter a cat name")
    
    if st.button("Cancel"):
        st.session_state.add_cat = False
        st.rerun()

def edit_cat_form(cat):
    st.subheader("✏️ Edit Cat Profile")
    
    with st.form("edit_cat_form"):
        cat_id, name, age, breed, weight, notes = cat
        
        name = st.text_input("Cat Name", value=name)
        age = st.text_input("Age", value=age)
        breed = st.text_input("Breed", value=breed)
        weight = st.number_input("Weight (kg)", value=float(weight) if weight else 0.0, min_value=0.0, step=0.1)
        notes = st.text_area("Notes", value=notes)
        submitted = st.form_submit_button("Update Cat")
        
        if submitted:
            update_cat(cat_id, name, age, breed, weight, notes)
            st.success(f"Cat '{name}' updated successfully!")
            st.session_state.edit_cat = False
            st.rerun()
    
    if st.button("Cancel"):
        st.session_state.edit_cat = False
        st.rerun()

def add_vet_visit_form(cat):
    st.subheader(f"🏥 Add Vet Visit for {cat[1]}")
    
    with st.form("add_vet_visit_form"):
        visit_date = st.date_input("Visit Date", value=datetime.now().date())
        vet_name = st.text_input("Veterinarian Name")
        reason = st.text_input("Reason for Visit")
        diagnosis = st.text_area("Diagnosis")
        treatment = st.text_area("Treatment")
        medications = st.text_area("Medications")
        notes = st.text_area("Additional Notes")
        submitted = st.form_submit_button("Add Visit")
        
        if submitted:
            add_vet_visit(cat[0], visit_date, vet_name, reason, diagnosis, treatment, medications, notes)
            st.success(f"Vet visit added for {cat[1]}!")
            st.session_state.add_vet_visit = False
            st.rerun()
    
    if st.button("Cancel"):
        st.session_state.add_vet_visit = False
        st.rerun()

def health_entries_page():
    user_id = st.session_state.user_id
    
    st.subheader("📝 Health Entries")
    
    # Get cats
    cats = get_cats(user_id)
    
    if cats:
        # Cat selector
        selected_cat_name = st.selectbox("Select Cat", [cat[1] for cat in cats])
        selected_cat = next(cat for cat in cats if cat[1] == selected_cat_name)
        cat_id = selected_cat[0]
        
        # Add new entry button
        if st.button("➕ Add Health Entry"):
            st.session_state.selected_cat_id = cat_id
            st.session_state.add_health_entry = True
            st.rerun()
        
        # Display existing entries
        entries = get_health_entries(cat_id)
        
        if entries:
            st.write(f"**Recent Health Entries for {selected_cat_name}**")
            
            for entry in entries[:10]:  # Show last 10 entries
                entry_id, cat_id_entry, entry_date, weight, water, food, activity, symptoms, medications, notes, created_at = entry
                
                with st.expander(f"📅 {entry_date}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Weight:** {weight} kg")
                        st.write(f"**Water:** {water} ml")
                        st.write(f"**Food:** {food} g")
                        st.write(f"**Activity:** {activity}")
                    
                    with col2:
                        if symptoms:
                            st.write(f"**Symptoms:** {symptoms}")
                        if medications:
                            st.write(f"**Medications:** {medications}")
                        if notes:
                            st.write(f"**Notes:** {notes}")
        else:
            st.info(f"No health entries found for {selected_cat_name}")
    
    else:
        st.info("No cats found. Please add cats first.")
    
    # Handle add entry form
    if st.session_state.get('add_health_entry'):
        cat_id = st.session_state.get('selected_cat_id')
        cat = get_cat_details(cat_id)
        if cat:
            add_health_entry_form(cat)

def add_health_entry_form(cat):
    st.subheader(f"📝 Add Health Entry for {cat[1]}")
    
    with st.form("add_health_entry_form"):
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
        water = st.number_input("Water Consumption (ml)", min_value=0.0, step=10.0)
        food = st.number_input("Food Consumption (g)", min_value=0.0, step=10.0)
        activity = st.selectbox("Activity Level", ["Low", "Normal", "High"])
        symptoms = st.text_area("Symptoms (if any)")
        medications = st.text_area("Medications (if any)")
        notes = st.text_area("Additional Notes")
        submitted = st.form_submit_button("Add Entry")
        
        if submitted:
            add_health_entry(cat[0], weight, water, food, activity, symptoms, medications, notes)
            st.success(f"Health entry added for {cat[1]}!")
            st.session_state.add_health_entry = False
            st.rerun()
    
    if st.button("Cancel"):
        st.session_state.add_health_entry = False
        st.rerun()

def tasks_page():
    user_id = st.session_state.user_id
    
    st.subheader("📋 Tasks")
    
    # Get today's tasks
    today_tasks = get_today_tasks(user_id)
    
    if today_tasks:
        st.write("⚠️ Reminder: No health entries for Haku, Kuro, Sonic today!")
        
        # Show incomplete tasks
        incomplete_tasks = [task for task in today_tasks if not task[4]]
        if incomplete_tasks:
            st.write("📝 Incomplete daily tasks: " + ", ".join([task[1] for task in incomplete_tasks]))
        
        # Display all tasks
        st.write("**Today's Tasks**")
        
        for task in today_tasks:
            task_id, task_name, task_type, cat_name, completed = task
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                status = "✅" if completed else "⏳"
                st.write(f"{status} {task_name} ({cat_name}) - {task_type}")
            
            with col2:
                if not completed:
                    if st.button("Complete", key=f"complete_{task_id}"):
                        complete_task(task_id)
                        st.rerun()
            
            with col3:
                if st.button("Details", key=f"details_{task_id}"):
                    st.write(f"Task: {task_name}")
                    st.write(f"Type: {task_type}")
                    st.write(f"Cat: {cat_name}")
                    st.write(f"Status: {'Completed' if completed else 'Pending'}")
    
    else:
        st.info("No tasks found for today.")
    
    # Get all cats for adding tasks
    cats = get_cats(user_id)
    
    if cats:
        st.write("🐱 Cat Profiles")
        
        for cat in cats:
            cat_id, name, age, breed, weight, notes = cat
            
            with st.expander(f"🐱 {name}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Age:** {age}")
                    st.write(f"**Breed:** {breed}")
                    st.write(f"**Weight:** {weight}")
                    st.write(f"**Vet Visits:** {len(get_vet_visits(cat_id))}")
                    
                    if notes:
                        st.divider()
                        st.write("**Notes:**")
                        st.write(notes)
                    else:
                        st.write("**Notes:** No notes yet")
                
                with col2:
                    if st.button("✏️ Edit Profile", key=f"edit_cat_{cat_id}"):
                        st.session_state.selected_cat_id = cat_id
                        st.session_state.edit_cat = True
                        st.rerun()
        
        # Add new task button
        if st.button("➕ Add Task"):
            st.session_state.add_task = True
            st.rerun()
    
    else:
        st.info("No cats found. Please add cats first.")
    
    # Handle add task form
    if st.session_state.get('add_task'):
        add_task_form()

def add_task_form():
    st.subheader("➕ Add New Task")
    
    with st.form("add_task_form"):
        # Get cats for dropdown
        cats = get_cats(st.session_state.user_id)
        cat_names = [cat[1] for cat in cats]
        
        selected_cat = st.selectbox("Select Cat", cat_names)
        cat_id = next(cat[0] for cat in cats if cat[1] == selected_cat)
        
        task_name = st.text_input("Task Name")
        task_type = st.selectbox("Task Type", ["Health", "Care", "Grooming", "Medication", "Other"])
        frequency = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
        submitted = st.form_submit_button("Add Task")
        
        if submitted:
            if task_name:
                add_task(cat_id, task_name, task_type, frequency.lower())
                st.success(f"Task '{task_name}' added successfully!")
                st.session_state.add_task = False
                st.rerun()
            else:
                st.error("Please enter a task name")
    
    if st.button("Cancel"):
        st.session_state.add_task = False
        st.rerun()

def ai_assistant_page():
    st.subheader("🤖 AI Cat Health Assistant")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Get cats for context
    cats = get_cats(st.session_state.user_id)
    cat_names = [cat[1] for cat in cats] if cats else []
    
    # Chat input
    if prompt := st.chat_input("Ask about your cat's health..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Get AI response
        cat_context = None
        if cat_names:
            # Try to identify cat name in prompt
            for cat_name in cat_names:
                if cat_name.lower() in prompt.lower():
                    cat_context = cat_name
                    break
        
        ai_response = get_ai_response(prompt, cat_context, "Cat health tracker user")
        
        # Add AI response to chat history
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        
        # Rerun to update the chat
        st.rerun()

# Main application
def main():
    # Check if user is logged in
    if not st.session_state.get('logged_in'):
        if st.session_state.get('show_register'):
            register_page()
        else:
            login_page()
    else:
        dashboard_page()

if __name__ == "__main__":
    main()
