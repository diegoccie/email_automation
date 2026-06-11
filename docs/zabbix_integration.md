# Módulo de Integração com Zabbix 6.0

## Visão Geral

Este módulo é responsável pela integração com o Zabbix 6.0 para monitoramento de roteadores Cisco IOS 15.0 (série 3800). Ele captura logs via syslog, detecta eventos de flapping de interfaces e aciona alertas que serão processados pelo backend.

## Componentes

### 1. Configuração do Zabbix Server

#### Requisitos
- Zabbix Server 6.0
- Servidor rsyslog configurado
- Acesso aos roteadores Cisco via rede

#### Configuração do Syslog
```bash
# Configuração do rsyslog para receber logs dos roteadores Cisco
# Arquivo: /etc/rsyslog.d/10-cisco.conf

# Definir template para logs Cisco
$template CiscoLogs,"/var/log/cisco/%HOSTNAME%.log"

# Receber logs UDP na porta 514
$ModLoad imudp
$UDPServerRun 514

# Filtrar logs dos roteadores Cisco e salvar em arquivos separados
if $fromhost-ip startswith '192.168.' and $msg contains 'LINEPROTO' then ?CiscoLogs
& stop
```

### 2. Templates e Triggers do Zabbix

#### Template para Roteadores Cisco
- Nome: `Template Cisco IOS 15.0 Router`
- Aplicações: Network, Interfaces, Syslog
- Itens:
  - Interface Status (SNMP)
  - Syslog Monitoring (Log)
  - CPU Usage (SNMP)
  - Memory Usage (SNMP)

#### Trigger para Detecção de Flapping
```
Nome: Interface Flapping Detected
Expressão: {Template Cisco IOS 15.0 Router:log[/var/log/cisco/*.log].regexp("Interface .* changed state to (up|down)",#5)}=1
Severidade: Alta
Descrição: Detectado flapping na interface do roteador {HOST.NAME}
```

### 3. Ações do Zabbix

#### Ação para Notificação de Flapping
- Nome: `Interface Flapping Action`
- Condições: Trigger = "Interface Flapping Detected"
- Operações:
  1. Enviar webhook para o backend
  2. Enviar e-mail para administradores
  3. Executar script remoto (opcional)

#### Configuração do Webhook
```
URL: http://backend-api:5000/api/events/flapping
Método: POST
Tipo de conteúdo: application/json
Corpo:
{
    "host": "{HOST.NAME}",
    "ip": "{HOST.IP}",
    "trigger": "{TRIGGER.NAME}",
    "status": "{TRIGGER.STATUS}",
    "severity": "{TRIGGER.SEVERITY}",
    "item": "{ITEM.NAME}",
    "value": "{ITEM.VALUE}",
    "id": "{EVENT.ID}",
    "date": "{EVENT.DATE}",
    "time": "{EVENT.TIME}",
    "description": "{TRIGGER.DESCRIPTION}"
}
```

### 4. API Python para Zabbix

Este componente fornece uma interface Python para interagir com a API do Zabbix 6.0.

