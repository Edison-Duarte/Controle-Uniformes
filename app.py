import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Controle de Uniformes", page_icon="👕", layout="wide")

st.title("👕 Sistema de Registro de Uniformes")
st.markdown("Os dados abaixo são sincronizados diretamente com o Google Sheets.")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARREGAR HISTÓRICO ---
try:
    df_historico = conn.read(worksheet="movimentacoes", ttl=0)
    df_historico = df_historico.loc[:, ~df_historico.columns.str.contains('^Unnamed')]
    
    if "Quantidade" in df_historico.columns:
        df_historico["Quantidade"] = pd.to_numeric(df_historico["Quantidade"], errors="coerce").fillna(0).astype(int)
except Exception as e:
    st.error(f"Erro ao conectar com a planilha: {e}")
    df_historico = pd.DataFrame(columns=["Data", "Funcionario", "Setor", "Acao", "Quantidade", "Peca", "Devolvido", "Obs"])

# --- FORMULÁRIO DE REGISTRO ---
with st.container(border=True):
    st.subheader("➕ Nova Movimentação")
    
    col1, col2 = st.columns(2)
    
    with col1:
        data_selecionada = st.date_input("Data da Ação", datetime.now())
        tipo_acao = st.selectbox("Tipo de Movimentação", 
                               ["Entrega Inicial (Admissão)", "Entrega de Peças Extras", "Troca por Desgaste", "Devolução de Uniforme"])
        
        # Lista única de funcionários já existentes na planilha
        lista_funcionarios = sorted(df_historico["Funcionario"].dropna().unique().tolist()) if not df_historico.empty else []

        # Se for DEVOLUÇÃO ou TROCA, usamos o menu suspenso para travar o funcionário correto
        if tipo_acao in ["Devolução de Uniforme", "Troca por Desgaste"]:
            if lista_funcionarios:
                funcionario = st.selectbox("Selecione o Funcionário", lista_funcionarios)
            else:
                st.warning("⚠️ Nenhum funcionário cadastrado no sistema para realizar esta ação.")
                funcionario = ""
        else:
            funcionario = st.text_input("Nome Completo do Funcionário")
            
        setor = st.selectbox("Setor/Departamento", 
                           ["Náutica", "Administração", "Manutenção", "Portaria", "Limpeza", "Copa/Cozinha", "Flats"])
    
    with col2:
        obs = st.text_input("Observações Gerais")
        
        # --- LÓGICA DE VERIFICAÇÃO DE SALDO (DEVOLUÇÃO E TROCA) ---
        peça_para_baixa = None
        qtd_devolucao = 1
        pecas_devolvidas = "-"
        
        if tipo_acao in ["Devolução de Uniforme", "Troca por Desgaste"] and funcionario:
            # Calcular o saldo atual do funcionário selecionado
            df_func = df_historico[df_historico["Funcionario"] == funcionario]
            if not df_func.empty and "Peca" in df_func.columns:
                df_saldo = df_func.groupby("Peca")["Quantidade"].sum().reset_index()
                pecas_em_posse = df_saldo[df_saldo["Quantidade"] > 0]["Peca"].tolist()
            else:
                pecas_em_posse = []
                
            st.divider()
            if pecas_em_posse:
                st.markdown(f"### 🔍 Selecione a Peça Antiga para dar Baixa")
                peça_para_baixa = st.selectbox("Escolha a peça que o funcionário está devolvendo:", pecas_em_posse)
                
                max_devolucao = int(df_saldo[df_saldo["Peca"] == peça_para_baixa]["Quantidade"].values[0])
                qtd_devolucao = st.number_input(f"Quantidade Devolvida (Máximo em posse: {max_devolucao})", min_value=1, max_value=max_devolucao, value=1, step=1)
                
                if tipo_acao == "Devolução de Uniforme":
                    motivo_devolucao = st.selectbox("Motivo da Devolução", ["Uniforme Danificado / Rasgado", "Desligamento / Demissão", "Ajuste de Tamanho", "Outro"])
                    pecas_devolvidas = f"Baixa: {motivo_devolucao}"
                else:
                    pecas_devolvidas = f"Troca: Peça antiga recolhida por desgaste"
            else:
                st.error("❌ Este funcionário não possui nenhum uniforme ativo no sistema para dar baixa/trocar.")
                peça_para_baixa = None

    # Se for uma TROCA ou ENTREGA, exibe a tabela dinâmica para lançar o uniforme NOVO que está saindo
    if tipo_acao != "Devolução de Uniforme":
        st.divider()
        if tipo_acao == "Troca por Desgaste":
            st.markdown("**👕 Itens NOVOS sendo Entregues** (Digite abaixo os dados do novo uniforme que o funcionário vai levar)")
        else:
            st.markdown("**📋 Itens da Movimentação** (Clique duas vezes na célula vazia para digitar a quantidade e o nome da peça)")
        
        df_itens_padrao = pd.DataFrame([{"Quantidade": 1, "Peça de Roupa": ""}])
        itens_editados = st.data_editor(
            df_itens_padrao,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Quantidade": st.column_config.NumberColumn("Qtd", min_value=1, step=1, default=1, required=True),
                "Peça de Roupa": st.column_config.TextColumn("Peça de Roupa", required=True)
            }
        )
    
    st.divider()
    btn_salvar = st.button("🚀 Salvar no Histórico", type="primary", use_container_width=True)

    if btn_salvar:
        if not funcionario:
            st.error("Erro: Selecione ou preencha o nome do funcionário.")
        elif tipo_acao in ["Devolução de Uniforme", "Troca por Desgaste"] and not peça_para_baixa:
            st.error("Erro: Operação cancelada. O funcionário precisa ter a peça em posse para fazer a baixa/troca.")
        elif tipo_acao != "Devolução de Uniforme" and (itens_editados.empty or itens_editados["Peça de Roupa"].isna().any() or (itens_editados["Peça de Roupa"] == "").any()):
            st.error("Erro: Adicione o nome da peça nova para todas as linhas preenchidas.")
        else:
            with st.spinner("Salvando dados na planilha..."):
                data_formatada = data_selecionada.strftime('%d/%m/%Y')
                novas_linhas = []
                
                # CENÁRIO 1: Se for Devolução Pura (Apenas linha negativa de saída)
                if tipo_acao == "Devolução de Uniforme":
                    novas_linhas.append({
                        "Data": data_formatada,
                        "Funcionario": funcionario,
                        "Setor": setor,
                        "Acao": tipo_acao,
                        "Quantidade": -int(qtd_devolucao),
                        "Peca": peça_para_baixa,
                        "Devolvido": pecas_devolvidas,
                        "Obs": obs if obs else "-"
                    })
                
                # CENÁRIO 2: Se for Troca por Desgaste (Salva 2 linhas: a de baixa negativa E a de entrega positiva)
                elif tipo_acao == "Troca por Desgaste":
                    # Linha 1: Baixa da peça antiga (Negativa)
                    novas_linhas.append({
                        "Data": data_formatada,
                        "Funcionario": funcionario,
                        "Setor": setor,
                        "Acao": "Troca - Peça Devolvida",
                        "Quantidade": -int(qtd_devolucao),
                        "Peca": peça_para_baixa,
                        "Devolvido": pecas_devolvidas,
                        "Obs": obs if obs else "-"
                    })
                    # Linha 2: Entrada da(s) peça(s) nova(s) da tabela (Positiva)
                    for _, item in itens_editados.iterrows():
                        novas_linhas.append({
                            "Data": data_formatada,
                            "Funcionario": funcionario,
                            "Setor": setor,
                            "Acao": "Troca - Peça Nova Entregue",
                            "Quantidade": int(item["Quantidade"]),
                            "Peca": str(item["Peça de Roupa"]).strip(),
                            "Devolvido": "-",
                            "Obs": obs if obs else "-"
                        })
                        
                # CENÁRIO 3: Entregas normais (Apenas linhas positivas)
                else:
                    for _, item in itens_editados.iterrows():
                        novas_linhas.append({
                            "Data": data_formatada,
                            "Funcionario": funcionario,
                            "Setor": setor,
                            "Acao": tipo_acao,
                            "Quantidade": int(item["Quantidade"]),
                            "Peca": str(item["Peça de Roupa"]).strip(),
                            "Devolvido": pecas_devolvidas,
                            "Obs": obs if obs else "-"
                        })
                
                df_novas = pd.DataFrame(novas_linhas)
                df_historico["Data"] = df_historico["Data"].astype(str)
                df_historico["Quantidade"] = df_historico["Quantidade"].astype(int)
                
                df_final = pd.concat([df_historico, df_novas], ignore_index=True)
                
                try:
                    conn.update(worksheet="movimentacoes", data=df_final)
                    st.success("Sucesso! Operação gravada na planilha.")
                    st.rerun()
                except Exception as ex:
                    if "200" in str(ex):
                        st.success("Sucesso! Operação gravada na planilha.")
                        st.rerun()
                    else:
                        st.error(f"Erro ao salvar: {ex}")

