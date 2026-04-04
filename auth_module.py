"""
Authentication and Encryption Module for Cat Health Tracker
"""
import streamlit as st
import hashlib
import hmac
import json
import base64
from cryptography.fernet import Fernet
from datetime import datetime, timedelta

# Generate or load encryption key
def get_encryption_key():
    """Get or generate encryption key from Streamlit secrets"""
    if 'ENCRYPTION_KEY' in st.secrets:
        try:
            key = st.secrets['ENCRYPTION_KEY']
            # Ensure key is bytes
            if isinstance(key, str):
                key = key.encode()
            # Validate key format
            test_cipher = Fernet(key)
            return key
        except Exception as e:
            st.error(f"Invalid ENCRYPTION_KEY in secrets: {e}")
            st.info("Generating temporary key for this session...")
    
    # For local development or if key is invalid, generate a temporary key
    key = Fernet.generate_key()
    st.warning("⚠️ Using temporary encryption key. Add a valid ENCRYPTION_KEY to Streamlit secrets for production!")
    st.info(f"💡 Run this to generate a valid key: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`")
    return key

# Initialize encryption
try:
    ENCRYPTION_KEY = get_encryption_key()
    cipher_suite = Fernet(ENCRYPTION_KEY)
    ENCRYPTION_ENABLED = True
except Exception as e:
    st.error(f"Encryption initialization failed: {e}")
    ENCRYPTION_ENABLED = False
    cipher_suite = None

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    if not ENCRYPTION_ENABLED or cipher_suite is None:
        return data
    try:
        encrypted = cipher_suite.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        st.error(f"Encryption error: {e}")
        return data

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    if not ENCRYPTION_ENABLED or cipher_suite is None:
        return encrypted_data
    try:
        decoded = base64.b64decode(encrypted_data.encode())
        decrypted = cipher_suite.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        # Data might not be encrypted
        return encrypted_data

def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = "cat_health_tracker_salt_2024"  # In production, use secrets
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

# Default user credentials (change these!)
DEFAULT_USERS = {
    'admin': hash_password('admin123'),  # Change this password!
}

def load_users():
    """Load user credentials from secrets or use defaults"""
    if 'USERS' in st.secrets:
        # Users stored in secrets as JSON
        try:
            users = json.loads(st.secrets['USERS'])
            return users
        except:
            return DEFAULT_USERS
    return DEFAULT_USERS

def check_authentication():
    """Check if user is authenticated"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.failed_attempts = 0
        st.session_state.locked_until = None
    
    return st.session_state.authenticated

def check_lockout():
    """Check if account is locked due to failed attempts"""
    if st.session_state.locked_until:
        if datetime.now() < st.session_state.locked_until:
            remaining = (st.session_state.locked_until - datetime.now()).seconds
            return True, remaining
        else:
            # Lockout expired
            st.session_state.locked_until = None
            st.session_state.failed_attempts = 0
    return False, 0

def login_page():
    """Display login page"""
    st.set_page_config(
        page_title="Cat Health Tracker - Login",
        page_icon="🐱",
        layout="centered"
    )
    
    # Custom CSS for login page
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .login-header {
            text-align: center;
            color: white;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .login-subtitle {
            text-align: center;
            color: #f0f0f0;
            margin-bottom: 30px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Check for lockout
    is_locked, remaining = check_lockout()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-header">🐱</div>', unsafe_allow_html=True)
        st.markdown('<h1 style="text-align: center; color: white;">Cat Health Tracker</h1>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Secure Login</p>', unsafe_allow_html=True)
        
        if is_locked:
            st.error(f"🔒 Too many failed attempts. Try again in {remaining} seconds.")
            return
        
        # Login form
        with st.form("login_form"):
            username = st.text_input("👤 Username", key="username_input")
            password = st.text_input("🔑 Password", type="password", key="password_input")
            
            col_a, col_b = st.columns(2)
            with col_a:
                submit = st.form_submit_button("🔓 Login", use_container_width=True)
            with col_b:
                show_signup = st.form_submit_button("📝 Sign Up", use_container_width=True)
            
            if submit:
                users = load_users()
                
                if username in users:
                    if verify_password(password, users[username]):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.failed_attempts = 0
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.session_state.failed_attempts += 1
                        if st.session_state.failed_attempts >= 5:
                            st.session_state.locked_until = datetime.now() + timedelta(minutes=5)
                            st.error("🔒 Account locked for 5 minutes due to multiple failed attempts.")
                        else:
                            remaining_attempts = 5 - st.session_state.failed_attempts
                            st.error(f"❌ Invalid password. {remaining_attempts} attempts remaining.")
                else:
                    st.session_state.failed_attempts += 1
                    st.error("❌ Username not found.")
            
            if show_signup:
                st.session_state.show_signup = True
                st.rerun()
        
        # Show signup form if requested
        if 'show_signup' in st.session_state and st.session_state.show_signup:
            show_signup_form()
        
        # Information section
        st.markdown("---")
        st.info("""
        **🔐 Security Features:**
        - Password hashing with PBKDF2
        - Data encryption at rest
        - Account lockout after 5 failed attempts
        - Secure session management
        
        **Default credentials (change immediately!):**
        - Username: `admin`
        - Password: `admin123`
        """)

def show_signup_form():
    """Display signup form"""
    st.markdown("---")
    st.subheader("📝 Create New Account")
    
    with st.form("signup_form"):
        new_username = st.text_input("Choose Username")
        new_password = st.text_input("Choose Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        signup = st.form_submit_button("Create Account")
        cancel = st.form_submit_button("Cancel")
        
        if signup:
            if len(new_username) < 3:
                st.error("Username must be at least 3 characters")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            elif new_password != confirm_password:
                st.error("Passwords don't match")
            else:
                # Save new user (in production, this would go to database)
                st.success(f"""
                ✅ Account created for: {new_username}
                
                **To activate this account in production:**
                1. Go to Streamlit Cloud → Settings → Secrets
                2. Add/Update USERS secret:
                ```
                USERS = '{{"admin": "{hash_password('admin123')}", "{new_username}": "{hash_password(new_password)}"}}'
                ```
                3. Save and redeploy
                """)
                st.session_state.show_signup = False
        
        if cancel:
            st.session_state.show_signup = False
            st.rerun()

def logout():
    """Logout current user"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.rerun()

def require_auth(func):
    """Decorator to require authentication"""
    def wrapper(*args, **kwargs):
        if not check_authentication():
            login_page()
            return
        return func(*args, **kwargs)
    return wrapper
