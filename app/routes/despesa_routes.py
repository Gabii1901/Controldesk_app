from sqlalchemy.orm import defer, joinedload
from flask import (
    Blueprint, request, jsonify, render_template, redirect, url_for,
    flash, Response, send_file, session
    
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
import shutil
import filetype
from fpdf import FPDF
import pandas as pd
from io import BytesIO
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import Despesa, Imagem, Colaborador, Usuario, Projeto
import pytz


despesa_bp = Blueprint('despesa_bp', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ✅ pasta temporária para pré-confirmação (NÃO salva bytes em cookie)
# ajuste se quiser outro lugar:
TMP_DIR = os.path.join("app", "static", "uploads", "tmp_despesas")

# ✅ pasta definitiva dos comprovantes (antes iam em bytes pro Postgres)
COMPROVANTES_DIR = os.path.join("app", "static", "uploads", "comprovantes")


def _ensure_comprovantes_dir():
    os.makedirs(COMPROVANTES_DIR, exist_ok=True)


def _comprovante_abs_path(nome_arquivo: str) -> str:
    return os.path.join(COMPROVANTES_DIR, nome_arquivo)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _is_colaborador():
    return isinstance(current_user, Colaborador)


def _brl(v: float) -> str:
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _ensure_tmp_dir():
    os.makedirs(TMP_DIR, exist_ok=True)


def _tmp_abs_path(tmp_name: str) -> str:
    return os.path.join(TMP_DIR, tmp_name)


def _tmp_public_url(tmp_name: str) -> str:
    # static path
    return url_for("static", filename=f"uploads/tmp_despesas/{tmp_name}")


def _cleanup_tmp(tmp_name: str | None):
    if not tmp_name:
        return
    try:
        p = _tmp_abs_path(tmp_name)
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


@despesa_bp.route('/menu_despesas', methods=['GET'])
@login_required
def menu_despesas():
    if not _is_colaborador():
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))
    return render_template("menu_despesas.html", colaborador=current_user)


@despesa_bp.route('/cadastro_despesa', methods=['GET'])
@login_required
def cadastro_despesa_page():
    if not _is_colaborador():
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))
    return render_template("cadastro_despesa.html", colaborador=current_user)


# =========================
# ✅ PRÉ-CONFIRMAÇÃO (GET)
# =========================
@despesa_bp.route('/despesa_confirmar', methods=['GET'])
@login_required
def despesa_confirmar_page():
    if not _is_colaborador():
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    payload = session.get("despesa_preview") or {}
    if not payload:
        flash("Nenhuma despesa para confirmar.", "warning")
        return redirect(url_for("despesa_bp.cadastro_despesa_page"))

    projeto_nome = None
    if payload.get("projeto_id"):
        p = Projeto.query.get(payload.get("projeto_id"))
        projeto_nome = p.nome if p else None

    try:
        valor_f = float(payload.get("valor") or 0)
    except Exception:
        valor_f = 0.0

    # ✅ URL pública para preview da imagem (vem do arquivo temporário)
    tmp_name = payload.get("tmp_name")
    imagem_preview_url = _tmp_public_url(tmp_name) if tmp_name else None

    return render_template(
        "despesa_confirmar.html",
        colaborador=current_user,
        dados=payload,
        projeto_nome=projeto_nome,
        valor_formatado=_brl(valor_f),
        imagem_preview_url=imagem_preview_url,
        imagem_nome=payload.get("imagem_nome"),
    )


