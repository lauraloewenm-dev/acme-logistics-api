import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# --- Configuración de la página ---
st.set_page_config(page_title="Acme AI Agent Analytics", layout="wide")

# Título y descripción
st.title("🚛 Acme Logistics - AI Voice Agent Analytics")
st.markdown("Real-time performance metrics and insights for the Acme AI Dispatcher.")
st.divider()

# --- Obtención de Datos (Ajusta la URL a tu Railway) ---
API_URL = "https://acme-logistics-api-production.up.railway.app/get-logs" 

@st.cache_data(ttl=5) # Refresca cada 5 segundos
def fetch_data():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200 and len(response.json()) > 0:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return pd.DataFrame()

df = fetch_data()

if df.empty:
    st.info("Waiting for inbound calls... No data available yet.")
else:
    # --- PROCESAMIENTO DE DATOS ---
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    total_calls = len(df)
    
    # Cálculos de negocio
    booked_calls = df[df['call_outcome'].str.contains('Booked', case=False, na=False)]
    conversion_rate = (len(booked_calls) / total_calls) * 100 if total_calls > 0 else 0
    
    # Calcular ahorros/margen (Initial Rate - Agreed Rate)
    # Si la IA negocia bien, el Agreed Rate será igual o ligeramente mayor, pero nunca por encima del máximo.
    df['negotiation_delta'] = df['agreed_rate'] - df['initial_rate']
    avg_delta = df['negotiation_delta'].mean() if not df['negotiation_delta'].isnull().all() else 0

    # --- ROW 1: KPIs TOP (Product Vision) ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Inbound Calls", value=total_calls)
    with col2:
        st.metric(label="Booking Conversion", value=f"{conversion_rate:.1f}%")
    with col3:
        st.metric(label="Positive Sentiment", value=f"{len(df[df['carrier_sentiment'] == 'Positive'])}")
    with col4:
        # Mostramos cómo se mueve el precio respecto a la oferta inicial
        st.metric(label="Avg Negotiation Delta", value=f"${avg_delta:.2f}", 
                  help="Average difference between the AI's initial offer and final agreed rate.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ROW 2: GRÁFICOS (Insights) ---
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Call Outcomes")
        # Gráfico de anillo interactivo
        fig_outcomes = px.pie(df, names='call_outcome', hole=0.4, 
                              color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_outcomes.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_outcomes, use_container_width=True)

    with chart_col2:
        st.subheader("Rate Negotiation Performance")
        # Gráfico de barras comparando precio inicial vs final para las cargas reservadas
        if not booked_calls.empty:
            comparison_df = booked_calls[['carrier_name', 'initial_rate', 'agreed_rate']].melt(id_vars='carrier_name', var_name='Rate Type', value_name='Price ($)')
            fig_rates = px.bar(comparison_df, x='carrier_name', y='Price ($)', color='Rate Type', barmode='group',
                               color_discrete_sequence=['#AEC7E8', '#1F77B4'])
            fig_rates.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_rates, use_container_width=True)
        else:
            st.info("Not enough booked loads to show rate comparisons.")

    st.divider()

    # --- ROW 3: REGISTRO DETALLADO Y RESÚMENES ---
    st.subheader("Detailed Call Logs & Summaries")
    
    # Mostramos una tabla limpia
    display_df = df[['timestamp', 'mc_number', 'carrier_name', 'load_id', 'initial_rate', 'agreed_rate', 'call_outcome', 'carrier_sentiment']]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Expander para ver los resúmenes de texto de las llamadas
    with st.expander("📝 View AI Call Summaries (Transcripts)"):
        for index, row in df.iterrows():
            st.markdown(f"**Call at {row['timestamp']} | {row['carrier_name']} ({row['call_outcome']})**")
            # Si tienes un call_summary en tu API, lo muestras. Si no, usamos este mensaje temporal:
            summary_text = row.get('call_summary', "No AI summary extracted for this call.")
            st.write(f"> *{summary_text}*")
            st.markdown("---")
