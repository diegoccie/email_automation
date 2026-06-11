#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import subprocess
import time
from flask import Flask, render_template, send_from_directory
import docker

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('deployment')

class SimulationEnvironment:
    """
    Classe para gerenciar o ambiente de simulação com Docker
    """
    
    def __init__(self, base_dir=None):
        """
        Inicializa o ambiente de simulação
        
        Args:
            base_dir: Diretório base do projeto (opcional)
        """
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.docker_client = docker.from_env()
        self.containers = {}
        
    def setup_environment(self):
        """
        Configura o ambiente de simulação
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            logger.info("Configurando ambiente de simulação...")
            
            # Criar diretório para arquivos do Zabbix
            zabbix_data_dir = os.path.join(self.base_dir, 'data', 'zabbix')
            os.makedirs(zabbix_data_dir, exist_ok=True)
            
            # Criar diretório para logs do Cisco
            cisco_logs_dir = os.path.join(self.base_dir, 'data', 'cisco_logs')
            os.makedirs(cisco_logs_dir, exist_ok=True)
            
            # Criar arquivo de configuração do rsyslog
            rsyslog_conf = os.path.join(self.base_dir, 'data', 'rsyslog.conf')
            with open(rsyslog_conf, 'w') as f:
                f.write("""
# Configuração do rsyslog para receber logs dos roteadores Cisco
# Definir template para logs Cisco
$template CiscoLogs,"/var/log/cisco/%HOSTNAME%.log"

# Receber logs UDP na porta 514
$ModLoad imudp
$UDPServerRun 514

# Filtrar logs dos roteadores Cisco e salvar em arquivos separados
if $fromhost-ip startswith '192.168.' and $msg contains 'LINEPROTO' then ?CiscoLogs
& stop
                """)
            
            # Criar arquivo docker-compose.yml
            docker_compose_file = os.path.join(self.base_dir, 'docker-compose.yml')
            with open(docker_compose_file, 'w') as f:
                f.write("""
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
      - ./data/zabbix/postgres:/var/lib/postgresql/data

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
      - ./data/cisco_logs:/var/log/cisco

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
      - ./data/rsyslog.conf:/etc/rsyslog.conf
      - ./data/cisco_logs:/var/log/cisco

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    restart: always
    depends_on:
      - zabbix-web
    environment:
      ZABBIX_URL: http://zabbix-web:8080/api_jsonrpc.php
      ZABBIX_USER: Admin
      ZABBIX_PASSWORD: zabbix
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "5000:5000"
    volumes:
      - ./backend:/app
      - ./ansible:/app/ansible
                """)
            
            # Criar Dockerfile para o backend
            dockerfile = os.path.join(self.base_dir, 'Dockerfile.backend')
            with open(dockerfile, 'w') as f:
                f.write("""
FROM python:3.9-slim

WORKDIR /app

# Instalar dependências
RUN apt-get update && apt-get install -y \\
    ansible \\
    sshpass \\
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY backend /app
COPY ansible /app/ansible

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["python", "app.py"]
                """)
            
            # Criar arquivo requirements.txt
            requirements_file = os.path.join(self.base_dir, 'requirements.txt')
            with open(requirements_file, 'w') as f:
                f.write("""
