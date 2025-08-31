import dash
from flask import request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
from database import get_lead_status, update_lead_status_and_data, get_lead_info, save_lead_to_db
import json
import re
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
import os
import joblib

# Carrega o conteúdo dinâmico do arquivo JSON
try:
    with open('content.json', 'r', encoding='utf-8') as f:
        content_data = json.load(f)
except FileNotFoundError:
    print("Erro: O arquivo 'content.json' não foi encontrado. Certifique-se de que ele está na mesma pasta que o 'chatbot.py'.")
    content_data = {}

# --- IA - Treinamento e Predição de Intenções ---

# Defina as intenções e as frases de exemplo
INTENT_DATA = [
    ("oi", "saudacao"),
    ("ola", "saudacao"),
    ("bom dia", "saudacao"),
    ("boa tarde", "saudacao"),
    ("fala ai", "saudacao"),
    ("oi tudo bem", "saudacao"),
    ("tudo bem", "saudacao"),
    
    ("quero finalizar", "finalizar_conversa"),
    ("nao quero mais", "finalizar_conversa"),
    ("9", "finalizar_conversa"),
    ("finalizar", "finalizar_conversa"),
    ("sair", "finalizar_conversa"),
    ("tchau", "finalizar_conversa"),
    ("finalizado", "finalizar_conversa"),
    ("digite 9", "finalizar_conversa"),
    ("acabou", "finalizar_conversa"),
    ("vou sair", "finalizar_conversa"),

    ("preciso de ajuda", "comando_ajuda"),
    ("ajuda", "comando_ajuda"),
    ("o que eu faco agora", "comando_ajuda"),
    ("socorro", "comando_ajuda"),
    
    ("voltar", "comando_voltar"),
    ("volta", "comando_voltar"),
    ("quero voltar", "comando_voltar"),
    ("volta uma etapa", "comando_voltar"),
    ("passo anterior", "comando_voltar"),
    ("voltar uma", "comando_voltar"),
    
    ("meu nome eh joao", "informar_nome"),
    ("joao", "informar_nome"),
    ("sou o joao", "informar_nome"),
    ("me chamo joao", "informar_nome"),
    ("meu nome é André", "informar_nome"),
    ("me chamo Ana", "informar_nome"),
    ("Maria", "informar_nome"),
    ("Luiz Carlos", "informar_nome"),
    ("Pedro", "informar_nome"),
    ("Ana", "informar_nome"),
    ("elton", "informar_nome"),
    ("sou elton", "informar_nome"),
    ("jackson", "informar_nome"),
    ("sou jackson", "informar_nome"),

    ("meu email eh joao@teste.com", "informar_email"),
    ("joao@teste.com", "informar_email"),
    ("joao.teste@gmail.com", "informar_email"),
    ("o email é contato@dahoragames.com", "informar_email"),
    ("sou o email joao@hotmail.com", "informar_email"),

    ("meu endereco eh rua a, 123", "informar_endereco"),
    ("rua a, 123", "informar_endereco"),
    ("av b, 456", "informar_endereco"),
    ("moro na rua c, 789", "informar_endereco"),
    ("meu endereço é Rua do Comércio, 100", "informar_endereco"),
    
    ("meu xbox eh fat", "informar_modelo"),
    ("slim", "informar_modelo"),
    ("super slim", "informar_modelo"),
    ("xbox 360 slim", "informar_modelo"),
    ("modelo fat", "informar_modelo"),

    ("ano 2010", "informar_ano"),
    ("fabricado em 2012", "informar_ano"),
    ("2010", "informar_ano"),
    ("2012", "informar_ano"),
    ("o ano de fabricacao e 2007", "informar_ano"),
    ("2013", "informar_ano"),
    ("o ano e 2008", "informar_ano"),
    ("é de 2011", "informar_ano"),
    ("e de 2014", "informar_ano"),
    ("ano e 2015", "informar_ano"),
    ("é 2010", "informar_ano"),
    ("o meu e 2009", "informar_ano"),
    ("meu console é de 2012", "informar_ano"),
    ("fabricado em 2013", "informar_ano"),

    ("tenho hd interno", "informar_armazenamento"),
    ("hd externo", "informar_armazenamento"),
    ("pendrive", "informar_armazenamento"),
    ("nao tenho armazenamento", "informar_armazenamento"),
    ("armazenamento hd interno", "informar_armazenamento"),
    ("uso um pen drive", "informar_armazenamento"),
    
    ("1, 2, 3", "selecao_jogos"),
    ("1, 2, 25", "selecao_jogos"),
    ("quero o jogo 1", "selecao_jogos"),
    ("gta v e fifa", "selecao_jogos"),
    ("selecionar os jogos", "selecao_jogos"),
    ("escolho os jogos 1, 14, 20", "selecao_jogos"),
    ("os numeros sao 5,10,15", "selecao_jogos"),
    ("3, 7, 11, 22", "selecao_jogos"),
    ("1, 5", "selecao_jogos"),
    ("2, 8, 14", "selecao_jogos"),
    ("3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25", "selecao_jogos"),
    ("1,3,5,7", "selecao_jogos"),
    ("2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24", "selecao_jogos"),

    ("sim", "confirmar_localizacao"),
    ("nao", "confirmar_localizacao"),
    ("não", "confirmar_localizacao"),
    ("quero o link", "confirmar_localizacao"),
    ("sim quero", "confirmar_localizacao"),
    ("nao, obrigado", "confirmar_localizacao"),
    ("não, obrigado", "confirmar_localizacao")

]

