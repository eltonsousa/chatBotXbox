import dash
from flask import request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
from database import get_lead_status, save_or_update_lead, get_lead_info
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

# --- CONSTANTES ---
# Definindo as strings de status como constantes para melhor legibilidade e manutenção.
class Status:
    INICIADO = 'INICIADO'
    AGUARDANDO_NOME = 'AGUARDANDO_NOME'
    AGUARDANDO_EMAIL = 'AGUARDANDO_EMAIL'
    AGUARDANDO_ENDERECO = 'AGUARDANDO_ENDERECO'
    AGUARDANDO_MODELO = 'AGUARDANDO_MODELO'
    AGUARDANDO_ANO = 'AGUARDANDO_ANO'
    AGUARDANDO_ARMAZENAMENTO = 'AGUARDANDO_ARMAZENAMENTO'
    AGUARDANDO_JOGOS = 'AGUARDANDO_JOGOS'
    AGUARDANDO_LOCALIZACAO_OU_FINALIZAR = 'AGUARDANDO_LOCALIZACAO_OU_FINALIZAR'
    AGUARDANDO_CONTINUAR_OU_ENCERRAR = 'AGUARDANDO_CONTINUAR_OU_ENCERRAR'
    AGUARDANDO_DESBLOQUEIO_SEM_JOGOS = 'AGUARDANDO_DESBLOQUEIO_SEM_JOGOS'
    FINALIZADO = 'FINALIZADO'
    # Novo status para tratar o retorno do usuário
    AGUARDANDO_OPCAO_RETORNO = 'AGUARDANDO_OPCAO_RETORNO'

# --- IA - Treinamento e Predição de Intenções ---

# Defina as intenções e as frases de exemplo
# Frases de finalização foram removidas para evitar conflito com dados de entrada.
INTENT_DATA = [
    ("oi", "saudacao"),
    ("ola", "saudacao"),
    ("bom dia", "saudacao"),
    ("boa tarde", "saudacao"),
    ("fala ai", "saudacao"),
    ("oi tudo bem", "saudacao"),
    ("tudo bem", "saudacao"),
    
    ("quero ajuda", "comando_ajuda"),
    ("ajuda", "comando_ajuda"),
    
    ("voltar", "comando_voltar"),
    ("quero voltar", "comando_voltar"),
    
    ("meu nome eh", "informar_nome"),
    ("meu nome é", "informar_nome"),
    ("me chamo", "informar_nome"),
    ("é", "informar_nome"),
    ("eh", "informar_nome"),
    
    ("email", "informar_email"),
    ("meu email eh", "informar_email"),
    ("meu email e", "informar_email"),

    ("endereco", "informar_endereco"),
    ("rua", "informar_endereco"),
    ("meu endereco eh", "informar_endereco"),

    ("xbox", "informar_modelo"),
    ("fat", "informar_modelo"),
    ("slim", "informar_modelo"),
    ("super slim", "informar_modelo"),
    
    ("ano", "informar_ano"),
    ("2010", "informar_ano"),
    ("2007", "informar_ano"),

    ("hd", "informar_armazenamento"),
    ("armazenamento", "informar_armazenamento"),
    
    ("queria jogos", "informar_jogos"),
    ("jogos", "informar_jogos"),
    ("jogos", "informar_jogos"),
]

# Treinamento do modelo
corpus = [item[0].lower() for item in INTENT_DATA]
labels = [item[1] for item in INTENT_DATA]

vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b', min_df=1, ngram_range=(1, 3))
X = vectorizer.fit_transform(corpus)

model = LinearSVC()
model.fit(X, labels)

# Salva o modelo e o vetorizador
joblib.dump(model, 'intent_model.joblib')
joblib.dump(vectorizer, 'vectorizer.joblib')

# Carrega o modelo treinado (para uso em produção)
try:
    vectorizer = joblib.load('vectorizer.joblib')
    model = joblib.load('intent_model.joblib')
except FileNotFoundError:
    print("Aviso: Modelos de IA não encontrados. O chatbot usará a lógica base.")
    vectorizer = None
    model = None

def get_intent(text):
    """
    Prediz a intenção da mensagem do usuário usando o modelo treinado.
    Retorna 'nao_entendi' se o modelo não estiver carregado ou não conseguir classificar.
    """
    if vectorizer and model:
        text_vectorized = vectorizer.transform([text.lower()])
        return model.predict(text_vectorized)[0]
    return 'nao_entendi'

# --- FLUXO DE CONVERSA ---

def get_menu_message():
    """Gera a mensagem do menu principal."""
    menu_message = content_data.get('menu', "Menu não encontrado.")
    return menu_message

