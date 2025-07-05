from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate  # ✅ Adicionado para gerenciar migrações

from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate = Migrate(app, db)  # ✅ Inicializa o Flask-Migrate

    login_manager.login_view = "auth_bp.login"
    login_manager.login_message_category = "info"

    from app.models import Usuario, Colaborador  # ✅ Importa modelos para user_loader

    @login_manager.user_loader
    def load_user(user_id):
        user = Usuario.query.get(int(user_id))
        if user:
            return user
        return Colaborador.query.get(int(user_id))

    # ✅ Registra os Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.projeto_routes import projeto_bp
    from app.routes.empresa_routes import empresa_bp
    from app.routes.colaborador_routes import colaborador_bp
    from app.routes.relatorio_routes import relatorio_bp
    from app.routes.despesa_routes import despesa_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projeto_bp)
    app.register_blueprint(empresa_bp)
    app.register_blueprint(colaborador_bp)
    app.register_blueprint(relatorio_bp)
    app.register_blueprint(despesa_bp)

    return app
