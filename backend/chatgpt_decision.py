#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import time
import openai
from datetime import datetime

class ChatGPTDecisionMaker:
    """
    Classe para integração com a API do ChatGPT para tomada de decisões
    sobre eventos de rede detectados pelo Zabbix
    """
    
    def __init__(self, api_key=None, model="gpt-4", temperature=0.2, max_tokens=1000):
        """
        Inicializa o módulo de decisão com ChatGPT
        
        Args:
            api_key: Chave de API da OpenAI (se None, tenta obter da variável de ambiente OPENAI_API_KEY)
            model: Modelo do ChatGPT a ser utilizado
            temperature: Temperatura para geração de texto (0.0 a 1.0)
            max_tokens: Número máximo de tokens na resposta
        """
        # Configurar API key
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("OPENAI_API_KEY")
            
        if not self.api_key:
            raise ValueError("API key não fornecida e não encontrada na variável de ambiente OPENAI_API_KEY")
            
        openai.api_key = self.api_key
        
        # Configurações do modelo
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Configurar logger
        self.logger = logging.getLogger('chatgpt_decision')
        
        # Cache para decisões recentes
        self.decision_cache = {}
        
    def analyze_flapping(self, flapping_data, router_info=None):
        """
        Analisa dados de flapping e decide se deve aplicar shutdown na interface
        
        Args:
            flapping_data: Dados de flapping da interface (dict)
            router_info: Informações adicionais sobre o roteador (opcional)
            
        Returns:
            dict: Decisão e análise do ChatGPT
        """
        # Verificar se já existe decisão em cache para este evento
        cache_key = self._generate_cache_key(flapping_data)
        if cache_key in self.decision_cache:
            self.logger.info(f"Decisão encontrada em cache para {cache_key}")
            return self.decision_cache[cache_key]
        
        # Preparar prompt para o ChatGPT
        prompt = self._prepare_flapping_prompt(flapping_data, router_info)
        
        # Enviar para o ChatGPT
        try:
            response = self._call_chatgpt_api(prompt)
            
            # Processar resposta
            decision = self._process_flapping_response(response)
            
            # Armazenar em cache
            self.decision_cache[cache_key] = decision
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Erro ao chamar API do ChatGPT: {str(e)}")
            
            # Retornar decisão padrão em caso de erro
            return {
                "shutdown_recommended": False,
                "confidence": 0.0,
                "reasoning": f"Erro ao consultar ChatGPT: {str(e)}",
                "raw_response": None,
                "timestamp": datetime.now().isoformat()
            }
    
    def _prepare_flapping_prompt(self, flapping_data, router_info=None):
        """
        Prepara o prompt para análise de flapping
        
        Args:
            flapping_data: Dados de flapping da interface
            router_info: Informações adicionais sobre o roteador
            
        Returns:
            str: Prompt formatado para o ChatGPT
        """
        # Extrair informações relevantes
        interfaces = flapping_data.get("interfaces", {})
        flapping_interfaces = flapping_data.get("flapping_interfaces", [])
        changes = flapping_data.get("changes", 0)
        time_window = flapping_data.get("time_window_seconds", 300)
        threshold = flapping_data.get("threshold", 5)
        
        # Formatar informações de interfaces
        interfaces_info = ""
        for interface_name, data in interfaces.items():
            if interface_name in flapping_interfaces:
                status = "FLAPPING"
            else:
                status = "NORMAL"
                
            up_count = data.get("up_count", 0)
            down_count = data.get("down_count", 0)
            recent_changes = data.get("recent_changes", 0)
            
            interfaces_info += f"Interface: {interface_name}\n"
            interfaces_info += f"Status: {status}\n"
            interfaces_info += f"Mudanças recentes: {recent_changes} em {time_window/60} minutos\n"
            interfaces_info += f"Transições para UP: {up_count}\n"
            interfaces_info += f"Transições para DOWN: {down_count}\n\n"
        
        # Formatar informações do roteador
        router_details = ""
        if router_info:
            router_details = f"""
Informações do Roteador:
Nome: {router_info.get('name', 'N/A')}
Modelo: {router_info.get('model', 'Cisco 3800')}
IP: {router_info.get('ip', 'N/A')}
Localização: {router_info.get('location', 'N/A')}
Importância: {router_info.get('importance', 'Normal')}
"""
        
        # Construir prompt completo
        prompt = f"""Você é um especialista em redes Cisco com foco em roteadores da série 3800 rodando IOS 15.0.

Analise os seguintes dados de flapping de interface e determine se é recomendado aplicar shutdown na(s) interface(s) afetada(s).

Resumo do Evento:
- Flapping detectado: {flapping_data.get('flapping_detected', False)}
- Total de mudanças de estado: {changes} em {time_window/60} minutos
- Threshold configurado: {threshold} mudanças
- Interfaces com flapping: {', '.join(flapping_interfaces) if flapping_interfaces else 'Nenhuma'}

{interfaces_info}

{router_details}

Baseado nessas informações, responda:

1. É recomendado aplicar shutdown na(s) interface(s) com flapping? (Sim/Não)
2. Qual seu nível de confiança nesta decisão? (0-100%)
3. Explique seu raciocínio detalhadamente.
4. Quais seriam os impactos potenciais desta ação?
5. Existe alguma ação alternativa que poderia ser considerada?

Forneça sua resposta em formato estruturado, começando com "DECISÃO: Sim" ou "DECISÃO: Não".
"""
        
        return prompt
    
    def _call_chatgpt_api(self, prompt):
        """
        Chama a API do ChatGPT com o prompt fornecido
        
        Args:
            prompt: Texto do prompt
            
        Returns:
            str: Resposta do ChatGPT
        """
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em redes Cisco com foco em análise de problemas de rede."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extrair texto da resposta
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Erro ao chamar API do ChatGPT: {str(e)}")
            raise
    
    def _process_flapping_response(self, response):
        """
        Processa a resposta do ChatGPT para extrair a decisão
        
        Args:
            response: Texto da resposta do ChatGPT
            
        Returns:
            dict: Decisão estruturada
        """
        # Valores padrão
        decision = {
            "shutdown_recommended": False,
            "confidence": 0.0,
            "reasoning": "",
            "raw_response": response,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Verificar se a resposta contém uma decisão clara
            if "DECISÃO: Sim" in response:
                decision["shutdown_recommended"] = True
            elif "DECISÃO: Não" in response:
                decision["shutdown_recommended"] = False
            else:
                # Tentar inferir a decisão do texto
                lower_response = response.lower()
                if "recomendado aplicar shutdown" in lower_response and "não" not in lower_response[:50]:
                    decision["shutdown_recommended"] = True
                elif "recomendo shutdown" in lower_response or "deve aplicar shutdown" in lower_response:
                    decision["shutdown_recommended"] = True
            
            # Extrair nível de confiança
            confidence_pattern = r'confiança[:\s]+(\d+)'
            import re
            confidence_match = re.search(confidence_pattern, response, re.IGNORECASE)
            if confidence_match:
                confidence = int(confidence_match.group(1))
                decision["confidence"] = min(confidence / 100.0, 1.0)  # Normalizar para 0-1
            
            # Extrair raciocínio
            reasoning_parts = []
            if "raciocínio" in response.lower():
                parts = response.split("raciocínio", 1)
                if len(parts) > 1:
                    reasoning_parts.append(parts[1].strip())
            
            if "explique" in response.lower():
                parts = response.split("explique", 1)
                if len(parts) > 1:
                    reasoning_parts.append(parts[1].strip())
            
            # Se não encontrou seções específicas, usar toda a resposta como raciocínio
            if not reasoning_parts:
                decision["reasoning"] = response
            else:
                decision["reasoning"] = "\n".join(reasoning_parts)
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Erro ao processar resposta do ChatGPT: {str(e)}")
            decision["reasoning"] = f"Erro ao processar resposta: {str(e)}\n\nResposta original: {response}"
            return decision
    
    def _generate_cache_key(self, flapping_data):
        """
        Gera uma chave de cache para os dados de flapping
        
        Args:
            flapping_data: Dados de flapping
            
        Returns:
            str: Chave de cache
        """
        # Extrair informações relevantes para a chave
        interfaces = sorted(flapping_data.get("flapping_interfaces", []))
        changes = flapping_data.get("changes", 0)
        timestamp = flapping_data.get("timestamp", "")
        
        # Truncar timestamp para minutos para agrupar eventos próximos
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime("%Y-%m-%d-%H-%M")
            except (ValueError, TypeError):
                timestamp = str(timestamp)[:16]
        
        # Gerar chave
        key = f"flapping_{'-'.join(interfaces)}_{changes}_{timestamp}"
        return key
    
    def analyze_logs(self, logs, context=None):
        """
        Analisa logs de roteador para identificar problemas e recomendar ações
        
        Args:
            logs: String contendo logs do roteador
            context: Informações de contexto adicionais (opcional)
            
        Returns:
            dict: Análise e recomendações do ChatGPT
        """
        # Preparar prompt para o ChatGPT
        prompt = self._prepare_logs_prompt(logs, context)
        
        # Enviar para o ChatGPT
        try:
            response = self._call_chatgpt_api(prompt)
            
            # Processar resposta
            analysis = {
                "raw_response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            # Extrair informações estruturadas da resposta
            analysis.update(self._extract_structured_data(response))
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Erro ao analisar logs com ChatGPT: {str(e)}")
            
            # Retornar análise padrão em caso de erro
            return {
                "issues_detected": False,
                "severity": "unknown",
                "analysis": f"Erro ao consultar ChatGPT: {str(e)}",
                "recommendations": [],
                "raw_response": None,
                "timestamp": datetime.now().isoformat()
            }
    
    def _prepare_logs_prompt(self, logs, context=None):
        """
        Prepara o prompt para análise de logs
        
        Args:
            logs: String contendo logs do roteador
            context: Informações de contexto adicionais
            
        Returns:
            str: Prompt formatado para o ChatGPT
        """
        # Limitar tamanho dos logs para evitar exceder limites da API
        max_log_length = 4000
        if len(logs) > max_log_length:
            logs = logs[-max_log_length:]
            logs = "...[logs anteriores omitidos]...\n" + logs
        
        # Formatar informações de contexto
        context_info = ""
        if context:
            context_info = "Informações de Contexto:\n"
            for key, value in context.items():
                context_info += f"- {key}: {value}\n"
            context_info += "\n"
        
        # Construir prompt completo
        prompt = f"""Você é um especialista em redes Cisco com foco em roteadores da série 3800 rodando IOS 15.0.

Analise os seguintes logs de roteador e identifique problemas, sua severidade e recomende ações:

{context_info}
LOGS:
{logs}

Baseado nesses logs, responda:

1. Quais problemas você identifica? Liste-os em ordem de severidade.
2. Qual a severidade geral da situação? (Crítica, Alta, Média, Baixa, Informacional)
3. Quais ações você recomenda para resolver cada problema identificado?
4. Existe algum padrão ou tendência preocupante nesses logs?

Forneça sua resposta em formato estruturado, começando com "ANÁLISE:" seguido de sua avaliação.
"""
        
        return prompt
    
    def _extract_structured_data(self, response):
        """
        Extrai dados estruturados da resposta do ChatGPT
        
        Args:
            response: Texto da resposta do ChatGPT
            
        Returns:
            dict: Dados estruturados extraídos
        """
        data = {
            "issues_detected": False,
            "severity": "unknown",
            "analysis": "",
            "recommendations": []
        }
        
        try:
            # Verificar se foram detectados problemas
            lower_response = response.lower()
            if "nenhum problema" in lower_response or "não identifiquei problemas" in lower_response:
                data["issues_detected"] = False
                data["severity"] = "informacional"
            else:
                data["issues_detected"] = True
            
            # Extrair severidade
            severity_mapping = {
                "crítica": "critical",
                "alta": "high",
                "média": "medium",
                "baixa": "low",
                "informacional": "informational"
            }
            
            for pt, en in severity_mapping.items():
                if pt in lower_response:
                    data["severity"] = en
                    break
            
            # Extrair análise
            if "análise:" in lower_response:
                parts = response.split("análise:", 1)
                if len(parts) > 1:
                    data["analysis"] = parts[1].strip()
            else:
                data["analysis"] = response
            
            # Extrair recomendações
            recommendations = []
            if "recomend" in lower_response or "ações" in lower_response:
                # Tentar encontrar lista numerada de recomendações
                import re
                rec_pattern = r'\d+\.\s+([^\n]+)'
                rec_matches = re.findall(rec_pattern, response)
                
                if rec_matches:
                    recommendations = rec_matches
                else:
                    # Tentar encontrar seção de recomendações
                    if "recomendações:" in lower_response:
                        parts = response.split("recomendações:", 1)
                        if len(parts) > 1:
                            rec_text = parts[1].strip()
                            recommendations = [line.strip() for line in rec_text.split("\n") if line.strip()]
            
            data["recommendations"] = recommendations
            
            return data
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair dados estruturados: {str(e)}")
            data["analysis"] = response
            return data

# Exemplo de uso
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Inicializar módulo de decisão
    # Substitua 'sua-api-key' pela chave real ou configure a variável de ambiente OPENAI_API_KEY
    decision_maker = ChatGPTDecisionMaker(api_key="sua-api-key")
    
    # Exemplo de dados de flapping
    flapping_data = {
        "flapping_detected": True,
        "interfaces": {
            "GigabitEthernet0/1": {
                "changes": [
                    {"timestamp": datetime.now(), "state": "down"},
                    {"timestamp": datetime.now(), "state": "up"}
                ],
                "up_count": 3,
                "down_count": 3,
                "flapping": True,
                "recent_changes": 6
            }
        },
        "flapping_interfaces": ["GigabitEthernet0/1"],
        "changes": 6,
        "time_window_seconds": 300,
        "threshold": 5,
        "timestamp": datetime.now().isoformat(),
        "message": "Flapping detectado na interface GigabitEthernet0/1. 6 mudanças de estado em 5 minutos."
    }
    
    # Informações do roteador
    router_info = {
        "name": "Router-3845",
        "model": "Cisco 3845",
        "ip": "192.168.1.1",
        "location": "Datacenter Principal",
        "importance": "Crítico"
    }
    
    # Analisar flapping
    decision = decision_maker.analyze_flapping(flapping_data, router_info)
    
    # Exibir decisão
    print(f"Shutdown recomendado: {decision['shutdown_recommended']}")
    print(f"Confiança: {decision['confidence'] * 100:.0f}%")
    print(f"Raciocínio: {decision['reasoning']}")
    
    # Exemplo de análise de logs
    sample_logs = """
    Apr 17 22:15:30 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down
    Apr 17 22:16:45 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up
    Apr 17 22:18:20 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down
    Apr 17 22:19:10 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up
    Apr 17 22:20:05 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down
    Apr 17 22:21:30 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up
    Apr 17 22:22:15 Router-3845 %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to down
    Apr 17 22:23:45 Router-3845 %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to up
    """
    
    # Analisar logs
    log_analysis = decision_maker.analyze_logs(sample_logs, context=router_info)
    
    # Exibir análise
    print("\nAnálise de Logs:")
    print(f"Problemas detectados: {log_analysis['issues_detected']}")
    print(f"Severidade: {log_analysis['severity']}")
    print(f"Análise: {log_analysis['analysis']}")
    
    if log_analysis['recommendations']:
        print("\nRecomendações:")
        for i, rec in enumerate(log_analysis['recommendations'], 1):
            print(f"{i}. {rec}")
