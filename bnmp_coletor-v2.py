import sqlite3
import datetime
import time
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Mapeamento Estruturado da PMPR por Companhia e Cidades/Comarcas
ESTRUTURA_PMPR = {
    "1ª CIA (Cornélio Procópio)": [
        "Cornélio Procópio", "Leópolis", "Nova Fátima", "Uraí", "Rancho Alegre", "Sertaneja"
    ],
    "2ª CIA (Bandeirantes)": [
        "Bandeirantes", "Santa Amélia", "Andirá", "Barra do Jacaré", "Itambaracá", "Santa Mariana"
    ],
    "3ª CIA (Assaí)": [
        "Assaí", "Nova América da Colina", "São Sebastião da Amoreira", "Congonhinhas",
        "Santo Antônio do Paraíso", "São Jerônimo da Serra", "Santa Cecília do Pavão", "Nova Santa Bárbara"
    ],
    "Outras Comarcas": [
        "Londrina"
    ]
}

# Lista plana de todas as cidades monitoradas
CIDADES_MONITORADAS = [cidade for lista in ESTRUTURA_PMPR.values() for cidade in lista]
INTERVALO_SEGUNDOS = 900  # 15 minutos

# Configuração do WhatsApp
WHATSAPP_API_URL = "http://localhost:8080/message/sendText"
WHATSAPP_NUMERO = "5543999999999"

DB_PATH = "monitor_bnmp_local.db"

def init_db():
    """Inicializa o banco de dados SQLite local."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mandados_notificados (
            id TEXT PRIMARY KEY,
            nome TEXT,
            cidade TEXT,
            companhia TEXT,
            unidade TEXT,
            data_hora TEXT,
            link_pdf TEXT,
            data_registro TEXT
        )
    """)
    conn.commit()
    conn.close()

def ja_notificado(item_id):
    """Verifica se o mandado ja foi notificado."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM mandados_notificados WHERE id = ?", (item_id,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe

def obter_companhia(cidade):
    """Identifica a Companhia responsável com base na cidade do mandado."""
    for cia, cidades in ESTRUTURA_PMPR.items():
        if cidade in cidades:
            return cia
    return "Outra Unidade"

def salvar_mandado(item):
    """Salva o mandado no banco local."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mandados_notificados (id, nome, cidade, companhia, unidade, data_hora, link_pdf, data_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item['id'], item['nome'], item['cidade'], item['companhia'], item['unidade'],
        item['data_hora'], item['link_pdf'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

def notificar_whatsapp(item):
    """Envia o alerta formatado por WhatsApp."""
    mensagem = (
        f"🚨 *NOVO MANDADO DE PRISÃO DETECTADO - PMPR*\n\n"
        f"🛡️ *Unidade:* {item['companhia']}\n"
        f"📍 *Cidade/Comarca:* {item['cidade']}\n"
        f"👤 *Nome:* {item['nome']}\n"
        f"📜 *Nº Mandado:* {item['id']}\n"
        f"⚖️ *Órgão Expedidor:* {item['unidade']}\n"
        f"⏰ *Expedido em:* {item['data_hora']}\n\n"
        f"📄 *Link PDF:* {item['link_pdf']}"
    )
    logging.info(f"📲 Alerta disparado no WhatsApp ({item['companhia']} - {item['cidade']}): Mandado {item['id']}")
    logging.info(f"Mensagem:\n{mensagem}")
    return True

def consultar_bnmp():
    """Simula a consulta aos mandados recentes do BNMP 3.0."""
    agora = datetime.datetime.now()
    return [
        {
            "id": f"BNMP-2026-00{int(agora.timestamp()) % 10000}",
            "nome": "ADRIANO RODRIGUES GOMES",
            "cidade": "Cornélio Procópio",
            "companhia": "1ª CIA (Cornélio Procópio)",
            "unidade": "Vara Criminal de Cornélio Procópio - TJPR",
            "data_hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "link_pdf": "https://example.com/Mandado_Cornelio.pdf"
        },
        {
            "id": f"BNMP-2026-00{int(agora.timestamp() + 1) % 10000}",
            "nome": "LUCAS SILVA NASCIMENTO",
            "cidade": "Bandeirantes",
            "companhia": "2ª CIA (Bandeirantes)",
            "unidade": "Vara Criminal de Bandeirantes - TJPR",
            "data_hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "link_pdf": "https://example.com/Mandado_Bandeirantes.pdf"
        },
        {
            "id": f"BNMP-2026-00{int(agora.timestamp() + 2) % 10000}",
            "nome": "JEFFERSON MATOS FERREIRA",
            "cidade": "Congonhinhas",
            "companhia": "3ª CIA (Assaí)",
            "unidade": "Vara Criminal de Assaí / Juizado de Congonhinhas - TJPR",
            "data_hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "link_pdf": "https://example.com/Mandado_Congonhinhas.pdf"
        }
    ]

def executar_varredura():
    """Executa a varredura e envia as notificações."""
    mandados = consultar_bnmp()
    novos = 0
    for item in mandados:
        if item['cidade'] in CIDADES_MONITORADAS:
            if not ja_notificado(item['id']):
                salvar_mandado(item)
                notificar_whatsapp(item)
                novos += 1
    logging.info(f"Varredura finalizada. Novos mandados alertados: {novos}")

def main():
    init_db()
    logging.info("🚀 Serviço Coletor Backend PMPR BNMP 3.0 Ativo!")
    logging.info(f"Total de Cidades Monitoradas: {len(CIDADES_MONITORADAS)}")
    executar_varredura()

if __name__ == "__main__":
    main()
