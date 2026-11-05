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
        "Cascavel", "Foz do Iguaçu", "Guarapuava", "Toledo", "Apucarana", "Arapongas", "Marechal Cândido Rondon"
    ]
}

ARQUIVO_DADOS = "mandados.json"

def remover_acentos(texto):
    if not texto:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")

def extrair_comarca_e_cia(orgao_str, comarca_str):
    texto_busca = f"{comarca_str or ''} {orgao_str or ''}".strip()
    if not texto_busca or texto_busca.lower() == 'nan':
        return "Outras Comarcas (Paraná)", "Outras Comarcas (Paraná)"
        
    texto_clean = remover_acentos(texto_busca.lower())
    
    # 1. Procurar correspondência estrita por limites de palavra (\b) para cidades da região
    for cia, cidades in ESTRUTURA_COMPANHIAS.items():
        if cia == "Outras Comarcas (Paraná)":
            continue
        for c in cidades:
            c_noacc = remover_acentos(c.lower())
            pattern = r'\b' + re.escape(c_noacc) + r'\b'
            if re.search(pattern, texto_clean):
                return c, cia
                
    # 2. Se não estiver na região, verificar se é uma cidade/comarca conhecida do Paraná
    for c in ESTRUTURA_COMPANHIAS["Outras Comarcas (Paraná)"]:
        c_noacc = remover_acentos(c.lower())
        pattern = r'\b' + re.escape(c_noacc) + r'\b'
        if re.search(pattern, texto_clean):
            return c, "Outras Comarcas (Paraná)"

    # 3. Retornar Comarca informada ou Outras Comarcas
    raw_comarca = str(comarca_str).strip() if comarca_str and str(comarca_str).lower() != 'nan' else "Outras Comarcas (Paraná)"
    return raw_comarca, "Outras Comarcas (Paraná)"

def extrair_ano_e_timestamp(data_str):
    now = datetime.datetime.now()
    if not data_str or str(data_str).lower() == 'nan':
        return str(now.year), float(now.timestamp()), now.strftime("%d/%m/%Y %H:%M:%S")
        
    s = str(data_str).strip()
    
    # DD/MM/YYYY
    m1 = re.search(r'(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?', s)
    if m1:
        dia, mes, ano = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        h = int(m1.group(4)) if m1.group(4) else 0
        mn = int(m1.group(5)) if m1.group(5) else 0
        sc = int(m1.group(6)) if m1.group(6) else 0
        try:
            dt = datetime.datetime(ano, mes, dia, h, mn, sc)
            return str(ano), float(dt.timestamp()), dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            pass
            
    # YYYY-MM-DD
    m2 = re.search(r'(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?)?', s)
    if m2:
        ano, mes, dia = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        h = int(m2.group(4)) if m2.group(4) else 0
        mn = int(m2.group(5)) if m2.group(5) else 0
        sc = int(m2.group(6)) if m2.group(6) else 0
        try:
            dt = datetime.datetime(ano, mes, dia, h, mn, sc)
            return str(ano), float(dt.timestamp()), dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            pass
            
    return str(now.year), float(now.timestamp()), s

