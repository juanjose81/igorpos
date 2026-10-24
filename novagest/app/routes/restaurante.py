from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg

restaurante_bp = Blueprint('restaurante', __name__)

DB_CONFIG = "dbname=novagest_db user=postgres password=Novagest2026 host=localhost"

# ==========================================
# REDIRECCIÓN BLINDADA CONTRA EL ERROR 404
# ==========================================
@restaurante_bp.route('/admin/dashboard')
def dashboard_redirect():
    return redirect('/admin')

# --- CREAR PRODUCTO ---
@restaurante_bp.route('/productos/crear', methods=['GET', 'POST'])
def crear_producto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        categoria = request.form.get('categoria')
        descripcion = request.form.get('descripcion', '')
        try:
            conex = psycopg.connect(DB_CONFIG)
            with conex.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO productos (nombre, precio, categoria, descripcion) VALUES (%s, %s, %s, %s)",
                    (nombre, precio, categoria, descripcion)
                )
                conex.commit()
            conex.close()
            flash('¡Producto creado con éxito!', 'success')
            return redirect('/admin')
        except Exception as e:
            flash(f'Error al crear el producto: {e}', 'danger')
    return render_template('crear_producto.html')

# --- RUTAS DE COCINA Y BAR ---
@restaurante_bp.route('/admin/cocina')
def vista_cocina():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
        
    try:
        conex = psycopg.connect(DB_CONFIG)
        with conex.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, m.numero_mesa, p.producto, p.cantidad, p.estado, p.destino, p.fecha_comandado
                FROM pedidos_mesa p
                JOIN mesas m ON p.id_mesa = m.id
                WHERE p.estado IN ('Pendiente', 'Comandado') 
                  AND (LOWER(p.destino) = 'cocina' OR p.destino IS NULL OR p.destino = '')
                ORDER BY p.id ASC;
            """)
            pedidos = cursor.fetchall()
            print("--- PEDIDOS ENCONTRADOS PARA COCINA: ---", pedidos)
        conex.close()
    except Exception as e:
        print("--- ERROR EN COCINA: ---", e)
        pedidos = []

    lista_pedidos = []
    for p in pedidos:
        f_comandado = p[6].isoformat() if p[6] else ''
        lista_pedidos.append({
            'id': p[0],
            'mesa': p[1],
            'producto': p[2],
            'cantidad': p[3],
            'estado': p[4],
            'destino': p[5] or 'Cocina',
            'fecha_comandado': f_comandado
        })
        
    return render_template('cocina.html', pedidos=lista_pedidos)

@restaurante_bp.route('/admin/bar')
def vista_bar():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
        
    try:
        conex = psycopg.connect(DB_CONFIG)
        with conex.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, m.numero_mesa, p.producto, p.cantidad, p.estado, p.destino, p.fecha_comandado
                FROM pedidos_mesa p
                JOIN mesas m ON p.id_mesa = m.id
                WHERE p.estado IN ('Pendiente', 'Comandado') 
                  AND LOWER(p.destino) = 'bar'
                ORDER BY p.id ASC;
            """)
            pedidos = cursor.fetchall()
            print("--- PEDIDOS ENCONTRADOS PARA BAR: ---", pedidos)
        conex.close()
    except Exception as e:
        pedidos = []

    lista_pedidos = []
    for p in pedidos:
        f_comandado = p[6].isoformat() if p[6] else ''
        lista_pedidos.append({
            'id': p[0],
            'mesa': p[1],
            'producto': p[2],
            'cantidad': p[3],
            'estado': p[4],
            'destino': p[5],
            'fecha_comandado': f_comandado
        })
        
    return render_template('bar.html', pedidos=lista_pedidos)

@restaurante_bp.route('/admin/pedido/entregar/<int:id_pedido>', methods=['POST'])
def marcar_entregado(id_pedido):
    try:
        conex = psycopg.connect(DB_CONFIG)
        with conex.cursor() as cursor:
            cursor.execute("UPDATE pedidos_mesa SET estado = 'Entregado' WHERE id = %s;", (id_pedido,))
            conex.commit()
        conex.close()
    except Exception as e:
        pass
    
    return redirect(request.referrer or url_for('restaurante.vista_cocina'))