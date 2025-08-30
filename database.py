import sqlite3
import pandas as pd
import json

def init_db():
    """Inicializa o banco de dados e cria a tabela 'leads'."""
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
    """Salva um novo lead no banco de dados."""
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

def update_lead_status_and_data(phone_number, new_status, new_data=None):
    """Atualiza o status e outros dados de um lead existente."""
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    
    if new_data:
        update_str = ', '.join([f"{key} = ?" for key in new_data.keys()])
        values = list(new_data.values()) + [new_status, phone_number, phone_number]
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
    """Retorna o status atual do lead, ou None se não existir."""
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM leads WHERE telefone = ? ORDER BY timestamp DESC LIMIT 1", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_lead_info(phone_number):
    """Retorna as informações do lead como um dicionário, ou None se não existir."""
    conn = sqlite3.connect('chatbot.db')
    df = pd.read_sql_query("SELECT * FROM leads WHERE telefone = ? ORDER BY timestamp DESC LIMIT 1", conn, params=(phone_number,))
    conn.close()
    
    if not df.empty:
        return df.iloc[0].to_dict()
    else:
        return None

def get_data_from_db():
    """Função centralizada para ler dados da tabela 'leads' do banco de dados."""
    conn = sqlite3.connect('chatbot.db')
    try:
        df = pd.read_sql_query("SELECT * FROM leads", conn)
    except pd.io.sql.DatabaseError:
        df = pd.DataFrame(columns=['id', 'timestamp', 'nome', 'email', 'telefone', 'endereco', 'modelo', 'ano', 'tipo_de_armazenamento', 'jogos_selecionados', 'status'])
    finally:
        conn.close()

    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['data_dia'] = df['timestamp'].dt.date

    return df