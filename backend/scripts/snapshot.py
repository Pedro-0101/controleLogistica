"""Captura um snapshot da câmera e reconhece a placa (ANPR).

Uso (a partir da pasta backend/):
    python -m scripts.snapshot --url http://192.168.11.241/ISAPI/Streaming/channels/101/picture --sem-salvar
    python -m scripts.snapshot --ponto PORTARIA_ENTRADA
    python -m scripts.snapshot --ponto BALANCA --destino teste.jpg
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app import models
from app.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Snapshot da câmera + reconhecimento de placa"
    )
    fonte = parser.add_mutually_exclusive_group(required=True)
    fonte.add_argument("--url", help="URL completa de snapshot da câmera")
    fonte.add_argument("--ponto", help="Código do ponto cadastrado (usa Ponto.camera_url)")
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
    parser.add_argument(
        "--destino", help="Caminho para guardar uma cópia do JPEG capturado"
    )
    args = parser.parse_args()

    from app.db import SessionLocal
    from app.services.camera import capturar_snapshot
    from app.services.erros import (
        CameraNaoConfiguradaError,
        CameraSnapshotError,
    )
    from app.services.imagem import decodificar
    from app.services.ponto_service import obter_planta_por_codigo, obter_ponto

    camera_url = args.url
    db = SessionLocal()
    try:
        if args.ponto:
            ponto = db.execute(
                select(models.Ponto).where(models.Ponto.codigo == args.ponto)
            ).scalar_one_or_none()
            if ponto is None:
                print(f"Ponto '{args.ponto}' não encontrado.", file=sys.stderr)
                raise SystemExit(1)
            if not ponto.camera_url:
                print(
                    f"Ponto '{args.ponto}' sem camera_url cadastrada.", file=sys.stderr
                )
                raise SystemExit(1)
            camera_url = ponto.camera_url

        print(f"Capturando: {camera_url}")
        try:
            conteudo = asyncio.run(capturar_snapshot(camera_url))
        except CameraSnapshotError as exc:
            print(f"Erro na captura: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        imagem = decodificar(conteudo)
        print(f"Snapshot OK ({len(conteudo)} bytes).")
    finally:
        db.close()

    if args.destino:
        destino = Path(args.destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
        print(f"Cópia salva em: {destino}")

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

    from app.services.plate_service import PlacaResolvida
    from app.services.visita_service import registrar_entrada, registrar_saida

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
        foto_path = settings.imagens_dir / nome
        foto_path.write_bytes(conteudo)

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
            foto_path=str(foto_path),
        )
        assert isinstance(mov, models.PortariaMovimentacao)
        print(
            f"Salvo: id={mov.id} visita={mov.visita_id} operacao={mov.operacao}"
        )


if __name__ == "__main__":
    main()
