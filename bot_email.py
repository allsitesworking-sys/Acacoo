import imaplib
import email
import re
import requests
import os
import uuid

# Configurações via Secrets
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
# Substitua a linha antiga por esta:
SUPABASE_URL = "https://gmdilslueoobjrjvsfjk.supabase.co"
SUPABASE_KEY = os.getenv("sb_publishable_Qe2tvLvV_CSPXaCZbMVT3Q_buxZ9Qrf")


def extrair_numero_venda(corpo_email):
    # CORREÇÃO: Procura especificamente por "Número da venda:" para não pegar o ID do anúncio
    match = re.search(r'Número da venda:\s*(\d+)', corpo_email, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def cadastrar_no_supabase(num_compra):
    # Gera chave aleatória (Ex: A1B2-C3D4-E5F6-7890)
    raw = str(uuid.uuid4()).replace('-', '').upper()
    serial_key = f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"

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

    # Se SUPABASE_URL vier vazio, avisa no log para facilitar debug
    if not SUPABASE_URL:
        print("ERRO CRÍTICO: SUPABASE_URL não foi encontrada nas variáveis de ambiente.")
        return

    try:
        r = requests.post(SUPABASE_URL, json=payload, headers=headers)
        if r.status_code in [200, 201]:
            print(f"✅ SUCESSO! Venda: {num_compra} | Key: {serial_key}")
        else:
            print(f"❌ Erro Supabase ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")


def processar_vendas():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Filtra pelo assunto exato que você recebe
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada -")')

        email_ids = response[0].split()
        print(f"E-mails encontrados para processar: {len(email_ids)}")

        for num in email_ids:
            status, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])

            corpo = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            corpo = part.get_payload(decode=True).decode('utf-8')
                        except:
                            corpo = part.get_payload(decode=True).decode('latin-1')
            else:
                try:
                    corpo = msg.get_payload(decode=True).decode('utf-8')
                except:
                    corpo = msg.get_payload(decode=True).decode('latin-1')

            # Aqui chamamos a nova função corrigida
            num_venda = extrair_numero_venda(corpo)

            if num_venda:
                print(f"Processando venda número: {num_venda}")
                cadastrar_no_supabase(num_venda)
                # Marca como lido
                mail.store(num, '+FLAGS', '\\Seen')
            else:
                print("E-mail lido, mas não achei o 'Número da venda'.")

        mail.logout()
    except Exception as e:
        print(f"Erro no processamento: {e}")


if __name__ == "__main__":
    processar_vendas()

