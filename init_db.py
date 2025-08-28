import sqlite3

def init_db():
    conn = sqlite3.connect('chatbot.db')
    cursor = conn.cursor()
    
    # Cria a tabela de leads se ela não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            timestamp TEXT,
            nome TEXT,
            telefone TEXT,
            modelo TEXT,
            ano INTEGER,
            problema TEXT,
            jogos_solicitados TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Banco de dados e tabela 'leads' criados com sucesso.")

if __name__ == '__main__':
    init_db()