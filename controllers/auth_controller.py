"""
Controlador para autenticación
"""
from typing import Dict, Any, Optional
from flask import request, session, flash, redirect, url_for, render_template

from utils.decorators import handle_form_errors
from utils.validators import ValidationError
from utils.logging_config import get_logger
from config.settings import get_settings


class AuthController:
    """Controlador para manejo de autenticación"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
    
    def check_auth(self, username: str, password: str) -> bool:
        """
        Verificar credenciales de usuario
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            
        Returns:
            bool: True si las credenciales son correctas
        """
        try:
            admin_username = self.settings.security.admin_username
            admin_password = self.settings.security.admin_password
            
            is_valid = username == admin_username and password == admin_password
            
            if is_valid:
                self.logger.info(f"Login exitoso para usuario: {username}")
            else:
                self.logger.warning(f"Intento de login fallido para usuario: {username}")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Error verificando credenciales: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """
        Verificar si el usuario está autenticado
        
        Returns:
            bool: True si está autenticado
        """
        return session.get('authenticated', False)
    
    def login_user(self, username: str) -> None:
        """
        Marcar usuario como autenticado
        
        Args:
            username: Nombre del usuario
        """
        session['authenticated'] = True
        session['username'] = username
        session.permanent = self.settings.security.session_permanent
        
        self.logger.info(f"Usuario autenticado en sesión: {username}")
    
    def logout_user(self) -> None:
        """Cerrar sesión del usuario"""
        username = session.get('username', 'unknown')
        
        session.pop('authenticated', None)
        session.pop('username', None)
        session.clear()
        
        self.logger.info(f"Sesión cerrada para usuario: {username}")
    
    @handle_form_errors('main.login')
    def handle_login(self):
        """
        Manejar proceso de login
        
        Returns:
            Response de Flask
        """
        if request.method == 'GET':
            return render_template('login.html')
        
        # POST request
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Usuario y contraseña son requeridos', 'error')
            return render_template('login.html')
        
        if self.check_auth(username, password):
            self.login_user(username)
            flash('Sesión iniciada correctamente', 'success')
            
            # Redirigir a la página solicitada originalmente
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return render_template('login.html')
    
    def handle_logout(self):
        """
        Manejar proceso de logout
        
        Returns:
            Response de Flask
        """
        self.logout_user()
        flash('Sesión cerrada exitosamente', 'success')
        return redirect(url_for('main.login'))


# Instancia global del controlador de autenticación
auth_controller = AuthController()