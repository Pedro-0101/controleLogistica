"""Cria dados iniciais (planta e pontos de coleta) no banco.

Uso (a partir da pasta backend/):
    python -m scripts.seed
"""

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app import models

PONTOS_PADRAO = [
    ("PORTARIA_ENTRADA", "portaria_entrada", "Portaria - Entrada"),
    ("PORTARIA_SAIDA", "portaria_saida", "Portaria - Saída"),
    ("BALANCA", "balanca", "Balança rodoviária"),
]


def seed() -> None:
    init_db()
    with SessionLocal() as db:
        planta = db.execute(
            select(models.Planta).where(models.Planta.codigo == "PLT001")
        ).scalar_one_or_none()
        if planta is None:
            planta = models.Planta(codigo="PLT001", nome="Planta Principal")
            db.add(planta)
            db.flush()

        for codigo, tipo, descricao in PONTOS_PADRAO:
            ponto = db.execute(
                select(models.Ponto).where(models.Ponto.codigo == codigo)
            ).scalar_one_or_none()
            if ponto is None:
                db.add(
                    models.Ponto(
                        planta_id=planta.id,
                        codigo=codigo,
                        tipo=tipo,
                        descricao=descricao,
                    )
                )

        db.commit()
        print(f"Planta '{planta.codigo}' id={planta.id} pronta.")
        print("Pontos:", ", ".join(p[0] for p in PONTOS_PADRAO))


if __name__ == "__main__":
    seed()
