import os
import json
import time
import requests
from bs4 import BeautifulSoup

# === CONFIGURAZIONE TELEGRAM ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "IL_TUO_TOKEN_TELEGRAM")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "IL_TUO_CHAT_ID")

# File per la persistenza dello stato delle notifiche
NOTIFIED_FILE = "notified_vessels.json"

def load_notified_vessels():
    """Carica le navi già notificate dal file JSON per evitare duplicati dopo i riavvii."""
    if os.path.exists(NOTIFIED_FILE):
        try:
            with open(NOTIFIED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Errore nel caricamento del file JSON: {e}")
    return set()

def save_notified_vessels(vessels_set):
    """Salva il set delle navi notificate sul file JSON."""
    try:
        with open(NOTIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(vessels_set), f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Errore nel salvataggio del file JSON: {e}")

# Registro navi già notificate (caricato da file)
notified_vessels = load_notified_vessels()

def send_telegram_message(message):
    """Invia un messaggio Telegram tramite la Bot API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Errore invio Telegram: {e}")
        return False

def check_genoa_arrivals():
    """
    Effettua lo scraping degli arrivi previsti al Porto di Genova
    e filtra per navi da crociera MSC e Costa.
    """
    url = "https://www.vesselfinder.com/ports/ITGOA001"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Errore nella richiesta HTTP: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        tables = soup.find_all("table")

        global notified_vessels
        updated = False

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                text = row.text.strip().upper()
                
                if ("MSC " in text or "COSTA " in text) and ("CARGO" not in text and "CONTAINER" not in text):
                    
                    cols = [td.text.strip() for td in row.find_all("td")]
                    if len(cols) >= 2:
                        ship_name = cols[1] if len(cols) > 1 else "Nave MSC/Costa"
                        eta_time = cols[0] if len(cols) > 0 else "In arrivo"
                        
                        vessel_key = f"{ship_name}_{eta_time}"
                        
                        if vessel_key not in notified_vessels:
                            msg = (
                                f"🚢 *Nuovo Arrivo Crociera a Genova!*\n\n"
                                f"📌 *Nave:* {ship_name}\n"
                                f"🕒 *ETA / Arrivo:* {eta_time}\n"
                                f"📍 *Porto:* Genova (ITGOA)\n"
                            )
                            print(f"Notifica inviata per: {ship_name}")
                            
                            if send_telegram_message(msg):
                                notified_vessels.add(vessel_key)
                                updated = True

        if updated:
            save_notified_vessels(notified_vessels)

    except Exception as e:
        print(f"Errore durante lo scraping: {e}")

if __name__ == "__main__":
    print("Bot avviato... Controllo arrivi in corso.")
    while True:
        check_genoa_arrivals()
        time.sleep(1200)
