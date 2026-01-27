import imaplib
import email
import re
import requests
import os
import uuid

# --- CONFIGURAÇÕES ---
# URL do Supabase (Pode ficar fixa pois é publica, mas a Key deve vir do Secret)
SUPABASE_URL = "https://gmdilslueoobjrjvsfjk.supabase.co" 
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Pega a SECRET Key dos Segredos do GitHub

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def extrair_dados_venda(corpo_email):
    # 1. Extrai o Número da Venda (Procura por "Número da venda: XXXXX")
    match_num = re.search(r'Número da venda:\s*(\d+)', corpo_email, re.IGNORECASE)
    numero = match_num.group(1) if match_num else None
    
    # 2. Extrai o Nome do Produto (Versão Melhorada)
    # Pega TUDO o que estiver na linha do "Anúncio:"
    match_prod = re.search(r'Anúncio:\s*(.+)', corpo_email, re.IGNORECASE)
    
    if match_prod:
        linha_completa = match_prod.group(1).strip()
        
        # Lógica inteligente: O preço está sempre depois do ÚLTIMO traço (-)
        # Então separamos a frase no último traço e pegamos a primeira parte (o nome)
        if '-' in linha_completa:
            # rsplit separa da direita para a esquerda (Right Split)
            produto = linha_completa.rsplit('-', 1)[0].strip()
        else:
            produto = linha_completa # Se não tiver traço, pega tudo
            
        # Limpeza extra (remove espaços duplos se houver)
        produto = " ".join(produto.split())
    else:
        produto = "Software Desconhecido"
    
    return numero, produto

def cadastrar_no_supabase(num_compra, nome_produto):
    # Gera chave aleatória
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
            print(f"✅ Venda Processada com Sucesso!")
            print(f"🛒 Compra: {num_compra}")
            print(f"📦 Produto Identificado: {nome_produto}")
            print(f"🔑 Key Gerada: {serial_key}")
        else:
            print(f"❌ Erro ao salvar no Supabase ({r.status_code}): {r.text}")
            
    except Exception as e:
        print(f"❌ Erro de Conexão: {e}")

def processar_vendas():
    try:
        print("Conectando ao Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Busca emails não lidos com o assunto correto
        status, response = mail.search(None, '(UNSEEN SUBJECT "Venda confirmada -")')
        email_ids = response[0].split()
        print(f"E-mails novos encontrados: {len(email_ids)}")

        for num in email_ids:
            try:
                status, data = mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(data[0][1])
                
                # Decodifica o corpo do email
                corpo = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try: corpo = part.get_payload(decode=True).decode('utf-8')
                            except: corpo = part.get_payload(decode=True).decode('latin-1')
                else:
                    try: corpo = msg.get_payload(decode=True).decode('utf-8')
                    except: corpo = msg.get_payload(decode=True).decode('latin-1')
                
                # Extrai os dados
                numero, produto = extrair_dados_venda(corpo)
                
                if numero:
                    cadastrar_no_supabase(numero, produto)
                    mail.store(num, '+FLAGS', '\\Seen') # Marca como lido
                else:
                    print("⚠️ E-mail lido, mas não achei o 'Número da venda'. Verifique o formato.")
                    
            except Exception as e_email:
                print(f"Erro ao ler um dos emails: {e_email}")
        
        mail.logout()
    except Exception as e:
        print(f"Erro Geral: {e}")

if __name__ == "__main__":
    processar_vendas()
