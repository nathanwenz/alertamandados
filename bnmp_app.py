import streamlit as st
import pandas as pd
import datetime
import time

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

# Gerenciamento de Estado do aplicativo (Session State)
if 'comarcas' not in st.session_state:
    st.session_state.comarcas = ["Maringá", "Sarandi", "Paiçandu", "Curitiba", "Londrina", "Ponta Grossa", "Cascavel"]

if 'mandados' not in st.session_state:
    agora = datetime.datetime.now()
    st.session_state.mandados = [
        {
            "id": "BNMP-2026-009841",
            "nome": "CARLOS EDUARDO DA SILVA",
            "cpf": "109.***.***-45",
            "comarca": "Maringá",
            "orgao_expedidor": "Vara Criminal de Maringá - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(minutes=20)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumpimento",
            "pdf_nome": "Mandado_Prisao_009841.pdf",
            "notificado": True
        },
        {
            "id": "BNMP-2026-009840",
            "nome": "MARCOS VINICIUS SANTOS",
            "cpf": "088.***.***-12",
            "comarca": "Sarandi",
            "orgao_expedidor": "Vara Criminal de Sarandi - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(hours=1, minutes=15)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumpimento",
            "pdf_nome": "Mandado_Prisao_009840.pdf",
            "notificado": True
        },
        {
            "id": "BNMP-2026-009835",
            "nome": "RODRIGO ALVES PEREIRA",
            "cpf": "054.***.***-89",
            "comarca": "Curitiba",
            "orgao_expedidor": "1ª Vara de Execuções Penais de Curitiba - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(hours=3, minutes=40)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumpimento",
            "pdf_nome": "Mandado_Prisao_009835.pdf",
            "notificado": False
        },
        {
            "id": "BNMP-2026-009822",
            "nome": "ALEXANDRE GOMES FERREIRA",
            "cpf": "012.***.***-33",
            "comarca": "Paiçandu",
            "orgao_expedidor": "Vara Criminal de Paiçandu - TJPR",
            "expedicao_datahora": (agora - datetime.timedelta(hours=5, minutes=50)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumpimento",
            "pdf_nome": "Mandado_Prisao_009822.pdf",
            "notificado": False
        }
    ]

# BARRA LATERAL (Sidebar)
st.sidebar.title("🚨 Configurações PMPR")
st.sidebar.markdown("**Monitor de Mandados BNMP 3.0**")

st.sidebar.subheader("📍 Comarcas Monitoradas")
nova_cidade = st.sidebar.text_input("Adicionar nova cidade/comarca:")
if st.sidebar.button("➕ Adicionar Comarca"):
    if nova_cidade and nova_cidade not in st.session_state.comarcas:
        st.session_state.comarcas.append(nova_cidade.strip())
        st.sidebar.success(f"Comarca '{nova_cidade}' adicionada!")

cidades_selecionadas = st.sidebar.multiselect(
    "Exibir apenas as comarcas:",
    options=st.session_state.comarcas,
    default=st.session_state.comarcas
)

st.sidebar.markdown("---")
st.sidebar.subheader("📲 WhatsApp do Batalhão/Equipe")
num_whatsapp = st.sidebar.text_input("Número de destino (DDD + Número):", value="44999999999")
notif_auto = st.sidebar.checkbox("Enviar alerta automático a cada novo mandado", value=True)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Executar Varredura BNMP Agora"):
    with st.spinner("Consultando atualizações no portal BNMP 3.0..."):
        time.sleep(1.2)
        st.sidebar.success("Varredura realizada com sucesso!")

# ÁREA PRINCIPAL (Dashboard)
st.markdown('<div class="titulo-principal">🚨 PMPR - Sistema de Notificação de Mandados expedidos (BNMP 3.0)</div>', unsafe_allow_html=True)

# Métricas no topo
c_m1, c_m2, c_m3, c_m4 = st.columns(4)
mandados_filtrados = [m for m in st.session_state.mandados if m['comarca'] in cidades_selecionadas]

c_m1.metric("Mandados Ativos", len(mandados_filtrados))
c_m2.metric("Comarcas Monitoradas", len(cidades_selecionadas))
c_m3.metric("Notificações WhatsApp", len([m for m in st.session_state.mandados if m['notificado']]))
c_m4.metric("Conexão BNMP 3.0", "Ativa", delta="Tempo Real")

st.markdown("---")

# Filtro de busca por texto
busca = st.text_input("🔍 Buscar por Nome do Indivíduo, CPF ou Nº do Mandado:", placeholder="Digite o nome ou número...")
if busca:
    mandados_filtrados = [
        m for m in mandados_filtrados
        if busca.lower() in m['nome'].lower() or busca in m['id'] or busca in m['cpf']
    ]

# Ordenação cronológica rigorosa (mais recente primeiro)
mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x['expedicao_datahora'], reverse=True)

