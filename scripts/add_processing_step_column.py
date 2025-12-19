"""
Script de migração para adicionar coluna processing_step
Adiciona nomenclatura descritiva das etapas de processamento
"""
import psycopg2
import os

# Obter credenciais do PostgreSQL
db_host = os.getenv('DB_HOST', 'db')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'transcriptions')
db_user = os.getenv('DB_USER', 'postgres')
db_password = os.getenv('DB_PASSWORD', '')

try:
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password
    )
    cur = conn.cursor()
    
    # Verificar se a coluna já existe
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='transcription_tasks' AND column_name='processing_step'
    """)
    
    if cur.fetchone():
        print('✅ Coluna processing_step já existe; nada a fazer.')
    else:
        cur.execute('ALTER TABLE transcription_tasks ADD COLUMN processing_step TEXT;')
        conn.commit()
        print('✅ Coluna processing_step adicionada com sucesso.')
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f'❌ Erro ao adicionar coluna: {e}')