def get_modelos_message():
    """Gera a mensagem para a seleção do modelo."""
    modelos_text = content_data.get('texto_modelos', "Modelos não encontrados.")
    modelos_lista = content_data.get('modelos_xbox', {})
    
    modelos_string = "\n".join([f"  {num} - {nome}" for num, nome in modelos_lista.items()])
    return f"{modelos_text}\n\n{modelos_string}\n\nResponda com o número do modelo."

def get_armazenamento_message():
    """Gera a mensagem para a seleção do armazenamento."""
    armazenamento_text = content_data.get('perguntas', {}).get('pergunta_armazenamento', 'Qual o tipo de armazenamento do seu console?')
    opcoes_lista = content_data.get('opcoes_armazenamento', {})
    
    opcoes_string = "\n".join([f"  {num} - {nome}" for num, nome in opcoes_lista.items()])
    return f"{armazenamento_text}\n\n{opcoes_string}\n\nResponda com o número do tipo de armazenamento."

def get_jogos_message():
    """Gera a mensagem para a seleção de jogos."""
    jogos_text = content_data.get('texto_jogos', "Jogos não encontrados.")
    jogos_lista = content_data.get('jogos', {})
    
    jogos_string = "\n".join([f"  {num} - {nome}" for num, nome in jogos_lista.items()])
    return f"{jogos_text}\n\n{jogos_string}\n\nVocê pode selecionar mais de um jogo, separando por vírgula. Ex: 1, 5, 8"

def handle_awaiting_name(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_NOME.
    Salva o nome e muda o status para AGUARDANDO_EMAIL.
    """
    nome = incoming_msg.strip()
    save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_EMAIL, 'nome': nome})
    return f"Obrigado, {nome}! Qual é o seu email?"

def handle_awaiting_email(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_EMAIL.
    Valida o email, salva e muda o status.
    """
    email_regex = r'^\S+@\S+\.\S+$'
    if re.match(email_regex, incoming_msg.strip()):
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_ENDERECO, 'email': incoming_msg.strip()})
        return content_data.get('perguntas', {}).get('pergunta_endereco', 'Qual é o seu endereço?')
    else:
        return content_data.get('erros', {}).get('erro_email', 'Email inválido. Por favor, digite um email válido.')

def handle_awaiting_address(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_ENDERECO.
    Salva o endereço e muda o status.
    """
    endereco = incoming_msg.strip()
    save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_MODELO, 'endereco': endereco})
    return get_modelos_message()

def handle_awaiting_model(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_MODELO.
    Valida o modelo, salva e muda o status.
    """
    modelos_lista = content_data.get('modelos_xbox', {})
    if incoming_msg.strip() in modelos_lista:
        modelo = modelos_lista[incoming_msg.strip()]
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_ANO, 'modelo': modelo})
        return content_data.get('perguntas', {}).get('pergunta_ano', 'Qual o ano de fabricação do console? (Ex: 2010)')
    else:
        return content_data.get('erros', {}).get('erro_modelo', 'Modelo inválido. Por favor, selecione um modelo da lista.')

def handle_awaiting_year(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_ANO.
    Valida o ano, salva e muda o status.
    """
    try:
        ano = int(incoming_msg.strip())
        if ano == 2015:
            # Consoles de 2015 não permitem jogos, então a seleção de armazenamento é pulada.
            save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_CONTINUAR_OU_ENCERRAR, 'ano': ano})
            return content_data.get('perguntas', {}).get('pergunta_continuar_ou_encerrar', 'Atenção: Consoles fabricados em 2015 não permitem o desbloqueio definitivo. Deseja continuar com a solicitação ou encerrar? (Sim/Não)')
        elif 2007 <= ano <= 2015:
            save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_ARMAZENAMENTO, 'ano': ano})
            return get_armazenamento_message()
        else:
            return content_data.get('erros', {}).get('erro_ano', 'Ano inválido. Por favor, digite um ano entre 2007 e 2015.')
    except ValueError:
        return content_data.get('erros', {}).get('erro_ano', 'Ano inválido. Por favor, digite um ano entre 2007 e 2015.')

def handle_awaiting_storage(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_ARMAZENAMENTO.
    Valida a seleção de armazenamento, incluindo a nova opção '4 - Não tenho'.
    """
    opcoes_armazenamento = content_data.get('opcoes_armazenamento', {})
    
    if incoming_msg.strip() in ['1', '2', '3']:
        armazenamento = opcoes_armazenamento[incoming_msg.strip()]
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_JOGOS, 'tipo_de_armazenamento': armazenamento})
        return get_jogos_message()
    elif incoming_msg.strip() == '4' or incoming_msg.strip().lower() in ['nao tenho', 'não tenho', 'sem hd', 'sem armazenamento']:
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_DESBLOQUEIO_SEM_JOGOS, 'tipo_de_armazenamento': 'Não tenho'})
        return content_data.get('perguntas', {}).get('pergunta_desbloqueio_sem_jogos', 'Aviso: Não poderá rodar jogos no seu xbox sem armazenamento! Deseja continuar somente com o desbloqueio?\n1 - Sim\n2 - Não')
    else:
        return content_data.get('erros', {}).get('erro_armazenamento', 'Opção de armazenamento inválida. Por favor, selecione uma das opções de 1 a 4.')

