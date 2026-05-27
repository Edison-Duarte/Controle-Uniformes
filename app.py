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
        
        # Lista única de funcionários já existentes na planilha para evitar erros
        lista_funcionarios = sorted(df_historico["Funcionario"].dropna().unique().tolist()) if not df_historico.empty else []

        # Se for DEVOLUÇÃO, usamos o menu suspenso. Se for ENTREGA, permitimos digitar o nome (caso seja um funcionário novo).
        if tipo_acao == "Devolução de Uniforme":
            if lista_funcionarios:
                funcionario = st.selectbox("Selecione o Funcionário", lista_funcionarios)
            else:
                st.warning("⚠️ Nenhum funcionário cadastrado no sistema para realizar devolução.")
                funcionario = ""
        else:
            funcionario = st.text_input("Nome Completo do Funcionário")
            
        setor = st.selectbox("Setor/Departamento", 
                           ["Náutica", "Administração", "Manutenção", "Portaria", "Limpeza", "Copa/Cozinha", "Flats"])
    
    with col2:
        obs = st.text_input("Observações Gerais")
        
        # Fluxo condicional para Devolução Pura
        if tipo_acao == "Devolução de Uniforme" and funcionario:
            motivo_devolucao = st.selectbox("Motivo da Devolução",
                                            ["Uniforme Danificado / Rasgado", "Desligamento / Demissão", "Ajuste de Tamanho", "Outro"])
            pecas_devolvidas = f"Baixa: {motivo_devolucao}"
            
            # Calcular o saldo atual do funcionário selecionado para descobrir o que ele tem em posse
            df_func = df_historico[df_historico["Funcionario"] == funcionario]
            if not df_func.empty and "Peca" in df_func.columns:
                df_saldo = df_func.groupby("Peca")["Quantidade"].sum().reset_index()
                # Pegar apenas as peças cujo saldo atual é maior que zero
                pecas_em_posse = df_saldo[df_saldo["Quantidade"] > 0]["Peca"].tolist()
            else:
                pecas_em_posse = []
                
            st.divider()
            if pecas_em_posse:
                st.markdown("### 🔍 Baixa de Peça Específica")
                peça_para_baixa = st.selectbox("Escolha a peça que está sendo devolvida:", pecas_em_posse)
                
                # Descobrir o limite máximo que ele pode devolver dessa peça
                max_devolucao = int(df_saldo[df_saldo["Peca"] == peça_para_baixa]["Quantidade"].values[0])
                qtd_devolucao = st.number_input(f"Quantidade Devolvida (Máximo em posse: {max_devolucao})", min_value=1, max_value=max_devolucao, value=1, step=1)
            else:
                st.error("❌ Este funcionário não possui nenhum uniforme ativo no sistema para dar baixa.")
                peça_para_baixa = None
                
        elif tipo_acao == "Troca por Desgaste":
            pecas_devolvidas = st.text_area("Peças Recebidas de Volta (Descreva o material trocado)")
        else:
            pecas_devolvidas = "-"

    # Se NÃO for devolução, exibe a tabela dinâmica padrão para lançar as entregas/trocas
    if tipo_acao != "Devolução de Uniforme":
        st.divider()
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
        elif (tipo_acao == "Troca por Desgaste" and (not pecas_devolvidas or pecas_devolvidas == "-")):
            st.warning("⚠️ Atenção: Para movimentações de 'Troca', é necessário descrever as peças substituídas.")
        elif tipo_acao == "Devolução de Uniforme" and not peça_para_baixa:
            st.error("Erro: Não é possível salvar uma devolução para quem não possui peças em posse.")
        elif tipo_acao != "Devolução de Uniforme" and (itens_editados.empty or itens_editados["Peça de Roupa"].isna().any() or (itens_editados["Peça de Roupa"] == "").any()):
            st.error("Erro: Adicione o nome da peça para todas as linhas preenchidas.")
        else:
            with st.spinner("Salvando dados na planilha..."):
                data_formatada = data_selecionada.strftime('%d/%m/%Y')
                novas_linhas = []
                
                # Cenário 1: Salvando a DEVOLUÇÃO direcionada
                if tipo_acao == "Devolução de Uniforme":
                    novas_linhas.append({
                        "Data": data_formatada,
                        "Funcionario": funcionario,
                        "Setor": setor,
                        "Acao": tipo_acao,
                        "Quantidade": -int(qtd_devolucao), # Força o valor negativo automático para o Sheets
                        "Peca": peça_para_baixa,
                        "Devolvido": pecas_devolvidas,
                        "Obs": obs if obs else "-"
                    })
                # Cenário 2: Salvando as ENTREGAS comuns vindas da tabela
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
