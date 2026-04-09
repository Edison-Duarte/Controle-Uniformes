import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Protocolo de Uniformes", page_icon="👕")

st.title("👕 Protocolo Digital de Uniformes")
st.markdown("Registre as entregas e trocas de uniformes para controle administrativo.")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ENTRADA DE DADOS ---
with st.container(border=True):
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            data = st.date_input("Data da Ação", datetime.now()).strftime('%d/%m/%Y')
            funcionario = st.text_input("Nome Completo do Funcionário")
            setor = st.selectbox("Setor/Departamento", 
                               ["Náutica", "Administração", "Manutenção", "Portaria", "Limpeza", "Copa/Cozinha"])
        
        with col2:
            tipo_acao = st.selectbox("Tipo de Movimentação", 
                                   ["Entrega Inicial (Admissão)", "Troca por Desgaste", "Substituição (Dano)", "Devolução Final"])
            pecas_entregues = st.text_input("Peças Entregues (Ex: 2 Bermudas M, 1 Boné)")
            
        st.divider()
        
        # Campo de devolução (obrigatório se for troca)
        pecas_devolvidas = st.text_area("Peças Recebidas de Volta (Obrigatório para trocas)")
        obs = st.text_input("Observações (Ex: Tamanho especial, ajuste de costura)")
        
        confirmacao = st.checkbox("Confirmo que o funcionário conferiu as peças entregues.")
        
        btn_salvar = st.form_submit_button("Finalizar e Salvar Registro")

        if btn_salvar:
            if not funcionario or not pecas_entregues:
                st.error("Por favor, preencha o nome do funcionário e o que está sendo entregue.")
            elif "Troca" in tipo_acao and not pecas_devolvidas:
                st.warning("⚠️ Para trocas, você deve descrever o que foi devolvido no campo acima.")
            elif not confirmacao:
                st.error("Por favor, marque o campo de confirmação.")
            else:
                # Criar DataFrame com a nova linha
                nova_movimentacao = pd.DataFrame([{
                    "Data": data,
                    "Funcionario": funcionario,
                    "Setor": setor,
                    "Ação": tipo_acao,
                    "Entregue": pecas_entregues,
                    "Devolvido": pecas_devolvidas,
                    "Obs": obs
                }])
                
                # Ler dados atuais e concatenar
                df_atual = conn.read(worksheet="movimentacoes")
                df_final = pd.concat([df_atual, nova_movimentacao], ignore_index=True)
                
                # Salvar na Planilha
                conn.update(worksheet="movimentacoes", data=df_final)
                
                st.success(f"Registro de {funcionario} salvo com sucesso!")
                st.balloons()

# --- VISUALIZAÇÃO DOS ÚLTIMOS REGISTROS ---
st.subheader("📋 Histórico de Entregas")
try:
    dados_exibicao = conn.read(worksheet="movimentacoes")
    if not dados_exibicao.empty:
        # Mostra os 10 registros mais recentes no topo
        st.dataframe(dados_exibicao.iloc[::-1].head(10), use_container_width=True)
    else:
        st.info("Aguardando o primeiro registro...")
except:
    st.error("Erro ao carregar a planilha. Verifique a conexão nos Secrets.")