flask==2.0.1
flask-cors==3.0.10
requests==2.26.0
openai==0.27.0
paramiko==2.8.0
docker==5.0.3
                """)
            
            logger.info("Ambiente de simulação configurado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar ambiente de simulação: {str(e)}")
            return False
    
    def start_containers(self):
        """
        Inicia os containers Docker
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            logger.info("Iniciando containers Docker...")
            
            # Verificar se o docker-compose está instalado
            try:
                subprocess.run(['docker-compose', '--version'], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("docker-compose não está instalado ou não está no PATH")
                return False
            
            # Iniciar containers com docker-compose
            result = subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=self.base_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            logger.info(f"Containers iniciados: {result.stdout}")
            
            # Aguardar inicialização dos serviços
            logger.info("Aguardando inicialização dos serviços...")
            time.sleep(30)  # Aguardar 30 segundos para inicialização
            
            # Verificar status dos containers
            containers = self.docker_client.containers.list(
                filters={'label': 'com.docker.compose.project'}
            )
            
            for container in containers:
                self.containers[container.name] = container
                logger.info(f"Container {container.name} está {container.status}")
            
            logger.info("Todos os containers foram iniciados com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar containers: {str(e)}")
            return False
    
    def stop_containers(self):
        """
        Para os containers Docker
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            logger.info("Parando containers Docker...")
            
            # Parar containers com docker-compose
            result = subprocess.run(
                ['docker-compose', 'down'],
                cwd=self.base_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            logger.info(f"Containers parados: {result.stdout}")
            self.containers = {}
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao parar containers: {str(e)}")
            return False
    
    def simulate_cisco_logs(self):
        """
        Simula logs de roteadores Cisco
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            logger.info("Simulando logs de roteadores Cisco...")
            
            # Criar diretório para logs simulados
            logs_dir = os.path.join(self.base_dir, 'data', 'cisco_logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # Simular logs para 3 roteadores
            for i in range(1, 4):
                router_name = f"Router-3845-{i}"
                log_file = os.path.join(logs_dir, f"{router_name}.log")
                
                with open(log_file, 'w') as f:
                    # Simular logs normais
                    f.write(f"Apr 17 22:00:00 {router_name} %LINK-5-CHANGED: Interface GigabitEthernet0/0, changed state to up\n")
                    f.write(f"Apr 17 22:00:01 {router_name} %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/0, changed state to up\n")
                    
                    # Simular logs de flapping para o primeiro roteador
                    if i == 1:
                        for j in range(5):
                            timestamp = f"Apr 17 22:{10+j:02d}:00"
                            f.write(f"{timestamp} {router_name} %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down\n")
                            f.write(f"{timestamp} {router_name} %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to down\n")
                            
                            timestamp = f"Apr 17 22:{10+j:02d}:30"
                            f.write(f"{timestamp} {router_name} %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up\n")
                            f.write(f"{timestamp} {router_name} %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to up\n")
            
            logger.info("Logs de roteadores Cisco simulados com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao simular logs de roteadores Cisco: {str(e)}")
            return False
    
    def configure_zabbix(self):
        """
        Configura o Zabbix com templates e triggers
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            logger.info("Configurando Zabbix...")
            
            # Aguardar disponibilidade da API do Zabbix
            logger.info("Aguardando disponibilidade da API do Zabbix...")
            time.sleep(60)  # Aguardar 60 segundos para inicialização completa
            
            # Importar módulo ZabbixAPI
            import sys
            sys.path.append(os.path.join(self.base_dir, 'backend'))
            from zabbix_api import ZabbixAPI
            
            # Conectar à API do Zabbix
            zabbix_api = ZabbixAPI(
                url="http://localhost:8080/api_jsonrpc.php",
                user="Admin",
                password="zabbix"
            )
            
            if not zabbix_api.login():
                logger.error("Falha ao conectar à API do Zabbix")
                return False
            
            logger.info("Conectado à API do Zabbix com sucesso")
            
            # Criar grupo de hosts para roteadores Cisco
            host_groups = zabbix_api.get_host_groups()
            cisco_group_id = None
            
            for group in host_groups:
                if group['name'] == 'Cisco Routers':
                    cisco_group_id = group['groupid']
                    break
            
            if not cisco_group_id:
                # Criar grupo
                result = zabbix_api.api_call("hostgroup.create", {
                    "name": "Cisco Routers"
                })
                
                if result and 'groupids' in result:
                    cisco_group_id = result['groupids'][0]
                    logger.info(f"Grupo 'Cisco Routers' criado com ID {cisco_group_id}")
                else:
                    logger.error("Falha ao criar grupo 'Cisco Routers'")
                    return False
            
            # Criar template para roteadores Cisco
            templates = zabbix_api.get_templates()
            cisco_template_id = None
            
            for template in templates:
                if template['name'] == 'Template Cisco IOS 15.0 Router':
                    cisco_template_id = template['templateid']
                    break
            
            if not cisco_template_id:
                # Criar template
                result = zabbix_api.api_call("template.create", {
                    "host": "Template Cisco IOS 15.0 Router",
                    "groups": {"groupid": cisco_group_id},
                    "description": "Template para roteadores Cisco IOS 15.0"
                })
                
                if result and 'templateids' in result:
                    cisco_template_id = result['templateids'][0]
                    logger.info(f"Template 'Template Cisco IOS 15.0 Router' criado com ID {cisco_template_id}")
                else:
                    logger.error("Falha ao criar template 'Template Cisco IOS 15.0 Router'")
                    return False
            
            # Criar hosts para roteadores simulados
            for i in range(1, 4):
                router_name = f"Router-3845-{i}"
                
                # Verificar se o host já existe
                host = zabbix_api.get_host_by_name(router_name)
                
                if not host:
                    # Criar host
                    result = zabbix_api.create_host(
                        host_name=router_name,
                        ip=f"192.168.1.{i}",
                        group_ids=[cisco_group_id],
                        template_ids=[cisco_template_id]
                    )
                    
                    if result:
                        logger.info(f"Host '{router_name}' criado com sucesso")
                    else:
                        logger.error(f"Falha ao criar host '{router_name}'")
                        return False
                else:
                    logger.info(f"Host '{router_name}' já existe")
            
            logger.info("Zabbix configurado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar Zabbix: {str(e)}")
            return False
    
    def deploy_application(self):
        """
        Implanta a aplicação web
        
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            logger.info("Implantando aplicação web...")
            
            # Verificar se o container do backend está em execução
            backend_container = self.docker_client.containers.list(
                filters={'name': 'network-automation_backend'}
            )
            
            if not backend_container:
                logger.error("Container do backend não está em execução")
                return False
            
            # Verificar se a aplicação está respondendo
            import requests
            
            try:
                response = requests.get("http://localhost:5000/api/status")
                if response.status_code == 200:
                    logger.info("Aplicação web implantada com sucesso")
                    return True
                else:
                    logger.error(f"Aplicação web retornou status {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro ao conectar à aplicação web: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Erro ao implantar aplicação web: {str(e)}")
            return False

# Função principal
def main():
    """Função principal para configurar e iniciar o ambiente de simulação"""
    logger.info("Iniciando configuração do ambiente de simulação...")
    
    # Criar ambiente de simulação
    env = SimulationEnvironment()
    
    # Configurar ambiente
    if not env.setup_environment():
        logger.error("Falha ao configurar ambiente de simulação")
        return False
    
    # Iniciar containers
    if not env.start_containers():
        logger.error("Falha ao iniciar containers")
        return False
    
    # Simular logs de roteadores Cisco
    if not env.simulate_cisco_logs():
        logger.error("Falha ao simular logs de roteadores Cisco")
        return False
    
    # Configurar Zabbix
    if not env.configure_zabbix():
        logger.error("Falha ao configurar Zabbix")
        return False
    
    # Implantar aplicação
    if not env.deploy_application():
        logger.error("Falha ao implantar aplicação")
        return False
    
    logger.info("Ambiente de simulação configurado e iniciado com sucesso!")
    logger.info("Acesse a aplicação em: http://localhost:5000")
    logger.info("Acesse o Zabbix em: http://localhost:8080 (usuário: Admin, senha: zabbix)")
    
    return True

if __name__ == "__main__":
    main()
