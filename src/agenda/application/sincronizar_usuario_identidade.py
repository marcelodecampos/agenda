from __future__ import annotations

import uuid

from agenda.domain.usuario import Usuario
from agenda.ports import IdentidadeExterna


class SincronizarUsuarioIdentidade:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, identidade: IdentidadeExterna) -> Usuario:
        existente = self.repositorio.buscar_por_provider_subject(
            identidade.provider,
            identidade.subject,
        )
        if existente is not None:
            atualizado = Usuario(
                id=existente.id,
                provider=existente.provider,
                subject=existente.subject,
                nome=identidade.nome or existente.nome,
                cpf=identidade.cpf or existente.cpf,
                email=identidade.email or existente.email,
                telefone=identidade.telefone or existente.telefone,
            )
            return self.repositorio.atualizar(atualizado)

        novo_usuario = Usuario(
            id=uuid.uuid7(),
            provider=identidade.provider,
            subject=identidade.subject,
            nome=identidade.nome,
            cpf=identidade.cpf,
            email=identidade.email,
            telefone=identidade.telefone,
        )
        for campo, valor, buscar in (
            ("cpf", novo_usuario.cpf, self.repositorio.buscar_por_cpf),
            ("email", novo_usuario.email, self.repositorio.buscar_por_email),
            ("telefone", novo_usuario.telefone, self.repositorio.buscar_por_telefone),
        ):
            if valor is not None and buscar(valor) is not None:
                raise ValueError(f"identidade externa conflitante por {campo}")
        return self.repositorio.salvar(novo_usuario)