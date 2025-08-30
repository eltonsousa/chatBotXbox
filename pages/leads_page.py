import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output
import io
from datetime import datetime
from utils import get_data_from_db

# Layout da página de Leads
df_initial = get_data_from_db()
layout = dbc.Container(
    [
        html.H2("Dados Brutos dos Leads", className="text-white mt-4"),
        html.P("Aqui você pode visualizar, buscar e baixar todos os leads.", className="text-muted"),

        # Linha nova: Adiciona o dcc.Interval para auto-atualização
        dcc.Interval(
            id='interval-leads',
            interval=5*1000, # Atualiza a cada 5 segundos
            n_intervals=0
        ),
        
        # Linha nova: Adiciona um elemento para mostrar a data da última atualização
        html.P(id="last-updated-leads", className="text-muted", style={'fontSize': '0.9em'}),

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

# Callback para download dos dados (inalterado)
@dash.callback(
    Output("download-leads-csv", "data"),
    Input("download-button", "n_clicks"),
    prevent_initial_call=True,
)
def generate_csv(n_clicks):
    df = get_data_from_db()
    return dcc.send_data_frame(df.to_csv, "leads_xbox_360.csv")

# Linhas alteradas:
@dash.callback(
    Output('leads-table', 'data'),
    Output('last-updated-leads', 'children'),
    Input('interval-leads', 'n_intervals'), # Linha nova: agora o intervalo dispara o callback
    Input('leads-table', 'page_current'),
    Input('leads-table', 'page_size')
)
def update_table(n_intervals, page_current, page_size):
    df = get_data_from_db()
    last_updated_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return df.to_dict('records'), f"Última atualização: {last_updated_time}"