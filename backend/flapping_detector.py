#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time
import re
from datetime import datetime, timedelta

class FlappingDetector:
    """
    Classe para detecção de flapping em interfaces de roteadores Cisco
    """
    
    def __init__(self, threshold=5, time_window=300):
        """
        Inicializa o detector de flapping
        
        Args:
            threshold: Número mínimo de mudanças de estado para considerar flapping
            time_window: Janela de tempo em segundos para considerar flapping (padrão: 5 minutos)
        """
        self.threshold = threshold
        self.time_window = time_window
        self.logger = logging.getLogger('flapping_detector')
        
    def analyze_logs(self, logs):
        """
        Analisa logs para detectar flapping
        
        Args:
            logs: String contendo logs do roteador
            
        Returns:
            dict: Resultado da análise com informações sobre flapping
        """
        if not logs:
            return {
                "flapping_detected": False,
                "message": "Nenhum log fornecido para análise",
                "changes": 0,
                "interfaces": {}
            }
        
        # Padrão para detectar mudanças de estado em interfaces
        pattern = r'(\w+ \d+ \d+:\d+:\d+).*Interface ([^,]+), changed state to (up|down)'
        
        # Encontrar todas as ocorrências
        matches = re.findall(pattern, logs)
        
        if not matches:
            return {
                "flapping_detected": False,
                "message": "Nenhuma mudança de estado de interface encontrada nos logs",
                "changes": 0,
                "interfaces": {}
            }
        
        # Processar ocorrências
        interfaces = {}
        
        for timestamp_str, interface, state in matches:
            # Converter timestamp para objeto datetime
            try:
                # Formato típico de logs Cisco: "Apr 17 22:30:45"
                # Adicionar ano atual se não estiver presente
                if len(timestamp_str.split()) == 3:
                    current_year = datetime.now().year
                    timestamp_str = f"{timestamp_str} {current_year}"
                    timestamp = datetime.strptime(timestamp_str, "%b %d %H:%M:%S %Y")
                else:
                    # Tentar outros formatos comuns
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Se não conseguir converter, usar timestamp atual
                self.logger.warning(f"Não foi possível converter timestamp: {timestamp_str}")
                timestamp = datetime.now()
            
            # Inicializar interface se não existir
            if interface not in interfaces:
                interfaces[interface] = {
                    "changes": [],
                    "up_count": 0,
                    "down_count": 0,
                    "flapping": False
                }
            
            # Adicionar mudança de estado
            interfaces[interface]["changes"].append({
                "timestamp": timestamp,
                "state": state
            })
            
            # Incrementar contador de estado
            if state == "up":
                interfaces[interface]["up_count"] += 1
            else:
                interfaces[interface]["down_count"] += 1
        
        # Analisar flapping para cada interface
        now = datetime.now()
        time_window_start = now - timedelta(seconds=self.time_window)
        
        flapping_interfaces = []
        total_changes = 0
        
        for interface, data in interfaces.items():
            # Filtrar mudanças dentro da janela de tempo
            recent_changes = [
                change for change in data["changes"] 
                if change["timestamp"] >= time_window_start
            ]
            
            # Atualizar contagem de mudanças
            data["recent_changes"] = len(recent_changes)
            total_changes += data["recent_changes"]
            
            # Verificar se atinge o threshold de flapping
            if data["recent_changes"] >= self.threshold:
                data["flapping"] = True
                flapping_interfaces.append(interface)
                
                # Calcular frequência de flapping (mudanças por minuto)
                if self.time_window > 0:
                    data["frequency"] = (data["recent_changes"] * 60) / (self.time_window / 60)
                else:
                    data["frequency"] = 0
        
        # Resultado final
        result = {
            "flapping_detected": len(flapping_interfaces) > 0,
            "interfaces": interfaces,
            "flapping_interfaces": flapping_interfaces,
            "changes": total_changes,
            "time_window_seconds": self.time_window,
            "threshold": self.threshold,
            "timestamp": datetime.now().isoformat()
        }
        
        # Adicionar mensagem descritiva
        if result["flapping_detected"]:
            interfaces_str = ", ".join(flapping_interfaces)
            result["message"] = f"Flapping detectado nas interfaces: {interfaces_str}. {total_changes} mudanças de estado em {self.time_window/60} minutos."
        else:
            result["message"] = f"Nenhum flapping detectado. {total_changes} mudanças de estado em {self.time_window/60} minutos."
        
        return result
    
    def analyze_interface(self, interface_name, logs):
        """
        Analisa logs para uma interface específica
        
        Args:
            interface_name: Nome da interface
            logs: String contendo logs do roteador
            
        Returns:
            dict: Resultado da análise para a interface específica
        """
        # Analisar todos os logs primeiro
        result = self.analyze_logs(logs)
        
        # Filtrar apenas para a interface especificada
        if interface_name in result["interfaces"]:
            interface_data = result["interfaces"][interface_name]
            
            # Atualizar resultado para focar apenas nesta interface
            result["flapping_detected"] = interface_data["flapping"]
            result["changes"] = interface_data["recent_changes"]
            
            if interface_data["flapping"]:
                result["message"] = f"Flapping detectado na interface {interface_name}. {interface_data['recent_changes']} mudanças de estado em {self.time_window/60} minutos."
            else:
                result["message"] = f"Nenhum flapping detectado na interface {interface_name}. {interface_data['recent_changes']} mudanças de estado em {self.time_window/60} minutos."
                
            # Manter apenas a interface especificada
            result["interfaces"] = {interface_name: interface_data}
            
            if interface_data["flapping"]:
                result["flapping_interfaces"] = [interface_name]
            else:
                result["flapping_interfaces"] = []
        else:
            # Interface não encontrada nos logs
            result["flapping_detected"] = False
            result["changes"] = 0
            result["message"] = f"Interface {interface_name} não encontrada nos logs analisados"
            result["interfaces"] = {}
            result["flapping_interfaces"] = []
        
        return result

# Exemplo de uso
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Exemplo de logs
    sample_logs = """
    Apr 17 22:15:30 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down
    Apr 17 22:16:45 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up
    Apr 17 22:18:20 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down
    Apr 17 22:19:10 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up
    Apr 17 22:20:05 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down
    Apr 17 22:21:30 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up
    Apr 17 22:22:15 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/2, changed state to down
    Apr 17 22:23:45 Router-3845 %LINK-3-UPDOWN: Interface GigabitEthernet0/2, changed state to up
    """
    
    # Criar detector com threshold de 5 mudanças em 10 minutos
    detector = FlappingDetector(threshold=5, time_window=600)
    
    # Analisar logs
    result = detector.analyze_logs(sample_logs)
    
    # Exibir resultado
    print(f"Flapping detectado: {result['flapping_detected']}")
    print(f"Mensagem: {result['message']}")
    print(f"Total de mudanças: {result['changes']}")
    
    if result['flapping_interfaces']:
        print(f"Interfaces com flapping: {', '.join(result['flapping_interfaces'])}")
        
    # Analisar interface específica
    interface_result = detector.analyze_interface("GigabitEthernet0/1", sample_logs)
    print(f"\nAnálise para GigabitEthernet0/1:")
    print(f"Flapping detectado: {interface_result['flapping_detected']}")
    print(f"Mensagem: {interface_result['message']}")
