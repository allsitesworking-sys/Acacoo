import imaplib
import email
import re
import requests
import os
import uuid

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://gmdilslueoobjrjvsfjk.supabase.co"
SUPABASE_KEY = "sb_secret_EhIcfETy5O8B_pfBy0DEmA_9EYAu38P" # Use a SECRET aqui

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def extrair_dados_venda(corpo_email):
    # 1. Extrai o Número da Venda
    match_num = re.search(r'Número da venda:\s*(\d+)', corpo_email, re.IGNORECASE)
    numero = match_num.group(1) if match_num else None
    
    # 2. Extrai o Nome do Produto (Pega tudo depois de 'Anúncio:' até o traço do preço)
    # Exemplo do email: "Anúncio: Mucabrasil Auto Pick | Zen... - 39,99"
    match_prod = re.search(r'Anúncio:\s*(.*?)\s*-\s*\d+', corpo_email, re.IGNORECASE)
    produto = match_prod.group(1).strip() if match_prod else "Software Desconhecido"
    
    return numero, produto

def cadastrar_no_supabase(num_compra, nome_produto):
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
        "nome_produto": nome_produto,  # <--- NOVA INFORMAÇÃO ENVIADA
        "ativo": True
    }
    
    try:
        url_completa = f"{SUPABASE_URL}/rest/v1/licencas"
        r = requests.post(url_completa, json=payload, headers=headers)
        if r.status_code in [200, 201]:
            print(f"✅ Venda: {num_compra} | Produto: {nome_produto} | Key Gerada")
        else:
            print(f"❌ Erro Supabase: {r.text}")
    except Exception as e:
        print(f"❌ Erro Conexão: {e}")

def processar_vendas():
    try:
        print("Conectando ao Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada -")')
        email_ids = response[0].split()
        print(f"E-mails novos: {len(email_ids)}")

        for num in email_ids:
            status, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            
            corpo = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try: corpo = part.get_payload(decode=True).decode('utf-8')
                        except: corpo = part.get_payload(decode=True).decode('latin-1')
            else:
                try: corpo = msg.get_payload(decode=True).decode('utf-8')
                except: corpo = msg.get_payload(decode=True).decode('latin-1')
            
            numero, produto = extrair_dados_venda(corpo)
            
            if numero:
                cadastrar_no_supabase(numero, produto)
                mail.store(num, '+FLAGS', '\\Seen')
        
        mail.logout()
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    processar_vendas()
