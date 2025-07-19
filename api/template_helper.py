"""
Helper functions for template rendering.
"""
from flask import render_template, g
from config.template_config import get_template_path

def render_role_template(template_name, role=None, **context):
    """
    Render a template for a specific role.
    
    Args:
        template_name (str): The template name without the role prefix
        role (str, optional): The user role. If None, uses g.user_type
        **context: Template context variables
        
    Returns:
        str: The rendered template
    """
    # Get the role from g if not provided
    if role is None:
        role = getattr(g, 'user_type', 'student')  # Default to student if not set
    
    # Get the template path
    template_path = get_template_path(role, template_name)
    
    # Add role to context if not already present
    if 'user_type' not in context:
        context['user_type'] = role
    
    # Add active_page to context if not already present
    if 'active_page' not in context and template_name != 'base':
        context['active_page'] = template_name
    
    # Render the template
    return render_template(template_path, **context)