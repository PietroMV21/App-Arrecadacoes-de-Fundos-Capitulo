import streamlit as st
import pandas as pd
import os
import json
from PIL import Image
from datetime import datetime
import altair as alt
import unicodedata
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

# --- 1. CONFIGURAÇÃO INICIAL E LOGO ---
caminho_logo = "Brasão CDS PNG.png"
tem_logo = os.path.exists(caminho_logo)

try:
    img_icon = Image.open(caminho_logo) if tem_logo else "🍗"
except:
    img_icon = "🍗"

st.set_page_config(
    page_title="Controle de Ingressos - Galeto",
    page_icon=img_icon,
    layout="wide"
)

CONFIG_FILE = "config_galeto.json"
IMG_DIR = "comprovantes"

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

if "ingresso_edit" not in st.session_state:
    st.session_state.ingresso_edit = None

def selecionar_ingresso(id_ing):
    if st.session_state.ingresso_edit == id_ing:
        st.session_state.ingresso_edit = None
    else:
        st.session_state.ingresso_edit = id_ing

# --- 2. CONFIGURAÇÕES, PLANILHA NA NUVEM E IMAGENS ---

LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1kpbNVDhO4OGd0rxcsCA71qWqYkZKmS7MwJEnTveCwPA/edit?usp=sharing"

def conectar_google_sheets():
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    cred_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    credentials = Credentials.from_service_account_info(cred_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    return gc.open_by_url(LINK_PLANILHA).sheet1

try:
    planilha_bd = conectar_google_sheets()
except Exception as e:
    st.error(f"Erro ao conectar ao Google Sheets. Verifique os Secrets. Erro: {e}")
    st.stop()

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if "vendedores_extras" not in config:
                config["vendedores_extras"] = []
            if "vendedores_ocultos" not in config:
                config["vendedores_ocultos"] = []
            return config
    return {"total_ingressos": 200, "data_evento": datetime.now().strftime("%Y-%m-%d"), "vendedores_extras": [], "vendedores_ocultos": []}

def salvar_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

config_app = carregar_config()

def ler_dados_nuvem():
    dados = planilha_bd.get_all_records()
    if not dados:
        df = pd.DataFrame(columns=["ID_Ingresso", "Vendedor", "Status", "Observacao", "Comprovante", "Retirado"])
        return df
    
    df = pd.DataFrame(dados)
    df['ID_Num'] = pd.to_numeric(df['ID_Ingresso'], errors='coerce')
    df = df.sort_values('ID_Num').drop(columns=['ID_Num'])
    df.fillna("", inplace=True) 
    return df

df_dados = ler_dados_nuvem()

def salvar_dados_nuvem(df):
    planilha_bd.clear()
    lista_dados = [df.columns.values.tolist()] + df.fillna("").astype(str).values.tolist()
    planilha_bd.update(values=lista_dados, range_name='A1')

def upload_comprovante_nuvem(arquivo):
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": st.secrets["IMGBB_API_KEY"],
        "image": base64.b64encode(arquivo.getvalue()).decode("utf-8")
    }
    res = requests.post(url, data=payload)
    return res.json()["data"]["url"]

# --- 3. TRATAMENTO DE NOMES E ORDENAÇÃO ---
lista_base = ["Bernardo", "Caetano", "Gabriel", "Gabriel Medina", "Guilherme", "Guilherme Evangelho", 
              "Gustavinho", "Henrique De Oliveira", "Ícaro", "Iuri", "João", "José Vicente", "Leonel", 
              "Linhares", "Luis Felipe", "Matheus", "Miguel", "Nicolas", "Pedro Terra", "Pietro", 
              "Ramiro", "Teodoro", "Thierry"]

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

todos_iniciais = set(df_dados["Vendedor"].unique()) | set(lista_base) | set(config_app.get("vendedores_extras", []))

