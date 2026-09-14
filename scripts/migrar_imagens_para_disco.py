"""
Migra os comprovantes de despesa que ainda estão em bytes no Postgres
(coluna `imagens.imagem`) para arquivos em app/static/uploads/comprovantes/.

Só ATUALIZA o banco (campo `caminho`) depois de escrever o arquivo em disco
E confirmar, lendo-o de volta, que o conteúdo bate byte a byte com o que
estava no Postgres. A coluna `imagem` (BLOB) NÃO é apagada por este script —
ela continua servindo de fallback em app/routes/despesa_routes.py até
alguém decidir explicitamente remover os bytes antigos (etapa separada).

Uso:
    python scripts/migrar_imagens_para_disco.py           # migra de verdade
    python scripts/migrar_imagens_para_disco.py --dry-run # só relata, não grava nada
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wsgi import app
from app import db
from app.models import Imagem

COMPROVANTES_DIR = os.path.join("app", "static", "uploads", "comprovantes")


def _abs_path(nome_arquivo: str) -> str:
    return os.path.join(COMPROVANTES_DIR, nome_arquivo)


def _sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


BATCH_SIZE = 20  # processa poucas imagens por vez pra não estourar RAM da VPS


def migrar(dry_run: bool = False):
    os.makedirs(COMPROVANTES_DIR, exist_ok=True)

    ja_no_disco = 0
    migradas = 0
    sem_blob = 0
    falhas = []

    with app.app_context():
        # só os ids agora (leve); os bytes de cada imagem só são carregados
        # lote por lote, e descartados da memória (expunge_all) entre lotes
        todos_ids = [
            row.id for row in db.session.query(Imagem.id).order_by(Imagem.id).all()
        ]
        total = len(todos_ids)

        for inicio in range(0, total, BATCH_SIZE):
            lote_ids = todos_ids[inicio:inicio + BATCH_SIZE]
            lote = Imagem.query.filter(Imagem.id.in_(lote_ids)).all()

            for img in lote:
                caminho_atual = _abs_path(img.caminho) if img.caminho else None

                if caminho_atual and os.path.exists(caminho_atual):
                    ja_no_disco += 1
                    continue

                if not img.imagem:
                    sem_blob += 1
                    falhas.append((img.id, "sem bytes no banco e sem arquivo em disco"))
                    continue

                # nome de arquivo único e estável, prefixado pelo id da imagem
                # para nunca colidir com outro registro
                base_nome = img.caminho or img.nome_arquivo or f"comprovante_{img.id}"
                novo_nome = f"{img.id}_{base_nome}"
                destino = _abs_path(novo_nome)

                hash_original = _sha256(img.imagem)
                tamanho = len(img.imagem)

                print(f"[{img.id}] gravando {tamanho} bytes em {destino}"
                      f"{' (dry-run)' if dry_run else ''}")

                if dry_run:
                    migradas += 1
                    continue

                try:
                    with open(destino, "wb") as f:
                        f.write(img.imagem)

                    with open(destino, "rb") as f:
                        hash_gravado = _sha256(f.read())

                    if hash_gravado != hash_original:
                        raise ValueError("hash do arquivo gravado não bate com o do banco")

                    img.caminho = novo_nome
                    db.session.commit()
                    migradas += 1
                except Exception as exc:
                    db.session.rollback()
                    if os.path.exists(destino):
                        os.remove(destino)
                    falhas.append((img.id, str(exc)))

            # libera da memória os bytes já processados deste lote antes do próximo
            db.session.expunge_all()

    print("\n===== Resumo =====")
    print(f"Total de registros em `imagens`: {total}")
    print(f"Já estavam no disco (nada a fazer): {ja_no_disco}")
    print(f"Migradas nesta execução: {migradas}")
    print(f"Sem BLOB e sem arquivo (não migráveis): {sem_blob}")
    print(f"Falhas: {len(falhas)}")
    for id_, motivo in falhas:
        print(f"  - imagem id={id_}: {motivo}")

    if not dry_run and not falhas:
        print("\nTodas as imagens confirmadas em disco (hash verificado). "
              "A coluna `imagens.imagem` no banco NÃO foi tocada.")


if __name__ == "__main__":
    migrar(dry_run="--dry-run" in sys.argv)
