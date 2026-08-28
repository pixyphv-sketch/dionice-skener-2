from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Postavke stranice
st.set_page_config(
    page_title="Dnevni Skener Dionica Pro", page_icon="📈", layout="wide"
)

st.title("📈 Dnevni Skener Dionica Pro")
st.markdown(
    "Prilagođeni skener dionica s grafičkim prikazom TP/SL razina, naprednim"
    " filterima i arhivom."
)

# Inicijalizacija arhive u session_state
if "arhiva" not in st.session_state:
  st.session_state["arhiva"] = []

# --- BOČNA TRAKA (PARAMETRI & FILTERI) ---
st.sidebar.header("⚙️ Postavke Skenera")

nacin_rada = st.sidebar.selectbox(
    "Način rada", ["Skeniraj Novo Trziste", "Pregled Arhive"]
)

pocetni_kapital = st.sidebar.number_input(
    "Unesi Početni Kapital (€/$)", min_value=100, value=3000, step=100
)
odaberi_trziste = st.sidebar.selectbox(
    "Odaberi Tržište", ["Sve regije", "SAD", "Europa", "Azija"]
)

tp_pct = st.sidebar.number_input(
    "Ciljani Profit Postotak (%)",
    min_value=0.5,
    max_value=50.0,
    value=4.0,
    step=0.5,
)
sl_pct = st.sidebar.number_input(
    "Stop Loss Postotak (%)", min_value=0.5, max_value=50.0, value=2.0, step=0.5
)
rsi_prag = st.sidebar.slider(
    "RSI Prag (Maksimalni)", min_value=10, max_value=70, value=40
)

st.sidebar.subheader("🔍 Napredni Filteri")
filtriraj_sma200 = st.sidebar.checkbox(
    "Filtriraj Samo Uzlazni Trend (SMA200)", value=True
)
potvrda_macd = st.sidebar.checkbox("Potvrda MACD Preokreta", value=False)
filtriraj_bollinger = st.sidebar.checkbox(
    "Filtriraj i po Bollingeru", value=False
)

# --- DEFINICIJA TRŽIŠTA ---
USA_TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "AMD",
    "INTC",
    "KO",
    "PEP",
    "MCD",
    "NKE",
    "WMT",
    "PG",
    "COST",
    "DIS",
    "SBUX",
    "V",
    "MA",
    "JPM",
    "BAC",
    "CAT",
    "BA",
    "XOM",
    "PFE",
    "JNJ",
    "SPOT",
    "ABNB",
    "RBLX",
    "LULU",
    "PLTR",
    "MSTR",
    "CMG",
    "DAL",
    "F",
    "HPQ",
]
EU_TICKERS = [
    "ASML",
    "MC.PA",
    "SAP",
    "SIE.DE",
    "ALV.DE",
    "NOVO-B.CO",
    "MBG.DE",
    "BMW.DE",
    "VOW3.DE",
    "NESN.SW",
    "OR.PA",
    "ADS.DE",
    "BN.PA",
    "DBK.DE",
    "SHEL.L",
    "TTE.PA",
    "PUM.DE",
    "CON.DE",
    "PHIA.AS",
]
ASIA_TICKERS = [
    "TSM",
    "SONY",
    "TM",
    "HMC",
    "BABA",
    "JD",
    "BYDDF",
    "005930.KS",
    "NIO",
    "LI",
]

if odaberi_trziste == "SAD":
  dionice_db = USA_TICKERS
elif odaberi_trziste == "Europa":
  dionice_db = EU_TICKERS
elif odaberi_trziste == "Azija":
  dionice_db = ASIA_TICKERS
else:
  dionice_db = USA_TICKERS + EU_TICKERS + ASIA_TICKERS


# --- POMOĆNE FUNKCIJE ---
def izracunaj_rsi(series, window=14):
  delta = series.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
  rs = gain / loss
  return 100 - (100 / (1 + rs))


def izracunaj_macd(series, fast=12, slow=26, signal=9):
  exp1 = series.ewm(span=fast, adjust=False).mean()
  exp2 = series.ewm(span=slow, adjust=False).mean()
  macd = exp1 - exp2
  macd_signal = macd.ewm(span=signal, adjust=False).mean()
  return macd, macd_signal


