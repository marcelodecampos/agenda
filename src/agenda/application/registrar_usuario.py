from __future__ import annotations

from agenda.domain.usuario import Usuario


class RegistrarUsuario:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, usuario: Usuario) -> Usuario:
        if self.repositorio.buscar_por_provider_subject(usuario.provider, usuario.subject):
            raise ValueError("usuario duplicado")
        for campo, valor, buscar in (
            ("cpf", usuario.cpf, self.repositorio.buscar_por_cpf),
            ("email", usuario.email, self.repositorio.buscar_por_email),
            ("telefone", usuario.telefone, self.repositorio.buscar_por_telefone),
        ):
            if valor is not None and buscar(valor):
                raise ValueError(f"usuario duplicado por {campo}")
        return self.repositorio.salvar(usuario)
