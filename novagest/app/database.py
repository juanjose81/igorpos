import psycopg


def get_db_connection():
  conn = psycopg.connect(
      dbname='novagest_db',
      user='postgres',
      password='Novagest2026',
      host='localhost',
      port='5432',
  )
  return conn