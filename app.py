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
        funcionario = st.text_input("Nome Completo do Funcionário")
        setor = st.selectbox("Setor/Departamento", 
                           ["Náutica", "Administração", "Manutenção", "Portaria", "Limpeza", "Copa/Cozinha", "Flats"])
    
    with col2:
        tipo_acao = st.selectbox("Tipo de Movimentação", 
                               ["Entrega Inicial (Admissão)", "Troca por Desgaste", "Substituição (Dano)", "Devolução Final"])
        obs = st.text_input("Observações Gerais")
        if "Troca" in tipo_acao or "Devolução" in tipo_acao:
            pecas_devolvidas = st.text_area("Peças Recebidas de Volta (Obrigatório para trocas/devoluções)")
        else:
            pecas_devolvidas = "-"

    st.divider()
    st.markdown("**📋 Itens da Movimentação** (Clique duas vezes na célula vazia para digitar a quantidade e o nome da peça)")
    
    # Tabela dinâmica corrigida (sem o parâmetro inválido placeholder)
    df_itens_padrao = pd.DataFrame([{"Quantidade": 1, "Peça de Roupa": ""}])
    itens_editados = st.data_editor(
        df_itens_padrao,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Quantidade": st.column_config.NumberColumn("Qtd", min_value=1, step=1, default=1, required=True),
            "Peça de Roupa": st.column_config.TextColumn(
                "Peça de Roupa (Ex: Camisa Polo M, Bota nº 41...)",
                required=True
            )
        }
    )
    
    st.divider()
    btn_salvar = st.button("🚀 Salvar no Histórico", type="primary", use_container_width=True)

    if btn_salvar:
        if not funcionario:
            st.error("Erro: Preencha o nome do funcionário.")
        elif ("Troca" in tipo_acao and (not pecas_devolvidas or pecas_devolvidas == "-")):
            st.warning("⚠️ Atenção: Para movimentações de 'Troca', é necessário descrever as peças devolvidas.")
        elif itens_editados.empty or itens_editados["Peça de Roupa"].isna().any() or (itens_editados["Peça de Roupa"] == "").any():
            st.error("Erro: Adicione o nome da peça para todas as linhas preenchidas.")
        else:
            with st.spinner("Salvando dados na planilha..."):
                data_formatada = data_selecionada.strftime('%d/%m/%Y')
                novas_linhas = []
                
                for _, item in itens_editados.iterrows():
                    qtd = int(item["Quantidade"])
                    if "Devolução Final" in tipo_acao:
                        qtd = -qtd # Salva como negativo para abater na soma automática do saldo
                        
                    novas_linhas.append({
                        "Data": data_formatada,
                        "Funcionario": funcionario,
                        "Setor": setor,
                        "Acao": tipo_acao,
                        "Quantidade": qtd,
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
                    st.success(f"Sucesso! Movimentação de {funcionario} salva.")
                    st.rerun()
                except Exception as ex:
                    if "200" in str(ex):
                        st.success(f"Sucesso! Movimentação de {funcionario} salva.")
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
            df_balanco_pecas = df_balanco_pecas[df_balanco_pecas["Quantidade"] >= 0]
        else:
            df_balanco_pecas = pd.DataFrame()
        
        col_card1, col_card2 = st.columns([1, 2])
        with col_card1:
            st.metric(label=f"Total de Peças com {busca.title()}", value=f"{total_pecas} un")
        with col_card2:
            st.markdown("**Saldo Atual de Uniformes Ativos:**")
            if not df_balanco_pecas.empty and total_pecas > 0:
                linhas_pecas = [f"• {row['Peca']}: **{row['Quantidade']}** un" for _, row in df_balanco_pecas.iterrows() if row['Quantidade'] > 0]
                st.markdown("\n".join(linhas_pecas))
            else:
                st.caption("Nenhum uniforme ativo em posse (Tudo devolvido ou zerado).")
        st.divider()

    st.dataframe(df_exibicao.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info("Nenhum registro encontrado na planilha.")
