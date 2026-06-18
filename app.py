import streamlit as st
import pandas as pd
import os
import json
from PIL import Image
from datetime import datetime
import altair as alt
import unicodedata

# --- 1. CONFIGURAÇÃO INICIAL E LOGO ---
# Corrigido para .png conforme o arquivo do Capítulo
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

DB_FILE = "dados_galeto.csv"
CONFIG_FILE = "config_galeto.json"
IMG_DIR = "comprovantes"

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

if "ingresso_edit" not in st.session_state:
    st.session_state.ingresso_edit = None

def selecionar_ingresso(id_ing):
    # Se clicar no mesmo ingresso, ele fecha a caixinha. Se clicar em outro, ele abre o novo.
    if st.session_state.ingresso_edit == id_ing:
        st.session_state.ingresso_edit = None
    else:
        st.session_state.ingresso_edit = id_ing

# --- 2. CONFIGURAÇÕES E BANCO DE DADOS ---
def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"total_ingressos": 200, "data_evento": datetime.now().strftime("%Y-%m-%d")}

def salvar_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

config_app = carregar_config()

def inicializar_dados():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, dtype=str)
        df.fillna("", inplace=True)
        # Ordena numericamente garantindo a exibição crescente
        df['ID_Num'] = pd.to_numeric(df['ID_Ingresso'], errors='coerce')
        df = df.sort_values('ID_Num').drop(columns=['ID_Num'])
        return df
    
    df = pd.DataFrame(columns=["ID_Ingresso", "Vendedor", "Status", "Observacao", "Comprovante", "Retirado"])
    df.to_csv(DB_FILE, index=False)
    return df

df_dados = inicializar_dados()

lista_base = ["Bernardo", "Caetano", "Gabriel", "Gabriel Medina", "Guilherme", "Guilherme Evangelho", 
              "Gustavinho", "Henrique De Oliveira", "Ícaro", "Iuri", "João", "José Vicente", "Leonel", 
              "Linhares", "Luis Felipe", "Matheus", "Miguel", "Nicolas", "Pedro Terra", "Pietro", 
              "Ramiro", "Teodoro", "Thierry"]

# Função para remover acentos para ordem alfabética correta (Ícaro vai para o I)
def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

lista_todos_meninos = sorted(list(set(df_dados["Vendedor"].unique()) | set(lista_base)), key=strip_accents)

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
        for j, (_, row) in enumerate(lote.iterrows()):
            icone = get_cor_status(row['Status'])
            retirado_mark = " ✔️" if row['Retirado'] == "Sim" else ""
            cols[j].button(f"{icone} {row['ID_Ingresso']}{retirado_mark}", 
                           key=f"{prefixo_chave}_{row['ID_Ingresso']}", 
                           on_click=selecionar_ingresso, args=(row['ID_Ingresso'],))

# --- 3. MENU LATERAL ---
if tem_logo:
    try:
        st.sidebar.image(Image.open(caminho_logo), use_container_width=True)
    except:
        pass
st.sidebar.title("🍗 Galeto do Capítulo")
menu = st.sidebar.radio("Navegação", ["🏠 Página Inicial", "👦 Área do Vendedor", "💼 Tesouraria", "⚙️ Configurações"])

hoje = datetime.now().date()
data_ev = datetime.strptime(config_app["data_evento"], "%Y-%m-%d").date()
dias_faltantes = (data_ev - hoje).days

# --- 4. PÁGINA INICIAL ---
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
    nao_vendidos = total_estipulado - vendidos_total
    retirados = len(df_dados[df_dados["Retirado"] == "Sim"])
    
    # Cálculos seguros para progresso
    prog_pagos = min(pagos / total_estipulado, 1.0) if total_estipulado > 0 else 0
    prog_aguardando = min(aguardando / total_estipulado, 1.0) if total_estipulado > 0 else 0
    prog_vendidos = min(vendidos_total / total_estipulado, 1.0) if total_estipulado > 0 else 0
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
        st.progress(min(nao_vendidos / total_estipulado, 1.0) if total_estipulado > 0 else 0)
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

