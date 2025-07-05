from flask import Blueprint, request, render_template, jsonify, redirect, url_for
from app.models import Empresa
from app import db

empresa_bp = Blueprint('empresa_bp', __name__)

# ✅ Listagem de Empresas
@empresa_bp.route('/empresas', methods=['GET'])
def listar_empresas():
    try:
        empresas = Empresa.query.all()
        return render_template("listar_empresas.html", empresas=empresas)
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar empresas: {str(e)}"}), 500

# ✅ Página de Cadastro de Empresa
@empresa_bp.route('/cadastro_empresa', methods=['GET'])
def cadastro_empresa_page():
    return render_template("cadastro_empresa.html")

# ✅ Cadastro de Empresa (POST)
@empresa_bp.route('/cadastro_empresa', methods=['POST'])
def cadastro_empresa():
    try:
        data = request.form

        # 🔹 Verifica se os campos obrigatórios estão preenchidos
        if not data.get('razao_social') or not data.get('cnpj') or not data.get('endereco'):
            return jsonify({"error": "Todos os campos são obrigatórios!"}), 400

        # 🔹 Validação: Verifica se o CNPJ já existe
        empresa_existente = Empresa.query.filter_by(cnpj=data['cnpj']).first()
        if empresa_existente:
            return jsonify({"error": "CNPJ já cadastrado!"}), 400

        # 🔹 Criando nova empresa
        nova_empresa = Empresa(
            razao_social=data['razao_social'],
            cnpj=data['cnpj'],
            endereco=data['endereco']
        )
        db.session.add(nova_empresa)
        db.session.commit()

        return redirect(url_for('empresa_bp.listar_empresas'))

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao cadastrar empresa: {str(e)}"}), 500

# ✅ Edição de Empresa
@empresa_bp.route('/empresas/editar/<int:id>', methods=['GET', 'POST'])
def editar_empresa(id):
    empresa = Empresa.query.get_or_404(id)

    if request.method == 'POST':
        data = request.form
        empresa.razao_social = data.get('razao_social', empresa.razao_social)
        empresa.cnpj = data.get('cnpj', empresa.cnpj)
        empresa.endereco = data.get('endereco', empresa.endereco)

        db.session.commit()
        return redirect(url_for('empresa_bp.listar_empresas'))

    return render_template("editar_empresa.html", empresa=empresa)
