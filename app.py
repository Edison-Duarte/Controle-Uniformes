import streamlit as st
import pandas as pd
from datetime import datetime

# Configurações da página
st.set_page_config(page_title="Controle de Uniformes", layout="wide")

st.title("👕 Sistema de Controle de Uniformes")

# --- SIDEBAR: Filtros e Status ---
st.sidebar.header("Painel de Controle")
aba = st.sidebar.radio("Navegação", ["Registrar Entrega/Troca", "Estoque Atual", "Relatório de Pendências"])

# --- MOCK DATA (Substitua pela conexão com seu Banco de Dados) ---
# Aqui simulamos uma lista de funcionários e peças
funcionarios = ["João Silva", "Maria Souza", "Carlos Oliveira", "Ana Costa"]
pecas_disponiveis = ["Camiseta Polo M", "Camiseta Polo G", "Calça Operacional 42", "Calça Operacional 44", "Bota de Segurança 40"]

if aba == "Registrar Entrega/Troca":
    st.subheader("Nova Movimentação")
    
    with st.form("form_uniforme", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            data_entrega = st.date_input("Data da Entrega", datetime.now())
            funcionario = st.selectbox("Selecione o Funcionário", funcionarios)
            setor = st.text_input("Setor")
        
        with col2:
            tipo_acao = st.selectbox("Tipo de Ação", ["Admissão", "Troca por Desgaste", "Substituição (Dano)", "Devolução (Desligamento)"])
            peca_entregue = st.multiselect("Peças Sendo Entregues", pecas_disponiveis)
        
        st.divider()
        
        # Lógica de Obrigatoriedade de Devolução
        st.warning("⚠️ Para trocas, a devolução das peças antigas é obrigatória.")
        pecas_devolvidas = st.text_area("Descreva as peças que foram DEVOLVIDAS (Ex: 2 camisetas desgastadas)")
        
        condicao_devolucao = st.select_slider(
            "Condição das peças devolvidas",
            options=["N/A", "Muito Desgastada", "Dano por mau uso", "Em bom estado"]
        )

        observacoes = st.text_input("Observações Adicionais")
        
        submit = st.form_submit_button("Registrar Movimentação")
        
        if submit:
            if tipo_acao == "Troca por Desgaste" and not pecas_devolvidas:
                st.error("Erro: Não é possível registrar uma troca sem descrever as peças devolvidas.")
            else:
                # Aqui entra sua lógica de 'st.session_state' ou 'db.insert()'
                st.success(f"Registro realizado com sucesso para {funcionario}!")
                st.balloons()

elif aba == "Relatório de Pendências":
    st.subheader("Funcionários com trocas pendentes ou histórico")
    # Simulação de DataFrame para visualização rápida
    df_exemplo = pd.DataFrame({
        'Data': ['01/04/2026', '05/04/2026'],
        'Funcionário': ['João Silva', 'Ana Costa'],
        'Entregue': ['2x Polo M', '1x Bota 40'],
        'Devolvido': ['Pendente', '1x Bota Velha'],
        'Status': ['🔴 Pendente', '🟢 Ok']
    })
    st.table(df_exemplo)
