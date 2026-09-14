from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.services.ai_service import AiServiceError, gerar_especificacao_grafico
from app.services.grafico_service import montar_dados_grafico

ai_bp = Blueprint("ai_bp", __name__)


@ai_bp.route("/api/graficos/ia", methods=["POST"])
@login_required
def gerar_grafico_ia():
    dados = request.get_json(silent=True) or {}
    pergunta = (dados.get("pergunta") or "").strip()

    if not pergunta:
        return jsonify({"erro": "Descreva o gráfico que você quer gerar."}), 400

    try:
        spec = gerar_especificacao_grafico(pergunta)
        grafico = montar_dados_grafico(spec)
    except AiServiceError as exc:
        return jsonify({"erro": str(exc)}), 502

    if not grafico["labels"]:
        return jsonify({"erro": "Nenhuma despesa encontrada para esse pedido."}), 200

    return jsonify(grafico)