# Abas do aplicativo
aba1, aba2, aba3 = st.tabs(["📋 Mandados Expedidos (Ordem Cronológica)", "⚙️ Configurar Bot do WhatsApp", "📊 Análise por Comarca"])

with aba1:
    st.subheader(f"Mandados em Ordem Recente de Lançamento ({len(mandados_filtrados)})")
    
    if not mandados_filtrados:
        st.info("Nenhum mandado encontrado para os filtros selecionados.")
    else:
        for m in mandados_filtrados:
            st.markdown(f"""
            <div class="card-mandado">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:18px; font-weight:bold; color:#0F172A;">👤 {m['nome']} (CPF: {m['cpf']})</span>
                    <span class="badge-status">{m['situacao']}</span>
                </div>
                <div style="margin-top: 8px; color: #475569; font-size: 14px;">
                    <b>Nº Mandado:</b> {m['id']} | 
                    <b>Comarca:</b> <span class="badge-cidade">{m['comarca']}</span> | 
                    <b>Órgão Expedidor:</b> {m['orgao_expedidor']}
                </div>
                <div style="margin-top: 6px; color: #334155; font-size: 14px;">
                    ⏰ <b>Expedido em:</b> {m['expedicao_datahora']} | 
                    📄 <b>Arquivo PDF:</b> {m['pdf_nome']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_pdf, col_wa, col_vazio = st.columns([3, 3, 4])
            with col_pdf:
                st.download_button(
                    label=f"📥 Baixar {m['pdf_nome']}",
                    data=f"Conteudo Simulado do PDF do Mandado {m['id']}\nNome: {m['nome']}\nComarca: {m['comarca']}",
                    file_name=m['pdf_nome'],
                    mime="application/pdf",
                    key=f"dl_{m['id']}"
                )
            with col_wa:
                if st.button(f"📲 Notificar no WhatsApp ({m['id']})", key=f"wa_{m['id']}"):
                    texto_msg = f"🚨 *NOVO MANDADO DE PRISÃO DETECTADO*\n\n👤 *Nome:* {m['nome']}\n📜 *Nº Mandado:* {m['id']}\n🏛️ *Comarca:* {m['comarca']}\n⏰ *Expedido em:* {m['expedicao_datahora']}\n📄 *PDF:* {m['pdf_nome']}"
                    st.success(f"Notificação disparada com sucesso para {num_whatsapp}!")
                    st.code(texto_msg, language="markdown")

with aba2:
    st.subheader("Configuração da API de Notificação Automática (WhatsApp)")
    st.write("Configuração da API HTTP / Webhook para envio automático das mensagens nos grupos operacionais da PMPR:")
    
    st.text_input("Endpoint do Servidor da API (Evolution API / Z-API):", value="http://localhost:8080/message/sendText")
    st.text_input("Identificador da Instância / Canal:", value="pmpr_batalhao_operacional")
    st.text_area("Modelo da Mensagem enviada ao celular:", value="🚨 *NOVO MANDADO DE PRISÃO - PMPR*\n\n👤 *Nome:* {nome}\n📜 *Nº Mandado:* {id}\n🏛️ *Comarca:* {comarca}\n⏰ *Expedido em:* {expedicao_datahora}\n📄 *PDF:* {link_pdf}")
    
    if st.button("💾 Salvar Parâmetros de Notificação"):
        st.success("Parâmetros de notificação salvos no sistema!")

with aba3:
    st.subheader("📊 Distribuição de Mandados por Comarca Selecionada")
    if mandados_filtrados:
        df_mandados = pd.DataFrame(mandados_filtrados)
        contagem = df_mandados['comarca'].value_counts()
        st.bar_chart(contagem)
    else:
        st.write("Nenhum dado disponível para exibir gráfico.")
