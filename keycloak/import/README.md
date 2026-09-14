# Realm export do Keycloak

Coloque aqui o arquivo de export do realm (ex: `agenda-realm.json`) para que o Keycloak importe automaticamente na subida do container (`start-dev --import-realm`, já configurado no docker-compose.yml).

Fluxo recomendado:
1. Suba o ambiente sem nenhum arquivo aqui (`docker compose up -d`).
2. Configure o realm manualmente pelo console admin (`http://localhost:8080`), incluindo roles/papéis conforme o catálogo do BUSINESS_MODEL.md.
3. Exporte o realm (Admin Console > Realm settings > Action > Partial/Full export, ou `kc.sh export`) e salve o JSON gerado nesta pasta.
4. Faça commit do JSON exportado (sem credenciais/segredos de usuários reais) para que o próximo `docker compose up -d` já suba o realm pronto.