ocultos = set(config_app.get("vendedores_ocultos", []))
ativos_com_ingresso = set(df_dados["Vendedor"].unique())
ocultos_validos = ocultos - ativos_com_ingresso 

lista_todos_meninos = sorted(list(todos_iniciais - ocultos_validos), key=strip_accents)

def get_cor_status(status):
    if status == "Não Vendido": return "🔴"
    if status == "Aguardando Pagamento": return "🟡"
    if status == "Pago": return "🟢"
    return "⚪"

def exibir_blocos_ingressos(df_filtrado, prefixo_chave):
    n_cols = 10
    for i in range(0, len(df_filtrado), n_cols):
        cols = st.columns(n_cols)
        lote = df_filtrado.iloc[i:i+n_cols]
        for j, (idx, row) in enumerate(lote.iterrows()):
            icone = get_cor_status(row['Status'])
            retirado_mark = " ✔️" if row['Retirado'] == "Sim" else ""
            cols[j].button(f"{icone} {row['ID_Ingresso']}{retirado_mark}", 
                           key=f"{prefixo_chave}_{row['ID_Ingresso']}_{idx}", 
                           on_click=selecionar_ingresso, args=(row['ID_Ingresso'],))

# --- 4. MENU LATERAL ---
if tem_logo:
    try:
        st.sidebar.image(Image.open(caminho_logo), use_container_width=True)
    except:
        pass
st.sidebar.title("🍗 Galeto do Capítulo")
menu = st.sidebar.radio("Navegação", ["🏠 Página Inicial", "👦 Área do Vendedor", "💼 Tesouraria", "⚙️ Configurações"])

from datetime import timezone, timedelta

fuso_brasil = timezone(timedelta(hours=-3))
hoje = datetime.now(fuso_brasil).date()

data_ev = datetime.strptime(config_app["data_evento"], "%Y-%m-%d").date()
dias_faltantes = (data_ev - hoje).days

# --- 5. PÁGINA INICIAL ---
if menu == "🏠 Página Inicial":
    st.title("📊 Dashboard do Evento")
    
    if dias_faltantes > 0:
        st.info(f"⏳ Faltam **{dias_faltantes} dias** para o nosso Galeto!")
    elif dias_faltantes == 0:
        st.success("🎉 O Galeto é HOJE! Bom trabalho a todos!")
    
    pagos = len(df_dados[df_dados["Status"] == "Pago"])
    aguardando = len(df_dados[df_dados["Status"] == "Aguardando Pagamento"])
    vendidos_total = pagos + aguardando
    total_estipulado = config_app["total_ingressos"]
    nao_vendidos = max(total_estipulado - vendidos_total, 0)
    retirados = len(df_dados[df_dados["Retirado"] == "Sim"])
    
    prog_pagos = min(pagos / total_estipulado, 1.0) if total_estipulado > 0 else 0
    prog_aguardando = min(aguardando / total_estipulado, 1.0) if total_estipulado > 0 else 0
    prog_vendidos = min(vendidos_total / total_estipulado, 1.0) if total_estipulado > 0 else 0
    prog_nao_vendidos = min(nao_vendidos / total_estipulado, 1.0) if total_estipulado > 0 else 0
    prog_retirados = min(retirados / vendidos_total, 1.0) if vendidos_total > 0 else 0
    
    st.markdown("### 📈 Resumo de Arrecadação")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🟢 Pagos", pagos)
        st.progress(prog_pagos)
    with col2:
        st.metric("🟡 Aguardando", aguardando)
        st.progress(prog_aguardando)
    with col3:
        st.metric("🔥 Total Vendidos", vendidos_total)
        st.progress(prog_vendidos)
    with col4:
        st.metric("🔴 Não Vendidos", nao_vendidos)
        st.progress(prog_nao_vendidos)
    with col5:
        st.metric("🍗 Galetos Retirados", retirados)
        st.progress(prog_retirados)
        
    st.markdown("---")
    col_chart1, col_chart2 = st.columns([1, 2])
    
    with col_chart1:
        st.subheader("Pizza de Status")
        source = pd.DataFrame({
            "Status": ["Pagos", "Aguardando", "Não Vendidos"],
            "Quantidade": [pagos, aguardando, nao_vendidos]
        })
        pie_chart = alt.Chart(source).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Quantidade", type="quantitative"),
            color=alt.Color(field="Status", type="nominal", scale=alt.Scale(domain=["Pagos", "Aguardando", "Não Vendidos"], range=["#28a745", "#ffc107", "#dc3545"])),
            tooltip=["Status", "Quantidade"]
        )
        st.altair_chart(pie_chart, use_container_width=True)

    with col_chart2:
        st.subheader("🏆 Top 10 Vendedores")
        df_vendidos = df_dados[df_dados["Status"].isin(["Pago", "Aguardando Pagamento"])]
        vendas_count = df_vendidos['Vendedor'].value_counts().reset_index()
        vendas_count.columns = ['Vendedor', 'Vendas']
        
        todos = pd.DataFrame({'Vendedor': lista_todos_meninos})
        ranking = pd.merge(todos, vendas_count, on='Vendedor', how='left').fillna(0)
        ranking['Vendas'] = ranking['Vendas'].astype(int)
        ranking = ranking.sort_values(by=['Vendas', 'Vendedor'], ascending=[False, True]).head(10)
        
        chart = alt.Chart(ranking).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
            x=alt.X('Vendedor:N', sort=None, title='', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Vendas:Q', title='Ingressos Vendidos'),
            color=alt.Color('Vendas:Q', scale=alt.Scale(scheme='greens'), legend=None),
            tooltip=['Vendedor', 'Vendas']
        ).properties(height=350)
        
        st.altair_chart(chart, use_container_width=True)

