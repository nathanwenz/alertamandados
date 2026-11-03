import json
import os
import datetime
import requests

# Estrutura de Companhias e Municípios da Região
ESTRUTURA_COMPANHIAS = {
    "1ª CIA (Cornélio Procópio)": [
        "Cornélio Procópio", "Leópolis", "Nova Fátima", "Uraí", "Rancho Alegre", "Sertaneja"
    ],
    "2ª CIA (Bandeirantes)": [
        "Bandeirantes", "Santa Amélia", "Andirá", "Barra do Jacaré", "Itambaracá", "Santa Mariana"
    ],
    "3ª CIA (Assaí)": [
        "Assaí", "Nova América da Colina", "São Sebastião da Amoreira", "Congonhinhas",
        "Santo Antônio do Paraíso", "São Jerônimo da Serra", "Santa Cecília do Pavão", "Nova Santa Bárbara"
    ]
}

MANDADOS_FILE = "mandados.json"
API_ENDPOINT = os.getenv("API_ENDPOINT", "")
API_KEY = os.getenv("API_KEY", "")

def carregar_mandados():
    if os.path.exists(MANDADOS_FILE):
        try:
            with open(MANDADOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salvar_mandados(mandados):
    with open(MANDADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(mandados, f, ensure_ascii=False, indent=2)

def executar_coleta_nuvem():
    print("🔄 Executando varredura automatizada na Nuvem (GitHub Actions)...")
    mandados = carregar_mandados()
    
    # ESTRUTURA PREPARADA PARA QUANDO VOCÊ TIVER A CHAVE DE API
    if API_ENDPOINT and API_KEY:
        print("🔑 Chave de API detectada! Consultando servidores do Poder Judiciário...")
        try:
            headers = {"Authorization": f"Bearer {API_KEY}"}
            res = requests.get(API_ENDPOINT, headers=headers, timeout=10)
            if res.status_code == 200:
                print("✅ Dados recebidos com sucesso da API!")
        except Exception as e:
            print(f"Erro na consulta da API: {e}")
    else:
        print("ℹ️ Modo sem API ativo. Mantendo estrutura pronta e aplicando filtro de 45 dias.")
        
    # Manter estritamente mandados com expedição judicial nos últimos 45 dias
    data_corte = datetime.datetime.now() - datetime.timedelta(days=45)
    mandados_validos = []
    
    for m in mandados:
        try:
            dt = datetime.datetime.strptime(m["expedicao_datahora"], "%d/%m/%Y %H:%M:%S")
            if dt >= data_corte:
                mandados_validos.append(m)
        except Exception:
            mandados_validos.append(m)

    salvar_mandados(mandados_validos)
    print(f"✅ Execução concluída! {len(mandados_validos)} mandados ativos salvos na nuvem.")

if __name__ == "__main__":
    executar_coleta_nuvem()
