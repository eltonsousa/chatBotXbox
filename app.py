import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
from pages import dashboard_page, status_page, leads_page
from database import init_db
from chatbot import whatsapp_webhook
from flask import request

# Use o link direto para a folha de estilo do Bootstrap
BS_THEME = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
FA_ICONS = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"

app = dash.Dash(__name__, external_stylesheets=[BS_THEME, FA_ICONS], suppress_callback_exceptions=True)
server = app.server

# Garante que o banco de dados e a tabela existem quando o app inicia
init_db()

# --- ROTA PARA O WEBHOOK DO WHATSAPP (TWILIO) ---
@server.route("/whatsapp_webhook", methods=["POST"])
def webhook():
    return whatsapp_webhook()

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
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/leads':
        return leads_page.layout
    elif pathname == '/status':
        return status_page.layout
    else:
        return dashboard_page.layout

# Não chame as funções de callback aqui. O Dash as executará automaticamente.

if __name__ == '__main__':
    app.run(debug=True)