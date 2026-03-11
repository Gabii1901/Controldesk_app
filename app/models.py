from flask_login import UserMixin
from app import db, bcrypt
from datetime import datetime
from pytz import timezone  # hora de Brasília

# Associação N:N entre colaboradores e projetos
colaborador_projeto = db.Table(
    "colaborador_projeto",
    db.Column("colaborador_id", db.Integer, db.ForeignKey("colaboradores.id"), primary_key=True),
    db.Column("projeto_id", db.Integer, db.ForeignKey("projetos.id"), primary_key=True),
)

# =========================
# Modelo de Usuário (admin)
# =========================
class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    def set_password(self, senha: str):
        self.senha = bcrypt.generate_password_hash(senha).decode("utf-8")

    def check_password(self, senha: str) -> bool:
        return bcrypt.check_password_hash(self.senha, senha)

    def get_id(self) -> str:
        return f"U:{self.id}"   # << prefixo para diferenciar do Colaborador

# =================
# Modelo de Empresa
# =================
class Empresa(db.Model):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    endereco = db.Column(db.String(255), nullable=False)

    projetos = db.relationship("Projeto", backref="empresa", cascade="all, delete-orphan")
    colaboradores = db.relationship("Colaborador", backref="empresa", cascade="all, delete-orphan")

# =================
# Modelo de Projeto
# =================
class Projeto(db.Model):
    __tablename__ = "projetos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    local = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default="EM ANDAMENTO")

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    colaboradores = db.relationship("Colaborador", secondary=colaborador_projeto, backref="projetos")

# ====================
# Modelo de Colaborador
# ====================
class Colaborador(db.Model, UserMixin):
    __tablename__ = "colaboradores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    numero_cartao = db.Column(db.String(4), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)

    def set_password(self, senha: str):
        self.senha = bcrypt.generate_password_hash(senha).decode("utf-8")

    def check_password(self, senha: str) -> bool:
        return bcrypt.check_password_hash(self.senha, senha)

    def get_id(self) -> str:
        return f"C:{self.id}"   # << prefixo para diferenciar do Usuario

# ==============
# Modelo Despesa
# ==============
class Despesa(db.Model):
    __tablename__ = "despesas"

    id = db.Column(db.Integer, primary_key=True)
    cidade = db.Column(db.String(255))
    local = db.Column(db.String(255))
    numero_documento = db.Column(db.String(50))
    descricao = db.Column(db.Text)
    valor = db.Column(db.Numeric(10, 2))
    observacao = db.Column(db.Text)
    complemento = db.Column(db.Text, nullable=False)
    data_registro = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone("America/Sao_Paulo")),
    )
    nome_colaborador = db.Column(db.String(100))
    cnpj_cpf_local = db.Column(db.String(18))
    nome_empresa = db.Column(db.String(255))
    num_cartao = db.Column(db.String(4))
    nome_projeto = db.Column(db.String(255))

    imagens = db.relationship("Imagem", back_populates="despesa", lazy=True, cascade="all, delete-orphan")

# =============
# Modelo Imagem
# =============
class Imagem(db.Model):
    __tablename__ = "imagens"

    id = db.Column(db.Integer, primary_key=True)
    despesa_id = db.Column(db.Integer, db.ForeignKey("despesas.id"), nullable=False)
    imagem = db.Column(db.LargeBinary, nullable=False)
    data_upload = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone("America/Sao_Paulo")),
    )
    nome_arquivo = db.Column(db.String(255))
    caminho = db.Column(db.String(255), nullable=False)

    despesa = db.relationship("Despesa", back_populates="imagens")

