"""Probe/descoberta do endpoint de snapshot de uma câmera IP Intelbras.

Cada câmera tem seu próprio IP. Como a linha Intelbras tem firmwares de OEMs
diferentes (Dahua, XiongMai etc.), o endpoint de snapshot varia. Este script
testa vários padrões comuns e informa qual respondeu.

Uso (a partir da pasta backend/):
    python -m scripts.dvr_probe --host 192.168.11.241 --password senha

O snapshot de teste é salvo em ``data/imagens/dvr_probe.jpg``.
"""

import argparse

import httpx

from app.config import settings

CAMINHOS_SNAPSHOT = [
    "/cgi-bin/snapshot.cgi",
    "/cgi-bin/snapshot.cgi?channel=1",
    "/cgi-bin/snapshot.cgi?channel=0",
    "/webcapture.jpg?command=snap&channel=1",
    "/tmpfs/auto.jpg",
    "/snapshot.jpg",
    "/jpg/image.jpg",
    "/onvif/snapshot",
    "/cgi-bin/images_cgi?channel=0&subtype=0",
    "/cgi-bin/currentpic.cgi",
    "/Streaming/channels/1/picture",
    "/ISAPI/Streaming/channels/101/picture",
    "/cap.jpg",
]


def _tentar(base: str, user: str, password: str, caminho: str) -> bytes | None:
    url = f"{base}{caminho}"
    for auth in (httpx.DigestAuth(user, password), httpx.BasicAuth(user, password)):
        try:
            resp = httpx.get(url, auth=auth, timeout=settings.dvr_timeout)
        except httpx.HTTPError:
            continue
        if resp.status_code == 200 and resp.content:
            return resp.content
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe da câmera IP Intelbras")
    parser.add_argument("--host", required=True, help="IP da câmera")
    parser.add_argument("--port", type=int, default=80, help="Porta HTTP (padrão 80)")
    parser.add_argument("--user", default=settings.dvr_user, help="Usuário da câmera")
    parser.add_argument(
        "--password", default=settings.dvr_password, help="Senha da câmera"
    )
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"

    for caminho in CAMINHOS_SNAPSHOT:
        conteudo = _tentar(base, args.user, args.password, caminho)
        if conteudo is not None:
            destino = settings.imagens_dir / "dvr_probe.jpg"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(conteudo)
            print(f"OK ({len(conteudo)} bytes) em {base}{caminho}")
            print(f"Snapshot salvo em: {destino}")
            print(f"Cadastre no ponto: camera_url={base}{caminho}")
            return

    print("Nenhum endpoint de snapshot respondeu 200.")
    print("Possíveis causas: porta errada, senha errada ou firmware não suportado.")
    print("Informe o modelo da câmera para ajustarmos o caminho.")


if __name__ == "__main__":
    main()
