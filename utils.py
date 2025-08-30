import pandas as pd
import sqlite3

def get_data_from_db():
    """
    Função centralizada para ler dados da tabela 'leads' do banco de dados.
    Garante que a estrutura dos dados seja consistente em todas as páginas do Dash.
    """
    conn = sqlite3.connect('chatbot.db')
    try:
        df = pd.read_sql_query("SELECT * FROM leads", conn)
    except pd.io.sql.DatabaseError:
        # Retorna um DataFrame vazio com a estrutura de colunas correta
        # de acordo com a tabela definida em database.py
        df = pd.DataFrame(columns=[
            'id', 'timestamp', 'nome', 'email', 'telefone', 'endereco', 'modelo',
            'ano', 'tipo_de_armazenamento', 'jogos_selecionados', 'status'
        ])
    finally:
        conn.close()

    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['data_dia'] = df['timestamp'].dt.date

    return df