# ==========================================
# ✅ PRÉ-CONFIRMAÇÃO -> SALVAR DEFINITIVO (POST)
# ==========================================
@despesa_bp.route('/despesa_confirmar', methods=['POST'])
@login_required
def despesa_confirmar_salvar():
    if not _is_colaborador():
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    payload = session.get("despesa_preview") or {}
    if not payload:
        flash("Nenhuma despesa para confirmar.", "warning")
        return redirect(url_for("despesa_bp.cadastro_despesa_page"))

    fuso_brasilia = pytz.timezone('America/Sao_Paulo')
    data_registro = datetime.now(fuso_brasilia)

    projeto_id = payload.get("projeto_id")
    projeto = Projeto.query.get(projeto_id) if projeto_id else None
    nome_projeto = projeto.nome if projeto else None

    try:
        valor_f = float(payload.get("valor"))
    except Exception:
        flash("Valor inválido.", "danger")
        return redirect(url_for("despesa_bp.despesa_confirmar_page"))

    # ✅ salva despesa
    despesa = Despesa(
        nome_colaborador=current_user.nome,
        cidade=payload.get("cidade"),
        local=payload.get("local"),
        cnpj_cpf_local=payload.get("cnpj_cpf_local"),
        numero_documento=payload.get("numero_documento"),
        descricao=payload.get("descricao"),
        valor=valor_f,
        observacao=payload.get("observacao") or "",
        complemento=payload.get("complemento"),
        nome_empresa=current_user.empresa.razao_social if current_user.empresa else None,
        num_cartao=current_user.numero_cartao or '',
        nome_projeto=nome_projeto,
        data_registro=data_registro
    )

    tmp_name = payload.get("tmp_name")
    tmp_path = _tmp_abs_path(tmp_name) if tmp_name else None

    try:
        db.session.add(despesa)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("Erro ao salvar a despesa. Verifique os campos e tente novamente.", "danger")
        return redirect(url_for("despesa_bp.despesa_confirmar_page"))

    # ✅ salva imagem (lê do arquivo temporário e grava em disco, não no BD)
    if tmp_path and os.path.exists(tmp_path):
        try:
            with open(tmp_path, "rb") as f:
                raw = f.read()

            # tenta inferir extensão
            kind = filetype.guess(raw)
            extensao = (kind.extension if kind else None) or (payload.get("imagem_ext") or "png")

            nome_colab = current_user.nome.lower().replace(" ", "_")
            timestamp = datetime.now(fuso_brasilia).strftime("%Y%m%d_%H%M%S")
            nome_arquivo = secure_filename(f"{nome_colab}_despesa{despesa.id}_{timestamp}.{extensao}")

            _ensure_comprovantes_dir()
            with open(_comprovante_abs_path(nome_arquivo), "wb") as destino:
                destino.write(raw)

            imagem = Imagem(
                despesa_id=despesa.id,
                nome_arquivo=nome_arquivo,
                caminho=nome_arquivo,
                data_upload=datetime.now(fuso_brasilia)
            )
            db.session.add(imagem)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Despesa salva, mas houve erro ao salvar a imagem.", "warning")
        finally:
            _cleanup_tmp(tmp_name)

    # limpa preview da sessão (não estoura cookie)
    session.pop("despesa_preview", None)

    return redirect(url_for('despesa_bp.despesa_sucesso', despesa_id=despesa.id))


# ✅ cancelar confirmação (opcional, mas recomendado)
@despesa_bp.route('/despesa_confirmar/cancelar', methods=['POST'])
@login_required
def despesa_confirmar_cancelar():
    if not _is_colaborador():
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    payload = session.get("despesa_preview") or {}
    _cleanup_tmp(payload.get("tmp_name"))
    session.pop("despesa_preview", None)

    flash("Cadastro cancelado.", "info")
    return redirect(url_for("despesa_bp.cadastro_despesa_page"))


@despesa_bp.route('/despesa_sucesso', methods=['GET'])
@login_required
def despesa_sucesso():
    if not _is_colaborador():
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    despesa_id = request.args.get('despesa_id', type=int)
    return render_template("despesa_sucesso.html", colaborador=current_user, despesa_id=despesa_id)


