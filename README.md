# ControlDesk

**ControlDesk** é uma plataforma web para controle de despesas corporativas: colaboradores registram gastos (com comprovante anexado) vinculados a projetos e empresas, e a gestão acompanha tudo por dashboards, relatórios e gráficos gerados por IA.

Construído com **Flask** no backend, **PostgreSQL** como banco de dados e templates **HTML/CSS/JavaScript** renderizados pelo próprio servidor (Jinja2).

## Funcionalidades

- **Autenticação** de dois perfis (Usuário/gestor e Colaborador), com sessão via Flask-Login e API autenticada por JWT.
- **Cadastro de despesas**: cidade, estabelecimento, CPF/CNPJ, tipo, valor, observações e anexo de comprovante (imagem).
- **Histórico e listagem de despesas**, com filtros por projeto, empresa, colaborador e data.
- **Cadastro e gestão de empresas, projetos e colaboradores** (exclusivo da gestão), incluindo vínculo de colaboradores a projetos e filiais.
- **Relatórios**: gastos por empresa, por projeto, mensais por colaborador e por cartão, com exportação (Excel/PDF).
- **Gráficos por IA**: geração de gráficos a partir de perguntas em linguagem natural, usando a API da Groq para interpretar o pedido e montar a consulta.
- **Comprovantes armazenados em disco** (`app/static/uploads/`), com scripts de migração/compactação/verificação para manter o espaço em disco sob controle (ver [Scripts utilitários](#scripts-utilitários)).

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Flask 3, Flask-SQLAlchemy, Flask-Migrate (Alembic), Flask-Login, Flask-JWT-Extended, Flask-Bcrypt |
| Banco de dados | PostgreSQL |
| Frontend | HTML, CSS, JavaScript (Jinja2 server-side) |
| Relatórios | pandas, openpyxl, XlsxWriter, fpdf, pdfkit |
| IA | Groq API (geração de gráficos a partir de linguagem natural) |
| Autenticação | Flask-Login (sessão) + JWT (API) |

## Estrutura do projeto

```
app/
├── models.py              # Usuario, Empresa, Projeto, Colaborador, Despesa, Imagem
├── routes/                # Blueprints (auth, despesa, projeto, empresa, colaborador, relatorio, dashboard, user, ai)
├── services/               # Regras de negócio (auth, relatórios, gráficos por IA)
├── static/                 # CSS, imagens e uploads de comprovantes
└── templates/               # Páginas Jinja2 (cadastro, listagem, relatórios, dashboard...)
scripts/                    # Scripts de manutenção dos comprovantes (ver abaixo)
migrations/                 # Migrações do banco (Alembic/Flask-Migrate)
config.py                   # Configuração da app (lida variáveis do .env)
wsgi.py                     # Ponto de entrada para produção (Gunicorn/etc.)
```

## Como rodar localmente

### Pré-requisitos
- Python 3.10+
- PostgreSQL rodando e acessível

### Passo a passo

```bash
# 1. Criar e ativar um ambiente virtual
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
# Crie um arquivo .env na raiz do projeto com:
#   DATABASE_URL=postgresql://usuario:senha@host:porta/nome_do_banco
#   SECRET_KEY=uma_chave_secreta
#   JWT_SECRET_KEY=outra_chave_secreta
#   FLASK_ENV=development
#   GROQ_API_KEY=sua_chave_da_groq        # necessário só para os gráficos por IA
#   GROQ_MODEL=openai/gpt-oss-120b        # opcional, tem default

# 4. Aplicar as migrações do banco
flask db upgrade

# 5. Rodar a aplicação
python app/run.py
```

Em produção, a aplicação é servida via `wsgi.py` (compatível com Gunicorn/uWSGI atrás de um proxy reverso como o nginx, já com `ProxyFix` configurado).

## Scripts utilitários

Scripts de manutenção dos comprovantes de despesa, pensados para rodar em VPS com pouca RAM (processam em lotes):

- `scripts/migrar_imagens_para_disco.py` — migra comprovantes salvos como BLOB no Postgres para arquivos em `app/static/uploads/comprovantes/`, só atualizando o banco depois de confirmar que o arquivo gravado bate byte a byte com o original. Aceita `--dry-run`.
- `scripts/verificar_migracao_imagens.py` — confere, em lotes, se os arquivos em disco batem (hash SHA-256) com os BLOBs ainda existentes no banco. Só leitura, não altera nada.
- `scripts/compactar_comprovantes_antigos.py` — redimensiona e recomprime (JPEG) comprovantes com mais de 3 meses para reduzir o espaço em disco. Operação definitiva: só substitui o arquivo original se o resultado for realmente menor.

## Segurança

- Senhas de usuários e colaboradores são armazenadas com hash (bcrypt).
- Sessões web usam cookies `HttpOnly`, `Secure` e `SameSite=Lax`.
- Endpoints de API (ex.: gráficos por IA) exigem token JWT via header `Authorization: Bearer <token>`.
