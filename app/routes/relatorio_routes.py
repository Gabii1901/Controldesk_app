from flask import Blueprint, render_template, request
from flask_jwt_extended import jwt_required

relatorio_bp = Blueprint('relatorio_bp', __name__)

@relatorio_bp.route('/relatorios')
def listar_relatorios():
    return render_template("listar_relatorios.html")