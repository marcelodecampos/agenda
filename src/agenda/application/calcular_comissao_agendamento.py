from __future__ import annotations

from decimal import Decimal

from agenda.domain.agendamento import Agendamento
from agenda.domain.comissao import RegraComissao, calcular_comissao


class CalcularComissaoAgendamento:
    def executar(
        self,
        agendamento: Agendamento,
        membership_id: object,
        regras: tuple[RegraComissao, ...],
        status_concluido: str,
    ) -> Decimal:
        return calcular_comissao(
            agendamento=agendamento,
            membership_id=membership_id,
            regras=regras,
            status_concluido=status_concluido,
        )
