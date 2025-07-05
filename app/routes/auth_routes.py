from flask import Blueprint, render_template, request, redirect, url_for, flash 
from flask_login import login_user, logout_user, login_required
from app.models import Usuario, Colaborador  # ✅ Adiciona Colaborador
from app import db

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        cpf = request.form.get("cpf")  # 🔹 Busca pelo CPF
        senha = request.form.get("senha")

        # Primeiro tenta autenticar como administrador
        user = Usuario.query.filter_by(cpf=cpf).first()
        if user and user.check_password(senha):
            login_user(user)
            return redirect(url_for("dashboard_bp.dashboard"))

        # Senão, tenta autenticar como colaborador
        colaborador = Colaborador.query.filter_by(cpf=cpf).first()
        if colaborador and colaborador.check_password(senha):
            login_user(colaborador)
            return redirect(url_for("despesa_bp.menu_despesas"))  # 👈 Redireciona para o menu de despesas

        flash("CPF ou senha inválidos.", "danger")
        return redirect(url_for("auth_bp.login"))

    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth_bp.login"))
