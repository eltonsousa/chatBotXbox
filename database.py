import sqlite3
import pandas as pd
from datetime import datetime

DATABASE_NAME = 'chatbot.db'

def init_db():
    """
    Inicializa o banco de dados e cria a tabela 'leads' com a coluna 'telefone'
    como chave primária para garantir que cada telefone seja único.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            telefone TEXT PRIMARY KEY,
            timestamp TEXT,
            nome TEXT,
            email TEXT,
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

def save_or_update_lead(lead_data):
    """
    Salva ou atualiza um lead no banco de dados usando o 'telefone' como identificador único.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Prepara os dados, removendo o telefone e o timestamp da lista de colunas a serem atualizadas
    telefone = lead_data.pop('telefone', None)
    lead_data['timestamp'] = datetime.now().isoformat()
    
    if not telefone:
        # Se o telefone não for fornecido, a operação não pode ser concluída.
        print("Erro: O número de telefone é obrigatório para salvar ou atualizar um lead.")
        return

    # Constrói a query de atualização dinamicamente
    update_fields = ", ".join([f"{key} = ?" for key in lead_data.keys()])
    update_values = list(lead_data.values())
    
    # Tenta atualizar o registro existente
    cursor.execute(f"UPDATE leads SET {update_fields} WHERE telefone = ?", update_values + [telefone])
    
    # Se nenhuma linha foi atualizada, o lead não existia. Então, insere um novo.
    if cursor.rowcount == 0:
        columns = "telefone, " + ", ".join(lead_data.keys())
        placeholders = ", ".join(["?"] * (len(lead_data) + 1))
        
        cursor.execute(f"INSERT INTO leads ({columns}) VALUES ({placeholders})", [telefone] + list(lead_data.values()))
    
    conn.commit()
    conn.close()

def get_lead_status(phone_number):
    """Retorna o status atual do lead, ou None se não existir."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM leads WHERE telefone = ?", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_lead_info(phone_number):
    """Retorna as informações do lead como um dicionário, ou None se não existir."""
    conn = sqlite3.connect(DATABASE_NAME)
    df = pd.read_sql_query("SELECT * FROM leads WHERE telefone = ?", conn, params=(phone_number,))
    conn.close()
    
    if not df.empty:
        return df.iloc[0].to_dict()
    else:
        return None

def get_data_from_db():
    """Função centralizada para ler dados da tabela 'leads' do banco de dados."""
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        df = pd.read_sql_query("SELECT * FROM leads", conn)
    except pd.io.sql.DatabaseError:
        df = pd.DataFrame(columns=['telefone', 'timestamp', 'nome', 'email', 'endereco', 'modelo', 'ano', 'tipo_de_armazenamento', 'jogos_selecionados', 'status'])
    finally:
        conn.close()

    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['data_dia'] = df['timestamp'].dt.date

    return df