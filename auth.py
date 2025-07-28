import os
from functools import wraps
from flask import session, request, redirect, url_for, flash, render_template

def check_auth(username, password):
    """Check if provided credentials match the configured admin credentials"""
    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    return username == admin_username and password == admin_password

def authenticate():
    """Check if user is authenticated"""
    return session.get('authenticated', False)

def requires_auth(f):
    """Decorator to require authentication for a route"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not authenticate():
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated

def login_user():
    """Mark user as authenticated in session"""
    session['authenticated'] = True
    session.permanent = True

def logout_user():
    """Clear authentication from session"""
    session.pop('authenticated', None)
    session.clear()