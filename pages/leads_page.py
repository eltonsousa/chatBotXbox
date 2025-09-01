import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import io
from datetime import datetime
from utils import get_data_from_db
import json
import pandas as pd

# Carrega o conteúdo dinâmico do arquivo JSON
try:
    with open('content.json', 'r', encoding='utf-8') as f:
        content_data = json.load(f)
except FileNotFoundError:
    print("Erro: O arquivo 'content.json' não foi encontrado. Certifique-se de que ele está na mesma pasta que o 'leads_page.py'.")
    content_data = {}

# Layout da página de Leads
df_initial = get_data_from_db()

layout = dbc.Container(
    [
        html.H2("Dados dos Leads", className="text-white mt-4"),
        html.P("Visualize e gerencie os leads gerados pelo chatbot.", className="text-muted"),

        dcc.Interval(
            id='interval-leads',
            interval=5*1000,
            n_intervals=0
        ),

        html.Div(id="modal-trigger"), # Elemento para disparar o modal

        html.P(id="last-updated-leads", className="text-muted", style={'fontSize': '0.9em'}),

        # Linha para os botões e campo de busca
        dbc.Row([
            dbc.Col(
                dbc.Button("Baixar Dados", id="download-button", color="secondary", className="mb-3"),
                width="auto"
            ),
            dbc.Col(
                dcc.Download(id="download-leads-csv")
            ),
            dbc.Col(
                dbc.Input(
                    id="search-input",
                    placeholder="Buscar por nome, email ou telefone...",
                    type="text",
                    className="mb-3"
                ),
                width=True
            )
        ], className="align-items-center"),

        # Tabela de Leads
        dash_table.DataTable(
            id='leads-table',
            columns=[
                {"name": "Data", "id": "timestamp"},
                {"name": "Nome", "id": "nome"},
                {"name": "Email", "id": "email"},
                {"name": "Telefone", "id": "telefone"},
                {"name": "Status", "id": "status"}
            ],
            data=df_initial.to_dict('records'),
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{status} eq "FINALIZADO"'},
                    'backgroundColor': '#28a745',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                {
                    'if': {'filter_query': '{status} eq "AGUARDANDO_NOME"'},
                    'backgroundColor': '#ffc107',
                    'color': 'black',
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
            },
            row_selectable='single',
        ),

        # Modal para exibir os detalhes do lead
        dbc.Modal(
            [
                dbc.ModalHeader("Detalhes do Lead"),
                dbc.ModalBody(id="modal-body"),
                dbc.ModalFooter(
                    dbc.Button("Fechar", id="close-modal", className="ms-auto")
                ),
            ],
            id="modal-leads",
            is_open=False,
            className="bg-dark text-gray"
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

# Callback para atualizar a tabela e o timestamp
@dash.callback(
    Output('leads-table', 'data'),
    Output('last-updated-leads', 'children'),
    Input('interval-leads', 'n_intervals'),
    Input('search-input', 'value')
)
def update_table_data(n_intervals, search_value):
    df = get_data_from_db()

    # Aplica o filtro de busca
    if search_value:
        df_filtered = df[
            df.apply(
                lambda row: search_value.lower() in str(row['nome']).lower() or
                            search_value.lower() in str(row['email']).lower() or
                            search_value.lower() in str(row['telefone']).lower(),
                axis=1
            )
        ]
    else:
        df_filtered = df

    data = df_filtered.to_dict('records')
    last_updated_time = datetime.now().strftime("%H:%M:%S")
    return data, f"Última atualização: {last_updated_time}"

# Callback para exibir o modal
@dash.callback(
    Output("modal-leads", "is_open"),
    Output("modal-body", "children"),
    Input("leads-table", "selected_rows"),
    Input("close-modal", "n_clicks"),
    State("leads-table", "data"),
    State("modal-leads", "is_open"),
)
def toggle_modal(selected_rows, close_clicks, rows, is_open):
    triggered_id = callback_context.triggered[0]['prop_id']

    # Se o modal está sendo fechado, apenas feche-o
    if triggered_id == "close-modal.n_clicks":
        return not is_open, ""

    # Se uma linha foi selecionada, abra o modal e preencha com os dados
    if selected_rows:
        selected_lead = rows[selected_rows[0]]
        
        # Cria a lista de informações para o modal
        info_list = html.Ul([
            html.Li(f"ID: {selected_lead.get('id', 'N/A')}"),
            html.Li(f"Nome: {selected_lead.get('nome', 'N/A')}"),
            html.Li(f"Email: {selected_lead.get('email', 'N/A')}"),
            html.Li(f"Telefone: {selected_lead.get('telefone', 'N/A')}"),
            html.Li(f"Endereço: {selected_lead.get('endereco', 'N/A')}"),
            html.Li(f"Modelo: {selected_lead.get('modelo', 'N/A')}"),
            html.Li(f"Ano: {selected_lead.get('ano', 'N/A')}"),
            html.Li(f"Armazenamento: {selected_lead.get('tipo_de_armazenamento', 'N/A')}"),
            html.Li(f"Jogos: {selected_lead.get('jogos_selecionados', 'N/A')}"),
            html.Li(f"Status: {selected_lead.get('status', 'N/A')}"),
            html.Li(f"Data/Hora: {selected_lead.get('timestamp', 'N/A')}")
        ])
        
        return not is_open, info_list

    return is_open, ""