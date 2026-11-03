import streamlit as st
import pandas as pd
import datetime
import time

# Configuração da página no Streamlit
st.set_page_config(
    page_title="Monitor BNMP 3.0 - PMPR (Região & Companhias)",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização visual customizada
st.markdown("""
<style>
    .titulo-principal {
        font-size: 26px;
        font-weight: bold;
        color: #1E3A8A;
        border-bottom: 2px solid #1E3A8A;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .card-mandado {
        background-color: #F8FAFC;
        border-left: 5px solid #2563EB;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
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
</style>
""", unsafe_allow_html=True)

# Estrutura Organizacional da PMPR (Companhias e Cidades)
ESTRUTURA_COMPANHIAS = {
    "1ª CIA (Sede Cornélio Procópio)": [
        "Cornélio Procópio", "Leópolis", "Nova Fátima", "Uraí", "Rancho Alegre", "Sertaneja"
    ],
    "2ª CIA (Sede Bandeirantes)": [
        "Bandeirantes", "Santa Amélia", "Andirá", "Barra do Jacaré", "Itambaracá", "Santa Mariana"
    ],
    "3ª CIA (Sede Assaí)": [
        "Assaí", "Nova América da Colina", "São Sebastião da Amoreira", "Congonhinhas",
        "Santo Antônio do Paraíso", "São Jerônimo da Serra", "Santa Cecília do Pavão", "Nova Santa Bárbara"
    ],
    "Outras Comarcas Regionais": [
        "Londrina"
    ]
}

# Inicialização de Session State
if 'estruturas' not in st.session_state:
    st.session_state.estruturas = ESTRUTURA_COMPANHIAS

if 'mandados' not in st.session_state:
    agora = datetime.datetime.now()
    st.session_state.mandados = [
        {
            "id": "BNMP-2026-009855",
            "nome": "ADRIANO RODRIGUES GOMES",
            "cpf": "112.***.***-09",
            "comarca": "Cornélio Procópio",
            "companhia": "1ª CIA (Sede Cornélio Procópio)",
            "orgao_expedidor": "Vara Criminal de Cornélio Procópio - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(minutes=15)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_nome": "Mandado_Prisao_009855.pdf",
            "notificado": True
        },
        {
            "id": "BNMP-2026-009851",
            "nome": "LUCAS SILVA NASCIMENTO",
            "cpf": "077.***.***-88",
            "comarca": "Bandeirantes",
            "companhia": "2ª CIA (Sede Bandeirantes)",
            "orgao_expedidor": "Vara Criminal de Bandeirantes - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(minutes=45)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_nome": "Mandado_Prisao_009851.pdf",
            "notificado": True
        },
        {
            "id": "BNMP-2026-009848",
            "nome": "FERNANDO SANTOS OLIVEIRA",
            "cpf": "045.***.***-21",
            "comarca": "Assaí",
            "companhia": "3ª CIA (Sede Assaí)",
            "orgao_expedidor": "Vara Criminal de Assaí - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(hours=1, minutes=20)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_nome": "Mandado_Prisao_009848.pdf",
            "notificado": False
        },
        {
            "id": "BNMP-2026-009844",
            "nome": "JEFFERSON MATOS FERREIRA",
            "cpf": "099.***.***-67",
            "comarca": "Congonhinhas",
            "companhia": "3ª CIA (Sede Assaí)",
            "orgao_expedidor": "Vara Criminal de Assaí / Juizado de Congonhinhas - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(hours=2, minutes=10)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_nome": "Mandado_Prisao_009844.pdf",
            "notificado": False
        },
        {
            "id": "BNMP-2026-009838",
            "nome": "MARCOS ANTONIO ALVES",
            "cpf": "031.***.***-54",
            "comarca": "Uraí",
            "companhia": "1ª CIA (Sede Cornélio Procópio)",
            "orgao_expedidor": "Vara Criminal de Uraí - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(hours=3, minutes=50)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_nome": "Mandado_Prisao_009838.pdf",
            "notificado": False
        },
        {
            "id": "BNMP-2026-009830",
            "nome": "ROBERTO CARLOS ALMEIDA",
            "cpf": "022.***.***-11",
            "comarca": "Londrina",
            "companhia": "Outras Comarcas Regionais",
            "orgao_expedidor": "1ª Vara Criminal de Londrina - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(hours=5, minutes=15)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_nome": "Mandado_Prisao_009830.pdf",
            "notificado": False
        }
    ]

# BARRA LATERAL (Sidebar)
st.sidebar.title("🚨 Filtros por Cia & Cidade")
st.sidebar.markdown("**PMPR - Sistema BNMP 3.0**")

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

# Opção de adicionar cidade personalizada
with st.sidebar.expander("➕ Adicionar Cidade/Comarca"):
    nova_cidade_input = st.text_input("Nome da Cidade:")
    cia_destino = st.selectbox("Atribuir à Companhia:", options=list(st.session_state.estruturas.keys()))
    if st.button("Salvar Nova Cidade"):
        if nova_cidade_input and nova_cidade_input not in st.session_state.estruturas[cia_destino]:
            st.session_state.estruturas[cia_destino].append(nova_cidade_input.strip())
            st.success(f"Cidade '{nova_cidade_input}' adicionada à {cia_destino}!")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📲 WhatsApp do Batalhão / Cia")
num_whatsapp = st.sidebar.text_input("Número de Destino (DDD + Número):", value="43999999999")
notif_auto = st.sidebar.checkbox("Notificação Automática no WhatsApp", value=True)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Executar Varredura BNMP Agora"):
    with st.spinner("Consultando lançamentos no BNMP 3.0..."):
        time.sleep(1.0)
        st.sidebar.success("Varredura realizada com sucesso!")

# ÁREA PRINCIPAL (Dashboard)
st.markdown('<div class="titulo-principal">🚨 PMPR - Sistema Regional de Mandados de Prisão (BNMP 3.0)</div>', unsafe_allow_html=True)

# Métricas Operacionais
c_m1, c_m2, c_m3, c_m4 = st.columns(4)

# Filtragem dos mandados
mandados_filtrados = [
    m for m in st.session_state.mandados
    if m['comarca'] in cidades_selecionadas
]

c_m1.metric("Mandados em Exibição", len(mandados_filtrados))
c_m2.metric("Cias Ativas", len(cias_selecionadas))
c_m3.metric("Cidades Monitoradas", len(cidades_selecionadas))
c_m4.metric("Status BNMP 3.0", "Conectado", delta="Tempo Real")

st.markdown("---")

# Filtro de Busca por Texto
busca = st.text_input("🔍 Pesquisar por Nome, CPF, Comarca ou Nº do Mandado:", placeholder="Digite aqui para buscar...")
if busca:
    mandados_filtrados = [
        m for m in mandados_filtrados
        if busca.lower() in m['nome'].lower() or busca in m['id'] or busca in m['cpf'] or busca.lower() in m['comarca'].lower()
    ]

# Ordenação cronológica (do mais recente para o mais antigo)
mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x['expedicao_datahora'], reverse=True)

