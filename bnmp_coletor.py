import sqlite3
import datetime
import time
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Cidades/Comarcas Monitoradas
CIDADES_MONITORADAS = ["Maringa", "Sarandi", "Paicandu", "Curitiba", "Londrina", "Ponta Grossa", "Cascavel"]
INTERVALO_SEGUNDOS = 900  # Varredura a cada 15 minutos

# Configurações do Webhook de WhatsApp (Evolution API / Z-API / WhatsApp Web)
WHATSAPP_API_URL = "http://localhost:8080/message/sendText"
WHATSAPP_NUMERO = "5544999999999"  # Numero com DDD

DB_PATH = "monitor_bnmp_local.db"

def init_db():
    """Inicializa a base de dados SQLite local para armazenar o historico de alertas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mandados_notificados (
            id TEXT PRIMARY KEY,
            nome TEXT,
            cidade TEXT,
            unidade TEXT,
            data_hora TEXT,
            link_pdf TEXT,
            data_registro TEXT
        )
    """)
    conn.commit()
    conn.close()

def ja_notificado(item_id):
    """Verifica se o mandado ja foi notificado anteriormente."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM mandados_notificados WHERE id = ?", (item_id,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe

def salvar_mandado(item):
    """Grava o novo mandado no banco local."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mandados_notificados (id, nome, cidade, unidade, data_hora, link_pdf, data_registro)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        item['id'], item['nome'], item['cidade'], item['unidade'],
        item['data_hora'], item['link_pdf'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

def notificar_whatsapp(item):
    """Monta a mensagem de alerta formatada para envio no WhatsApp da equipe policial."""
    mensagem = (
        f"🚨 *NOVO MANDADO DETECTADO - PMPR*\n\n"
        f"👤 *Nome:* {item['nome']}\n"
        f"📜 *Nº Mandado:* {item['id']}\n"
        f"🏛️ *Comarca/Cidade:* {item['cidade']}\n"
        f"⚖️ *Orgao Expedidor:* {item['unidade']}\n"
        f"⏰ *Expedido em:* {item['data_hora']}\n\n"
        f"📄 *PDF:* {item['link_pdf']}"
    )
    logging.info(f"📲 Alerta disparado para WhatsApp ({item['cidade']}): Mandado {item['id']}")
    logging.info(f"Mensagem:\n{mensagem}")
    return True

def consultar_bnmp():
    """Simula a consulta aos lancamentos mais recentes do BNMP 3.0."""
    agora = datetime.datetime.now()
    return [
        {
            "id": "BNMP-2026-009940",
            "nome": "CARLOS EDUARDO DA SILVA",
            "cidade": "Maringa",
            "unidade": "Vara Criminal de Maringa - TJPR",
            "data_hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "link_pdf": "https://example.com/Mandado_009940.pdf"
        },
        {
            "id": "BNMP-2026-009941",
            "nome": "MARCOS VINICIUS SANTOS",
            "cidade": "Sarandi",
            "unidade": "Vara Criminal de Sarandi - TJPR",
            "data_hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "link_pdf": "https://example.com/Mandado_009941.pdf"
        }
    ]

def executar_varredura():
    """Varre as novidades, aplica o filtro por cidade e gera a notificacao."""
    mandados = consultar_bnmp()
    novos = 0
    for item in mandados:
        if item['cidade'] in CIDADES_MONITORADAS:
            if not ja_notificado(item['id']):
                salvar_mandado(item)
                notificar_whatsapp(item)
                novos += 1
    logging.info(f"Varredura concluida. Novos mandados alertados: {novos}")

def main():
    init_db()
    logging.info("🚀 Servico Coletor Backend BNMP 3.0 Ativo!")
    logging.info(f"Cidades Monitoradas: {', '.join(CIDADES_MONITORADAS)}")
    executar_varredura()

if __name__ == "__main__":
    main()
