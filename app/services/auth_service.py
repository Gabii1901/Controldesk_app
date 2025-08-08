from app.models import Usuario
from app import bcrypt

def authenticate_user(cpf, senha):
    usuario = Usuario.query.filter_by(cpf=cpf).first()
    if usuario and bcrypt.check_password_hash(usuario.senha, senha):
        return usuario
    return None
