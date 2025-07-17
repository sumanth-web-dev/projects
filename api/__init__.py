"""
API Blueprint package for the Job Application Agent.
"""
from flask import Blueprint

# Create the main API blueprint
api_bp = Blueprint('api', __name__)

# Import routes to register them with the blueprint
from api import routes_new as routes
from api import profile_routes
from api import job_routes
from api import application_routes
from api import settings_routes