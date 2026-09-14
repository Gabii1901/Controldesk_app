from datetime import datetime

from sqlalchemy import func, literal_column

from app import db
from app.models import Despesa

_COLUNA_POR_DIMENSAO = {
    "colaborador": Despesa.nome_colaborador,
    "projeto": Despesa.nome_projeto,
    "empresa": Despesa.nome_empresa,
    "cidade": Despesa.cidade,
    "cartao": Despesa.num_cartao,
}


def _rotulo(agrupar_por: str):
    if agrupar_por == "mes":
        return func.date_trunc(literal_column("'month'"), Despesa.data_registro)
    if agrupar_por == "dia":
        return func.date_trunc(literal_column("'day'"), Despesa.data_registro)

    coluna = _COLUNA_POR_DIMENSAO[agrupar_por]
    # func.upper evita que a mesma pessoa/projeto/empresa vire dois grupos
    # diferentes só por causa de maiúsculas/minúsculas divergentes no cadastro.
    return func.upper(func.coalesce(coluna, literal_column("'Não informado'")))


def _sem_acento_ilike(coluna, termo: str):
    # unaccent() torna a comparação insensível a acento além de maiúscula/minúscula
    # (ilike já cobre isso sozinho), porque a IA às vezes devolve o termo do jeito
    # que o usuário digitou e às vezes "traduz" removendo acentos (ex.: "almoço" -> "almoco").
    return func.unaccent(coluna).ilike(func.unaccent(f"%{termo}%"))


def _aplicar_filtros(query, filtros: dict):
    if filtros.get("colaborador"):
        query = query.filter(_sem_acento_ilike(Despesa.nome_colaborador, filtros["colaborador"]))
    if filtros.get("projeto"):
        query = query.filter(_sem_acento_ilike(Despesa.nome_projeto, filtros["projeto"]))
    if filtros.get("empresa"):
        query = query.filter(_sem_acento_ilike(Despesa.nome_empresa, filtros["empresa"]))
    if filtros.get("cidade"):
        query = query.filter(_sem_acento_ilike(Despesa.cidade, filtros["cidade"]))
    if filtros.get("cartao"):
        query = query.filter(Despesa.num_cartao.ilike(f"%{filtros['cartao']}%"))
    if filtros.get("descricao"):
        query = query.filter(_sem_acento_ilike(Despesa.descricao, filtros["descricao"]))
    if filtros.get("valor_min") is not None:
        query = query.filter(Despesa.valor >= filtros["valor_min"])
    if filtros.get("valor_max") is not None:
        query = query.filter(Despesa.valor <= filtros["valor_max"])

    if filtros.get("data_inicio"):
        try:
            inicio = datetime.strptime(filtros["data_inicio"], "%Y-%m-%d")
            query = query.filter(Despesa.data_registro >= inicio)
        except ValueError:
            pass

    if filtros.get("data_fim"):
        try:
            fim = datetime.strptime(filtros["data_fim"], "%Y-%m-%d")
            query = query.filter(Despesa.data_registro <= fim)
        except ValueError:
            pass

    return query


def montar_dados_grafico(spec: dict) -> dict:
    rotulo_col = _rotulo(spec["agrupar_por"])

    metrica_col = (
        func.sum(Despesa.valor) if spec["metrica"] == "soma_valor" else func.count(Despesa.id)
    )

    query = db.session.query(rotulo_col.label("rotulo"), metrica_col.label("valor"))
    query = _aplicar_filtros(query, spec["filtros"])
    # Agrupa pelo alias "rotulo" (extensão do Postgres) para não repetir a
    # expressão (coalesce/date_trunc) no SELECT e no GROUP BY: quando essa
    # repetição vira dois bind params distintos, o pg8000 faz o Postgres
    # rejeitar a query com "coluna deve aparecer no GROUP BY".
    query = query.group_by(literal_column("rotulo")).order_by(metrica_col.desc())

    if spec.get("top_n"):
        query = query.limit(spec["top_n"])

    resultado = query.all()

    if spec["agrupar_por"] in ("mes", "dia"):
        formato = "%m/%Y" if spec["agrupar_por"] == "mes" else "%d/%m/%Y"
        linhas = sorted(resultado, key=lambda r: r.rotulo)
        labels = [r.rotulo.strftime(formato) if r.rotulo else "Não informado" for r in linhas]
        valores = [float(r.valor or 0) for r in linhas]
    else:
        labels = [str(r.rotulo) for r in resultado]
        valores = [float(r.valor or 0) for r in resultado]

    return {
        "tipo_grafico": spec["tipo_grafico"],
        "titulo": spec["titulo"],
        "metrica": spec["metrica"],
        "labels": labels,
        "valores": valores,
    }
