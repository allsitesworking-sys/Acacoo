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
    # 1. Limpeza pesada: Remove espaços invisíveis (\xa0)
    corpo_email = corpo_email.replace('\xa0', ' ')
    
    # 2. Extrai o Número da Venda (CORRIGIDO E FUNCIONANDO)
    match_num = re.search(r'mero da venda:\D*(\d+)', corpo_email, re.IGNORECASE)
    numero = match_num.group(1) if match_num else None
    
    # 3. Limpeza de HTML: Remove todas as tags (<a href...>, <b>, etc)
    # Isso transforma o "código do link" no texto puro que você quer ler.
    texto_puro = re.sub(r'<[^>]+>', '', corpo_email)
    
    # 4. Extrai o Nome do Produto
    produto = "Software Desconhecido" # Valor padrão caso não ache
    
    # Divide o texto limpo em linhas
    linhas = texto_puro.splitlines()
    
    for linha in linhas:
        linha_limpa = linha.strip()
        
        # Ignora a linha de "Detalhes" e acha a linha do "Anúncio:"
        if "ncio:" in linha_limpa.lower() and "detalhes" not in linha_limpa.lower():
            
            partes = linha_limpa.split(":", 1)
            
            if len(partes) > 1:
                conteudo = partes[1].strip()
                
                # Só processa se realmente existir texto
                if conteudo != "":
                    # Salva exatamente o texto da frente (ex: "Mu Online |Auto Pick... - 9,99")
                    produto = conteudo
                    break # Achou o produto, pode parar!

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
