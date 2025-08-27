import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import sqlite3
import json

# --- Configurações da API do WhatsApp ---
META_TOKEN = os.environ.get('META_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN') 

# --- Configurações do Flask e do Banco de Dados ---
app = Flask(__name__)
conn = sqlite3.connect('chatbot.db')
cursor = conn.cursor()

# --- VARIÁVEL GLOBAL DE ESTADOS DO USUÁRIO ---
user_states = {}

def create_table():
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY,
                nome TEXT,
                email TEXT,
                modelo TEXT,
                ano INTEGER,
                armazenamento TEXT,
                jogos TEXT,
                localizacao_solicitada TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Erro ao criar a tabela: {e}")

def save_lead(nome, email, modelo, ano, armazenamento, jogos, localizacao_solicitada):
    try:
        cursor.execute('''
            INSERT INTO leads (nome, email, modelo, ano, armazenamento, jogos, localizacao_solicitada)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, email, modelo, ano, armazenamento, jogos, localizacao_solicitada))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Erro ao salvar o lead: {e}")

def get_bot_response(user_id, message_text):
    state = user_states.get(user_id, {'state': 'start'})

    # Verificação para encerrar a conversa a qualquer momento
    if message_text.lower() in ["encerrar", "parar", "cancelar", "sair"]:
        user_states[user_id] = {'state': 'start'}
        return "Conversa encerrada. Se precisar de algo, é só me chamar novamente. Digite 'olá' para recomeçar."
        
    # Lógica aprimorada de início da conversa
    if state['state'] == 'start':
        if message_text.lower() in ["olá", "ola", "oi", "iniciar"]:
            user_states[user_id] = {'state': 'awaiting_name'}
            return "Olá! Sou seu assistente virtual para conserto e desbloqueio de Xbox 360. Para começar, por favor, me informe seu nome completo."
        else:
            return "Olá! Para iniciar a conversa, por favor, digite 'olá'."

    # Salva o Nome e Pede o E-mail
    if state['state'] == 'awaiting_name':
        user_states[user_id]['nome'] = message_text.strip().capitalize()
        user_states[user_id]['state'] = 'awaiting_email'
        nome_usuario = user_states[user_id]['nome']
        return f"Ótimo, {nome_usuario}! Agora, por favor, me informe seu e-mail."

    # Valida e Salva o E-mail
    if state['state'] == 'awaiting_email':
        email = message_text.strip().lower()
        if "@" in email and "." in email:
            user_states[user_id]['email'] = email
            user_states[user_id]['state'] = 'awaiting_model'
            return "E-mail registrado! Agora, vamos falar sobre seu console. Qual é o modelo do seu Xbox 360?\nDigite:\n1. Fat\n2. Slim\n3. Super Slim"
        else:
            return "Parece que o e-mail não está em um formato válido. Por favor, digite seu e-mail novamente."

    # Fluxo restante da conversa (mantido)
    if state['state'] == 'awaiting_model':
        model_map = {'1': 'Fat', '2': 'Slim', '3': 'Super Slim'}
        if message_text in model_map:
            user_states[user_id]['modelo'] = model_map[message_text]
            user_states[user_id]['state'] = 'awaiting_year'
            return "Certo. E qual é o ano de fabricação dele? (Entre 2007 e 2015)\nLembre-se: se for de 2015, o desbloqueio definitivo não será possível."
        else:
            return "Opção inválida. Por favor, escolha 1, 2 ou 3."

    if state['state'] == 'awaiting_year':
        try:
            year = int(message_text)
            if 2007 <= year <= 2015:
                user_states[user_id]['ano'] = year
                user_states[user_id]['state'] = 'awaiting_storage'
                return "Para copiar os jogos, precisamos de um dispositivo de armazenamento. Seu console tem HD interno, HD externo ou um pendrive de no mínimo 16GB?\nDigite:\n1. HD Interno\n2. HD Externo\n3. Pendrive\n4. Nenhuma das opções"
            else:
                return "Ano inválido. Por favor, digite um ano entre 2007 e 2015."
        except ValueError:
            return "Entrada inválida. Por favor, digite um número."

    if state['state'] == 'awaiting_storage':
        if message_text == '4':
            user_states[user_id]['armazenamento'] = 'Nenhuma'
            user_states[user_id]['jogos'] = 'Nenhum'
            user_states[user_id]['state'] = 'awaiting_continue_or_end'
            return "Entendido. Não será possível continuar o processo de cópia de jogos sem um dispositivo de armazenamento.\n\nVocê gostaria de continuar a conversa para conserto e desbloqueio ou prefere encerrar?\nDigite:\n1. Continuar\n2. Encerrar"
        
        storage_map = {'1': 'HD Interno', '2': 'HD Externo', '3': 'Pendrive'}
        if message_text in storage_map:
            user_states[user_id]['armazenamento'] = storage_map[message_text]
            user_states[user_id]['state'] = 'awaiting_games'
            return "Ótimo! Agora, por favor, escolha até 3 jogos da lista. Digite os números separados por vírgula (ex: 1, 3, 4).\nOpções:\n1. GTA V\n2. PES 2013\n3. PES 2018\n4. FIFA 19"
        else:
            return "Opção inválida. Por favor, escolha uma das opções de 1 a 4."
    
    # --- NOVO ESTADO: Agora com opções numeradas ---
    if state['state'] == 'awaiting_continue_or_end':
        if message_text in ["1", "continuar"]:
            user_states[user_id]['state'] = 'awaiting_location'
            return "Perfeito! Para finalizar, você gostaria de receber a localização da nossa loja para trazer seu console?\nDigite:\n1. Sim\n2. Não"
        elif message_text in ["2", "encerrar"]:
            user_states[user_id] = {'state': 'start'}
            return "Tudo bem, conversa encerrada. Se precisar de algo, é só me chamar. Obrigado!"
        else:
            return "Opção inválida. Por favor, digite '1' para continuar ou '2' para encerrar."

    if state['state'] == 'awaiting_games':
        game_map = {'1': 'GTA V', '2': 'PES 2013', '3': 'PES 2018', '4': 'FIFA 19'}
        selected_games = []
        choices = message_text.replace(" ", "").split(',')
        for choice in choices:
            if choice in game_map:
                selected_games.append(game_map[choice])
        
        user_states[user_id]['jogos'] = ', '.join(selected_games)
        user_states[user_id]['state'] = 'awaiting_location'
        return "Perfeito! Já tenho todas as informações. Para finalizar, você gostaria de receber a localização da nossa loja para trazer seu console?\nDigite:\n1. Sim\n2. Não"

    if state['state'] == 'awaiting_location':
        location_map = {'1': 'Sim', '2': 'Não'}
        if message_text in location_map:
            user_states[user_id]['localizacao'] = location_map[message_text]
            
            save_lead(
                user_states[user_id].get('nome'),
                user_states[user_id].get('email'),
                user_states[user_id].get('modelo'),
                user_states[user_id].get('ano'),
                user_states[user_id].get('armazenamento'),
                user_states[user_id].get('jogos'),
                user_states[user_id].get('localizacao')
            )

            resumo = (
                f"\n\n*Resumo do Pedido*\n"
                f"Nome: {user_states[user_id].get('nome')}\n"
                f"E-mail: {user_states[user_id].get('email')}\n"
                f"Modelo do Xbox: {user_states[user_id].get('modelo')}\n"
                f"Ano de Fabricação: {user_states[user_id].get('ano')}\n"
                f"Armazenamento: {user_states[user_id].get('armazenamento')}\n"
                f"Jogos Selecionados: {user_states[user_id].get('jogos')}\n"
                f"Localização Solicitada: {user_states[user_id].get('localizacao')}"
            )

            user_states[user_id] = {'state': 'start'}
            
            if location_map[message_text] == 'Sim':
                return resumo + "\n\nAqui está o link para a localização da nossa loja no Google Maps: https://maps.app.goo.gl/UYBxmyn1qm893aRC6. Estamos ansiosos para te receber! Se precisar de algo mais, é só me chamar."
            else:
                return resumo + "\n\nOk. Se precisar de algo, estarei aqui para ajudar. Obrigado!"
        else:
            return "Opção inválida. Por favor, escolha 1 ou 2."

    return "Desculpe, não entendi. Tente digitar 'olá' para recomeçar."
    
def send_whatsapp_message(to_number, text_message):
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": text_message
        }
    }
    requests.post(f"https://graph.facebook.com/v15.0/{PHONE_NUMBER_ID}/messages", headers=headers, json=payload)

# --- ROTAS DO FLASK ---
@app.route('/whatsapp_webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    print("--- Webhook recebido ---")
    try:
        if request.method == 'GET':
            print("Webhook verification (GET) request received.")
            mode = request.args.get('hub.mode')
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')
            
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                print("Webhook verified successfully.")
                return challenge, 200
            else:
                print("Webhook verification failed.")
                return 'Webhook verification failed', 403

        elif request.method == 'POST':
            if request.form:
                print("Webhook detectado como Twilio.")
                message_info = request.form
                from_number = message_info.get('From')
                message_text = message_info.get('Body')
                response_type = 'twilio'
            elif request.json and "entry" in request.json:
                print("Webhook detectado como Meta (WhatsApp Cloud API).")
                data = request.json
                if "messages" in data["entry"][0]["changes"][0]["value"]:
                    message_info = data["entry"][0]["changes"][0]["value"]["messages"][0]
                    from_number = message_info["from"]
                    if "text" in message_info:
                        message_text = message_info["text"]["body"]
                        print(f"Mensagem de texto recebida: {message_text}")
                    else:
                        message_text = None
                        print(f"Mensagem de tipo '{message_info.get('type')}' recebida. Ignorando...")
                else:
                    message_text = None
                    from_number = None
                    print("Mensagem de status ou sem conteúdo. Ignorando.")
                
                response_type = 'meta'
            else:
                print("Formato de webhook desconhecido ou vazio.")
                return "OK", 200

            if not from_number:
                return "OK", 200
            
            if message_text:
                bot_response = get_bot_response(from_number, message_text)
                print(f"Resposta do bot gerada: {bot_response}")
            else:
                return "OK", 200
                
            if response_type == 'twilio':
                resp = MessagingResponse()
                resp.message(bot_response)
                return str(resp)
            else:
                send_whatsapp_message(from_number, bot_response)
                return "OK", 200
        
    except Exception as e:
        print(f"\n--- ERRO CRÍTICO ---")
        print(f"Erro no processamento do webhook: {e}")
        error_message = "Desculpe, um erro inesperado ocorreu. Por favor, tente novamente mais tarde."
        
        try:
            if 'response_type' in locals() and response_type == 'twilio':
                resp = MessagingResponse()
                resp.message(error_message)
                return str(resp), 500
            elif 'from_number' in locals():
                send_whatsapp_message(from_number, error_message)
        except Exception as e_inner:
            print(f"Erro ao enviar mensagem de erro: {e_inner}")

        return "Internal Server Error", 500


if __name__ == '__main__':
    create_table()
    app.run(host='0.0.0.0', port=5000, debug=True)