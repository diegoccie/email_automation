#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, request, jsonify

# Rotas da API
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Importar componentes (serão definidos no app.py)
zabbix_api = None
chatgpt_decision = None
ansible_automation = None

def init_routes(zabbix, chatgpt, ansible):
    """Inicializa as referências aos componentes"""
    global zabbix_api, chatgpt_decision, ansible_automation
    zabbix_api = zabbix
    chatgpt_decision = chatgpt
    ansible_automation = ansible

@api_bp.route('/status', methods=['GET'])
def api_status():
    """Retorna o status da API e dos componentes"""
    return jsonify({
        'status': 'online',
        'components': {
            'zabbix': zabbix_api is not None,
            'chatgpt': chatgpt_decision is not None,
            'ansible': ansible_automation is not None
        }
    })

@api_bp.route('/zabbix/hosts', methods=['GET'])
def get_zabbix_hosts():
    """Retorna a lista de hosts do Zabbix"""
    if not zabbix_api:
        return jsonify({'error': 'API do Zabbix não inicializada'}), 500
        
    try:
        hosts = zabbix_api.get_hosts()
        return jsonify({'hosts': hosts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/zabbix/cisco_routers', methods=['GET'])
def get_cisco_routers():
    """Retorna a lista de roteadores Cisco do Zabbix"""
    if not zabbix_api:
        return jsonify({'error': 'API do Zabbix não inicializada'}), 500
        
    try:
        routers = zabbix_api.get_cisco_routers()
        return jsonify({'routers': routers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/zabbix/flapping_events', methods=['GET'])
def get_flapping_events():
    """Retorna a lista de eventos de flapping do Zabbix"""
    if not zabbix_api:
        return jsonify({'error': 'API do Zabbix não inicializada'}), 500
        
    try:
        # Obter parâmetros da requisição
        time_from = request.args.get('time_from')
        limit = request.args.get('limit', 50, type=int)
        
        # Converter time_from para timestamp se fornecido
        if time_from:
            try:
                time_from = int(time_from)
            except ValueError:
                return jsonify({'error': 'Parâmetro time_from inválido'}), 400
        
        events = zabbix_api.get_interface_flapping_events(time_from=time_from, limit=limit)
        return jsonify({'events': events})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chatgpt/analyze_flapping', methods=['POST'])
def analyze_flapping():
    """Analisa dados de flapping com ChatGPT"""
    if not chatgpt_decision:
        return jsonify({'error': 'Módulo de decisão ChatGPT não inicializado'}), 500
        
    try:
        # Obter dados da requisição
        data = request.json
        
        if not data:
            return jsonify({'error': 'Nenhum dado fornecido'}), 400
            
        # Extrair dados de flapping e informações do roteador
        flapping_data = data.get('flapping_data')
        router_info = data.get('router_info')
        
        if not flapping_data:
            return jsonify({'error': 'Dados de flapping não fornecidos'}), 400
            
        # Analisar flapping com ChatGPT
        decision = chatgpt_decision.analyze_flapping(flapping_data, router_info)
        
        return jsonify({'decision': decision})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/ansible/shutdown_interface', methods=['POST'])
def shutdown_interface():
    """Desativa uma interface em um roteador Cisco"""
    if not ansible_automation:
        return jsonify({'error': 'Módulo de automação Ansible não inicializado'}), 500
        
    try:
        # Obter dados da requisição
        data = request.json
        
        if not data:
            return jsonify({'error': 'Nenhum dado fornecido'}), 400
            
        # Extrair parâmetros
        router = data.get('router')
        interface = data.get('interface')
        reason = data.get('reason')
        extra_vars = data.get('extra_vars')
        
        if not router or not interface:
            return jsonify({'error': 'Router e interface são obrigatórios'}), 400
            
        # Executar shutdown
        result = ansible_automation.shutdown_interface(
            router=router,
            interface=interface,
            reason=reason,
            extra_vars=extra_vars
        )
        
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/ansible/enable_interface', methods=['POST'])
def enable_interface():
    """Ativa uma interface em um roteador Cisco"""
    if not ansible_automation:
        return jsonify({'error': 'Módulo de automação Ansible não inicializado'}), 500
        
    try:
        # Obter dados da requisição
        data = request.json
        
        if not data:
            return jsonify({'error': 'Nenhum dado fornecido'}), 400
            
        # Extrair parâmetros
        router = data.get('router')
        interface = data.get('interface')
        reason = data.get('reason')
        extra_vars = data.get('extra_vars')
        
        if not router or not interface:
            return jsonify({'error': 'Router e interface são obrigatórios'}), 400
            
        # Executar ativação
        result = ansible_automation.enable_interface(
            router=router,
            interface=interface,
            reason=reason,
            extra_vars=extra_vars
        )
        
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/discovery', methods=['POST'])
def discover_devices():
    """Descobre dispositivos do Zabbix e adiciona ao inventário Ansible"""
    if not zabbix_api or not ansible_automation:
        return jsonify({'error': 'API do Zabbix ou módulo de automação Ansible não inicializados'}), 500
        
    try:
        # Obter roteadores Cisco do Zabbix
        routers = zabbix_api.get_cisco_routers()
        
        if not routers:
            return jsonify({'message': 'Nenhum roteador Cisco encontrado no Zabbix'}), 200
            
        # Converter para formato do inventário Ansible
        hosts = []
        for router in routers:
            # Obter interface principal
            main_interface = None
            for interface in router.get('interfaces', []):
                if interface.get('main') == '1':
                    main_interface = interface
                    break
            
            if not main_interface:
                continue
                
            hosts.append({
                'name': router.get('host', f"router_{router.get('hostid')}"),
                'ip': main_interface.get('ip', '')
            })
        
        # Atualizar inventário Ansible
        if hosts:
            result = ansible_automation.update_inventory(hosts)
            
            if result:
                return jsonify({
                    'success': True,
                    'message': f"{len(hosts)} roteadores adicionados ao inventário Ansible",
                    'hosts': hosts
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Falha ao atualizar inventário Ansible'
                }), 500
        else:
            return jsonify({
                'success': True,
                'message': 'Nenhum roteador válido encontrado para adicionar ao inventário'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
