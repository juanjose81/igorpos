import os
import psycopg

def get_db_connection():
    # Intenta leer la variable de entorno DATABASE_URL para producción en Vercel
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Corrección clave: psycopg exige 'postgresql://' en lugar de 'postgres://'
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
            
        # Si existe la variable en Vercel, se conecta a la base de datos en la nube
        conn = psycopg.connect(database_url)
    else:
        # Si no existe, usa tus credenciales locales manteniendo tu estructura intacta
        conn = psycopg.connect(
            dbname='novagest_db',
            user='postgres',
            password='Novagest2026',
            host='localhost',
            port='5432',
        )
    
    return conn