# =========================
# ✅ CADASTRO (POST) -> VAI PRA CONFIRMAR
# =========================
@despesa_bp.route('/cadastro_despesa', methods=['POST'])
@login_required
def cadastro_despesa():
    if not _is_colaborador():
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    data = request.form
    arquivo = request.files.get('imagem')

    if (
        not data.get('cidade') or
        not data.get('local') or
        not data.get('valor') or
        not data.get('complemento') or
        not data.get('projeto_id') or
        not arquivo
    ):
        flash("Todos os campos obrigatórios devem ser preenchidos e a imagem deve ser enviada.", "danger")
        return redirect(url_for('despesa_bp.cadastro_despesa_page'))

    if arquivo and not allowed_file(arquivo.filename):
        flash("Formato de imagem inválido. Envie PNG, JPG, JPEG ou GIF.", "danger")
        return redirect(url_for('despesa_bp.cadastro_despesa_page'))

    # ✅ limpa um preview anterior se existir
    prev = session.get("despesa_preview") or {}
    _cleanup_tmp(prev.get("tmp_name"))
    session.pop("despesa_preview", None)

    # ✅ salva arquivo temporário em disco (NÃO em session)
    _ensure_tmp_dir()

    original_name = secure_filename(arquivo.filename or "comprovante.png")
    ext = (original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "png")
    tmp_name = f"{uuid.uuid4().hex}.{ext}"
    tmp_path = _tmp_abs_path(tmp_name)
    arquivo.save(tmp_path)

    payload = {
        "cidade": (data.get("cidade") or "").strip(),
        "local": (data.get("local") or "").strip(),
        "cnpj_cpf_local": (data.get("cnpj_cpf_local") or "").strip(),
        "numero_documento": (data.get("numero_documento") or "").strip(),
        "descricao": (data.get("descricao") or "").strip(),
        "valor": (data.get("valor") or "").strip(),
        "observacao": (data.get("observacao") or "").strip(),
        "complemento": (data.get("complemento") or "").strip(),
        "projeto_id": (data.get("projeto_id") or None),

        # somente metadados pequenos + nome do tmp
        "tmp_name": tmp_name,
        "imagem_nome": original_name,
        "imagem_ext": ext,
    }

    session["despesa_preview"] = payload

    return redirect(url_for("despesa_bp.despesa_confirmar_page"))


@despesa_bp.route('/historico_despesas', methods=['GET'])
@login_required
def historico_despesas():
    if not _is_colaborador():
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    despesas = Despesa.query.filter_by(nome_colaborador=current_user.nome).order_by(Despesa.id.desc()).all()
    return render_template("historico_despesas.html", despesas=despesas, colaborador=current_user)


@despesa_bp.route('/ver_comprovantes')
@login_required
def ver_comprovantes():
    if not isinstance(current_user, Usuario):
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("auth_bp.login"))

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per", 30, type=int), 60)

    q = (
        db.session.query(Imagem)
        .options(defer(Imagem.imagem), joinedload(Imagem.despesa))
        .order_by(Imagem.data_upload.desc())
    )

    pag = q.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "ver_comprovantes.html",
        imagens=pag.items,
        pag=pag
    )

def _ler_bytes_comprovante(imagem: Imagem) -> bytes | None:
    """Lê os bytes do comprovante do disco (caminho novo) e, se não existir
    (registro ainda não migrado), cai para o BLOB antigo salvo no Postgres."""
    if imagem.caminho:
        caminho_absoluto = _comprovante_abs_path(imagem.caminho)
        if os.path.exists(caminho_absoluto):
            with open(caminho_absoluto, "rb") as f:
                return f.read()

    return imagem.imagem


@despesa_bp.route('/imagem/<int:id>')
@login_required
def imagem_blob(id):
    imagem = db.session.get(Imagem, id)
    raw = _ler_bytes_comprovante(imagem) if imagem else None
    if not raw:
        return "Imagem não encontrada", 404

    kind = filetype.guess(raw)
    mime_type = kind.mime if kind else "image/png"
    return Response(raw, mimetype=mime_type)


@despesa_bp.route('/download_imagem/<int:id>')
@login_required
def download_imagem(id):
    imagem = db.session.get(Imagem, id)
    raw = _ler_bytes_comprovante(imagem) if imagem else None
    if not raw:
        return "Imagem não encontrada", 404

    kind = filetype.guess(raw)
    mime_type = kind.mime if kind else "image/png"
    extensao = kind.extension if kind else "png"

    nome_arquivo = imagem.nome_arquivo or f"comprovante_{imagem.id}.{extensao}"
    if not nome_arquivo.lower().endswith(f".{extensao}"):
        nome_arquivo += f".{extensao}"

    return Response(
        raw,
        mimetype=mime_type,
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
    )


