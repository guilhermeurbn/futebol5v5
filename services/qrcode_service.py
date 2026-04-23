"""
Serviço de Compartilhamento com QR Code
"""
import qrcode
import base64
import json
import io
from typing import Dict, Tuple


class QRCodeService:
    """Serviço para gerar QR codes de sorteios"""
    
    @staticmethod
    def gerar_qr_sorteio(sorteio_data: Dict, url_base: str = "http://localhost:5001") -> Tuple[str, bytes]:
        """
        Gera QR code de um sorteio
        
        Args:
            sorteio_data: Dados do sorteio (times, somas, etc)
            url_base: URL base da aplicação
            
        Returns:
            Tupla (url_compartilhamento, qr_code_bytes)
        """
        # Codificar dados em Base64
        dados_json = json.dumps(sorteio_data, ensure_ascii=False)
        dados_b64 = base64.b64encode(dados_json.encode()).decode()
        
        # URL de compartilhamento
        url_compartilhamento = f"{url_base}/compartilhado?sorteio={dados_b64}"
        
        # Gerar QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url_compartilhamento)
        qr.make(fit=True)
        
        # Converter para imagem PIL
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return url_compartilhamento, img_bytes.getvalue()
    
    @staticmethod
    def gerar_qr_string(texto: str) -> bytes:
        """
        Gera QR code de um texto simples
        
        Args:
            texto: Texto a ser codificado
            
        Returns:
            Bytes da imagem PNG do QR code
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(texto)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
    
    @staticmethod
    def decodificar_sorteio(dados_b64: str) -> Dict:
        """
        Decodifica dados de sorteio de Base64
        
        Args:
            dados_b64: String em Base64
            
        Returns:
            Dicionário com dados do sorteio
        """
        try:
            dados_json = base64.b64decode(dados_b64).decode()
            return json.loads(dados_json)
        except Exception as e:
            raise ValueError(f"Erro ao decodificar sorteio: {str(e)}")
    
    @staticmethod
    def gerar_link_compartilhamento(sorteio_id: int, url_base: str = "http://localhost:5001") -> str:
        """
        Gera link de compartilhamento simples (sem QR code)
        
        Args:
            sorteio_id: ID do sorteio
            url_base: URL base da aplicação
            
        Returns:
            URL de compartilhamento
        """
        return f"{url_base}/sorteio/{sorteio_id}"
    
    @staticmethod
    def gerar_string_compartilhamento(times: list, somas: list) -> str:
        """
        Gera uma string de texto para compartilhamento em texto
        
        Args:
            times: Lista de times com jogadores
            somas: Lista de pontuações
            
        Returns:
            String formatada
        """
        linhas = ["⚽ SORTEIO DE TIMES - NaTrave\n"]
        
        for idx, (time, soma) in enumerate(zip(times, somas), 1):
            linhas.append(f"Time {idx} ({soma} pts):")
            for jogador in time:
                icon = "🧤" if jogador.get('posicao') == 'goleiro' else "⚽"
                nome = jogador.get('nome', 'Jogador')
                nivel = jogador.get('nivel', 5)
                linhas.append(f"  {icon} {nome} (N{nivel})")
            linhas.append("")
        
        return "\n".join(linhas)
