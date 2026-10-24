import os
import psycopg

def get_db_connection():
    # Intenta leer la variable de entorno DATABASE_URL que configuramos en Render
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Si existe (estamos en Render), se conecta usando la URL en la nube
        conn = psycopg.connect(database_url)
    else:
        # Si no existe (estás en tu computador local), usa tus datos de siempre
        conn = psycopg.connect(
            dbname='novagest_db',
            user='postgres',
            password='Novagest2026',
            host='localhost',
            port='5432',
        )
    
    return conn