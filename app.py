import streamlit as st
import pandas as pd
import datetime
import time
import json
import io
import re
import unicodedata

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
    .badge-comarca {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: bold;
        margin-right: 5px;
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

# Estrutura Organizacional PMPR por Companhias, Comarcas Sedes (Fóruns) e Municípios Abrangidos
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
        "Outras Comarcas (Paraná)": [
            "Londrina", "Maringá", "Curitiba", "Ponta Grossa", "Jacarezinho", "Santo Antônio da Platina",
            "Cascavel", "Foz do Iguaçu", "Guarapuava", "Toledo", "Apucarana", "Arapongas", "Campo Mourão",
            "Umuarama", "Paranavaí", "Pato Branco", "Francisco Beltrão", "Telêmaco Borba", "Jandaia do Sul"
        ]
    }
}

ARQUIVO_DADOS = "mandados.json"

def remover_acentos(texto):
    if not texto:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")

# Mapeamento de normalização para Cidades e Comarcas
MAPA_MUNICIPOS = {}
MAPA_COMARCA_SEDE = {}
MAPA_COMPANHIA = {}

for cia_key, comarcas_dict in ESTRUTURA_COMPANHIAS.items():
    for comarca_sede, m_list in comarcas_dict.items():
        for m in m_list:
            norm_m = remover_acentos(m.lower())
            MAPA_MUNICIPOS[norm_m] = m
            MAPA_COMARCA_SEDE[norm_m] = comarca_sede
            MAPA_COMPANHIA[norm_m] = cia_key

def normalizar_municipio(nome_raw):
    if not nome_raw or pd.isna(nome_raw):
        return "Outras Comarcas (Paraná)"
    raw_clean = remover_acentos(str(nome_raw).strip().lower())
    if raw_clean in MAPA_MUNICIPOS:
        return MAPA_MUNICIPOS[raw_clean]
    for key, oficial in MAPA_MUNICIPOS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', raw_clean):
            return oficial
    return str(nome_raw).strip()

def identificar_comarca_sede(cidade_ou_orgao):
    if not cidade_ou_orgao or pd.isna(cidade_ou_orgao):
        return "Outras Comarcas (Paraná)"
    text_clean = remover_acentos(str(cidade_ou_orgao).strip().lower())
    for key, sede in MAPA_COMARCA_SEDE.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text_clean):
            return sede
    return "Outras Comarcas (Paraná)"

def identificar_companhia(cidade_ou_comarca):
    cidade_norm = normalizar_municipio(cidade_ou_comarca)
    cidade_clean = remover_acentos(cidade_norm.lower())
    if cidade_clean in MAPA_COMPANHIA:
        return MAPA_COMPANHIA[cidade_clean]
    comarca_sede = identificar_comarca_sede(cidade_ou_comarca)
    comarca_clean = remover_acentos(comarca_sede.lower())
    if comarca_clean in MAPA_COMPANHIA:
        return MAPA_COMPANHIA[comarca_clean]
    return "Outras Comarcas (Paraná)"

