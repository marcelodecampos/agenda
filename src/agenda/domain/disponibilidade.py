import uuid
from dataclasses import dataclass, field
from datetime import date, time

from agenda.domain.exceptions import DisponibilidadeInvalidaError


@dataclass(frozen=True)
class IntervaloHorario:
    inicio: time
    fim: time

    def __post_init__(self) -> None:
        if self.inicio >= self.fim:
            raise DisponibilidadeInvalidaError(
                "inicio do intervalo deve ser anterior ao fim"
            )


@dataclass(frozen=True)
class JanelaSemanal:
    """Intervalo recorrente; dia da semana segue date.weekday() (segunda=0)."""

    dia_semana: int
    intervalo: IntervaloHorario

    def __post_init__(self) -> None:
        if self.dia_semana not in range(7):
            raise DisponibilidadeInvalidaError("dia da semana deve estar entre 0 e 6")


@dataclass(frozen=True)
class ExcecaoAgenda:
    """Substitui a agenda semanal de uma data; intervalos vazios significam folga."""

    data: date
    intervalos: tuple[IntervaloHorario, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Disponibilidade:
    """Disponibilidade configurada por profissional, organizacao ou ambos."""

    id: uuid.UUID
    semanal: tuple[JanelaSemanal, ...] = field(default_factory=tuple)
    excecoes: tuple[ExcecaoAgenda, ...] = field(default_factory=tuple)
    profissional_id: uuid.UUID | None = None
    organizacao_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if self.profissional_id is None and self.organizacao_id is None:
            raise DisponibilidadeInvalidaError(
                "disponibilidade precisa pertencer a um profissional ou organizacao"
            )
        self._validar_sobreposicoes_semanais()
        self._validar_excecoes()

    def intervalos_para(self, data_consulta: date) -> tuple[IntervaloHorario, ...]:
        for excecao in self.excecoes:
            if excecao.data == data_consulta:
                return excecao.intervalos

        return tuple(
            janela.intervalo
            for janela in self.semanal
            if janela.dia_semana == data_consulta.weekday()
        )

    def esta_disponivel(
        self, data_consulta: date, inicio: time, fim: time
    ) -> bool:
        if inicio >= fim:
            return False

        intervalos = self.intervalos_para(data_consulta)
        if not intervalos:
            return False

        solicitado = IntervaloHorario(inicio=inicio, fim=fim)
        return any(
            janela.inicio <= solicitado.inicio and solicitado.fim <= janela.fim
            for janela in intervalos
        )

    def _validar_sobreposicoes_semanais(self) -> None:
        por_dia: dict[int, list[IntervaloHorario]] = {}
        for janela in self.semanal:
            por_dia.setdefault(janela.dia_semana, []).append(janela.intervalo)

        for intervalos in por_dia.values():
            self._validar_sobreposicoes(intervalos)

    def _validar_excecoes(self) -> None:
        datas = [excecao.data for excecao in self.excecoes]
        if len(datas) != len(set(datas)):
            raise DisponibilidadeInvalidaError(
                "nao pode haver mais de uma excecao para a mesma data"
            )
        for excecao in self.excecoes:
            self._validar_sobreposicoes(excecao.intervalos)

    @staticmethod
    def _validar_sobreposicoes(intervalos: tuple[IntervaloHorario, ...] | list[IntervaloHorario]) -> None:
        ordenados = sorted(intervalos, key=lambda intervalo: intervalo.inicio)
        if any(atual.fim > proximo.inicio for atual, proximo in zip(ordenados, ordenados[1:])):
            raise DisponibilidadeInvalidaError("intervalos de horario nao podem se sobrepor")