"""Cria dados iniciais (planta, pontos e usuário admin) no banco.

Requer o banco migrado (rode `alembic upgrade head` antes).

Uso (a partir da pasta backend/):
    python -m scripts.seed
"""

from sqlalchemy import select

from app import models
from app.auth.security import hash_senha
from app.config import settings
from app.db import SessionLocal

PONTOS_PADRAO = [
    ("PORTARIA_ENTRADA", "Entrada Portaria", "portaria_entrada", "Portaria - Entrada"),
    ("PORTARIA_SAIDA", "Saída Portaria", "portaria_saida", "Portaria - Saída"),
    ("BALANCA", "Balança", "balanca", "Balança rodoviária"),
]


def seed() -> None:
    with SessionLocal() as db:
        planta = db.execute(
            select(models.Planta).where(models.Planta.codigo == "SAO_JOAO")
        ).scalar_one_or_none()
        if planta is None:
            planta = models.Planta(codigo="SAO_JOAO", nome="São João")
            db.add(planta)
            db.flush()

        for codigo, nome, tipo, descricao in PONTOS_PADRAO:
            ponto = db.execute(
                select(models.Ponto).where(models.Ponto.codigo == codigo)
            ).scalar_one_or_none()
            if ponto is None:
                db.add(
                    models.Ponto(
                        planta_id=planta.id,
                        codigo=codigo,
                        nome=nome,
                        tipo=tipo,
                        descricao=descricao,
                    )
                )

        admin = db.execute(
            select(models.Usuario).where(models.Usuario.email == settings.admin_email)
        ).scalar_one_or_none()
        if admin is None:
            db.add(
                models.Usuario(
                    nome=settings.admin_nome,
                    email=settings.admin_email,
                    senha_hash=hash_senha(settings.admin_password),
                    role="admin",
                    ativo=True,
                )
            )

        db.commit()
        print(f"Planta '{planta.codigo}' id={planta.id} pronta.")
        print("Pontos:", ", ".join(p[0] for p in PONTOS_PADRAO))
        print(f"Admin '{settings.admin_email}' pronto.")


if __name__ == "__main__":
    seed()