# --- 5. ÁREA DO VENDEDOR ---
elif menu == "👦 Área do Vendedor":
    st.title("👦 Gestão dos Meus Ingressos")
    vendedor_sel = st.selectbox("Selecione seu nome:", ["..."] + lista_todos_meninos)
    
    if vendedor_sel != "...":
        df_meus = df_dados[df_dados["Vendedor"] == vendedor_sel]
        
        if df_meus.empty:
            st.warning("Você ainda não tem ingressos atrelados ao seu nome. Fale com a Tesouraria.")
        else:
            st.write(f"Você possui **{len(df_meus)}** ingressos atrelados. Clique no bloco para editar:")
            exibir_blocos_ingressos(df_meus, "btn_vend")
            
            # Caixa de Edição aparecendo embaixo dos ingressos
            if st.session_state.ingresso_edit in df_meus["ID_Ingresso"].values:
                ing_id = st.session_state.ingresso_edit
                idx = df_meus[df_meus["ID_Ingresso"] == ing_id].index[0] # Puxa do df_meus pra não errar a pessoa
                dados_atuais = df_dados.iloc[idx]
                
                with st.expander(f"📝 Editando Ingresso {ing_id}", expanded=True):
                    novo_status = st.selectbox("Status de Pagamento:", ["Não Vendido", "Aguardando Pagamento", "Pago"], index=["Não Vendido", "Aguardando Pagamento", "Pago"].index(dados_atuais["Status"]))
                    
                    tem_obs = bool(dados_atuais["Observacao"].strip())
                    quer_obs = st.checkbox("Adicionar/Editar Observação", value=tem_obs)
                    
                    if quer_obs:
                        nova_obs = st.text_input("Observação:", value=dados_atuais["Observacao"])
                    else:
                        nova_obs = ""
                        
                    comprovante_file = st.file_uploader("🧾 Anexar Comprovante PIX", type=["png", "jpg", "jpeg"])
                    
                    col_sv1, col_sv2 = st.columns([1, 4])
                    if col_sv1.button("💾 Salvar", key="save_vend"):
                        df_dados.at[idx, "Status"] = novo_status
                        df_dados.at[idx, "Observacao"] = nova_obs
                        if comprovante_file is not None:
                            ext = comprovante_file.name.split(".")[-1]
                            caminho_completo = os.path.join(IMG_DIR, f"pix_{ing_id}_{datetime.now().strftime('%H%M%S')}.{ext}")
                            with open(caminho_completo, "wb") as f: f.write(comprovante_file.getbuffer())
                            df_dados.at[idx, "Comprovante"] = caminho_completo
                        df_dados.to_csv(DB_FILE, index=False)
                        st.success("Atualizado!")
                        st.session_state.ingresso_edit = None
                        st.rerun()
                    if col_sv2.button("❌ Cancelar", key="canc_vend"):
                        st.session_state.ingresso_edit = None
                        st.rerun()

