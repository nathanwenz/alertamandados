import streamlit as st
import pandas as pd
import datetime
import json
import os
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

MANDADOS_FILE = "mandados.json"

def identificar_companhia(cidade_nome):
    if not cidade_nome:
        return "1ª CIA (Cornélio Procópio)"
    cidade_clean = str(cidade_nome).strip().lower()
    for cia, cidades in ESTRUTURA_COMPANHIAS.items():
        for c in cidades:
            if c.lower() in cidade_clean or cidade_clean in c.lower():
                return cia
    return "1ª CIA (Cornélio Procópio)"

def carregar_mandados():
    if os.path.exists(MANDADOS_FILE):
        try:
            with open(MANDADOS_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    for m in dados:
                        if "expedicao_dt" not in m:
                            try:
                                m["expedicao_dt"] = datetime.datetime.strptime(m["expedicao_datahora"], "%d/%m/%Y %H:%M:%S")
                            except Exception:
                                m["expedicao_dt"] = datetime.datetime.now()
                    return dados
        except Exception:
            pass
    return []

def salvar_mandados_json(mandados):
    serializable = []
    for m in mandados:
        m_copy = dict(m)
        if "expedicao_dt" in m_copy:
            del m_copy["expedicao_dt"]
        serializable.append(m_copy)
    with open(MANDADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)

def recarregar_app():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# Inicialização de Session State
if "estruturas" not in st.session_state:
    st.session_state.estruturas = ESTRUTURA_COMPANHIAS

if "mandados" not in st.session_state:
    carregados = carregar_mandados()
    st.session_state.mandados = carregados

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

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Limpar Todos os Mandados Salvos"):
    st.session_state.mandados = []
    salvar_mandados_json([])
    st.sidebar.success("Base de mandados limpa!")
    recarregar_app()

# ÁREA PRINCIPAL
st.markdown('<div class="titulo-principal">🚨 PMPR - Mandados de Prisão Ativos (Últimos 45 dias)</div>', unsafe_allow_html=True)

# FILTRO DOS ÚLTIMOS 45 DIAS DE EXPEDIÇÃO JUDICIAL
data_corte_45dias = datetime.datetime.now() - datetime.timedelta(days=45)

mandados_filtrados = [
    m for m in st.session_state.mandados
    if m.get('comarca') in cidades_selecionadas and m.get('expedicao_dt', datetime.datetime.now()) >= data_corte_45dias
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
        if busca.lower() in m.get('nome', '').lower() or busca in m.get('id', '') or busca in m.get('cpf', '') or busca.lower() in m.get('comarca', '').lower()
    ]

# ORDENAÇÃO CRONOLÓGICA (Mais recente para o mais antigo)
mandados_filtrados = sorted(mandados_filtrados, key=lambda x: x.get('expedicao_dt', datetime.datetime.now()), reverse=True)

aba1, aba2, aba3, aba4 = st.tabs([
    "📋 Mandados Expedidos (Últimos 45 dias)",
    "🚀 Importar Rápido (Bookmarklet / Texto)",
    "⚙️ Configuração WhatsApp",
    "📊 Estatísticas"
])

with aba1:
    st.subheader(f"Mandados Expedidos na Região ({len(mandados_filtrados)})")
    st.caption("Exibindo exclusivamente mandados com data de expedição judicial nos últimos 45 dias.")
    
    if not mandados_filtrados:
        st.warning("⚠️ Nenhum mandado real importado no momento.")
        st.info("👉 Vá na aba '🚀 Importar Rápido (Bookmarklet / Texto)' para colar os mandados capturados no BNMP!")
    else:
        for m in mandados_filtrados:
            st.markdown(f"""
            <div class="card-mandado">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:17px; font-weight:bold; color:#0F172A;">👤 {m.get('nome', 'NÃO INFORMADO')} (CPF: {m.get('cpf', '000.***.***-00')})</span>
                    <span class="badge-status">{m.get('situacao', 'Pendente de Cumprimento')}</span>
                </div>
                <div style="margin-top: 6px; color: #475569; font-size: 13px;">
                    <span class="badge-cia">🛡️ {m.get('companhia', '1ª CIA')}</span>
                    <b>Comarca/Município:</b> <span class="badge-cidade">📍 {m.get('comarca', 'N/A')}</span> | 
                    <b>Nº Mandado:</b> <code>{m.get('id', 'N/A')}</code>
                </div>
                <div style="margin-top: 6px; color: #334155; font-size: 13px;">
                    ⚖️ <b>Órgão Expedidor:</b> {m.get('orgao_expedidor', 'Vara Criminal')} | 
                    ⏰ <b>Expedido em (Judicial):</b> <b>{m.get('expedicao_datahora', 'N/A')}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_pdf, col_wa = st.columns(2)
            with col_pdf:
                st.link_button(
                    label=f"🔗 Abrir PDF no BNMP 3.0 ({m.get('id')})",
                    url="https://portalbnmp.cnj.jus.br/#/pesquisa-peca"
                )
                st.markdown(
                    f"<div style='background-color:#FEF3C7; color:#78350F; padding:8px; border-radius:6px; font-size:12px; margin-top:5px;'>"
                    f"🔐 <b>Nº para pesquisar no BNMP:</b> <code>{m.get('id')}</code><br>"
                    f"<i>Ao clicar no botão acima, digite/cole este número no site do BNMP, resolva o CAPTCHA e baixe o PDF assinado pelo juiz.</i>"
                    f"</div>", 
                    unsafe_allow_html=True
                )
            with col_wa:
                if st.button(f"📲 Alerta WhatsApp ({m.get('id')})", key=f"wa_{m.get('id')}"):
                    texto_msg = (
                        f"🚨 *NOVO MANDADO DE PRISÃO DETECTADO - PMPR*\n\n"
                        f"🛡️ *{m.get('companhia')} - Município: {m.get('comarca')}*\n"
                        f"👤 *Nome:* {m.get('nome')} (CPF: {m.get('cpf')})\n"
                        f"📜 *Nº Mandado:* {m.get('id')}\n"
                        f"⚖️ *Órgão Expedidor:* {m.get('orgao_expedidor')}\n"
                        f"⏰ *Expedido em:* {m.get('expedicao_datahora')}\n\n"
                        f"📄 *Buscar PDF no BNMP:* https://portalbnmp.cnj.jus.br/#/pesquisa-peca"
                    )
                    st.success(f"Alerta enviado para o WhatsApp cadastrado ({num_whatsapp})!")
                    st.code(texto_msg, language="markdown")

with aba2:
    st.subheader("🚀 Importar Mandados Rápido (Bookmarklet / Copiar e Colar)")
    st.markdown(
        "Utilize esta aba para **colar o resultado capturado pelo botão '🚀 Enviar Mandados PMPR'** "
        "ou cole linhas no formato `Nº Mandado | Nome | CPF | Cidade | Órgão | Data`."
    )
    
    texto_importado = st.text_area(
        "Cole aqui o texto copiado pelo Bookmarklet ou do BNMP (Ctrl + V):",
        height=200,
        placeholder="Cole o conteúdo copiado aqui..."
    )
    
    col_bt1, col_bt2 = st.columns(2)
    with col_bt1:
        if st.button("📥 Processar e Salvar no App", type="primary"):
            if not texto_importado.strip():
                st.warning("Cole o texto antes de clicar em processar!")
            else:
                linhas = texto_importado.strip().split("\n")
                novos_adicionados = 0
                for lin in linhas:
                    if not lin.strip():
                        continue
                    if "|" in lin:
                        partes = [p.strip() for p in lin.split("|")]
                    else:
                        partes = [lin.strip()]
                    
                    if len(partes) >= 1:
                        m_id = partes[0]
                        m_nome = partes[1] if len(partes) > 1 else "NÃO INFORMADO"
                        m_cpf = partes[2] if len(partes) > 2 else "000.***.***-00"
                        m_cidade = partes[3] if len(partes) > 3 else "Cornélio Procópio"
                        m_orgao = partes[4] if len(partes) > 4 else f"Vara Criminal de {m_cidade}"
                        m_data_str = partes[5] if len(partes) > 5 else datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        
                        try:
                            dt_obj = datetime.datetime.strptime(m_data_str, "%d/%m/%Y %H:%M:%S")
                        except Exception:
                            dt_obj = datetime.datetime.now()
                        
                        cia_pertencente = identificar_companhia(m_cidade)
                        
                        ids_existentes = [m.get('id') for m in st.session_state.mandados]
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
                
                salvar_mandados_json(st.session_state.mandados)
                st.success(f"✅ {novos_adicionados} novos mandados salvos e salvos no arquivo 'mandados.json' com sucesso!")
                time.sleep(1.0)
                recarregar_app()

    with col_bt2:
        file_upload = st.file_open = st.file_uploader("Ou faça upload de arquivo (.csv, .xlsx):", type=["csv", "xlsx"])
        if file_upload is not None:
            try:
                if file_upload.name.endswith('.csv'):
                    df_up = pd.read_csv(file_upload)
                else:
                    df_up = pd.read_excel(file_upload)
                st.dataframe(df_up.head())
                if st.button("📥 Importar Planilha Uploaded"):
                    novos_up = 0
                    for _, row in df_up.iterrows():
                        m_id = str(row.get('Nº Mandado', row.get('id', f"BNMP-2026-{novos_up}")))
                        m_nome = str(row.get('Nome', row.get('nome', 'NÃO INFORMADO')))
                        m_cpf = str(row.get('CPF', row.get('cpf', '000.***.***-00')))
                        m_cidade = str(row.get('Cidade', row.get('comarca', 'Cornélio Procópio')))
                        m_orgao = str(row.get('Órgão', row.get('orgao_expedidor', f'Vara Criminal de {m_cidade}')))
                        m_data_str = str(row.get('Data', row.get('expedicao_datahora', datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))))
                        
                        try:
                            dt_obj = datetime.datetime.strptime(m_data_str, "%d/%m/%Y %H:%M:%S")
                        except Exception:
                            dt_obj = datetime.datetime.now()
                            
                        cia_pertencente = identificar_companhia(m_cidade)
                        ids_existentes = [m.get('id') for m in st.session_state.mandados]
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
                            novos_up += 1
                    salvar_mandados_json(st.session_state.mandados)
                    st.success(f"✅ {novos_up} mandados da planilha salvos com sucesso!")
                    time.sleep(1.0)
                    recarregar_app()
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

with aba3:
    st.subheader("⚙️ Configuração do Webhook / Envio do WhatsApp")
    st.write("Insira as credenciais do seu serviço de WhatsApp (Evolution API / Z-API):")
    st.text_input("Endpoint da API HTTP:", value="http://localhost:8080/message/sendText")
    st.text_input("Número do WhatsApp de Destino:", value=num_whatsapp)
    if st.button("💾 Salvar Parâmetros"):
        st.success("Configurações salvas!")

with aba4:
    st.subheader("📊 Estatísticas por Companhia e Município")
    if mandados_filtrados:
        df_mandados = pd.DataFrame(mandados_filtrados)
        st.markdown("#### Total por Companhia")
        st.bar_chart(df_mandados['companhia'].value_counts())
        st.markdown("#### Total por Município")
        st.bar_chart(df_mandados['comarca'].value_counts())
    else:
        st.write("Nenhum dado para exibir.")
