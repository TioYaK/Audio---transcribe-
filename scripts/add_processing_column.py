import sqlite3
import os
import sys

DB_PATH = os.getenv('DATABASE_PATH', '/app/data/transcriptions.db')

if not os.path.exists(DB_PATH):
    print('ERRO: arquivo de banco não encontrado em', DB_PATH)
    sys.exit(2)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("PRAGMA table_info(transcription_tasks);")
cols = [r[1] for r in cur.fetchall()]
print('Colunas atuais:', cols)
if 'processing_time' in cols:
    print('Já existe coluna processing_time; nada a fazer.')
    conn.close()
    sys.exit(0)

try:
    cur.execute('ALTER TABLE transcription_tasks ADD COLUMN processing_time FLOAT;')
    conn.commit()
    print('Coluna processing_time adicionada com sucesso.')
except Exception as e:
    print('Erro ao adicionar coluna:', e)
    sys.exit(3)
finally:
    conn.close()
