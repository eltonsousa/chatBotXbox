from flask import request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
from database import get_lead_status, update_lead_status_and_data, get_lead_info, save_lead_to_db
import json
import re

# Carrega o conteúdo dinâmico do arquivo JSON
try:
    with open('content.json', 'r', encoding='utf-8') as f:
        content_data = json.load(f)
except FileNotFoundError:
    print("Erro: O arquivo 'content.json' não foi encontrado. Certifique-se de que ele está na mesma pasta que o 'chatbot.py'.")
    content_data = {}

def start_new_conversation(sender_phone_number):
    """Inicia uma nova conversa e cria um lead."""
    response_message = "Olá! 👋 Bem-vindo ao Da Hora Games! Para começar, por favor, informe seu nome. 🎮"
    lead_data = {
        'timestamp': datetime.now().isoformat(),
        'nome': 'Não informado',
        'email': 'Não informado',
        'telefone': sender_phone_number,
        'endereco': 'Não informado',
        'modelo': 'Não informado',
        'ano': 0,
        'tipo_de_armazenamento': 'Não informado',
        'jogos_selecionados': 'Não informado',
        'status': 'AGUARDANDO_NOME'
    }
    save_lead_to_db(lead_data)
    return response_message

def handle_awaiting_name(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando o nome do usuário."""
    if not re.match(r'^[a-zA-Z\s]+$', incoming_msg):
        return "Nome inválido. Por favor, digite seu nome usando apenas letras e espaços. ✍️"
    else:
        nome = incoming_msg.capitalize()
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_EMAIL', {'nome': nome})
        return f"Certo, {nome}! Agora, por favor, me informe seu email: [9 - Sair]"

def handle_awaiting_email(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando o email do usuário."""
    if not re.match(r'[^@]+@[^@]+\.[^@]+', incoming_msg):
        return "Email inválido. Por favor, digite um email no formato correto (ex: seu.nome@dominio.com). 📧"
    else:
        lead_info = get_lead_info(sender_phone_number)
        if lead_info:
            nome = lead_info.get('nome', 'amigo')
            update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ENDERECO', {'email': incoming_msg})
            return f"Obrigado, {nome}! Qual é o seu endereço completo? 🏡 [9 - Sair]"
        else:
            update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
            return "Desculpe, não consegui encontrar seus dados. Por favor, reinicie a conversa digitando 'oi'."

def handle_awaiting_address(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando o endereço do usuário."""
    response_message = "Obrigado! Qual é o modelo do seu Xbox? Por favor, digite o número da opção:\n"
    for num, modelo in content_data.get("modelos_xbox", {}).items():
        response_message += f"{num} - {modelo}\n"
    response_message += "\n[9 - Sair]"
    update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_MODELO', {'endereco': incoming_msg.capitalize()})
    return response_message

def handle_awaiting_model(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando o modelo do Xbox."""
    modelos_mapeamento = content_data.get("modelos_xbox", {})
    if incoming_msg in modelos_mapeamento:
        modelo_selecionado = modelos_mapeamento[incoming_msg]
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ANO', {'modelo': modelo_selecionado})
        return f"Entendido. Qual o ano de fabricação do seu console? (Ex: 2008, 2012). [9 - Sair]"
    else:
        return "Por favor, digite um dos números válidos: 1, 2 ou 3."

def handle_awaiting_year(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando o ano de fabricação."""
    try:
        ano = int(incoming_msg)
        response_message = ""
        
        if not 2007 <= ano <= 2015:
            return "Por favor, digite um ano entre 2007 e 2015. 🗓️"
        
        if ano == 2015:
            response_message += "Atenção: Consoles fabricados em 2015 não podem ser desbloqueados definitivamente! ⚠️"
        
        response_message += "\n\nO seu console tem Armazenamento?\n1- HD Interno\n2- HD Externo\n3- Pendrive 16gb+\n4- Não tenho\n\n[9 - Sair]"
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ARMAZENAMENTO', {'ano': ano})
        return response_message
    except ValueError:
        return "Por favor, digite apenas o ano de fabricação (Ex: 2010). 🔢"

def handle_awaiting_storage(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando o tipo de armazenamento."""
    jogos_options = ""
    for num, jogo in content_data.get("jogos", {}).items():
        jogos_options += f"{num}. {jogo}\n"

    if incoming_msg == '1':
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'HD Interno'})
        return f"Escolha 15 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
    elif incoming_msg == '2':
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'HD Externo'})
        return f"Escolha 15 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
    elif incoming_msg == '3':
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'Pendrive 16gb+'})
        return f"Escolha 15 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
    elif incoming_msg == '4':
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_CONTINUAR', {'tipo_de_armazenamento': 'Não tenho'})
        return "Atenção: Sem armazenamento, não será possível jogar nem copiar os jogos. Deseja continuar o atendimento?\n1 - Sim\n2 - Não\n\n[9 - Sair]"
    else:
        return "Opção inválida. Por favor, digite um número de 1 a 4. ❌"

