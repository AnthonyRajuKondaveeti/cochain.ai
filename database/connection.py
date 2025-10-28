# database/connection.py
from supabase import create_client
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_config import SUPABASE_KEY, SUPABASE_URL

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

