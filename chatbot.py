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

def whatsapp_webhook():
    try:
        incoming_msg = request.values.get('Body', '').lower().strip()
        sender_phone_number = request.values.get('From', '')

        print(f"\n--- Nova Mensagem ---")
        print(f"Origem: {sender_phone_number}")
        print(f"Mensagem recebida: {incoming_msg}")

        resp = MessagingResponse()
        current_status = get_lead_status(sender_phone_number)
        
        if current_status == 'FINALIZADO':
            response_message = "Parece que a nossa conversa foi finalizada. Para começar um novo atendimento, digite 'oi'."
            
            if incoming_msg == 'oi':
                response_message = "Olá! Bem-vindo ao Xbox Repair. Para começar, por favor, informe seu nome."
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
        
        elif incoming_msg == '9':
            response_message = "O atendimento foi cancelado. Obrigado por entrar em contato! Você pode começar um novo atendimento a qualquer momento digitando 'oi'."
            update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
            
        elif current_status == 'AGUARDANDO_NOME':
            # Nova validação para o nome
            if not re.match(r'^[a-zA-Z\s]+$', incoming_msg):
                response_message = "Nome inválido. Por favor, digite seu nome usando apenas letras e espaços."
            else:
                nome = incoming_msg.capitalize()
                response_message = f"Certo, {nome}! Agora, por favor, me informe seu email. [9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_EMAIL', {'nome': nome})
            
        elif current_status == 'AGUARDANDO_EMAIL':
            # Nova validação para o email
            if not re.match(r'[^@]+@[^@]+\.[^@]+', incoming_msg):
                response_message = "Email inválido. Por favor, digite um email no formato correto (ex: seu.nome@dominio.com)."
            else:
                lead_info = get_lead_info(sender_phone_number)
                if lead_info is not None:
                    nome = lead_info['nome']
                    response_message = f"Obrigado, {nome}! Qual é o seu endereço completo? [9 - Sair]"
                    update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ENDERECO', {'email': incoming_msg})
                else:
                    response_message = "Desculpe, não consegui encontrar seu nome. Por favor, reinicie a conversa digitando 'oi'."
                    update_lead_status_and_data(sender_phone_number, 'FINALIZADO')

        elif current_status == 'AGUARDANDO_ENDERECO':
            response_message = "Obrigado! Qual é o modelo do seu Xbox? Por favor, digite o número da opção:\n"
            for num, modelo in content_data.get("modelos_xbox", {}).items():
                response_message += f"{num} - {modelo}\n"
            response_message += "\n[9 - Sair]"
            update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_MODELO', {'endereco': incoming_msg.capitalize()})
            
        elif current_status == 'AGUARDANDO_MODELO':
            modelos_mapeamento = content_data.get("modelos_xbox", {})
            if incoming_msg in modelos_mapeamento:
                modelo_selecionado = modelos_mapeamento[incoming_msg]
                response_message = f"Entendido. Qual o ano de fabricação do seu console? (Ex: 2008, 2012). [9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ANO', {'modelo': modelo_selecionado})
            else:
                response_message = "Por favor, digite um dos números válidos: 1, 2 ou 3."

        elif current_status == 'AGUARDANDO_ANO':
            try:
                ano = int(incoming_msg)
                response_message = ""
                
                if not 2007 <= ano <= 2015:
                    response_message = "Por favor, digite um ano entre 2007 e 2015."
                elif ano == 2015:
                    response_message = "Atenção: Consoles fabricados em 2015 não podem ser desbloqueados definitivamente."
                    
                if 2007 <= ano <= 2015:
                    response_message += "\n\nO seu console tem armazenamento?\n1- HD Interno\n2- HD Externo\n3- Pendrive 16gb+\n4- Não tenho\n\n[9 - Sair]"
                    update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ARMAZENAMENTO', {'ano': ano})
                else:
                    pass
            except ValueError:
                response_message = "Por favor, digite apenas o ano de fabricação (Ex: 2010)."
                
        elif current_status == 'AGUARDANDO_ARMAZENAMENTO':
            jogos_options = ""
            for num, jogo in content_data.get("jogos", {}).items():
                jogos_options += f"{num}. {jogo}\n"

            if incoming_msg == '1':
                response_message = f"Escolha 3 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'HD Interno'})
            elif incoming_msg == '2':
                response_message = f"Escolha 3 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'HD Externo'})
            elif incoming_msg == '3':
                response_message = f"Escolha 3 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'Pendrive 16gb+'})
            elif incoming_msg == '4':
                response_message = "Atenção: Sem armazenamento, não será possível jogar nem copiar os jogos. Deseja continuar o atendimento?\n1 - Sim\n2 - Não\n\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_CONTINUAR', {'tipo_de_armazenamento': 'Não tenho'})
            else:
                response_message = "Opção inválida. Por favor, digite um número de 1 a 4."
        
        elif current_status == 'AGUARDANDO_CONTINUAR':
            lead_info = get_lead_info(sender_phone_number)
            if incoming_msg == '1':
                if lead_info is not None and lead_info['tipo_de_armazenamento'] == 'Não tenho':
                    response_message = "Tudo certo! Você deseja receber o link da nossa localização? (1 - Sim / 2 - Não)\n\n[9 - Sair]"
                    update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_LOCALIZACAO', {'jogos_selecionados': 'Nenhum, pois não tem armazenamento'})
                else:
                    jogos_options = ""
                    for num, jogo in content_data.get("jogos", {}).items():
                        jogos_options += f"{num}. {jogo}\n"
                    response_message = f"Tudo bem, vamos prosseguir. Escolha 3 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
                    update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS')
            elif incoming_msg == '2':
                response_message = "Entendido. Obrigado por usar nosso serviço! Seu atendimento foi registrado. Qualquer dúvida, pode nos contatar."
                update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
            else:
                response_message = "Opção inválida. Por favor, digite '1' para continuar ou '2' para finalizar."

        elif current_status == 'AGUARDANDO_JOGOS':
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
            
            if len(jogos_escolhidos_numeros) != 3 or jogos_invalidos:
                response_message = "Seleção inválida. Por favor, escolha 3 jogos da lista e separe-os por vírgula."
            else:
                response_message = "Tudo certo! Você deseja receber o link da nossa localização? (1 - Sim / 2 - Não)\n\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_LOCALIZACAO', {'jogos_selecionados': ', '.join(jogos_selecionados)})

        elif current_status == 'AGUARDANDO_LOCALIZACAO':
            lead_data = get_lead_info(sender_phone_number)
            
            final_message = ""
            if incoming_msg == '1':
                final_message = "Obrigado! Aqui está o link da nossa localização: [Link da Localização](https://maps.app.goo.gl/9TqC6k5Q5pYqD4gA8)\n"
                update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
            elif incoming_msg == '2':
                final_message = "Entendido. Obrigado por usar nosso serviço! Seu atendimento foi registrado.\n"
                update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
            else:
                response_message = "Opção inválida. Por favor, digite '1' para Sim ou '2' para Não."
                resp.message(response_message)
                print(f"Resposta gerada: {response_message}\n")
                return str(resp)
            
            if lead_data is not None:
                summary = (
                    f"--- Resumo do seu Atendimento ---\n"
                    f"ID: {lead_data.get('id')}\n"
                    f"Nome: {lead_data['nome']}\n"
                    f"Email: {lead_data['email']}\n"
                    f"Endereço: {lead_data['endereco']}\n"
                    f"Modelo do Xbox: {lead_data['modelo']}\n"
                    f"Ano de Fabricação: {lead_data['ano']}\n"
                    f"Armazenamento: {lead_data['tipo_de_armazenamento']}\n"
                    f"Jogos Selecionados: {lead_data['jogos_selecionados']}\n"
                    f"--- Fim do Resumo ---"
                )
                final_message += summary
            
            response_message = final_message
        
        else:
            response_message = "Olá! Bem-vindo ao Xbox Repair. Para começar, por favor, informe seu nome. [9 - Sair]"
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

        resp.message(response_message)
        print(f"Resposta gerada: {response_message}\n")

        return str(resp)

    except Exception as e:
        print(f"Erro ao processar a mensagem do Twilio: {e}")
        return "Erro interno no servidor", 200