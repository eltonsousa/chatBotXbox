import sqlite3
import pandas as pd

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