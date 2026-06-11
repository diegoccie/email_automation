// Atualizar o arquivo app.py para integrar as rotas
import os
import logging
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS

# Importar módulos personalizados
from zabbix_api import ZabbixAPI
from chatgpt_decision import ChatGPTDecisionMaker
from ansible_automation import AnsibleAutomation
from routes import api_bp, init_routes

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('backend_api')

# Criar aplicação Flask
app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas as rotas

# Configurações
app.config.update(
    ZABBIX_URL=os.environ.get('ZABBIX_URL', 'http://localhost:8080/api_jsonrpc.php'),
    ZABBIX_USER=os.environ.get('ZABBIX_USER', 'Admin'),
    ZABBIX_PASSWORD=os.environ.get('ZABBIX_PASSWORD', 'zabbix'),
    OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY', ''),
    ANSIBLE_PATH=os.environ.get('ANSIBLE_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ansible'))
)

# Inicializar componentes
zabbix_api = None
chatgpt_decision = None
ansible_automation = None

def init_components():
    """Inicializa os componentes da aplicação"""
    global zabbix_api, chatgpt_decision, ansible_automation
    
    try:
        # Inicializar API do Zabbix
        zabbix_api = ZabbixAPI(
            url=app.config['ZABBIX_URL'],
            user=app.config['ZABBIX_USER'],
            password=app.config['ZABBIX_PASSWORD']
        )
        if zabbix_api.login():
            logger.info("API do Zabbix inicializada com sucesso")
        else:
            logger.error("Falha ao inicializar API do Zabbix")
            
        # Inicializar módulo de decisão ChatGPT
        if app.config['OPENAI_API_KEY']:
            chatgpt_decision = ChatGPTDecisionMaker(api_key=app.config['OPENAI_API_KEY'])
            logger.info("Módulo de decisão ChatGPT inicializado com sucesso")
        else:
            logger.warning("API key do OpenAI não configurada, módulo de decisão ChatGPT não inicializado")
            
        # Inicializar módulo de automação Ansible
        ansible_automation = AnsibleAutomation(ansible_path=app.config['ANSIBLE_PATH'])
        logger.info("Módulo de automação Ansible inicializado com sucesso")
        
        # Inicializar rotas
        init_routes(zabbix_api, chatgpt_decision, ansible_automation)
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao inicializar componentes: {str(e)}")
        return False

# Registrar blueprint de API
app.register_blueprint(api_bp)

# Servir arquivos estáticos do frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve os arquivos estáticos do frontend"""
    if path == "" or path == "index.html":
        return render_template('index.html')
    else:
        return send_from_directory('static', path)

# Inicializar componentes ao iniciar a aplicação
@app.before_first_request
def before_first_request():
    """Inicializa componentes antes da primeira requisição"""
    init_components()

# Iniciar aplicação
if __name__ == '__main__':
    # Inicializar componentes
    init_components()
    
    # Iniciar servidor
    app.run(host='0.0.0.0', port=5000, debug=True)
