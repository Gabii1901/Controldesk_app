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
    return render_template("relatorios.html")


@relatorio_bp.route('/relatorios/colaboradores')
@login_required
def relatorio_colaborador():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    if not data_inicio or not data_fim:
        return render_template('Rel.gastos_mensais_col.html', relatorio=[], datetime=datetime, timedelta=timedelta)

    data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
    data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)

    query = text("""
        SELECT * FROM despesas_colaborador_detalhado
        WHERE data_pagamento >= :inicio AND data_pagamento < :fim
        ORDER BY nome_colaborador, data_pagamento
    """)

    resultado = db.session.execute(query, {
        'inicio': data_inicio_dt,
        'fim': data_fim_dt
    }).fetchall()

    relatorio = {}
    for row in resultado:
        nome = row.nome_colaborador.strip() if row.nome_colaborador else 'Desconhecido'
        if nome not in relatorio:
            relatorio[nome] = {'nome': nome, 'despesas': [], 'total': 0}
        relatorio[nome]['despesas'].append(row)
        relatorio[nome]['total'] += row.valor

    return render_template('Rel.gastos_mensais_col.html', relatorio=relatorio.values(), datetime=datetime, timedelta=timedelta)


@relatorio_bp.route('/relatorios/cartoes')
@login_required
def relatorio_cartoes():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    # 🔸 Se não houver filtro, renderiza com datas sugeridas no template
    if not data_inicio or not data_fim:
        return render_template('Rel.gastos_cartao.html', relatorio=[], datetime=datetime, timedelta=timedelta)

    # 🔸 Converte datas para datetime e soma 1 dia no fim
    data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
    data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)

    query = text("""
        SELECT * FROM despesas_cartao_detalhado
        WHERE data_pagamento >= :inicio AND data_pagamento < :fim
        ORDER BY numero_cartao, data_pagamento
    """)

    resultado = db.session.execute(query, {
        'inicio': data_inicio_dt,
        'fim': data_fim_dt
    }).fetchall()

    relatorio = {}
    for row in resultado:
        numero = row.numero_cartao if row.numero_cartao else 'Não informado'
        if numero not in relatorio:
            relatorio[numero] = {'numero': numero, 'despesas': [], 'total': 0}

        relatorio[numero]['despesas'].append({
            'data_pagamento': row.data_pagamento,
            'descricao': row.descricao,
            'valor': row.valor,
            'observacao': row.observacao,
            'nome_colaborador': row.nome_colaborador
        })

        relatorio[numero]['total'] += row.valor or 0

    return render_template('Rel.gastos_cartao.html', relatorio=relatorio.values(), datetime=datetime, timedelta=timedelta)



@relatorio_bp.route('/relatorios/projetos')
@login_required
def relatorio_projetos():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    # 🔸 Se não vier filtro, renderiza com datas sugeridas no HTML
    if not data_inicio or not data_fim:
        return render_template('Rel.gastos_projeto.html', relatorio=[], datetime=datetime, timedelta=timedelta)

    # 🔸 Converte as datas e ajusta fim +1 dia
    data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
    data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)

    query = text("""
        SELECT * FROM despesas_projeto_detalhado
        WHERE data_pagamento >= :inicio AND data_pagamento < :fim
        ORDER BY nome_projeto, data_pagamento
    """)

    resultado = db.session.execute(query, {
        'inicio': data_inicio_dt,
        'fim': data_fim_dt
    }).fetchall()

    relatorio = {}
    for row in resultado:
        projeto = row.nome_projeto if row.nome_projeto else 'Não informado'
        if projeto not in relatorio:
            relatorio[projeto] = {'projeto': projeto, 'despesas': [], 'total': 0}
        relatorio[projeto]['despesas'].append(row)
        relatorio[projeto]['total'] += row.valor

    return render_template('Rel.gastos_projeto.html', relatorio=relatorio.values(), datetime=datetime, timedelta=timedelta)

@relatorio_bp.route('/relatorios/empresa', methods=['GET'])
@login_required
def relatorio_empresa():
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    try:
        if data_inicio and data_fim:
            inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
        else:
            hoje = datetime.utcnow()
            inicio = hoje.replace(day=1)
            fim = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.listar_relatorios"))

    despesas = Despesa.query.filter(
        Despesa.data_registro >= inicio,
        Despesa.data_registro < fim
    ).all()


    agrupado = {}
    for d in despesas:
        nome = d.nome_empresa or "Não informado"
        agrupado.setdefault(nome, []).append(d)

    relatorio = []
    for empresa, lista in agrupado.items():
        relatorio.append({
            "empresa": empresa,
            "despesas": lista,
            "total": sum(d.valor for d in lista)
        })

    return render_template(
        'Rel.gastos_empresa.html',
        relatorio=relatorio,
        datetime=datetime,
        timedelta=timedelta
    )
