#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import logging
import time
from datetime import datetime, timedelta

class ZabbixAPI:
    def __init__(self, url, user, password):
        """
        Inicializa a API do Zabbix
        
        Args:
            url: URL da API do Zabbix (ex: http://zabbix-server/api_jsonrpc.php)
            user: Nome de usuário para autenticação
            password: Senha para autenticação
        """
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
            
            # Obter versão da API
            api_version = self.api_call("apiinfo.version", auth_required=False)
            if api_version:
                self.api_version = api_version
                self.logger.info(f"Versão da API Zabbix: {self.api_version}")
            
            return True
        else:
            self.logger.error(f"Falha na autenticação: {result.get('error', {}).get('data', 'Erro desconhecido')}")
            return False
    
    def api_call(self, method, params=None, auth_required=True):
        """
        Fazer chamada genérica à API do Zabbix
        
        Args:
            method: Método da API Zabbix (ex: "host.get")
            params: Parâmetros para o método (dict)
            auth_required: Se True, inclui token de autenticação
            
        Returns:
            Resultado da chamada API ou None em caso de erro
        """
        if auth_required and not self.auth_token:
            if not self.login():
                return None
            
        if params is None:
            params = {}
            
        data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 2
        }
        
        if auth_required:
            data["auth"] = self.auth_token
        
        try:
            response = requests.post(
                self.url,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json-rpc'},
                timeout=30
            )
            
            result = response.json()
            
            if 'result' in result:
                return result['result']
            else:
                error_data = result.get('error', {}).get('data', 'Erro desconhecido')
                self.logger.error(f"Erro na chamada API {method}: {error_data}")
                
                # Se o erro for de autenticação, tentar fazer login novamente
                if result.get('error', {}).get('code') == -32602 and auth_required:
                    self.logger.info("Tentando autenticar novamente...")
                    if self.login():
                        return self.api_call(method, params, auth_required)
                
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro de conexão na chamada API {method}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Erro ao decodificar resposta JSON: {str(e)}")
            return None
    
    def get_hosts(self, filter_params=None):
        """
        Obter lista de hosts com filtros opcionais
        
        Args:
            filter_params: Parâmetros adicionais para filtrar hosts
            
        Returns:
            Lista de hosts ou None em caso de erro
        """
        params = {
            "output": ["hostid", "host", "name", "status", "interfaces"],
            "selectInterfaces": ["interfaceid", "ip", "dns", "useip", "type", "main"],
            "selectGroups": ["groupid", "name"],
            "selectTags": ["tag", "value"]
        }
        
        if filter_params:
            params.update(filter_params)
            
        return self.api_call("host.get", params)
    
    def get_host_by_ip(self, ip):
        """
        Obter host pelo endereço IP
        
        Args:
            ip: Endereço IP do host
            
        Returns:
            Informações do host ou None se não encontrado
        """
        hosts = self.get_hosts({
            "filter": {
                "ip": ip
            }
        })
        
        if hosts and len(hosts) > 0:
            return hosts[0]
        return None
    
    def get_host_by_name(self, name):
        """
        Obter host pelo nome
        
        Args:
            name: Nome do host
            
        Returns:
            Informações do host ou None se não encontrado
        """
        hosts = self.get_hosts({
            "filter": {
                "host": name
            }
        })
        
        if hosts and len(hosts) > 0:
            return hosts[0]
        return None
    
    def get_triggers(self, host_id=None, active_only=True):
        """
        Obter triggers para um host específico ou todos os triggers
        
        Args:
            host_id: ID do host (opcional)
            active_only: Se True, retorna apenas triggers ativos
            
        Returns:
            Lista de triggers ou None em caso de erro
        """
        params = {
            "output": ["triggerid", "description", "priority", "status", "value", "lastchange"],
            "expandDescription": True,
            "selectHosts": ["hostid", "host", "name"],
            "selectItems": ["itemid", "name", "key_", "lastvalue"],
            "sortfield": "lastchange",
            "sortorder": "DESC"
        }
        
        if host_id:
            params["hostids"] = host_id
            
        if active_only:
            params["filter"] = {"value": 1}  # Apenas triggers ativos
            
        return self.api_call("trigger.get", params)
    
    def get_events(self, trigger_id=None, time_from=None, time_till=None, limit=10):
        """
        Obter eventos para um trigger específico ou todos os eventos
        
        Args:
            trigger_id: ID do trigger (opcional)
            time_from: Timestamp inicial (opcional)
            time_till: Timestamp final (opcional)
            limit: Limite de eventos a retornar
            
        Returns:
            Lista de eventos ou None em caso de erro
        """
        params = {
            "output": "extend",
            "select_acknowledges": "extend",
            "sortfield": ["clock", "eventid"],
            "sortorder": "DESC",
            "limit": limit
        }
        
        if trigger_id:
            params["objectids"] = trigger_id
            
        if time_from:
            params["time_from"] = time_from
            
        if time_till:
            params["time_till"] = time_till
            
        return self.api_call("event.get", params)
    
    def get_history(self, item_id, time_from=None, time_till=None, limit=100):
        """
        Obter histórico para um item específico
        
        Args:
            item_id: ID do item
            time_from: Timestamp inicial (opcional)
            time_till: Timestamp final (opcional)
            limit: Limite de registros a retornar
            
        Returns:
            Lista de registros históricos ou None em caso de erro
        """
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
    
    def get_items(self, host_id, application=None):
        """
        Obter itens para um host específico
        
        Args:
            host_id: ID do host
            application: Nome da aplicação para filtrar (opcional)
            
        Returns:
            Lista de itens ou None em caso de erro
        """
        params = {
            "output": ["itemid", "name", "key_", "lastvalue", "lastclock", "status", "state", "error"],
            "hostids": host_id,
            "sortfield": "name",
            "selectApplications": ["applicationid", "name"]
        }
        
        items = self.api_call("item.get", params)
        
        if items and application:
            filtered_items = []
            for item in items:
                for app in item.get("applications", []):
                    if app["name"] == application:
                        filtered_items.append(item)
                        break
            return filtered_items
        
        return items
    
    def get_cisco_routers(self):
        """
        Obter lista de roteadores Cisco
        
        Returns:
            Lista de roteadores Cisco ou None em caso de erro
        """
        # Buscar por hosts com "Cisco" no nome ou descrição
        cisco_hosts = self.get_hosts({
            "search": {
                "name": "Cisco"
            },
            "searchWildcardsEnabled": True
        })
        
        # Filtrar apenas roteadores Cisco IOS 15.0 (série 3800)
        if cisco_hosts:
            routers = []
            for host in cisco_hosts:
                # Verificar se é um roteador da série 3800
                if "3800" in host.get("name", "") or "3800" in host.get("host", ""):
                    routers.append(host)
            return routers
        
        return []
    
    def get_interface_flapping_events(self, time_from=None, limit=50):
        """
        Obter eventos de flapping de interface
        
        Args:
            time_from: Timestamp inicial (opcional)
            limit: Limite de eventos a retornar
            
        Returns:
            Lista de eventos de flapping ou None em caso de erro
        """
        # Se time_from não for especificado, usar as últimas 24 horas
        if not time_from:
            time_from = int(time.time()) - 86400  # 24 horas
            
        params = {
            "output": "extend",
            "select_acknowledges": "extend",
            "search": {
                "name": "Interface Flapping Detected"
            },
            "searchWildcardsEnabled": True,
            "sortfield": ["clock", "eventid"],
            "sortorder": "DESC",
            "limit": limit,
            "time_from": time_from
        }
            
        return self.api_call("event.get", params)
    
    def acknowledge_event(self, event_id, message):
        """
        Reconhecer um evento
        
        Args:
            event_id: ID do evento
            message: Mensagem de reconhecimento
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        params = {
            "eventids": event_id,
            "action": 6,  # Adicionar mensagem + reconhecer
            "message": message
        }
        
        result = self.api_call("event.acknowledge", params)
        return result is not None
    
    def create_host(self, host_name, ip, group_ids, template_ids=None):
        """
        Criar um novo host
        
        Args:
            host_name: Nome do host
            ip: Endereço IP
            group_ids: Lista de IDs de grupos
            template_ids: Lista de IDs de templates (opcional)
            
        Returns:
            ID do host criado ou None em caso de erro
        """
        params = {
            "host": host_name,
            "interfaces": [
                {
                    "type": 1,  # Agent
                    "main": 1,
                    "useip": 1,
                    "ip": ip,
                    "dns": "",
                    "port": "10050"
                }
            ],
            "groups": [{"groupid": gid} for gid in group_ids],
            "tags": [
                {
                    "tag": "Type",
                    "value": "Cisco Router"
                },
                {
                    "tag": "Model",
                    "value": "3800"
                }
            ]
        }
        
        if template_ids:
            params["templates"] = [{"templateid": tid} for tid in template_ids]
            
        result = self.api_call("host.create", params)
        
        if result and "hostids" in result:
            return result["hostids"][0]
        return None
    
    def update_host(self, host_id, params):
        """
        Atualizar um host existente
        
        Args:
            host_id: ID do host
            params: Parâmetros a serem atualizados
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        params["hostid"] = host_id
        result = self.api_call("host.update", params)
        return result is not None
    
    def delete_host(self, host_id):
        """
        Excluir um host
        
        Args:
            host_id: ID do host
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        result = self.api_call("host.delete", [host_id])
        return result is not None
    
    def get_host_groups(self):
        """
        Obter grupos de hosts
        
        Returns:
            Lista de grupos ou None em caso de erro
        """
        params = {
            "output": ["groupid", "name"]
        }
        
        return self.api_call("hostgroup.get", params)
    
    def get_templates(self):
        """
        Obter templates
        
        Returns:
            Lista de templates ou None em caso de erro
        """
        params = {
            "output": ["templateid", "host", "name"]
        }
        
        return self.api_call("template.get", params)
    
    def get_template_by_name(self, name):
        """
        Obter template pelo nome
        
        Args:
            name: Nome do template
            
        Returns:
            Informações do template ou None se não encontrado
        """
        params = {
            "output": ["templateid", "host", "name"],
            "filter": {
                "host": name
            }
        }
        
        templates = self.api_call("template.get", params)
        
        if templates and len(templates) > 0:
            return templates[0]
        return None
    
    def get_problems(self, host_ids=None, severity=None, recent=True):
        """
        Obter problemas ativos
        
        Args:
            host_ids: Lista de IDs de hosts (opcional)
            severity: Nível mínimo de severidade (opcional)
            recent: Se True, retorna apenas problemas recentes (últimas 24h)
            
        Returns:
            Lista de problemas ou None em caso de erro
        """
        params = {
            "output": "extend",
            "selectAcknowledges": "extend",
            "selectTags": "extend",
            "sortfield": ["eventid"],
            "sortorder": "DESC"
        }
        
        if host_ids:
            params["hostids"] = host_ids
            
        if severity:
            params["severities"] = list(range(severity, 6))  # De severity até 5 (Desastre)
            
        if recent:
            params["time_from"] = int(time.time()) - 86400  # 24 horas
            
        return self.api_call("problem.get", params)
    
    def get_sla(self, service_ids, interval=30):
        """
        Obter SLA para serviços
        
        Args:
            service_ids: Lista de IDs de serviços
            interval: Intervalo em dias
            
        Returns:
            Informações de SLA ou None em caso de erro
        """
        # Calcular período
        now = datetime.now()
        time_till = int(now.timestamp())
        time_from = int((now - timedelta(days=interval)).timestamp())
        
        params = {
            "serviceids": service_ids,
            "intervals": [
                {
                    "from": time_from,
                    "to": time_till
                }
            ]
        }
        
        return self.api_call("service.getsla", params)

# Exemplo de uso
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Inicializar API
    zabbix = ZabbixAPI(
        url="http://localhost:8080/api_jsonrpc.php",
        user="Admin",
        password="zabbix"
    )
    
    # Testar conexão
    if zabbix.login():
        print("Conectado ao Zabbix com sucesso!")
        
        # Obter hosts
        hosts = zabbix.get_hosts()
        if hosts:
            print(f"Encontrados {len(hosts)} hosts:")
            for host in hosts:
                print(f"  - {host['name']} ({host['host']})")
        else:
            print("Nenhum host encontrado ou erro na API")
    else:
        print("Falha ao conectar ao Zabbix")
