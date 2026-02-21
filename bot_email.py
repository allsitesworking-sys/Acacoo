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
    # 1. Extrai o Número da Venda (A correção blindada que funcionou)
    match_num = re.search(r'mero da venda:\D*(\d+)', corpo_email, re.IGNORECASE)
    numero = match_num.group(1) if match_num else None
    
    # 2. Extrai o Nome do Produto (Sua lógica adaptada para o novo corpo)
    produto = "Software Desconhecido" # Valor padrão caso não ache
    
    # Divide o e-mail em uma lista de linhas e analisa uma por uma
    linhas = corpo_email.splitlines()
    
    for linha in linhas:
        # Substitui espaços invisíveis em HTML (\xa0) por espaços normais e limpa
        linha_limpa = linha.replace(u'\xa0', u' ').strip()
        
        # Em vez de startswith, usamos "in" para evitar falhas se a linha começar com espaços
        # Verificamos "núncio:" para contornar qualquer erro na primeira letra 'A'
        if "núncio:" in linha_limpa.lower() or "nuncio:" in linha_limpa.lower():
            
            # Divide a frase onde estão os dois pontos ":"
            partes = linha_limpa.split(":", 1)
            
            if len(partes) > 1:
                conteudo = partes[1].strip()
                
                # Agora removemos o preço (tudo depois do último traço)
                if "-" in conteudo:
                    # Pega só a parte da esquerda do último traço
                    produto = conteudo.rsplit("-", 1)[0].strip()
                else:
                    produto = conteudo
            
            break # Para de procurar, já achamos!

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
            print(f"📦 Produto: {nome_produto}") # Agora vai aparecer certo!
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
        
        # Busca emails não lidos
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
                        try: corpo = part.get_payload(decode=True).decode('utf-8')
                        except: corpo = part.get_payload(decode=True).decode('latin-1')
            else:
                try: corpo = msg.get_payload(decode=True).decode('utf-8')
                except: corpo = msg.get_payload(decode=True).decode('latin-1')
            
            numero, produto = extrair_dados_venda(corpo)
            
            if numero:
                cadastrar_no_supabase(numero, produto)
                mail.store(num, '+FLAGS', '\\Seen')
            else:
                print(f"⚠️ Não achei o número da venda no email ID {num}")
        
        mail.logout()
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    processar_vendas()
