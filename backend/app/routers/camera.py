"""Rota para reconhecimento de placa via câmera IP com credenciais customizadas."""

from fastapi import APIRouter, HTTPException

from ..anpr.recognizer import get_recognizer
from ..schemas import PlacaCameraIn, PlacaCameraOut
from ..services.erros import CameraSnapshotError
from ..services.imagem import decodificar, salvar

router = APIRouter(prefix="/camera", tags=["camera"])

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


async def _descobrir_snapshot(base: str, user: str, password: str, auth_type: str) -> str | None:
    """Testa endpoints comuns de snapshot e retorna a URL que funcionou."""
    import httpx

    auth = (
        httpx.BasicAuth(user, password)
        if auth_type.lower() == "basic"
        else httpx.DigestAuth(user, password)
    )
    async with httpx.AsyncClient(auth=auth, timeout=5.0) as client:
        for caminho in CAMINHOS_SNAPSHOT:
            url = f"{base}{caminho}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and resp.content:
                    return url
            except httpx.HTTPError:
                continue
    return None


async def _capturar_com_credenciais(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    auth_type: str,
    camera_url: str | None,
) -> tuple[bytes, str]:
    """Captura snapshot usando credenciais fornecidas no request.

    Retorna tupla (bytes_do_snapshot, url_que_funcionou).
    """
    import httpx

    base = f"http://{host}:{port}"
    auth = (
        httpx.BasicAuth(user, password)
        if auth_type.lower() == "basic"
        else httpx.DigestAuth(user, password)
    )

    url = camera_url
    if not url:
        url = await _descobrir_snapshot(base, user, password, auth_type)
        if url is None:
            raise CameraSnapshotError(
                "Nenhum endpoint de snapshot respondeu. "
                "Verifique IP, porta, credenciais ou informe camera_url manualmente."
            )

    try:
        async with httpx.AsyncClient(auth=auth, timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            conteudo = resp.content
    except httpx.HTTPError as exc:
        raise CameraSnapshotError(f"Falha ao capturar snapshot: {exc}") from exc

    if not conteudo:
        raise CameraSnapshotError("Snapshot vazio")

    return conteudo, url


@router.post(
    "/reconhecer-placa",
    response_model=PlacaCameraOut,
    summary="Captura imagem da câmera IP e retorna a placa do veículo",
    responses={
        400: {"description": "Credenciais inválidas ou camera_url malformada"},
        422: {"description": "Placa não reconhecida na imagem capturada"},
        502: {"description": "Falha ao conectar ou capturar imagem da câmera"},
    },
)
async def reconhecer_placa(body: PlacaCameraIn) -> PlacaCameraOut:
    """Captura um snapshot da câmera IP usando as credenciais fornecidas e
    retorna a placa do veículo via ANPR (PaddleOCR).

    O endpoint tenta descobrir automaticamente o URL de snapshot correto
    caso ``camera_url`` não seja informado (testa 13 padrões comuns de
    câmeras Intelbras/Dahua/Hikvision).
    """
    try:
        conteudo, url_encontrada = await _capturar_com_credenciais(
            host=body.host,
            port=body.port,
            user=body.user,
            password=body.password,
            auth_type=body.auth,
            camera_url=body.camera_url,
        )
    except CameraSnapshotError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        imagem = decodificar(conteudo)
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="Imagem inválida retornada pela câmera"
        ) from exc

    try:
        melhor = get_recognizer().reconhecer_melhor(imagem)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erro no ANPR: {exc}"
        ) from exc

    if melhor is None:
        raise HTTPException(
            status_code=422, detail="Placa não reconhecida na imagem capturada"
        )

    foto_path = salvar(conteudo)

    return PlacaCameraOut(
        placa=melhor.placa.valor,
        formato=melhor.placa.formato,
        confianca=melhor.confianca,
        raw=melhor.raw,
        camera_url_encontrada=url_encontrada,
        foto_path=foto_path,
    )
