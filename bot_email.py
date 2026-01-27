import imaplib
import email
import re
import requests
import os
import uuid
import quopri

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://gmdilslueoobjrjvsfjk.supabase.co"
# ATENÇÃO: A chave deve vir do ambiente (Secrets), não fixada no código para segurança
SUPABASE_KEY = os.getenv("sb_secret_EhIcfETy5O8B_pfBy0DEmA_9EYAu38P") # Pega a SECRET Key dos Segredos do GitHub

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def decodificar_corpo(msg):
    corpo = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))

            if ctype == "text/plain" and "attachment" not in cdispo:
                payload = part.get_payload(decode=True)
                try:
                    corpo = payload.decode('utf-8')
                except:
                    try: corpo = payload.decode('latin-1')
                    except: corpo = str(payload)
                break # Pega apenas a primeira parte de texto plano
    else:
        payload = msg.get_payload(decode=True)
        try:
            corpo = payload.decode('utf-8')
        except:
            try: corpo = payload.decode('latin-1')
            except: corpo = str(payload)
            
    return corpo

def extrair_dados_venda(corpo_email):
    # Remove quebras de linha excessivas para facilitar a busca
    corpo_limpo = " ".join(corpo_email.splitlines())

    # 1. Extrai o Número da Venda
    # Procura por "Número da venda:" seguido de digitos
    match_num = re.search(r'Número da venda:\s*(\d+)', corpo_email, re.IGNORECASE)
    if not match_num:
         # Tenta procurar na versão de uma linha só caso a formatação esteja estranha
         match_num = re.search(r'Número da venda:\s*(\d+)', corpo_limpo, re.IGNORECASE)
    
    numero = match_num.group(1) if match_num else None
    
    # 2. Extrai o Nome do Produto
    # Procura por "Anúncio:" ... até ... "- PREÇO"
    # A regex pega tudo (.*?) até encontrar um traço seguido de digitos (preço)
    match_prod = re.search(r'Anúncio:\s*(.+?)\s*-\s*\d+[\.,]\d+', corpo_email, re.IGNORECASE | re.DOTALL)
    
    if match_prod:
        produto = match_prod.group(1).strip()
        # Remove caracteres indesejados se necessário (ex: quebras de linha no meio do nome)
        produto = produto.replace('\n', ' ').replace('\r', '')
        produto = " ".join(produto.split()) # Remove espaços duplos
    else:
        # Tentativa secundária: pega a linha inteira do anúncio
        match_prod_backup = re.search(r'Anúncio:\s*(.+)', corpo_email, re.IGNORECASE)
        if match_prod_backup:
            produto = match_prod_backup.group(1).split('-')[0].strip()
        else:
            produto = "Software Desconhecido"
    
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
            print(f"✅ SUCESSO! Venda: {num_compra} | Produto: {nome_produto} | Key: {serial_key}")
        else:
            print(f"❌ Erro Supabase ({r.status_code}): {r.text}")
            
    except Exception as e:
        print(f"❌ Erro de Conexão: {e}")

def processar_vendas():
    try:
        print("Conectando ao Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Filtro ajustado: Busca qualquer e-mail não lido com "Venda confirmada" no assunto
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada")')
        email_ids = response[0].split()
        print(f"E-mails novos encontrados: {len(email_ids)}")

        for num in email_ids:
            try:
                status, data = mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(data[0][1])
                
                corpo = decodificar_corpo(msg)
                
                # Debug: Mostra o início do corpo para conferência (opcional)
                # print(f"Corpo parcial: {corpo[:100]}...")

                numero, produto = extrair_dados_venda(corpo)
                
                if numero:
                    print(f"Processando venda: {numero}")
                    cadastrar_no_supabase(numero, produto)
                    mail.store(num, '+FLAGS', '\\Seen') # Marca como lido
                else:
                    print(f"⚠️ E-mail lido (ID {num}), mas padrão de venda não encontrado.")
                    # mail.store(num, '+FLAGS', '\\Seen') # Descomente se quiser marcar como lido mesmo com erro
                    
            except Exception as e_email:
                print(f"Erro ao processar e-mail ID {num}: {e_email}")
        
        mail.logout()
    except Exception as e:
        print(f"Erro Geral no Script: {e}")

if __name__ == "__main__":
    processar_vendas()
