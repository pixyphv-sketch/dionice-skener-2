import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import numpy as np
import pandas as pd
import yfinance as yf

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

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
        print("❌ E-mail podaci nisu postavljeni.")
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
        print("📧 Email poslan!")
    except Exception as e:
        print(f"❌ Greška pri slanju emaila: {e}")

def generiraj_html_stranicu(df_signali):
    datum_vrijeme = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M CEST')
    
    if df_signali is not None and not df_signali.empty:
        df_prikaz = df_signali.drop(columns=["Nalog"])
        tablica_html = df_prikaz.to_html(index=False, escape=False, classes='moja-tablica')
        nalozi_html = "<br>".join([f"<li><code>{row['Nalog']}</code></li>" for _, row in df_signali.iterrows()])
        sadrzaj = f"""
        <div class="card">
            <h3>✅ Pronađeni Signali</h3>
            <div style="overflow-x:auto;">{tablica_html}</div>
            <hr style="border: 0.5px solid #333; margin: 20px 0;">
            <h3>📋 Gotovi Nalozi za Brokera</h3>
            <ul>{nalozi_html}</ul>
        </div>
        """
    else:
        sadrzaj = """
        <div class="card warning">
            ⚠️ <b>Danas nema dionica koje zadovoljavaju postavljene uvjete (RSI ≤ 45 i iznad SMA200).</b>
        </div>
        """

    html_kod = f"""
    <!DOCTYPE html>
    <html lang="hr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Stock Scanner</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #ffffff; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            h1 {{ color: #2ed573; text-align: center; margin-bottom: 5px; }}
            .datum {{ text-align: center; color: #a4b0be; font-size: 0.9em; margin-bottom: 25px; }}
            .card {{ background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #333; }}
            .warning {{ background-color: #2d1b1b; color: #ff6b6b; border-color: #ff4757; text-align: center; }}
            .moja-tablica {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: center; }}
            .moja-tablica th {{ background-color: #1b4d3e; color: #2ed573; padding: 12px; border-bottom: 2px solid #2ed573; }}
            .moja-tablica td {{ padding: 10px; border-bottom: 1px solid #333; }}
            .moja-tablica tr:nth-child(even) {{ background-color: #242424; }}
            code {{ background-color: #222; color: #2ed573; padding: 4px 8px; border-radius: 4px; font-size: 13px; }}
            ul {{ list-style-type: none; padding-left: 0; }}
            li {{ margin-bottom: 8px; }}
            a {{ color: #2ed573; text-decoration: underline; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📈 Dnevni Skener Dionica</h1>
            <div class="datum">Zadnje ažuriranje: {datum_vrijeme}</div>
            {sadrzaj}
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_kod)
    print("🌐 Web stranica index.html je uspješno generirana!")

def pokreni_skeniranje():
    print("Preuzimam podatke...")
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

            if rsi_val <= 45.0 and ulaz >= sma200_val:
                komada = int(max_ulog // ulaz)
                if komada > 0:
                    tp = round(ulaz * 1.04, 2)
                    sl = round(ulaz * 0.98, 2)
                    dana = int(np.ceil((tp - ulaz) / (atr_val * 0.7))) if atr_val > 0 else 5

                    url = f"https://finance.yahoo.com/quote/{ticker}"
                    link_html = f'<a href="{url}" target="_blank">{ticker} 🔗</a>'

                    signali.append({
                        "Dionica": link_html,
                        "Ulaz (€/$)": round(ulaz, 2),
                        "RSI": round(rsi_val, 1),
                        "TP (+4%)": tp,
                        "SL (-2%)": sl,
                        "Est. Dana": f"~{dana}d",
                        "Nalog": f"KUPI {komada}x {ticker} @ {round(ulaz,2)} | TP: {tp} | SL: {sl}"
                    })
        except Exception: continue

    df_res = pd.DataFrame(signali) if signali else None
    
    generiraj_html_stranicu(df_res)

    if df_res is not None and not df_res.empty:
        html_tablica = df_res.drop(columns=["Nalog"]).to_html(index=False, escape=False)
        nalozi = "<br>".join([f"<li><code>{s['Nalog']}</code></li>" for s in signali])
        tijelo = f"<h2>🎯 Pronađene prilike za danas:</h2>{html_tablica}<h3>📋 Gotovi Nalozi:</h3><ul>{nalozi}</ul>"
        posalji_email(f"📈 Daily Skener: Pronađeno {len(signali)} dionica!", tijelo)

if __name__ == "__main__":
    pokreni_skeniranje()
