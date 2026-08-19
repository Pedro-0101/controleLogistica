"""Reconhece placas em uma imagem e, opcionalmente, registra no banco.

Uso (a partir da pasta backend/):
    python -m scripts.recognize --imagem caminho/da/foto.jpg --ponto PORTARIA_ENTRADA
    python -m scripts.recognize --imagem foto.jpg --ponto PORTARIA_ENTRADA --sem-salvar
"""

import argparse

from app.anpr.recognizer import get_recognizer
from app.db import SessionLocal, init_db
from app.services.plate_service import registrar_evento
from app import models
from sqlalchemy import select


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconhece placa em uma imagem.")
    parser.add_argument("--imagem", required=True, help="Caminho da imagem")
    parser.add_argument("--ponto", default=None, help="Código do ponto (ex: PORTARIA_ENTRADA)")
    parser.add_argument(
        "--sem-salvar", action="store_true", help="Apenas reconhece, sem gravar no banco"
    )
    args = parser.parse_args()

    recognizer = get_recognizer()
    candidato = recognizer.reconhecer_melhor(args.imagem)

    if candidato is None:
        print("Nenhuma placa reconhecida.")
        return

    c = candidato
    print(
        f"  placa={c['placa'].valor} formato={c['placa'].formato} "
        f"confianca={c['confianca']:.4f} raw={c['raw']!r}"
    )

    if args.sem_salvar or not args.ponto:
        return

    init_db()
    with SessionLocal() as db:
        ponto = db.execute(
            select(models.Ponto).where(models.Ponto.codigo == args.ponto)
        ).scalar_one_or_none()
        if ponto is None:
            print(f"Ponto '{args.ponto}' não encontrado. Rode `python -m scripts.seed`.")
            return

        evento = registrar_evento(
            db,
            placa=c["placa"],
            confianca=c["confianca"],
            raw=c["raw"],
            planta_id=ponto.planta_id,
            ponto_id=ponto.id,
            imagem_path=args.imagem,
        )
        print(f"  -> evento #{evento.id} registrado (planta={ponto.planta_id}, ponto={ponto.id})")


if __name__ == "__main__":
    main()
