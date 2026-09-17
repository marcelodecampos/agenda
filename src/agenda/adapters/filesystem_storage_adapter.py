from __future__ import annotations

from pathlib import Path

from agenda.ports import ArmazenamentoBinarioPort


class FilesystemStorageAdapter(ArmazenamentoBinarioPort):
    """Adapter inicial: grava o conteudo em disco local, fragmentado por prefixo do
    sha256 para nao lotar um unico diretorio. obter_url aponta para a rota estatica
    montada pela API (ver main.py); adapters de nuvem devolverao URLs assinadas."""

    def __init__(self, *, raiz: str, base_url: str) -> None:
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def _caminho(self, chave: str) -> Path:
        return self.raiz / chave[:2] / chave[2:4] / chave

    def salvar(self, *, chave: str, conteudo: bytes, mime_type: str) -> None:
        caminho = self._caminho(chave)
        if caminho.exists():
            return
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo)

    def obter_url(self, chave: str) -> str:
        return f"{self.base_url}/media/arquivos/{chave[:2]}/{chave[2:4]}/{chave}"

    def remover(self, chave: str) -> None:
        caminho = self._caminho(chave)
        if caminho.exists():
            caminho.unlink()