# --- 6. TESOURARIA ---
elif menu == "💼 Tesouraria":
    st.title("💼 Painel de Controle da Tesouraria")
    
    # Painel Dashboard Restabelecido
    pagos = len(df_dados[df_dados["Status"] == "Pago"])
    aguardando = len(df_dados[df_dados["Status"] == "Aguardando Pagamento"])
    vendidos_total = pagos + aguardando
    total_estipulado = config_app["total_ingressos"]
    nao_vendidos = total_estipulado - vendidos_total
    retirados = len(df_dados[df_dados["Retirado"] == "Sim"])
    
    st.info(f"**Resumo do Evento:**")
    col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
    col_t1.metric("🟢 Pagos", pagos)
    col_t2.metric("🟡 Aguardando", aguardando)
    col_t3.metric("🔥 Total Vendidos", vendidos_total)
    col_t4.metric("🔴 Não Vendidos", nao_vendidos)
    col_t5.metric("🍗 Retirados", retirados)
    st.markdown("---")
    
    aba_geral, aba_admin = st.tabs(["👁️ Visão Geral e Edição", "➕ Atribuir Ingressos"])
    
    with aba_geral:
        for vendedor in lista_todos_meninos:
            df_vend = df_dados[df_dados["Vendedor"] == vendedor]
            if not df_vend.empty:
                st.markdown(f"**👤 {vendedor}** ({len(df_vend)} ingressos)")
                exibir_blocos_ingressos(df_vend, "btn_tes")
                
                # A caixinha de edição abre exatamente abaixo do vendedor correto
                if st.session_state.ingresso_edit in df_vend["ID_Ingresso"].values:
                    ing_id = st.session_state.ingresso_edit
                    idx = df_vend[df_vend["ID_Ingresso"] == ing_id].index[0]
                    dados_atuais = df_dados.iloc[idx]
                    
                    with st.expander(f"🛠️ Editando Ingresso {ing_id} ({dados_atuais['Vendedor']})", expanded=True):
                        col_ed1, col_ed2 = st.columns(2)
                        with col_ed1:
                            novo_status = st.selectbox("Status:", ["Não Vendido", "Aguardando Pagamento", "Pago"], index=["Não Vendido", "Aguardando Pagamento", "Pago"].index(dados_atuais["Status"]))
                            
                            tem_obs = bool(dados_atuais["Observacao"].strip())
                            quer_obs = st.checkbox("Adicionar/Editar Observação", value=tem_obs, key=f"obs_tes_{ing_id}")
                            if quer_obs:
                                nova_obs = st.text_input("Observação:", value=dados_atuais["Observacao"], key=f"txt_tes_{ing_id}")
                            else:
                                nova_obs = ""
                                
                        with col_ed2:
                            novo_retirado = st.radio("Galeto Retirado?", ["Não", "Sim"], index=["Não", "Sim"].index(dados_atuais["Retirado"]))
                            
                        if dados_atuais["Comprovante"] != "" and os.path.exists(dados_atuais["Comprovante"]):
                            st.image(Image.open(dados_atuais["Comprovante"]), width=300, caption="Comprovante Enviado")
                            
                        col_b1, col_b2 = st.columns([1, 4])
                        if col_b1.button("💾 Salvar", key=f"sv_tes_{ing_id}"):
                            df_dados.at[idx, "Status"] = novo_status
                            df_dados.at[idx, "Observacao"] = nova_obs
                            df_dados.at[idx, "Retirado"] = novo_retirado
                            df_dados.to_csv(DB_FILE, index=False)
                            st.success("Salvo!")
                            st.session_state.ingresso_edit = None
                            st.rerun()
                        if col_b2.button("❌ Cancelar", key=f"cc_tes_{ing_id}"):
                            st.session_state.ingresso_edit = None
                            st.rerun()
                st.write("") # Espaçamento

    with aba_admin:
        st.subheader("➕ Atribuir Lote de Ingressos")
        nome_add = st.selectbox("Selecione o Menino:", lista_todos_meninos)
        
        tot_ing = config_app["total_ingressos"]
        mapa_donos = df_dados.set_index('ID_Ingresso')['Vendedor'].to_dict()
        opcoes_ingressos = []
        
        for i in range(1, tot_ing + 1):
            num_str = str(i).zfill(3)
            if num_str in mapa_donos:
                opcoes_ingressos.append(f"{num_str} (Atribuído a {mapa_donos[num_str]})")
            else:
                opcoes_ingressos.append(num_str)
                
        selecionados = st.multiselect("Selecione os números para atribuir (Pode escolher vários):", opcoes_ingressos)
        
        if st.button("Atribuir Ingressos"):
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
                df_dados.to_csv(DB_FILE, index=False)
                st.success(f"{len(novas_linhas)} ingressos atribuídos a {nome_add}!")
                st.rerun()

# --- 7. CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.title("⚙️ Configurações Exclusivas")
    
    st.subheader("Editar Dados da Edição Atual")
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        novo_total = st.number_input("Número Total de Ingressos:", min_value=1, value=config_app["total_ingressos"])
    with col_cfg2:
        nova_data = st.date_input("Data do Galeto:", value=datetime.strptime(config_app["data_evento"], "%Y-%m-%d").date())
        
    senha_geral = st.text_input("Senha da Tesouraria:", type="password", key="senha_geral")
    
    if st.button("💾 Salvar Configurações"):
        if senha_geral == "2102":
            config_app["total_ingressos"] = novo_total
            config_app["data_evento"] = nova_data.strftime("%Y-%m-%d")
            salvar_config(config_app)
            st.success("Configurações atualizadas com sucesso!")
            st.rerun()
        elif senha_geral != "":
            st.error("Senha incorreta. Acesso negado.")
        else:
            st.warning("Digite a senha para confirmar as alterações.")
        
    st.markdown("---")
    st.subheader("⚠️ Zona de Perigo")
    st.warning("Esta ação apagará todos os dados de vendas, ingressos atribuídos e status.")
    
    senha_delete = st.text_input("Senha da Tesouraria para DELETAR tudo:", type="password", key="senha_delete")
    
    if st.button("🗑️ Apagar todos os dados e reiniciar App"):
        if senha_delete == "2102":
            df_zerado = pd.DataFrame(columns=["ID_Ingresso", "Vendedor", "Status", "Observacao", "Comprovante", "Retirado"])
            df_zerado.to_csv(DB_FILE, index=False)
            st.success("Sistema reiniciado com sucesso para a nova edição!")
            st.rerun()
        elif senha_delete != "":
            st.error("Senha incorreta. Acesso negado.")
        else:
            st.warning("Digite a senha para autorizar a exclusão.")