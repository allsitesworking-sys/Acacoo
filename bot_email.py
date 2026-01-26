import imaplib
import email
import re
import requests
import os
import uuid

# --- SEUS DADOS JÁ CONFIGURADOS ---
SUPABASE_URL = "https://gmdilslueoobjrjvsfjk.supabase.co"
SUPABASE_KEY = "sb_publishable_Qe2tvLvV_CSPXaCZbMVT3Q_buxZ9Qrf"

# O usuário e senha do e-mail continuam vindo dos Segredos (Segurança)
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def extrair_numero_venda(corpo_email):
    # Procura pelo padrão "Número da venda: XXXXX"
    match = re.search(r'Número da venda:\s*(\d+)', corpo_email, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def cadastrar_no_supabase(num_compra):
    # Gera chave aleatória (Ex: A1B2-C3D4-E5F6)
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
    
    try:
        # AQUI ESTAVA O ERRO 404: Agora o endereço está completo
        url_completa = f"{SUPABASE_URL}/rest/v1/licencas"
        
        r = requests.post(url_completa, json=payload, headers=headers)
        
        if r.status_code in [200, 201]:
            print(f"✅ SUCESSO! Venda salva no banco: {num_compra} | Serial: {serial_key}")
        else:
            print(f"❌ Erro ao salvar ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

def processar_vendas():
    try:
        print("Conectando ao Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Busca apenas e-mails NÃO LIDOS com o assunto correto
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada -")')
        
        email_ids = response[0].split()
        print(f"E-mails não lidos encontrados: {len(email_ids)}")

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
            
            num_venda = extrair_numero_venda(corpo)
            
            if num_venda:
                print(f"Processando venda: {num_venda}")
                cadastrar_no_supabase(num_venda)
                mail.store(num, '+FLAGS', '\\Seen') # Marca como lido após sucesso
            else:
                print("E-mail encontrado, mas o número da venda não estava no padrão esperado.")
        
        mail.logout()
    except Exception as e:
        print(f"Erro geral no script: {e}")

if __name__ == "__main__":
    processar_vendas()
