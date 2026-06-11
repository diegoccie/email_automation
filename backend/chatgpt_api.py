#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify, Blueprint

# Importar módulos personalizados
from chatgpt_decision import ChatGPTDecisionMaker
from flapping_detector import FlappingDetector

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('chatgpt_api')

# Criar blueprint para API
chatgpt_bp = Blueprint('chatgpt', __name__, url_prefix='/api/chatgpt')

# Inicializar módulo de decisão
decision_maker = None

def init_decision_maker(api_key=None):
    """
    Inicializa o módulo de decisão com ChatGPT
    
    Args:
        api_key: Chave de API da OpenAI (opcional)
    """
    global decision_maker
    
    try:
        # Se api_key não for fornecido, tenta obter da variável de ambiente
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            
        if not api_key:
            logger.error("API key não fornecida e não encontrada na variável de ambiente OPENAI_API_KEY")
            return False
            
        # Inicializar módulo de decisão
        decision_maker = ChatGPTDecisionMaker(api_key=api_key)
        logger.info("Módulo de decisão ChatGPT inicializado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao inicializar módulo de decisão ChatGPT: {str(e)}")
        return False

@chatgpt_bp.route('/analyze_flapping', methods=['POST'])
def analyze_flapping():
    """
    Endpoint para análise de flapping com ChatGPT
    """
    global decision_maker
    
    # Verificar se o módulo de decisão foi inicializado
    if not decision_maker:
        return jsonify({
            "error": "Módulo de decisão ChatGPT não inicializado",
            "message": "Configure a API key da OpenAI"
        }), 500
    
    # Obter dados da requisição
    data = request.json
    
    if not data:
        return jsonify({"error": "Nenhum dado fornecido"}), 400
    
    # Extrair dados de flapping e informações do roteador
    flapping_data = data.get("flapping_data")
    router_info = data.get("router_info")
    
    if not flapping_data:
        return jsonify({"error": "Dados de flapping não fornecidos"}), 400
    
    try:
        # Analisar flapping com ChatGPT
        decision = decision_maker.analyze_flapping(flapping_data, router_info)
        
        # Adicionar timestamp
        decision["timestamp"] = datetime.now().isoformat()
        
        # Registrar decisão
        logger.info(f"Decisão para {flapping_data.get('flapping_interfaces', [])}: shutdown_recommended={decision['shutdown_recommended']}, confidence={decision['confidence']}")
        
        return jsonify({
            "status": "success",
            "decision": decision
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao analisar flapping: {str(e)}")
        return jsonify({
            "error": "Erro ao analisar flapping",
            "message": str(e)
        }), 500

@chatgpt_bp.route('/analyze_logs', methods=['POST'])
def analyze_logs():
    """
    Endpoint para análise de logs com ChatGPT
    """
    global decision_maker
    
    # Verificar se o módulo de decisão foi inicializado
    if not decision_maker:
        return jsonify({
            "error": "Módulo de decisão ChatGPT não inicializado",
            "message": "Configure a API key da OpenAI"
        }), 500
    
    # Obter dados da requisição
    data = request.json
    
    if not data:
        return jsonify({"error": "Nenhum dado fornecido"}), 400
    
    # Extrair logs e contexto
    logs = data.get("logs")
    context = data.get("context")
    
    if not logs:
        return jsonify({"error": "Logs não fornecidos"}), 400
    
    try:
        # Analisar logs com ChatGPT
        analysis = decision_maker.analyze_logs(logs, context)
        
        # Adicionar timestamp
        analysis["timestamp"] = datetime.now().isoformat()
        
        # Registrar análise
        logger.info(f"Análise de logs: issues_detected={analysis['issues_detected']}, severity={analysis['severity']}")
        
        return jsonify({
            "status": "success",
            "analysis": analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao analisar logs: {str(e)}")
        return jsonify({
            "error": "Erro ao analisar logs",
            "message": str(e)
        }), 500

@chatgpt_bp.route('/detect_flapping', methods=['POST'])
def detect_flapping():
    """
    Endpoint para detecção de flapping a partir de logs
    """
    # Obter dados da requisição
    data = request.json
    
    if not data:
        return jsonify({"error": "Nenhum dado fornecido"}), 400
    
    # Extrair logs e parâmetros
    logs = data.get("logs")
    threshold = data.get("threshold", 5)
    time_window = data.get("time_window", 300)
    interface = data.get("interface")
    
    if not logs:
        return jsonify({"error": "Logs não fornecidos"}), 400
    
    try:
        # Inicializar detector de flapping
        detector = FlappingDetector(threshold=threshold, time_window=time_window)
        
        # Detectar flapping
        if interface:
            # Analisar interface específica
            result = detector.analyze_interface(interface, logs)
        else:
            # Analisar todas as interfaces
            result = detector.analyze_logs(logs)
        
        # Adicionar timestamp
        result["timestamp"] = datetime.now().isoformat()
        
        # Registrar resultado
        logger.info(f"Detecção de flapping: flapping_detected={result['flapping_detected']}, interfaces={result.get('flapping_interfaces', [])}")
        
        return jsonify({
            "status": "success",
            "flapping_data": result
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao detectar flapping: {str(e)}")
        return jsonify({
            "error": "Erro ao detectar flapping",
            "message": str(e)
        }), 500

@chatgpt_bp.route('/set_api_key', methods=['POST'])
def set_api_key():
    """
    Endpoint para configurar a API key da OpenAI
    """
    # Obter dados da requisição
    data = request.json
    
    if not data:
        return jsonify({"error": "Nenhum dado fornecido"}), 400
    
    # Extrair API key
    api_key = data.get("api_key")
    
    if not api_key:
        return jsonify({"error": "API key não fornecida"}), 400
    
    try:
        # Inicializar módulo de decisão com a nova API key
        success = init_decision_maker(api_key)
        
        if success:
            # Salvar API key em variável de ambiente para persistência
            os.environ["OPENAI_API_KEY"] = api_key
            
            return jsonify({
                "status": "success",
                "message": "API key configurada com sucesso"
            }), 200
        else:
            return jsonify({
                "error": "Falha ao configurar API key",
                "message": "Verifique se a API key é válida"
            }), 400
        
    except Exception as e:
        logger.error(f"Erro ao configurar API key: {str(e)}")
        return jsonify({
            "error": "Erro ao configurar API key",
            "message": str(e)
        }), 500

@chatgpt_bp.route('/status', methods=['GET'])
def status():
    """
    Endpoint para verificar o status do módulo de decisão
    """
    global decision_maker
    
    # Verificar se o módulo de decisão foi inicializado
    if decision_maker:
        return jsonify({
            "status": "active",
            "model": decision_maker.model,
            "api_configured": True
        }), 200
    else:
        return jsonify({
            "status": "inactive",
            "api_configured": False,
            "message": "API key não configurada"
        }), 200

def register_blueprint(app):
    """
    Registra o blueprint na aplicação Flask
    
    Args:
        app: Aplicação Flask
    """
    app.register_blueprint(chatgpt_bp)
    logger.info("Blueprint ChatGPT registrado na aplicação Flask")
    
    # Tentar inicializar módulo de decisão
    init_decision_maker()

# Exemplo de uso direto (para testes)
if __name__ == "__main__":
    # Criar aplicação Flask
    app = Flask(__name__)
    
    # Registrar blueprint
    register_blueprint(app)
    
    # Iniciar servidor
    app.run(host="0.0.0.0", port=5000, debug=True)
