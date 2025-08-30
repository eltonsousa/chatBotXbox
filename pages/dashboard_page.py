import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output
from datetime import datetime, date
import plotly.graph_objects as go
from utils import get_data_from_db # Linha alterada: importa a função do novo arquivo

# --- FUNÇÕES ---

def create_funnel_graph(total_leads, modelos_count):
    df_funnel = pd.DataFrame(dict(
        number=[total_leads, modelos_count],
        stage=['Leads Totais', 'Modelo Selecionado']
    ))

    fig = go.Figure(go.Funnel(
        y=df_funnel['stage'],
        x=df_funnel['number'],
        textinfo="value+percent initial"
    ))

    fig.update_layout(
        title_text='Funil de Conversão de Leads',
        plot_bgcolor='rgb(33,37,41)',
        paper_bgcolor='rgb(33,37,41)',
        font_color='white'
    )
    return fig

def create_dashboard_elements(df, start_date=None, end_date=None, selected_year=None):
    df_filtered = df.copy()

    if selected_year is not None:
        df_filtered = df_filtered[df_filtered['ano'] == selected_year]
    elif start_date and end_date:
        start_date_obj = pd.to_datetime(start_date).normalize()
        end_date_obj = pd.to_datetime(end_date).normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_filtered = df_filtered[(df_filtered['timestamp'] >= start_date_obj) & (df_filtered['timestamp'] <= end_date_obj)]

    if df_filtered.empty:
        total_leads = 0
        modelos_count = 0
        leads_hoje = 0
        leads_recentes = 0
        df_modelos = pd.DataFrame(columns=['modelo', 'count'])
        df_leads_por_dia = pd.DataFrame(columns=['data_dia', 'count'])
        df_anos = pd.DataFrame(columns=['ano', 'count'])
        df_jogos = pd.DataFrame(columns=['jogos_selecionados', 'count']) # Linha corrigida
    else:
        total_leads = len(df_filtered)
        modelos_count = len(df_filtered.dropna(subset=['modelo']))

        hoje = pd.Timestamp.today().normalize()
        ultimos_7_dias = hoje - pd.Timedelta(days=7)
        leads_hoje = len(df_filtered[df_filtered['data_dia'] == hoje.date()])
        leads_recentes = len(df_filtered[df_filtered['timestamp'] >= ultimos_7_dias])

        try:
            df_jogos = df_filtered['jogos_selecionados'].value_counts().reset_index(name='count')
        except KeyError:
            df_jogos = pd.DataFrame(columns=['jogos_selecionados', 'count'])

        df_modelos = df_filtered['modelo'].value_counts().reset_index(name='count')
        df_leads_por_dia = df_filtered.groupby('data_dia').size().reset_index(name='count')
        df_anos = df_filtered['ano'].value_counts().reset_index(name='count')

    fig_modelos = px.pie(
        df_modelos,
        values='count',
        names='modelo',
        hole=0.4,
        title='Modelos de Xbox',
        labels={'modelo': 'Modelo do Console'},
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    fig_leads_por_dia = px.area(
        df_leads_por_dia,
        x='data_dia',
        y='count',
        labels={'data_dia': 'Data', 'count': 'Quantidade de Leads'},
        title='Leads por Dia',
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    fig_anos = px.bar(
        df_anos,
        x='ano',
        y='count',
        labels={'ano': 'Ano de Fabricação', 'count': 'Quantidade de Consoles'},
        title='Consoles por Ano de Fabricação',
        color_discrete_sequence=px.colors.sequential.Viridis
    )
    fig_jogos = px.bar(
        df_jogos,
        x='jogos_selecionados', # Linha corrigida
        y='count',
        labels={'jogos_selecionados': 'Jogo', 'count': 'Solicitações'},
        title='Jogos Mais Solicitados',
        color_discrete_sequence=px.colors.sequential.Plasma
    )

    fig_modelos.update_traces(textposition='inside', textinfo='percent+label')

    fig_funnel = create_funnel_graph(total_leads, modelos_count)

    return total_leads, modelos_count, leads_hoje, leads_recentes, fig_modelos, fig_leads_por_dia, fig_anos, fig_jogos, fig_funnel, df_filtered

# --- LAYOUT DO DASHBOARD ---
df_initial = get_data_from_db()
today = date.today()

total_leads_init, modelos_count_init, leads_hoje_init, leads_recentes_init, fig_modelos_init, fig_leads_por_dia_init, fig_anos_init, fig_jogos_init, fig_funnel_init, _ = create_dashboard_elements(df_initial, today, today)

layout = dbc.Container([
    # Componente de intervalo para auto-atualização a cada 30 segundos
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # em milissegundos
        n_intervals=0
    ),

    dbc.Row([
        dbc.Col(html.H2("Dashboard", className="text-white")),
        dbc.Col(
            html.P(id="last-updated-text", className="text-muted", style={'fontSize': '0.9em'}),
            width="auto", 
            align="end"
        )
    ], className="g-0 my-4 d-flex align-items-center justify-content-between"),

    dbc.Row([
        dbc.Col(
            html.Div([
                html.H5("Filtrar por Data", className="text-white"),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    start_date=today,
                    end_date=today,
                    display_format='DD/MM/YYYY',
                    style={
                        'color': '#fff',
                        'background-color': '#212529',
                        'border': '1px solid #495057'
                    }
                )
            ]),
            xs=12, md=6
        )
    ]),

    # KPIs
    dbc.Row([
        dbc.Col(dbc.Card(
            [
                dbc.CardHeader(html.H5("Total de Leads", className="text-white")),
                dbc.CardBody([
                    html.H3(id="total-leads", children=total_leads_init, className="text-white"),
                    html.I(className="fa-solid fa-users fa-2x fa-beat", style={'color': '#0b5ed7'})
                ], className="d-flex justify-content-between align-items-center")
            ],
            color="primary", inverse=True
        ), xs=12, sm=6, lg=3, className="my-2"),

        dbc.Col(dbc.Card(
            [
                dbc.CardHeader(html.H5("Hoje", className="text-white")),
                dbc.CardBody([
                    html.H3(id="leads-hoje", children=leads_hoje_init, className="text-white"),
                    html.I(className="fa-solid fa-calendar-day fa-2x fa-beat", style={'color': '#157347'})
                ], className="d-flex justify-content-between align-items-center")
            ],
            color="success", inverse=True
        ), xs=12, sm=6, lg=3, className="my-2"),

        dbc.Col(dbc.Card(
            [
                dbc.CardHeader(html.H5("Modelos", className="text-white")),
                dbc.CardBody([
                    html.H3(id="modelos-count", children=modelos_count_init, className="text-white"),
                    html.I(className="fa-solid fa-gamepad fa-2x fa-beat", style={'color': '#0aa6e0'})
                ], className="d-flex justify-content-between align-items-center")
            ],
            color="info", inverse=True
        ), xs=12, sm=6, lg=3, className="my-2"),

        dbc.Col(dbc.Card(
            [
                dbc.CardHeader(html.H5("Recentes", className="text-white")),
                dbc.CardBody([
                    html.H3(id="leads-recentes", children=leads_recentes_init, className="text-white"),
                    html.I(className="fa-solid fa-clock-rotate-left fa-2x fa-beat", style={'color': '#e6a300'})
                ], className="d-flex justify-content-between align-items-center")
            ],
            color="warning", inverse=True
        ), xs=12, sm=6, lg=3, className="my-2"),
    ], className="my-4"),

    dbc.Row([
        dbc.Col(
            dbc.Card(dbc.CardBody(
                dcc.Graph(id='graph-daily-leads', figure=fig_leads_por_dia_init)
            )), xs=12, md=6, className="mb-3"
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody(
                dcc.Graph(id='graph-funnel', figure=fig_funnel_init)
            )), xs=12, md=6
        ),
    ], className="my-4"),

    dbc.Row([
        dbc.Col(
            dbc.Card(dbc.CardBody(
                dcc.Graph(id='graph-models', figure=fig_modelos_init)
            )), xs=12, md=4, className="mb-3"
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody(
                dcc.Graph(id='graph-by-year', figure=fig_anos_init)
            )), xs=12, md=4, className="mb-3"
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody(
                dcc.Graph(id='graph-by-game', figure=fig_jogos_init)
            )), xs=12, md=4
        ),
    ], className="my-4"),

], fluid=True, className="bg-dark text-white p-3")

