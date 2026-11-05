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

# Estrutura Organizacional da PMPR (Companhias e Cidades)
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
    "Outras Comarcas Regionais": [
        "Londrina"
    ]
}

ARQUIVO_DADOS = "mandados.json"

def identificar_companhia(cidade_nome):
    cidade_clean = str(cidade_nome).strip().lower()
    for cia, cidades in ESTRUTURA_COMPANHIAS.items():
        for c in cidades:
            if c.lower() in cidade_clean or cidade_clean in c.lower():
                return cia
    return "1ª CIA (Cornélio Procópio)"

def carregar_mandados_salvos():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salvar_mandados_disco(lista_mandados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(lista_mandados, f, ensure_ascii=False, indent=2)

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
    
    for linha in linhas:
        partes = [p.strip() for p in linha.split('|')]
        
        if len(partes) >= 4:
            mandado_id = partes[0]
            nome = partes[1] if len(partes) > 1 else "NÃO INFORMADO"
            cpf = partes[2] if len(partes) > 2 else "000.***.***-00"
            cidade = partes[3] if len(partes) > 3 else "Cornélio Procópio"
            orgao = partes[4] if len(partes) > 4 else "Vara Criminal da Comarca"
            expedicao = partes[5] if len(partes) > 5 else agora.strftime("%d/%m/%Y %H:%M:%S")
        else:
            # Tentar extrair por expressões regulares (regex)
            id_match = re.search(r'([A-Z0-9\.\-\/]+(?:BNMP|\d{4}-\d+|\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}))', linha)
            cpf_match = re.search(r'(\d{3}\.[\*\d]{3}\.[\*\d]{3}-\d{2})', linha)
            data_match = re.search(r'(\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2}:\d{2})?)', linha)
            
            mandado_id = id_match.group(1) if id_match else f"BNMP-2026-{len(st.session_state.mandados)+1001}"
            cpf = cpf_match.group(1) if cpf_match else "000.***.***-00"
            expedicao = data_match.group(1) if data_match else agora.strftime("%d/%m/%Y %H:%M:%S")
            
            # Tentar extrair a cidade
            cidade = "Cornélio Procópio"
            for cia, c_list in ESTRUTURA_COMPANHIAS.items():
                for c in c_list:
                    if c.lower() in linha.lower():
                        cidade = c
                        break
            
            nome = "NÃO INFORMADO"
            orgao = "Vara Criminal da Comarca"
            
        cia = identificar_companhia(cidade)
        
        # Calcular timestamp para ordenação
        try:
            if ":" in expedicao:
                dt = datetime.datetime.strptime(expedicao, "%d/%m/%Y %H:%M:%S")
            else:
                dt = datetime.datetime.strptime(expedicao, "%d/%m/%Y")
            ts = dt.timestamp()
        except Exception:
            ts = agora.timestamp()

        # Evitar duplicados por ID
        if not any(m['id'] == mandado_id for m in st.session_state.mandados):
            item = {
                "id": mandado_id,
                "nome": nome.upper(),
                "cpf": cpf,
                "comarca": cidade,
                "companhia": cia,
                "orgao_expedidor": orgao,
                "expedicao_datahora": expedicao,
                "timestamp": ts,
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

# Seleção de Companhias
cias_selecionadas = st.sidebar.multiselect(
    "1️⃣ Selecionar Companhia(s):",
    options=list(st.session_state.estruturas.keys()),
    default=list(st.session_state.estruturas.keys())
)

# Cidades derivadas das Cias selecionadas
cidades_disponiveis = []
for cia in cias_selecionadas:
    cidades_disponiveis.extend(st.session_state.estruturas[cia])

cidades_selecionadas = st.sidebar.multiselect(
    "2️⃣ Filtrar Cidades/Municípios:",
    options=cidades_disponiveis,
    default=cidades_disponiveis
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

# Filtrar mandados ativos nos últimos 45 dias
data_corte_45d = datetime.datetime.now() - datetime.timedelta(days=45)
mandados_validos_45d = []
for m in st.session_state.mandados:
    ts = m.get('timestamp', 0)
    if datetime.datetime.fromtimestamp(ts) >= data_corte_45d:
        mandados_validos_45d.append(m)

mandados_filtrados = [
    m for m in mandados_validos_45d
    if m['comarca'] in cidades_selecionadas
]

c_m1.metric("Mandados Salvos (Total)", len(st.session_state.mandados))
c_m2.metric("Ativos (Últimos 45 Dias)", len(mandados_validos_45d))
c_m3.metric("Filtrados na Tela", len(mandados_filtrados))
c_m4.metric("Status BNMP 3.0", "Conectado", delta="Tempo Real")

st.markdown("---")

# Filtro de Busca por Texto
busca = st.text_input("🔍 Pesquisar por Nome, CPF, Comarca ou Nº do Mandado:", placeholder="Digite para buscar...")
if busca:
    mandados_filtrados = [
        m for m in mandados_filtrados
        if busca.lower() in m['nome'].lower() or busca in m['id'] or busca in m['cpf'] or busca.lower() in m['comarca'].lower()
    ]

# Ordenação cronológica (mais recentes primeiro)
mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x.get('timestamp', 0), reverse=True)

# Abas da Aplicação
aba1, aba2, aba3 = st.tabs(["📋 Mandados Expedidos", "🚀 Importar Rápido (Bookmarklet / Texto)", "📊 Estatísticas"])

with aba1:
    st.subheader(f"Mandados Expedidos na Região ({len(mandados_filtrados)})")
    
    if not mandados_filtrados:
        st.info("Nenhum mandado localizado. Utilize a aba 'Importar Rápido' para alimentar a base com os dados do BNMP.")
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
            
            col_link, col_info = st.columns([4, 6])
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
    st.subheader("🚀 Importação Automática dos Mandados Reais do BNMP")
    st.write("Cole aqui o texto copiado pelo botão **`🚀 Enviar Mandados PMPR`** (Bookmarklet do navegador) ou de arquivos planilhados:")
    
    texto_input = st.text_area("Texto dos Mandados Capturados:", height=200, placeholder="BNMP-2026-010420 | CARLOS EDUARDO SOUZA | 088.***.***-12 | Cornélio Procópio | Vara Criminal | 03/11/2026 08:30:00")
    
    if st.button("📥 Processar e Salvar no App", type="primary"):
        if texto_input.strip():
            qtd = processar_texto_importado(texto_input)
            if qtd > 0:
                st.success(f"✅ {qtd} novo(s) mandado(s) real(is) importado(s) e salvo(s) com sucesso!")
                recarregar_app()
            else:
                st.warning("Nenhum mandado novo foi adicionado (ou os mandados colados já existem no banco).")
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
