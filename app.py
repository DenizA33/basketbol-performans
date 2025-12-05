import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
import os

# --- AYARLAR ---
st.set_page_config(page_title="Basketbol Performans Paneli", layout="wide")
VERI_DOSYASI = "basketbol_veritabani.csv"

# --- 1. VERİTABANI YÖNETİMİ (CSV) ---
def verileri_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            return pd.read_csv(VERI_DOSYASI)
        except:
            return pd.DataFrame(columns=["date", "player", "minutes", "rpe", "session_load"])
    else:
        return pd.DataFrame(columns=["date", "player", "minutes", "rpe", "session_load"])

def veriyi_kaydet(df):
    df.to_csv(VERI_DOSYASI, index=False)

# --- 2. HESAPLAMA MOTORU ---
def calculate_acwr(df):
    if df.empty:
        return None, None, None
        
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values("date").set_index("date")
    
    full_idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
    df_resampled = df.reindex(full_idx).fillna({'session_load': 0})
    
    acute = df_resampled['session_load'].rolling(window=7).mean()
    chronic = df_resampled['session_load'].rolling(window=28).mean()
    acwr = acute / chronic
    
    return acute, chronic, acwr

def create_pdf(player_name, acute, chronic, acwr):
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.plot(acute.index, acute, label='Akut (7g)', color='blue')
    plt.plot(chronic.index, chronic, label='Kronik (28g)', color='gray', linestyle='--')
    plt.title(f"{player_name} - Yuk Takibi")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(2, 1, 2)
    plt.plot(acwr.index, acwr, label='Risk (ACWR)', color='purple')
    plt.axhline(y=1.5, color='red', linestyle=':', label='Risk Limiti')
    plt.axhspan(0.8, 1.3, color='green', alpha=0.1, label='Güvenli')
    plt.title("Sakatlik Risk Analizi")
    plt.legend()
    plt.tight_layout()
    plt.savefig("temp_chart_web.png")
    plt.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Rapor: {player_name}", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Tarih: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='C')
    pdf.image("temp_chart_web.png", x=10, w=190)
    
    last_val = acwr.iloc[-1] if not acwr.isna().all() else 0
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Guncel Risk Puani: {last_val:.2f}", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. ARAYÜZ (FRONTEND) ---
st.title("🏀 Basketbol Performans & Risk Paneli")

df = verileri_yukle()

# Yan Menü
st.sidebar.header("📝 Veri Girişi")
input_player = st.sidebar.text_input("Oyuncu Adı", "")
input_date = st.sidebar.date_input("Tarih", datetime.now())
input_minutes = st.sidebar.number_input("Süre (Dakika)", 0, 120, 60)
input_rpe = st.sidebar.slider("RPE (Zorluk 1-10)", 1, 10, 5)

if st.sidebar.button("Antrenmanı Kaydet"):
    if input_player.strip() == "":
        st.sidebar.error("İsim giriniz!")
    else:
        new_entry = {
            "date": input_date.strftime("%Y-%m-%d"),
            "player": input_player, 
            "minutes": input_minutes, 
            "rpe": input_rpe, 
            "session_load": input_minutes * input_rpe
        }
        new_df = pd.DataFrame([new_entry])
        if df.empty:
            df = new_df
        else:
            df = pd.concat([df, new_df], ignore_index=True)
        veriyi_kaydet(df)
        st.sidebar.success(f"{input_player} eklendi!")
        st.rerun()

st.markdown("---")

# Ana Ekran
if df.empty:
    st.warning("⚠️ Henüz veri yok. Soldan oyuncu ekleyin.")
else:
    players = df['player'].unique()
    selected = st.selectbox("Oyuncu Seç:", players)
    
    p_df = df[df['player'] == selected].copy()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Yük", f"{int(p_df['session_load'].sum())}")
    c2.metric("Ortalama RPE", f"{p_df['rpe'].mean():.1f}")
    c3.metric("Antrenman", f"{len(p_df)}")
    
    if len(p_df) > 1:
        acute, chronic, acwr = calculate_acwr(p_df)
        
        tab1, tab2 = st.tabs(["Grafikler", "Veri Listesi"])
        with tab1:
            fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
            ax[0].plot(acute.index, acute, color='blue', label='Acute')
            ax[0].plot(chronic.index, chronic, color='gray', linestyle='--', label='Chronic')
            ax[0].legend()
            ax[1].plot(acwr.index, acwr, color='purple', label='Risk')
            ax[1].axhline(1.5, color='red', linestyle=':')
            ax[1].axhspan(0.8, 1.3, color='green', alpha=0.1)
            ax[1].legend()
            st.pyplot(fig)
            
            pdf_data = create_pdf(selected, acute, chronic, acwr)
            st.download_button("PDF İndir", pdf_data, file_name=f"{selected}.pdf", mime="application/pdf")
            
        with tab2:
            st.dataframe(p_df)
            if st.button("Oyuncuyu Sil"):
                df = df[df['player'] != selected]
                veriyi_kaydet(df)
                st.rerun()