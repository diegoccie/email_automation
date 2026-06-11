#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import subprocess
import tempfile
from datetime import datetime

class AnsibleAutomation:
    """
    Classe para automação de operações em roteadores Cisco usando Ansible
    """
    
    def __init__(self, ansible_path=None, inventory_path=None):
        """
        Inicializa o módulo de automação Ansible
        
        Args:
            ansible_path: Caminho para os playbooks Ansible (opcional)
            inventory_path: Caminho para o inventário Ansible (opcional)
        """
        # Configurar caminhos
        self.ansible_path = ansible_path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ansible')
        self.inventory_path = inventory_path or os.path.join(self.ansible_path, 'inventory.ini')
        
        # Verificar se os arquivos existem
        if not os.path.exists(self.ansible_path):
            raise FileNotFoundError(f"Diretório Ansible não encontrado: {self.ansible_path}")
            
        if not os.path.exists(self.inventory_path):
            raise FileNotFoundError(f"Arquivo de inventário não encontrado: {self.inventory_path}")
        
        # Configurar logger
        self.logger = logging.getLogger('ansible_automation')
        
        # Verificar se o Ansible está instalado
        try:
            result = subprocess.run(['ansible', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning("Ansible não encontrado ou não está funcionando corretamente")
            else:
                self.logger.info(f"Ansible encontrado: {result.stdout.splitlines()[0]}")
        except Exception as e:
            self.logger.warning(f"Erro ao verificar versão do Ansible: {str(e)}")
    
    def shutdown_interface(self, router, interface, reason=None, extra_vars=None):
        """
        Desativa uma interface em um roteador Cisco
        
        Args:
            router: Nome ou IP do roteador
            interface: Nome da interface (ex: GigabitEthernet0/1)
            reason: Motivo do shutdown (opcional)
            extra_vars: Variáveis adicionais para o playbook (opcional)
            
        Returns:
            dict: Resultado da operação
        """
        # Preparar variáveis
        vars_dict = {
            'target_host': router,
            'interface': interface
        }
        
        if reason:
            vars_dict['shutdown_reason'] = reason
            
        if extra_vars:
            vars_dict.update(extra_vars)
            
        # Executar playbook
        return self._run_playbook('shutdown_interface.yml', vars_dict)
    
    def enable_interface(self, router, interface, reason=None, extra_vars=None):
        """
        Ativa uma interface em um roteador Cisco
        
        Args:
            router: Nome ou IP do roteador
            interface: Nome da interface (ex: GigabitEthernet0/1)
            reason: Motivo da ativação (opcional)
            extra_vars: Variáveis adicionais para o playbook (opcional)
            
        Returns:
            dict: Resultado da operação
        """
        # Preparar variáveis
        vars_dict = {
            'target_host': router,
            'interface': interface
        }
        
        if reason:
            vars_dict['enable_reason'] = reason
            
        if extra_vars:
            vars_dict.update(extra_vars)
            
        # Executar playbook
        return self._run_playbook('enable_interface.yml', vars_dict)
    
    def collect_router_info(self, router, output_dir=None, extra_vars=None):
        """
        Coleta informações de um roteador Cisco
        
        Args:
            router: Nome ou IP do roteador
            output_dir: Diretório para salvar as informações (opcional)
            extra_vars: Variáveis adicionais para o playbook (opcional)
            
        Returns:
            dict: Resultado da operação
        """
        # Preparar variáveis
        vars_dict = {
            'target_host': router
        }
        
        if output_dir:
            vars_dict['output_directory'] = output_dir
        else:
            # Usar diretório temporário se não for especificado
            vars_dict['output_directory'] = tempfile.mkdtemp(prefix='cisco_info_')
            
        if extra_vars:
            vars_dict.update(extra_vars)
            
        # Executar playbook
        result = self._run_playbook('collect_router_info.yml', vars_dict)
        
        # Adicionar caminho do diretório de saída ao resultado
        result['output_directory'] = vars_dict['output_directory']
        
        return result
    
    def _run_playbook(self, playbook_name, extra_vars=None):
        """
        Executa um playbook Ansible
        
        Args:
            playbook_name: Nome do arquivo do playbook
            extra_vars: Variáveis extras para o playbook (opcional)
            
        Returns:
            dict: Resultado da execução
        """
        # Caminho completo para o playbook
        playbook_path = os.path.join(self.ansible_path, playbook_name)
        
        # Verificar se o playbook existe
        if not os.path.exists(playbook_path):
            error_msg = f"Playbook não encontrado: {playbook_path}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }
        
        # Preparar comando
        cmd = ['ansible-playbook', '-i', self.inventory_path, playbook_path]
        
        # Adicionar variáveis extras
        if extra_vars:
            # Criar arquivo temporário para variáveis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(extra_vars, temp_file)
                vars_file = temp_file.name
                
            cmd.extend(['-e', f'@{vars_file}'])
        else:
            vars_file = None
        
        try:
            # Executar comando
            self.logger.info(f"Executando playbook: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Processar resultado
            if result.returncode == 0:
                self.logger.info(f"Playbook {playbook_name} executado com sucesso")
                output = {
                    'success': True,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                self.logger.error(f"Erro ao executar playbook {playbook_name}: {result.stderr}")
                output = {
                    'success': False,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode,
                    'error': f"Ansible retornou código {result.returncode}",
                    'timestamp': datetime.now().isoformat()
                }
            
            # Remover arquivo temporário de variáveis
            if vars_file and os.path.exists(vars_file):
                os.unlink(vars_file)
                
            return output
            
        except Exception as e:
            self.logger.error(f"Exceção ao executar playbook {playbook_name}: {str(e)}")
            
            # Remover arquivo temporário de variáveis
            if vars_file and os.path.exists(vars_file):
                os.unlink(vars_file)
                
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def update_inventory(self, hosts_data):
        """
        Atualiza o inventário Ansible com novos hosts
        
        Args:
            hosts_data: Lista de dicionários com informações dos hosts
                        [{'name': 'router1', 'ip': '192.168.1.1', 'user': 'admin', 'password': 'cisco'}, ...]
            
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            # Fazer backup do inventário atual
            backup_path = f"{self.inventory_path}.bak"
            if os.path.exists(self.inventory_path):
                with open(self.inventory_path, 'r') as src, open(backup_path, 'w') as dst:
                    dst.write(src.read())
                self.logger.info(f"Backup do inventário criado: {backup_path}")
            
            # Ler inventário atual
            inventory_content = []
            if os.path.exists(self.inventory_path):
                with open(self.inventory_path, 'r') as f:
                    inventory_content = f.readlines()
            
            # Encontrar seção [cisco_routers]
            cisco_routers_index = -1
            vars_index = -1
            
            for i, line in enumerate(inventory_content):
                if line.strip() == "[cisco_routers]":
                    cisco_routers_index = i
                elif line.strip() == "[cisco_routers:vars]":
                    vars_index = i
            
            # Se não encontrou seção, criar nova
            if cisco_routers_index == -1:
                inventory_content.append("[cisco_routers]\n")
                cisco_routers_index = len(inventory_content) - 1
            
            # Adicionar hosts entre [cisco_routers] e a próxima seção
            new_hosts = []
            for host in hosts_data:
                host_line = f"{host['name']} ansible_host={host['ip']}"
                
                # Adicionar variáveis específicas do host, se fornecidas
                if 'user' in host:
                    host_line += f" ansible_user={host['user']}"
                if 'password' in host:
                    host_line += f" ansible_password={host['password']}"
                
                new_hosts.append(host_line + "\n")
            
            # Determinar onde inserir os novos hosts
            if vars_index > cisco_routers_index:
                # Inserir antes da seção de variáveis
                inventory_content[cisco_routers_index+1:vars_index] = new_hosts
            else:
                # Inserir após a seção [cisco_routers]
                inventory_content[cisco_routers_index+1:cisco_routers_index+1] = new_hosts
            
            # Se não encontrou seção de variáveis, criar nova
            if vars_index == -1:
                inventory_content.append("\n[cisco_routers:vars]\n")
                inventory_content.append("ansible_connection=network_cli\n")
                inventory_content.append("ansible_network_os=ios\n")
                inventory_content.append("ansible_become=yes\n")
                inventory_content.append("ansible_become_method=enable\n")
            
            # Escrever novo inventário
            with open(self.inventory_path, 'w') as f:
                f.writelines(inventory_content)
                
            self.logger.info(f"Inventário atualizado com {len(hosts_data)} hosts")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar inventário: {str(e)}")
            
            # Restaurar backup se existir
            if os.path.exists(backup_path):
                with open(backup_path, 'r') as src, open(self.inventory_path, 'w') as dst:
                    dst.write(src.read())
                self.logger.info(f"Inventário restaurado do backup")
                
            return False
    
    def get_inventory_hosts(self):
        """
        Obtém a lista de hosts do inventário
        
        Returns:
            list: Lista de dicionários com informações dos hosts
        """
        try:
            # Executar comando ansible-inventory
            cmd = ['ansible-inventory', '-i', self.inventory_path, '--list']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Erro ao obter inventário: {result.stderr}")
                return []
            
            # Processar saída JSON
            inventory_data = json.loads(result.stdout)
            
            # Extrair hosts do grupo cisco_routers
            hosts = []
            
            if 'cisco_routers' in inventory_data and 'hosts' in inventory_data['cisco_routers']:
                for host in inventory_data['cisco_routers']['hosts']:
                    host_info = {
                        'name': host
                    }
                    
                    # Adicionar variáveis do host, se disponíveis
                    if '_meta' in inventory_data and 'hostvars' in inventory_data['_meta'] and host in inventory_data['_meta']['hostvars']:
                        hostvars = inventory_data['_meta']['hostvars'][host]
                        
                        if 'ansible_host' in hostvars:
                            host_info['ip'] = hostvars['ansible_host']
                        
                        if 'ansible_user' in hostvars:
                            host_info['user'] = hostvars['ansible_user']
                    
                    hosts.append(host_info)
            
            return hosts
            
        except Exception as e:
            self.logger.error(f"Erro ao obter hosts do inventário: {str(e)}")
            return []

# Exemplo de uso
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Inicializar módulo de automação
    ansible = AnsibleAutomation()
    
    # Exemplo: Desativar interface
    result = ansible.shutdown_interface(
        router="router1",
        interface="GigabitEthernet0/1",
        reason="Interface desativada devido a flapping detectado"
    )
    
    print(f"Resultado do shutdown: {result['success']}")
    
    # Exemplo: Coletar informações do roteador
    info_result = ansible.collect_router_info(
        router="router1"
    )
    
    print(f"Informações coletadas: {info_result['success']}")
    print(f"Diretório de saída: {info_result.get('output_directory')}")
