from flask import Blueprint, redirect, url_for
from flask_login import current_user

index_bp = Blueprint('index_bp', __name__)

@index_bp.route('/')
def index():
    """Redireciona para a tela de login se não estiver autenticado, ou para o dashboard se estiver."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_bp.dashboard'))
    return redirect(url_for('auth_bp.login_page'))
