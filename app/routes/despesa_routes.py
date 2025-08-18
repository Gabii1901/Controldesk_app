from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, Response, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import filetype
from fpdf import FPDF
import pandas as pd
from io import BytesIO
from app import db
from app.models import Despesa, Imagem, Colaborador, Usuario, Projeto
from flask_login import login_required, current_user
import pytz


despesa_bp = Blueprint('despesa_bp', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 🔹 Menu principal de despesas
@despesa_bp.route('/menu_despesas', methods=['GET'])
@login_required
def menu_despesas():
    if not isinstance(current_user, Colaborador):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))
    return render_template("menu_despesas.html", colaborador=current_user)

# 🔹 Página de cadastro de despesas
@despesa_bp.route('/cadastro_despesa', methods=['GET'])
@login_required
def cadastro_despesa_page():
    if not isinstance(current_user, Colaborador):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))
    return render_template("cadastro_despesa.html", colaborador=current_user)

# 🔹 Processamento do cadastro
@despesa_bp.route('/cadastro_despesa', methods=['POST'])
@login_required
def cadastro_despesa():
    if not isinstance(current_user, Colaborador):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    data = request.form
    arquivo = request.files.get('imagem')

    # ✅ Validação de campos obrigatórios
    if (
        not data.get('cidade') or
        not data.get('local') or
        not data.get('valor') or
        not data.get('complemento') or
        not arquivo
    ):
        flash("Todos os campos obrigatórios devem ser preenchidos e a imagem deve ser enviada.", "danger")
        return redirect(url_for('despesa_bp.cadastro_despesa_page'))

    projeto_id = data.get('projeto_id')
    projeto = Projeto.query.get(projeto_id) if projeto_id else None
    nome_projeto = projeto.nome if projeto else None

    # 📌 Data no horário de Brasília
    fuso_brasilia = pytz.timezone('America/Sao_Paulo')
    data_registro = datetime.now(fuso_brasilia)

    despesa = Despesa(
        nome_colaborador=current_user.nome,
        cidade=data.get('cidade'),
        local=data.get('local'),
        cnpj_cpf_local=data.get('cnpj_cpf_local'),
        numero_documento=data.get('numero_documento'),
        descricao=data.get('descricao'),
        valor=float(data.get('valor')),
        observacao=data.get('observacao', ''),
        complemento=data.get('complemento'),
        nome_empresa=current_user.empresa.razao_social if current_user.empresa else None,
        num_cartao=current_user.numero_cartao or '',
        nome_projeto=nome_projeto,
        data_registro=data_registro
    )
    db.session.add(despesa)
    db.session.commit()

    if allowed_file(arquivo.filename):
        nome_colab = current_user.nome.lower().replace(" ", "_")
        extensao = arquivo.filename.rsplit(".", 1)[-1].lower()

        timestamp = datetime.now(fuso_brasilia).strftime("%Y%m%d_%H%M%S")
        nome_arquivo = secure_filename(f"{nome_colab}_despesa{despesa.id}_{timestamp}.{extensao}")

        imagem = Imagem(
            despesa_id=despesa.id,
            imagem=arquivo.read(),
            nome_arquivo=nome_arquivo,
            caminho=nome_arquivo,
            data_upload=datetime.now(fuso_brasilia)
        )
        db.session.add(imagem)
        db.session.commit()

    flash("Despesa cadastrada com sucesso!", "success")
    return redirect(url_for('despesa_bp.menu_despesas'))




# 🔹 Histórico de despesas
@despesa_bp.route('/historico_despesas', methods=['GET'])
@login_required
def historico_despesas():
    if not isinstance(current_user, Colaborador):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("auth_bp.login"))

    despesas = Despesa.query.filter_by(nome_colaborador=current_user.nome).order_by(Despesa.id.desc()).all()
    return render_template("historico_despesas.html", despesas=despesas, colaborador=current_user)

# 🔹 Visualizar comprovantes
@despesa_bp.route('/ver_comprovantes')
@login_required
def ver_comprovantes():
    if not isinstance(current_user, Usuario):
        flash("Acesso restrito a administradores.", "danger")
        return redirect(url_for("auth_bp.login"))

    imagens = db.session.query(Imagem).join(Despesa).order_by(Imagem.data_upload.desc()).all()
    return render_template('ver_comprovantes.html', imagens=imagens)

