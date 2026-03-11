from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import text
from app import db
from app.models import Despesa
from datetime import datetime, timedelta

relatorio_bp = Blueprint('relatorio_bp', __name__)

@relatorio_bp.route('/relatorios')
@login_required
def listar_relatorios():
    query = text("""
        SELECT
            COALESCE(nome_colaborador, 'Não informado') AS nome,
            COALESCE(num_cartao, 'Não informado') AS cartao,
            COALESCE(nome_projeto, 'Não informado') AS projeto,
            COALESCE(nome_empresa, 'Não informado') AS empresa,
            COALESCE(valor, 0) AS valor,
            data_registro AS data,
            COALESCE(descricao, '') AS descricao_despesa
        FROM despesas
        ORDER BY data_registro DESC, nome_colaborador
    """)

    resultado = db.session.execute(query).fetchall()

    relatorios = []
    for row in resultado:
        relatorios.append({
            "nome": row.nome,
            "cartao": row.cartao,
            "projeto": row.projeto,
            "empresa": row.empresa,
            "valor": f"R$ {float(row.valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "data": row.data.strftime("%d/%m/%Y") if row.data else "",
            "descricao_despesa": row.descricao_despesa
        })

    return render_template("relatorios.html", relatorios=relatorios)