"""Lê o peso da balança (serial ou simulador) até estabilizar e registra.

Uso (a partir da pasta backend/):
    python -m scripts.pesar --simular                       # teste sem hardware
    python -m scripts.pesar --simular --ponto BALANCA       # registra no banco
    python -m scripts.pesar --porta COM3 --ponto BALANCA    # balança real
"""

import argparse
import time

from sqlalchemy import select

from app import models
from app.balanca.estabilizador import EstabilizadorPeso
from app.balanca.leitor import BalancaSerial
from app.balanca.parser import extrair_peso
from app.balanca.simulador import SimuladorBalanca
from app.db import SessionLocal, init_db
from app.services.peso_service import registrar_pesagem


def main() -> None:
    parser = argparse.ArgumentParser(description="Lê peso da balança até estabilizar.")
    parser.add_argument("--porta", default=None, help="Porta serial (ex: COM3)")
    parser.add_argument("--simular", action="store_true", help="Usa simulador (sem hardware)")
    parser.add_argument("--peso-alvo", type=float, default=15480.0, help="Peso alvo do simulador (kg)")
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument("--amostras", type=int, default=25, help="Leituras por janela de estabilização")
    parser.add_argument("--tolerancia", type=float, default=5.0, help="MAD máximo para considerar estável (kg)")
    parser.add_argument("--peso-minimo", type=float, default=100.0, help="Ignora pesos abaixo disso (balança vazia)")
    parser.add_argument("--regex", default=None, help="Regex com grupo p/ o número do peso (protocolo específico)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Tempo máximo esperando estabilizar (s)")
    parser.add_argument("--ponto", default=None, help="Código do ponto (ex: BALANCA)")
    parser.add_argument("--placa", default=None, help="Placa do veículo na balança (para parear)")
    parser.add_argument("--sem-salvar", action="store_true", help="Não grava no banco")
    args = parser.parse_args()

    serial = None
    if args.simular:
        simulador = SimuladorBalanca(peso_alvo=args.peso_alvo)
        ler = simulador.proxima_linha
        origem = f"simulador (alvo={args.peso_alvo} kg)"
    elif args.porta:
        serial = BalancaSerial(args.porta, baudrate=args.baudrate)
        ler = serial.ler_linha
        origem = f"serial {args.porta}"
    else:
        parser.error("informe --porta ou --simular")

    estabilizador = EstabilizadorPeso(
        tamanho_janela=args.amostras,
        tolerancia=args.tolerancia,
        peso_minimo=args.peso_minimo,
    )
    print(
        f"Monitorando {origem} (amostras={args.amostras}, "
        f"tolerancia={args.tolerancia} kg, peso_minimo={args.peso_minimo} kg)"
    )

    try:
        estavel = None
        inicio = time.time()
        while time.time() - inicio < args.timeout:
            linha = ler()
            if linha is None:
                continue
            peso = extrair_peso(linha, padrao=args.regex)
            if peso is None:
                continue
            estavel = estabilizador.adicionar(peso)
            if estavel is not None:
                break

        if estavel is None:
            print("Não estabilizou dentro do tempo limite.")
            return

        print(
            f"Peso estável: {estavel.peso} kg "
            f"(desvio={estavel.desvio} kg, amostras={estavel.amostras})"
        )

        if args.sem_salvar or not args.ponto:
            return

        if not args.placa:
            print("Informe --placa para parear a pesagem a um veículo.")
            return

        init_db()
        with SessionLocal() as db:
            ponto = db.execute(
                select(models.Ponto).where(models.Ponto.codigo == args.ponto)
            ).scalar_one_or_none()
            if ponto is None:
                print(f"Ponto '{args.ponto}' não encontrado. Rode `python -m scripts.seed`.")
                return
            pesagem = registrar_pesagem(
                db,
                placa=args.placa,
                peso=estavel.peso,
                desvio=estavel.desvio,
                amostras=estavel.amostras,
                planta_id=ponto.planta_id,
                ponto_id=ponto.id,
            )
            print(f"  -> pesagem #{pesagem.id} registrada (planta={ponto.planta_id}, ponto={ponto.id})")
    finally:
        if serial is not None:
            serial.fechar()


if __name__ == "__main__":
    main()