def carregar_mandados_salvos():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    clean_list = []
                    for item in dados:
                        if isinstance(item, dict):
                            c_norm = normalizar_municipio(item.get("comarca", item.get("municipio", "")))
                            sede_norm = identificar_comarca_sede(item.get("comarca_sede", item.get("orgao_expedidor", c_norm)))
                            cia_norm = identificar_companhia(c_norm)
                            item["comarca"] = c_norm
                            item["comarca_sede"] = sede_norm
                            item["companhia"] = cia_norm
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
                c_norm = normalizar_municipio(item.get("comarca", item.get("municipio", "")))
                sede_norm = identificar_comarca_sede(item.get("comarca_sede", item.get("orgao_expedidor", c_norm)))
                cia_norm = identificar_companhia(c_norm)
                limpos.append({
                    "id": str(item.get("id", "")),
                    "nome": str(item.get("nome", "NÃO INFORMADO")),
                    "cpf": str(item.get("cpf", "000.***.***-00")),
                    "comarca": str(c_norm),
                    "comarca_sede": str(sede_norm),
                    "companhia": str(cia_norm),
                    "orgao_expedidor": str(item.get("orgao_expedidor", "Vara Criminal da Comarca")),
                    "expedicao_datahora": str(item.get("expedicao_datahora", "")),
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

# Inicialização do Session State
if 'estruturas' not in st.session_state:
    st.session_state.estruturas = ESTRUTURA_COMPANHIAS

if 'mandados' not in st.session_state:
    st.session_state.mandados = carregar_mandados_salvos()

def processar_texto_importado(texto_bruto):
    linhas = [l.strip() for l in texto_bruto.split('\n') if l.strip()]
    novos_mandados = []
    agora = datetime.datetime.now()
    
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
                
            if data_match:
                current_record['data'] = data_match.group(1)
                
            c_detectada = normalizar_municipio(l)
            if c_detectada != l and 'cidade' not in current_record:
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
        cidade_raw = b.get('cidade', '')
        orgao = str(b.get('orgao', '')).strip() or "Vara Criminal da Comarca"
        expedicao = str(b.get('data', '')).strip() or agora.strftime("%d/%m/%Y %H:%M:%S")
        
        cidade = normalizar_municipio(cidade_raw or orgao)
        comarca_sede = identificar_comarca_sede(orgao or cidade)
        cia = identificar_companhia(cidade)
        
        try:
            if ":" in expedicao:
                dt = datetime.datetime.strptime(expedicao, "%d/%m/%Y %H:%M:%S")
            else:
                dt = datetime.datetime.strptime(expedicao, "%d/%m/%Y")
            ts = float(dt.timestamp())
        except Exception:
            ts = float(agora.timestamp())

        if not any(m['id'] == mandado_id for m in st.session_state.mandados) and not any(m['id'] == mandado_id for m in novos_mandados):
            item = {
                "id": str(mandado_id),
                "nome": str(nome).upper(),
                "cpf": str(cpf),
                "comarca": str(cidade),
                "comarca_sede": str(comarca_sede),
                "companhia": str(cia),
                "orgao_expedidor": str(orgao),
                "expedicao_datahora": str(expedicao),
                "timestamp": float(ts),
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
    
    # 1. ID / Mandado
    for orig, c in zip(df.columns, cols_clean):
        if any(k in c for k in ['no mandado', 'num_mandado', 'numero_mandado', 'n_mandado', 'no do mandado', 'numero do mandado', 'peca']) or c in ['id', 'mandado', 'numero']:
            cols_map['id'] = orig
            break

    # 2. Nome
    for orig, c in zip(df.columns, cols_clean):
        if 'nome' in c or 'procurado' in c or 'individuo' in c or 'pessoa' in c or 'reu' in c:
            cols_map['nome'] = orig
            break

    # 3. CPF
    for orig, c in zip(df.columns, cols_clean):
        if 'cpf' in c:
            cols_map['cpf'] = orig
            break

    # 4. Comarca Expedidora / Órgão Expedidor
    for orig, c in zip(df.columns, cols_clean):
        if 'orgao' in c or 'expedidor' in c or 'vara' in c or 'juizado' in c or 'julgador' in c:
            if cols_map.get('id') != orig:
                cols_map['orgao'] = orig
                break

    # 5. Comarca / Cidade / Municipio
    for orig, c in zip(df.columns, cols_clean):
        if ('comarca' in c or 'municipio' in c or 'cidade' in c or 'jurisdicao' in c) and orig != cols_map.get('orgao'):
            cols_map['comarca'] = orig
            break

    # 6. Data
    for orig, c in zip(df.columns, cols_clean):
        if 'data' in c or 'expedicao' in c or 'datahora' in c:
            cols_map['data'] = orig
            break

    novos_mandados = []
    agora = datetime.datetime.now()
    
    for idx, row in df.iterrows():
        mandado_id = str(row[cols_map['id']]).strip() if 'id' in cols_map and pd.notna(row[cols_map['id']]) else f"BNMP-2026-CSV-{idx+1}"
        if not mandado_id or mandado_id == "nan":
            continue
            
        nome = str(row[cols_map['nome']]).strip().upper() if 'nome' in cols_map and pd.notna(row[cols_map['nome']]) else "NÃO INFORMADO"
        cpf = str(row[cols_map['cpf']]).strip() if 'cpf' in cols_map and pd.notna(row[cols_map['cpf']]) else "000.***.***-00"
        
        comarca_raw = str(row[cols_map['comarca']]).strip() if 'comarca' in cols_map and pd.notna(row[cols_map['comarca']]) else ""
        orgao_raw = str(row[cols_map['orgao']]).strip() if 'orgao' in cols_map and pd.notna(row[cols_map['orgao']]) else "Vara Criminal da Comarca"
        expedicao = str(row[cols_map['data']]).strip() if 'data' in cols_map and pd.notna(row[cols_map['data']]) else agora.strftime("%d/%m/%Y %H:%M:%S")

        cidade = normalizar_municipio(comarca_raw or orgao_raw)
        comarca_sede = identificar_comarca_sede(orgao_raw or comarca_raw)
        cia = identificar_companhia(cidade)

        try:
            if ":" in expedicao:
                dt = datetime.datetime.strptime(expedicao, "%d/%m/%Y %H:%M:%S")
            else:
                dt = datetime.datetime.strptime(expedicao, "%d/%m/%Y")
            ts = float(dt.timestamp())
        except Exception:
            ts = float(agora.timestamp())

        if not any(m['id'] == mandado_id for m in st.session_state.mandados) and not any(m['id'] == mandado_id for m in novos_mandados):
            item = {
                "id": str(mandado_id),
                "nome": str(nome),
                "cpf": str(cpf),
                "comarca": str(cidade),
                "comarca_sede": str(comarca_sede),
                "companhia": str(cia),
                "orgao_expedidor": str(orgao_raw),
                "expedicao_datahora": str(expedicao),
                "timestamp": float(ts),
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

# 1. Filtro de Companhias PMPR
cias_padrao = ["1ª CIA (Cornélio Procópio)", "2ª CIA (Bandeirantes)", "3ª CIA (Assaí)"]
cias_selecionadas = st.sidebar.multiselect(
    "1️⃣ Selecionar Companhia(s):",
    options=list(st.session_state.estruturas.keys()),
    default=cias_padrao
)

# 2. Filtro de Comarcas Sedes (Fóruns)
comarcas_disponiveis = []
for cia in cias_selecionadas:
    comarcas_disponiveis.extend(list(st.session_state.estruturas[cia].keys()))

comarcas_selecionadas = st.sidebar.multiselect(
    "2️⃣ Selecionar Comarca(s) Sede (Fóruns):",
    options=comarcas_disponiveis,
    default=comarcas_disponiveis
)

# 3. Filtro de Municípios / Cidades
municipios_disponiveis = []
for cia in cias_selecionadas:
    for comarca in comarcas_selecionadas:
        if comarca in st.session_state.estruturas[cia]:
            municipios_disponiveis.extend(st.session_state.estruturas[cia][comarca])

municipios_selecionados = st.sidebar.multiselect(
    "3️⃣ Filtrar Municípios/Cidades:",
    options=list(set(municipios_disponiveis)),
    default=list(set(municipios_disponiveis))
)

# 4. Filtro de Período de Expedição
st.sidebar.markdown("---")
opcao_periodo = st.sidebar.selectbox(
    "4️⃣ Período de Expedição:",
    options=[
        "⭐ Últimos 50 Dias (Ano 2026)",
        "Ano 2026 Completo",
        "Últimos 30 Dias",
        "Últimos 90 Dias",
        "Últimos 180 Dias",
        "Histórico Completo (Todos os Anos)"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Exportar Base Completa (CSV)")
if st.session_state.mandados:
    df_exp = pd.DataFrame(st.session_state.mandados)
    cols_export = ['id', 'nome', 'cpf', 'comarca', 'comarca_sede', 'companhia', 'orgao_expedidor', 'expedicao_datahora', 'situacao']
    cols_exist = [c for c in cols_export if c in df_exp.columns]
    df_exp_final = df_exp[cols_exist].rename(columns={
        'id': 'Nº Mandado',
        'nome': 'Nome Procurado',
        'cpf': 'CPF',
        'comarca': 'Município/Cidade',
        'comarca_sede': 'Comarca Sede (Fórum)',
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
else:
    st.sidebar.caption("Nenhum mandado salvo para exportação.")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Ações do Banco de Dados")
if st.sidebar.button("🗑️ Limpar Todos os Mandados Salvos"):
    st.session_state.mandados = []
    salvar_mandados_disco([])
    st.sidebar.success("Base de dados limpa!")
    recarregar_app()

# ÁREA PRINCIPAL (Dashboard)
st.markdown('<div class="titulo-principal">🚨 PMPR - Sistema Regional de Mandados de Prisão (BNMP 3.0)</div>', unsafe_allow_html=True)

# Aplicação do Filtro de Período Temporal
agora = datetime.datetime.now()
mandados_filtrados_tempo = []

for m in st.session_state.mandados:
    ts = m.get('timestamp', 0)
    try:
        dt_m = datetime.datetime.fromtimestamp(ts)
    except Exception:
        dt_m = agora
        
    if "Últimos 50 Dias (Ano 2026)" in opcao_periodo:
        if dt_m.year == 2026 and (agora - dt_m).days <= 50:
            mandados_filtrados_tempo.append(m)
    elif "Ano 2026 Completo" in opcao_periodo:
        if dt_m.year == 2026:
            mandados_filtrados_tempo.append(m)
    elif "Últimos 30 Dias" in opcao_periodo:
        if (agora - dt_m).days <= 30:
            mandados_filtrados_tempo.append(m)
    elif "Últimos 90 Dias" in opcao_periodo:
        if (agora - dt_m).days <= 90:
            mandados_filtrados_tempo.append(m)
    elif "Últimos 180 Dias" in opcao_periodo:
        if (agora - dt_m).days <= 180:
            mandados_filtrados_tempo.append(m)
    else:
        mandados_filtrados_tempo.append(m)

# Aplicação do Filtro Geográfico por Companhia, Comarca Sede e Município
mandados_filtrados = [
    m for m in mandados_filtrados_tempo
    if m.get('companhia') in cias_selecionadas
    and m.get('comarca_sede', m.get('comarca')) in comarcas_selecionadas
    and m.get('comarca') in municipios_selecionados
]

# Métricas Operacionais
c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.metric("Mandados Salvos (Total)", len(st.session_state.mandados))
c_m2.metric("No Período Selecionado", len(mandados_filtrados_tempo))
c_m3.metric("Filtrados na Tela", len(mandados_filtrados))
c_m4.metric("Status BNMP 3.0", "Conectado", delta="Tempo Real")

st.markdown("---")

busca = st.text_input("🔍 Pesquisar por Nome, CPF, Comarca Sede, Município ou Nº do Mandado:", placeholder="Digite para buscar...")
if busca:
    mandados_filtrados = [
        m for m in mandados_filtrados
        if busca.lower() in m['nome'].lower()
        or busca in m['id']
        or busca in m['cpf']
        or busca.lower() in m['comarca'].lower()
        or busca.lower() in m.get('comarca_sede', '').lower()
    ]

mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x.get('timestamp', 0), reverse=True)

aba1, aba2, aba3 = st.tabs(["📋 Mandados Expedidos", "🚀 Importar CSV / Bookmarklet / Texto", "📊 Estatísticas"])

with aba1:
    st.subheader(f"Mandados Expedidos na Região ({len(mandados_filtrados)})")
    
    if not mandados_filtrados:
        qtd_fora = len(mandados_filtrados_tempo) - len(mandados_filtrados)
        if qtd_fora > 0:
            st.warning(f"⚠️ Existem **{qtd_fora} mandado(s)** no período selecionado salvos no banco de dados, mas eles pertencem a Comarcas/Municípios fora dos filtros atualmente selecionados.")
            st.info("💡 **Como visualizar:** Na barra lateral, certifique-se de marcar as Companhias, Comarcas Sedes e Municípios desejados.")
        else:
            st.info("Nenhum mandado localizado para os filtros selecionados.")
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
                    <span class="badge-comarca">🏛️ Comarca Sede: {m.get('comarca_sede', m['comarca'])}</span>
                    <b>Município:</b> <span class="badge-cidade">📍 {m['comarca']}</span>
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
            st.markdown("#### Mandados por Comarca Sede")
            if 'comarca_sede' in df_mandados.columns:
                st.bar_chart(df_mandados['comarca_sede'].value_counts())
            else:
                st.bar_chart(df_mandados['comarca'].value_counts())
    else:
        st.write("Nenhum dado disponível para estatísticas.")