@despesa_bp.route('/exportar_pdf', methods=['GET'])
@login_required
def exportar_pdf():
    filtro_nome = request.args.get("colaborador")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    query = Despesa.query

    if data_inicio and data_fim:
        try:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
            fim = datetime.strptime(data_fim, "%Y-%m-%d")
            query = query.filter(Despesa.data_registro >= inicio, Despesa.data_registro <= fim)
        except ValueError:
            flash("Formato de data inválido. Use o formato YYYY-MM-DD.", "danger")
            return redirect(url_for("despesa_bp.menu_despesas"))

    if filtro_nome:
        query = query.filter_by(nome_colaborador=filtro_nome)

    despesas = query.order_by(Despesa.nome_colaborador, Despesa.data_registro).all()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    colaborador_atual = ""
    total_colab = 0
    total_geral = 0

    for d in despesas:
        if d.nome_colaborador != colaborador_atual:
            if colaborador_atual:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, f"Total do colaborador: R$ {total_colab:,.2f}", ln=True)
                pdf.ln(5)
                total_colab = 0

            colaborador_atual = d.nome_colaborador
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"Colaborador: {colaborador_atual}", ln=True)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(30, 8, "Data", border=1)
            pdf.cell(80, 8, "Descrição", border=1)
            pdf.cell(30, 8, "Valor", border=1)
            pdf.cell(50, 8, "Observação", border=1)
            pdf.ln()

        pdf.set_font("Arial", "", 10)
        pdf.cell(30, 8, d.data_registro.strftime("%d/%m/%Y"), border=1)
        pdf.cell(80, 8, d.descricao, border=1)
        pdf.cell(30, 8, f"R$ {d.valor:,.2f}", border=1)
        pdf.cell(50, 8, d.observacao or "", border=1)
        pdf.ln()

        total_colab += d.valor
        total_geral += d.valor

    if colaborador_atual:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"Total do colaborador: R$ {total_colab:,.2f}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total Geral: R$ {total_geral:,.2f}", ln=True, align="R")

    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    output = BytesIO(pdf_bytes)
    output.seek(0)

    nome = filtro_nome or "relatorio_completo"
    return send_file(output, download_name=f"{nome}_gastos.pdf", as_attachment=True)


@despesa_bp.route('/exportar_excel', methods=['GET'])
@login_required
def exportar_excel():
    filtro_nome = request.args.get("colaborador")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    query = Despesa.query

    if data_inicio and data_fim:
        try:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
            fim = datetime.strptime(data_fim, "%Y-%m-%d")
            query = query.filter(Despesa.data_registro >= inicio, Despesa.data_registro <= fim)
        except ValueError:
            flash("Formato de data inválido. Use o formato YYYY-MM-DD.", "danger")
            return redirect(url_for("despesa_bp.menu_despesas"))

    if filtro_nome:
        query = query.filter_by(nome_colaborador=filtro_nome)

    despesas = query.order_by(Despesa.nome_colaborador, Despesa.data_registro).all()

    data_out = []
    for d in despesas:
        data_out.append({
            "Colaborador": d.nome_colaborador,
            "Data": d.data_registro.strftime('%d/%m/%Y'),
            "Descrição": d.descricao,
            "Valor (R$)": f"{d.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "Local": d.local,
            "Cidade": d.cidade,
            "CNPJ/CPF": d.cnpj_cpf_local,
            "Empresa": d.nome_empresa,
            "Projeto": d.nome_projeto,
            "Cartão": d.num_cartao,
            "Complemento": d.complemento or "",
            "Observação": d.observacao or "",
        })

    df = pd.DataFrame(data_out)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório de Gastos')
    output.seek(0)

    nome = filtro_nome or "relatorio_completo"
    return send_file(
        output,
        download_name=f"{nome}_gastos.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ======= (demais rotas de exportação permanecem iguais) =======
@despesa_bp.route('/exportar_pdf_cartao', methods=['GET'])
@login_required
def exportar_pdf_cartao():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_cartao"))

    despesas = Despesa.query.filter(
        Despesa.data_registro >= inicio,
        Despesa.data_registro <= fim
    ).all()

    agrupado = {}
    for d in despesas:
        numero = d.num_cartao or "Não informado"
        agrupado.setdefault(numero, []).append(d)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    total_geral = 0

    for numero, lista in agrupado.items():
        total_cartao = sum(d.valor for d in lista)
        total_geral += total_cartao

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"Cartão: {numero}", ln=True)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(30, 8, "Data", border=1)
        pdf.cell(60, 8, "Descrição", border=1)
        pdf.cell(25, 8, "Valor", border=1)
        pdf.cell(40, 8, "Colaborador", border=1)
        pdf.cell(35, 8, "Observação", border=1)
        pdf.ln()

        pdf.set_font("Arial", "", 10)
        for d in lista:
            pdf.cell(30, 8, d.data_registro.strftime("%d/%m/%Y"), border=1)
            pdf.cell(60, 8, d.descricao[:30], border=1)
            pdf.cell(25, 8, f"R$ {d.valor:,.2f}", border=1)
            pdf.cell(40, 8, d.nome_colaborador[:18], border=1)
            pdf.cell(35, 8, (d.observacao or "")[:20], border=1)
            pdf.ln()

        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"Total do cartão: R$ {total_cartao:,.2f}", ln=True)
        pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total Geral: R$ {total_geral:,.2f}", ln=True, align="R")

    pdf_output = BytesIO()
    pdf_content = pdf.output(dest='S').encode('latin-1')
    pdf_output.write(pdf_content)
    pdf_output.seek(0)

    return send_file(pdf_output, download_name="gastos_por_cartao.pdf", as_attachment=True)


