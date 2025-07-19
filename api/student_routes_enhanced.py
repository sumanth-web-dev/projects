from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for, send_file, g
from api import user_bp as student_bp
from config.template_config import get_template_path
from api.template_helper import render_role_template
from services.user_services import user_service
from models.application import Application
import datetime

@student_bp.route('/offers', methods=['GET'])
def offers():
    """View and manage job offers."""
    user_id = session.get('user_id')
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
        
    # Set user type and active page for template
    g.user_type = 'student'
    g.active_page = 'offers'
    
    try:
        # Get all applications with offer status
        applications = Application.query.filter(
            Application.user_id == user_id,
            Application.status == 'offer_received'
        ).all()
        
        # Format offers data
        offers = []
        pending_offers = []
        accepted_offers = []
        declined_offers = []
        
        for app in applications:
            offer_data = app.meta_data_dict.get('offer_details', {})
            offer = {
                'id': app.id,
                'company': app.job.company if app.job else 'Unknown Company',
                'company_logo': app.job.company_logo if app.job and hasattr(app.job, 'company_logo') else None,
                'position': app.job.title if app.job else 'Unknown Position',
                'salary': offer_data.get('salary', 'Not specified'),
                'offer_date': app.updated_at,
                'deadline': offer_data.get('deadline'),
                'status': app.meta_data_dict.get('offer_response', 'pending'),
                'days_remaining': None
            }
            
            # Calculate days remaining if deadline exists
            if offer['deadline']:
                deadline_date = datetime.datetime.fromisoformat(offer['deadline'])
                days_remaining = (deadline_date - datetime.datetime.utcnow()).days
                offer['days_remaining'] = max(0, days_remaining)
            
            offers.append(offer)
            
            # Categorize by status
            if offer['status'] == 'pending':
                pending_offers.append(offer)
            elif offer['status'] == 'accepted':
                accepted_offers.append(offer)
            elif offer['status'] == 'declined':
                declined_offers.append(offer)
        
        # Get user notifications
        notifications = user_service.get_user_notifications(user_id)
        
        return render_role_template('offers',
                             user=user,
                             offers=offers,
                             pending_offers=pending_offers,
                             accepted_offers=accepted_offers,
                             declined_offers=declined_offers,
                             notifications=notifications)
    
    except Exception as e:
        flash(f'Error loading offers: {str(e)}', 'error')
        return render_role_template('offers',
                             user=user,
                             offers=[],
                             pending_offers=[],
                             accepted_offers=[],
                             declined_offers=[],
                             notifications=[])
                             
@student_bp.route('/test', methods=['GET'])
def test_template():
    """Test the student base template."""
    user_id = session.get('user_id')
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
        
    # Set user type and active page for template
    g.user_type = 'student'
    g.active_page = 'test'
    
    # Get user notifications
    notifications = user_service.get_user_notifications(user_id)
    
    return render_role_template('test',
                         user=user,
                         notifications=notifications)