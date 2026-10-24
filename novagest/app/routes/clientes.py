from app.database import get_db_connection
from flask import Blueprint, redirect, render_template, request, url_for

clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('/clientes')
def listar_clientes():
  conn = get_db_connection()
  cur = conn.cursor()
  cur.execute('SELECT id, nombre, telefono, correo FROM clientes ORDER BY id DESC;')
  clientes = cur.fetchall()
  cur.close()
  conn.close()
  return render_template('clientes.html', clientes=clientes)


@clientes_bp.route('/clientes/agregar', methods=['POST'])
def agregar_cliente():
  nombre = request.form.get('nombre')
  telefono = request.form.get('telefono')
  correo = request.form.get('correo')

  conn = get_db_connection()
  cur = conn.cursor()
  cur.execute(
      'INSERT INTO clientes (nombre, telefono, correo) VALUES (%s, %s, %s);',
      (nombre, telefono, correo),
  )
  conn.commit()
  cur.close()
  conn.close()

  return redirect(url_for('clientes.listar_clientes'))