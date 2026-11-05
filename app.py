import streamlit as st
import pandas as pd
import datetime
import json
import os
import re
import io
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

# Estrutura Organizacional da PMPR (Companhias e Cidades da Região)
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
    ],
    "Outras Comarcas (Paraná)": [
        "Londrina", "Maringá", "Curitiba", "Ponta Grossa", "Jacarezinho", "Santo Antônio da Platina",
        "Cascavel", "Foz do Iguaçu", "Guarapuava", "Toledo", "Apucarana", "Arapongas", "Campo Mourão",
        "Umuarama", "Paranavaí", "Pato Branco", "Francisco Beltrão", "Telêmaco Borba", "Jandaia do Sul"
    ]
}

ARQUIVO_DADOS = "mandados.json"

def remover_acentos(texto):
    if not texto:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")

# Tabela completa de normalização com suporte a abreviações e nomes sem acento
MAPA_NORMALIZACAO = {}
for cia_key, cidades_list in ESTRUTURA_COMPANHIAS.items():
    for c in cidades_list:
        c_clean = remover_acentos(c.lower())
        MAPA_NORMALIZACAO[c.lower()] = c
        MAPA_NORMALIZACAO[c_clean] = c
        
        if c == 'Cornélio Procópio':
            for v in ['cornelio procopio', 'c procopio', 'c. procopio', 'procopio']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Nova Fátima':
            for v in ['nova fatima', 'n fatima', 'n. fatima']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Rancho Alegre':
            for v in ['rancho alegre', 'r alegre', 'r. alegre']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Santa Amélia':
            for v in ['santa amelia', 'sta amelia', 'sta. amelia', 'st amelia']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Barra do Jacaré':
            for v in ['barra do jacare', 'b jacare', 'b. jacare', 'b. do jacare']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Santa Mariana':
            for v in ['santa mariana', 'sta mariana', 'sta. mariana', 'st mariana']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Nova América da Colina':
            for v in ['nova america da colina', 'n america colina', 'n. america da colina']: MAPA_NORMALIZACAO[v] = c
        elif c == 'São Sebastião da Amoreira':
            for v in ['sao sebastiao da amoreira', 's s amoreira', 's.s. amoreira', 's. s. amoreira', 's. sebastiao da amoreira', 'amoreira']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Santo Antônio do Paraíso':
            for v in ['santo antonio do paraiso', 'sto antonio paraiso', 'sto. antonio do paraiso', 'st. antonio do paraiso']: MAPA_NORMALIZACAO[v] = c
        elif c == 'São Jerônimo da Serra':
            for v in ['sao jeronimo da serra', 's jeronimo serra', 's. jeronimo da serra']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Santa Cecília do Pavão':
            for v in ['santa cecilia do pavao', 'sta cecilia pavao', 'sta. cecilia do pavao']: MAPA_NORMALIZACAO[v] = c
        elif c == 'Nova Santa Bárbara':
            for v in ['nova santa barbara', 'n sta barbara', 'n. sta. barbara', 'santa barbara']: MAPA_NORMALIZACAO[v] = c

def normalizar_cidade(nome_raw):
    if not nome_raw or pd.isna(nome_raw):
        return None
    raw = str(nome_raw).strip()
    if not raw or raw.lower() == 'nan':
        return None
    raw_clean = remover_acentos(raw.lower())
    if raw_clean in MAPA_NORMALIZACAO:
        return MAPA_NORMALIZACAO[raw_clean]
        
    sorted_keys = sorted(MAPA_NORMALIZACAO.keys(), key=lambda x: len(x), reverse=True)
    for key in sorted_keys:
        if len(key) >= 3 and key in raw_clean:
            return MAPA_NORMALIZACAO[key]
    return None

def identificar_companhia(cidade_nome):
    cidade_norm = normalizar_cidade(cidade_nome)
    if cidade_norm:
        for cia, cidades in ESTRUTURA_COMPANHIAS.items():
            if cidade_norm in cidades:
                return cia
    return "Outras Comarcas (Paraná)"

def extrair_cidade_de_item_ou_linha(item):
    if isinstance(item, dict):
        vals = [item.get('comarca'), item.get('orgao_expedidor'), item.get('id'), item.get('nome')]
    elif hasattr(item, 'values'):
        vals = list(item.values)
    else:
        vals = [str(item)]
        
    for val in vals:
        if pd.notna(val):
            c_norm = normalizar_cidade(val)
            if c_norm:
                return c_norm
    return "Outras Comarcas (Paraná)"

