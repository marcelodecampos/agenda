from __future__ import annotations

import smtplib
from email.message import EmailMessage

from agenda.ports import NotificacaoAgendamento, NotificacaoPort


class SMTPNotificacaoAdapter(NotificacaoPort):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        remetente: str,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.remetente = remetente
        self.username = username
        self.password = password
        self.starttls = starttls

    def enviar(self, notificacao: NotificacaoAgendamento) -> None:
        if notificacao.destinatario.canal != "email":
            raise ValueError("SMTP suporta somente o canal email")
        mensagem = EmailMessage()
        mensagem["From"] = self.remetente
        mensagem["To"] = notificacao.destinatario.destino
        mensagem["Subject"] = "Lembrete de agendamento"
        mensagem.set_content(notificacao.mensagem)
        with smtplib.SMTP(self.host, self.port, timeout=10) as servidor:
            if self.starttls:
                servidor.starttls()
            if self.username:
                servidor.login(self.username, self.password or "")
            servidor.send_message(mensagem)