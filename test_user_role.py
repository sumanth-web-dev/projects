#!/usr/bin/env python
"""
Script to test the User model with the role field.
"""
import uuid
import random
from app import create_app
from models.database import db
from models.user import User

app = create_app()

with app.app_context():
    try:
        # Create a test user with a specific role and unique email
        user_id = str(uuid.uuid4())
        random_num = random.randint(1000, 9999)
        test_email = f"test{random_num}@example.com"
        
        test_user = User(
            id=user_id,
            email=test_email,
            role="admin"
        )
        
        # Print the user details
        print(f"User created: {test_user}")
        print(f"User ID: {test_user.id}")
        print(f"User Email: {test_user.email}")
        print(f"User Role: {test_user.role}")
        
        # Try to save the user to the database
        db.session.add(test_user)
        db.session.commit()
        print("User saved to database successfully")
        
        # Retrieve the user from the database
        retrieved_user = User.query.filter_by(id=user_id).first()
        print(f"Retrieved user role: {retrieved_user.role}")
        
        # Clean up - delete the test user
        db.session.delete(retrieved_user)
        db.session.commit()
        print("Test user deleted")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error testing user role: {e}")