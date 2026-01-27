import imaplib
import email
import re
import requests
import os
import uuid

# --- CONFIGURAÇÕES ---
SUPABASE_URL = "https://gmdilslueoobjrjvsfjk.supabase.co"

# CORREÇÃO: A chave deve ser uma string direta ou a variável de ambiente correta.
# Como você já expôs a chave aqui, vou colocá-la direta para garantir que funcione.
SUPABASE_KEY = "sb_secret_EhIcfETy5O8B_pfBy0DEmA_9EYAu38P" 

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
                try: corpo = payload.decode('utf-8')
                except: 
                    try: corpo = payload.decode('latin-1')
                    except: corpo = str(payload)
                break 
    else:
        payload = msg.get_payload(decode=True)
        try: corpo = payload.decode('utf-8')
        except: 
            try: corpo = payload.decode('latin-1')
            except: corpo = str(payload)
            
    return corpo

def extrair_dados_venda(corpo_email):
    # Remove quebras de linha para facilitar a busca
    corpo_limpo = " ".join(corpo_email.splitlines())

    # 1. Extrai o Número da Venda (Prioridade para o campo específico)
    match_venda = re.search(r'Número da venda:\s*(\d+)', corpo_email, re.IGNORECASE)
    if match_venda:
        numero = match_venda.group(1)
    else:
        # Se falhar, tenta pegar apenas "Número:" (cuidado para não pegar o do anúncio)
        # No seu email, o número da venda aparece bem claro no final.
        match_generic = re.search(r'Número da venda:\s*(\d+)', corpo_limpo, re.IGNORECASE)
        numero = match_generic.group(1) if match_generic else None

    # 2. Extrai o Nome do Produto
    # Pega tudo depois de "Anúncio:" até encontrar o traço do preço
    match_prod = re.search(r'Anúncio:\s*(.+?)\s*-\s*\d+', corpo_email, re.IGNORECASE | re.DOTALL)
    
    if match_prod:
        # Pega o grupo, remove quebras de linha e espaços extras
        raw_prod = match_prod.group(1)
        produto = " ".join(raw_prod.split()).strip()
    else:
        # Tentativa de backup linha a linha
        match_backup = re.search(r'Anúncio:\s*(.+)', corpo_email, re.IGNORECASE)
        if match_backup:
            # Separa no último traço (-)
            produto = match_backup.group(1).rsplit('-', 1)[0].strip()
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
        
        # BUSCA APENAS EMAILS NÃO LIDOS (UNSEEN)
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada")')
        email_ids = response[0].split()
        print(f"E-mails novos encontrados: {len(email_ids)}")

        for num in email_ids:
            try:
                status, data = mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(data[0][1])
                corpo = decodificar_corpo(msg)
                
                # Debug para você ver o que ele leu
                # print(f"--- Corpo do Email ---\n{corpo}\n----------------------")

                numero, produto = extrair_dados_venda(corpo)
                
                if numero:
                    print(f"Processando venda: {numero}")
                    cadastrar_no_supabase(numero, produto)
                    mail.store(num, '+FLAGS', '\\Seen') # Marca como lido
                else:
                    print(f"⚠️ E-mail lido, mas número não encontrado.")
                    
            except Exception as e_email:
                print(f"Erro no email {num}: {e_email}")
        
        mail.logout()
    except Exception as e:
        print(f"Erro Geral: {e}")

if __name__ == "__main__":
    processar_vendas()