# --- 6. ÁREA DO VENDEDOR ---
elif menu == "👦 Área do Vendedor":
    st.title("👦 Gestão dos Meus Ingressos")
    vendedor_sel = st.selectbox("Selecione seu nome (Ordem Alfabética):", ["..."] + lista_todos_meninos)
    
    if vendedor_sel != "...":
        df_meus = df_dados[df_dados["Vendedor"] == vendedor_sel]
        
        if df_meus.empty:
            st.warning("Você ainda não tem ingressos atrelados ao seu nome. Fale com a Tesouraria.")
        else:
            st.write(f"Você possui **{len(df_meus)}** ingressos atrelados. Clique no bloco para editar:")
            exibir_blocos_ingressos(df_meus, "btn_vend")
            
            if st.session_state.ingresso_edit in df_meus["ID_Ingresso"].values:
                ing_id = st.session_state.ingresso_edit
                idx = df_dados[df_dados["ID_Ingresso"] == ing_id].index[0]
                dados_atuais = df_dados.loc[idx]
                
                with st.expander(f"📝 Editando Ingresso {ing_id}", expanded=True):
                    novo_status = st.selectbox("Status de Pagamento:", ["Não Vendido", "Aguardando Pagamento", "Pago"], index=["Não Vendido", "Aguardando Pagamento", "Pago"].index(dados_atuais["Status"]))
                    
                    tem_obs = bool(str(dados_atuais["Observacao"]).strip())
                    quer_obs = st.checkbox("Adicionar/Editar Observação", value=tem_obs, key=f"check_obs_vend_{ing_id}_{idx}")
                    
                    if quer_obs:
                        nova_obs = st.text_input("Observação:", value=dados_atuais["Observacao"], key=f"txt_obs_vend_{ing_id}_{idx}")
                    else:
                        nova_obs = ""
                        
                    comprovante_file = st.file_uploader("🧾 Anexar Comprovante PIX", type=["png", "jpg", "jpeg"])
                    
                    col_sv1, col_sv2 = st.columns([1, 4])
                    if col_sv1.button("💾 Salvar", key=f"save_vend_{idx}"):
                        df_dados.at[idx, "Status"] = novo_status
                        df_dados.at[idx, "Observacao"] = nova_obs
                        
                        if comprovante_file is not None:
                            link_foto = upload_comprovante_nuvem(comprovante_file)
                            df_dados.at[idx, "Comprovante"] = link_foto
                            
                        salvar_dados_nuvem(df_dados)
                        st.success("Atualizado na Nuvem com Sucesso!")
                        st.session_state.ingresso_edit = None
                        st.rerun()
                    if col_sv2.button("❌ Cancelar", key=f"canc_vend_{idx}"):
                        st.session_state.ingresso_edit = None
                        st.rerun()