# Treina o modelo de intenção
def train_intent_model():
    model_path = 'intent_model.joblib'
    vectorizer_path = 'vectorizer.joblib'

    if os.path.exists(model_path) and os.path.exists(vectorizer_path):
        return joblib.load(model_path), joblib.load(vectorizer_path)

    corpus = [item[0] for item in INTENT_DATA]
    labels = [item[1] for item in INTENT_DATA]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
    X = vectorizer.fit_transform(corpus)
    y = labels

    model = LinearSVC(max_iter=5000)
    model.fit(X, y)

    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vectorizer_path)

    return model, vectorizer

# Carrega o modelo de intenção
intent_model, intent_vectorizer = train_intent_model()

# Função para prever a intenção de uma nova mensagem
def get_intent(message):
    message_vector = intent_vectorizer.transform([message.lower()])
    prediction = intent_model.predict(message_vector)
    return prediction[0]

# --- Funções de Manuseio da Conversa ---

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
    # Extrai a última palavra da mensagem como o nome
    partes_da_frase = incoming_msg.split()
    nome_candidato = partes_da_frase[-1]
    
    if not re.match(r'^[a-zA-Z\u00C0-\u017F\s-]+$', nome_candidato):
        return "Nome inválido. Por favor, digite seu nome usando apenas letras, espaços e hífens. ✍️"
    else:
        nome = nome_candidato.title()
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
    
    # Mapeamento reverso para traduzir o nome do modelo para o número
    modelos_reverso = {v.lower(): k for k, v in modelos_mapeamento.items()}
    
    modelo_selecionado = None
    
    # 1. Tenta encontrar a opção por número
    if incoming_msg in modelos_mapeamento:
        modelo_selecionado = modelos_mapeamento[incoming_msg]
        
    # 2. Tenta encontrar a opção por nome (usando a IA)
    elif get_intent(incoming_msg) == 'informar_modelo':
        # Tenta encontrar o nome do modelo no mapeamento reverso
        for modelo_nome, modelo_numero in modelos_reverso.items():
            if modelo_nome in incoming_msg:
                modelo_selecionado = modelos_mapeamento[modelo_numero]
                break

    if modelo_selecionado:
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ANO', {'modelo': modelo_selecionado})
        return f"Entendido. Qual o ano de fabricação do seu console? (Ex: 2008, 2012). [9 - Sair]"
    else:
        return "Por favor, digite um dos números válidos: 1, 2 ou 3."

