import imaplib
import email
import re
import requests
import os
import uuid

# Configurações via Secrets
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SUPABASE_URL = os.getenv("https://gmdilslueoobjrjvsfjk.supabase.co")
SUPABASE_KEY = os.getenv("sb_publishable_Qe2tvLvV_CSPXaCZbMVT3Q_buxZ9Qrf")


def extrair_numero_compra(corpo_email):
    # Tenta capturar apenas os números após "compra:" ou "venda:"
    match = re.search(r'(?:compra|venda|Número):\s*(\d+)', corpo_email, re.IGNORECASE)
    return match.group(1) if match else None


def gerar_chave_formatada():
    # Gera um código aleatório e formata como XXXX-XXXX-XXXX-XXXX
    raw = str(uuid.uuid4()).replace('-', '').upper()
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"


def cadastrar_no_supabase(num_compra):
    serial_key = gerar_chave_formatada()

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-upsert"
    }

    payload = {
        "numero_compra": str(num_compra),
        "serial_key": serial_key,
        "ativo": True
    }

    r = requests.post(SUPABASE_URL, json=payload, headers=headers)
    if r.status_code in [200, 201]:
        print(f"✅ Sucesso! Compra: {num_compra} | Key: {serial_key}")
    else:
        print(f"❌ Erro ao salvar: {r.text}")


def processar_vendas():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Filtra apenas e-mails da DFG não lidos
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada -")')

        email_ids = response[0].split()
        print(f"E-mails encontrados: {len(email_ids)}")

        for num in email_ids:
            status, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])

            corpo = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        corpo = str(part.get_payload(decode=True).decode('utf-8'))
            else:
                corpo = str(msg.get_payload(decode=True).decode('utf-8'))

            num_compra = extrair_numero_compra(corpo)

            if num_compra:
                cadastrar_no_supabase(num_compra)
                # Marca como lido apenas se deu tudo certo
                mail.store(num, '+FLAGS', '\\Seen')

        mail.logout()
    except Exception as e:
        print(f"Erro fatal: {e}")


if __name__ == "__main__":
    processar_vendas()
