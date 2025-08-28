import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output
from pages import dashboard_page, status_page, leads_page
import sqlite3
import pandas as pd
from datetime import datetime
from flask import request
from twilio.twiml.messaging_response import MessagingResponse
import os
import re

# Use o link direto para a folha de estilo do Bootstrap
BS_THEME = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
FA_ICONS = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"

app = dash.Dash(__name__, external_stylesheets=[BS_THEME, FA_ICONS], suppress_callback_exceptions=True)
server = app.server

# --- Funções de interação com o banco de dados ---
def init_db():
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            nome TEXT,
            email TEXT,
            telefone TEXT,
            endereco TEXT,
            modelo TEXT,
            ano INTEGER,
            tipo_de_armazenamento TEXT,
            jogos_selecionados TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_lead_to_db(lead_data):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO leads (timestamp, nome, email, telefone, endereco, modelo, ano, tipo_de_armazenamento, jogos_selecionados, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        lead_data.get('timestamp'),
        lead_data.get('nome'),
        lead_data.get('email'),
        lead_data.get('telefone'),
        lead_data.get('endereco'),
        lead_data.get('modelo'),
        lead_data.get('ano'),
        lead_data.get('tipo_de_armazenamento'),
        lead_data.get('jogos_selecionados'),
        lead_data.get('status')
    ))
    conn.commit()
    conn.close()

def update_lead_status_and_data(phone_number, new_status, data_to_update=None):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()

    if data_to_update:
        update_str = ", ".join([f"{key} = ?" for key in data_to_update.keys()])
        values = list(data_to_update.values())
        values.append(new_status)
        values.append(phone_number)
        values.append(phone_number)
        
        cursor.execute(f'''
            UPDATE leads
            SET {update_str}, status = ?
            WHERE telefone = ? AND id = (
                SELECT id FROM leads
                WHERE telefone = ?
                ORDER BY timestamp DESC
                LIMIT 1
            )
        ''', tuple(values))
    else:
        cursor.execute('''
            UPDATE leads
            SET status = ?
            WHERE telefone = ? AND id = (
                SELECT id FROM leads
                WHERE telefone = ?
                ORDER BY timestamp DESC
                LIMIT 1
            )
        ''', (new_status, phone_number, phone_number))
        
    conn.commit()
    conn.close()

def get_lead_status(phone_number):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM leads WHERE telefone = ? ORDER BY timestamp DESC LIMIT 1", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_leads_count(phone_number):
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leads WHERE telefone = ?", (phone_number,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_lead_info(phone_number):
    conn = sqlite3.connect('chatbot.db')
    df = pd.read_sql_query("SELECT * FROM leads WHERE telefone = ? ORDER BY timestamp DESC LIMIT 1", conn, params=(phone_number,))
    conn.close()
    return df.iloc[0] if not df.empty else None

# Garante que o banco de dados e a tabela existem quando o app inicia
init_db()

