import streamlit as st
import pandas as pd
import datetime
import json
import os
import re
import io
import unicodedata

# ------------------------------------------------------------------------------
# Configuração Visual e Estilização
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Monitor BNMP 3.0 - PMPR",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# ------------------------------------------------------------------------------
# Mapeamento Oficial da PMPR (Companhias, Comarcas Sedes e Municípios)
# ------------------------------------------------------------------------------
ESTRUTURA_PMPR = {
    "1ª CIA (Cornélio Procópio)": {
        "Cornélio Procópio": ["Cornélio Procópio", "Leópolis", "Rancho Alegre"],
        "Uraí": ["Uraí", "Nova Fátima", "Sertaneja"]
    },
    "2ª CIA (Bandeirantes)": {
        "Bandeirantes": ["Bandeirantes", "Santa Amélia", "Santa Mariana"],
        "Andirá": ["Andirá", "Itambaracá", "Barra do Jacaré"]
    },
    "3ª CIA (Assaí)": {
        "Assaí": ["Assaí", "Nova América da Colina", "São Sebastião da Amoreira"],
        "Congonhinhas": ["Congonhinhas", "Santo Antônio do Paraíso"],
        "São Jerônimo da Serra": ["São Jerônimo da Serra", "Santa Cecília do Pavão", "Nova Santa Bárbara"]
    }
}

ARQUIVO_DADOS = "mandados.json"

def norm(txt):
    if not txt or pd.isna(txt):
        return ""
    txt = str(txt).lower().strip()
    return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")

# Montar tabelas de busca estritas sem sobreposição
MUNICIPIOS_ESPECIFICOS = {}
COMARCAS_SEDE = {}

for cia, comarcas in ESTRUTURA_PMPR.items():
    for sede, munis in comarcas.items():
        n_s = norm(sede)
        COMARCAS_SEDE[n_s] = (sede, sede, cia)
        for m in munis:
            n_m = norm(m)
            MUNICIPIOS_ESPECIFICOS[n_m] = (m, sede, cia)

KEYS_SPECIFIC = sorted(MUNICIPIOS_ESPECIFICOS.keys(), key=lambda x: len(x), reverse=True)
KEYS_SEDE = sorted(COMARCAS_SEDE.keys(), key=lambda x: len(x), reverse=True)

def identificar_localizacao_precisa(texto_completo):
    """
    Identifica de forma estrita a cidade, a comarca sede e a companhia PMPR a partir de qualquer texto.
    """
    if not texto_completo or pd.isna(texto_completo):
        return "Outras Comarcas (Paraná)", "Outras Comarcas (Paraná)", "Outras Comarcas (Paraná)"
        
    t_norm = norm(texto_completo)
    
    # 1. Tentar encontrar município específico que não seja sede primeiro (ex: Barra do Jacaré, Itambaracá, Leópolis)
    for k in KEYS_SPECIFIC:
        m, sede, cia = MUNICIPIOS_ESPECIFICOS[k]
        if m != sede:
            pattern = r'\b' + re.escape(k) + r'\b'
            if re.search(pattern, t_norm):
                return m, sede, cia
                
    # 2. Se não encontrou município agregado, tentar encontrar sede (ex: Andirá, Bandeirantes, Cornélio Procópio, Assaí)
    for k in KEYS_SEDE:
        m, sede, cia = COMARCAS_SEDE[k]
        pattern = r'\b' + re.escape(k) + r'\b'
        if re.search(pattern, t_norm):
            return m, sede, cia

    return "Outras Comarcas (Paraná)", "Outras Comarcas (Paraná)", "Outras Comarcas (Paraná)"

