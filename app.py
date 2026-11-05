import streamlit as st
import pandas as pd
import datetime
import json
import os
import re

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

# Tabela de normalização para evitar divergências de caixa e acentuação
MAPA_NORMALIZACAO = {}
for cia_key, cidades_list in ESTRUTURA_COMPANHIAS.items():
    for c in cidades_list:
        MAPA_NORMALIZACAO[c.lower()] = c
        c_sem_acento = c.lower().replace('á','a').replace('ã','a').replace('â','a').replace('é','e').replace('ê','e').replace('í','i').replace('ó','o').replace('ô','o').replace('ú','u').replace('ç','c')
        MAPA_NORMALIZACAO[c_sem_acento] = c
        cap_js = " ".join([w.capitalize() for w in c.split(" ")])
        MAPA_NORMALIZACAO[cap_js.lower()] = c

def normalizar_cidade(nome_raw):
    if not nome_raw:
        return "Outras Comarcas (Paraná)"
    raw = str(nome_raw).strip()
    raw_lower = raw.lower()
    if raw_lower in MAPA_NORMALIZACAO:
        return MAPA_NORMALIZACAO[raw_lower]
    for key, oficial in MAPA_NORMALIZACAO.items():
        if key in raw_lower:
            return oficial
    return raw

def identificar_companhia(cidade_nome):
    cidade_norm = normalizar_cidade(cidade_nome)
    for cia, cidades in ESTRUTURA_COMPANHIAS.items():
        if cidade_norm in cidades:
            return cia
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
                            c_norm = normalizar_cidade(item.get("comarca", ""))
                            cia_norm = identificar_companhia(c_norm)
                            item["comarca"] = c_norm
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
                c_norm = normalizar_cidade(item.get("comarca", ""))
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
        cidade = normalizar_cidade(b.get('cidade', ''))
        orgao = str(b.get('orgao', '')).strip() or "Vara Criminal da Comarca"
        expedicao = str(b.get('data', '')).strip() or agora.strftime("%d/%m/%Y %H:%M:%S")
        
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

def processar_dataframe_csv(df):
    agora = datetime.datetime.now()
    novos_mandados = []
    
    col_map = {}
    for col in df.columns:
        c_lower = str(col).lower().strip()
        if any(k in c_lower for k in ['id', 'mandado', 'numero', 'nº', 'peca']):
            col_map['id'] = col
        elif any(k in c_lower for k in ['nome', 'procurado', 'reu', 'indivíduo', 'individuo']):
            col_map['nome'] = col
        elif 'cpf' in c_lower:
            col_map['cpf'] = col
        elif any(k in c_lower for k in ['comarca', 'cidade', 'municipio', 'município']):
            col_map['comarca'] = col
        elif any(k in c_lower for k in ['orgao', 'órgão', 'vara', 'expedidor']):
            col_map['orgao_expedidor'] = col
        elif any(k in c_lower for k in ['data', 'expedicao', 'expedição', 'datahora']):
            col_map['expedicao_datahora'] = col

    for idx, row in df.iterrows():
        mandado_id = str(row.get(col_map.get('id', ''), '')).strip()
        if not mandado_id or mandado_id.lower() == 'nan':
            continue
            
        nome = str(row.get(col_map.get('nome', ''), 'NÃO INFORMADO')).strip().upper()
        cpf = str(row.get(col_map.get('cpf', ''), '000.***.***-00')).strip()
        comarca_raw = str(row.get(col_map.get('comarca', ''), '')).strip()
        orgao = str(row.get(col_map.get('orgao_expedidor', ''), 'Vara Criminal da Comarca')).strip()
        expedicao = str(row.get(col_map.get('expedicao_datahora', ''), agora.strftime("%d/%m/%Y %H:%M:%S"))).strip()

        cidade = normalizar_cidade(comarca_raw)
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
    "2️⃣ Filtrar Cidades/Municípios:",
    options=cidades_disponiveis,
    default=cidades_disponiveis
)

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Exportar Base Completa (CSV)")

df_todos_mandados = pd.DataFrame(st.session_state.mandados)
if not df_todos_mandados.empty:
    csv_data = df_todos_mandados[['id', 'nome', 'cpf', 'comarca', 'companhia', 'orgao_expedidor', 'expedicao_datahora', 'situacao']].to_csv(index=False, encoding='utf-8-sig')
    st.sidebar.download_button(
        label="📥 Baixar Mandados em CSV",
        data=csv_data,
        file_name=f"mandados_parana_pmpr_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
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

cidades_sel_norm = [normalizar_cidade(c) for c in cidades_selecionadas]

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
        st.info("Nenhum mandado localizado para os municípios selecionados nos filtros da barra lateral.")
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
    st.subheader("🚀 Importação por Arquivo CSV / Excel ou Texto")
    
    col_csv, col_texto = st.columns(2)
    
    with col_csv:
        st.markdown("#### 📁 Opção A: Importar Arquivo CSV / Excel")
        arquivo_upload = st.file_uploader("Selecione uma planilha (.csv ou .xlsx):", type=['csv', 'xlsx'])
        if arquivo_upload is not None:
            try:
                if arquivo_upload.name.endswith('.csv'):
                    df_up = pd.read_csv(arquivo_upload)
                else:
                    df_up = pd.read_excel(arquivo_upload)
                
                qtd_csv = processar_dataframe_csv(df_up)
                if qtd_csv > 0:
                    st.success(f"✅ {qtd_csv} novo(s) mandado(s) importado(s) a partir do arquivo CSV/Excel!")
                    recarregar_app()
                else:
                    st.info("Nenhum mandado novo foi adicionado do arquivo (ou já existiam no banco).")
            except Exception as err:
                st.error(f"Erro ao ler arquivo: {err}")
                
    with col_texto:
        st.markdown("#### 📝 Opção B: Cole o Texto (Bookmarklet ou Tela BNMP)")
        texto_input = st.text_area("Texto dos Mandados Capturados:", height=180, placeholder="Cole aqui o texto copiado pelo Bookmarklet ou selecionado na tela do BNMP...")
        if st.button("📥 Processar e Salvar Texto", type="primary"):
            if texto_input.strip():
                qtd = processar_texto_importado(texto_input)
                if qtd > 0:
                    st.success(f"✅ {qtd} novo(s) mandado(s) real(is) importado(s) e salvo(s) com sucesso!")
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