def izracunaj_bollinger(series, window=20, num_sd=2):
  sma = series.rolling(window).mean()
  std = series.rolling(window).std()
  lower_band = sma - (std * num_sd)
  upper_band = sma + (std * num_sd)
  return lower_band, upper_band


def izracunaj_atr(df, window=14):
  tr1 = df["High"] - df["Low"]
  tr2 = (df["High"] - df["Close"].shift()).abs()
  tr3 = (df["Low"] - df["Close"].shift()).abs()
  tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
  return tr.rolling(window).mean()


# --- GLAVNI EKRANI ---
if nacin_rada == "Skeniraj Novo Trziste":
  if st.button("🚀 Pokreni skeniranje tržišta", type="primary"):
    with st.spinner("Preuzimam podatke i skeniram tržište..."):
      data = yf.download(
          dionice_db,
          period="1y",
          interval="1d",
          auto_adjust=True,
          progress=False,
      )
      signali = []
      max_ulog = pocetni_kapital * 0.20

      for ticker in dionice_db:
        try:
          close_s = (
              data["Close"][ticker].dropna()
              if isinstance(data.columns, pd.MultiIndex)
              else data["Close"].dropna()
          )
          high_s = (
              data["High"][ticker].dropna()
              if isinstance(data.columns, pd.MultiIndex)
              else data["High"].dropna()
          )
          low_s = (
              data["Low"][ticker].dropna()
              if isinstance(data.columns, pd.MultiIndex)
              else data["Low"].dropna()
          )

          if len(close_s) < 200:
            continue

          df_t = pd.DataFrame({"High": high_s, "Low": low_s, "Close": close_s})
          rsi_s = izracunaj_rsi(close_s)
          sma200_s = close_s.rolling(200).mean()
          atr_s = izracunaj_atr(df_t)
          macd_s, macd_sig_s = izracunaj_macd(close_s)
          boll_low_s, boll_up_s = izracunaj_bollinger(close_s)

          ulaz = float(close_s.iloc[-1])
          rsi_val = float(rsi_s.iloc[-1])
          sma200_val = float(sma200_s.iloc[-1])
          atr_val = float(atr_s.iloc[-1])

          # Uvjeti filtriranja
          is_rsi_ok = rsi_val <= rsi_prag
          is_sma_ok = (not filtriraj_sma200) or (ulaz >= sma200_val)
          is_macd_ok = (not potvrda_macd) or (
              macd_s.iloc[-1] > macd_sig_s.iloc[-1]
          )
          is_boll_ok = (not filtriraj_bollinger) or (
              ulaz <= boll_low_s.iloc[-1] * 1.02
          )

          if is_rsi_ok and is_sma_ok and is_macd_ok and is_boll_ok:
            komada = int(max_ulog // ulaz)
            if komada > 0:
              tp = round(ulaz * (1 + tp_pct / 100), 2)
              sl = round(ulaz * (1 - sl_pct / 100), 2)
              dana = (
                  int(np.ceil((tp - ulaz) / (atr_val * 0.7)))
                  if atr_val > 0
                  else 5
              )

              signali.append({
                  "Ticker": ticker,
                  "Cijena (€/$)": round(ulaz, 2),
                  "RSI": round(rsi_val, 1),
                  "TP (" + str(tp_pct) + "%)": tp,
                  "SL (" + str(sl_pct) + "%)": sl,
                  "Količina": komada,
                  "Est. Dana": f"~{dana}d",
                  "Nalog": (
                      f"KUPI {komada}x {ticker} @ {round(ulaz,2)} | TP: {tp} |"
                      f" SL: {sl}"
                  ),
                  "df_history": df_t.tail(90),
                  "ULAZ": round(ulaz, 2),
                  "TP_VAL": tp,
                  "SL_VAL": sl,
              })
        except Exception:
          continue

      st.session_state["zadnji_signali"] = signali

  # Prikaz rezultata ako postoje
  if "zadnji_signali" in st.session_state and st.session_state["zadnji_signali"]:
    signali = st.session_state["zadnji_signali"]
    st.success(
        f"Pronađeno {len(signali)} dionica koje odgovaraju zadanim kriterijima!"
    )

    # Tablica
    df_display = pd.DataFrame([
        {
            k: v
            for k, v in s.items()
            if k not in ["df_history", "ULAZ", "TP_VAL", "SL_VAL"]
        }
        for s in signali
    ])
    st.subheader("🎯 Pronađeni Signali")
    st.dataframe(df_display.drop(columns=["Nalog"]), use_container_width=True)

    st.subheader("📋 Gotovi Nalozi i Interaktivni Grafovi")

    for idx, s in enumerate(signali):
      with st.expander(
          f"📊 {s['Ticker']} — Ulaz: {s['ULAZ']} | TP: {s['TP_VAL']} | SL:"
          f" {s['SL_VAL']}",
          expanded=True,
      ):
        col1, col2 = st.columns([3, 1])

        with col1:
          # Izrada Plotly grafa s TP / SL linijama
          df_hist = s["df_history"]
          fig = go.Figure()

          fig.add_trace(
              go.Candlestick(
                  x=df_hist.index,
                  open=df_hist["Close"],
                  high=df_hist["High"],
                  low=df_hist["Low"],
                  close=df_hist["Close"],
                  name="Cijena",
              )
          )

          # Dodaj TP, ULAZ i SL linije
          fig.add_hline(
              y=s["TP_VAL"],
              line_dash="dash",
              line_color="green",
              annotation_text=f"TP ({s['TP_VAL']})",
              annotation_position="top right",
          )
          fig.add_hline(
              y=s["ULAZ"],
              line_dash="solid",
              line_color="blue",
              annotation_text=f"Ulaz ({s['ULAZ']})",
              annotation_position="top right",
          )
          fig.add_hline(
              y=s["SL_VAL"],
              line_dash="dash",
              line_color="red",
              annotation_text=f"SL ({s['SL_VAL']})",
              annotation_position="bottom right",
          )

          fig.update_layout(
              title=f"{s['Ticker']} - Zadnjih 90 dana s TP i SL razinama",
              yaxis_title="Cijena (€/$)",
              xaxis_rangeslider_visible=False,
              height=400,
              margin=dict(l=20, r=20, t=40, b=20),
          )
          st.plotly_chart(fig, use_container_width=True)

        with col2:
          st.code(s["Nalog"], language="text")
          if st.button(
              f"💾 Spremi u Arhivu ({s['Ticker']})", key=f"save_{idx}"
          ):
            st.session_state["arhiva"].append({
                "Datum": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Ticker": s["Ticker"],
                "Ulaz": s["ULAZ"],
                "TP": s["TP_VAL"],
                "SL": s["SL_VAL"],
                "Količina": s["Količina"],
                "Nalog": s["Nalog"],
            })
            st.success(f"{s['Ticker']} spremljen u arhivu!")

  elif (
      "zadnji_signali" in st.session_state
      and not st.session_state["zadnji_signali"]
  ):
    st.warning(
        "Nijedna dionica ne zadovoljava trenutno postavljene filtere. Pokušajte"
        " ublažiti RSI ili isključiti neki od dodanih filtera."
    )

elif nacin_rada == "Pregled Arhive":
  st.subheader("📁 Arhivirane Dionice i Nalozi")

  if st.session_state["arhiva"]:
    df_arhiva = pd.DataFrame(st.session_state["arhiva"])
    st.dataframe(df_arhiva, use_container_width=True)

    # Download gumb za preuzimanje arhive u CSV formatu
    csv = df_arhiva.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Preuzmi Arhivu (CSV)",
        data=csv,
        file_name="arhiva_dionica.csv",
        mime="text/csv",
    )

    if st.button("🗑️ Očisti Arhivu"):
      st.session_state["arhiva"] = []
      st.rerun()
  else:
    st.info(
        "Arhiva je trenutno prazna. Skenirajte tržište i spremiti željene"
        " dionice klikom na gumb 'Spremi u Arhivu'."
    )