import os
import logging
from dotenv import load_dotenv

load_dotenv()  # Carregar variáveis do .env

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "sua_chave_secreta")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")  # Ajustar nome se no .env for DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "sua_chave_secreta")
    JWT_ACCESS_TOKEN_EXPIRES = 7200  # 2 horas

    # Groq (IA para geração de gráficos)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    # Configurações de segurança
    SESSION_COOKIE_SECURE = True      # Apenas HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https"

    # Configuração de log (produção)
    LOG_LEVEL = logging.WARNING