@despesa_bp.route('/exportar_excel_cartao', methods=['GET'])
@login_required
def exportar_excel_cartao():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_cartao"))

    despesas = Despesa.query.filter(
        Despesa.data_registro >= inicio,
        Despesa.data_registro <= fim
    ).all()

    dados = []
    for d in despesas:
        dados.append({
            "Cartão": d.num_cartao or "Não informado",
            "Data": d.data_registro.strftime("%d/%m/%Y"),
            "Descrição": d.descricao,
            "Valor": d.valor,
            "Observação": d.observacao or "",
            "Colaborador": d.nome_colaborador
        })

    df = pd.DataFrame(dados)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Gastos por Cartão")

    output.seek(0)
    return send_file(output, download_name="gastos_por_cartao.xlsx", as_attachment=True)


@despesa_bp.route('/exportar_pdf_projeto', methods=['GET'])
@login_required
def exportar_pdf_projeto():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_projeto"))

    despesas = Despesa.query.filter(
        Despesa.data_registro >= inicio,
        Despesa.data_registro <= fim
    ).all()

    agrupado = {}
    for d in despesas:
        nome = d.nome_projeto or "Não informado"
        agrupado.setdefault(nome, []).append(d)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    total_geral = 0
    for nome, lista in agrupado.items():
        total_proj = sum(d.valor for d in lista)
        total_geral += total_proj

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"Projeto: {nome}", ln=True)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(30, 8, "Data", border=1)
        pdf.cell(60, 8, "Descrição", border=1)
        pdf.cell(25, 8, "Valor", border=1)
        pdf.cell(40, 8, "Colaborador", border=1)
        pdf.cell(35, 8, "Observação", border=1)
        pdf.ln()

        pdf.set_font("Arial", "", 10)
        for d in lista:
            pdf.cell(30, 8, d.data_registro.strftime("%d/%m/%Y"), border=1)
            pdf.cell(60, 8, d.descricao[:30], border=1)
            pdf.cell(25, 8, f"R$ {d.valor:,.2f}", border=1)
            pdf.cell(40, 8, d.nome_colaborador[:18], border=1)
            pdf.cell(35, 8, (d.observacao or "")[:20], border=1)
            pdf.ln()

        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"Total do projeto: R$ {total_proj:,.2f}", ln=True)
        pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total Geral: R$ {total_geral:,.2f}", ln=True, align="R")

    output_str = pdf.output(dest='S').encode('latin1')
    output = BytesIO(output_str)

    return send_file(output, download_name="gastos_por_projeto.pdf", as_attachment=True)


