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
    # Remove colunas fantasma se houverem
    df_historico = df_historico.loc[:, ~df_historico.columns.str.contains('^Unnamed')]
except Exception as e:
    st.error(f"Erro ao conectar com a planilha: {e}")
    df_historico = pd.DataFrame(columns=["Data", "Funcionario", "Setor", "Acao", "Entregue", "Devolvido", "Obs"])

# --- FORMULÁRIO DE REGISTRO ---
with st.container(border=True):
    st.subheader("➕ Nova Movimentação")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # CORREÇÃO: Pegar o objeto date puramente aqui
            data_selecionada = st.date_input("Data da Ação", datetime.now())
            funcionario = st.text_input("Nome Completo do Funcionário")
            setor = st.selectbox("Setor/Departamento", 
                               ["Náutica", "Administração", "Manutenção", "Portaria", "Limpeza", "Copa/Cozinha"])
        
        with col2:
            tipo_acao = st.selectbox("Tipo de Movimentação", 
                                   ["Entrega Inicial (Admissão)", "Troca por Desgaste", "Substituição (Dano)", "Devolução Final"])
            pecas_entregues = st.text_input("Peças Entregues (Ex: 2 Bermudas M, 1 Boné)")
            
        st.divider()
        
        # Regra de negócio da devolução obrigatória
        pecas_devolvidas = st.text_area("Peças Recebidas de Volta (Obrigatório para trocas)")
        obs = st.text_input("Observações Gerais")
        
        btn_salvar = st.form_submit_button("Salvar no Histórico", type="primary")

        if btn_salvar:
            if not funcionario or not pecas_entregues:
                st.error("Erro: Preencha o nome do funcionário e as peças entregues.")
            elif "Troca" in tipo_acao and not pecas_devolvidas:
                st.warning("⚠️ Atenção: Para movimentações de 'Troca', é obrigatório descrever as peças devolvidas.")
            else:
                with st.spinner("Salvando dados na planilha..."):
                    # CORREÇÃO: Formatar a data para string padrão brasileiro apenas aqui
                    data_formatada = data_selecionada.strftime('%d/%m/%Y')
                    
                    # Criar DataFrame com o novo registro
                    nova_linha = pd.DataFrame([{
                        "Data": data_formatada,
                        "Funcionario": funcionario,
                        "Setor": setor,
                        "Acao": tipo_acao,
                        "Entregue": pecas_entregues,
                        "Devolvido": pecas_devolvidas if pecas_devolvidas else "-",
                        "Obs": obs if obs else "-"
                    }])
                    
                    # Garantir que os tipos batam antes da junção
                    df_historico["Data"] = df_historico["Data"].astype(str)
                    
                    # Unir o histórico antigo com a nova linha
                    df_final = pd.concat([df_historico, nova_linha], ignore_index=True)
                    
                    # CORREÇÃO: Proteção para falsos positivos de erro no update do GSheets
                    try:
                        conn.update(worksheet="movimentacoes", data=df_final)
                        st.success(f"Sucesso! Registro de {funcionario} salvo.")
                        st.rerun()
                    except Exception as ex:
                        if "200" in str(ex):
                            st.success(f"Sucesso! Registro de {funcionario} salvo.")
                            st.rerun()
                        else:
                            st.error(f"Erro real ao salvar: {ex}")

# --- EXIBIÇÃO DO HISTÓRICO ---
st.divider()
st.subheader("📜 Histórico de Movimentações")

if not df_historico.empty:
    busca = st.text_input("🔍 Buscar por nome do funcionário:")
    
    df_exibicao = df_historico.copy()
    if busca:
        df_exibicao = df_exibicao[df_exibicao["Funcionario"].str.contains(busca, case=False, na=False)]
    
    # Mostra o histórico invertido (o mais recente no topo)
    st.dataframe(df_exibicao.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info("Nenhum registro encontrado na planilha.")
