from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import get_db_connection

pos_bp = Blueprint('pos', __name__)

@pos_bp.route('/pos', methods=['GET'])
def seleccionar_mesa():
    if 'usuario_id' not in session:
        return redirect('/login')

    empresa_id = session.get('empresa_id')
    conn = get_db_connection()
    cur = conn.cursor()

    # Validar si hay una caja abierta para la empresa
    cur.execute("SELECT id FROM cajas WHERE empresa_id = %s AND estado = 'abierta';", (empresa_id,))
    caja_abierta = cur.fetchone()

    if not caja_abierta and session.get('rol') == 'auxiliar':
        conn.close()
        return "<h3>⛔ Acceso Bloqueado: La caja se encuentra cerrada. Solicita al Gerente o Administrador que abra la caja para operar el POS.</h3>", 403

    # Cargar las mesas de la empresa
    cur.execute("SELECT id, numero_mesa, estado FROM mesas WHERE empresa_id = %s ORDER BY id ASC;", (empresa_id,))
    mesas = cur.fetchall()
    conn.close()

    return render_template('pos_mesas.html', mesas=mesas)

@pos_bp.route('/pos/mesa/<int:mesa_id>', methods=['GET', 'POST'])
def interfaz_pos(mesa_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    empresa_id = session.get('empresa_id')
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener info de la mesa
    cur.execute("SELECT id, numero_mesa, estado FROM mesas WHERE id = %s AND empresa_id = %s;", (mesa_id, empresa_id))
    mesa = cur.fetchone()
    if not mesa:
        conn.close()
        return "Mesa no encontrada", 404

    # Obtener productos disponibles de la empresa
    cur.execute("SELECT id, nombre, precio, area_preparacion FROM productos WHERE empresa_id = %s;", (empresa_id,))
    productos = cur.fetchall()

    if request.method == 'POST':
        # Procesar comanda enviada
        productos_seleccionados = request.form.getlist('producto_id')
        cantidades = request.form.getlist('cantidad')

        if productos_seleccionados:
            # Crear una orden principal para la mesa
            cur.execute("""
                INSERT INTO ordenes (mesa_id, usuario_id, empresa_id, estado)
                VALUES (%s, %s, %s, 'pendiente') RETURNING id;
            """, (mesa_id, session['usuario_id'], empresa_id))
            orden_id = cur.fetchone()[0]

            for i in range(len(productos_seleccionados)):
                prod_id = productos_seleccionados[i]
                cant = int(cantidades[i])
                if cant > 0:
                    # Obtener datos del producto (precio y area_preparacion)
                    cur.execute("SELECT precio, area_preparacion FROM productos WHERE id = %s;", (prod_id,))
                    prod_info = cur.fetchone()
                    precio = prod_info[0]
                    area = prod_info[1] # 'cocina' o 'bar'

                    # Insertar detalle de la orden con su área de destino correspondiente
                    cur.execute("""
                        INSERT INTO detalle_ordenes (orden_id, producto_id, cantidad, precio_unitario, area_destino, estado_item)
                        VALUES (%s, %s, %s, %s, %s, 'pendiente');
                    """, (orden_id, prod_id, cant, precio, area))

            # Cambiar estado de la mesa a ocupada
            cur.execute("UPDATE mesas SET estado = 'ocupada' WHERE id = %s;", (mesa_id,))
            conn.commit()
            conn.close()
            flash("¡Comanda enviada con éxito a Cocina y Bar!")
            return redirect(url_for('pos.seleccionar_mesa'))

    conn.close()
    return render_template('pos.html', mesa=mesa, productos=productos)

@pos_bp.route('/cocina', methods=['GET'])
def pantalla_cocina():
    if 'usuario_id' not in session:
        return redirect('/login')

    empresa_id = session.get('empresa_id')
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener ítems pendientes para la cocina
    cur.execute("""
        <output omitted for brevity, full query below>
    """)
    # (Consulta integrada para traer ítems de área cocina de la empresa)
    cur.execute("""
        SELECT d.id, m.numero_mesa, p.nombre, d.cantidad, d.estado_item
        FROM detalle_ordenes d
        JOIN ordenes o ON d.orden_id = o.id
        JOIN mesas m ON o.mesa_id = m.id
        JOIN productos p ON d.producto_id = p.id
        WHERE o.empresa_id = %s AND d.area_destino = 'cocina' AND d.estado_item = 'pendiente';
    """, (empresa_id,))
    items_cocina = cur.fetchall()
    conn.close()

    return render_template('cocina.html', items_cocina=items_cocina)

@pos_bp.route('/bar', methods=['GET'])
def pantalla_bar():
    if 'usuario_id' not in session:
        return redirect('/login')

    empresa_id = session.get('empresa_id')
    conn = get_db_connection()
    cur = conn.cursor()

    # Obtener ítems pendientes para el bar
    cur.execute("""
        SELECT d.id, m.numero_mesa, p.nombre, d.cantidad, d.estado_item
        FROM detalle_ordenes d
        JOIN ordenes o ON d.orden_id = o.id
        JOIN mesas m ON o.mesa_id = m.id
        JOIN productos p ON d.producto_id = p.id
        WHERE o.empresa_id = %s AND d.area_destino = 'bar' AND d.estado_item = 'pendiente';
    """, (empresa_id,))
    items_bar = cur.fetchall()
    conn.close()

    return render_template('bar.html', items_bar=items_bar)

