"""
Reduz o tamanho em disco dos comprovantes de despesas com mais de 3 meses,
redimensionando a foto (largura/altura máx. 1600px) e recomprimindo como
JPEG qualidade 75. Comprovantes recentes (<= 3 meses) não são tocados.

Isso é DIFERENTE de zip/gzip: fotos JPEG já vêm comprimidas, então um
compactador sem perda (zip, gzip, 7z) economiza menos de 1% de espaço nelas
(testado com dados reais). Redimensionar/recomprimir com perda é o único jeito
de realmente reduzir o espaço ocupado, e o comprovante continua perfeitamente
legível na tela.

A operação é DEFINITIVA por escolha do usuário: o arquivo original em alta
resolução é substituído pelo comprimido (não há um botão de "ver original"
depois). Antes de sobrescrever, o script só aceita o resultado se ele for
realmente menor que o original; senão mantém o arquivo como está.

Uso:
    python scripts/compactar_comprovantes_antigos.py            # roda de verdade
    python scripts/compactar_comprovantes_antigos.py --dry-run  # só relata
    python scripts/compactar_comprovantes_antigos.py --meses 3  # muda o corte (padrão 3)
"""
import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dateutil.relativedelta import relativedelta
from PIL import Image
from sqlalchemy.orm import defer

from wsgi import app
from app import db
from app.models import Imagem, Despesa

COMPROVANTES_DIR = os.path.join("app", "static", "uploads", "comprovantes")
LADO_MAXIMO = 1600
QUALIDADE_JPEG = 75


def _abs_path(nome_arquivo: str) -> str:
    return os.path.join(COMPROVANTES_DIR, nome_arquivo)


def _recomprimir(caminho_absoluto: str) -> bytes | None:
    """Retorna os bytes da versão redimensionada/recomprimida, ou None se
    não for uma imagem legível pelo Pillow (ex.: arquivo corrompido)."""
    try:
        with Image.open(caminho_absoluto) as im:
            im = im.convert("RGB") if im.mode not in ("RGB", "L") else im

            largura, altura = im.size
            maior_lado = max(largura, altura)
            if maior_lado > LADO_MAXIMO:
                fator = LADO_MAXIMO / maior_lado
                im = im.resize(
                    (max(1, int(largura * fator)), max(1, int(altura * fator))),
                    Image.LANCZOS,
                )

            buffer = io.BytesIO()
            im.save(buffer, format="JPEG", quality=QUALIDADE_JPEG, optimize=True)
            return buffer.getvalue()
    except Exception:
        return None


def compactar(dry_run: bool = False, meses: int = 3):
    corte = relativedelta(months=meses)

    total_candidatas = 0
    compactadas = 0
    ja_pequenas = 0
    ilegveis = 0
    sem_arquivo = 0
    espaco_economizado = 0

    with app.app_context():
        from datetime import datetime
        data_corte = datetime.now() - corte

        candidatas = (
            db.session.query(Imagem)
            .options(defer(Imagem.imagem))  # nunca carregar o BLOB antigo pra memória
            .join(Despesa, Imagem.despesa_id == Despesa.id)
            .filter(Despesa.data_registro < data_corte)
            .filter(Imagem.compactada.is_(False))
            .all()
        )
        total_candidatas = len(candidatas)

        for img in candidatas:
            if not img.caminho:
                sem_arquivo += 1
                continue

            caminho_absoluto = _abs_path(img.caminho)
            if not os.path.exists(caminho_absoluto):
                sem_arquivo += 1
                continue

            tamanho_original = os.path.getsize(caminho_absoluto)
            novo_conteudo = _recomprimir(caminho_absoluto)

            if novo_conteudo is None:
                ilegveis += 1
                continue

            if len(novo_conteudo) >= tamanho_original:
                # já era pequena/eficiente: não compensa trocar
                ja_pequenas += 1
                img.compactada = True
                if not dry_run:
                    db.session.commit()
                continue

            economia = tamanho_original - len(novo_conteudo)
            print(
                f"[{img.id}] {os.path.basename(caminho_absoluto)}: "
                f"{tamanho_original} -> {len(novo_conteudo)} bytes "
                f"(-{100 * economia / tamanho_original:.0f}%)"
                f"{' (dry-run)' if dry_run else ''}"
            )

            if dry_run:
                compactadas += 1
                espaco_economizado += economia
                continue

            # Normaliza tudo pra .jpg (é o formato de saída da recompressão)
            novo_nome = os.path.splitext(img.caminho)[0] + ".jpg"
            novo_caminho_absoluto = _abs_path(novo_nome)

            try:
                with open(novo_caminho_absoluto, "wb") as f:
                    f.write(novo_conteudo)

                if novo_caminho_absoluto != caminho_absoluto and os.path.exists(caminho_absoluto):
                    os.remove(caminho_absoluto)

                img.caminho = novo_nome
                if img.nome_arquivo:
                    img.nome_arquivo = os.path.splitext(img.nome_arquivo)[0] + ".jpg"
                img.compactada = True
                db.session.commit()

                compactadas += 1
                espaco_economizado += economia
            except Exception as exc:
                db.session.rollback()
                print(f"  ERRO ao compactar imagem {img.id}: {exc}")

    print("\n===== Resumo =====")
    print(f"Comprovantes com mais de {meses} mes(es) ainda não compactados: {total_candidatas}")
    print(f"Compactadas nesta execução: {compactadas}")
    print(f"Já eram pequenas (mantidas como estavam): {ja_pequenas}")
    print(f"Ilegíveis pelo Pillow (não tocadas): {ilegveis}")
    print(f"Sem arquivo em disco: {sem_arquivo}")
    print(f"Espaço economizado: {espaco_economizado / (1024 * 1024):.1f} MB"
          f"{' (estimado, dry-run)' if dry_run else ''}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--meses", type=int, default=3)
    args = parser.parse_args()

    compactar(dry_run=args.dry_run, meses=args.meses)
