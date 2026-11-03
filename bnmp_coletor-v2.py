import sqlite3
import datetime
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

ESTRUTURA_COMPANHIAS = {
    "1ª CIA (Cornélio Procópio)": ["Cornélio Procópio", "Leópolis", "Nova Fátima", "Uraí", "Rancho Alegre", "Sertaneja"],
    "2ª CIA (Bandeirantes)": ["Bandeirantes", "Santa Amélia", "Andirá", "Barra do Jacaré", "Itambaracá", "Santa Mariana"],
    "3ª CIA (Assaí)": ["Assaí", "Nova América da Colina", "São Sebastião da Amoreira", "Congonhinhas", "Santo Antônio do Paraíso", "São Jerônimo da Serra", "Santa Cecília do Pavão", "Nova Santa Bárbara"]
}

CIDADES_MONITORADAS = [cidade for cia, cidades in ESTRUTURA_COMPANHIAS.items() for cidade in cidades]
DB_PATH = "monitor_bnmp_local.db"

def init_db():
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM mandados_notificados WHERE id = ?", (item_id,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe

def salvar_mandado(item):
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
    mensagem = (
        f"🚨 *NOVO MANDADO DE PRISÃO DETECTADO - PMPR*\n\n"
        f"🛡️ *{item['companhia']} - Município: {item['cidade']}*\n"
        f"👤 *Nome:* {item['nome']} (CPF: {item['cpf']})\n"
        f"📜 *Nº Mandado:* {item['id']}\n"
        f"⚖️ *Órgão Expedidor:* {item['unidade']}\n"
        f"⏰ *Expedido em:* {item['data_hora']}\n\n"
        f"📄 *PDF do Mandado:* {item['link_pdf']}"
    )
    logging.info(f"📲 Alerta disparado no WhatsApp Cadastrado ({item['cidade']}): Mandado {item['id']}")
    logging.info(f"Mensagem:\n{mensagem}")
    return True

def consultar_bnmp():
    agora = datetime.datetime.now()
    return [
        {
            "id": "BNMP-2026-005841",
            "nome": "ADRIANO RODRIGUES GOMES",
            "cpf": "112.***.***-09",
            "cidade": "Cornélio Procópio",
            "companhia": "1ª CIA (Cornélio Procópio)",
            "unidade": "Vara Criminal de Cornélio Procópio - TJPR",
            "data_hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "link_pdf": "https://portalbnmp.cnj.jus.br/"
        },
        {
            "id": "BNMP-2026-005842",
            "nome": "LUCAS SILVA NASCIMENTO",
            "cpf": "077.***.***-88",
            "cidade": "Bandeirantes",
            "companhia": "2ª CIA (Bandeirantes)",
            "unidade": "Vara Criminal de Bandeirantes - TJPR",
            "data_hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "link_pdf": "https://portalbnmp.cnj.jus.br/"
        },
        {
            "id": "BNMP-2026-005843",
            "nome": "JEFFERSON MATOS FERREIRA",
            "cpf": "099.***.***-67",
            "cidade": "Congonhinhas",
            "companhia": "3ª CIA (Assaí)",
            "unidade": "Vara Criminal de Assaí / Juizado de Congonhinhas - TJPR",
            "data_hora": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "link_pdf": "https://portalbnmp.cnj.jus.br/"
        }
    ]

def executar_varredura():
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
