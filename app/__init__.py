from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Proxy (nginx) → garante scheme/host corretos no Flask
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # ✅ Filtro para formatar valores em R$ (pt-BR)
    @app.template_filter("brl")
    def format_brl(value):
        try:
            return f"R$ {value:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
        except Exception:
            return "R$ 0,00"

    # ✅ Configuração do JWT
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"
    jwt = JWTManager(app)

    # ✅ Inicialização de extensões
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate = Migrate(app, db)

    login_manager.login_view = "auth_bp.login"
    login_manager.login_message_category = "info"

    # ✅ Imports que dependem do app/db já prontos
    from app.models import Usuario, Colaborador

    # ✅ Flask-Login: carrega tanto Usuario quanto Colaborador
    @login_manager.user_loader
    def load_user(user_key: str):
        try:
            tipo, id_str = user_key.split(":", 1)
            _id = int(id_str)
        except Exception:
            return None

        if tipo == "U":
            return Usuario.query.get(_id)
        if tipo == "C":
            return Colaborador.query.get(_id)
        return None

    # ✅ Registro das rotas (Blueprints)
    from app.routes.auth_routes import auth_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.projeto_routes import projeto_bp
    from app.routes.empresa_routes import empresa_bp
    from app.routes.colaborador_routes import colaborador_bp
    from app.routes.relatorio_routes import relatorio_bp
    from app.routes.despesa_routes import despesa_bp
    from app.routes.user_routes import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projeto_bp)
    app.register_blueprint(empresa_bp)
    app.register_blueprint(colaborador_bp)
    app.register_blueprint(relatorio_bp)
    app.register_blueprint(despesa_bp)
    app.register_blueprint(user_bp)

    return app