def handle_awaiting_desbloqueio_sem_jogos(incoming_msg, sender_phone_number):
    """
    Trata a mensagem após o usuário indicar que não tem armazenamento.
    Adiciona mais variações para 'sim' e 'não'.
    """
    # Lista de opções válidas para "Sim"
    valid_sim = ['1', 'sim', 'Sim', 'yes', 'sin', 'simm', 'SIM', 'SIN']
    # Lista de opções válidas para "Não"
    valid_nao = ['2', 'nao', 'não', 'Não', 'nop', 'not', 'NAO', 'NÃO', 'não quero']
    
    incoming_msg_lower = incoming_msg.strip()
    
    if incoming_msg_lower in valid_sim:
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_LOCALIZACAO_OU_FINALIZAR})
        return content_data.get('perguntas', {}).get('pergunta_localizacao_ou_finalizar', 'Ótimo, seu pedido foi registrado! Deseja que eu envie a localização da loja para você? (Sim/Não)')
    elif incoming_msg_lower in valid_nao:
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.FINALIZADO})
        return content_data.get('respostas', {}).get('resposta_finalizada_encerrar', 'Entendido. Pedido encerrado. Em breve um de nossos consultores entrará em contato. Agradecemos o contato.')
    else:
        return content_data.get('erros', {}).get('erro_sim_nao', 'Resposta inválida. Por favor, digite "Sim" ou "Não".')

def handle_awaiting_continue_or_end(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_CONTINUAR_OU_ENCERRAR.
    Finaliza o pedido ou direciona para a seleção de jogos (no caso do ano 2015).
    """
    # Lista de opções válidas para "Sim"
    valid_sim = ['1', 'sim', 'Sim', 'yes', 'sin', 'simm', 'SIM', 'SIN']
    # Lista de opções válidas para "Não"
    valid_nao = ['2', 'nao', 'não', 'Não', 'nop', 'not', 'NAO', 'NÃO', 'não quero']
    
    incoming_msg_lower = incoming_msg.strip()
    if incoming_msg_lower in valid_sim:
        # Nova lógica: se continuar, vai para a seleção de armazenamento.
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_ARMAZENAMENTO})
        return get_armazenamento_message()
    elif incoming_msg_lower in valid_nao:
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.FINALIZADO})
        return content_data.get('respostas', {}).get('resposta_finalizada_encerrar', 'Entendido. Pedido encerrado. Em breve um de nossos consultores entrará em contato. Agradecemos o contato.')
    else:
        return content_data.get('erros', {}).get('erro_sim_nao', 'Resposta inválida. Por favor, digite "Sim" ou "Não".')

def handle_awaiting_games(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_JOGOS.
    Valida a seleção de jogos e pergunta se o cliente deseja a localização.
    """
    jogos_lista = content_data.get('jogos', {})
    jogos_escolhidos_numeros = [num.strip() for num in incoming_msg.split(',')]
    
    if len(jogos_escolhidos_numeros) > 15 or len(jogos_escolhidos_numeros) < 1:
        return content_data.get('erros', {}).get('erro_jogos', 'Seleção inválida. Por favor, selecione de 1 a 15 jogos.')
        
    jogos_selecionados_nomes = []
    
    for num_jogo in jogos_escolhidos_numeros:
        if num_jogo in jogos_lista:
            jogos_selecionados_nomes.append(jogos_lista[num_jogo])
        else:
            return content_data.get('erros', {}).get('erro_jogos_invalido', 'Opção de jogo inválida. Por favor, selecione apenas números da lista.')
    
    jogos_selecionados = ', '.join(jogos_selecionados_nomes)
    
    save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_LOCALIZACAO_OU_FINALIZAR, 'jogos_selecionados': jogos_selecionados})
    return content_data.get('perguntas', {}).get('pergunta_localizacao_ou_finalizar', 'Ótimo, seu pedido foi registrado! Deseja que eu envie a localização da loja para você? (Sim/Não)')