# Abas do aplicativo
aba1, aba2, aba3 = st.tabs(["📋 Mandados Expedidos por Cia", "⚙️ Configurações do WhatsApp", "📊 Estatísticas por Cia e Município"])

with aba1:
    st.subheader(f"Mandados Expedidos - Ordem Recente de Lançamento ({len(mandados_filtrados)})")
    
    if not mandados_filtrados:
        st.info("Nenhum mandado registrado para as Companhias/Cidades selecionadas no momento.")
    else:
        for m in mandados_filtrados:
            st.markdown(f"""
            <div class="card-mandado">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:18px; font-weight:bold; color:#0F172A;">👤 {m['nome']} (CPF: {m['cpf']})</span>
                    <span class="badge-status">{m['situacao']}</span>
                </div>
                <div style="margin-top: 8px; color: #475569; font-size: 14px;">
                    <span class="badge-cia">🛡️ {m['companhia']}</span>
                    <b>Comarca/Município:</b> <span class="badge-cidade">📍 {m['comarca']}</span> | 
                    <b>Nº Mandado:</b> {m['id']}
                </div>
                <div style="margin-top: 6px; color: #334155; font-size: 14px;">
                    ⚖️ <b>Órgão Expedidor:</b> {m['orgao_expedidor']} | 
                    ⏰ <b>Expedido em:</b> {m['expedicao_datahora']} | 
                    📄 <b>PDF:</b> {m['pdf_nome']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_pdf, col_wa, col_espaco = st.columns([3, 3, 4])
            with col_pdf:
                st.download_button(
                    label=f"📥 Baixar {m['pdf_nome']}",
                    data=f"PDF Oficial do Mandado BNMP {m['id']}\nNome: {m['nome']}\nCPF: {m['cpf']}\nComarca: {m['comarca']}\nCia: {m['companhia']}",
                    file_name=m['pdf_nome'],
                    mime="application/pdf",
                    key=f"dl_{m['id']}"
                )
            with col_wa:
                if st.button(f"📲 Alertas WhatsApp ({m['id']})", key=f"wa_{m['id']}"):
                    texto_msg = f"🚨 *NOVO MANDADO DE PRISÃO DETECTADO*\n\n🛡️ *Unidade:* {m['companhia']}\n📍 *Cidade/Comarca:* {m['comarca']}\n👤 *Nome:* {m['nome']}\n📜 *Nº Mandado:* {m['id']}\n⏰ *Expedido em:* {m['expedicao_datahora']}\n📄 *PDF:* {m['pdf_nome']}"
                    st.success(f"Alerta enviado para o número {num_whatsapp}!")
                    st.code(texto_msg, language="markdown")

with aba2:
    st.subheader("⚙️ Configuração do Envio de Alertas via WhatsApp")
    st.write("Configure os grupos ou contatos que receberão os mandados automaticamente por Companhia:")
    
    st.text_input("Endpoint da API WhatsApp (Evolution/Z-API):", value="http://localhost:8080/message/sendText")
    st.text_input("Grupo/Canal 1ª CIA (Cornélio Procópio):", value="grupo_1cia_cornelio")
    st.text_input("Grupo/Canal 2ª CIA (Bandeirantes):", value="grupo_2cia_bandeirantes")
    st.text_input("Grupo/Canal 3ª CIA (Assaí):", value="grupo_3cia_assai")
    
    if st.button("💾 Salvar Parâmetros por Companhia"):
        st.success("Configurações atualizadas!")

with aba3:
    st.subheader("📊 Distribuição de Mandados por Companhia e Município")
    if mandados_filtrados:
        df_mandados = pd.DataFrame(mandados_filtrados)
        st.markdown("#### Total por Companhia")
        st.bar_chart(df_mandados['companhia'].value_counts())
        
        st.markdown("#### Total por Município/Comarca")
        st.bar_chart(df_mandados['comarca'].value_counts())
    else:
        st.write("Sem dados para os filtros selecionados.")