@despesa_bp.route('/exportar_excel_projeto', methods=['GET'])
@login_required
def exportar_excel_projeto():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_projeto"))

    despesas = Despesa.query.filter(
        Despesa.data_registro >= inicio,
        Despesa.data_registro <= fim
    ).all()

    dados = []
    for d in despesas:
        dados.append({
            "Projeto": d.nome_projeto or "Não informado",
            "Data": d.data_registro.strftime("%d/%m/%Y"),
            "Descrição": d.descricao,
            "Valor": d.valor,
            "Colaborador": d.nome_colaborador,
            "Observação": d.observacao or ""
        })

    df = pd.DataFrame(dados)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="gastos_por_projeto.xlsx", as_attachment=True)


@despesa_bp.route('/exportar_pdf_empresa', methods=['GET'])
@login_required
def exportar_pdf_empresa():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_empresa"))

    despesas = Despesa.query.filter(
        Despesa.data_registro >= inicio,
        Despesa.data_registro <= fim
    ).all()

    agrupado = {}
    for d in despesas:
        nome = d.nome_empresa or "Não informado"
        agrupado.setdefault(nome, []).append(d)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    total_geral = 0
    for nome, lista in agrupado.items():
        total_emp = sum(d.valor for d in lista)
        total_geral += total_emp

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"Empresa: {nome}", ln=True)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(30, 8, "Data", border=1)
        pdf.cell(60, 8, "Descrição", border=1)
        pdf.cell(25, 8, "Valor", border=1)
        pdf.cell(40, 8, "Colaborador", border=1)
        pdf.cell(35, 8, "Observação", border=1)
        pdf.ln()

        pdf.set_font("Arial", "", 10)
        for d in lista:
            pdf.cell(30, 8, d.data_registro.strftime("%d/%m/%Y"), border=1)
            pdf.cell(60, 8, d.descricao[:30], border=1)
            pdf.cell(25, 8, f"R$ {d.valor:,.2f}", border=1)
            pdf.cell(40, 8, d.nome_colaborador[:18], border=1)
            pdf.cell(35, 8, (d.observacao or "")[:20], border=1)
            pdf.ln()

        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"Total da empresa: R$ {total_emp:,.2f}", ln=True)
        pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total Geral: R$ {total_geral:,.2f}", ln=True, align="R")

    output_str = pdf.output(dest='S').encode('latin1')
    output = BytesIO(output_str)

    return send_file(output, download_name="gastos_por_empresa.pdf", as_attachment=True)


@despesa_bp.route('/exportar_excel_empresa', methods=['GET'])
@login_required
def exportar_excel_empresa():
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_empresa"))

    despesas = Despesa.query.filter(
        Despesa.data_registro >= inicio,
        Despesa.data_registro <= fim
    ).all()

    dados = []
    for d in despesas:
        dados.append({
            "Empresa": d.nome_empresa or "Não informado",
            "Data": d.data_registro.strftime("%d/%m/%Y"),
            "Descrição": d.descricao,
            "Valor": d.valor,
            "Colaborador": d.nome_colaborador,
            "Observação": d.observacao or ""
        })

    df = pd.DataFrame(dados)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name="gastos_por_empresa.xlsx", as_attachment=True)


@despesa_bp.route('/controle_despesas', methods=['GET'])
@login_required
def controle_despesas():
    despesas = Despesa.query.order_by(Despesa.data_registro.desc()).all()
    return render_template('controle_despesas.html', despesas=despesas)


@despesa_bp.route('/despesa/excluir/<int:id>', methods=['GET'])
@login_required
def excluir_despesa(id):
    despesa = Despesa.query.get_or_404(id)

    # guarda os caminhos antes do cascade apagar as linhas de `imagens`
    caminhos_para_remover = [
        _comprovante_abs_path(img.caminho) for img in despesa.imagens if img.caminho
    ]

    db.session.delete(despesa)
    db.session.commit()

    for caminho in caminhos_para_remover:
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except OSError:
            pass

    flash("Despesa excluída com sucesso!", "success")
    return redirect(url_for('despesa_bp.controle_despesas'))
