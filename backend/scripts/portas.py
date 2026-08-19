"""Detecta portas USB/seriais e lê o peso da balança.

Serve também para a instalação: lista todas as portas do computador, permite
selecionar (ou detectar automaticamente) em qual delas a balança está conectada
e exibe ao vivo as linhas brutas e o peso extraído.

Uso (a partir da pasta backend/):
    python -m scripts.portas                  # lista e seleciona interativamente
    python -m scripts.portas --listar         # apenas lista as portas
    python -m scripts.portas --porta COM3     # monitora a porta informada
    python -m scripts.portas --detectar       # varre as portas procurando a balança
"""

import argparse

from serial.tools.list_ports_common import ListPortInfo

from app.balanca.estabilizador import EstabilizadorPeso
from app.balanca.leitor import BalancaSerial
from app.balanca.parser import extrair_peso
from app.balanca.portas import detectar, limpar, listar_portas


def descrever_porta(info: ListPortInfo, indice: int | None = None) -> str:
    """Formata uma porta para exibição (índice, dispositivo e descrição)."""
    prefixo = f"{indice:>3}. " if indice is not None else ""
    detalhes = "  ".join(
        campo for campo in (info.description, info.manufacturer) if campo
    )
    return f"{prefixo}{info.device:<12} {detalhes or '(sem descrição)'}"


def imprimir_portas(portas: list[ListPortInfo]) -> None:
    """Imprime as portas com um índice para seleção."""
    if not portas:
        print("Nenhuma porta serial/USB encontrada.")
        return
    for indice, porta in enumerate(portas):
        print(descrever_porta(porta, indice))


def selecionar_porta(portas: list[ListPortInfo]) -> ListPortInfo | None:
    """Pede ao usuário para escolher uma porta pelo índice exibido.

    Returns:
        A porta escolhida, ou None se a escolha for cancelada/inválida.
    """
    if not portas:
        return None
    try:
        escolha = input("Escolha o número da porta (Enter para cancelar): ").strip()
    except EOFError:
        return None
    if not escolha:
        return None
    try:
        indice = int(escolha)
    except ValueError:
        print("Número inválido.")
        return None
    if not 0 <= indice < len(portas):
        print("Número fora da lista.")
        return None
    return portas[indice]


def monitorar(
    porta: str,
    baudrate: int = 9600,
    amostras: int = 25,
    tolerancia: float = 5.0,
    peso_minimo: float = 100.0,
    regex: str | None = None,
) -> None:
    """Lê continuamente a balança na porta e imprime linha bruta e peso.

    Interrompa com Ctrl+C. Quando a janela estabiliza, imprime o peso estável.
    """
    serial = BalancaSerial(porta, baudrate=baudrate)
    estabilizador = EstabilizadorPeso(
        tamanho_janela=amostras,
        tolerancia=tolerancia,
        peso_minimo=peso_minimo,
    )
    print(f"Lendo {porta} @ {baudrate} baud. Ctrl+C para sair.")
    print(f"{'linha bruta':<40} {'peso (kg)':>10}")
    try:
        while True:
            linha = serial.ler_linha()
            if linha is None:
                continue
            peso = extrair_peso(linha, padrao=regex)
            marcador = ""
            if peso is not None:
                estavel = estabilizador.adicionar(peso)
                if estavel is not None:
                    marcador = f"  <- estável: {estavel.peso} kg (desvio {estavel.desvio})"
            rotulo = f"{peso:.1f}" if peso is not None else "-"
            print(f"{limpar(linha):<40} {rotulo:>10}{marcador}")
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        serial.fechar()


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lista portas e lê o peso da balança.")
    parser.add_argument("--listar", action="store_true", help="Apenas lista as portas e sai.")
    parser.add_argument("--porta", default=None, help="Porta serial (ex: COM3 ou /dev/ttyUSB0).")
    parser.add_argument("--detectar", action="store_true", help="Varre as portas procurando a balança.")
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument("--amostras", type=int, default=25, help="Leituras por janela de estabilização.")
    parser.add_argument("--tolerancia", type=float, default=5.0, help="MAD máximo para considerar estável (kg).")
    parser.add_argument("--peso-minimo", type=float, default=100.0, help="Ignora pesos abaixo disso (balança vazia).")
    parser.add_argument("--regex", default=None, help="Regex com grupo p/ o número do peso (protocolo específico).")
    return parser.parse_args()


def main() -> None:
    args = _argumentos()

    if args.listar:
        imprimir_portas(listar_portas())
        return

    porta = args.porta
    if porta is None and args.detectar:
        porta = detectar(baudrate=args.baudrate, regex=args.regex)

    if porta is None:
        portas = listar_portas()
        imprimir_portas(portas)
        escolhida = selecionar_porta(portas)
        if escolhida is None:
            return
        porta = escolhida.device

    monitorar(
        porta=porta,
        baudrate=args.baudrate,
        amostras=args.amostras,
        tolerancia=args.tolerancia,
        peso_minimo=args.peso_minimo,
        regex=args.regex,
    )


if __name__ == "__main__":
    main()
