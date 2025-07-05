from flask import Blueprint, request, render_template, jsonify, redirect, url_for
from app.models import Colaborador, Projeto, Empresa  # ✅ Adicionando Empresa
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
        projetos = Projeto.query.all()  # 🔹 Buscar todos os projetos cadastrados
        empresas = Empresa.query.all()  # 🔹 Buscar todas as empresas cadastradas
        return render_template("cadastro_colaborador.html", projetos=projetos, empresas=empresas)
    except Exception as e:
        return jsonify({"error": f"Erro ao carregar dados: {str(e)}"}), 500

# ✅ Cadastrar um Colaborador (POST)
@colaborador_bp.route('/cadastro_colaborador', methods=['POST'])
def criar_colaborador():
    try:
        data = request.form

        if not data.get('nome') or not data.get('cpf') or not data.get('numero_cartao') or not data.get('senha') or not data.get('projeto_id') or not data.get('empresa_id'):
            return jsonify({"error": "Todos os campos são obrigatórios!"}), 400

        # 🔹 Validação do CPF
        if len(data['cpf']) != 14:
            return jsonify({"error": "CPF inválido! O formato deve ser XXX.XXX.XXX-XX"}), 400

        # 🔹 Validação do número do cartão
        if len(data['numero_cartao']) != 4 or not data['numero_cartao'].isdigit():
            return jsonify({"error": "Número do cartão deve ter 4 dígitos numéricos!"}), 400

        projeto_id = int(data['projeto_id'])  # 🔹 Certificando que projeto_id é um inteiro
        empresa_id = int(data['empresa_id'])  # 🔹 Certificando que empresa_id é um inteiro

        # ✅ Criptografando a senha antes de salvar
        senha_hash = bcrypt.generate_password_hash(data['senha']).decode('utf-8')

        novo_colaborador = Colaborador(
            nome=data['nome'],
            cpf=data['cpf'],
            senha=senha_hash,  # ✅ Senha agora é criptografada antes de salvar
            numero_cartao=data['numero_cartao'],
            projeto_id=projeto_id,  # 🔹 Associando o colaborador a um projeto
            empresa_id=empresa_id  # 🔹 Associando o colaborador a uma empresa
        )
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
        projetos = Projeto.query.all()  # 🔹 Obtém todos os projetos disponíveis para seleção
        empresas = Empresa.query.all()  # 🔹 Obtém todas as empresas para seleção
        return render_template("editar_colaborador.html", colaborador=colaborador, projetos=projetos, empresas=empresas)
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
        colaborador.projeto_id = int(data.get('projeto_id', colaborador.projeto_id))  # 🔹 Atualizando o projeto
        colaborador.empresa_id = int(data.get('empresa_id', colaborador.empresa_id))  # 🔹 Atualizando a empresa

        # ✅ Se uma nova senha for fornecida, ela será criptografada antes de ser salva
        if data.get('senha'):
            colaborador.senha = bcrypt.generate_password_hash(data['senha']).decode('utf-8')

        db.session.commit()
        return redirect(url_for('colaborador_bp.listar_colaboradores'))

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao atualizar colaborador: {str(e)}"}), 500

# ✅ Excluir Colaborador
@colaborador_bp.route('/excluir_colaborador/<int:id>', methods=['POST'])
def excluir_colaborador(id):
    try:
        colaborador = Colaborador.query.get_or_404(id)
        db.session.delete(colaborador)
        db.session.commit()
        return redirect(url_for('colaborador_bp.listar_colaboradores'))

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao excluir colaborador: {str(e)}"}), 500
