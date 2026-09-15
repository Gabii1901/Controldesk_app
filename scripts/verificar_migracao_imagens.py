"""
Confere, em lotes pequenos (pra não estourar memória em VPS com pouca RAM),
se cada arquivo em app/static/uploads/comprovantes/ bate byte a byte (hash
SHA-256) com o BLOB que ainda está no Postgres. Não altera nada — só lê.

Uso:
    python scripts/verificar_migracao_imagens.py
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wsgi import app
from app import db
from app.models import Imagem

COMPROVANTES_DIR = os.path.join("app", "static", "uploads", "comprovantes")
BATCH_SIZE = 20


def _sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def verificar():
    with app.app_context():
        todos_ids = [row.id for row in db.session.query(Imagem.id).order_by(Imagem.id).all()]
        total = len(todos_ids)

        ok = 0
        sem_arquivo = []
        divergentes = []

        for inicio in range(0, total, BATCH_SIZE):
            lote_ids = todos_ids[inicio:inicio + BATCH_SIZE]
            lote = Imagem.query.filter(Imagem.id.in_(lote_ids)).all()

            for img in lote:
                caminho = os.path.join(COMPROVANTES_DIR, img.caminho or "")
                if not img.caminho or not os.path.exists(caminho):
                    sem_arquivo.append(img.id)
                    continue

                with open(caminho, "rb") as f:
                    disco = f.read()

                if img.imagem is None:
                    ok += 1
                elif _sha256(disco) == _sha256(img.imagem):
                    ok += 1
                else:
                    divergentes.append(img.id)

            db.session.expunge_all()
            print(f"...verificadas {min(inicio + BATCH_SIZE, total)}/{total}")

        print("\n===== Resultado =====")
        print(f"Total: {total}")
        print(f"OK (disco == banco, ou banco já sem BLOB): {ok}")
        print(f"Sem arquivo em disco: {sem_arquivo}")
        print(f"Divergentes (NÃO bateu hash): {divergentes}")


if __name__ == "__main__":
    verificar()
