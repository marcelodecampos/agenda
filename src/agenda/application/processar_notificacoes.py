from __future__ import annotations

from datetime import datetime

from agenda.ports import NotificacaoPort


class ProcessarNotificacoesVencidas:
    def __init__(
        self,
        repositorio: object,
        entregador: NotificacaoPort,
        max_tentativas: int = 3,
    ) -> None:
        self.repositorio = repositorio
        self.entregador = entregador
        self.max_tentativas = max_tentativas

    def executar(self, agora: datetime) -> dict[str, int]:
        processadas = 0
        enviadas = 0
        falhas = 0
        for notificacao in self.repositorio.listar_pendentes_vencidas(agora):
            processadas += 1
            registro = self.repositorio.buscar_por_agendamento_id(
                notificacao.agendamento_id
            )
            if registro is not None and registro.tentativas >= self.max_tentativas:
                continue
            if not self.repositorio.marcar_enviando(notificacao.agendamento_id):
                continue
            try:
                self.entregador.enviar(notificacao)
            except Exception as exc:
                self.repositorio.marcar_falha(notificacao.agendamento_id, str(exc))
                falhas += 1
            else:
                self.repositorio.marcar_enviada(notificacao.agendamento_id, agora)
                enviadas += 1
        return {"processadas": processadas, "enviadas": enviadas, "falhas": falhas}