# --- CALLBACKS ---

@dash.callback(
    Output("last-updated-text", "children"),
    Output("total-leads", "children"),
    Output("modelos-count", "children"),
    Output("leads-hoje", "children"),
    Output("leads-recentes", "children"),
    Output("graph-daily-leads", "figure"),
    Output("graph-models", "figure"),
    Output("graph-by-year", "figure"),
    Output("graph-by-game", "figure"),
    Output("graph-funnel", "figure"),
    Input("interval-component", "n_intervals"),
    Input("date-picker-range", "start_date"),
    Input("date-picker-range", "end_date"),
    Input("graph-by-year", "clickData")
)
def update_dashboard(n, start_date, end_date, clickData):
    triggered_id = callback_context.triggered[0]['prop_id'].split('.')[0]

    df_updated = get_data_from_db()

    if triggered_id == 'interval-component':
        start_date = None
        end_date = None

    selected_year = None
    if clickData and 'points' in clickData:
        selected_year = clickData['points'][0]['x']

    total_leads, modelos_count, leads_hoje, leads_recentes, fig_modelos, fig_leads_por_dia, fig_anos, fig_jogos, fig_funnel, df_filtered = create_dashboard_elements(df_updated, start_date, end_date, selected_year)

    last_updated_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return (
        f"Última atualização: {last_updated_time}",
        total_leads,
        modelos_count,
        leads_hoje,
        leads_recentes,
        fig_leads_por_dia,
        fig_modelos,
        fig_anos,
        fig_jogos,
        fig_funnel,
    )