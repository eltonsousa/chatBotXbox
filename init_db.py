import sqlite3

def init_db():
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    
    # Cria a tabela de leads se ela não existir
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
    print("Banco de dados e tabela 'leads' criados com sucesso.")

if __name__ == '__main__':
    init_db()