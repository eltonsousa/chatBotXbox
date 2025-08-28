import dash
import dash_bootstrap_components as dbc
import pandas as pd
import sqlite3
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import io
from datetime import datetime

# Estilos externos para a tabela
BS_THEME = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
FA_ICONS = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"


# --- FUNÇÕES ---
def get_data_from_db():
    conn_dash = sqlite3.connect('chatbot.db')
    try:
        # Tenta ler os dados da tabela
        df = pd.read_sql_query("SELECT * FROM leads", conn_dash)
    except pd.io.sql.DatabaseError:
        # Se a tabela não existir, retorna um DataFrame vazio
        df = pd.DataFrame(columns=['timestamp', 'nome', 'email', 'telefone', 'endereco', 'modelo', 'ano', 'problema', 'jogos_selecionados', 'localizacao_solicitada', 'status'])
    finally:
        conn_dash.close()
    
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['data_dia'] = df['timestamp'].dt.date
    
    return df

# Layout da página de Leads
df_initial = get_data_from_db()
layout = dbc.Container(
    [
        html.H2("Dados Brutos dos Leads", className="text-white mt-4"),
        html.P("Aqui você pode visualizar, buscar e baixar todos os leads.", className="text-muted"),
        
        dbc.Button("Baixar Dados", id="download-button", color="secondary", className="mb-3"),
        dcc.Download(id="download-leads-csv"),

        dash_table.DataTable(
            id='leads-table',
            columns=[{"name": i, "id": i} for i in df_initial.columns],
            data=df_initial.to_dict('records'),
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{status} eq "FINALIZADO"'},
                    'backgroundColor': '#28a745',
                    'color': 'white',
                    'fontWeight': 'bold'
                }
            ],
            style_header={
                'backgroundColor': '#343a40',
                'color': 'white',
                'fontWeight': 'bold'
            },
            style_data={
                'backgroundColor': '#495057',
                'color': 'white'
            }
        )
    ],
    fluid=True,
    className="bg-dark text-white p-3",
)

# Callback para download dos dados
@dash.callback(
    Output("download-leads-csv", "data"),
    Input("download-button", "n_clicks"),
    prevent_initial_call=True,
)
def generate_csv(n_clicks):
    df = get_data_from_db()
    return dcc.send_data_frame(df.to_csv, "leads_xbox_360.csv")

# Callback para atualizar a tabela (com a atualização automática)
@dash.callback(
    Output('leads-table', 'data'),
    Input('leads-table', 'page_current'),
    Input('leads-table', 'page_size')
)
def update_table(page_current, page_size):
    df = get_data_from_db()
    return df.to_dict('records')