from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
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
            d.id AS despesa_id,
            COALESCE(d.nome_colaborador, 'Não informado') AS nome,
            COALESCE(d.num_cartao, 'Não informado') AS cartao,
            COALESCE(d.nome_projeto, 'Não informado') AS projeto,
            COALESCE(d.nome_empresa, 'Não informado') AS empresa,
            COALESCE(d.valor, 0) AS valor,
            d.data_registro AS data,
            COALESCE(d.descricao, '') AS descricao_despesa,
            (SELECT MIN(i.id) FROM imagens i WHERE i.despesa_id = d.id) AS imagem_id
        FROM despesas d
        ORDER BY d.data_registro DESC, d.nome_colaborador
    """)

    resultado = db.session.execute(query).fetchall()

    relatorios = []
    for row in resultado:
        relatorios.append({
            "despesa_id": row.despesa_id,
            "nome": row.nome,
            "cartao": row.cartao,
            "projeto": row.projeto,
            "empresa": row.empresa,
            "valor": f"R$ {float(row.valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "data": row.data.strftime("%d/%m/%Y") if row.data else "",
            "descricao_despesa": row.descricao_despesa,
            "imagem_id": row.imagem_id,
        })

    return render_template(
        "relatorios.html",
        relatorios=relatorios,
        usuario_nome=getattr(current_user, "nome", "Usuário"),
    )