# 🔹 Ver imagem blob
@despesa_bp.route('/imagem/<int:id>')
@login_required
def imagem_blob(id):
    imagem = db.session.get(Imagem, id)
    if not imagem or not imagem.imagem:
        return "Imagem não encontrada", 404

    kind = filetype.guess(imagem.imagem)
    mime_type = kind.mime if kind else "image/png"
    return Response(imagem.imagem, mimetype=mime_type)

# 🔹 Download da imagem
@despesa_bp.route('/download_imagem/<int:id>')
@login_required
def download_imagem(id):
    imagem = db.session.get(Imagem, id)
    if not imagem or not imagem.imagem:
        return "Imagem não encontrada", 404

    kind = filetype.guess(imagem.imagem)
    mime_type = kind.mime if kind else "image/png"
    extensao = kind.extension if kind else "png"

    nome_arquivo = imagem.nome_arquivo or f"comprovante_{imagem.id}.{extensao}"
    if not nome_arquivo.lower().endswith(f".{extensao}"):
        nome_arquivo += f".{extensao}"

    return Response(
        imagem.imagem,
        mimetype=mime_type,
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
    )

# 🔹 Exportação em PDF
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
                # Total anterior
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

    # Último colaborador
    if colaborador_atual:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"Total do colaborador: R$ {total_colab:,.2f}", ln=True)

    # Total geral
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total Geral: R$ {total_geral:,.2f}", ln=True, align="R")

    # ✅ Correção aqui:
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    output = BytesIO(pdf_bytes)
    output.seek(0)

    nome = filtro_nome or "relatorio_completo"
    return send_file(output, download_name=f"{nome}_gastos.pdf", as_attachment=True)


# 🔹 Exportação em Excel
@despesa_bp.route('/exportar_excel', methods=['GET'])
@login_required
def exportar_excel():
    filtro_nome = request.args.get("colaborador")
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    query = Despesa.query

    # ✅ Conversão das datas
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

    # Montar DataFrame
    data = []
    for d in despesas:
        data.append({
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

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório de Gastos')
    output.seek(0)

    nome = filtro_nome or "relatorio_completo"
    return send_file(output, download_name=f"{nome}_gastos.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

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
        if numero not in agrupado:
            agrupado[numero] = []
        agrupado[numero].append(d)

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

    # Exportação segura
    pdf_output = BytesIO()
    pdf_content = pdf.output(dest='S').encode('latin-1')
    pdf_output.write(pdf_content)
    pdf_output.seek(0)

    return send_file(pdf_output, download_name="gastos_por_cartao.pdf", as_attachment=True)



@despesa_bp.route('/exportar_excel_cartao', methods=['GET'])
@login_required
def exportar_excel_cartao():
    import pandas as pd

    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_cartao"))

    despesas = Despesa.query.filter(Despesa.data_registro >= inicio, Despesa.data_registro <= fim).all()

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
    from fpdf import FPDF

    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_projeto"))

    despesas = Despesa.query.filter(Despesa.data_registro >= inicio, Despesa.data_registro <= fim).all()

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
    import pandas as pd

    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_projeto"))

    despesas = Despesa.query.filter(Despesa.data_registro >= inicio, Despesa.data_registro <= fim).all()

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
    from fpdf import FPDF

    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_empresa"))

    despesas = Despesa.query.filter(Despesa.data_registro >= inicio, Despesa.data_registro <= fim).all()

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
    import pandas as pd

    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    try:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
    except Exception:
        flash("Datas inválidas", "danger")
        return redirect(url_for("relatorio_bp.relatorio_gastos_empresa"))

    despesas = Despesa.query.filter(Despesa.data_registro >= inicio, Despesa.data_registro <= fim).all()

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
    db.session.delete(despesa)
    db.session.commit()
    flash("Despesa excluída com sucesso!", "success")
    return redirect(url_for('despesa_bp.controle_despesas'))

