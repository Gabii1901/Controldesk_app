import os
import logging
from dotenv import load_dotenv

load_dotenv()  # Carregar variáveis do .env

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "sua_chave_secreta")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "sua_chave_secreta")
    JWT_ACCESS_TOKEN_EXPIRES = 7200  # 2 horas

    # Configuração do Log
    LOG_LEVEL = logging.DEBUG  # Níveis: DEBUG, INFO, WARNING, ERROR, CRITICAL
