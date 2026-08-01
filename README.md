# TecWorld

Sistema de gestão para provedores e equipes de infraestrutura: clientes, ordens de serviço, orçamentos, financeiro e relatórios. A aplicação é construída com Django, PostgreSQL, templates responsivos e CBVs — o Django Admin fica exclusivamente para suporte.

## Subir o ambiente

1. Copie `.env.example` para `.env` e altere as credenciais em produção.
2. Execute `docker compose up --build`.
3. Em outro terminal, crie o administrador: `docker compose exec web python manage.py createsuperuser`.
4. Acesse `http://localhost:8001/login/`.

Para técnicos, crie usuários pela área administrativa de manutenção (`/admin/`) e deixe `is_staff` desmarcado. Eles visualizarão apenas as OS atribuídas a eles.