def carregar_mandados_salvos():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    clean_list = []
                    modificado = False
                    for item in dados:
                        if isinstance(item, dict):
                            # Auto-repair comarca if previously set to 'Outras Comarcas' or misclassified
                            c_norm = extrair_cidade_de_item_ou_linha(item)
                            cia_norm = identificar_companhia(c_norm)
                            
                            if item.get("comarca") != c_norm or item.get("companhia") != cia_norm:
                                item["comarca"] = c_norm
                                item["companhia"] = cia_norm
                                modificado = True
                                
                            clean_list.append(item)
                    if modificado:
                        salvar_mandados_disco(clean_list)
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
                c_norm = extrair_cidade_de_item_ou_linha(item)
                cia_norm = identificar_companhia(c_norm)
                limpos.append({
                    "id": str(item.get("id", "")),
                    "nome": str(item.get("nome", "NÃO INFORMADO")),
                    "cpf": str(item.get("cpf", "000.***.***-00")),
                    "comarca": str(c_norm),
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

def extrair_data_e_timestamp(val_data):
    agora = datetime.datetime.now()
    if pd.isna(val_data) or not val_data or str(val_data).lower() in ['nan', 'none', '']:
        return agora.strftime("%d/%m/%Y %H:%M:%S"), float(agora.timestamp())
    try:
        dt = pd.to_datetime(val_data, dayfirst=True)
        if pd.notna(dt):
            exp_str = dt.strftime("%d/%m/%Y %H:%M:%S")
            ts = float(dt.timestamp())
            return exp_str, ts
    except Exception:
        pass
    return agora.strftime("%d/%m/%Y %H:%M:%S"), float(agora.timestamp())

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
                
            c_detectada = normalizar_cidade(l)
            if c_detectada and 'cidade' not in current_record:
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
        cidade = extrair_cidade_de_item_ou_linha(b)
        orgao = str(b.get('orgao', '')).strip() or "Vara Criminal da Comarca"
        
        expedicao_str, ts = extrair_data_e_timestamp(b.get('data'))
        cia = identificar_companhia(cidade)

        if not any(m['id'] == mandado_id for m in st.session_state.mandados) and not any(m['id'] == mandado_id for m in novos_mandados):
            item = {
                "id": str(mandado_id),
                "nome": str(nome).upper(),
                "cpf": str(cpf),
                "comarca": str(cidade),
                "companhia": str(cia),
                "orgao_expedidor": str(orgao),
                "expedicao_datahora": str(expedicao_str),
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
    
    # Keyword identification
    id_keywords = ['no mandado', 'num_mandado', 'numero_mandado', 'n_mandado', 'numero da peca', 'num_peca', 'numero_peca', 'peca', 'mandado', 'id', 'numero', 'processo']
    for kw in id_keywords:
        for orig, c in zip(df.columns, cols_clean):
            if kw in c and 'id' not in cols_map:
                cols_map['id'] = orig
                break
        if 'id' in cols_map: break

    nome_keywords = ['nome do procurado', 'nome da pessoa', 'nome do reu', 'nome do individuo', 'nome procurado', 'nome pessoa', 'nome reu', 'nome completo', 'nome', 'procurado', 'pessoa', 'reu', 'individuo']
    for kw in nome_keywords:
        for orig, c in zip(df.columns, cols_clean):
            if kw in c and 'nome' not in cols_map:
                cols_map['nome'] = orig
                break
        if 'nome' in cols_map: break

    for orig, c in zip(df.columns, cols_clean):
        if 'cpf' in c and 'cpf' not in cols_map:
            cols_map['cpf'] = orig
            break

    comarca_keywords = ['comarca', 'municipio', 'cidade', 'jurisdicao', 'foro', 'orgao julgador', 'unidade judiciaria', 'localidade', 'local', 'uf / municipio', 'uf/municipio', 'vara', 'orgao']
    for kw in comarca_keywords:
        for orig, c in zip(df.columns, cols_clean):
            if kw in c and 'comarca' not in cols_map:
                cols_map['comarca'] = orig
                break
        if 'comarca' in cols_map: break

    orgao_keywords = ['orgao expedidor', 'orgao_expedidor', 'orgao julgador', 'orgao', 'vara', 'juizado', 'tribunal']
    for kw in orgao_keywords:
        for orig, c in zip(df.columns, cols_clean):
            if kw in c and 'orgao' not in cols_map and orig != cols_map.get('comarca'):
                cols_map['orgao'] = orig
                break
        if 'orgao' in cols_map: break

    data_keywords = ['data de expedicao', 'data da expedicao', 'data expedicao', 'data_expedicao', 'data emissao', 'data de emissao', 'expedicao', 'emissao', 'datahora', 'data', 'dt_expedicao']
    for kw in data_keywords:
        for orig, c in zip(df.columns, cols_clean):
            if kw in c and 'data' not in cols_map:
                cols_map['data'] = orig
                break
        if 'data' in cols_map: break

    novos_mandados = []
    
    for idx, row in df.iterrows():
        mandado_id = str(row[cols_map['id']]).strip() if 'id' in cols_map and pd.notna(row[cols_map['id']]) else f"BNMP-2026-CSV-{idx+1}"
        if not mandado_id or mandado_id == "nan":
            continue
            
        nome = str(row[cols_map['nome']]).strip().upper() if 'nome' in cols_map and pd.notna(row[cols_map['nome']]) else "NÃO INFORMADO"
        cpf = str(row[cols_map['cpf']]).strip() if 'cpf' in cols_map and pd.notna(row[cols_map['cpf']]) else "000.***.***-00"
        orgao = str(row[cols_map['orgao']]).strip() if 'orgao' in cols_map and pd.notna(row[cols_map['orgao']]) else "Vara Criminal da Comarca"
        val_data = row[cols_map['data']] if 'data' in cols_map else None

        # Extract city scanning all columns in row
        cidade = extrair_cidade_de_item_ou_linha(row)
        cia = identificar_companhia(cidade)
        expedicao_str, ts = extrair_data_e_timestamp(val_data)

        if not any(m['id'] == mandado_id for m in st.session_state.mandados) and not any(m['id'] == mandado_id for m in novos_mandados):
            item = {
                "id": str(mandado_id),
                "nome": str(nome),
                "cpf": str(cpf),
                "comarca": str(cidade),
                "companhia": str(cia),
                "orgao_expedidor": str(orgao),
                "expedicao_datahora": str(expedicao_str),
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

# BARRA LATERAL (Sidebar)
st.sidebar.title("🚨 Filtros PMPR")
st.sidebar.markdown("**Monitor de Mandados BNMP 3.0**")

# Default: Select ALL companies so no mandados are hidden by default!
cias_selecionadas = st.sidebar.multiselect(
    "1️⃣ Selecionar Companhia(s):",
    options=list(st.session_state.estruturas.keys()),
    default=list(st.session_state.estruturas.keys())
)

cidades_disponiveis = []
for cia in cias_selecionadas:
    cidades_disponiveis.extend(st.session_state.estruturas[cia])

cidades_selecionadas = st.sidebar.multiselect(
    "2️⃣ Filtrar Cidades/Municípios:",
    options=cidades_disponiveis,
    default=cidades_disponiveis
)

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

# Métricas Operacionais
c_m1, c_m2, c_m3, c_m4 = st.columns(4)

data_corte_45d = datetime.datetime.now() - datetime.timedelta(days=45)
mandados_validos_45d = []
for m in st.session_state.mandados:
    ts = m.get('timestamp', 0)
    try:
        if datetime.datetime.fromtimestamp(ts) >= data_corte_45d:
            mandados_validos_45d.append(m)
    except Exception:
        mandados_validos_45d.append(m)

cidades_sel_norm = [normalizar_cidade(c) for c in cidades_selecionadas if normalizar_cidade(c)]

mandados_filtrados = [
    m for m in mandados_validos_45d
    if normalizar_cidade(m['comarca']) in cidades_sel_norm
]

c_m1.metric("Mandados Salvos (Total)", len(st.session_state.mandados))
c_m2.metric("Ativos (Últimos 45 Dias)", len(mandados_validos_45d))
c_m3.metric("Filtrados na Tela", len(mandados_filtrados))
c_m4.metric("Status BNMP 3.0", "Conectado", delta="Tempo Real")

st.markdown("---")

busca = st.text_input("🔍 Pesquisar por Nome, CPF, Comarca ou Nº do Mandado:", placeholder="Digite para buscar...")
if busca:
    mandados_filtrados = [
        m for m in mandados_filtrados
        if busca.lower() in m['nome'].lower() or busca in m['id'] or busca in m['cpf'] or busca.lower() in m['comarca'].lower()
    ]

mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x.get('timestamp', 0), reverse=True)

aba1, aba2, aba3 = st.tabs(["📋 Mandados Expedidos", "🚀 Importar CSV / Bookmarklet / Texto", "📊 Estatísticas"])

with aba1:
    st.subheader(f"Mandados Expedidos na Região ({len(mandados_filtrados)})")
    
    if not mandados_filtrados:
        qtd_fora = len(mandados_validos_45d) - len(mandados_filtrados)
        if qtd_fora > 0:
            st.warning(f"⚠️ Existem **{qtd_fora} mandado(s) ativo(s)** nos últimos 45 dias salvos no banco de dados, mas eles pertencem a municípios fora dos filtros atualmente selecionados.")
            st.info("💡 **Como visualizar:** Na barra lateral à esquerda, em **'1️⃣ Selecionar Companhia(s)'**, marque a opção **'Outras Comarcas (Paraná)'** para exibir os mandados do restante do estado.")
        else:
            st.info("Nenhum mandado localizado no banco de dados.")
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
                    <b>Comarca/Município:</b> <span class="badge-cidade">📍 {m['comarca']}</span>
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
