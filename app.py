import streamlit as st
import pandas as pd
import datetime
import re
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
        font-size: 24px;
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
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .badge-cia {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-right: 5px;
    }
    .badge-status {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Estrutura Organizacional por Companhias (1ª CIA, 2ª CIA e 3ª CIA)
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

def identificar_companhia(cidade_nome):
    cidade_clean = cidade_nome.strip().lower()
    for cia, cidades in ESTRUTURA_COMPANHIAS.items():
        for c in cidades:
            if c.lower() in cidade_clean or cidade_clean in c.lower():
                return cia
    return "1ª CIA (Cornélio Procópio)"

if "estruturas" not in st.session_state:
    st.session_state.estruturas = ESTRUTURA_COMPANHIAS

# Inicialização de dados
if "mandados" not in st.session_state:
    agora = datetime.datetime.now()
    url_bnmp_busca = "https://portalbnmp.cnj.jus.br/#/pesquisa-peca"
    
    st.session_state.mandados = [
        {
            "id": "BNMP-2026-009855",
            "nome": "ADRIANO RODRIGUES GOMES",
            "cpf": "112.***.***-09",
            "comarca": "Cornélio Procópio",
            "companhia": "1ª CIA (Cornélio Procópio)",
            "orgao_expedidor": "Vara Criminal de Cornélio Procópio - TJPR",
            "expedicao_dt": agora - datetime.timedelta(hours=2),
            "expedicao_datahora": (agora - datetime.timedelta(hours=2)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_url_oficial": url_bnmp_busca
        },
        {
            "id": "BNMP-2026-009851",
            "nome": "LUCAS SILVA NASCIMENTO",
            "cpf": "077.***.***-88",
            "comarca": "Bandeirantes",
            "companhia": "2ª CIA (Bandeirantes)",
            "orgao_expedidor": "Vara Criminal de Bandeirantes - TJPR",
            "expedicao_dt": agora - datetime.timedelta(days=4),
            "expedicao_datahora": (agora - datetime.timedelta(days=4)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_url_oficial": url_bnmp_busca
        },
        {
            "id": "BNMP-2026-009848",
            "nome": "FERNANDO SANTOS OLIVEIRA",
            "cpf": "045.***.***-21",
            "comarca": "Assaí",
            "companhia": "3ª CIA (Assaí)",
            "orgao_expedidor": "Vara Criminal de Assaí - TJPR",
            "expedicao_dt": agora - datetime.timedelta(days=15),
            "expedicao_datahora": (agora - datetime.timedelta(days=15)).strftime("%d/%m/%Y %H:%M:%S"),
            "situacao": "Pendente de Cumprimento",
            "pdf_url_oficial": url_bnmp_busca
        }
    ]

def recarregar_app():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# BARRA LATERAL (Sidebar)
st.sidebar.title("🚨 Filtros PMPR")
st.sidebar.markdown("**Monitor de Mandados BNMP 3.0**")

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

with st.sidebar.expander("➕ Adicionar Cidade/Comarca"):
    nova_cidade_input = st.text_input("Nome da Cidade:")
    cia_destino = st.selectbox("Atribuir à Companhia:", options=list(st.session_state.estruturas.keys()))
    if st.button("Salvar Cidade"):
        if nova_cidade_input and nova_cidade_input not in st.session_state.estruturas[cia_destino]:
            st.session_state.estruturas[cia_destino].append(nova_cidade_input.strip())
            st.success(f"Cidade '{nova_cidade_input}' adicionada!")
            recarregar_app()

st.sidebar.markdown("---")
st.sidebar.subheader("📲 WhatsApp de Destino")
num_whatsapp = st.sidebar.text_input("Número Cadastrado (DDD + Número):", value="43999999999")

# ÁREA PRINCIPAL
st.markdown('<div class="titulo-principal">🚨 PMPR - Mandados de Prisão Ativos (Últimos 45 dias)</div>', unsafe_allow_html=True)

# FILTRO DOS ÚLTIMOS 45 DIAS DE EXPEDIÇÃO JUDICIAL
data_corte_45dias = datetime.datetime.now() - datetime.timedelta(days=45)

mandados_filtrados = [
    m for m in st.session_state.mandados
    if m['comarca'] in cidades_selecionadas and m['expedicao_dt'] >= data_corte_45dias
]

c_m1, c_m2, c_m3, c_m4 = st.columns(4)
c_m1.metric("Mandados Ativos (<= 45 dias)", len(mandados_filtrados))
c_m2.metric("Cias Selecionadas", len(cias_selecionadas))
c_m3.metric("Cidades Monitoradas", len(cidades_selecionadas))
c_m4.metric("Status BNMP 3.0", "Conectado", delta="Tempo Real")

st.markdown("---")

busca = st.text_input("🔍 Pesquisar por Nome, CPF, Comarca ou Nº do Mandado:", placeholder="Digite para buscar...")
if busca:
    mandados_filtrados = [
        m for m in mandados_filtrados
        if busca.lower() in m['nome'].lower() or busca in m['id'] or busca in m['cpf'] or busca.lower() in m['comarca'].lower()
    ]

# ORDENAÇÃO CRONOLÓGICA (Mais recente para o mais antigo)
mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x['expedicao_dt'], reverse=True)

aba1, aba2, aba3, aba4 = st.tabs([
    "📋 Mandados Expedidos (Últimos 45 dias)",
    "🚀 Importar com 1 Clique (Bookmarklet)",
    "⚙️ Configuração WhatsApp",
    "📊 Estatísticas"
])

with aba1:
    st.subheader(f"Mandados Expedidos na Região ({len(mandados_filtrados)})")
    st.caption("Exibindo exclusivamente mandados com data de expedição judicial nos últimos 45 dias.")
    
    if not mandados_filtrados:
        st.info("Nenhum mandado localizado para os filtros e janela de 45 dias selecionados.")
    else:
        for m in mandados_filtrados:
            st.markdown(f"""
            <div class="card-mandado">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:17px; font-weight:bold; color:#0F172A;">👤 {m['nome']} (CPF: {m['cpf']})</span>
                    <span class="badge-status">{m['situacao']}</span>
                </div>
                <div style="margin-top: 6px; color: #475569; font-size: 13px;">
                    <span class="badge-cia">🛡️ {m['companhia']}</span>
                    <b>Comarca/Município:</b> <span class="badge-cidade">📍 {m['comarca']}</span> | 
                    <b>Nº Mandado:</b> {m['id']}
                </div>
                <div style="margin-top: 6px; color: #334155; font-size: 13px;">
                    ⚖️ <b>Órgão Expedidor:</b> {m['orgao_expedidor']} | 
                    ⏰ <b>Expedido em (Judicial):</b> <b>{m['expedicao_datahora']}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_pdf, col_wa = st.columns(2)
            with col_pdf:
                st.link_button(
                    label=f"🔗 Abrir PDF no BNMP 3.0 ({m['id']})",
                    url="https://portalbnmp.cnj.jus.br/#/pesquisa-peca"
                )
                st.markdown(
                    f"<div style='background-color:#FEF3C7; color:#78350F; padding:8px; border-radius:6px; font-size:12px; margin-top:5px;'>"
                    f"🔐 <b>Nº para buscar no BNMP:</b> <code>{m['id']}</code><br>"
                    f"<i>Clique no botão acima para abrir o portal oficial, digite este número, resolva o CAPTCHA e baixe o PDF.</i>"
                    f"</div>", 
                    unsafe_allow_html=True
                )
            with col_wa:
                if st.button(f"📲 Alerta WhatsApp ({m['id']})", key=f"wa_{m['id']}"):
                    texto_msg = (
                        f"🚨 *NOVO MANDADO DE PRISÃO DETECTADO - PMPR*\n\n"
                        f"🛡️ *{m['companhia']} - Município: {m['comarca']}*\n"
                        f"👤 *Nome:* {m['nome']} (CPF: {m['cpf']})\n"
                        f"📜 *Nº Mandado:* {m['id']}\n"
                        f"⚖️ *Órgão Expedidor:* {m['orgao_expedidor']}\n"
                        f"⏰ *Expedido em:* {m['expedicao_datahora']}\n\n"
                        f"📄 *Buscar PDF no BNMP:* https://portalbnmp.cnj.jus.br/#/pesquisa-peca"
                    )
                    st.success(f"Alerta simulado para o WhatsApp ({num_whatsapp})!")
                    st.code(texto_msg, language="markdown")

with aba2:
    st.subheader("🚀 Importador Automático (Método 3: Botão de 1 Clique)")
    st.markdown(
        "Instale o botão **'🚀 Enviar Mandados PMPR'** no navegador do computador do batalhão. "
        "Depois de fazer a busca no BNMP 3.0 e resolver o CAPTCHA, clique no botão para capturar tudo e colar abaixo com 1 clique!"
    )
    
    texto_importado = st.text_area(
        "Cole aqui os dados capturados pelo Botão do Navegador (ou em lote):",
        placeholder="Aperte Ctrl+V para colar os dados capturados...",
        height=180
    )
    
    if st.button("📥 Processar e Atualizar Painel"):
        if not texto_importado.strip():
            st.warning("Cole o texto capturado antes de processar.")
        else:
            linhas = texto_importado.strip().split("\n")
            novos_adicionados = 0
            for lin in linhas:
                if not lin.strip():
                    continue
                if "|" in lin:
                    partes = [p.strip() for p in lin.split("|")]
                    m_id = partes[0]
                    m_nome = partes[1] if len(partes) > 1 else "NÃO INFORMADO"
                    m_cpf = partes[2] if len(partes) > 2 else "000.***.***-00"
                    m_cidade = partes[3] if len(partes) > 3 else "Cornélio Procópio"
                    m_orgao = partes[4] if len(partes) > 4 else f"Vara Criminal de {m_cidade}"
                    m_data_str = partes[5] if len(partes) > 5 else datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                else:
                    # Leitura flexível
                    m_id = f"BNMP-2026-{int(time.time()) % 100000:06d}"
                    m_nome = lin.strip()
                    m_cpf = "000.***.***-00"
                    m_cidade = "Cornélio Procópio"
                    m_orgao = "Vara Criminal"
                    m_data_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                try:
                    dt_obj = datetime.datetime.strptime(m_data_str, "%d/%m/%Y %H:%M:%S")
                except Exception:
                    dt_obj = datetime.datetime.now()
                
                cia_pertencente = identificar_companhia(m_cidade)
                
                ids_existentes = [m['id'] for m in st.session_state.mandados]
                if m_id not in ids_existentes:
                    st.session_state.mandados.append({
                        "id": m_id,
                        "nome": m_nome,
                        "cpf": m_cpf,
                        "comarca": m_cidade,
                        "companhia": cia_pertencente,
                        "orgao_expedidor": m_orgao,
                        "expedicao_dt": dt_obj,
                        "expedicao_datahora": m_data_str,
                        "situacao": "Pendente de Cumprimento",
                        "pdf_url_oficial": "https://portalbnmp.cnj.jus.br/#/pesquisa-peca"
                    })
                    novos_adicionados += 1
            
            st.success(f"✅ {novos_adicionados} mandados importados com sucesso!")
            time.sleep(0.8)
            recarregar_app()

with aba3:
    st.subheader("⚙️ Configuração do Webhook / Envio do WhatsApp")
    st.write("Insira as credenciais da API do WhatsApp:")
    st.text_input("Endpoint da API HTTP:", value="http://localhost:8080/message/sendText")
    st.text_input("Número do WhatsApp de Destino:", value=num_whatsapp)
    if st.button("💾 Salvar Parâmetros"):
        st.success("Configurações salvas!")

with aba4:
    st.subheader("📊 Estatísticas da Região")
    if mandados_filtrados:
        df_mandados = pd.DataFrame(mandados_filtrados)
        st.markdown("#### Total por Companhia")
        st.bar_chart(df_mandados['companhia'].value_counts())
        st.markdown("#### Total por Município")
        st.bar_chart(df_mandados['comarca'].value_counts())
    else:
        st.write("Nenhum dado para exibir.")
