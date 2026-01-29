import streamlit as st
import pandas as pd
from urllib.parse import quote

# --- Configurações da Aplicação ---
st.set_page_config(layout="wide", page_title="Processador de Vendas Jumbo")

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
    
    # 1. Verificação de Colunas
    required_cols = [COL_ID, COL_NAME, COL_PHONE, COL_FILTER, COL_STATUS, COL_ORDER_ID, COL_TOTAL_VALUE]
    if not all(col in df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df.columns]
        raise ValueError(f"O arquivo está faltando as seguintes colunas obrigatórias: {', '.join(missing)}")

    # 2. Filtros e Limpeza
    df[COL_FILTER] = pd.to_numeric(df[COL_FILTER], errors='coerce').fillna(-1)
    
    # Filtro: Apenas clientes com status "Pedido Salvo", que nunca enviaram pedidos (0) 
    # e removendo duplicados pelo ID do cliente.
    df_qualified = df[
        (df[COL_STATUS] == 'Pedido Salvo') & 
        (df[COL_FILTER] == 0)
    ].drop_duplicates(subset=[COL_ID], keep='first').reset_index(drop=True)
    
    # 3. Formatação da Mensagem (Seu Modelo Original + N. Pedido)
    def create_message(row):
        full_name_str = str(row[COL_NAME]).strip()
        first_name = full_name_str.split(' ')[0].capitalize() if full_name_str else "Cliente"
        order_num = row[COL_ORDER_ID] # Puxando o número do pedido
        
        # --- SEU TEMPLATE ORIGINAL COM O N. PEDIDO INCLUÍDO ---
        message = (
            f"Olá {first_name}! Aqui é a Tais, sua *consultora exclusiva da Jumbo CDP!*\n"
            f"Tenho uma ótima notícia para você.\n\n"
            f"Vi que você iniciou seu cadastro (Pedido n. {order_num}), mas não conseguiu finalizar a compra.\n"
            f"Para eu te ajudar, poderia me contar o motivo?\n\n"
            f"Consegui separar *UM BRINDE ESPECIAL* para incluir no seu pedido n. {order_num}, e quero garantir que você receba tudo certinho.\n\n"
            f"Conte comigo para cuidar de você!"
        )
        return first_name, message

    if not df_qualified.empty:
        # Aplicação da lógica de mensagem
        df_qualified[[COL_OUT_NAME, COL_OUT_MSG]] = df_qualified.apply(
            lambda r: pd.Series(create_message(r)), axis=1
        )
        
        # Formatação de Moeda BRL
        def format_brl(value):
            try:
                v = str(value).replace('R$', '').replace('.', '').replace(',', '.')
                return f"R$ {float(v):.2f}".replace('.', ',')
            except: return str(value)
            
        df_qualified['Valor_BRL'] = df_qualified[COL_TOTAL_VALUE].apply(format_brl)
    
    return df_qualified

# --- Interface ---
uploaded_file = st.file_uploader("Upload do Relatório (Excel/CSV)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_load = pd.read_csv(uploaded_file)
        else:
            df_load = pd.read_excel(uploaded_file, engine='openpyxl')
        
        if st.button("🚀 Processar Leads e Gerar Mensagens"):
            df_final = process_data(df_load)
            
            if df_final.empty:
                st.warning("Nenhum lead qualificado encontrado com os filtros aplicados.")
            else:
                st.header(f"Leads Prontos ({len(df_final)})")
                st.markdown("---")

                # Layout da Tabela de Disparo
                for _, row in df_final.iterrows():
                    cols = st.columns([1.5, 1, 1, 1.5, 4])
                    
                    cols[0].write(f"**{row[COL_OUT_NAME]}**")
                    cols[1].write(f"Ped: #{row[COL_ORDER_ID]}")
                    cols[2].write(row['Valor_BRL'])
                    
                    # Preparação do Link do WhatsApp
                    phone = "".join(filter(str.isdigit, str(row[COL_PHONE])))
                    link = f"https://wa.me/55{phone}?text={quote(row[COL_OUT_MSG])}"
                    
                    # Botão com seu estilo original
                    btn_html = f"""
                    <a href="{link}" target="_blank" style="
                        display: inline-block; padding: 8px 12px; 
                        background-color: #25D366; color: white; 
                        text-align: center; text-decoration: none; 
                        border-radius: 4px; border: 1px solid #128C7E;
                        font-weight: bold; width: 100%;">
                        Chamar no WhatsApp (Pedido {row[COL_ORDER_ID]})
                    </a>"""
                    cols[4].markdown(btn_html, unsafe_allow_html=True)
                    st.markdown("---")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
