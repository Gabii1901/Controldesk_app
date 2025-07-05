from flask import Blueprint, request, render_template, jsonify, redirect, url_for
from flask_login import login_required
from app.models import Projeto, Empresa
from app import db

projeto_bp = Blueprint('projeto_bp', __name__)

# ✅ Listar Projetos
@projeto_bp.route('/', methods=['GET'])
@login_required
def listar_projetos():
    try:
        projetos = Projeto.query.all()
        return render_template("listar_projetos.html", projetos=projetos)
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar projetos: {str(e)}"}), 500

# ✅ Página de Cadastro de Projeto
@projeto_bp.route('/cadastro', methods=['GET'])
@login_required
def cadastro_projeto_page():
    try:
        empresas = Empresa.query.all()
        return render_template("cadastro_projeto.html", empresas=empresas)
    except Exception as e:
        return jsonify({"error": f"Erro ao carregar empresas: {str(e)}"}), 500

# ✅ Cadastrar um Projeto (POST)
@projeto_bp.route('/cadastro', methods=['POST'])
@login_required
def cadastrar_projeto():
    try:
        data = request.form

        if not data.get('nome') or not data.get('local') or not data.get('empresa_id'):
            return jsonify({"error": "Todos os campos são obrigatórios!"}), 400

        empresa_id = int(data['empresa_id'])

        novo_projeto = Projeto(
            nome=data['nome'],
            local=data['local'],
            status=data.get('status', 'EM ANDAMENTO'),
            empresa_id=empresa_id
        )
        db.session.add(novo_projeto)
        db.session.commit()

        return redirect(url_for('dashboard_bp.dashboard'))  # ✅ Redireciona para o Dashboard

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao cadastrar projeto: {str(e)}"}), 500

# ✅ Editar Projeto
@projeto_bp.route('/editar/<int:id>', methods=['GET'])
@login_required
def editar_projeto(id):
    try:
        projeto = Projeto.query.get_or_404(id)
        empresas = Empresa.query.all()
        return render_template("editar_projeto.html", projeto=projeto, empresas=empresas)
    except Exception as e:
        return jsonify({"error": f"Erro ao carregar projeto para edição: {str(e)}"}), 500

# ✅ Atualizar Projeto
@projeto_bp.route('/editar/<int:id>', methods=['POST'])
@login_required
def atualizar_projeto(id):
    try:
        projeto = Projeto.query.get_or_404(id)
        data = request.form

        projeto.nome = data.get('nome', projeto.nome)
        projeto.local = data.get('local', projeto.local)
        projeto.status = data.get('status', projeto.status)

        if data.get('empresa_id'):
            projeto.empresa_id = int(data.get('empresa_id'))

        db.session.commit()
        return redirect(url_for('dashboard_bp.dashboard'))  # ✅ Redireciona para o Dashboard

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao atualizar projeto: {str(e)}"}), 500

# ✅ Excluir Projeto
@projeto_bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_projeto(id):
    try:
        projeto = Projeto.query.get_or_404(id)
        db.session.delete(projeto)
        db.session.commit()
        return redirect(url_for('dashboard_bp.dashboard'))  # ✅ Redireciona para o Dashboard

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao excluir projeto: {str(e)}"}), 500
