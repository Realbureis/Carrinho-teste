import streamlit as st
import pandas as pd
from urllib.parse import quote
import io

# --- Configurações da Aplicação ---
st.set_page_config(layout="wide", page_title="Processador de Clientes de Vendas Prioritárias")

# Inicializa o estado para rastrear leads contatados
if 'contatados' not in st.session_state:
    st.session_state.contatados = set()

st.title("🎯 Qualificação para Time de Vendas (Jumbo CDP)")

# --- Definição das Colunas ---
COL_ID = 'Codigo Cliente'
COL_NAME = 'Cliente'
COL_PHONE = 'Fone Fixo'
COL_FILTER = 'Quant. Pedidos Enviados' 
COL_STATUS = 'Status' 
COL_ORDER_ID = 'N. Pedido' 
COL_TOTAL_VALUE = 'Valor Total' 
COL_OUT_NAME = 'Cliente_Formatado'
COL_OUT_MSG = 'Mensagem_Personalizada'

@st.cache_data
def process_data(df_input):
    df = df_input.copy() 
    required_cols = [COL_ID, COL_NAME, COL_PHONE, COL_FILTER, COL_STATUS, COL_ORDER_ID, COL_TOTAL_VALUE]
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        raise ValueError(f"Faltando colunas: {', '.join(missing)}")

    metrics = {'original_count': len(df), 'removed_duplicates': 0, 'removed_filter': 0}

    df_unique = df.drop_duplicates(subset=[COL_ID], keep='first')
    metrics['removed_duplicates'] = len(df) - len(df_unique)
    df = df_unique
    
    df[COL_FILTER] = pd.to_numeric(df[COL_FILTER], errors='coerce').fillna(-1) 
    tem_outro_status_series = df[COL_STATUS] != 'Pedido Salvo'
    clientes_com_outro_status = df.groupby(COL_ID)[COL_ID].transform(lambda x: tem_outro_status_series.loc[x.index].any())
    
    df_qualified = df[
        (df[COL_STATUS] == 'Pedido Salvo') & 
        (~clientes_com_outro_status) & 
        (df[COL_FILTER] == 0)
    ].reset_index(drop=True)
        
    metrics['removed_filter'] = len(df_input) - len(df_qualified)
    if df_qualified.empty: return df_qualified, metrics 

    def format_name_and_create_message(full_name):
        first_name = str(full_name).strip().split(' ')[0].capitalize() if full_name else "Cliente"
        message = (
            f"Olá {first_name}! Aqui é a Tais, sua *consultora exclusiva da Jumbo CDP!*\n"
            f"Tenho uma ótima notícia para você.\n\n"
            f"Vi que você iniciou seu cadastro, mas não conseguiu finalizar a compra.\n"
            f"Para eu te ajudar, poderia me contar o motivo?\n\n"
            f"Consegui separar *UM BRINDE ESPECIAL* para incluir no seu pedido.\n\n"
            f"Conte comigo!"
        )
        return first_name, message

    df_qualified[COL_NAME] = df_qualified[COL_NAME].astype(str).fillna('')
    data_series = df_qualified[COL_NAME].apply(format_name_and_create_message)
    temp_df = pd.DataFrame(data_series.tolist()) 
    df_qualified[COL_OUT_NAME] = temp_df[0]
    df_qualified[COL_OUT_MSG] = temp_df[1]
    
    df_qualified['Valor_BRL'] = df_qualified[COL_TOTAL_VALUE].apply(lambda x: f"R$ {float(str(x).replace('R$', '').replace('.', '').replace(',', '.')):.2f}".replace('.', ','))
    
    return df_qualified, metrics

# --- Interface ---
uploaded_file = st.file_uploader("Envie o relatório Excel/CSV", type=["csv", "xlsx"])

if uploaded_file:
    try:
        df_original = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        
        if st.button("🚀 Processar Dados"):
            st.session_state.df_processed, st.session_state.metrics = process_data(df_original)
            # Limpa o histórico ao processar um novo arquivo
            st.session_state.contatados = set()

        if 'df_processed' in st.session_state:
            df = st.session_state.df_processed
            
            st.header("Lista de Disparo")
            
            # --- Barra de Progresso Visual ---
            progresso = len(st.session_state.contatados) / len(df) if len(df) > 0 else 0
            st.write(f"**Progresso: {len(st.session_state.contatados)} de {len(df)} leads contatados**")
            st.progress(progresso)

            st.markdown("---")
            
            for index, row in df.iterrows():
                cols = st.columns([1.5, 1, 1, 1.5, 3, 1])
                
                lead_id = str(row[COL_ID])
                is_done = lead_id in st.session_state.contatados
                
                # Cores e Estilo
                bg_color = "#E0E0E0" if is_done else "#25D366"
                label = "✅ Enviado" if is_done else "Enviar WhatsApp"
                text_color = "#666666" if is_done else "white"
                
                cols[0].write(f"**{row[COL_OUT_NAME]}**")
                cols[1].write(f"Pedidos: {row[COL_FILTER]:.0f}")
                cols[2].write(row[COL_ORDER_ID])
                cols[3].write(row['Valor_BRL'])
                
                # Link do WhatsApp
                phone = "".join(filter(str.isdigit, str(row[COL_PHONE])))
                link = f"https://wa.me/55{phone}?text={quote(row[COL_OUT_MSG])}"
                
                # Botão HTML customizado que muda de cor
                button_html = f"""
                    <a href="{link}" target="_blank" 
                       onclick="window.location.href='#{lead_id}';" 
                       style="display: inline-block; padding: 6px 12px; background-color: {bg_color}; 
                       color: {text_color}; text-decoration: none; border-radius: 5px; width: 100%; text-align: center;
                       border: 1px solid {'#ccc' if is_done else '#128C7E'};">
                       {label}
                    </a>"""
                
                cols[4].markdown(button_html, unsafe_allow_html=True)
                
                # Botão de confirmação para mudar a cor (Streamlit)
                if cols[5].button("Marcar", key=f"btn_{lead_id}"):
                    if lead_id in st.session_state.contatados:
                        st.session_state.contatados.remove(lead_id)
                    else:
                        st.session_state.contatados.add(lead_id)
                    st.rerun()

    except Exception as e:
        st.error(f"Erro: {e}")
