from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from app import db, bcrypt
from app.models import Usuario

user_bp = Blueprint('user_bp', __name__)

# Página de Cadastro de Usuário (Renderiza o Formulário)
@user_bp.route('/cadastro_usuario', methods=['GET'])
def cadastro_usuario_page():
    return render_template("cadastro_usuario.html")

# Endpoint para Cadastrar Usuário
@user_bp.route('/cadastro_usuario', methods=['POST'])
def cadastro_usuario():
    # Verifica se o tipo de conteúdo da requisição está correto
    if request.content_type != 'application/x-www-form-urlencoded':
        return jsonify({"error": "Tipo de conteúdo inválido. Use application/x-www-form-urlencoded"}), 415

    # Obtém os dados do formulário
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    senha = request.form.get('senha')

    # Valida se todos os campos obrigatórios foram preenchidos
    if not nome or not cpf or not senha:
        flash("Todos os campos são obrigatórios!", "error")
        return redirect(url_for('user_bp.cadastro_usuario_page'))

    # Verifica se o CPF já está cadastrado no sistema
    usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
    if usuario_existente:
        flash("Já existe um usuário com este CPF!", "error")
        return redirect(url_for('user_bp.cadastro_usuario_page'))

    # Criptografa a senha antes de salvar no banco
    senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

    # Cria um novo usuário
    novo_usuario = Usuario(nome=nome, cpf=cpf, senha=senha_hash)
    db.session.add(novo_usuario)
    db.session.commit()

    flash("Usuário cadastrado com sucesso!", "success")
    return redirect(url_for('user_bp.cadastro_usuario_page'))

# Endpoint para listar usuários cadastrados
@user_bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    usuarios = Usuario.query.all()
    usuarios_json = [{"id": u.id, "nome": u.nome, "cpf": u.cpf} for u in usuarios]
    return jsonify(usuarios_json), 200

# Endpoint para atualizar um usuário pelo ID
@user_bp.route('/usuarios/<int:id>', methods=['PUT'])
def atualizar_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"error": "Usuário não encontrado"}), 404

    data = request.form
    usuario.nome = data.get('nome', usuario.nome)
    usuario.cpf = data.get('cpf', usuario.cpf)
    if 'senha' in data and data['senha']:
        usuario.senha = bcrypt.generate_password_hash(data['senha']).decode('utf-8')

    db.session.commit()
    return jsonify({"message": "Usuário atualizado com sucesso!"}), 200

# Endpoint para excluir um usuário pelo ID
@user_bp.route('/usuarios/<int:id>', methods=['DELETE'])
def excluir_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"error": "Usuário não encontrado"}), 404

    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"message": "Usuário excluído com sucesso!"}), 200
