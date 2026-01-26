import imaplib
import email
import re
import requests
import os
import time

# Configurações via Secrets do GitHub
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SUPABASE_URL = "https://gmdilslueoobjrjvsfjk.supabase.co"
SUPABASE_KEY = os.getenv("sb_publishable_Qe2tvLvV_CSPXaCZbMVT3Q_buxZ9Qrf")


def extrair_numero_compra(corpo_email):
    # Procura o padrão numérico das imagens que você enviou
    match = re.search(r'(?:compra|venda|Número):\s*(\d+)', corpo_email, re.IGNORECASE)
    return match.group(1) if match else None


def cadastrar_no_supabase(num_compra):
    serial = f"KEY-{num_compra}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-upsert"
    }
    payload = {"numero_compra": str(num_compra), "serial_key": serial, "ativo": True}
    requests.post(SUPABASE_URL, json=payload, headers=headers)


def processar_emails():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        _, search_data = mail.search(None, 'UNSEEN')

        for num in search_data[0].split():
            _, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            corpo = str(msg.get_payload(decode=True)) if not msg.is_multipart() else ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        corpo = str(part.get_payload(decode=True))

            num_compra = extrair_numero_compra(corpo)
            if num_compra:
                cadastrar_no_supabase(num_compra)
                mail.store(num, '+FLAGS', '\\Seen')
        mail.logout()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    # Roda a primeira vez
    processar_emails()
    # Espera 150 segundos (2.5 min) e roda de novo dentro do mesmo minuto do GitHub
    time.sleep(150)
    processar_emails()