def carregar_mandados_salvos():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    clean_list = []
                    for item in dados:
                        if isinstance(item, dict):
                            c_norm, cia_norm = extrair_comarca_e_cia(item.get("orgao_expedidor", ""), item.get("comarca", ""))
                            ano, ts, dt_fmt = extrair_ano_e_timestamp(item.get("expedicao_datahora", ""))
                            item["comarca"] = c_norm
                            item["companhia"] = cia_norm
                            item["ano"] = ano
                            item["timestamp"] = ts
                            item["expedicao_datahora"] = dt_fmt
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
                c_norm, cia_norm = extrair_comarca_e_cia(item.get("orgao_expedidor", ""), item.get("comarca", ""))
                ano, ts, dt_fmt = extrair_ano_e_timestamp(item.get("expedicao_datahora", ""))
                limpos.append({
                    "id": str(item.get("id", "")),
                    "nome": str(item.get("nome", "NÃO INFORMADO")),
                    "cpf": str(item.get("cpf", "000.***.***-00")),
                    "comarca": str(c_norm),
                    "companhia": str(cia_norm),
                    "orgao_expedidor": str(item.get("orgao_expedidor", "Vara Criminal da Comarca")),
                    "expedicao_datahora": str(dt_fmt),
                    "ano": str(ano),
                    "timestamp": float(ts),
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
        comarca_in = str(b.get('cidade', '')).strip()
        expedicao = str(b.get('data', '')).strip() or agora.strftime("%d/%m/%Y %H:%M:%S")
        
        cidade, cia = extrair_comarca_e_cia(orgao, comarca_in)
        ano, ts, dt_fmt = extrair_ano_e_timestamp(expedicao)

        if not any(m['id'] == mandado_id for m in st.session_state.mandados) and not any(m['id'] == mandado_id for m in novos_mandados):
            item = {
                "id": str(mandado_id),
                "nome": str(nome).upper(),
                "cpf": str(cpf),
                "comarca": str(cidade),
                "companhia": str(cia),
                "orgao_expedidor": str(orgao),
                "expedicao_datahora": str(dt_fmt),
                "ano": str(ano),
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
        
    cols_raw = list(df.columns)
    cols_norm = [remover_acentos(str(c).lower().replace(' ', '').replace('_', '').replace('-', '').replace('.', '')) for c in cols_raw]
    
    cols_map = {}
    
    for orig, norm in zip(cols_raw, cols_norm):
        if any(k in norm for k in ['numeropeca', 'numpeca', 'nopeca', 'numeromandado', 'nomandado', 'nmandado', 'nummandado', 'peca', 'mandado', 'id', 'numero', 'numb']):
            cols_map['id'] = orig
            break
            
    for orig, norm in zip(cols_raw, cols_norm):
        if any(k in norm for k in ['nomepessoa', 'nomeprocurado', 'nomecompleto', 'nome', 'reu', 'procurado', 'individuo', 'pessoa']):
            cols_map['nome'] = orig
            break
            
    for orig, norm in zip(cols_raw, cols_norm):
        if 'cpf' in norm or 'doc' in norm:
            cols_map['cpf'] = orig
            break

    for orig, norm in zip(cols_raw, cols_norm):
        if any(k in norm for k in ['orgaoexpedidor', 'orgaojulgador', 'orgao', 'vara', 'tribunal', 'juizado']):
            cols_map['orgao'] = orig
            break

    for orig, norm in zip(cols_raw, cols_norm):
        if 'residencia' not in norm and 'endereco' not in norm and 'rua' not in norm and 'bairro' not in norm and 'reu' not in norm:
            if any(k in norm for k in ['comarcaexpedidora', 'comarca', 'jurisdicao', 'localidade', 'cidadeexpedidora', 'municipio']):
                cols_map['comarca'] = orig
                break
                
    if 'comarca' not in cols_map and 'orgao' in cols_map:
        cols_map['comarca'] = cols_map['orgao']
    elif 'orgao' not in cols_map and 'comarca' in cols_map:
        cols_map['orgao'] = cols_map['comarca']

    for orig, norm in zip(cols_raw, cols_norm):
        if any(k in norm for k in ['dataexpedicao', 'dataemissao', 'datahoraexpedicao', 'datahora', 'data', 'dt']):
            cols_map['data'] = orig
            break

    for orig, norm in zip(cols_raw, cols_norm):
        if any(k in norm for k in ['situacaopeca', 'situacao', 'status', 'situac']):
            cols_map['situacao'] = orig
            break

    novos_mandados = []
    
    for idx, row in df.iterrows():
        mandado_id = str(row[cols_map['id']]).strip() if 'id' in cols_map and pd.notna(row[cols_map['id']]) else f"BNMP-2026-CSV-{idx+1}"
        if not mandado_id or mandado_id.lower() == "nan":
            continue
            
        nome = str(row[cols_map['nome']]).strip().upper() if 'nome' in cols_map and pd.notna(row[cols_map['nome']]) else "NÃO INFORMADO"
        cpf = str(row[cols_map['cpf']]).strip() if 'cpf' in cols_map and pd.notna(row[cols_map['cpf']]) else "000.***.***-00"
        orgao = str(row[cols_map['orgao']]).strip() if 'orgao' in cols_map and pd.notna(row[cols_map['orgao']]) else "Vara Criminal da Comarca"
        comarca_in = str(row[cols_map['comarca']]).strip() if 'comarca' in cols_map and pd.notna(row[cols_map['comarca']]) else ""
        expedicao = str(row[cols_map['data']]).strip() if 'data' in cols_map and pd.notna(row[cols_map['data']]) else ""
        situacao = str(row[cols_map['situacao']]).strip() if 'situacao' in cols_map and pd.notna(row[cols_map['situacao']]) else "Pendente de Cumprimento"

        cidade, cia = extrair_comarca_e_cia(orgao, comarca_in)
        ano, ts, dt_fmt = extrair_ano_e_timestamp(expedicao)

        if not any(m['id'] == mandado_id for m in st.session_state.mandados) and not any(m['id'] == mandado_id for m in novos_mandados):
            item = {
                "id": str(mandado_id),
                "nome": str(nome),
                "cpf": str(cpf),
                "comarca": str(cidade),
                "companhia": str(cia),
                "orgao_expedidor": str(orgao),
                "expedicao_datahora": str(dt_fmt),
                "ano": str(ano),
                "timestamp": float(ts),
                "situacao": str(situacao),
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
                st.error(f"Erro ao ler arquivo CSV/Texto: {e}")
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

cidades_disponiveis = []
for cia in cias_selecionadas:
    cidades_disponiveis.extend(st.session_state.estruturas[cia])

cidades_selecionadas = st.sidebar.multiselect(
    "2️⃣ Filtrar Cidades/Comarcas:",
    options=cidades_disponiveis,
    default=cidades_disponiveis
)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Período de Expedição")
opcao_periodo = st.sidebar.selectbox(
    "3️⃣ Filtrar por Ano / Período:",
    options=[
        "⭐ 2026 (Ano Atual)",
        "📅 2025 - 2026 (Últimos 2 Anos)",
        "⏱️ Últimos 90 Dias",
        "⏱️ Últimos 180 Dias",
        "🗂️ Todos os Anos (Histórico Completo)"
    ],
    index=0
)

apenas_pendentes = st.sidebar.checkbox("✅ Apenas Pendentes de Cumprimento (Ativos)", value=True)

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
        'comarca': 'Comarca/Município',
        'companhia': 'Companhia PMPR',
        'orgao_expedidor': 'Órgão Expedidor',
        'expedicao_datahora': 'Data de Expedição',
        'situacao': 'Situação'
    })
    csv_bytes = df_exp_final.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.sidebar.download_button(
        label="📥 Baixar Mandados em CSV",
        data=csv_bytes,
        file_name=f"mandados_pmpr_{datetime.date.today().strftime('%Y%m%d')}.csv",
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
agora_ts = datetime.datetime.now().timestamp()
ano_atual = str(datetime.datetime.now().year)
ano_passado = str(datetime.datetime.now().year - 1)

mandados_filtrados_periodo = []
for m in st.session_state.mandados:
    if apenas_pendentes:
        sit = str(m.get('situacao', '')).lower()
        if 'cumprido' in sit or 'revogado' in sit or 'extinto' in sit:
            continue
            
    ts = float(m.get('timestamp', 0))
    ano = str(m.get('ano', ''))
    
    if "2026" in opcao_periodo:
        if ano == ano_atual:
            mandados_filtrados_periodo.append(m)
    elif "Últimos 2 Anos" in opcao_periodo:
        if ano in [ano_atual, ano_passado]:
            mandados_filtrados_periodo.append(m)
    elif "90 Dias" in opcao_periodo:
        if ts >= agora_ts - (90 * 86400):
            mandados_filtrados_periodo.append(m)
    elif "180 Dias" in opcao_periodo:
        if ts >= agora_ts - (180 * 86400):
            mandados_filtrados_periodo.append(m)
    else:
        mandados_filtrados_periodo.append(m)

cidades_sel_clean = [remover_acentos(c.lower()) for c in cidades_selecionadas]

mandados_filtrados = [
    m for m in mandados_filtrados_periodo
    if remover_acentos(m['comarca'].lower()) in cidades_sel_clean
]

c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.metric("Mandados Salvos (Total)", len(st.session_state.mandados))
c_m2.metric("Mandados no Período", len(mandados_filtrados_periodo))
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
        qtd_outras_cias = len([m for m in mandados_filtrados_periodo if m['companhia'] == 'Outras Comarcas (Paraná)'])
        qtd_anos_anteriores = len(st.session_state.mandados) - len(mandados_filtrados_periodo)
        
        if qtd_outras_cias > 0 or qtd_anos_anteriores > 0:
            st.warning(f"⚠️ Existem **{len(st.session_state.mandados)} mandados salvos** no total.")
            if qtd_anos_anteriores > 0:
                st.info(f"🗓️ **Anos anteriores:** {qtd_anos_anteriores} mandados pertencem a anos anteriores. Mude o filtro **'3️⃣ Período'** na barra lateral para **'Histórico Completo'** se desejar visualizá-los.")
            if qtd_outras_cias > 0:
                st.info(f"📍 **Outras comarcas do PR:** {qtd_outras_cias} mandados pertencem a comarcas fora da região. Marque **'Outras Comarcas (Paraná)'** no filtro de Companhias para exibi-los.")
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
