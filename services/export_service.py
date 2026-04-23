"""
Serviço de Exportação (PDF e CSV)
"""
import csv
import io
from datetime import datetime
from typing import List, Dict
from models.jogadores import Jogador

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ExportService:
    """Serviço para exportar dados em diferentes formatos"""

    @staticmethod
    def _normalizar_jogador(jogador):
        if isinstance(jogador, Jogador):
            return jogador

        if isinstance(jogador, dict):
            return Jogador.do_dict(jogador)

        nome = getattr(jogador, 'nome', str(jogador))
        nivel = getattr(jogador, 'nivel', 0)
        tipo = getattr(jogador, 'tipo', 'avulso')
        posicao = getattr(jogador, 'posicao', 'linha')
        jogador_id = getattr(jogador, 'id', None)
        criado_em = getattr(jogador, 'criado_em', None)

        return Jogador(
            nome=nome,
            nivel=nivel,
            tipo=tipo,
            posicao=posicao,
            id=jogador_id,
            criado_em=criado_em
        )

    @classmethod
    def _normalizar_time(cls, time):
        return [cls._normalizar_jogador(jogador) for jogador in time]
    
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
            time = ExportService._normalizar_time(time)
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
            time = ExportService._normalizar_time(time)
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
    def exportar_sorteio_pdf(times: List[List[Jogador]], somas: List[int], diferenca: int, sorteio_id=None) -> bytes:
        """Exporta um sorteio em PDF."""
        buffer = io.BytesIO()
        documento = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=f'Sorteio {sorteio_id or "NaTrave"}'
        )

        estilos = getSampleStyleSheet()
        estilos.add(ParagraphStyle(
            name='TituloNaTrave',
            parent=estilos['Title'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#f8f9ff'),
            spaceAfter=10,
        ))
        estilos.add(ParagraphStyle(
            name='SubtituloNaTrave',
            parent=estilos['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#9fb2d7'),
            spaceAfter=8,
        ))
        estilos.add(ParagraphStyle(
            name='TimeTitulo',
            parent=estilos['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=14,
            textColor=colors.HexColor('#f8f9ff'),
            spaceBefore=8,
            spaceAfter=6,
        ))

        elementos = []
        data_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        elementos.append(Paragraph('Resultado do Sorteio - NaTrave', estilos['TituloNaTrave']))
        if sorteio_id is not None:
            elementos.append(Paragraph(f'Sorteio #{sorteio_id} • Gerado em {data_hora}', estilos['SubtituloNaTrave']))
        else:
            elementos.append(Paragraph(f'Gerado em {data_hora}', estilos['SubtituloNaTrave']))
        elementos.append(Spacer(1, 4 * mm))

        resumo = [
            ['Times', str(len(times))],
            ['Jogadores', str(sum(len(ExportService._normalizar_time(time)) for time in times))],
            ['Diferença máxima', f'{diferenca} pts'],
        ]
        tabela_resumo = Table(resumo, colWidths=[55 * mm, 45 * mm])
        tabela_resumo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#152036')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#31405f')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#31405f')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEADING', (0, 0), (-1, -1), 13),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elementos.append(tabela_resumo)
        elementos.append(Spacer(1, 6 * mm))

        for idx, (time, soma) in enumerate(zip(times, somas), 1):
            time = ExportService._normalizar_time(time)
            elementos.append(Paragraph(f'Time {idx} - {soma} pts', estilos['TimeTitulo']))

            linhas = [['Nome', 'Nível', 'Tipo', 'Posição']]
            for jogador in time:
                linhas.append([
                    jogador.nome,
                    str(jogador.nivel),
                    'Fixo' if jogador.tipo == 'fixo' else 'Avulso',
                    'Goleiro' if jogador.posicao == 'goleiro' else 'Linha'
                ])

            tabela_time = Table(linhas, colWidths=[72 * mm, 20 * mm, 25 * mm, 25 * mm], repeatRows=1)
            tabela_time.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3a58')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#101828')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#dfe7ff')),
                ('BOX', (0, 0), (-1, -1), 0.7, colors.HexColor('#31405f')),
                ('INNERGRID', (0, 0), (-1, -1), 0.45, colors.HexColor('#31405f')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('LEADING', (0, 0), (-1, -1), 11),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elementos.append(tabela_time)
            elementos.append(Spacer(1, 5 * mm))

        elementos.append(Paragraph('Gerado por NaTrave', estilos['SubtituloNaTrave']))
        documento.build(elementos)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    
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
