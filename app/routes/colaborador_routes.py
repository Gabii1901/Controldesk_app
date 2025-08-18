from flask import Blueprint, request, render_template, jsonify, redirect, url_for, flash
from app.models import Colaborador, Projeto, Empresa
from app import db, bcrypt

colaborador_bp = Blueprint('colaborador_bp', __name__)

# ✅ Listar Colaboradores
@colaborador_bp.route('/colaboradores', methods=['GET'])
def listar_colaboradores():
    try:
        colaboradores = Colaborador.query.all()
        return render_template("listar_colaboradores.html", colaboradores=colaboradores)
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar colaboradores: {str(e)}"}), 500

# ✅ Página de Cadastro de Colaborador
@colaborador_bp.route('/cadastro_colaborador', methods=['GET'])
def cadastro_colaborador_page():
    try:
        projetos = Projeto.query.all()
        empresas = Empresa.query.all()
        return render_template("cadastro_colaborador.html", projetos=projetos, empresas=empresas)
    except Exception as e:
        return jsonify({"error": f"Erro ao carregar dados: {str(e)}"}), 500

# ✅ Cadastrar um Colaborador (POST)
@colaborador_bp.route('/cadastro_colaborador', methods=['POST'])
def criar_colaborador():
    try:
        data = request.form

        if not data.get('nome') or not data.get('cpf') or not data.get('numero_cartao') or not data.get('senha') or not data.get('empresa_id'):
            return jsonify({"error": "Todos os campos são obrigatórios!"}), 400

        if len(data['cpf']) != 14:
            return jsonify({"error": "CPF inválido! O formato deve ser XXX.XXX.XXX-XX"}), 400

        if len(data['numero_cartao']) != 4 or not data['numero_cartao'].isdigit():
            return jsonify({"error": "Número do cartão deve ter 4 dígitos numéricos!"}), 400

        empresa_id = int(data['empresa_id'])
        ids_projetos = list(map(int, request.form.getlist('projetos')))
        senha_hash = bcrypt.generate_password_hash(data['senha']).decode('utf-8')

        novo_colaborador = Colaborador(
            nome=data['nome'],
            cpf=data['cpf'],
            senha=senha_hash,
            numero_cartao=data['numero_cartao'],
            empresa_id=empresa_id,
            ativo=True
        )
        novo_colaborador.projetos = Projeto.query.filter(Projeto.id.in_(ids_projetos)).all()

        db.session.add(novo_colaborador)
        db.session.commit()

        return redirect(url_for('colaborador_bp.listar_colaboradores'))

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao cadastrar colaborador: {str(e)}"}), 500

# ✅ Editar Colaborador (GET)
@colaborador_bp.route('/editar_colaborador/<int:id>', methods=['GET'])
def editar_colaborador(id):
    try:
        colaborador = Colaborador.query.get_or_404(id)
        projetos = Projeto.query.all()
        empresas = Empresa.query.all()
        colaborador_projetos_ids = [p.id for p in colaborador.projetos]
        return render_template("editar_colaborador.html", colaborador=colaborador, projetos=projetos, empresas=empresas, colaborador_projetos_ids=colaborador_projetos_ids)
    except Exception as e:
        return jsonify({"error": f"Erro ao carregar colaborador para edição: {str(e)}"}), 500

# ✅ Atualizar Colaborador (POST)
@colaborador_bp.route('/editar_colaborador/<int:id>', methods=['POST'])
def atualizar_colaborador(id):
    try:
        colaborador = Colaborador.query.get_or_404(id)
        data = request.form

        colaborador.nome = data.get('nome', colaborador.nome)
        colaborador.cpf = data.get('cpf', colaborador.cpf)
        colaborador.numero_cartao = data.get('numero_cartao', colaborador.numero_cartao)
        colaborador.empresa_id = int(data.get('empresa_id', colaborador.empresa_id))

        ids_projetos = list(map(int, request.form.getlist('projetos')))
        colaborador.projetos = Projeto.query.filter(Projeto.id.in_(ids_projetos)).all()

        if data.get('senha'):
            colaborador.senha = bcrypt.generate_password_hash(data['senha']).decode('utf-8')

        db.session.commit()
        return redirect(url_for('colaborador_bp.listar_colaboradores'))

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao atualizar colaborador: {str(e)}"}), 500

# ✅ Ativar/Inativar Colaborador
@colaborador_bp.route('/colaboradores/alterar_status/<int:id>', methods=['POST'])
def alterar_status(id):
    try:
        colaborador = Colaborador.query.get_or_404(id)
        colaborador.ativo = not colaborador.ativo
        db.session.commit()
        flash(f"Colaborador {'ativado' if colaborador.ativo else 'inativado'} com sucesso!", "success")
        return redirect(url_for('colaborador_bp.editar_colaborador', id=id))
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao alterar status: {str(e)}"}), 500
