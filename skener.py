import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import numpy as np
import pandas as pd
import yfinance as yf

# Čitanje tajnih podataka zabilježenih na GitHubu
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

# Baza dionica koje skeniramo
dionice_db = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "INTC",
    "KO", "PEP", "MCD", "NKE", "WMT", "PG", "COST", "DIS", "SBUX",
    "V", "MA", "JPM", "BAC", "CAT", "BA", "XOM", "PFE", "JNJ",
    "SPOT", "ABNB", "RBLX", "LULU", "PLTR", "MSTR", "CMG", "DAL", "F", "HPQ",
    "ASML", "MC.PA", "SAP", "SIE.DE", "ALV.DE", "NOVO-B.CO", "MBG.DE", "BMW.DE",
    "VOW3.DE", "NESN.SW", "OR.PA", "ADS.DE", "BN.PA", "DBK.DE", "SHEL.L",
    "TTE.PA", "PUM.DE", "CON.DE", "PHIA.AS", "TSM", "SONY", "TM", "HMC", 
    "BABA", "JD", "BYDDF", "005930.KS", "NIO", "LI"
]

def izracunaj_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def izracunaj_atr(df, window=14):
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift()).abs()
    tr3 = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window).mean()

def posalji_email(predmet, tekst_html):
    if not EMAIL_USER or not EMAIL_PASS or not EMAIL_TO:
        print("❌ E-mail podaci nisu pronađeni u Secrets postavkom!")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_TO
        msg['Subject'] = predmet
        msg.attach(MIMEText(tekst_html, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        server.quit()
        print("📧 Email je uspješno poslan!")
    except Exception as e:
        print(f"❌ Greška pri slanju maila: {e}")

def pokreni_skeniranje():
    print("Preuzimam podatke o dionicama...")
    data = yf.download(dionice_db, period="1y", interval="1d", auto_adjust=True, progress=False)
    signali = []
    kapital = 3000
    max_ulog = kapital * 0.20

    for ticker in dionice_db:
        try:
            close_s = data['Close'][ticker].dropna() if isinstance(data.columns, pd.MultiIndex) else data['Close'].dropna()
            high_s = data['High'][ticker].dropna() if isinstance(data.columns, pd.MultiIndex) else data['High'].dropna()
            low_s = data['Low'][ticker].dropna() if isinstance(data.columns, pd.MultiIndex) else data['Low'].dropna()

            if len(close_s) < 200: continue

            df_t = pd.DataFrame({'High': high_s, 'Low': low_s, 'Close': close_s})
            rsi_s = izracunaj_rsi(close_s)
            sma200 = close_s.rolling(200).mean()
            atr_s = izracunaj_atr(df_t)

            ulaz = float(close_s.iloc[-1])
            rsi_val = float(rsi_s.iloc[-1])
            sma200_val = float(sma200.iloc[-1])
            atr_val = float(atr_s.iloc[-1])

            # Uvjeti za kupovinu (RSI ispod 45 i cijena iznad SMA200)
            if rsi_val <= 45.0 and ulaz >= sma200_val:
                komada = int(max_ulog // ulaz)
                if komada > 0:
                    tp = round(ulaz * 1.04, 2)
                    sl = round(ulaz * 0.98, 2)
                    dana = int(np.ceil((tp - ulaz) / (atr_val * 0.7))) if atr_val > 0 else 5

                    signali.append({
                        "Ticker": ticker,
                        "Ulaz (€/$)": round(ulaz, 2),
                        "RSI": round(rsi_val, 1),
                        "TP (+4%)": tp,
                        "SL (-2%)": sl,
                        "Est. Dana": f"~{dana}d",
                        "Nalog": f"KUPI {komada}x {ticker} @ {round(ulaz,2)} | TP: {tp} | SL: {sl}"
                    })
        except Exception: continue

    if signali:
        df_res = pd.DataFrame(signali)
        html_tablica = df_res.to_html(index=False)
        nalozi = "<br>".join([f"<li><code>{s['Nalog']}</code></li>" for s in signali])
        
        tijelo = f"<h2>🎯 Pronađene prilike za danas:</h2>{html_tablica}<h3>📋 Gotovi Nalozi:</h3><ul>{nalozi}</ul>"
        posalji_email(f"📈 Daily Skener: Pronađeno {len(signali)} dionica!", tijelo)
    else:
        print("Danas nema dionica koje zadovoljavaju uvjete.")

if __name__ == "__main__":
    pokreni_skeniranje()
