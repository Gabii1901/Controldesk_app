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
    if request.content_type != 'application/x-www-form-urlencoded':
        return jsonify({"error": "Tipo de conteúdo inválido. Use application/x-www-form-urlencoded"}), 415

    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    senha = request.form.get('senha')

    if not nome or not cpf or not senha:
        flash("Todos os campos são obrigatórios!", "error")
        return redirect(url_for('user_bp.cadastro_usuario_page'))

    usuario_existente = Usuario.query.filter_by(cpf=cpf).first()
    if usuario_existente:
        flash("Já existe um usuário com este CPF!", "error")
        return redirect(url_for('user_bp.cadastro_usuario_page'))

    senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
    novo_usuario = Usuario(nome=nome, cpf=cpf, senha=senha_hash)
    db.session.add(novo_usuario)
    db.session.commit()

    flash("Usuário cadastrado com sucesso!", "success")
    return redirect(url_for('user_bp.cadastro_usuario_page'))

# Endpoint para listar usuários em JSON
@user_bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    usuarios = Usuario.query.all()
    usuarios_json = [{"id": u.id, "nome": u.nome, "cpf": u.cpf} for u in usuarios]
    return jsonify(usuarios_json), 200

# Página de edição e atualização de usuário
@user_bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
def atualizar_usuario_page(id):
    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        senha = request.form.get('senha')

        usuario.nome = nome
        usuario.cpf = cpf

        if senha:
            usuario.senha = bcrypt.generate_password_hash(senha).decode('utf-8')

        db.session.commit()
        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for('user_bp.listar_usuarios_page'))

    return render_template("editar_usuario.html", usuario=usuario)

# Endpoint para excluir usuário
@user_bp.route('/usuarios/<int:id>', methods=['DELETE'])
def excluir_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"error": "Usuário não encontrado"}), 404

    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"message": "Usuário excluído com sucesso!"}), 200

# Página de listagem com opções de edição e inativação
@user_bp.route('/usuarios/listar', methods=['GET'])
def listar_usuarios_page():
    usuarios = Usuario.query.all()
    return render_template("listar_usuarios.html", usuarios=usuarios)

# Inativar usuário
@user_bp.route('/usuarios/inativar/<int:id>')
def inativar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    usuario.ativo = False
    db.session.commit()
    flash("Usuário inativado com sucesso!", "success")
    return redirect(url_for('user_bp.listar_usuarios_page'))

# Ativar usuário
@user_bp.route('/usuarios/ativar/<int:id>')
def ativar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    usuario.ativo = True
    db.session.commit()
    flash("Usuário ativado com sucesso!", "success")
    return redirect(url_for('user_bp.listar_usuarios_page'))
