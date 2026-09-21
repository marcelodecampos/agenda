from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalizar_texto(valor: str) -> str:
    """Normaliza caixa e diacríticos sem alterar o texto exibido ao usuário."""
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", valor.casefold())
        if not unicodedata.combining(caractere)
    )
    return " ".join(_TOKEN_RE.findall(sem_acentos))


def _forma_tolerante(token: str) -> str:
    # Trata a confusão s/z como uma variante de consulta, não como alteração do cadastro.
    return token.replace("z", "s")


def _similaridade_token(consulta: str, texto: str) -> float:
    consulta_tolerante = _forma_tolerante(consulta)
    texto_tolerante = _forma_tolerante(texto)
    return max(
        SequenceMatcher(None, consulta, texto).ratio(),
        SequenceMatcher(None, consulta_tolerante, texto_tolerante).ratio(),
    )


def corresponde_busca(termo: str, *campos: str) -> bool:
    """Retorna se o termo corresponde aos campos, tolerando variações pequenas."""
    consulta = normalizar_texto(termo)
    if not consulta:
        return True

    tokens_consulta = consulta.split()
    textos = [normalizar_texto(campo) for campo in campos if campo]
    texto_completo = " ".join(textos)
    tokens_texto = texto_completo.split()

    # Frases digitadas corretamente continuam exigindo a sequência completa.
    if len(consulta) >= 3 and consulta in texto_completo:
        return True

    for token_consulta in tokens_consulta:
        if not any(
            _similaridade_token(token_consulta, token_texto) >= _limiar(token_consulta)
            for token_texto in tokens_texto
        ):
            return False
    return True


def pontuar_busca(termo: str, texto: str) -> float:
    """Calcula a relevância de um texto para a consulta normalizada."""
    consulta = normalizar_texto(termo)
    alvo = normalizar_texto(texto)
    if not consulta or not alvo:
        return 0.0
    if consulta == alvo:
        return 1.0
    if alvo.startswith(consulta):
        return 0.96
    if consulta in alvo:
        return 0.92

    consulta_tokens = consulta.split()
    alvo_tokens = alvo.split()
    pontuacoes = [
        max(_similaridade_token(token, alvo_token) for alvo_token in alvo_tokens)
        for token in consulta_tokens
    ]
    if not pontuacoes:
        return 0.0
    return sum(pontuacoes) / len(pontuacoes)


def _limiar(token: str) -> float:
    tamanho = len(token)
    if tamanho <= 3:
        return 1.0
    if tamanho <= 5:
        return 0.78
    return 0.72