# --- ROTA PARA O WEBHOOK DO WHATSAPP (TWILIO) ---
@server.route("/whatsapp_webhook", methods=["POST"])
def whatsapp_webhook():
    try:
        incoming_msg = request.values.get('Body', '').lower().strip()
        sender_phone_number = request.values.get('From', '')

        print(f"\n--- Nova Mensagem ---")
        print(f"Origem: {sender_phone_number}")
        print(f"Mensagem recebida: {incoming_msg}")

        resp = MessagingResponse()
        current_status = get_lead_status(sender_phone_number)
        
        # O estado finalizado é tratado de forma separada no final do código
        if current_status == 'FINALIZADO':
            response_message = "Parece que a nossa conversa foi finalizada. Para começar um novo atendimento, digite 'oi'."
            
            # Se a mensagem for 'oi', salva um novo lead e inicia o fluxo
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
            # Recebeu o nome, agora pede o email e o chama pelo nome
            nome = incoming_msg.capitalize()
            response_message = f"Certo, {nome}! Agora, por favor, me informe seu email. [9 - Sair]"
            update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_EMAIL', {'nome': nome})
            
        elif current_status == 'AGUARDANDO_EMAIL':
            # Recebeu o email, agora pede o endereço
            lead_info = get_lead_info(sender_phone_number)
            if lead_info is not None:
                nome = lead_info['nome']
                response_message = f"Obrigado, {nome}! Qual é o seu endereço completo? [9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ENDERECO', {'email': incoming_msg})
            else:
                response_message = "Desculpe, não consegui encontrar seu nome. Por favor, reinicie a conversa digitando 'oi'."
                update_lead_status_and_data(sender_phone_number, 'FINALIZADO')

        elif current_status == 'AGUARDANDO_ENDERECO':
            # Recebeu o endereço, agora pede o modelo
            response_message = "Obrigado! Qual é o modelo do seu Xbox? Por favor, digite o número da opção:\n1 - Fat\n2 - Slim\n3 - Super Slim\n\n[9 - Sair]"
            update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_MODELO', {'endereco': incoming_msg.capitalize()})
            
        elif current_status == 'AGUARDANDO_MODELO':
            # Recebeu o modelo, agora pede o ano
            modelos_mapeamento = {
                '1': 'Fat',
                '2': 'Slim',
                '3': 'Super Slim'
            }
            if incoming_msg in modelos_mapeamento:
                modelo_selecionado = modelos_mapeamento[incoming_msg]
                response_message = f"Entendido. Qual o ano de fabricação do seu console? (Ex: 2008, 2012). [9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_ANO', {'modelo': modelo_selecionado})
            else:
                response_message = "Por favor, digite um dos números válidos: 1, 2 ou 3."

        elif current_status == 'AGUARDANDO_ANO':
            # Recebeu o ano, valida e pede o tipo de armazenamento
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
            # Recebeu a opção de armazenamento
            if incoming_msg == '1':
                response_message = "Escolha 3 jogos da lista abaixo, separados por vírgula:\n1. GTA\n2. NFS\n3. FIFA 19\n4. PES 2018\n\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'HD Interno'})
            elif incoming_msg == '2':
                response_message = "Escolha 3 jogos da lista abaixo, separados por vírgula:\n1. GTA\n2. NFS\n3. FIFA 19\n4. PES 2018\n\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'HD Externo'})
            elif incoming_msg == '3':
                response_message = "Escolha 3 jogos da lista abaixo, separados por vírgula:\n1. GTA\n2. NFS\n3. FIFA 19\n4. PES 2018\n\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS', {'tipo_de_armazenamento': 'Pendrive 16gb+'})
            elif incoming_msg == '4':
                response_message = "Atenção: Sem armazenamento, não será possível jogar nem copiar os jogos. Deseja continuar o atendimento?\n1 - Sim\n2 - Não\n\n[9 - Sair]"
                update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_CONTINUAR', {'tipo_de_armazenamento': 'Não tenho'})
            else:
                response_message = "Opção inválida. Por favor, digite um número de 1 a 4."
        
        elif current_status == 'AGUARDANDO_CONTINUAR':
            lead_info = get_lead_info(sender_phone_number)
            if incoming_msg == '1':
                # Se o problema for 'Não tenho', pula a escolha de jogos
                if lead_info is not None and lead_info['tipo_de_armazenamento'] == 'Não tenho':
                    response_message = "Tudo certo! Você deseja receber o link da nossa localização? (1 - Sim / 2 - Não)\n\n[9 - Sair]"
                    update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_LOCALIZACAO', {'jogos_selecionados': 'Nenhum, pois não tem armazenamento'})
                else:
                    response_message = "Tudo bem, vamos prosseguir. Escolha 3 jogos da lista abaixo, separados por vírgula:\n1. GTA\n2. NFS\n3. FIFA 19\n4. PES 2018\n\n[9 - Sair]"
                    update_lead_status_and_data(sender_phone_number, 'AGUARDANDO_JOGOS')
            elif incoming_msg == '2':
                response_message = "Entendido. Obrigado por usar nosso serviço! Seu atendimento foi registrado. Qualquer dúvida, pode nos contatar."
                update_lead_status_and_data(sender_phone_number, 'FINALIZADO')
            else:
                response_message = "Opção inválida. Por favor, digite '1' para continuar ou '2' para finalizar."

        elif current_status == 'AGUARDANDO_JOGOS':
            # Recebeu a lista de jogos, valida e pede a localização
            jogos_mapeamento = {
                '1': 'GTA',
                '2': 'NFS',
                '3': 'FIFA 19',
                '4': 'PES 2018'
            }
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
            # Recebeu a escolha da localização e finaliza a conversa
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
            
            # Adiciona o resumo dos dados
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

# Layout principal que inclui a barra de navegação e o conteúdo dinâmico do Dash
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dcc.Link("Dashboard", href="/", className="nav-link")),
            dbc.NavItem(dcc.Link("Leads", href="/leads", className="nav-link")),
            dbc.NavItem(dcc.Link("Status", href="/status", className="nav-link")),
        ],
        brand="Xbox 360 Repair",
        brand_href="/",
        color="dark",
        dark=True,
    ),
    html.Div(id='page-content')
])

# Callback para gerenciar a navegação entre as páginas do Dash
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/status':
        return status_page.layout
    elif pathname == '/leads':
        return leads_page.layout
    else:
        return dashboard_page.layout

if __name__ == '__main__':
    app.run(debug=True, port=8050)