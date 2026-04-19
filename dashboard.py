import streamlit as st
import pandas as pd
import requests
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Acme Analytics | AI Dispatch", layout="wide")

API_URL = "https://ideal-commitment-production-d5ed.up.railway.app"
API_KEY = "super-secret-acme-key"

st.title("🚛 Acme Logistics: AI Dispatcher Performance")
st.markdown("Real-time business impact and negotiation analytics from the HappyRobot AI Voice Agent.")

# --- OBTENER DATOS ---
@st.cache_data(ttl=5)
def fetch_logs():
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.get(f"{API_URL}/get-logs", headers=headers)
        
        if response.status_code == 200:
            try:
                # Esto es lo que fallaba antes. Si no es un JSON, ahora no explotará.
                data = response.json()
                return pd.DataFrame(data)
            except:
                st.error("⚠️ La API está conectada, pero no está enviando datos en formato JSON. Verifica tu servidor en Railway.")
                return pd.DataFrame()
        return pd.DataFrame()
    except:
        return pd.DataFrame()

df = fetch_logs()

if df.empty:
    st.info("Waiting for Laura (AI) to make the first calls... Data will appear here automatically.")
else:
    # --- PROCESAMIENTO DE DATOS ---
    df['agreed_rate'] = pd.to_numeric(df['agreed_rate'], errors='coerce').fillna(0)
    df['initial_rate'] = pd.to_numeric(df['initial_rate'], errors='coerce').fillna(0)
    
    df['ai_savings'] = df.apply(
        lambda row: (row['initial_rate'] - row['agreed_rate']) if 'booked' in str(row['call_outcome']).lower() else 0, 
        axis=1
    )

    total_savings = df['ai_savings'].sum()
    total_booked = len(df[df['call_outcome'].str.lower().str.contains('booked')])
    total_calls = len(df)
    success_rate = (total_booked / total_calls) * 100 if total_calls > 0 else 0

    # --- KPI METRICS ---
    st.markdown("### 📈 Executive KPI Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total AI Savings (Profit)", f"${total_savings:,.2f}", "Added to Margin")
    col2.metric("Loads Successfully Booked", total_booked)
    col3.metric("AI Negotiation Win Rate", f"{success_rate:.1f}%")
    avg_savings = total_savings / total_booked if total_booked > 0 else 0
    col4.metric("Avg. Savings per Load", f"${avg_savings:,.2f}")

    st.divider()

    # --- GRÁFICOS DE IMPACTO ---
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("#### 💰 Negotiation Performance by Carrier")
        chart_data = df[df['ai_savings'] > 0][['carrier_name', 'initial_rate', 'agreed_rate']]
        if not chart_data.empty:
            chart_data.set_index('carrier_name', inplace=True)
            st.bar_chart(chart_data)
        else:
            st.write("No successful negotiations to display yet.")

    with col_chart2:
        st.markdown("#### 🎯 Actionable Operations Insights")
        st.info(f"**Insight 1:** Laura (AI) is saving an average of **${avg_savings:.2f}** per booked load.")
        
        if total_savings > 1000:
            st.success("**Recommendation:** The AI agent is highly profitable. Consider routing 100% of off-hours dispatch calls to HappyRobot to maximize margin.")
        elif total_booked > 0:
            st.warning("**Recommendation:** Agent is closing deals, but savings are baseline. Instruct the AI prompt to start negotiations 10% lower to increase the profit spread.")
        else:
            st.error("**Recommendation:** Conversion is low. Review call transcripts. The maximum rate limit in the AI prompt might be too low for the current market.")

    # --- DATOS CRUDOS ---
    st.markdown("### 📋 Call Log Database")
    st.dataframe(df[['load_id', 'carrier_name', 'initial_rate', 'agreed_rate', 'ai_savings', 'call_outcome', 'carrier_sentiment']], use_container_width=True)
