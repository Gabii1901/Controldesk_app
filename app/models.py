from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from app import db, bcrypt 
from datetime import datetime

# ✅ Modelo de Usuário (Autenticação para administradores)
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)

    def set_password(self, senha):
        self.senha = bcrypt.generate_password_hash(senha).decode('utf-8')

    def check_password(self, senha):
        return bcrypt.check_password_hash(self.senha, senha)

    def get_id(self):
        return str(self.id)


# ✅ Modelo de Empresa
class Empresa(db.Model):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    endereco = db.Column(db.String(255), nullable=False)

    projetos = db.relationship('Projeto', back_populates='empresa', cascade="all, delete-orphan")
    colaboradores = db.relationship('Colaborador', back_populates='empresa', cascade="all, delete-orphan")


# ✅ Modelo de Projeto
class Projeto(db.Model):
    __tablename__ = "projetos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    local = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="EM ANDAMENTO")
    
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    empresa = db.relationship('Empresa', back_populates='projetos')
    colaboradores = db.relationship('Colaborador', back_populates='projeto', cascade="all, delete-orphan")


# ✅ Modelo de Colaborador
class Colaborador(db.Model, UserMixin):
    __tablename__ = "colaboradores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    numero_cartao = db.Column(db.String(4), nullable=False)

    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    projeto_id = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False)

    empresa = db.relationship('Empresa', back_populates='colaboradores')
    projeto = db.relationship('Projeto', back_populates='colaboradores')

    def set_password(self, senha):
        self.senha = bcrypt.generate_password_hash(senha).decode('utf-8')

    def check_password(self, senha):
        return bcrypt.check_password_hash(self.senha, senha)


# ✅ Modelo de Despesa
class Despesa(db.Model):
    __tablename__ = "despesas"

    id = db.Column(db.Integer, primary_key=True)
    nome_colaborador = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    local = db.Column(db.String(200), nullable=False)
    cnpj_cpf_local = db.Column(db.String(18), nullable=False)
    numero_documento = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.String(300), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    observacao = db.Column(db.String(300), nullable=True)
    complemento = db.Column(db.String(300), nullable=True)
    data_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # ✅ adiciona data automática

    imagens = db.relationship('Imagem', back_populates='despesa', cascade="all, delete-orphan")


# ✅ Modelo de Imagem
class Imagem(db.Model):
    __tablename__ = "imagens"

    id = db.Column(db.Integer, primary_key=True)
    despesa_id = db.Column(db.Integer, db.ForeignKey('despesas.id'), nullable=False)
    caminho = db.Column(db.String(255), nullable=False)  # ✅ Campo corrigido

    despesa = db.relationship('Despesa', back_populates='imagens')
