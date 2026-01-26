import imaplib
import email
import re
import requests
import os

# Configurações via Secrets do GitHub
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SUPABASE_URL = os.getenv("https://gmdilslueoobjrjvsfjk.supabase.co")
SUPABASE_KEY = os.getenv("sb_publishable_Qe2tvLvV_CSPXaCZbMVT3Q_buxZ9Qrf")


def extrair_numero_compra(corpo_email):
    # Procura o número da compra no corpo do e-mail
    match = re.search(r'(?:compra|venda):\s*(\d+)', corpo_email, re.IGNORECASE)
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


def processar_vendas():
    try:
        # Conexão com o Gmail usando SSL
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # BUSCA REFINADA: Procura e-mails não lidos com o assunto específico
        # O filtro 'SUBJECT "Venda confirmada -"' garante que apenas esses e-mails sejam lidos
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada -")')

        for num in response[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])

            # Extração do conteúdo do e-mail
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
                # Marca como lido após o processamento
                mail.store(num, '+FLAGS', '\\Seen')

        mail.logout()
    except Exception as e:
        print(f"Erro ao processar: {e}")


if __name__ == "__main__":
    processar_vendas()
