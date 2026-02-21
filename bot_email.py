import imaplib
import email
import re
import requests
import os
import uuid

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://gmdilslueoobjrjvsfjk.supabase.co"
SUPABASE_KEY = "sb_secret_EhIcfETy5O8B_pfBy0DEmA_9EYAu38P" # Sua chave Secret

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def extrair_dados_venda(corpo_email):
    # 1. Extrai o Número da Venda (Blindado contra caracteres invisíveis)
    # O \D* ignora qualquer "lixo" (espaços HTML, quebras de linha) antes do número
    match_num = re.search(r"N[úu]mero\s+da\s+venda\D*(\d+)", corpo_email, re.IGNORECASE)
    numero = match_num.group(1) if match_num else None
    
    # 2. Extrai o Nome do Produto (Captura a linha inteira e ignora formatações ruins)
    produto = "Software Desconhecido" # Valor padrão caso não ache
    
    match_produto = re.search(r"An[úu]ncio:\s*(.*)", corpo_email, re.IGNORECASE)
    if match_produto:
        linha_produto = match_produto.group(1).strip()
        
        # Removemos o preço (tudo depois do último traço) se houver
        if "-" in linha_produto:
            produto = linha_produto.rsplit("-", 1)[0].strip()
        else:
            produto = linha_produto

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
        "nome_produto": nome_produto,
        "ativo": True
    }
    
    try:
        url_completa = f"{SUPABASE_URL}/rest/v1/licencas"
        r = requests.post(url_completa, json=payload, headers=headers)
        if r.status_code in [200, 201]:
            print(f"✅ SUCESSO! Venda: {num_compra}")
            print(f"📦 Produto: {nome_produto}")
            print(f"🔑 Key: {serial_key}")
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
        
        # Busca emails não lidos com o assunto específico
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada")')
        email_ids = response[0].split()
        print(f"E-mails novos: {len(email_ids)}")

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
            
            numero, produto = extrair_dados_venda(corpo)
            
            if numero:
                cadastrar_no_supabase(numero, produto)
                # Marca o e-mail como lido apenas se tiver sucesso em achar o número
                mail.store(num, '+FLAGS', '\\Seen')
            else:
                print(f"⚠️ Não achei o número da venda no email ID {num}")
                # Útil para debugar: imprime os primeiros 200 caracteres do e-mail problemático
                print(f"🔍 Trecho do e-mail: {corpo[:200]}...")
        
        mail.logout()
    except Exception as e:
        print(f"Erro Geral: {e}")

if __name__ == "__main__":
    processar_vendas()