def handle_awaiting_year(incoming_msg, sender_phone_number):
    """Trata a mensagem quando o chatbot está aguardando o ano de fabricação."""
    try:
        # Usa uma expressão regular para encontrar um número de 4 dígitos na mensagem
        match = re.search(r'\b(19|20)\d{2}\b', incoming_msg)
        
        if not match:
            return "Por favor, digite apenas o ano de fabricação (Ex: 2010). 🔢"
        
        ano = int(match.group(0))
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

    # Dicionário de mapeamento para traduzir frases para números
    armazenamento_mapeamento = {
        'hd interno': '1',
        'hd externo': '2',
        'pendrive': '3',
        'não tenho': '4'
    }

    # Verifica se a mensagem é um número válido
    if incoming_msg in ['1', '2', '3', '4']:
        escolha = incoming_msg
    # Se não for número, tenta encontrar a opção na frase
    else:
        encontrado = False
        for termo, numero in armazenamento_mapeamento.items():
            if termo in incoming_msg:
                escolha = numero
                encontrado = True
                break
        if not encontrado:
            return "Opção inválida. Por favor, digite um número de 1 a 4. ❌"

    # Lógica de resposta com base na escolha
    if escolha == '1':
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'HD Interno'})
        return f"Escolha 15 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
    elif escolha == '2':
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'HD Externo'})
        return f"Escolha 15 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
    elif escolha == '3':
        update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'Pendrive 16gb+'})
        return f"Escolha 15 jogos da lista abaixo, separados por vírgula:\n{jogos_options}\n[9 - Sair]"
    elif escolha == '4':
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
    
    # Adiciona a lógica para verificar 'sim' ou 'nao'
    if 'sim' in incoming_msg or '1' in incoming_msg:
        final_message = "Obrigado! Aqui está o link da nossa localização: https://maps.app.goo.gl/G4HYUhf9JqWPkJoT7\n"
        update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
    elif 'não' in incoming_msg or '2' in incoming_msg:
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
        
        # Prevemos a intenção da mensagem para lidar com comandos especiais
        intent = get_intent(incoming_msg)
        print(f"Intenção detectada: {intent}")

        # --- Lógica de prioridade por comandos especiais (mais confiável) ---
        
        # 1. Checa por comandos de finalização de conversa primeiro
        if intent == 'finalizar_conversa' or (incoming_msg == '9' and current_status != 'FINALIZADO'):
            update_lead_status_and_data(sender_phone_number, 'FINALIZADO', {})
            response_message = "Atendimento finalizado. Para começar um novo, digite 'oi'."

        # 2. Checa por comandos de saudação (para iniciar ou reiniciar a conversa)
        elif intent == 'saudacao':
            response_message = start_new_conversation(sender_phone_number)

        # 3. Lógica para comandos de controle (independente do status)
        elif intent == 'comando_voltar':
            if current_status == 'AGUARDANDO_EMAIL':
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_NOME')
                response_message = "Voltando... Qual é o seu nome?"
            elif current_status == 'AGUARDANDO_ENDERECO':
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_EMAIL')
                response_message = "Voltando... Por favor, digite seu email:"
            elif current_status == 'AGUARDANDO_MODELO':
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ENDERECO')
                response_message = "Voltando... Qual é o seu endereço completo?"
            elif current_status == 'AGUARDANDO_ANO':
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_MODELO')
                response_message = "Voltando... Qual é o modelo do seu Xbox? (1 - Fat, 2 - Slim, 3 - Super Slim)"
            elif current_status == 'AGUARDANDO_ARMAZENAMENTO':
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ANO')
                response_message = "Voltando... Qual o ano de fabricação do seu console?"
            elif current_status == 'AGUARDANDO_JOGOS' or current_status == 'AGUARDANDO_CONTINUAR':
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ARMAZENAMENTO')
                response_message = "Voltando... O seu console tem Armazenamento? (1- HD Interno, 2- HD Externo, etc.)"
            elif current_status == 'AGUARDANDO_LOCALIZACAO':
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS')
                jogos_options = ""
                for num, jogo in content_data.get("jogos", {}).items():
                    jogos_options += f"{num}. {jogo}\n"
                response_message = f"Voltando... Escolha 15 jogos da lista abaixo:\n{jogos_options}"
            else:
                response_message = "Você está no início da conversa ou o atendimento foi finalizado. Não é possível voltar."

        elif intent == 'comando_ajuda':
            if current_status == 'AGUARDANDO_NOME':
                response_message = "Por favor, digite seu nome. É a primeira informação que precisamos para começar o atendimento."
            elif current_status == 'AGUARDANDO_EMAIL':
                response_message = "Estamos esperando seu email. Ele é importante para enviarmos o resumo do atendimento."
            elif current_status == 'AGUARDANDO_ENDERECO':
                response_message = "Por favor, digite seu endereço completo para que possamos calcular o frete e tempo de serviço."
            elif current_status == 'AGUARDANDO_MODELO':
                response_message = "Precisamos saber o modelo do seu Xbox. Digite o número correspondente à sua opção (1, 2 ou 3)."
            elif current_status == 'AGUARDANDO_ANO':
                response_message = "Por favor, digite o ano de fabricação do seu console. Fica na parte de trás do aparelho."
            elif current_status == 'AGUARDANDO_ARMAZENAMENTO':
                response_message = "Estamos na etapa de armazenamento. Por favor, digite o número que melhor descreve o seu caso (1 a 4)."
            elif current_status == 'AGUARDANDO_JOGOS':
                response_message = "Por favor, digite o número de até 15 jogos que deseja, separados por vírgula. Exemplo: 1,5,10"
            elif current_status == 'AGUARDANDO_CONTINUAR':
                response_message = "Para continuar o atendimento mesmo sem armazenamento, digite '1'. Caso contrário, digite '2'."
            elif current_status == 'AGUARDANDO_LOCALIZACAO':
                response_message = "Estamos na última etapa. Para receber o link da nossa localização, digite '1'."
            else:
                response_message = "Para começar um novo atendimento, digite 'oi'. Se precisar de ajuda, digite 'ajuda'."
        
        # 4. Se não for um comando especial, lida com o fluxo de conversa normal
        else:
            if current_status is None or current_status == 'FINALIZADO':
                response_message = "Parece que a nossa conversa foi finalizada. Para começar um novo atendimento, digite 'oi'. 👋"
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