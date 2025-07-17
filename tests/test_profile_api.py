"""
Tests for the profile management API endpoints.
"""
import os
import json
import pytest
import tempfile
from io import BytesIO
from flask import session
from app import create_app
from models.database import db
from models.user import User
from services.auth_service import auth_service
from services.profile_service import profile_service


@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Create a temporary file to use as a test database
    db_fd, db_path = tempfile.mkstemp()
    
    # Create the Flask application
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test_secret_key',
        'UPLOAD_FOLDER': tempfile.mkdtemp()
    })
    
    # Create all tables in the database
    with app.app_context():
        db.create_all()
        
        # Create a test user
        success, user_id, _ = auth_service.create_user(
            'test@example.com', 'password123', 
            {
                'first_name': 'Test',
                'last_name': 'User',
                'phone': '+1234567890',
                'address': '123 Test St'
            }
        )
        
        # Create a second test user
        success, user_id2, _ = auth_service.create_user(
            'test2@example.com', 'password123', 
            {
                'first_name': 'Test2',
                'last_name': 'User2',
                'phone': '+1987654321',
                'address': '456 Test Ave'
            }
        )
    
    yield app
    
    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)
    
    # Remove the temporary upload folder
    os.rmdir(app.config['UPLOAD_FOLDER'])


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def auth_headers(app, client):
    """Get authentication headers for API requests."""
    # Login to get a session
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    data = json.loads(response.data)
    csrf_token = data.get('csrf_token')
    
    # Return headers with CSRF token
    return {
        'X-CSRF-Token': csrf_token,
        'Content-Type': 'application/json'
    }


def test_get_profile(client, auth_headers):
    """Test getting user profile."""
    # Login first
    client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Get profile
    response = client.get('/api/profile', headers=auth_headers)
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'profile' in data
    assert data['profile']['email'] == 'test@example.com'
    assert data['profile']['personal_data']['first_name'] == 'Test'


def test_update_profile(client, auth_headers):
    """Test updating user profile."""
    # Login first
    client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Update profile
    response = client.put('/api/profile', json={
        'personal_info': {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '+1234567890',
            'address': '123 Test St',
            'city': 'Test City',
            'state': 'TS',
            'zip_code': '12345'
        },
        'preferences': {
            'job_titles': ['Software Engineer', 'Developer'],
            'locations': ['Remote', 'New York'],
            'remote_only': True,
            'salary_min': 80000,
            'salary_max': 150000
        }
    }, headers=auth_headers)
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'profile' in data
    assert data['profile']['personal_data']['first_name'] == 'Updated'
    assert data['profile']['personal_data']['city'] == 'Test City'
    assert data['profile']['preferences']['job_titles'] == ['Software Engineer', 'Developer']
    assert data['profile']['preferences']['remote_only'] == True


def test_delete_profile(client, auth_headers):
    """Test clearing profile information."""
    # Login first
    client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Delete profile
    response = client.delete('/api/profile', headers=auth_headers)
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    
    # Verify profile was cleared by getting it again
    response = client.get('/api/profile', headers=auth_headers)
    data = json.loads(response.data)
    assert data['profile']['personal_data'] == {}
    assert data['profile']['preferences'] == {}


def test_resume_management(client, auth_headers, app):
    """Test resume upload, listing, and deletion."""
    # Login first
    client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Create a test resume file
    resume_content = b'This is a test resume'
    resume_file = BytesIO(resume_content)
    
    # Upload resume
    response = client.post(
        '/api/profile/resumes',
        data={
            'file': (resume_file, 'test_resume.pdf'),
            'name': 'My Resume',
            'description': 'Test resume description'
        },
        headers={'X-CSRF-Token': auth_headers['X-CSRF-Token']},
        content_type='multipart/form-data'
    )
    
    # Check response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'resume_id' in data
    resume_id = data['resume_id']
    
    # Get resume list
    response = client.get('/api/profile/resumes', headers=auth_headers)
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'resumes' in data
    assert len(data['resumes']) == 1
    assert data['resumes'][0]['id'] == resume_id
    assert data['resumes'][0]['name'] == 'My Resume'
    
    # Update resume metadata
    response = client.put(
        f'/api/profile/resumes/{resume_id}',
        json={
            'name': 'Updated Resume',
            'description': 'Updated description'
        },
        headers=auth_headers
    )
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    
    # Get resume list again to verify update
    response = client.get('/api/profile/resumes', headers=auth_headers)
    data = json.loads(response.data)
    assert data['resumes'][0]['name'] == 'Updated Resume'
    
    # Delete resume
    response = client.delete(
        f'/api/profile/resumes/{resume_id}',
        headers=auth_headers
    )
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    
    # Get resume list again to verify deletion
    response = client.get('/api/profile/resumes', headers=auth_headers)
    data = json.loads(response.data)
    assert len(data['resumes']) == 0


def test_cover_letter_management(client, auth_headers, app):
    """Test cover letter upload, listing, and deletion."""
    # Login first
    client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Create a test cover letter file
    cover_letter_content = b'This is a test cover letter'
    cover_letter_file = BytesIO(cover_letter_content)
    
    # Upload cover letter
    response = client.post(
        '/api/profile/cover-letters',
        data={
            'file': (cover_letter_file, 'test_cover_letter.pdf'),
            'name': 'My Cover Letter',
            'description': 'Test cover letter description'
        },
        headers={'X-CSRF-Token': auth_headers['X-CSRF-Token']},
        content_type='multipart/form-data'
    )
    
    # Check response
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'cover_letter_id' in data
    cover_letter_id = data['cover_letter_id']
    
    # Get cover letter list
    response = client.get('/api/profile/cover-letters', headers=auth_headers)
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'cover_letters' in data
    assert len(data['cover_letters']) == 1
    assert data['cover_letters'][0]['id'] == cover_letter_id
    assert data['cover_letters'][0]['name'] == 'My Cover Letter'
    
    # Update cover letter metadata
    response = client.put(
        f'/api/profile/cover-letters/{cover_letter_id}',
        json={
            'name': 'Updated Cover Letter',
            'description': 'Updated description'
        },
        headers=auth_headers
    )
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    
    # Get cover letter list again to verify update
    response = client.get('/api/profile/cover-letters', headers=auth_headers)
    data = json.loads(response.data)
    assert data['cover_letters'][0]['name'] == 'Updated Cover Letter'
    
    # Delete cover letter
    response = client.delete(
        f'/api/profile/cover-letters/{cover_letter_id}',
        headers=auth_headers
    )
    
    # Check response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    
    # Get cover letter list again to verify deletion
    response = client.get('/api/profile/cover-letters', headers=auth_headers)
    data = json.loads(response.data)
    assert len(data['cover_letters']) == 0


def test_unauthorized_access(client):
    """Test that unauthorized access is prevented."""
    # Try to access profile without authentication
    response = client.get('/api/profile')
    assert response.status_code == 401
    
    # Try to access resumes without authentication
    response = client.get('/api/profile/resumes')
    assert response.status_code == 401
    
    # Try to access cover letters without authentication
    response = client.get('/api/profile/cover-letters')
    assert response.status_code == 401


def test_csrf_protection(client):
    """Test that CSRF protection is working."""
    # Login first
    client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    # Try to update profile without CSRF token
    response = client.put('/api/profile', json={
        'personal_info': {
            'first_name': 'Hacked',
        }
    }, headers={'Content-Type': 'application/json'})
    
    # Should be rejected due to missing CSRF token
    assert response.status_code == 403
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'CSRF' in data['message']