import datetime
import json
import os
import re
import io
import unicodedata
import pandas as pd
import streamlit as st

# Configuração da página no Streamlit
st.set_page_config(
    page_title="Monitor BNMP 3.0 - PMPR",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização visual customizada
st.markdown("""
<style>
    .titulo-principal {
        font-size: 24px;
        font-weight: bold;
        color: #1E3A8A;
        border-bottom: 2px solid #1E3A8A;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .card-mandado {
        background-color: #F8FAFC;
        border-left: 6px solid #1E40AF;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .badge-cidade {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: bold;
    }
    .badge-cia {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: bold;
        margin-right: 5px;
    }
    .badge-status {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: bold;
    }
    .caixa-mandado {
        background-color: #FEF9C3;
        border: 1px solid #FDE047;
        padding: 8px 12px;
        border-radius: 6px;
        font-family: monospace;
        font-weight: bold;
        color: #854D0E;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Estrutura Organizacional Hierárquica da PMPR (Companhia -> Comarcas Sedes -> Municípios)
ESTRUTURA_COMPANHIAS = {
    "1ª CIA (Cornélio Procópio)": {
        "Cornélio Procópio": ["Cornélio Procópio", "Leópolis", "Rancho Alegre"],
        "Uraí": ["Uraí", "Nova Fátima", "Sertaneja"]
    },
    "2ª CIA (Bandeirantes)": {
        "Bandeirantes": ["Bandeirantes", "Santa Amélia", "Santa Mariana"],
        "Andirá": ["Andirá", "Barra do Jacaré", "Itambaracá"]
    },
    "3ª CIA (Assaí)": {
        "Assaí": ["Assaí", "Nova América da Colina", "São Sebastião da Amoreira"],
        "Congonhinhas": ["Congonhinhas", "Santo Antônio do Paraíso"],
        "São Jerônimo da Serra": ["São Jerônimo da Serra", "Santa Cecília do Pavão", "Nova Santa Bárbara"]
    },
    "Outras Comarcas (Paraná)": {
        "Outras Comarcas": [
            "Londrina", "Maringá", "Curitiba", "Ponta Grossa", "Jacarezinho", "Santo Antônio da Platina",
            "Cascavel", "Foz do Iguaçu", "Guarapuava", "Toledo", "Apucarana", "Arapongas", "Campo Mourão"
        ]
    }
}

ARQUIVO_DADOS = "mandados.json"

def remover_acentos(texto):
    if not texto:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")

MAPA_NORMALIZACAO_MUNICIPIOS = {}
MAPA_MUNICIPIO_PARA_COMARCA = {}
MAPA_COMARCA_PARA_CIA = {}

for cia_key, comarcas_dict in ESTRUTURA_COMPANHIAS.items():
    if isinstance(comarcas_dict, dict):
        for comarca_key, cidades_list in comarcas_dict.items():
            MAPA_COMARCA_PARA_CIA[comarca_key] = cia_key
            MAPA_COMARCA_PARA_CIA[comarca_key.lower()] = cia_key
            MAPA_COMARCA_PARA_CIA[remover_acentos(comarca_key.lower())] = cia_key
            for c in cidades_list:
                c_clean = remover_acentos(c.lower())
                MAPA_NORMALIZACAO_MUNICIPIOS[c.lower()] = c
                MAPA_NORMALIZACAO_MUNICIPIOS[c_clean] = c
                MAPA_MUNICIPIO_PARA_COMARCA[c] = comarca_key
                MAPA_MUNICIPIO_PARA_COMARCA[c.lower()] = comarca_key
                MAPA_MUNICIPIO_PARA_COMARCA[c_clean] = comarca_key
    elif isinstance(comarcas_dict, list):
        for c in comarcas_dict:
            c_clean = remover_acentos(c.lower())
            MAPA_NORMALIZACAO_MUNICIPIOS[c.lower()] = c
            MAPA_NORMALIZACAO_MUNICIPIOS[c_clean] = c
            MAPA_MUNICIPIO_PARA_COMARCA[c] = c
            MAPA_COMARCA_PARA_CIA[c] = cia_key

def normalizar_municipio(nome_raw):
    if not nome_raw or pd.isna(nome_raw):
        return "Outras Comarcas"
    raw = str(nome_raw).strip()
    raw_clean = remover_acentos(raw.lower())
    if raw_clean in MAPA_NORMALIZACAO_MUNICIPIOS:
        return MAPA_NORMALIZACAO_MUNICIPIOS[raw_clean]
    for key, oficial in MAPA_NORMALIZACAO_MUNICIPIOS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', raw_clean):
            return oficial
    return raw

def identificar_comarca_e_cia(texto_mencionado):
    if not texto_mencionado or pd.isna(texto_mencionado):
        return "Outras Comarcas", "Outras Comarcas (Paraná)"
    
    txt_clean = remover_acentos(str(texto_mencionado).lower())
    
    for m_key, m_oficial in MAPA_NORMALIZACAO_MUNICIPIOS.items():
        if re.search(r'\b' + re.escape(m_key) + r'\b', txt_clean):
            comarca = MAPA_MUNICIPIO_PARA_COMARCA.get(m_oficial, "Outras Comarcas")
            cia = MAPA_COMARCA_PARA_CIA.get(comarca, "Outras Comarcas (Paraná)")
            return m_oficial, cia

    for com_key, cia_val in MAPA_COMARCA_PARA_CIA.items():
        if re.search(r'\b' + re.escape(remover_acentos(com_key.lower())) + r'\b', txt_clean):
            return com_key, cia_val

    return "Outras Comarcas", "Outras Comarcas (Paraná)"

def identificar_coluna_data_expedicao(colunas):
    cols_clean = {c: remover_acentos(str(c).lower().strip()) for c in colunas}
    for col_orig, c_clean in cols_clean.items():
        if any(kw in c_clean for kw in ['nascimento', 'nasc', 'cumprimento', 'baixa', 'validade']):
            continue
        if any(kw in c_clean for kw in ['dataexpedicao', 'data de expedicao', 'dt_expedicao', 'data_expedicao', 'data expedicao', 'data emissao', 'data_emissao', 'data da peca', 'dt_emissao']):
            return col_orig
    for col_orig, c_clean in cols_clean.items():
        if any(kw in c_clean for kw in ['nascimento', 'nasc', 'cumprimento', 'baixa', 'validade']):
            continue
        if 'expedicao' in c_clean or 'emissao' in c_clean or 'datahora' in c_clean:
            return col_orig
    for col_orig, c_clean in cols_clean.items():
        if any(kw in c_clean for kw in ['nascimento', 'nasc', 'cumprimento', 'baixa', 'validade']):
            continue
        if 'data' in c_clean or 'dt' in c_clean:
            return col_orig
    return None

def extrair_data_e_timestamp(valor_raw):
    if not valor_raw or pd.isna(valor_raw):
        return "Não informada", 0.0

    if isinstance(valor_raw, (pd.Timestamp, datetime.datetime)):
        exp_str = valor_raw.strftime("%d/%m/%Y %H:%M:%S") if valor_raw.hour or valor_raw.minute else valor_raw.strftime("%d/%m/%Y")
        return exp_str, float(valor_raw.timestamp())

    val_str = str(valor_raw).strip()
    val_sem_cnj = re.sub(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', '', val_str)

    dt_obj = None
    padroes_dt = [
        r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',
        r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})',
        r'(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}-\d{2}-\d{4})'
    ]

    for p in padroes_dt:
        match = re.search(p, val_sem_cnj)
        if match:
            s = match.group(1).replace('T', ' ')
            for fmt in ["%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    dt_obj = datetime.datetime.strptime(s, fmt)
                    break
                except Exception:
                    continue
            if dt_obj:
                break

    if dt_obj:
        exp_formatted = dt_obj.strftime("%d/%m/%Y %H:%M:%S") if dt_obj.hour or dt_obj.minute else dt_obj.strftime("%d/%m/%Y")
        return exp_formatted, float(dt_obj.timestamp())

    return "Não informada", 0.0

def carregar_mandados_salvos():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    clean_list = []
                    for item in dados:
                        if isinstance(item, dict):
                            c_norm, cia_norm = identificar_comarca_e_cia(item.get("orgao_expedidor", "") + " " + item.get("comarca", ""))
                            if c_norm == "Outras Comarcas":
                                c_norm = normalizar_municipio(item.get("comarca", ""))
                                cia_norm = MAPA_COMARCA_PARA_CIA.get(MAPA_MUNICIPIO_PARA_COMARCA.get(c_norm, "Outras Comarcas"), "Outras Comarcas (Paraná)")
                            
                            dt_str, ts_val = extrair_data_e_timestamp(item.get("expedicao_datahora", ""))
                            if ts_val == 0.0 and item.get("timestamp"):
                                ts_val = float(item.get("timestamp", 0.0))
                            
                            item["comarca"] = c_norm
                            item["companhia"] = cia_norm
                            item["expedicao_datahora"] = dt_str if dt_str != "Não informada" else item.get("expedicao_datahora", "Não informada")
                            item["timestamp"] = ts_val
                            clean_list.append(item)
                    return clean_list
                return []
        except Exception:
            return []
    return []

def salvar_mandados_disco(lista_mandados):
    try:
        limpos = []
        for item in lista_mandados:
            if isinstance(item, dict):
                c_norm = normalizar_municipio(item.get("comarca", ""))
                cia_norm = MAPA_COMARCA_PARA_CIA.get(MAPA_MUNICIPIO_PARA_COMARCA.get(c_norm, "Outras Comarcas"), "Outras Comarcas (Paraná)")
                limpos.append({
                    "id": str(item.get("id", "")),
                    "nome": str(item.get("nome", "NÃO INFORMADO")),
                    "cpf": str(item.get("cpf", "000.***.***-00")),
                    "comarca": str(c_norm),
                    "companhia": str(cia_norm),
                    "orgao_expedidor": str(item.get("orgao_expedidor", "Vara Criminal da Comarca")),
                    "expedicao_datahora": str(item.get("expedicao_datahora", "Não informada")),
                    "timestamp": float(item.get("timestamp", 0.0)),
                    "situacao": str(item.get("situacao", "Pendente de Cumprimento")),
                    "pdf_url": str(item.get("pdf_url", "https://portalbnmp.cnj.jus.br/#/pesquisa-peca"))
                })
        with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
            json.dump(limpos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar dados no disco: {e}")

def recarregar_app():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# Inicialização segura do Session State
if 'estruturas' not in st.session_state:
    st.session_state.estruturas = ESTRUTURA_COMPANHIAS

if 'mandados' not in st.session_state:
    st.session_state.mandados = carregar_mandados_salvos()

def processar_texto_importado(texto_bruto):
    linhas = [l.strip() for l in texto_bruto.splitlines() if l.strip()]
    novos_mandados = []
    
    eh_pipe = any('|' in l for l in linhas)
    blocos_dados = []
    
    if eh_pipe:
        for l in linhas:
            if '|' in l:
                partes = [p.strip() for p in l.split('|')]
                if len(partes) >= 2:
                    blocos_dados.append({
                        'id': partes[0] if len(partes) > 0 else '',
                        'nome': partes[1] if len(partes) > 1 else '',
                        'cpf': partes[2] if len(partes) > 2 else '',
                        'cidade': partes[3] if len(partes) > 3 else '',
                        'orgao': partes[4] if len(partes) > 4 else '',
                        'data': partes[5] if len(partes) > 5 else ''
                    })
    else:
        current_record = {}
        for l in linhas:
            id_match = re.search(r'([A-Z0-9\.\-\/]{10,}(?:BNMP|\d{4}-\d+|\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}))', l, re.IGNORECASE)
            cpf_match = re.search(r'(\d{3}\.[\*\d]{3}\.[\*\d]{3}-\d{2})', l)
            data_match = re.search(r'(\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?)', l)
            
            if id_match and 'id' in current_record:
                blocos_dados.append(current_record)
                current_record = {}
                
            if id_match and 'id' not in current_record:
                current_record['id'] = id_match.group(1)
            
            if cpf_match:
                current_record['cpf'] = cpf_match.group(1)
                
            if data_match and 'data' not in current_record:
                current_record['data'] = data_match.group(1)
                
            c_detectada, cia_detectada = identificar_comarca_e_cia(l)
            if c_detectada != "Outras Comarcas" and 'cidade' not in current_record:
                current_record['cidade'] = c_detectada
                
            if ('vara' in l.lower() or 'juizado' in l.lower() or 'comarca' in l.lower() or 'tribunal' in l.lower() or 'tjpr' in l.lower()) and 'orgao' not in current_record:
                current_record['orgao'] = l
                
            if 'nome' not in current_record and not id_match and not cpf_match and not data_match:
                if l == l.upper() and len(l.split()) >= 2 and not any(kw in l.lower() for kw in ['mandado', 'prisão', 'peça', 'órgão', 'expedidor', 'município', 'situação', 'pendente', 'tribunal', 'vara']):
                    current_record['nome'] = l

        if current_record:
            blocos_dados.append(current_record)
            
    for b in blocos_dados:
        mandado_id = str(b.get('id', '')).strip()
        if not mandado_id:
            continue
            
        nome = str(b.get('nome', '')).strip() or "NÃO INFORMADO"
        cpf = str(b.get('cpf', '')).strip() or "000.***.***-00"
        orgao = str(b.get('orgao', '')).strip() or "Vara Criminal da Comarca"
        
        expedicao_raw = b.get('data', '')
        expedicao_str, ts_val = extrair_data_e_timestamp(expedicao_raw)
        
        cidade_bruta = b.get('cidade', '')
        cidade, cia = identificar_comarca_e_cia(orgao + " " + cidade_bruta)
        if cidade == "Outras Comarcas":
            cidade = normalizar_municipio(cidade_bruta)
            cia = MAPA_COMARCA_PARA_CIA.get(MAPA_MUNICIPIO_PARA_COMARCA.get(cidade, "Outras Comarcas"), "Outras Comarcas (Paraná)")

        if not any(m['id'] == mandado_id for m in st.session_state.mandados) and not any(m['id'] == mandado_id for m in novos_mandados):
            item = {
                "id": str(mandado_id),
                "nome": str(nome).upper(),
                "cpf": str(cpf),
                "comarca": str(cidade),
                "companhia": str(cia),
                "orgao_expedidor": str(orgao),
                "expedicao_datahora": str(expedicao_str),
                "timestamp": float(ts_val),
                "situacao": "Pendente de Cumprimento",
                "pdf_url": "https://portalbnmp.cnj.jus.br/#/pesquisa-peca"
            }
            novos_mandados.append(item)
            
    if novos_mandados:
        st.session_state.mandados.extend(novos_mandados)
        salvar_mandados_disco(st.session_state.mandados)
        return len(novos_mandados)
    return 0

def processar_dataframe_importado(df):
    if df is None or df.empty:
        return 0
        
    cols_map = {}
    cols_clean = [remover_acentos(str(c).lower().strip()) for c in df.columns]
    
    # 1. Identificar coluna de ID / Mandado
    for orig, c in zip(df.columns, cols_clean):
        if any(k in c for k in ['no mandado', 'num_mandado', 'numero_mandado', 'n_mandado', 'no do mandado', 'numero do mandado', 'numeropeca', 'peca']) or c in ['id', 'mandado', 'numero']:
            cols_map['id'] = orig
            break

    # 2. Identificar coluna de Nome
    for orig, c in zip(df.columns, cols_clean):
        if 'nome' in c or 'procurado' in c or 'individuo' in c or 'pessoa' in c:
            cols_map['nome'] = orig
            break

    # 3. Identificar coluna de CPF
    for orig, c in zip(df.columns, cols_clean):
        if 'cpf' in c:
            cols_map['cpf'] = orig
            break

    # 4. Identificar coluna de Órgão Expedidor
    for orig, c in zip(df.columns, cols_clean):
        if 'orgao' in c or 'expedidor' in c or 'vara' in c or 'juizado' in c:
            cols_map['orgao'] = orig
            break

    # 5. Identificar coluna de Comarca / Cidade
    for orig, c in zip(df.columns, cols_clean):
        if 'comarca' in c or 'municipio' in c or 'cidade' in c or 'jurisdicao' in c:
            if cols_map.get('orgao') != orig:
                cols_map['comarca'] = orig
                break

    # 6. Identificar estritamente a coluna de DATA DE EXPEDIÇÃO
    col_data_exp = identificar_coluna_data_expedicao(df.columns)
    if col_data_exp:
        cols_map['data'] = col_data_exp

    novos_mandados = []
    
    for idx, row in df.iterrows():
        mandado_id = str(row[cols_map['id']]).strip() if 'id' in cols_map and pd.notna(row[cols_map['id']]) else f"BNMP-2026-CSV-{idx+1}"
        if not mandado_id or mandado_id == "nan":
            continue
            
        nome = str(row[cols_map['nome']]).strip().upper() if 'nome' in cols_map and pd.notna(row[cols_map['nome']]) else "NÃO INFORMADO"
        cpf = str(row[cols_map['cpf']]).strip() if 'cpf' in cols_map and pd.notna(row[cols_map['cpf']]) else "000.***.***-00"
        orgao = str(row[cols_map['orgao']]).strip() if 'orgao' in cols_map and pd.notna(row[cols_map['orgao']]) else "Vara Criminal da Comarca"
        cidade_raw = str(row[cols_map['comarca']]).strip() if 'comarca' in cols_map and pd.notna(row[cols_map['comarca']]) else ""
        
        expedicao_raw = row[cols_map['data']] if 'data' in cols_map and pd.notna(row[cols_map['data']]) else ""
        expedicao_str, ts_val = extrair_data_e_timestamp(expedicao_raw)

        cidade, cia = identificar_comarca_e_cia(orgao + " " + cidade_raw)
        if cidade == "Outras Comarcas":
            cidade = normalizar_municipio(cidade_raw)
            cia = MAPA_COMARCA_PARA_CIA.get(MAPA_MUNICIPIO_PARA_COMARCA.get(cidade, "Outras Comarcas"), "Outras Comarcas (Paraná)")

        if not any(m['id'] == mandado_id for m in st.session_state.mandados) and not any(m['id'] == mandado_id for m in novos_mandados):
            item = {
                "id": str(mandado_id),
                "nome": str(nome),
                "cpf": str(cpf),
                "comarca": str(cidade),
                "companhia": str(cia),
                "orgao_expedidor": str(orgao),
                "expedicao_datahora": str(expedicao_str),
                "timestamp": float(ts_val),
                "situacao": "Pendente de Cumprimento",
                "pdf_url": "https://portalbnmp.cnj.jus.br/#/pesquisa-peca"
            }
            novos_mandados.append(item)

    if novos_mandados:
        st.session_state.mandados.extend(novos_mandados)
        salvar_mandados_disco(st.session_state.mandados)
        return len(novos_mandados)
    return 0

def carregar_arquivo_upload(uploaded_file):
    filename = uploaded_file.name.lower()
    df = None
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"Erro ao ler arquivo Excel: {e}")
            return 0
    else:
        content_bytes = uploaded_file.getvalue()
        try:
            df = pd.read_csv(io.BytesIO(content_bytes), sep=None, engine='python', on_bad_lines='skip')
        except Exception:
            try:
                df = pd.read_csv(io.BytesIO(content_bytes), sep=';', on_bad_lines='skip')
            except Exception:
                try:
                    df = pd.read_csv(io.BytesIO(content_bytes), sep=',', on_bad_lines='skip')
                except Exception:
                    df = None

        if df is None or df.empty or len(df.columns) == 1:
            try:
                texto = content_bytes.decode('utf-8', errors='ignore')
                return processar_texto_importado(texto)
            except Exception as e:
                st.error(f"Erro ao ler arquivo de texto/CSV: {e}")
                return 0

    return processar_dataframe_importado(df)

# BARRA LATERAL (Sidebar)
st.sidebar.title("🚨 Filtros PMPR")
st.sidebar.markdown("**Monitor de Mandados BNMP 3.0**")

cias_padrao = ["1ª CIA (Cornélio Procópio)", "2ª CIA (Bandeirantes)", "3ª CIA (Assaí)"]

cias_selecionadas = st.sidebar.multiselect(
    "1️⃣ Selecionar Companhia(s):",
    options=list(st.session_state.estruturas.keys()),
    default=cias_padrao
)

# Resolução de Comarcas Sedes (Resiliente)
comarcas_disponiveis = []
for cia in cias_selecionadas:
    estrutura_cia = st.session_state.estruturas.get(cia, {})
    if isinstance(estrutura_cia, dict):
        comarcas_disponiveis.extend(list(estrutura_cia.keys()))
    elif isinstance(estrutura_cia, list):
        comarcas_disponiveis.extend(estrutura_cia)

comarcas_disponiveis = sorted(list(set(comarcas_disponiveis)))

comarcas_selecionadas = st.sidebar.multiselect(
    "2️⃣ Selecionar Comarca(s) Sede (Fórums):",
    options=comarcas_disponiveis,
    default=comarcas_disponiveis
)

# Resolução de Municípios Subordinados
cidades_disponiveis = []
for cia in cias_selecionadas:
    estrutura_cia = st.session_state.estruturas.get(cia, {})
    if isinstance(estrutura_cia, dict):
        for comarca_nome in comarcas_selecionadas:
            if comarca_nome in estrutura_cia:
                cidades_disponiveis.extend(estrutura_cia[comarca_nome])
    elif isinstance(estrutura_cia, list):
        cidades_disponiveis.extend(estrutura_cia)

cidades_disponiveis = sorted(list(set(cidades_disponiveis)))

cidades_selecionadas = st.sidebar.multiselect(
    "3️⃣ Filtrar Municípios/Cidades:",
    options=cidades_disponiveis,
    default=cidades_disponiveis
)

st.sidebar.markdown("---")
opcoes_periodo = [
    "⭐ Últimos 50 Dias (Ano 2026)",
    "📅 Ano 2026 Completo",
    "🕒 Últimos 30 Dias",
    "🕒 Últimos 90 Dias",
    "🕒 Últimos 180 Dias",
    "🌐 Histórico Completo (Todos os Anos)"
]

periodo_selecionado = st.sidebar.selectbox("4️⃣ Período de Expedição:", options=opcoes_periodo, index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Exportar Base Completa (CSV)")
if st.session_state.mandados:
    df_exp = pd.DataFrame(st.session_state.mandados)
    cols_export = ['id', 'nome', 'cpf', 'comarca', 'companhia', 'orgao_expedidor', 'expedicao_datahora', 'situacao']
    cols_exist = [c for c in cols_export if c in df_exp.columns]
    df_exp_final = df_exp[cols_exist].rename(columns={
        'id': 'Nº Mandado',
        'nome': 'Nome Procurado',
        'cpf': 'CPF',
        'comarca': 'Município/Comarca',
        'companhia': 'Companhia PMPR',
        'orgao_expedidor': 'Órgão Expedidor',
        'expedicao_datahora': 'Data de Expedição',
        'situacao': 'Situação'
    })
    csv_bytes = df_exp_final.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.sidebar.download_button(
        label="📥 Baixar Mandados em CSV",
        data=csv_bytes,
        file_name=f"mandados_pmpr_parana_{datetime.date.today().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Ações do Banco de Dados")
if st.sidebar.button("🗑️ Limpar Todos os Mandados Salvos"):
    st.session_state.mandados = []
    salvar_mandados_disco([])
    st.sidebar.success("Base de dados limpa!")
    recarregar_app()

# ÁREA PRINCIPAL (Dashboard)
st.markdown('<div class="titulo-principal">🚨 PMPR - Sistema Regional de Mandados de Prisão (BNMP 3.0)</div>', unsafe_allow_html=True)

# Cálculo do Filtro Temporal
agora_dt = datetime.datetime.now()
data_corte_50d = agora_dt - datetime.timedelta(days=50)

mandados_validos_periodo = []
for m in st.session_state.mandados:
    ts = m.get('timestamp', 0.0)
    exp_str = str(m.get('expedicao_datahora', ''))
    
    dt_m = None
    if ts > 0.0:
        try:
            dt_m = datetime.datetime.fromtimestamp(ts)
        except Exception:
            dt_m = None

    if "50 Dias" in periodo_selecionado:
        if dt_m and dt_m >= data_corte_50d and dt_m.year == 2026:
            mandados_validos_periodo.append(m)
        elif "2026" in exp_str and dt_m and dt_m >= data_corte_50d:
            mandados_validos_periodo.append(m)
    elif "2026 Completo" in periodo_selecionado:
        if (dt_m and dt_m.year == 2026) or "2026" in exp_str:
            mandados_validos_periodo.append(m)
    elif "30 Dias" in periodo_selecionado:
        if dt_m and dt_m >= (agora_dt - datetime.timedelta(days=30)):
            mandados_validos_periodo.append(m)
    elif "90 Dias" in periodo_selecionado:
        if dt_m and dt_m >= (agora_dt - datetime.timedelta(days=90)):
            mandados_validos_periodo.append(m)
    elif "180 Dias" in periodo_selecionado:
        if dt_m and dt_m >= (agora_dt - datetime.timedelta(days=180)):
            mandados_validos_periodo.append(m)
    else:
        mandados_validos_periodo.append(m)

cidades_sel_norm = [normalizar_municipio(c) for c in cidades_selecionadas]

mandados_filtrados = [
    m for m in mandados_validos_periodo
    if normalizar_municipio(m['comarca']) in cidades_sel_norm or m['comarca'] in cidades_selecionadas
]

# Métricas Operacionais
c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.metric("Mandados Salvos (Total)", len(st.session_state.mandados))
c_m2.metric("No Período Filtrado", len(mandados_validos_periodo))
c_m3.metric("Filtrados na Tela", len(mandados_filtrados))
c_m4.metric("Status BNMP 3.0", "Conectado", delta="Tempo Real")

st.markdown("---")

busca = st.text_input("🔍 Pesquisar por Nome, CPF, Comarca ou Nº do Mandado:", placeholder="Digite para buscar...")
if busca:
    mandados_filtrados = [
        m for m in mandados_filtrados
        if busca.lower() in m['nome'].lower() or busca in m['id'] or busca in m['cpf'] or busca.lower() in m['comarca'].lower()
    ]

mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x.get('timestamp', 0.0), reverse=True)

aba1, aba2, aba3 = st.tabs(["📋 Mandados Expedidos", "🚀 Importar CSV / Bookmarklet / Texto", "📊 Estatísticas"])

with aba1:
    st.subheader(f"Mandados Expedidos na Região ({len(mandados_filtrados)})")
    
    if not mandados_filtrados:
        qtd_fora = len(mandados_validos_periodo) - len(mandados_filtrados)
        if qtd_fora > 0:
            st.warning(f"⚠️ Existem **{qtd_fora} mandado(s)** no período selecionado salvos no banco, mas pertencem a comarcas fora dos filtros ativos.")
            st.info("💡 **Dica:** Marque **'Outras Comarcas (Paraná)'** no filtro de Companhias para visualizar os mandados das demais regiões.")
        else:
            st.info("Nenhum mandado localizado no banco de dados para os critérios selecionados.")
    else:
        for m in mandados_filtrados:
            st.markdown(f"""
            <div class="card-mandado">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:18px; font-weight:bold; color:#0F172A;">👤 {m['nome']} (CPF: {m['cpf']})</span>
                    <span class="badge-status">{m['situacao']}</span>
                </div>
                <div style="margin-top: 8px; color: #475569; font-size: 13px;">
                    <span class="badge-cia">🛡️ {m['companhia']}</span>
                    <b>Município/Comarca:</b> <span class="badge-cidade">📍 {m['comarca']}</span>
                </div>
                <div style="margin-top: 8px; color: #334155; font-size: 13px;">
                    ⚖️ <b>Órgão Expedidor:</b> {m['orgao_expedidor']} | 
                    ⏰ <b>Expedido em (Judicial):</b> {m['expedicao_datahora']}
                </div>
                <div style="margin-top: 10px;">
                    <b>📜 Número do Mandado (Copie para pesquisar no BNMP):</b><br>
                    <div class="caixa-mandado">{m['id']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_link, col_info = st.columns(2)
            with col_link:
                st.markdown(f"""
                <a href="https://portalbnmp.cnj.jus.br/#/pesquisa-peca" target="_blank" style="text-decoration:none;">
                    <button style="background-color:#2563EB; color:white; border:none; padding:10px 16px; border-radius:6px; font-weight:bold; cursor:pointer; width:100%;">
                        🔗 Abrir PDF / Consultar no BNMP 3.0 (CNJ)
                    </button>
                </a>
                """, unsafe_allow_html=True)
            with col_info:
                st.caption("ℹ️ *Copie o número do mandado acima, clique no botão para abrir o site do CNJ, cole o número e resolva o CAPTCHA para visualizar o PDF oficial.*")
            st.markdown("<br>", unsafe_allow_html=True)

with aba2:
    st.subheader("🚀 Importação dos Mandados Reais (CSV, Excel ou Bookmarklet)")
    
    col_up, col_txt = st.columns(2)
    
    with col_up:
        st.markdown("#### 📄 Opção A: Importar Arquivo CSV / Excel")
        file_up = st.file_uploader("Selecione o arquivo (.csv, .xlsx):", type=['csv', 'xlsx', 'xls', 'txt'])
        if file_up is not None:
            if st.button("📥 Processar Arquivo Carregado", type="primary"):
                qtd = carregar_arquivo_upload(file_up)
                if qtd > 0:
                    st.success(f"✅ {qtd} novo(s) mandado(s) importado(s) do arquivo com sucesso!")
                    recarregar_app()
                else:
                    st.warning("Nenhum mandado novo foi adicionado (ou todos já constam no banco).")
                    
    with col_txt:
        st.markdown("#### 📋 Opção B: Cole o Texto (Bookmarklet / Copia Direta)")
        texto_input = st.text_area("Cole aqui o texto capturado do BNMP 3.0:", height=180, placeholder="Cole aqui os dados capturados...")
        if st.button("📥 Processar Texto Colado"):
            if texto_input.strip():
                qtd = processar_texto_importado(texto_input)
                if qtd > 0:
                    st.success(f"✅ {qtd} novo(s) mandado(s) importado(s) com sucesso!")
                    recarregar_app()
                else:
                    st.warning("Nenhum mandado novo foi adicionado.")
            else:
                st.error("Por favor, cole os dados antes de clicar em processar.")

with aba3:
    st.subheader("📊 Estatísticas Operacionais da Região")
    if mandados_filtrados:
        df_mandados = pd.DataFrame(mandados_filtrados)
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### Mandados por Companhia")
            st.bar_chart(df_mandados['companhia'].value_counts())
        with col_g2:
            st.markdown("#### Mandados por Município")
            st.bar_chart(df_mandados['comarca'].value_counts())
    else:
        st.write("Nenhum dado disponível para estatísticas.")
