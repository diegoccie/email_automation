# Arquitetura da Solução de Automação de Rede

## Visão Geral

Esta solução integra Zabbix 6.0, ChatGPT e Ansible para criar um sistema inteligente de monitoramento e resposta a eventos de rede, com foco em roteadores Cisco IOS 15.0 (série 3800).

```
+----------------+     +----------------+     +----------------+
|                |     |                |     |                |
|  Roteadores    |---->|    Zabbix 6.0  |---->|  Backend API   |
|  Cisco 3800    |     |  (Monitoramento)|    |  (Flask/Python)|
|                |     |                |     |                |
+----------------+     +----------------+     +-------+--------+
                                                     |
                                                     v
                       +----------------+     +----------------+
                       |                |     |                |
                       |    Frontend    |<----|  ChatGPT API   |
                       |  (React/Vue.js)|     |   (Decisor)    |
                       |                |     |                |
                       +-------+--------+     +-------+--------+
                               |                      |
                               v                      v
                       +----------------+     +----------------+
                       |                |     |                |
                       |  Usuário Final |     |    Ansible     |
                       |  (Dashboard)   |     | (Automação)    |
                       |                |     |                |
                       +----------------+     +----------------+
```

## Componentes Principais

### 1. Módulo de Integração com Zabbix 6.0
- **Responsabilidades:**
  - Monitorar logs de roteadores Cisco via syslog
  - Detectar eventos de flapping de interfaces
  - Acionar alertas e workflows de automação
  - Fornecer API para consulta de dados pelo backend

- **Tecnologias:**
  - Zabbix Server 6.0
  - Zabbix API (Python)
  - Rsyslog para captura de logs

### 2. Backend API (Python/Flask)
- **Responsabilidades:**
  - Servir como middleware entre todos os componentes
  - Processar dados do Zabbix
  - Comunicar com a API do ChatGPT
  - Acionar playbooks Ansible
  - Fornecer API RESTful para o frontend

- **Tecnologias:**
  - Python 3.8+
  - Flask/FastAPI
  - SQLite/PostgreSQL para armazenamento
  - Celery para tarefas assíncronas

### 3. Módulo de Decisão com ChatGPT
- **Responsabilidades:**
  - Analisar logs e eventos de rede
  - Tomar decisões baseadas em padrões de comportamento
  - Recomendar ações corretivas
  - Fornecer explicações para as decisões tomadas

- **Tecnologias:**
  - OpenAI API (GPT-4)
  - Prompts especializados em redes
  - Sistema de cache para otimização

### 4. Módulo de Automação com Ansible
- **Responsabilidades:**
  - Executar ações corretivas em roteadores Cisco
  - Aplicar configurações padronizadas
  - Realizar shutdown de interfaces com problemas
  - Documentar ações realizadas

- **Tecnologias:**
  - Ansible Core
  - Cisco IOS Collection
  - Playbooks customizados
  - Inventário dinâmico

### 5. Frontend (Dashboard Web)
- **Responsabilidades:**
  - Fornecer interface amigável para gerenciamento
  - Visualizar eventos e alertas em tempo real
  - Permitir aprovação manual de ações recomendadas
  - Implementar funcionalidade de discovery para novos dispositivos

- **Tecnologias:**
  - React.js ou Vue.js
  - Bootstrap ou Material UI
  - Gráficos com Chart.js
  - WebSockets para atualizações em tempo real

## Fluxo de Dados e Processos

### Fluxo Principal
1. Roteador Cisco envia logs via syslog para o servidor Zabbix
2. Zabbix detecta padrão de flapping através de triggers
3. Backend é notificado via webhook do Zabbix
4. Backend coleta dados detalhados do evento via Zabbix API
5. Backend envia dados para análise do ChatGPT
6. ChatGPT analisa e recomenda ação (shutdown ou não)
7. Backend registra decisão e notifica frontend
8. Usuário pode aprovar automaticamente ou manualmente
9. Se aprovado, backend aciona playbook Ansible
10. Ansible executa ação no roteador Cisco
11. Resultado é registrado e exibido no dashboard

### Fluxo de Discovery
1. Usuário clica no botão "Discovery" no dashboard
2. Frontend solicita ao backend para buscar dispositivos no Zabbix
3. Backend consulta Zabbix API para listar todos os hosts
4. Backend filtra dispositivos Cisco compatíveis
5. Frontend exibe lista de dispositivos para monitoramento
6. Usuário seleciona dispositivos para incluir na automação
7. Backend registra dispositivos selecionados no banco de dados

## Ambiente Simulado

Para demonstração, será criado um ambiente simulado com:

1. **Zabbix Server 6.0** em container Docker
2. **Roteadores Cisco IOS 15.0** simulados com GNS3/EVE-NG ou Cisco VIRL
3. **Backend e Frontend** em containers Docker
4. **Ansible Control Node** em container Docker

## Segurança

- Autenticação baseada em tokens JWT
- Comunicação criptografada (HTTPS)
- Armazenamento seguro de credenciais
- Logs de auditoria para todas as ações
- Controle de acesso baseado em funções (RBAC)

## Escalabilidade

- Arquitetura modular permitindo substituição de componentes
- Possibilidade de escalar horizontalmente o backend
- Suporte a múltiplas instâncias Zabbix
- Cache de decisões do ChatGPT para reduzir chamadas API