```python
# zabbix_api.py
import requests
import json
import logging

class ZabbixAPI:
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.auth_token = None
        self.api_version = None
        self.logger = logging.getLogger('zabbix_api')
        
    def login(self):
        """Autenticar na API do Zabbix e obter token"""
        data = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "user": self.user,
                "password": self.password
            },
            "id": 1
        }
        
        response = requests.post(
            self.url,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json-rpc'}
        )
        
        result = response.json()
        
        if 'result' in result:
            self.auth_token = result['result']
            self.logger.info("Autenticação bem-sucedida na API do Zabbix")
            return True
        else:
            self.logger.error(f"Falha na autenticação: {result['error']['data']}")
            return False
    
    def api_call(self, method, params=None):
        """Fazer chamada genérica à API do Zabbix"""
        if not self.auth_token:
            self.login()
            
        if params is None:
            params = {}
            
        data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "auth": self.auth_token,
            "id": 2
        }
        
        response = requests.post(
            self.url,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json-rpc'}
        )
        
        result = response.json()
        
        if 'result' in result:
            return result['result']
        else:
            self.logger.error(f"Erro na chamada API {method}: {result['error']['data']}")
            return None
    
    def get_hosts(self, filter_params=None):
        """Obter lista de hosts com filtros opcionais"""
        params = {
            "output": ["hostid", "host", "name", "status", "interfaces"],
            "selectInterfaces": ["interfaceid", "ip", "dns", "useip", "type", "main"]
        }
        
        if filter_params:
            params.update(filter_params)
            
        return self.api_call("host.get", params)
    
    def get_host_by_ip(self, ip):
        """Obter host pelo endereço IP"""
        hosts = self.get_hosts({
            "filter": {
                "ip": ip
            }
        })
        
        if hosts and len(hosts) > 0:
            return hosts[0]
        return None
    
    def get_triggers(self, host_id, active_only=True):
        """Obter triggers para um host específico"""
        params = {
            "output": ["triggerid", "description", "priority", "status", "value", "lastchange"],
            "hostids": host_id,
            "expandDescription": True,
            "selectHosts": ["hostid", "host", "name"],
            "selectItems": ["itemid", "name", "key_", "lastvalue"]
        }
        
        if active_only:
            params["filter"] = {"value": 1}  # Apenas triggers ativos
            
        return self.api_call("trigger.get", params)
    
    def get_events(self, trigger_id, time_from=None, time_till=None, limit=10):
        """Obter eventos para um trigger específico"""
        params = {
            "output": "extend",
            "select_acknowledges": "extend",
            "objectids": trigger_id,
            "sortfield": ["clock", "eventid"],
            "sortorder": "DESC",
            "limit": limit
        }
        
        if time_from:
            params["time_from"] = time_from
            
        if time_till:
            params["time_till"] = time_till
            
        return self.api_call("event.get", params)
    
    def get_history(self, item_id, time_from=None, time_till=None, limit=100):
        """Obter histórico para um item específico"""
        params = {
            "output": "extend",
            "itemids": item_id,
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": limit
        }
        
        if time_from:
            params["time_from"] = time_from
            
        if time_till:
            params["time_till"] = time_till
            
        return self.api_call("history.get", params)
    
    def get_cisco_routers(self):
        """Obter lista de roteadores Cisco"""
        return self.get_hosts({
            "search": {
                "name": "Cisco"
            },
            "searchWildcardsEnabled": True
        })
    
    def get_interface_flapping_events(self, time_from=None, limit=50):
        """Obter eventos de flapping de interface"""
        params = {
            "output": "extend",
            "select_acknowledges": "extend",
            "search": {
                "name": "Interface Flapping Detected"
            },
            "searchWildcardsEnabled": True,
            "sortfield": ["clock", "eventid"],
            "sortorder": "DESC",
            "limit": limit
        }
        
        if time_from:
            params["time_from"] = time_from
            
        return self.api_call("event.get", params)
    
    def acknowledge_event(self, event_id, message):
        """Reconhecer um evento"""
        params = {
            "eventids": event_id,
            "action": 6,  # Adicionar mensagem + reconhecer
            "message": message
        }
        
        return self.api_call("event.acknowledge", params)
```

### 5. Simulação de Roteadores Cisco

Para o ambiente simulado, utilizaremos GNS3 ou uma alternativa para simular roteadores Cisco IOS 15.0 (série 3800).

#### Configuração do Roteador Cisco para Syslog
```
! Configuração do roteador para enviar logs via syslog
router# configure terminal
router(config)# logging host 192.168.1.100
router(config)# logging trap informational
router(config)# logging facility local6
router(config)# logging source-interface GigabitEthernet0/0
router(config)# end
router# write memory
```

#### Script para Simular Flapping de Interface
```python
# simulate_flapping.py
import paramiko
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('flapping_simulator')

def simulate_flapping(router_ip, username, password, interface, count=5, interval_min=10, interval_max=30):
    """
    Simula flapping em uma interface de roteador Cisco
    
    Args:
        router_ip: IP do roteador
        username: Nome de usuário SSH
        password: Senha SSH
        interface: Nome da interface (ex: GigabitEthernet0/1)
        count: Número de ciclos de flapping
        interval_min: Intervalo mínimo entre mudanças de estado (segundos)
        interval_max: Intervalo máximo entre mudanças de estado (segundos)
    """
    logger.info(f"Iniciando simulação de flapping na interface {interface} do roteador {router_ip}")
    
    # Conectar ao roteador via SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(router_ip, username=username, password=password, look_for_keys=False)
        logger.info(f"Conectado ao roteador {router_ip}")
        
        # Configurar terminal
        channel = ssh.invoke_shell()
        channel.send("terminal length 0\n")
        time.sleep(1)
        
        # Ciclo de flapping
        for i in range(count):
            # Desativar interface
            logger.info(f"Ciclo {i+1}/{count}: Desativando interface {interface}")
            channel.send(f"configure terminal\n")
            time.sleep(1)
            channel.send(f"interface {interface}\n")
            time.sleep(1)
            channel.send(f"shutdown\n")
            time.sleep(1)
            channel.send(f"end\n")
            time.sleep(1)
            
            # Esperar intervalo aleatório
            wait_time = random.randint(interval_min, interval_max)
            logger.info(f"Aguardando {wait_time} segundos...")
            time.sleep(wait_time)
            
            # Ativar interface
            logger.info(f"Ciclo {i+1}/{count}: Ativando interface {interface}")
            channel.send(f"configure terminal\n")
            time.sleep(1)
            channel.send(f"interface {interface}\n")
            time.sleep(1)
            channel.send(f"no shutdown\n")
            time.sleep(1)
            channel.send(f"end\n")
            time.sleep(1)
            
            # Esperar intervalo aleatório se não for o último ciclo
            if i < count - 1:
                wait_time = random.randint(interval_min, interval_max)
                logger.info(f"Aguardando {wait_time} segundos...")
                time.sleep(wait_time)
        
        logger.info(f"Simulação de flapping concluída após {count} ciclos")
        
    except Exception as e:
        logger.error(f"Erro durante a simulação: {str(e)}")
    finally:
        ssh.close()
        logger.info(f"Conexão com o roteador {router_ip} encerrada")

if __name__ == "__main__":
    # Exemplo de uso
    simulate_flapping(
        router_ip="192.168.1.1",
        username="admin",
        password="cisco",
        interface="GigabitEthernet0/1",
        count=5,
        interval_min=5,
        interval_max=15
    )
```

