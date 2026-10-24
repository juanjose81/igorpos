from app.database import get_db_connection
from flask import Blueprint, render_template

reportes_bp = Blueprint('reportes', __name__)


@reportes_bp.route('/reportes')
def vista_reportes():
  conn = get_db_connection()
  cur = conn.cursor()

  # Total de ventas y facturas registradas hoy
  cur.execute(
      'SELECT COUNT(*), COALESCE(SUM(total), 0) FROM facturas WHERE'
      ' DATE(fecha) = CURRENT_DATE;'
  )
  res_hoy = cur.fetchone()
  total_facturas_hoy = res_hoy[0]
  dinero_hoy = res_hoy[1]

  # Historial de últimas facturas
  cur.execute(
      'SELECT id, mesa_id, total, metodo_pago, fecha FROM facturas ORDER BY'
      ' id DESC LIMIT 20;'
  )
  facturas = cur.fetchall()

  cur.close()
  conn.close()

  return render_template(
      'reportes.html',
      total_facturas_hoy=total_facturas_hoy,
      dinero_hoy=dinero_hoy,
      facturas=facturas,
  )