# --- 7. TESOURARIA ---
elif menu == "💼 Tesouraria":
    st.title("💼 Painel de Controle da Tesouraria")
    
    senha_acesso_painel = st.text_input("Digite a Senha da Tesouraria para liberar o acesso:", type="password", key="senha_acesso_painel_tes")
    
    if senha_acesso_painel == "2102":
        pagos = len(df_dados[df_dados["Status"] == "Pago"])
        aguardando = len(df_dados[df_dados["Status"] == "Aguardando Pagamento"])
        vendidos_total = pagos + aguardando
        total_estipulado = config_app["total_ingressos"]
        nao_vendidos = max(total_estipulado - vendidos_total, 0)
        retirados = len(df_dados[df_dados["Retirado"] == "Sim"])
        
        st.info(f"**Resumo em Tempo Real:**")
        col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
        col_t1.metric("🟢 Pagos", pagos)
        col_t2.metric("🟡 Aguardando", aguardando)
        col_t3.metric("🔥 Total Vendidos", vendidos_total)
        col_t4.metric("🔴 Não Vendidos", nao_vendidos)
        col_t5.metric("🍗 Retirados", retirados)
        st.markdown("---")
        
        aba_geral, aba_admin, aba_membros = st.tabs(["👁️ Visão Geral e Edição", "➕ Atribuir Ingressos", "👥 Gerenciar Meninos"])
        
        with aba_geral:
            busca = st.text_input("🔍 Buscar por Nome do Menino ou Número do Ingresso:").strip()
            st.write("")
            
            for vendedor in lista_todos_meninos:
                df_vend = df_dados[df_dados["Vendedor"] == vendedor]
                
                if not df_vend.empty:
                    nome_busca_limpo = strip_accents(busca.lower())
                    nome_vendedor_limpo = strip_accents(vendedor.lower())
                    
                    match_vendedor = nome_busca_limpo in nome_vendedor_limpo
                    match_ingresso = any(busca in str(ing) for ing in df_vend["ID_Ingresso"].values)
                    
                    if busca == "" or match_vendedor or match_ingresso:
                        df_exibir = df_vend
                        if busca != "" and not match_vendedor and match_ingresso:
                            df_exibir = df_vend[df_vend["ID_Ingresso"].astype(str).str.contains(busca, case=False)]
                        
                        st.markdown(f"**👤 {vendedor}** ({len(df_vend)} ingressos)")
                        exibir_blocos_ingressos(df_exibir, "btn_tes")
                        
                        if st.session_state.ingresso_edit in df_exibir["ID_Ingresso"].values:
                            ing_id = st.session_state.ingresso_edit
                            idx = df_exibir[df_exibir["ID_Ingresso"] == ing_id].index[0]
                            dados_atuais = df_dados.loc[idx]
                            
                            with st.expander(f"🛠️ Editando Ingresso {ing_id} - Dono: {dados_atuais['Vendedor']}", expanded=True):
                                col_ed1, col_ed2 = st.columns(2)
                                with col_ed1:
                                    novo_status = st.selectbox("Status:", ["Não Vendido", "Aguardando Pagamento", "Pago"], index=["Não Vendido", "Aguardando Pagamento", "Pago"].index(dados_atuais["Status"]), key=f"sel_status_tes_{ing_id}_{idx}")
                                    
                                    tem_obs = bool(str(dados_atuais["Observacao"]).strip())
                                    quer_obs = st.checkbox("Adicionar/Editar Observação", value=tem_obs, key=f"obs_tes_{ing_id}_{idx}")
                                    if quer_obs:
                                        nova_obs = st.text_input("Observação:", value=dados_atuais["Observacao"], key=f"txt_tes_{ing_id}_{idx}")
                                    else:
                                        nova_obs = ""
                                        
                                with col_ed2:
                                    novo_retirado = st.radio("Galeto Retirado?", ["Não", "Sim"], index=["Não", "Sim"].index(dados_atuais["Retirado"]), key=f"rad_ret_tes_{ing_id}_{idx}")
                                    
                                if dados_atuais["Comprovante"] != "":
                                    st.markdown(f"[🔗 Ver Comprovante em Tela Cheia]({dados_atuais['Comprovante']})")
                                    st.image(dados_atuais["Comprovante"], width=250)
                                    
                                col_b1, col_b2 = st.columns([1, 4])
                                if col_b1.button("💾 Salvar", key=f"sv_tes_{ing_id}_{idx}"):
                                    df_dados.at[idx, "Status"] = novo_status
                                    df_dados.at[idx, "Observacao"] = nova_obs
                                    df_dados.at[idx, "Retirado"] = novo_retirado
                                    salvar_dados_nuvem(df_dados)
                                    st.success("Salvo com sucesso na Planilha!")
                                    st.session_state.ingresso_edit = None
                                    st.rerun()
                                if col_b2.button("❌ Cancelar", key=f"cc_tes_{ing_id}_{idx}"):
                                    st.session_state.ingresso_edit = None
                                    st.rerun()
                        st.write("") 

        with aba_admin:
            st.subheader("➕ Atribuir Lote de Ingressos")
            nome_add = st.selectbox("Selecione o Menino:", lista_todos_meninos, key="admin_add_vendedor")
            
            tot_ing = config_app["total_ingressos"]
            mapa_donos = df_dados.set_index('ID_Ingresso')['Vendedor'].to_dict()
            opcoes_ingressos = []
            
            for i in range(1, tot_ing + 1):
                num_str = str(i).zfill(3)
                if num_str in mapa_donos:
                    opcoes_ingressos.append(f"{num_str} (Atribuído a {mapa_donos[num_str]})")
                else:
                    opcoes_ingressos.append(num_str)
                    
            selecionados = st.multiselect("Selecione os números para atribuir (Pode escolher vários de uma vez):", opcoes_ingressos)
            
            if st.button("Atribuir Lote Completo"):
                novas_linhas = []
                for s in selecionados:
                    num = s.split(" ")[0]
                    if "(Atribuído" in s:
                        st.error(f"Erro: O ingresso {num} já tem dono!")
                    else:
                        novas_linhas.append({
                            "ID_Ingresso": num, "Vendedor": nome_add,
                            "Status": "Não Vendido", "Observacao": "", "Comprovante": "", "Retirado": "Não"
                        })
                if novas_linhas:
                    df_dados = pd.concat([df_dados, pd.DataFrame(novas_linhas)], ignore_index=True)
                    salvar_dados_nuvem(df_dados)
                    st.success(f"Lote de {len(novas_linhas)} ingressos atrelado a {nome_add}!")
                    st.rerun()
                    
        with aba_membros:
            st.subheader("👥 Gerenciar Lista de Meninos")
            st.write("Adicione novos membros para que apareçam nas opções ou retire nomes daqueles que não estão mais vendendo.")
            
            col_add, col_rem = st.columns(2)
            
            with col_add:
                st.markdown("**➕ Adicionar Nome à Lista**")
                novo_nome = st.text_input("Digite o nome do novo menino:")
                if st.button("Adicionar Nome"):
                    if novo_nome:
                        extras = config_app.get("vendedores_extras", [])
                        ocultos = config_app.get("vendedores_ocultos", [])
                        
                        if novo_nome in ocultos:
                            ocultos.remove(novo_nome)
                            config_app["vendedores_ocultos"] = ocultos
                        elif novo_nome not in extras and novo_nome not in lista_base:
                            extras.append(novo_nome)
                            config_app["vendedores_extras"] = extras
                            
                        salvar_config(config_app)
                        st.success(f"'{novo_nome}' adicionado com sucesso!")
                        st.rerun()
                        
            with col_rem:
                st.markdown("**🗑️ Retirar Nome da Lista**")
                nome_remover = st.selectbox("Selecione o nome para retirar:", ["..."] + lista_todos_meninos)
                if st.button("Retirar Nome"):
                    if nome_remover != "...":
                        if nome_remover in df_dados["Vendedor"].values:
                            st.error(f"Não é possível retirar '{nome_remover}' pois ele ainda possui ingressos atrelados. Remova ou transfira os ingressos dele primeiro.")
                        else:
                            ocultos = config_app.get("vendedores_ocultos", [])
                            if nome_remover not in ocultos:
                                ocultos.append(nome_remover)
                                config_app["vendedores_ocultos"] = ocultos
                                salvar_config(config_app)
                                st.success(f"'{nome_remover}' retirado da lista com sucesso!")
                                st.rerun()
    elif senha_acesso_painel != "":
        st.error("Senha incorreta. Acesso negado.")
    else:
        st.warning("Esta área é restrita aos tesoureiros. Por favor, digite a senha para visualizar os dados.")