## Integração com o Backend

O módulo de integração com Zabbix se comunica com o backend através de webhooks e da API Python. O backend recebe notificações de eventos do Zabbix e pode consultar informações adicionais usando a API.

### Exemplo de Recebimento de Webhook no Backend

```python
# backend/routes/events.py
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

events_bp = Blueprint('events', __name__, url_prefix='/api/events')
logger = logging.getLogger('events')

@events_bp.route('/flapping', methods=['POST'])
def receive_flapping_event():
    """Receber notificação de evento de flapping do Zabbix"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    logger.info(f"Evento de flapping recebido: {data}")
    
    # Extrair informações relevantes
    event = {
        "host": data.get("host"),
        "ip": data.get("ip"),
        "trigger": data.get("trigger"),
        "severity": data.get("severity"),
        "description": data.get("description"),
        "event_id": data.get("id"),
        "timestamp": datetime.now().isoformat(),
        "status": "received",
        "processed": False
    }
    
    # Adicionar à fila de processamento (será processado pelo módulo ChatGPT)
    # queue.add_event(event)
    
    # Salvar no banco de dados
    # db.events.insert_one(event)
    
    return jsonify({"status": "success", "message": "Event received and queued for processing"}), 200
```

## Configuração do Ambiente Simulado

Para o ambiente simulado, utilizaremos Docker para criar containers com Zabbix Server 6.0 e GNS3/EVE-NG para simular roteadores Cisco.

### Docker Compose para Zabbix

```yaml
# docker-compose.yml
version: '3'

services:
  zabbix-postgres:
    image: postgres:13
    restart: always
    environment:
      POSTGRES_USER: zabbix
      POSTGRES_PASSWORD: zabbix
      POSTGRES_DB: zabbix
    volumes:
      - zabbix-postgres-data:/var/lib/postgresql/data

  zabbix-server:
    image: zabbix/zabbix-server-pgsql:6.0-ubuntu-latest
    restart: always
    depends_on:
      - zabbix-postgres
    environment:
      DB_SERVER_HOST: zabbix-postgres
      POSTGRES_USER: zabbix
      POSTGRES_PASSWORD: zabbix
      POSTGRES_DB: zabbix
    ports:
      - "10051:10051"
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/log/cisco:/var/log/cisco

  zabbix-web:
    image: zabbix/zabbix-web-nginx-pgsql:6.0-ubuntu-latest
    restart: always
    depends_on:
      - zabbix-postgres
      - zabbix-server
    environment:
      DB_SERVER_HOST: zabbix-postgres
      POSTGRES_USER: zabbix
      POSTGRES_PASSWORD: zabbix
      POSTGRES_DB: zabbix
      ZBX_SERVER_HOST: zabbix-server
      PHP_TZ: UTC
    ports:
      - "8080:8080"
    volumes:
      - /etc/localtime:/etc/localtime:ro

  rsyslog:
    image: rsyslog/syslog_appliance_alpine
    restart: always
    ports:
      - "514:514/udp"
    volumes:
      - ./rsyslog.conf:/etc/rsyslog.conf
      - /var/log/cisco:/var/log/cisco

volumes:
  zabbix-postgres-data:
```

## Próximos Passos

1. Implementar a configuração do Zabbix Server
2. Criar templates e triggers para monitoramento de roteadores Cisco
3. Desenvolver a API Python para integração com o Zabbix
4. Configurar o ambiente simulado com Docker e GNS3/EVE-NG
5. Testar a detecção de eventos de flapping