def handle_awaiting_continue(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot pergunta se o usuário deseja continuar sem armazenamento."""
    if incoming_msg == '1':
        lead_info = get_lead_info(sender_phone_number)
        if lead_info and lead_info['tipo_de_armazenamento'] == 'Não tenho':
            update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_LOCALIZACAO', {'jogos_selecionados': 'Nenhum, pois não tem armazenamento'})
            return "Tudo certo! Você deseja receber o link da nossa localização? (1 - Sim / 2 - Não)\n\n[9 - Sair]"
    elif incoming_msg == '2':
        update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
        return "Entendido. Obrigado por usar nosso serviço! Seu atendimento foi registrado. Qualquer dúvida, pode nos contatar. 👍"
    else:
        return "Opção inválida. Por favor, digite '1' para continuar ou '2' para finalizar. ❌"

def handle_awaiting_games(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando a seleção de jogos."""
    jogos_mapeamento = content_data.get("jogos", {})
    jogos_escolhidos_numeros = [j.strip() for j in incoming_msg.split(',')]
    
    jogos_selecionados = []
    jogos_invalidos = False
    for numero in jogos_escolhidos_numeros:
        if numero in jogos_mapeamento:
            jogos_selecionados.append(jogos_mapeamento[numero])
        else:
            jogos_invalidos = True
            break
    
    if len(jogos_escolhidos_numeros) > 15 or len(jogos_escolhidos_numeros) < 1 or jogos_invalidos:
        return "Seleção inválida. Por favor, escolha entre 1 e 15 jogos da lista e separe-os por vírgula."
    else:
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_LOCALIZACAO', {'jogos_selecionados': ', '.join(jogos_selecionados)})
        return "Tudo certo! ✅ Você deseja receber o link da nossa localização? (1 - Sim / 2 - Não)\n\n[9 - Sair]"

def handle_awaiting_location(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando a decisão sobre a localização."""
    lead_data = get_lead_info(sender_phone_number)
    
    final_message = ""
    if incoming_msg == '1':
        final_message = "Obrigado! Aqui está o link da nossa localização: https://maps.app.goo.gl/G4HYUhf9JqWPkJoT7\n"
        update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
    elif incoming_msg == '2':
        final_message = "Entendido. Obrigado por usar nosso serviço! Seu atendimento foi registrado. 👋\n"
        update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
    else:
        return "Opção inválida. Por favor, digite '1' para Sim ou '2' para Não. ❌"

    if lead_data:
        jogos_lista_formatada = ""
        jogos_selecionados = lead_data.get('jogos_selecionados')
        if jogos_selecionados == 'Nenhum, pois não tem armazenamento':
            jogos_lista_formatada = jogos_selecionados
        elif jogos_selecionados:
            jogos = jogos_selecionados.split(', ')
            for jogo in jogos:
                jogos_lista_formatada += f"• {jogo}\n"

        summary = (
            f"\n--- Resumo do seu Atendimento ---\n"
            f"ID: {lead_data.get('id')}\n"
            f"Nome: {lead_data.get('nome')}\n"
            f"Email: {lead_data.get('email')}\n"
            f"Endereço: {lead_data.get('endereco')}\n"
            f"Modelo do Xbox: {lead_data.get('modelo')}\n"
            f"Ano de Fabricação: {lead_data.get('ano')}\n"
            f"Armazenamento: {lead_data.get('tipo_de_armazenamento')}\n"
            f"Jogos Selecionados:\n{jogos_lista_formatada}\n"
            f"--- Fim do Resumo ---"
        )
        final_message += summary
    
    return final_message

# O "roteador" principal da conversa
def whatsapp_webhook():
    try:
        incoming_msg = request.values.get('Body', '').lower().strip()
        sender_phone_number = request.values.get('From', '')

        print(f"\n--- Nova Mensagem ---")
        print(f"Origem: {sender_phone_number}")
        print(f"Mensagem recebida: {incoming_msg}")

        resp = MessagingResponse()
        current_status = get_lead_status(sender_phone_number)
        response_message = ""

        if incoming_msg == '9':
            update_lead_status_and_data(sender_phone_number, 'FINALIZADO', {})
            response_message = "Atendimento finalizado. Para começar um novo, digite 'oi'."
        
        elif incoming_msg == 'oi':
            response_message = start_new_conversation(sender_phone_number)
        
        elif current_status == 'AGUARDANDO_NOME':
            response_message = handle_awaiting_name(incoming_msg, sender_phone_number)
        
        elif current_status == 'AGUARDANDO_EMAIL':
            response_message = handle_awaiting_email(incoming_msg, sender_phone_number)
        
        elif current_status == 'AGUARDANDO_ENDERECO':
            response_message = handle_awaiting_address(incoming_msg, sender_phone_number)
            
        elif current_status == 'AGUARDANDO_MODELO':
            response_message = handle_awaiting_model(incoming_msg, sender_phone_number)
        
        elif current_status == 'AGUARDANDO_ANO':
            response_message = handle_awaiting_year(incoming_msg, sender_phone_number)
            
        elif current_status == 'AGUARDANDO_ARMAZENAMENTO':
            response_message = handle_awaiting_storage(incoming_msg, sender_phone_number)
        
        elif current_status == 'AGUARDANDO_CONTINUAR':
            response_message = handle_awaiting_continue(incoming_msg, sender_phone_number)
            
        elif current_status == 'AGUARDANDO_JOGOS':
            response_message = handle_awaiting_games(incoming_msg, sender_phone_number)
        
        elif current_status == 'AGUARDANDO_LOCALIZACAO':
            response_message = handle_awaiting_location(incoming_msg, sender_phone_number)

        else:
            response_message = "Desculpe, não entendi. Por favor, digite 'oi' para começar."
        
        resp.message(response_message)
        print(f"Resposta gerada: {response_message}\n")
        return str(resp)

    except Exception as e:
        print(f"Ocorreu um erro no webhook: {e}")
        return "Erro interno. Por favor, tente novamente mais tarde."