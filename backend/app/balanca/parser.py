"""Extrai o valor de peso (kg) de uma linha enviada pela balança.

As balanças (Toledo, Filizola, Alfa, Micheletti...) têm protocolos próprios,
mas quase todas em "modo contínuo" enviam algo parecido com:

    +  15480 kg
    ST,GS,  15480,kg
    \x02 00015480 kg \x03

O parser tenta ser tolerante: remove caracteres de controle, aceita vírgula
como separador decimal e prioriza o número com unidade/sinal.
"""

import re

# número (opcionalmente com sinal), vírgula/ponto decimal e unidade opcional
_PADRAO_NUMERO = re.compile(r"([+-]?\s*\d+(?:[.,]\d+)?)(?:\s*(kg|lb|t))?\b", re.IGNORECASE)
_CONTROLE = re.compile(r"[\x00-\x1f]")


def _para_float(texto: str) -> float:
    return float(texto.replace(" ", "").replace(",", "."))


def extrair_peso(linha: str, padrao: str | None = None) -> float | None:
    """Retorna o peso em kg extraído de `linha`, ou None se não houver número.

    `padrao` (opcional) é uma regex com um grupo de captura para o número,
    para protocolos específicos (ex.: r"^ST,GS,\\s*([+-]?\\d+)").
    """
    if not linha:
        return None

    s = _CONTROLE.sub(" ", linha).strip()
    if not s:
        return None

    if padrao:
        m = re.search(padrao, s)
        if m:
            grupo = next((g for g in m.groups() if g is not None), None)
            if grupo is not None:
                return _para_float(grupo)
        return None

    achados = _PADRAO_NUMERO.findall(s)
    if not achados:
        return None

    # 1) número acompanhado de unidade (kg/lb/t)
    for numero, unidade in achados:
        if unidade:
            return _para_float(numero)

    # 2) número com sinal explícito
    for numero, _ in achados:
        if "+" in numero or "-" in numero:
            return _para_float(numero)

    # 3) número com mais dígitos (peso costuma ser maior que códigos de status)
    maior = max(achados, key=lambda t: len(re.sub(r"\D", "", t[0])))
    return _para_float(maior[0])
