import dash
import dash_bootstrap_components as dbc
import sqlite3
import pandas as pd
import os
from dash import html, dcc
from dash.dependencies import Input, Output
from datetime import datetime

# Função para verificar o status do banco de dados
def check_db_status():
    try:
        if not os.path.exists('chatbot.db'):
            return "❌ Banco de Dados não encontrado", "danger"
            
        conn_test = sqlite3.connect('chatbot.db')
        df_leads = pd.read_sql_query("SELECT * FROM leads", conn_test)
        conn_test.close()
        
        last_lead_time = "Nenhum lead encontrado"
        if not df_leads.empty:
            last_lead_timestamp = df_leads['timestamp'].max()
            last_lead_time = datetime.fromisoformat(last_lead_timestamp).strftime("%d/%m/%Y %H:%M:%S")

        return f"✅ Conexão OK (Último lead: {last_lead_time})", "success"
    except Exception as e:
        return f"❌ Erro de Conexão: {e}", "danger"

# Layout da página de Status
layout = dbc.Container([
    html.H2("Status da Aplicação", className="text-white mt-4"),
    html.P("Esta página monitora a saúde dos componentes principais.", className="text-muted"),
    
    dbc.Row([
        dbc.Col(
            dbc.Card(
                [
                    dbc.CardHeader(html.H5("Status do Banco de Dados", className="text-white")),
                    dbc.CardBody([
                        html.H3(id="db-status-text", className="text-white"),
                        html.P("Verifica se o arquivo chatbot.db existe e pode ser lido."),
                    ], className="d-flex justify-content-between align-items-center flex-column")
                ],
                color="dark", inverse=True
            ),
            className="my-3"
        ),
    ]),
    
    html.Hr(className="my-4"),
    
    html.Div(id='dummy-div', style={'display': 'none'}), # Elemento para disparar o callback
    dcc.Interval(
        id='interval-status',
        interval=5*1000, # Atualiza a cada 5 segundos
        n_intervals=0
    ),

], fluid=True, className="bg-dark text-white p-3")

# Callback para atualizar o status
@dash.callback(
    Output("db-status-text", "children"),
    Output("db-status-text", "className"),
    Input("interval-status", "n_intervals")
)
def update_status(n):
    status_text, status_color = check_db_status()
    text_class = f"text-{status_color}"
    return status_text, text_class