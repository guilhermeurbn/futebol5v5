"""
Serviço de Exportação (PDF e CSV)
"""
import csv
import io
from datetime import datetime
from typing import List, Dict
from models.jogadores import Jogador


class ExportService:
    """Serviço para exportar dados em diferentes formatos"""
    
    @staticmethod
    def exportar_sorteio_csv(times: List[List[Jogador]], somas: List[int], diferenca: int) -> str:
        """
        Exporta um sorteio em formato CSV
        
        Returns:
            String CSV
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Sorteio de Times', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
        writer.writerow([''])
        writer.writerow(['Resumo', ''])
        writer.writerow(['Número de Times:', len(times)])
        writer.writerow(['Total de Jogadores:', sum(len(time) for time in times)])
        writer.writerow(['Diferença Máxima:', f'{diferenca} pts'])
        writer.writerow([''])
        
        # Times
        for idx, (time, soma) in enumerate(zip(times, somas), 1):
            writer.writerow([f'TIME {idx} ({soma} pts)', ''])
            writer.writerow(['Nome', 'Nível', 'Tipo', 'Posição'])
            
            for jogador in time:
                writer.writerow([
                    jogador.nome,
                    jogador.nivel,
                    jogador.tipo,
                    jogador.posicao
                ])
            
            writer.writerow([''])
        
        return output.getvalue()
    
    @staticmethod
    def exportar_historico_csv(sorteios: List[Dict]) -> str:
        """
        Exporta histórico de sorteios em CSV
        
        Returns:
            String CSV
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Histórico de Sorteios', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
        writer.writerow([''])
        writer.writerow(['ID', 'Data', 'Jogadores', 'Times', 'Diferença', 'Melhor Time'])
        
        # Dados
        for sorteio in sorteios:
            data = sorteio.get('data', '')
            if data:
                # Converter ISO format para formato brasileiro
                try:
                    data_obj = datetime.fromisoformat(data)
                    data = data_obj.strftime('%d/%m/%Y %H:%M:%S')
                except:
                    pass
            
            # Encontrar melhor time
            pontuacoes = sorteio.get('pontuacoes', [])
            if pontuacoes:
                melhor_idx = pontuacoes.index(max(pontuacoes))
                melhor_time = f"Time {melhor_idx + 1}"
            else:
                melhor_time = "-"
            
            writer.writerow([
                sorteio.get('id', ''),
                data,
                sorteio.get('total_jogadores', ''),
                sorteio.get('num_times', ''),
                sorteio.get('diferenca', ''),
                melhor_time
            ])
        
        return output.getvalue()
    
    @staticmethod
    def exportar_sorteio_texto(times: List[List[Jogador]], somas: List[int], diferenca: int) -> str:
        """
        Exporta um sorteio em formato texto simples
        
        Returns:
            String em texto
        """
        linhas = []
        linhas.append("=" * 60)
        linhas.append("⚽ RESULTADO DO SORTEIO - NaTrave")
        linhas.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        linhas.append("=" * 60)
        linhas.append("")
        
        linhas.append("📊 RESUMO")
        linhas.append(f"  • Número de times: {len(times)}")
        linhas.append(f"  • Total de jogadores: {sum(len(time) for time in times)}")
        linhas.append(f"  • Diferença máxima: {diferenca} pts")
        linhas.append("")
        
        for idx, (time, soma) in enumerate(zip(times, somas), 1):
            linhas.append(f"⚽ TIME {idx} ({soma} pts)")
            linhas.append("-" * 40)
            
            # Contar goleiros
            goleiros = [j for j in time if j.posicao == 'goleiro']
            linha = [j for j in time if j.posicao == 'linha']
            
            for jogador in time:
                icon = "🧤" if jogador.posicao == 'goleiro' else "⚽"
                tipo = "Fixo" if jogador.tipo == 'fixo' else "Avulso"
                linhas.append(f"  {icon} {jogador.nome:20} | Nível {jogador.nivel} | {tipo}")
            
            linhas.append("")
        
        linhas.append("=" * 60)
        linhas.append("Gerado por NaTrave - https://github.com/guilhermeurbn/futebol5v5")
        
        return "\n".join(linhas)
    
    @staticmethod
    def exportar_estatisticas_csv(stats: Dict) -> str:
        """
        Exporta estatísticas em CSV
        
        Returns:
            String CSV
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Estatísticas Gerais', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
        writer.writerow([''])
        
        # Dados gerais
        writer.writerow(['Total de Sorteios:', stats.get('total_sorteios', 0)])
        writer.writerow(['Média de Jogadores por Sorteio:', stats.get('media_jogadores', 0)])
        writer.writerow(['Média de Diferença:', stats.get('media_diferenca', 0)])
        writer.writerow(['Melhor Balanceamento:', stats.get('melhor_balanceamento', '-')])
        writer.writerow(['Pior Balanceamento:', stats.get('pior_balanceamento', '-')])
        writer.writerow([''])
        
        # Jogadores frequentes
        writer.writerow(['Jogadores Mais Frequentes', ''])
        writer.writerow(['Nome', 'Vezes'])
        
        for jogador in stats.get('jogadores_frequentes', []):
            writer.writerow([
                jogador.get('nome', ''),
                jogador.get('vezes', '')
            ])
        
        return output.getvalue()