# --- EXIBIÇÃO E PESQUISA NO HISTÓRICO ---
st.divider()
st.subheader("📜 Histórico de Movimentações")

if not df_historico.empty:
    busca = st.text_input("🔍 Pesquisar por Funcionário para ver o saldo de roupas:")
    
    df_exibicao = df_historico.copy()
    if busca:
        df_exibicao = df_exibicao[df_exibicao["Funcionario"].str.contains(busca, case=False, na=False)]
        
        # --- CARD DO TOTALIZADOR INTELIGENTE ---
        total_pecas = df_exibicao["Quantidade"].sum()
        
        if "Peca" in df_exibicao.columns:
            df_balanco_pecas = df_exibicao.groupby("Peca")["Quantidade"].sum().reset_index()
            df_balanco_pecas = df_balanco_pecas[df_balanco_pecas["Quantidade"] > 0]
        else:
            df_balanco_pecas = pd.DataFrame()
        
        col_card1, col_card2 = st.columns([1, 2])
        with col_card1:
            st.metric(label=f"Total de Peças Atuais com {busca.title()}", value=f"{total_pecas} un")
        with col_card2:
            st.markdown("**Saldo Atual de Uniformes (Em Posse):**")
            if not df_balanco_pecas.empty and total_pecas > 0:
                linhas_pecas = [f"• {row['Peca']}: **{row['Quantidade']}** un" for _, row in df_balanco_pecas.iterrows()]
                st.markdown("\n".join(linhas_pecas))
            else:
                st.caption("Nenhum uniforme ativo em posse (Tudo devolvido, dado baixa ou zerado).")
        st.divider()

    st.dataframe(df_exibicao.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info("Nenhum registro encontrado na planilha.")

# --- ASSINATURA FINALIZADA COM FONTE GABRIOLA ---
st.markdown("---")

st.markdown(
    """
    <div style='text-align: center; margin-top: 100px;'>
        <p style='margin-bottom: -8px; font-family: "Gabriola", serif; font-style: italic; font-size: 18px; color: #0056b3;'>
            Developed by:
        </p>
        <p style='font-family: "Gabriola", serif; font-size: 20px; font-weight: 100; color: #1e7044;'>
            Edison Duarte Filho®
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
