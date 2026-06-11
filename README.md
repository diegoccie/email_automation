# Documentação Final - Automação de Monitoramento de Redes

## Visão Geral

Esta solução integra Zabbix 6.0, ChatGPT e Ansible para criar um sistema inteligente de monitoramento e resposta a eventos de rede, com foco em roteadores Cisco IOS 15.0 (série 3800). O sistema detecta eventos de flapping em interfaces, analisa os logs com ChatGPT para tomar decisões inteligentes e executa ações automatizadas via Ansible.

## Arquitetura

A solução é composta pelos seguintes componentes:

1. **Módulo de Integração com Zabbix 6.0**
   - Monitoramento de logs via syslog
   - Detecção de eventos de flapping
   - API Python para consulta de dados

2. **Módulo de Decisão com ChatGPT**
   - Análise inteligente de logs e eventos
   - Recomendação de ações baseada em padrões
   - Integração com a API da OpenAI

3. **Módulo de Automação com Ansible**
   - Playbooks para shutdown/ativação de interfaces
   - Coleta de informações de roteadores
   - Inventário dinâmico

4. **Interface Web**
   - Painel de gerenciamento completo
   - Funcionalidade de discovery
   - Visualização de eventos e alertas

## Fluxo de Funcionamento

1. Roteador Cisco envia logs via syslog para o servidor Zabbix
2. Zabbix detecta padrão de flapping através de triggers
3. Backend é notificado e coleta dados detalhados
4. ChatGPT analisa e recomenda ação (shutdown ou não)
5. Interface web exibe a recomendação
6. Usuário aprova ou o sistema executa automaticamente
7. Ansible executa a ação no roteador
8. Resultado é registrado e exibido no dashboard

## Componentes Desenvolvidos

### Backend

- **app.py**: Aplicação Flask principal
- **routes.py**: Rotas da API
- **zabbix_api.py**: Integração com Zabbix
- **flapping_detector.py**: Detector de flapping
- **chatgpt_decision.py**: Integração com ChatGPT
- **ansible_automation.py**: Integração com Ansible

### Ansible

- **shutdown_interface.yml**: Playbook para desativar interfaces
- **enable_interface.yml**: Playbook para ativar interfaces
- **collect_router_info.yml**: Playbook para coletar informações
- **inventory.ini**: Inventário de roteadores

### Frontend

- **templates/index.html**: Interface web completa

### Implantação

- **deploy.py**: Script para configurar ambiente de simulação
- **docker-compose.yml**: Configuração dos containers

## Requisitos

- Python 3.8+
- Flask/FastAPI
- Zabbix Server 6.0
- Ansible
- Docker (para ambiente de simulação)
- Chave API da OpenAI

## Instalação e Uso

### Configuração do Ambiente

1. Clone o repositório:
   ```
   git clone https://github.com/seu-usuario/network-automation.git
   cd network-automation
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Configure a chave API do ChatGPT:
   ```
   export OPENAI_API_KEY="sua-chave-api"
   ```

4. Execute o script de implantação:
   ```
   python deploy.py
   ```

### Acesso à Interface

- Interface Web: http://localhost:5000
- Zabbix: http://localhost:8080 (usuário: Admin, senha: zabbix)

### Uso da Funcionalidade de Discovery

1. Acesse a interface web
2. Clique no botão "Discovery" no dashboard
3. Clique em "Iniciar Discovery" no modal
4. Os roteadores detectados no Zabbix serão adicionados ao inventário Ansible

### Monitoramento e Automação

1. Os eventos de flapping serão exibidos no dashboard
2. Clique em um evento para ver detalhes e a análise do ChatGPT
3. Aprove ou rejeite a recomendação de shutdown
4. O sistema executará a ação via Ansible e atualizará o status

## Personalização

### Configuração do Zabbix

Edite as configurações do Zabbix na página de configurações da interface web:
- URL do Zabbix
- Credenciais de acesso
- Thresholds de detecção

### Configuração do ChatGPT

Edite as configurações do ChatGPT na página de configurações:
- Chave API
- Modelo (GPT-4 ou GPT-3.5)
- Parâmetros de geração

### Configuração do Ansible

Edite as configurações do Ansible na página de configurações:
- Caminho do inventário
- Credenciais de acesso aos roteadores

## Solução de Problemas

### Logs

Os logs da aplicação são armazenados em:
- Backend: stdout do container
- Zabbix: /var/log/zabbix
- Ansible: /tmp/ansible_*.log

### Problemas Comuns

1. **Erro de conexão com o Zabbix**
   - Verifique se o servidor Zabbix está em execução
   - Verifique as credenciais de acesso

2. **Erro na API do ChatGPT**
   - Verifique se a chave API está correta
   - Verifique se há saldo disponível na conta

3. **Erro na execução do Ansible**
   - Verifique se os roteadores estão acessíveis
   - Verifique as credenciais SSH

## Contribuição

Para contribuir com o projeto:
1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Envie um pull request

## Licença

Este projeto está licenciado sob a licença MIT.
