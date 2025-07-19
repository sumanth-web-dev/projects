"""
Main routes for the Job Application Agent web interface.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from services.profile_service import profile_service
from services.auth_service import auth_service
from models.database import db


# Create blueprint for main routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render the promotional home page."""
    # Always show the index.html page when accessing the root URL
    # If user is logged in, they'll be redirected via JavaScript in the template
    from datetime import datetime
    return render_template('index.html', now=datetime.now())
    

from sqlalchemy import text
import traceback

@main_bp.route('/test-connection')
def test_connection():
    try:
        print("🚀 Trying to connect to the database...")
        
        with db.engine.connect() as connection:
            print("✅ Connection established. Executing query...")
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print("✅ Query executed. Version fetched.")
        return f"✅ Connected to PostgreSQL: {version}"
    
    except Exception as e:
        print("❌ Connection or query failed.")
        traceback.print_exc()  # Print full error trace in console
        return f"❌ Connection failed: {str(e)}"