def handle_awaiting_location_or_finalize(incoming_msg, sender_phone_number):
    """
    Trata a mensagem quando o status é AGUARDANDO_LOCALIZACAO_OU_FINALIZAR.
    Finaliza o pedido, mostra um resumo e, opcionalmente, envia a localização.
    """
    lead_info = get_lead_info(sender_phone_number)
    name = lead_info.get('nome', 'amigo')

    valid_sim = ['sim', '1', 'yes', 'sin', 'simm', 'SIM', 'SIN']
    valid_nao = ['nao', 'não', 'Não', '2', 'nop', 'not', 'NAO', 'NÃO', 'não quero']
    
    incoming_msg_lower = incoming_msg.strip()
    save_or_update_lead({'telefone': sender_phone_number, 'status': Status.FINALIZADO})

    # Verifica se o cliente não tem armazenamento e ajusta a mensagem de jogos
    if lead_info.get('tipo_de_armazenamento') == 'Não tenho':
        jogos_resumo = 'Somente desbloqueio'
    else:
        jogos_resumo = lead_info.get('jogos_selecionados', 'Nenhum selecionado')

    # Nova lógica para determinar o tipo de serviço
    ano_console = lead_info.get('ano')
    tipo_armazenamento = lead_info.get('tipo_de_armazenamento')
    
    if ano_console == 2015:
        tipo_servico = "Somente Jogos"
    elif tipo_armazenamento == 'Não tenho':
        tipo_servico = "Somente Desbloqueio"
    else:
        tipo_servico = "Desbloqueio + Jogos"

    # Cria o resumo do pedido que será exibido em ambos os casos
    summary_message = f"**Olá, {name}! Resumo do seu pedido:**\n\n"
    summary_message += f"**Tipo de Serviço:** {tipo_servico}\n"
    summary_message += f"**Nome:** {lead_info.get('nome', 'N/A')}\n"
    summary_message += f"**Modelo:** {lead_info.get('modelo', 'N/A')}\n"
    summary_message += f"**Ano:** {lead_info.get('ano', 'N/A')}\n"
    summary_message += f"**Armazenamento:** {lead_info.get('tipo_de_armazenamento', 'N/A')}\n"
    summary_message += f"**Jogos:** {jogos_resumo}\n\n"

    # Agora, trata a resposta do usuário e adiciona a mensagem final apropriada
    if incoming_msg_lower in valid_sim:
        final_message = f"{summary_message}{content_data.get('respostas', {}).get('resposta_finalizada_com_localizacao', 'Seu pedido foi finalizado. Em breve um de nossos consultores entrará em contato. Agradecemos o contato.')} {content_data.get('localizacao_loja', 'Nossa loja está localizada em [INSERIR ENDEREÇO DA LOJA AQUI].')}"
        return final_message
    elif incoming_msg_lower in valid_nao:
        return f"{summary_message}{content_data.get('respostas', {}).get('resposta_finalizada', f'Entendido, {name}. Seu pedido foi finalizado. Em breve um de nossos consultores entrarão em contato para te ajudar. Agradecemos o contato.')}"
    else:
        return content_data.get('erros', {}).get('erro_sim_nao', 'Resposta inválida. Por favor, digite "Sim" ou "Não".')

def handle_awaiting_return_option(incoming_msg, sender_phone_number):
    """
    Trata a resposta do usuário após ele ser reconhecido como cliente existente.
    """
    incoming_msg_lower = incoming_msg.strip().lower()
    
    # Lista de opções para ver o resumo
    valid_resumo = ['2', 'resumo', 'ver resumo', 'ver o resumo', 'ver o anterior', 'anterior']
    # Lista de opções para fazer um novo pedido
    valid_novo = ['1', 'novo', 'novo pedido', 'novo orçamento', 'fazer novo']

    if incoming_msg_lower in valid_novo:
        # Se o usuário quer um novo pedido, reinicia o fluxo para a primeira etapa.
        # Reseta os dados para evitar que o resumo mostre informações do pedido anterior.
        save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_NOME, 'modelo': 'Não informado', 'ano': 0, 'tipo_de_armazenamento': 'Não informado', 'jogos_selecionados': 'Não informado'})
        return content_data.get('boas_vindas', 'Olá, tudo bem? Para começarmos, qual é o seu nome?')
    elif incoming_msg_lower in valid_resumo:
        # Se o usuário quer o resumo, chama a função de finalização que já gera o resumo.
        # Passamos 'não' para que a localização não seja enviada novamente.
        return handle_awaiting_location_or_finalize('não', sender_phone_number)
    else:
        # Resposta padrão para opções inválidas.
        return "Desculpe, não entendi. Por favor, responda '1' para começar um novo orçamento, ou '2' para ver o resumo do anterior."


