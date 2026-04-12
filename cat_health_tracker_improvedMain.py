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
