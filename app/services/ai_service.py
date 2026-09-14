import json
import requests
from datetime import date
from flask import current_app

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

DIMENSOES_VALIDAS = {"colaborador", "projeto", "empresa", "cidade", "cartao", "mes", "dia"}
METRICAS_VALIDAS = {"soma_valor", "quantidade"}
TIPOS_VALIDOS = {"barra", "linha", "pizza"}

SYSTEM_PROMPT = """Você traduz pedidos em português sobre despesas corporativas em uma
especificação JSON de gráfico. NUNCA invente valores numéricos: sua única tarefa é escolher
como agrupar e filtrar os dados; os números reais serão calculados depois a partir do banco.

Responda APENAS com um JSON no formato exato:
{
  "tipo_grafico": "barra" | "linha" | "pizza",
  "titulo": "string curta e descritiva",
  "agrupar_por": "colaborador" | "projeto" | "empresa" | "cidade" | "cartao" | "mes" | "dia",
  "metrica": "soma_valor" | "quantidade",
  "top_n": inteiro entre 3 e 20 (use 10 se o usuário não especificar, ou null para não limitar),
  "filtros": {
    "colaborador": "texto ou null",
    "projeto": "texto ou null",
    "empresa": "texto ou null",
    "cidade": "texto ou null",
    "cartao": "texto ou null",
    "descricao": "texto ou null",
    "data_inicio": "YYYY-MM-DD ou null",
    "data_fim": "YYYY-MM-DD ou null",
    "valor_min": "número ou null",
    "valor_max": "número ou null"
  }
}

Esses filtros cobrem exatamente as colunas que o usuário vê na tela de Relatórios de despesas:
Nome (colaborador), Cartão, Projeto, Empresa, Valor, Data e Descrição da despesa. Sempre que o
pedido mencionar qualquer uma dessas colunas para restringir os dados, preencha o filtro correspondente.

Regras:
- "soma_valor" = total gasto em R$; "quantidade" = número de lançamentos. Use soma_valor quando o
  pedido falar em "gasto", "valor", "total"; use quantidade quando falar em "quantidade", "número de despesas".
- "filtros.descricao" serve para o TIPO/categoria da despesa (ex.: "almoço", "hospedagem",
  "combustível", "passagem", "hotel", "jantar", "estacionamento"). Sempre que o pedido mencionar um
  tipo específico de gasto, coloque essa palavra (singular, sem acento de gênero) em filtros.descricao.
  Ela é comparada com a descrição livre de cada lançamento, então prefira um termo curto e específico.
- "filtros.cartao" é o número (ou os últimos dígitos) do cartão mencionado no pedido, como texto.
- "filtros.valor_min" e "filtros.valor_max" servem para pedidos como "despesas acima de R$500",
  "gastos entre 100 e 300 reais" ou "abaixo de 50 reais" — preencha apenas o(s) limite(s) citado(s).
- Se o pedido mencionar evolução no tempo (mês a mês, ao longo do ano), use agrupar_por "mes" e tipo_grafico "linha".
- Se o pedido já restringe tudo a UM colaborador/projeto/empresa/cidade/cartão específico (via filtros)
  e não pede explicitamente uma evolução no tempo ou uma comparação entre categorias, use esse mesmo
  campo como agrupar_por (ex.: agrupar_por "colaborador") para retornar o total filtrado em uma única
  barra, em vez de quebrar por mês.
- Se o pedido pedir "top N" de algo, use esse N em top_n.
- Resolva períodos relativos (ex.: "este mês", "últimos 3 meses", "este ano") em datas absolutas
  usando a data de hoje informada.
- Não inclua nenhum texto fora do JSON.
"""


class AiServiceError(Exception):
    pass


def gerar_especificacao_grafico(pergunta: str) -> dict:
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key or api_key == "coloque_sua_chave_groq_aqui":
        raise AiServiceError("GROQ_API_KEY não configurada no servidor.")

    payload = {
        "model": current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Data de hoje: {date.today().isoformat()}\nPedido do usuário: {pergunta}",
            },
        ],
    }

    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise AiServiceError(f"Falha ao conectar à Groq: {exc}") from exc

    if resp.status_code != 200:
        raise AiServiceError(f"Groq retornou erro {resp.status_code}: {resp.text[:300]}")

    try:
        conteudo = resp.json()["choices"][0]["message"]["content"]
        spec = json.loads(conteudo)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise AiServiceError("Resposta da IA em formato inesperado.") from exc

    return _validar_especificacao(spec)


def _validar_especificacao(spec: dict) -> dict:
    agrupar_por = spec.get("agrupar_por")
    metrica = spec.get("metrica")
    tipo_grafico = spec.get("tipo_grafico")

    if agrupar_por not in DIMENSOES_VALIDAS:
        raise AiServiceError(f"Agrupamento inválido retornado pela IA: {agrupar_por!r}")
    if metrica not in METRICAS_VALIDAS:
        raise AiServiceError(f"Métrica inválida retornada pela IA: {metrica!r}")
    if tipo_grafico not in TIPOS_VALIDOS:
        tipo_grafico = "barra"

    top_n = spec.get("top_n")
    if top_n is not None:
        try:
            top_n = max(1, min(int(top_n), 50))
        except (TypeError, ValueError):
            top_n = 10

    filtros_brutos = spec.get("filtros") or {}

    def _num(chave):
        valor = filtros_brutos.get(chave)
        if valor in (None, ""):
            return None
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None

    filtros = {
        "colaborador": filtros_brutos.get("colaborador") or None,
        "projeto": filtros_brutos.get("projeto") or None,
        "empresa": filtros_brutos.get("empresa") or None,
        "cidade": filtros_brutos.get("cidade") or None,
        "cartao": filtros_brutos.get("cartao") or None,
        "descricao": filtros_brutos.get("descricao") or None,
        "data_inicio": filtros_brutos.get("data_inicio") or None,
        "data_fim": filtros_brutos.get("data_fim") or None,
        "valor_min": _num("valor_min"),
        "valor_max": _num("valor_max"),
    }

    return {
        "tipo_grafico": tipo_grafico,
        "titulo": (spec.get("titulo") or "Gráfico de despesas").strip()[:120],
        "agrupar_por": agrupar_por,
        "metrica": metrica,
        "top_n": top_n,
        "filtros": filtros,
    }
