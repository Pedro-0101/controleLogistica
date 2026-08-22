"""Testa o reconhecimento de placas (ANPR) em uma imagem do disco.

Uso (a partir da pasta backend/):
    python -m scripts.recognize --imagem caminho/da/foto.jpg --sem-salvar
    python -m scripts.recognize --imagem foto.jpg --unidade SAO_JOAO --operacao entrada
"""

import argparse
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import cv2

from app import models
from app.config import settings
from app.db import SessionLocal
from app.services.ponto_service import obter_planta_por_codigo, obter_ponto
from app.services.visita_service import registrar_entrada, registrar_saida


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconhece placa em uma imagem.")
    parser.add_argument("--imagem", required=True, help="Caminho da imagem")
    parser.add_argument(
        "--sem-salvar",
        action="store_true",
        help="Apenas reconhece e imprime, sem gravar no banco",
    )
    parser.add_argument(
        "--unidade", default="SAO_JOAO", help="Código da planta (default: SAO_JOAO)"
    )
    parser.add_argument(
        "--operacao",
        choices=("entrada", "saida"),
        default="entrada",
        help="Operação ao salvar (default: entrada)",
    )
    args = parser.parse_args()

    caminho = Path(args.imagem)
    if not caminho.is_file():
        print(f"Erro: imagem não encontrada: {caminho}", file=sys.stderr)
        raise SystemExit(1)
    imagem = cv2.imread(str(caminho))
    if imagem is None:
        print(f"Erro: formato inválido: {caminho}", file=sys.stderr)
        raise SystemExit(1)

    # Import sob demanda: carrega o PaddleOCR só agora.
    from app.anpr.recognizer import get_recognizer

    candidatos = get_recognizer().reconhecer(imagem)
    if not candidatos:
        print("Nenhuma placa reconhecida.")
        return

    melhor = max(candidatos, key=lambda c: c.confianca)
    for c in sorted(candidatos, key=lambda c: -c.confianca):
        marca = "* " if c is melhor else "  "
        print(
            f"{marca}placa={c.placa.valor} formato={c.placa.formato} "
            f"confianca={c.confianca:.4f} raw={c.raw!r}"
        )

    if args.sem_salvar:
        return

    with SessionLocal() as db:
        planta = obter_planta_por_codigo(db, args.unidade)
        if planta is None:
            print(f"Unidade '{args.unidade}' não encontrada.", file=sys.stderr)
            raise SystemExit(1)
        tipo = (
            "portaria_entrada" if args.operacao == "entrada" else "portaria_saida"
        )
        ponto = obter_ponto(db, planta.id, tipo)
        if ponto is None:
            print(
                f"Ponto '{tipo}' não encontrado na unidade '{args.unidade}'.",
                file=sys.stderr,
            )
            raise SystemExit(1)

        settings.imagens_dir.mkdir(parents=True, exist_ok=True)
        nome = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.jpg"
        foto_path = str(settings.imagens_dir / nome)
        shutil.copyfile(caminho, foto_path)

        from app.services.plate_service import PlacaResolvida

        resolvida = PlacaResolvida(
            valor=melhor.placa.valor,
            formato=melhor.placa.formato,
            confianca=melhor.confianca,
            raw=melhor.raw,
        )
        registrar = (
            registrar_entrada if args.operacao == "entrada" else registrar_saida
        )
        mov = registrar(
            db,
            resolvida=resolvida,
            planta_id=planta.id,
            ponto_id=ponto.id,
            foto_path=foto_path,
        )
        assert isinstance(mov, models.PortariaMovimentacao)
        print(
            f"Salvo: id={mov.id} visita={mov.visita_id} operacao={mov.operacao}"
        )


if __name__ == "__main__":
    main()