# ------------------------------------------------------------------------------
# Persistência de Dados (JSON)
# ------------------------------------------------------------------------------
def carregar_mandados_salvos():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    clean_list = []
                    for item in dados:
                        if isinstance(item, dict):
                            # Re-normalizar dados ao carregar
                            texto_ref = f"{item.get('comarca','')} {item.get('orgao_expedidor','')} {item.get('nome','')}"
                            cid, com, cia = identificar_localizacao_precisa(texto_ref)
                            if cid != "Outras Comarcas (Paraná)":
                                item["comarca"] = cid
                                item["comarca_sede"] = com
                                item["companhia"] = cia
                            else:
                                item["comarca_sede"] = item.get("comarca_sede", item.get("comarca", "Outras Comarcas (Paraná)"))
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
                texto_ref = f"{item.get('comarca','')} {item.get('orgao_expedidor','')} {item.get('nome','')}"
                cid, com, cia = identificar_localizacao_precisa(texto_ref)
                
                c_final = cid if cid != "Outras Comarcas (Paraná)" else item.get("comarca", "Outras Comarcas (Paraná)")
                com_final = com if com != "Outras Comarcas (Paraná)" else item.get("comarca_sede", "Outras Comarcas (Paraná)")
                cia_final = cia if cia != "Outras Comarcas (Paraná)" else item.get("companhia", "Outras Comarcas (Paraná)")
                
                limpos.append({
                    "id": str(item.get("id", "")),
                    "nome": str(item.get("nome", "NÃO INFORMADO")),
                    "cpf": str(item.get("cpf", "000.***.***-00")),
                    "comarca": str(c_final),
                    "comarca_sede": str(com_final),
                    "companhia": str(cia_final),
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
if 'mandados' not in st.session_state:
    st.session_state.mandados = carregar_mandados_salvos()

# ------------------------------------------------------------------------------
# Processadores de Importação (Texto & Dataframe CSV/Excel)
# ------------------------------------------------------------------------------
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
                        'id': partes if len(partes) > 0 else '',
                        'nome': partes if len(partes) > 1 else '',
                        'cpf': partes if len(partes) > 2 else '',
                        'cidade': partes if len(partes) > 3 else '',
                        'orgao': partes if len(partes) > 4 else '',
                        'data': partes if len(partes) > 5 else ''
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
                
            cid, com, cia = identificar_localizacao_precisa(l)
            if cid != "Outras Comarcas (Paraná)" and 'cidade' not in current_record:
                current_record['cidade'] = cid
                current_record['comarca_sede'] = com
                current_record['companhia'] = cia
                
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
        expedicao = str(b.get('data', '')).strip() or agora.strftime("%d/%m/%Y %H:%M:%S")
        
        texto_ref = f"{b.get('cidade','')} {orgao} {nome}"
        cidade, comarca_sede, cia = identificar_localizacao_precisa(texto_ref)
        
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
    cols_clean = [norm(c) for c in df.columns]
    
    # Identificar colunas por nome aproximado
    for orig, c in zip(df.columns, cols_clean):
        if any(k in c for k in ['no mandado', 'num_mandado', 'numero_mandado', 'n_mandado', 'no do mandado', 'numero do mandado', 'numeropeca', 'peca']) or c in ['id', 'mandado', 'numero']:
            cols_map['id'] = orig
            break

    for orig, c in zip(df.columns, cols_clean):
        if 'nome' in c or 'procurado' in c or 'individuo' in c or 'pessoa' in c:
            cols_map['nome'] = orig
            break

    for orig, c in zip(df.columns, cols_clean):
        if 'cpf' in c:
            cols_map['cpf'] = orig
            break

    for orig, c in zip(df.columns, cols_clean):
        if 'comarca' in c or 'municipio' in c or 'cidade' in c or 'jurisdicao' in c or 'localidade' in c:
            cols_map['comarca'] = orig
            break

    for orig, c in zip(df.columns, cols_clean):
        if 'orgao' in c or 'expedidor' in c or 'vara' in c or 'juizado' in c or 'julgador' in c:
            if cols_map.get('id') != orig:
                cols_map['orgao'] = orig
                break

    for orig, c in zip(df.columns, cols_clean):
        if 'data' in c or 'expedicao' in c or 'datahora' in c or 'emissao' in c:
            cols_map['data'] = orig
            break

    novos_mandados = []
    agora = datetime.datetime.now()
    
    for idx, row in df.iterrows():
        linha_texto = " ".join([str(v) for v in row.values if pd.notna(v)])
        
        mandado_id = str(row[cols_map['id']]).strip() if 'id' in cols_map and pd.notna(row[cols_map['id']]) else ""
        if not mandado_id or mandado_id == "nan":
            id_match = re.search(r'([A-Z0-9\.\-\/]{10,}(?:BNMP|\d{4}-\d+|\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}))', linha_texto, re.IGNORECASE)
            mandado_id = id_match.group(1) if id_match else f"BNMP-2026-CSV-{idx+1}"
            
        nome = str(row[cols_map['nome']]).strip().upper() if 'nome' in cols_map and pd.notna(row[cols_map['nome']]) else "NÃO INFORMADO"
        cpf = str(row[cols_map['cpf']]).strip() if 'cpf' in cols_map and pd.notna(row[cols_map['cpf']]) else "000.***.***-00"
        orgao = str(row[cols_map['orgao']]).strip() if 'orgao' in cols_map and pd.notna(row[cols_map['orgao']]) else "Vara Criminal da Comarca"
        expedicao = str(row[cols_map['data']]).strip() if 'data' in cols_map and pd.notna(row[cols_map['data']]) else agora.strftime("%d/%m/%Y %H:%M:%S")

        cidade, comarca_sede, cia = identificar_localizacao_precisa(linha_texto)

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
                    try:
                        df = pd.read_csv(io.BytesIO(content_bytes), sep='|', on_bad_lines='skip')
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

# ------------------------------------------------------------------------------
# INTERFACE DO USUÁRIO (Streamlit UI)
# ------------------------------------------------------------------------------
st.sidebar.title("🚨 Filtros PMPR")
st.sidebar.markdown("**Monitor de Mandados BNMP 3.0**")

cias_padrao = ["1ª CIA (Cornélio Procópio)", "2ª CIA (Bandeirantes)", "3ª CIA (Assaí)"]

cias_selecionadas = st.sidebar.multiselect(
    "1️⃣ Selecionar Companhia(s):",
    options=list(ESTRUTURA_PMPR.keys()) + ["Outras Comarcas (Paraná)"],
    default=cias_padrao
)

# Obter Comarcas Sedes das Companhias Selecionadas
comarcas_disponiveis = []
for cia in cias_selecionadas:
    if cia in ESTRUTURA_PMPR:
        comarcas_disponiveis.extend(list(ESTRUTURA_PMPR[cia].keys()))
    else:
        comarcas_disponiveis.append("Outras Comarcas (Paraná)")

comarcas_selecionadas = st.sidebar.multiselect(
    "2️⃣ Filtrar Comarca Sede (Fórum):",
    options=comarcas_disponiveis,
    default=comarcas_disponiveis
)

# Obter Municípios Abrangidos
cidades_disponiveis = []
for cia in cias_selecionadas:
    if cia in ESTRUTURA_PMPR:
        for c_sede, m_list in ESTRUTURA_PMPR[cia].items():
            if c_sede in comarcas_selecionadas:
                cidades_disponiveis.extend(m_list)
    else:
        cidades_disponiveis.append("Outras Comarcas (Paraná)")

cidades_selecionadas = st.sidebar.multiselect(
    "3️⃣ Filtrar Município(s) Especifico(s):",
    options=cidades_disponiveis,
    default=cidades_disponiveis
)

filtro_periodo = st.sidebar.selectbox(
    "4️⃣ Período de Expedição:",
    options=[
        "📅 Todos os Mandados Salvos (Sem limite de data)",
        "⏱️ Últimos 30 dias",
        "⏱️ Últimos 60 dias",
        "⏱️ Últimos 90 dias",
        "⏱️ Últimos 180 dias"
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
        'comarca': 'Município Abrangido',
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
        file_name=f"mandados_pmpr_regiao_{datetime.date.today().strftime('%Y%m%d')}.csv",
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

# Aplicação do Filtro de Data
now = datetime.datetime.now()
mandados_periodo = []

for m in st.session_state.mandados:
    if "30 dias" in filtro_periodo:
        dt_corte = now - datetime.timedelta(days=30)
    elif "60 dias" in filtro_periodo:
        dt_corte = now - datetime.timedelta(days=60)
    elif "90 dias" in filtro_periodo:
        dt_corte = now - datetime.timedelta(days=90)
    elif "180 dias" in filtro_periodo:
        dt_corte = now - datetime.timedelta(days=180)
    else:
        dt_corte = None

    if dt_corte is None:
        mandados_periodo.append(m)
    else:
        ts = m.get('timestamp', 0)
        try:
            if datetime.datetime.fromtimestamp(ts) >= dt_corte:
                mandados_periodo.append(m)
        except Exception:
            mandados_periodo.append(m)

# Aplicação do Filtro Geográfico
mandados_filtrados = [
    m for m in mandados_periodo
    if (m.get('comarca') in cidades_selecionadas or m.get('comarca_sede') in comarcas_selecionadas or m.get('companhia') in cias_selecionadas)
]

c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.metric("Mandados Salvos (Total)", len(st.session_state.mandados))
c_m2.metric("No Período Selecionado", len(mandados_periodo))
c_m3.metric("Filtrados na Tela", len(mandados_filtrados))
c_m4.metric("Status BNMP 3.0", "Conectado", delta="Tempo Real")

st.markdown("---")

busca = st.text_input("🔍 Pesquisar por Nome, CPF, Comarca, Fórum ou Nº do Mandado:", placeholder="Digite para buscar...")
if busca:
    mandados_filtrados = [
        m for m in mandados_filtrados
        if busca.lower() in m['nome'].lower() or busca in m['id'] or busca in m['cpf'] or busca.lower() in m['comarca'].lower() or busca.lower() in m.get('comarca_sede','').lower()
    ]

mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x.get('timestamp', 0), reverse=True)

aba1, aba2, aba3 = st.tabs(["📋 Mandados Expedidos", "🚀 Importar CSV / Bookmarklet / Texto", "📊 Estatísticas"])

with aba1:
    st.subheader(f"Mandados Expedidos na Região ({len(mandados_filtrados)})")
    
    if not mandados_filtrados:
        qtd_fora = len(st.session_state.mandados) - len(mandados_filtrados)
        if qtd_fora > 0:
            st.warning(f"⚠️ Existem **{qtd_fora} mandado(s)** salvos no banco de dados, mas pertencem a outras comarcas fora dos filtros ativos.")
            st.info("💡 **Como visualizar:** Na barra lateral à esquerda, em **'1️⃣ Selecionar Companhia(s)'**, marque a opção **'Outras Comarcas (Paraná)'** para exibir os mandados do restante do estado.")
        else:
            st.info("Nenhum mandado localizado no banco de dados. Utilize a Aba 'Importar CSV / Bookmarklet' para carregar a base do BNMP 3.0.")
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
            st.markdown("#### Mandados por Município")
            st.bar_chart(df_mandados['comarca'].value_counts())
    else:
        st.write("Nenhum dado disponível para estatísticas.")