# Dicionário de mapeamento de funções.
status_handlers = {
    Status.AGUARDANDO_NOME: handle_awaiting_name,
    Status.AGUARDANDO_EMAIL: handle_awaiting_email,
    Status.AGUARDANDO_ENDERECO: handle_awaiting_address,
    Status.AGUARDANDO_MODELO: handle_awaiting_model,
    Status.AGUARDANDO_ANO: handle_awaiting_year,
    Status.AGUARDANDO_ARMAZENAMENTO: handle_awaiting_storage,
    Status.AGUARDANDO_JOGOS: handle_awaiting_games,
    Status.AGUARDANDO_LOCALIZACAO_OU_FINALIZAR: handle_awaiting_location_or_finalize,
    Status.AGUARDANDO_CONTINUAR_OU_ENCERRAR: handle_awaiting_continue_or_end,
    Status.AGUARDANDO_DESBLOQUEIO_SEM_JOGOS: handle_awaiting_desbloqueio_sem_jogos,
    Status.AGUARDANDO_OPCAO_RETORNO: handle_awaiting_return_option
}

# --- FUNÇÃO PRINCIPAL ---

def whatsapp_webhook():
    """
    Função principal que processa a requisição do Twilio e gera a resposta do chatbot.
    """
    try:
        incoming_msg = request.values.get('Body', '').lower()
        sender_phone_number = request.values.get('From', '').replace('whatsapp:', '')
        resp = MessagingResponse()
        
        current_status = get_lead_status(sender_phone_number)
        
        response_message = ""
        
        # --- Lógica de fluxo principal otimizada ---
        
        # 1. Checagem de comandos de finalização por correspondência exata
        finalizar_comandos = ['9', 'quero finalizar', 'nao quero mais', 'parar']
        if incoming_msg.strip().lower() in finalizar_comandos:
            save_or_update_lead({'telefone': sender_phone_number, 'status': Status.FINALIZADO})
            response_message = content_data.get('respostas', {}).get('resposta_finalizada', 'Seu pedido foi finalizado. Em breve um de nossos consultores entrará em contato para te ajudar. Agradecemos o contato.')
        
        # 2. Checagem de comandos de ajuda
        elif get_intent(incoming_msg) == 'comando_ajuda':
            response_message = content_data.get('ajuda', 'Para recomeçar, digite "oi". Se deseja encerrar, digite "finalizar" ou "9".')
        
        # 3. Checagem de comandos de "voltar"
        elif get_intent(incoming_msg) == 'comando_voltar':
            response_message = content_data.get('voltar', 'Desculpe, o comando "voltar" ainda não está disponível no meu fluxo. Para recomeçar, digite "oi".')

        # 4. Início de conversa para usuário que JÁ FOI FINALIZADO
        elif current_status == Status.FINALIZADO and get_intent(incoming_msg) == 'saudacao':
            lead_info = get_lead_info(sender_phone_number)
            nome = lead_info.get('nome', 'amigo')
            # Muda o status para a nova etapa de escolha
            save_or_update_lead({'telefone': sender_phone_number, 'status': Status.AGUARDANDO_OPCAO_RETORNO})
            response_message = f"Olá novamente, {nome}! Qual é a sua opção?\n\n1 - Fazer um novo orçamento\n2 - Ver resumo do pedido anterior"

        # 5. Início de conversa para novo usuário (ou que não está finalizado)
        elif (not current_status or current_status == Status.INICIADO) and get_intent(incoming_msg) == 'saudacao':
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
                'status': Status.AGUARDANDO_NOME
            }
            save_or_update_lead(lead_data)
            response_message = content_data.get('boas_vindas', 'Olá, tudo bem? Para começarmos, qual é o seu nome?')
        
        # 6. Fluxo de conversa normal
        elif current_status in status_handlers:
            handler = status_handlers[current_status]
            response_message = handler(incoming_msg, sender_phone_number)
        
        # 7. Fallback para mensagens não reconhecidas
        else:
            response_message = "Desculpe, não entendi. Por favor, digite 'oi' para começar."

        resp.message(response_message)
        print(f"Resposta gerada: {response_message}\n")
        return str(resp)

    except Exception as e:
        print(f"Erro no webhook do WhatsApp: {e}")
        resp = MessagingResponse()
        resp.message("Desculpe, ocorreu um erro. Por favor, tente novamente mais tarde.")
        return str(resp)