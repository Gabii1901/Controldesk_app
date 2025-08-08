import pandas as pd
import pdfkit
from io import BytesIO
from flask import send_file
from app.models import Despesa

def gerar_relatorio_excel():
    despesas = Despesa.query.all()
    
    # Transformar os dados em uma estrutura de dicionário para criar o DataFrame
    data = [{
        'Colaborador': d.nome_colaborador,
        'Cidade': d.cidade,
        'Local': d.local,
        'CNPJ/CPF': d.cnpj_cpf_local,
        'Nº Documento': d.numero_documento,
        'Descrição': d.descricao,
        'Valor': d.valor,
        'Observação': d.observacao,
        'Complemento': d.complemento
    } for d in despesas]

    df = pd.DataFrame(data)
    
    # Criando um arquivo Excel em memória
    output = BytesIO()
    df.to_excel(output, index=False, engine='xlsxwriter')
    output.seek(0)

    return send_file(output, download_name='relatorio.xlsx', as_attachment=True)

def gerar_relatorio_pdf():
    despesas = Despesa.query.all()
    
    # Criar um HTML para gerar o PDF
    html = """<html><head><style>
                table { width: 100%; border-collapse: collapse; }
                th, td { border: 1px solid black; padding: 8px; text-align: left; }
              </style></head><body>
              <h2>Relatório de Despesas</h2>
              <table><tr><th>Colaborador</th><th>Cidade</th><th>Local</th><th>CNPJ/CPF</th>
              <th>Nº Documento</th><th>Descrição</th><th>Valor</th></tr>"""
    
    for d in despesas:
        html += f"<tr><td>{d.nome_colaborador}</td><td>{d.cidade}</td><td>{d.local}</td>" \
                f"<td>{d.cnpj_cpf_local}</td><td>{d.numero_documento}</td><td>{d.descricao}</td>" \
                f"<td>R$ {d.valor:.2f}</td></tr>"
    
    html += "</table></body></html>"

    # Gerando PDF a partir do HTML
    output = BytesIO()
    pdfkit.from_string(html, output)
    output.seek(0)

    return send_file(output, download_name='relatorio.pdf', as_attachment=True)