# --- 8. CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.title("⚙️ Configurações Exclusivas da Tesouraria")
    
    st.subheader("Editar Dados da Edição Atual")
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        novo_total = st.number_input("Número Total de Ingressos Disponibilizados:", min_value=1, value=config_app["total_ingressos"])
    with col_cfg2:
        nova_data = st.date_input("Data Oficial do Galeto:", value=datetime.strptime(config_app["data_evento"], "%Y-%m-%d").date())
        
    senha_geral = st.text_input("Digite a Senha da Tesouraria para salvar alterações:", type="password", key="senha_geral")
    
    if st.button("💾 Salvar Configurações"):
        if senha_geral == "2102":
            config_app["total_ingressos"] = novo_total
            config_app["data_evento"] = nova_data.strftime("%Y-%m-%d")
            salvar_config(config_app)
            st.success("Métricas da edição updated com sucesso!")
            st.rerun()
        elif senha_geral != "":
            st.error("Senha incorreta. Acesso negado.")
        else:
            st.warning("Por favor, digite a senha para validar a operação.")
        
    st.markdown("---")
    st.subheader("⚠️ Zona de Perigo: Limpar para Próxima Edição")
    st.warning("Esta ação apagará permanentemente todos os status, observações e vínculos da planilha.")
    
    senha_delete = st.text_input("Digite a Senha da Tesouraria para RESETAR o sistema:", type="password", key="senha_delete")
    
    if st.button("🗑️ Apagar todos os dados e reiniciar App"):
        if senha_delete == "2102":
            df_zerado = pd.DataFrame(columns=["ID_Ingresso", "Vendedor", "Status", "Observacao", "Comprovante", "Retirado"])
            salvar_dados_nuvem(df_zerado)
            
            config_app["vendedores_extras"] = []
            config_app["vendedores_ocultos"] = []
            salvar_config(config_app)
            
            st.success("Banco de dados na nuvem resetado com sucesso para a próxima campanha!")
            st.rerun()
        elif senha_delete != "":
            st.error("Senha incorreta. Operação cancelada.")
        else:
            st.warning("A senha é obrigatória para executar o reset do evento.")
