from __future__ import annotations

import uuid
from dataclasses import dataclass

from agenda.domain.endereco import Endereco
from agenda.domain.ids import novo_id
from agenda.domain.membership import Membership
from agenda.domain.organizacao import Organizacao
from agenda.domain.papel import Papel


@dataclass(frozen=True)
class PerfilOrganizacaoComEquipe:
    organizacao: Organizacao
    membership: Membership


class CriarOrganizacaoComEquipe:
    """Bootstrap do caso salao/equipe: cria organizacao nao unipessoal e vincula o
    usuario autenticado como dono, pronta para receber funcionarios e autonomos
    associados em seguida via CriarMembership. Complementa CriarProfissionalIndependente,
    que cobre o caso autonomo puro (organizacao unipessoal)."""

    def __init__(self, organizacoes: object, memberships: object) -> None:
        self.organizacoes = organizacoes
        self.memberships = memberships

    def executar(
        self,
        *,
        usuario_id: uuid.UUID,
        nome: str,
        papel_dono: Papel,
        endereco: Endereco | None = None,
    ) -> PerfilOrganizacaoComEquipe:
        organizacao = Organizacao(
            id=novo_id(),
            nome=nome,
            unipessoal=False,
            endereco=endereco,
        )
        membership = Membership(
            id=novo_id(),
            usuario_id=usuario_id,
            organizacao_id=organizacao.id,
            papeis=[papel_dono],
        )

        self.organizacoes.salvar(organizacao)
        self.memberships.salvar(membership)
        return PerfilOrganizacaoComEquipe(
            organizacao=organizacao,
            membership=membership,
        )
