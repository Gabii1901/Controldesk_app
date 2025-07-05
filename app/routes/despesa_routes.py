from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app import db
from app.models import Despesa, Imagem, Colaborador

despesa_bp = Blueprint('despesa_bp', __name__)

# Configuração de upload
UPLOAD_FOLDER = "E:/Projetos/ControlDesk/uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 🔹 Menu principal de despesas
@despesa_bp.route('/menu_despesas', methods=['GET'])
@login_required
def menu_despesas():
    if not isinstance(current_user, Colaborador):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    return render_template("menu_despesas.html", colaborador=current_user)

# 🔹 Página de cadastro de despesas
@despesa_bp.route('/cadastro_despesa', methods=['GET'])
@login_required
def cadastro_despesa_page():
    if not isinstance(current_user, Colaborador):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    # Passa o colaborador logado para o template
    return render_template("cadastro_despesa.html", colaborador=current_user)

# 🔹 Processamento do cadastro
@despesa_bp.route('/cadastro_despesa', methods=['POST'])
@login_required
def cadastro_despesa():
    if not isinstance(current_user, Colaborador):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    data = request.form
    arquivo = request.files.get('imagem')

    if not data.get('cidade') or not data.get('local') or not data.get('valor'):
        flash("Campos obrigatórios não foram preenchidos.", "danger")
        return redirect(url_for('despesa_bp.cadastro_despesa_page'))

    despesa = Despesa(
        nome_colaborador=current_user.nome,  # Garante que o nome é do colaborador logado
        cidade=data.get('cidade'),
        local=data.get('local'),
        cnpj_cpf_local=data.get('cnpj_cpf_local'),
        numero_documento=data.get('numero_documento'),
        descricao=data.get('descricao'),
        valor=float(data.get('valor')),
        observacao=data.get('observacao', ''),
        complemento=data.get('complemento', '')
    )

    db.session.add(despesa)
    db.session.commit()

    if arquivo and allowed_file(arquivo.filename):
        filename = secure_filename(arquivo.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        arquivo.save(filepath)

        # Ajuste principal: campo correto é 'caminho'
        imagem = Imagem(despesa_id=despesa.id, caminho=filepath)
        db.session.add(imagem)
        db.session.commit()

    flash("Despesa cadastrada com sucesso!", "success")
    return redirect(url_for('despesa_bp.menu_despesas'))

@despesa_bp.route('/historico_despesas', methods=['GET'])
@login_required
def historico_despesas():
    if not isinstance(current_user, Colaborador):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    despesas = Despesa.query.filter_by(nome_colaborador=current_user.nome).order_by(Despesa.id.desc()).all()
    return render_template("historico_despesas.html", despesas=despesas, colaborador=current_user)
