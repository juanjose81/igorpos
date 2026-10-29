from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import urllib.parse
import traceback
from app.dian_service import enviar_factura_dian_api
from app.database import get_db_connection

caja_mesas_bp = Blueprint('caja_mesas', __name__)
NUMERO_EMISOR_POS = "3213860752"

def asegurar_tablas_globales(cursor, conex):
    cursor.execute("CREATE TABLE IF NOT EXISTS caja_diaria (id SERIAL PRIMARY KEY);")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS empresa_id INT;")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS monto_inicial NUMERIC(12,2) DEFAULT 0;")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS monto_final NUMERIC(12,2) DEFAULT 0;")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS total_ventas NUMERIC(12,2) DEFAULT 0;")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'Cerrada';")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS fecha_apertura TIMESTAMP DEFAULT NOW();")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS fecha_cierre TIMESTAMP;")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS usuario_apertura VARCHAR(100);")
    cursor.execute("ALTER TABLE caja_diaria ADD COLUMN IF NOT EXISTS usuario_cierre VARCHAR(100);")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_ventas (
            id SERIAL PRIMARY KEY,
            empresa_id INT,
            id_mesa INT,
            numero_mesa VARCHAR(50),
            total_venta NUMERIC(12,2) DEFAULT 0,
            tipo_pago VARCHAR(50),
            efectivo_recibido NUMERIC(12,2) DEFAULT 0,
            devueltas NUMERIC(12,2) DEFAULT 0,
            atendido_por VARCHAR(100),
            fecha_venta TIMESTAMP DEFAULT NOW()
        );
    """)
    cursor.execute("ALTER TABLE historial_ventas ADD COLUMN IF NOT EXISTS empresa_id INT;")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mesas (
            id SERIAL PRIMARY KEY,
            empresa_id INT,
            numero_mesa VARCHAR(50) NOT NULL,
            estado VARCHAR(50) DEFAULT 'Disponible',
            mesero_atendiendo VARCHAR(100) DEFAULT 'Sin asignar'
        );
    """)
    cursor.execute("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS empresa_id INT;")
    cursor.execute("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS numero_mesa VARCHAR(50);")
    cursor.execute("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'Disponible';")
    cursor.execute("ALTER TABLE mesas ADD COLUMN IF NOT EXISTS mesero_atendiendo VARCHAR(100) DEFAULT 'Sin asignar';")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos_mesa (
            id SERIAL PRIMARY KEY,
            empresa_id INT,
            id_mesa INT,
            producto VARCHAR(150),
            precio NUMERIC(10,2),
            cantidad INT DEFAULT 1,
            estado VARCHAR(50) DEFAULT 'Pendiente',
            destino VARCHAR(50) DEFAULT 'Cocina',
            id_venta_asociada INT,
            fecha_comandado TIMESTAMP DEFAULT NOW()
        );
    """)
    cursor.execute("ALTER TABLE pedidos_mesa ADD COLUMN IF NOT EXISTS empresa_id INT;")
    cursor.execute("ALTER TABLE pedidos_mesa ADD COLUMN IF NOT EXISTS id_venta_asociada INT;")
    cursor.execute("ALTER TABLE pedidos_mesa ADD COLUMN IF NOT EXISTS destino VARCHAR(50) DEFAULT 'Cocina';")
    cursor.execute("ALTER TABLE pedidos_mesa ADD COLUMN IF NOT EXISTS fecha_comandado TIMESTAMP DEFAULT NOW();")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            empresa_id INT,
            nombre VARCHAR(150) NOT NULL,
            precio NUMERIC(12,2) DEFAULT 0,
            stock INT DEFAULT 0,
            categoria VARCHAR(100) DEFAULT 'General',
            destino VARCHAR(50) DEFAULT 'Cocina',
            descripcion TEXT
        );
    """)
    cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS destino VARCHAR(50) DEFAULT 'Cocina';")
    cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS empresa_id INT;")
    cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS descripcion TEXT;")
    conex.commit()

def sincronizar_estados_mesas(cursor, conex, empresa_id):
    # Una mesa solo se mantiene ocupada si tiene productos COMANDADOS, LISTOS o ENTREGADOS. 
    # Los 'Pendientes' que no se han mandado a cocina no deben bloquear la mesa ni mostrar precios falsos.
    cursor.execute("""
        UPDATE mesas 
        SET estado = 'Disponible', mesero_atendiendo = 'Sin asignar'
        WHERE empresa_id = %s 
        AND id NOT IN (
            SELECT DISTINCT id_mesa 
            FROM pedidos_mesa 
            WHERE empresa_id = %s AND estado IN ('Comandado', 'Listo', 'Entregado')
        );
    """, (empresa_id, empresa_id))
    conex.commit()

def obtener_empresa_id_seguro(cursor):
    raw_empresa = session.get('empresa_id') or session.get('usuario_id') or session.get('user_id')
    if not raw_empresa:
        return 1
    if str(raw_empresa).isdigit():
        return int(raw_empresa)
    try:
        cursor.execute("SELECT id FROM usuarios WHERE usuario = %s OR nombre = %s LIMIT 1;", (str(raw_empresa), str(raw_empresa)))
        res = cursor.fetchone()
        if res:
            return int(res[0])
    except Exception:
        pass
    return 1

def generar_enlace_whatsapp(telefono_cliente, cliente_nombre, cliente_nit, id_venta, total_venta, numero_mesa, items, url_documento=None):
    if not telefono_cliente:
        return "#"
    tel_limpio = "".join(filter(str.isdigit, str(telefono_cliente)))
    if len(tel_limpio) == 10 and not tel_limpio.startswith("57"):
        tel_limpio = "57" + tel_limpio
        
    detalle_items = ""
    for item in items:
        detalle_items += f"   • {item['cantidad']}x {item['producto']} — ${item['subtotal']:,.2f}\n"
        
    base_url = request.host_url.rstrip('/')
    if "onrender.com" not in base_url and "localhost" not in base_url:
        base_url = "https://igorpos.onrender.com"
    url_real = f"{base_url}/admin/verificar-factura/{id_venta}"

    mensaje = (
        f"🚚 *Entrega:* Mesa / Domicilio (Mesa {numero_mesa})\n"
        f"👤 *Cliente:* {cliente_nombre or 'Consumidor Final'}\n"
        f"📄 *NIT/CC:* {cliente_nit or '222222222222'}\n"
        f"📞 *Tel:* +57 {tel_limpio}\n\n"
        f"💳 *Pago:* Efectivo / Transferencia\n"
        f"✅ Generado desde IGOR POS\n"
        f"----------------------------------------\n"
        f"📄 *Recibo y Factura Oficial (IGOR POS):*\n"
        f"Consulta tu factura real con todos tus datos aquí:\n"
        f"{url_real}\n\n"
        f"*Detalle de Consumo:*\n{detalle_items}"
        f"----------------------------------------\n"
        f"💰 *TOTAL:* ${total_venta:,.2f}\n\n"
        f"Gracias por su compra\nEquipo IGOR POS 🚀"
    )
    
    mensaje_codificado = urllib.parse.quote(mensaje, safe='')
    return f"https://api.whatsapp.com/send?phone={tel_limpio}&text={mensaje_codificado}"

@caja_mesas_bp.route('/admin/mesas', methods=['GET', 'POST'])
def gestionar_mesas():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
        
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    sincronizar_estados_mesas(cursor, conex, empresa_id)
    
    cursor.execute("SELECT id, monto_inicial FROM caja_diaria WHERE empresa_id = %s AND estado = 'Abierta' ORDER BY id DESC LIMIT 1;", (empresa_id,))
    caja_abierta = cursor.fetchone()
    rol_usuario = str(session.get('rol', 'Auxiliar')).lower()
    
    if not caja_abierta:
        cursor.close()
        conex.close()
        if rol_usuario in ['gerente', 'administrador', 'admin']:
            return redirect(url_for('caja_mesas.apertura_caja'))
        else:
            return render_template('acceso_restringido.html'), 403
            
    if request.method == 'POST':
        if rol_usuario not in ['gerente', 'administrador', 'admin']:
            cursor.close()
            conex.close()
            return redirect(url_for('caja_mesas.gestionar_mesas'))
        cantidad = request.form.get('cantidad')
        nombre_mesa = request.form.get('nombre_mesa')
        
        try:
            if nombre_mesa and nombre_mesa.strip() != "":
                cursor.execute(
                    "INSERT INTO mesas (empresa_id, numero_mesa, estado) VALUES (%s, %s, %s);",
                    (empresa_id, nombre_mesa.strip(), "Disponible")
                )
                conex.commit()
            elif cantidad and cantidad.isdigit():
                cant = int(cantidad)
                cursor.execute("SELECT COUNT(*) FROM mesas WHERE empresa_id = %s;", (empresa_id,))
                total_actuales = cursor.fetchone()[0]
                for i in range(1, cant + 1):
                    cursor.execute(
                        "INSERT INTO mesas (empresa_id, numero_mesa, estado) VALUES (%s, %s, %s);",
                        (empresa_id, f"Mesa {total_actuales + i}", "Disponible")
                    )
                conex.commit()
        except Exception as ex:
            conex.rollback()
            traceback.print_exc()
        cursor.close()
        conex.close()
        return redirect(url_for('caja_mesas.gestionar_mesas'))
        
    # CORRECCIÓN: Solo sumamos en el total acumulado de la mesa los productos que ya están COMANDADOS, LISTOS o ENTREGADOS.
    cursor.execute("""
        SELECT m.id, m.numero_mesa, m.estado, m.mesero_atendiendo,
               COALESCE(SUM(CASE WHEN p.estado IN ('Comandado', 'Listo', 'Entregado') THEN p.precio * p.cantidad ELSE 0 END), 0) AS total_acumulado
        FROM mesas m
        LEFT JOIN pedidos_mesa p ON m.id = p.id_mesa AND p.estado IN ('Comandado', 'Listo', 'Entregado')
        WHERE m.empresa_id = %s
        GROUP BY m.id, m.numero_mesa, m.estado, m.mesero_atendiendo
        ORDER BY m.id ASC;
    """, (empresa_id,))
    filas = cursor.fetchall()
    lista_mesas = []
    for fila in filas:
        lista_mesas.append({
            'id': fila[0],
            'numero_mesa': fila[1],
            'estado': fila[2],
            'mesero_atendiendo': fila[3] or 'Sin asignar',
            'total_acumulado': float(fila[4])
        })
    cursor.execute("SELECT id, numero_mesa, estado FROM mesas WHERE empresa_id = %s ORDER BY id ASC;", (empresa_id,))
    todas_las_mesas = cursor.fetchall()
    cursor.close()
    conex.close()
    
    usuario_actual = session.get('nombre', 'invitado')
    return render_template(
        'mesas.html',
        mesas=lista_mesas,
        todas_las_mesas=todas_las_mesas,
        rol_usuario=session.get('rol'),
        usuario_actual=usuario_actual,
        caja_abierta=caja_abierta
    )

@caja_mesas_bp.route('/admin/mesas/eliminar/<int:id_mesa>', methods=['POST'])
def eliminar_mesa(id_mesa):
    rol_usuario = str(session.get('rol', '')).lower()
    if rol_usuario not in ['gerente', 'administrador', 'admin']:
        flash('No tienes permisos para eliminar mesas.', 'danger')
        return redirect(url_for('caja_mesas.gestionar_mesas'))
    
    try:
        conex = get_db_connection()
        cursor = conex.cursor()
        asegurar_tablas_globales(cursor, conex)
        empresa_id = obtener_empresa_id_seguro(cursor)
        
        cursor.execute("SELECT estado FROM mesas WHERE id = %s AND empresa_id = %s;", (id_mesa, empresa_id))
        mesa_row = cursor.fetchone()
        if mesa_row:
            estado_mesa = mesa_row[0]
            if estado_mesa == 'Ocupada':
                flash('⚠️ No se puede eliminar una mesa que se encuentra ocupada.', 'danger')
            else:
                cursor.execute("DELETE FROM pedidos_mesa WHERE id_mesa = %s AND empresa_id = %s;", (id_mesa, empresa_id))
                cursor.execute("DELETE FROM mesas WHERE id = %s AND empresa_id = %s;", (id_mesa, empresa_id))
                conex.commit()
                flash('¡Mesa eliminada del sistema correctamente!', 'success')
        cursor.close()
        conex.close()
    except Exception as e:
        flash(f'Error al eliminar la mesa: {e}', 'danger')
        
    return redirect(url_for('caja_mesas.gestionar_mesas'))

@caja_mesas_bp.route('/admin/mesas/json-general')
def mesas_json_general():
    try:
        conex = get_db_connection()
        cursor = conex.cursor()
        asegurar_tablas_globales(cursor, conex)
        empresa_id = obtener_empresa_id_seguro(cursor)
        
        sincronizar_estados_mesas(cursor, conex, empresa_id)
        
        cursor.execute("""
            SELECT m.id, m.numero_mesa, m.estado, m.mesero_atendiendo,
                   COALESCE(SUM(CASE WHEN p.estado IN ('Comandado', 'Listo', 'Entregado') THEN p.precio * p.cantidad ELSE 0 END), 0) AS total_acumulado
            FROM mesas m
            LEFT JOIN pedidos_mesa p ON m.id = p.id_mesa AND p.estado IN ('Comandado', 'Listo', 'Entregado')
            WHERE m.empresa_id = %s
            GROUP BY m.id, m.numero_mesa, m.estado, m.mesero_atendiendo
            ORDER BY m.id ASC;
        """, (empresa_id,))
        filas = cursor.fetchall()
        cursor.close()
        conex.close()
        
        lista = []
        for f in filas:
            lista.append({
                'id': f[0],
                'numero_mesa': f[1],
                'estado': f[2],
                'mesero_atendiendo': f[3] or 'Sin asignar',
                'total_acumulado': float(f[4])
            })
        return jsonify(lista)
    except Exception as e:
        return jsonify([])

def cargar_productos_gerencia(cursor, conex, empresa_id):
    productos = []
    try:
        cursor.execute("SELECT id, nombre, precio, destino FROM productos WHERE empresa_id = %s ORDER BY id DESC;", (empresa_id,))
        filas = cursor.fetchall()
        for r in filas:
            p_id = r[0]
            p_nom = str(r[1]).strip() if r[1] is not None else ""
            if p_nom:
                try:
                    p_pre = float(r[2]) if r[2] is not None else 0.0
                except (ValueError, TypeError):
                    p_pre = 0.0
                
                p_des = str(r[3]).strip() if r[3] and str(r[3]).strip() != '' else 'Cocina'
                if p_des.lower() not in ['cocina', 'bar']:
                    p_des = 'Bar' if any(b in p_nom.lower() for b in ['gaseosa', 'bebida', 'cerveza', 'jugo', 'agua', 'refresco']) else 'Cocina'
                
                productos.append({
                    'id': p_id,
                    'nombre': p_nom,
                    'precio': p_pre,
                    'destino': p_des
                })
    except Exception as e:
        conex.rollback()
    return productos

@caja_mesas_bp.route('/admin/mesas/pedido/<int:id_mesa>', methods=['GET', 'POST'])
def abrir_pedido(id_mesa):
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
    rol_usuario = session.get('rol', 'Auxiliar')
    usuario_actual = session.get('nombre', 'Auxiliar')
    
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    cursor.execute("SELECT id FROM caja_diaria WHERE empresa_id = %s AND estado = 'Abierta' ORDER BY id DESC LIMIT 1;", (empresa_id,))
    caja_abierta = cursor.fetchone()
    if not caja_abierta:
        cursor.close()
        conex.close()
        return redirect(url_for('caja_mesas.gestionar_mesas'))
        
    productos_catalogo = cargar_productos_gerencia(cursor, conex, empresa_id)
    
    if request.method == 'POST' and 'agregar_producto' in request.form:
        producto_id = request.form.get('producto_id')
        cantidad = int(request.form.get('cantidad', 1))
        
        p_sel = next((p for p in productos_catalogo if str(p['id']) == str(producto_id)), None)
        if p_sel:
            p_nom, p_pre, p_des = p_sel['nombre'], p_sel['precio'], p_sel['destino']
            try:
                cursor.execute("""
                    SELECT id, cantidad FROM pedidos_mesa 
                    WHERE empresa_id = %s AND id_mesa = %s AND producto = %s AND estado = 'Pendiente';
                """, (empresa_id, id_mesa, p_nom))
                item_existente = cursor.fetchone()
                if item_existente:
                    nueva_cant = item_existente[1] + cantidad
                    cursor.execute("UPDATE pedidos_mesa SET cantidad = %s WHERE id = %s AND empresa_id = %s;", (nueva_cant, item_existente[0], empresa_id))
                else:
                    cursor.execute("""
                        INSERT INTO pedidos_mesa (empresa_id, id_mesa, producto, precio, cantidad, estado, destino, fecha_comandado)
                        VALUES (%s, %s, %s, %s, %s, 'Pendiente', %s, NOW());
                    """, (empresa_id, id_mesa, p_nom, p_pre, cantidad, p_des))
                conex.commit()
            except Exception as e:
                conex.rollback()
                
    if request.method == 'POST' and 'enviar_comanda' in request.form:
        try:
            cursor.execute("""
                UPDATE pedidos_mesa 
                SET estado = 'Comandado', fecha_comandado = NOW() 
                WHERE empresa_id = %s AND id_mesa = %s AND estado = 'Pendiente';
            """, (empresa_id, id_mesa))
            cursor.execute("UPDATE mesas SET estado = 'Ocupada', mesero_atendiendo = %s WHERE id = %s AND empresa_id = %s;", (f"{usuario_actual} ({rol_usuario})", id_mesa, empresa_id))
            conex.commit()
        except Exception:
            conex.rollback()
            
    if request.method == 'POST' and 'guardar_olvido' in request.form:
        try:
            cursor.execute("""
                UPDATE pedidos_mesa 
                SET estado = 'Entregado', fecha_comandado = NOW() 
                WHERE empresa_id = %s AND id_mesa = %s AND estado = 'Pendiente';
            """, (empresa_id, id_mesa))
            cursor.execute("UPDATE mesas SET estado = 'Ocupada', mesero_atendiendo = %s WHERE id = %s AND empresa_id = %s;", (f"{usuario_actual} ({rol_usuario})", id_mesa, empresa_id))
            conex.commit()
        except Exception:
            conex.rollback()
            
    sincronizar_estados_mesas(cursor, conex, empresa_id)
        
    cursor.execute("SELECT id, numero_mesa, estado, mesero_atendiendo FROM mesas WHERE id = %s AND empresa_id = %s;", (id_mesa, empresa_id))
    mesa_data = cursor.fetchone()
    if not mesa_data:
        cursor.close()
        conex.close()
        return redirect(url_for('caja_mesas.gestionar_mesas'))
        
    mesa = {
        'id': mesa_data[0],
        'numero_mesa': mesa_data[1],
        'estado': mesa_data[2],
        'mesero_atendiendo': mesa_data[3] or 'Sin asignar'
    }
    cursor.execute("SELECT id, numero_mesa, estado FROM mesas WHERE empresa_id = %s ORDER BY id ASC;", (empresa_id,))
    todas_las_mesas = cursor.fetchall()
    
    cursor.execute("""
        SELECT id, producto, precio, cantidad, (precio * cantidad) as subtotal, estado, destino
        FROM pedidos_mesa
        WHERE empresa_id = %s AND id_mesa = %s AND estado IN ('Pendiente', 'Comandado', 'Listo', 'Entregado')
        ORDER BY id ASC;
    """, (empresa_id, id_mesa))
    pedidos_raw = cursor.fetchall()
    
    pedidos = []
    total_acumulado = 0
    hay_pendientes_comandar = False
    for p in pedidos_raw:
        subtotal = float(p[4])
        if p[5] in ['Pendiente', 'Comandado', 'Listo', 'Entregado']:
            total_acumulado += subtotal
        if str(p[5]).strip().lower() == 'pendiente':
            hay_pendientes_comandar = True
        pedidos.append({
            'id': p[0],
            'producto': p[1],
            'precio': float(p[2]),
            'cantidad': p[3],
            'subtotal': subtotal,
            'estado': p[5],
            'destino': p[6]
        })
    cursor.close()
    conex.close()
    
    return render_template(
        'pedido_mesa.html',
        mesa=mesa,
        pedidos=pedidos,
        catalogo=productos_catalogo,
        todas_las_mesas=todas_las_mesas,
        total=total_acumulado,
        hay_pendientes=hay_pendientes_comandar,
        rol_usuario=rol_usuario,
        caja_abierta=caja_abierta
    )

@caja_mesas_bp.route('/admin/mesas/pedido/vaciar/<int:id_mesa>', methods=['POST'])
def vaciar_mesa(id_mesa):
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
        
    try:
        conex = get_db_connection()
        cursor = conex.cursor()
        asegurar_tablas_globales(cursor, conex)
        empresa_id = obtener_empresa_id_seguro(cursor)
        
        cursor.execute("DELETE FROM pedidos_mesa WHERE id_mesa = %s AND empresa_id = %s;", (id_mesa, empresa_id))
        cursor.execute("UPDATE mesas SET estado = 'Disponible', mesero_atendiendo = 'Sin asignar' WHERE id = %s AND empresa_id = %s;", (id_mesa, empresa_id))
        
        conex.commit()
        cursor.close()
        conex.close()
        flash('🧹 Mesa vaciada y liberada correctamente. Se borraron los consumos sin registrar en caja.', 'success')
    except Exception as e:
        flash(f'❌ Error al vaciar la mesa: {e}', 'danger')
        
    return redirect(url_for('caja_mesas.abrir_pedido', id_mesa=id_mesa))

@caja_mesas_bp.route('/admin/productos/eliminar/<int:id_producto>', methods=['POST'])
def eliminar_producto_catalogo(id_producto):
    rol_usuario = str(session.get('rol', '')).lower()
    if rol_usuario not in ['gerente', 'administrador', 'admin']:
        flash('No tienes permisos para eliminar productos.', 'danger')
        return redirect('/admin/productos')
    
    try:
        conex = get_db_connection()
        cursor = conex.cursor()
        asegurar_tablas_globales(cursor, conex)
        empresa_id = obtener_empresa_id_seguro(cursor)
        
        cursor.execute("DELETE FROM productos WHERE id = %s AND empresa_id = %s;", (id_producto, empresa_id))
        conex.commit()
        cursor.close()
        conex.close()
        flash('¡Producto eliminado del catálogo correctamente!', 'success')
    except Exception as e:
        flash(f'Error al eliminar el producto: {e}', 'danger')
        
    return redirect('/admin/productos')

@caja_mesas_bp.route('/admin/mesas/json/<int:id_mesa>')
def obtener_pedido_json(id_mesa):
    try:
        conex = get_db_connection()
        cursor = conex.cursor()
        asegurar_tablas_globales(cursor, conex)
        empresa_id = obtener_empresa_id_seguro(cursor)
        
        sincronizar_estados_mesas(cursor, conex, empresa_id)
        
        cursor.execute("""
            SELECT id, producto, precio, cantidad, (precio * cantidad) as subtotal, estado, destino
            FROM pedidos_mesa
            WHERE empresa_id = %s AND id_mesa = %s AND estado IN ('Pendiente', 'Comandado', 'Listo', 'Entregado')
            ORDER BY id ASC;
        """, (empresa_id, id_mesa))
        pedidos_raw = cursor.fetchall()
        cursor.close()
        conex.close()
        
        pedidos = []
        total = 0
        for p in pedidos_raw:
            sub = float(p[4])
            if p[5] in ['Pendiente', 'Comandado', 'Listo', 'Entregado']:
                total += sub
            pedidos.append({
                'id': p[0], 'producto': p[1], 'precio': float(p[2]),
                'cantidad': p[3], 'subtotal': sub, 'estado': p[5], 'destino': p[6]
            })
        return jsonify({'pedidos': pedidos, 'total': total})
    except Exception as e:
        return jsonify({'pedidos': [], 'total': 0})

@caja_mesas_bp.route('/admin/mesas/pedido/aumentar/<int:id_item>', methods=['POST'])
def aumentar_cantidad(id_item):
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    cursor.execute("SELECT id FROM caja_diaria WHERE empresa_id = %s AND estado = 'Abierta' ORDER BY id DESC LIMIT 1;", (empresa_id,))
    if not cursor.fetchone():
        cursor.close()
        conex.close()
        return redirect(url_for('caja_mesas.gestionar_mesas'))
    cursor.execute("SELECT id_mesa, cantidad FROM pedidos_mesa WHERE id = %s AND empresa_id = %s;", (id_item, empresa_id))
    row = cursor.fetchone()
    if row:
        id_mesa, cantidad = row[0], row[1]
        cursor.execute("UPDATE pedidos_mesa SET cantidad = %s WHERE id = %s AND empresa_id = %s;", (cantidad + 1, id_item, empresa_id))
        conex.commit()
    cursor.close()
    conex.close()
    return redirect(url_for('caja_mesas.abrir_pedido', id_mesa=id_mesa))

@caja_mesas_bp.route('/admin/mesas/pedido/disminuir/<int:id_item>', methods=['POST'])
def disminuir_cantidad(id_item):
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    cursor.execute("SELECT id FROM caja_diaria WHERE empresa_id = %s AND estado = 'Abierta' ORDER BY id DESC LIMIT 1;", (empresa_id,))
    if not cursor.fetchone():
        cursor.close()
        conex.close()
        return redirect(url_for('caja_mesas.gestionar_mesas'))
    cursor.execute("SELECT id_mesa, cantidad FROM pedidos_mesa WHERE id = %s AND empresa_id = %s;", (id_item, empresa_id))
    row = cursor.fetchone()
    if row:
        id_mesa, cantidad = row[0], row[1]
        if cantidad > 1:
            cursor.execute("UPDATE pedidos_mesa SET cantidad = %s WHERE id = %s AND empresa_id = %s;", (cantidad - 1, id_item, empresa_id))
        else:
            cursor.execute("DELETE FROM pedidos_mesa WHERE id = %s AND empresa_id = %s;", (id_item, empresa_id))
        conex.commit()
        
        sincronizar_estados_mesas(cursor, conex, empresa_id)
        
    cursor.close()
    conex.close()
    return redirect(url_for('caja_mesas.abrir_pedido', id_mesa=id_mesa))

@caja_mesas_bp.route('/admin/mesas/pedido/eliminar-item/<int:id_item>', methods=['POST'])
def eliminar_item(id_item):
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    cursor.execute("SELECT id_mesa FROM pedidos_mesa WHERE id = %s AND empresa_id = %s;", (id_item, empresa_id))
    row = cursor.fetchone()
    if row:
        id_mesa = row[0]
        cursor.execute("DELETE FROM pedidos_mesa WHERE id = %s AND empresa_id = %s;", (id_item, empresa_id))
        conex.commit()
        
        sincronizar_estados_mesas(cursor, conex, empresa_id)
    cursor.close()
    conex.close()
    return redirect(url_for('caja_mesas.abrir_pedido', id_mesa=id_mesa))

@caja_mesas_bp.route('/admin/mesas/cambiar/<int:id_mesa_origen>', methods=['POST'])
def cambiar_mesa(id_mesa_origen):
    id_mesa_destino = request.form.get('id_mesa_destino')
    if not id_mesa_destino:
        return redirect(url_for('caja_mesas.abrir_pedido', id_mesa=id_mesa_origen))
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    cursor.execute("""
        SELECT m.id, m.estado, COALESCE(SUM(p.precio * p.cantidad), 0) 
        FROM mesas m 
        LEFT JOIN pedidos_mesa p ON m.id = p.id_mesa AND p.estado IN ('Pendiente', 'Comandado', 'Listo', 'Entregado')
        WHERE m.id = %s AND m.empresa_id = %s
        GROUP BY m.id, m.estado;
    """, (id_mesa_destino, empresa_id))
    destino_data = cursor.fetchone()
    if destino_data and (destino_data[1] == 'Disponible' and float(destino_data[2]) == 0):
        cursor.execute("SELECT mesero_atendiendo FROM mesas WHERE id = %s AND empresa_id = %s;", (id_mesa_origen, empresa_id))
        mesero_orig = cursor.fetchone()[0]
        cursor.execute("UPDATE pedidos_mesa SET id_mesa = %s WHERE id_mesa = %s AND empresa_id = %s;", (id_mesa_destino, id_mesa_origen, empresa_id))
        cursor.execute("UPDATE mesas SET estado = 'Ocupada', mesero_atendiendo = %s WHERE id = %s AND empresa_id = %s;", (mesero_orig, id_mesa_destino, empresa_id))
        cursor.execute("UPDATE mesas SET estado = 'Disponible', mesero_atendiendo = 'Sin asignar' WHERE id = %s AND empresa_id = %s;", (id_mesa_origen, empresa_id))
        conex.commit()
    cursor.close()
    conex.close()
    return redirect(url_for('caja_mesas.abrir_pedido', id_mesa=id_mesa_destino))

@caja_mesas_bp.route('/admin/mesas/cerrar/<int:id_mesa>', methods=['POST'])
def cerrar_facturar_mesa(id_mesa):
    rol_usuario = str(session.get('rol', '')).lower()
    roles_permitidos = ['gerente', 'administrador', 'admin']
    if rol_usuario not in roles_permitidos:
        flash('⚠️ No tienes permisos de gerencia o administración para cobrar o facturar mesas.', 'danger')
        return render_template('acceso_restringido.html'), 403
        
    tipo_pago = request.form.get('tipo_pago', 'Efectivo')
    efectivo_recibido = float(request.form.get('efectivo_recibido', 0))
    
    desea_factura_impresa = request.form.get('desea_factura_impresa') == 'si'
    es_electronica = request.form.get('es_electronica') == 'si'
    
    cliente_nombre = request.form.get('cliente_nombre', '').strip()
    cliente_nit = request.form.get('cliente_nit', '').strip()
    cliente_telefono = request.form.get('cliente_telefono', '').strip()
    
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    cursor.execute("""
        SELECT COALESCE(SUM(precio * cantidad), 0) FROM pedidos_mesa 
        WHERE empresa_id = %s AND id_mesa = %s AND estado IN ('Pendiente', 'Comandado', 'Listo', 'Entregado');
    """, (empresa_id, id_mesa))
    total_venta = float(cursor.fetchone()[0])
    if total_venta == 0:
        cursor.close()
        conex.close()
        return redirect(url_for('caja_mesas.gestionar_mesas'))
        
    devueltas = max(0.0, efectivo_recibido - total_venta)
    cursor.execute("SELECT numero_mesa, mesero_atendiendo FROM mesas WHERE id = %s AND empresa_id = %s;", (id_mesa, empresa_id))
    datos_mesa = cursor.fetchone()
    num_mesa_str = datos_mesa[0]
    
    usuario_sesion = session.get('nombre') or session.get('usuario') or 'igor (gerente)'
    mesero_atendio = datos_mesa[1]
    if not mesero_atendio or mesero_atendio.strip() == '' or mesero_atendio == 'Sin asignar':
        mesero_atendio = usuario_sesion
    
    cursor.execute("""
        INSERT INTO historial_ventas (empresa_id, id_mesa, numero_mesa, total_venta, tipo_pago, efectivo_recibido, devueltas, atendido_por, fecha_venta)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW()) RETURNING id;
    """, (empresa_id, id_mesa, num_mesa_str, total_venta, tipo_pago, efectivo_recibido, devueltas, mesero_atendio))
    id_venta = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT producto, cantidad, (precio * cantidad) FROM pedidos_mesa 
        WHERE empresa_id = %s AND id_mesa = %s AND estado IN ('Pendiente', 'Comandado', 'Listo', 'Entregado');
    """, (empresa_id, id_mesa))
    items_raw = cursor.fetchall()
    items_lista = [{'producto': r[0], 'cantidad': r[1], 'subtotal': float(r[2])} for r in items_raw]
    
    base_url = request.host_url.rstrip('/')
    if "onrender.com" not in base_url and "localhost" not in base_url:
        base_url = "https://igorpos.onrender.com"
    url_real_render = f"{base_url}/admin/verificar-factura/{id_venta}"
    
    dian_result = {
        'exito': True,
        'numero_factura': f"FE-{id_venta}",
        'url_factura': url_real_render
    }
    
    link_wa = None
    if cliente_telefono:
        link_wa = generar_enlace_whatsapp(
            cliente_telefono, 
            cliente_nombre, 
            cliente_nit,
            id_venta, 
            total_venta, 
            num_mesa_str, 
            items_lista, 
            url_documento=url_real_render
        )
        
    cursor.execute("""
        UPDATE pedidos_mesa 
        SET estado = 'Facturado', id_venta_asociada = %s 
        WHERE empresa_id = %s AND id_mesa = %s AND estado IN ('Pendiente', 'Comandado', 'Listo', 'Entregado');
    """, (id_venta, empresa_id, id_mesa))
    cursor.execute("UPDATE mesas SET estado = 'Disponible', mesero_atendiendo = 'Sin asignar' WHERE id = %s AND empresa_id = %s;", (id_mesa, empresa_id))
    conex.commit()
    cursor.close()
    conex.close()
    
    session['dian_result_temp'] = dian_result
    if link_wa:
        return redirect(url_for('caja_mesas.imprimir_ticket', id_venta=id_venta, link_wa=link_wa))
        
    return redirect(url_for('caja_mesas.imprimir_ticket', id_venta=id_venta))

@caja_mesas_bp.route('/admin/caja/apertura', methods=['GET', 'POST'])
def apertura_caja():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
    rol_usuario = str(session.get('rol', '')).lower()
    roles_permitidos = ['gerente', 'administrador', 'admin']
    if rol_usuario not in roles_permitidos:
        return render_template('acceso_restringido.html'), 403
        
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        if accion == 'abrir':
            monto_inicial = float(request.form.get('monto_inicial', 0))
            usuario_actual = session.get('nombre', 'Administrador')
            cursor.execute("""
                INSERT INTO caja_diaria (empresa_id, monto_inicial, estado, fecha_apertura, usuario_apertura)
                VALUES (%s, %s, 'Abierta', NOW(), %s);
            """, (empresa_id, monto_inicial, usuario_actual))
            conex.commit()
        elif accion == 'cerrar':
            id_caja = request.form.get('id_caja')
            usuario_actual = session.get('nombre', 'Administrador')
            cursor.execute("""
                SELECT DISTINCT m.numero_mesa FROM mesas m
                LEFT JOIN pedidos_mesa p ON m.id = p.id_mesa AND p.estado IN ('Pendiente', 'Comandado', 'Listo', 'Entregado')
                WHERE m.empresa_id = %s AND (m.estado != 'Disponible' OR p.id IS NOT NULL);
            """, (empresa_id,))
            mesas_activas_raw = cursor.fetchall()
            if len(mesas_activas_raw) > 0:
                nombres_mesas = ", ".join([str(m[0]) for m in mesas_activas_raw])
                cursor.close()
                conex.close()
                flash(f'⚠️ ¡No se puede cerrar la caja! Mesas ocupadas: [{nombres_mesas}].', 'danger')
                return redirect(url_for('caja_mesas.apertura_caja'))
                
            cursor.execute("SELECT fecha_apertura, monto_inicial FROM caja_diaria WHERE id = %s AND empresa_id = %s;", (id_caja, empresa_id))
            caja_info = cursor.fetchone()
            if caja_info:
                fecha_ap = caja_info[0]
                monto_ini = float(caja_info[1])
                cursor.execute("""
                    SELECT COALESCE(SUM(total_venta), 0) 
                    FROM historial_ventas 
                    WHERE empresa_id = %s AND fecha_venta >= %s;
                """, (empresa_id, fecha_ap))
                ventas_turno = float(cursor.fetchone()[0])
                monto_final_calc = monto_ini + ventas_turno
                cursor.execute("""
                    UPDATE caja_diaria 
                    SET estado = 'Cerrada', fecha_cierre = NOW(), total_ventas = %s, monto_final = %s, usuario_cierre = %s
                    WHERE id = %s AND empresa_id = %s;
                """, (ventas_turno, monto_final_calc, usuario_actual, id_caja, empresa_id))
                conex.commit()
                flash('¡Caja cerrada con éxito!', 'success')
        cursor.close()
        conex.close()
        return redirect(url_for('caja_mesas.apertura_caja'))
        
    cursor.execute("SELECT id, monto_inicial, fecha_apertura, usuario_apertura FROM caja_diaria WHERE empresa_id = %s AND estado = 'Abierta' ORDER BY id DESC LIMIT 1;", (empresa_id,))
    caja_raw = cursor.fetchone()
    caja_abierta = None
    ventas_del_turno = 0
    monto_total_estimado = 0
    rendimiento_personal = []
    
    if caja_raw:
        caja_id = caja_raw[0]
        monto_ini = float(caja_raw[1])
        fecha_ap = caja_raw[2]
        user_ap = caja_raw[3]
        cursor.execute("""
            SELECT COALESCE(SUM(total_venta), 0) 
            FROM historial_ventas 
            WHERE empresa_id = %s AND fecha_venta >= %s;
        """, (empresa_id, fecha_ap))
        ventas_del_turno = float(cursor.fetchone()[0])
        monto_total_estimado = monto_ini + ventas_del_turno
        caja_abierta = {
            'id': caja_id,
            'monto_inicial': monto_ini,
            'fecha_apertura': fecha_ap,
            'usuario_apertura': user_ap,
            'ventas_del_turno': ventas_del_turno,
            'monto_total_estimado': monto_total_estimado
        }
        
        cursor.execute("""
            SELECT atendido_por, COUNT(id) as total_mesas_atendidas, SUM(total_venta) as total_vendido
            FROM historial_ventas
            WHERE empresa_id = %s AND fecha_venta >= %s 
              AND atendido_por IS NOT NULL 
              AND TRIM(atendido_por) != '' 
              AND atendido_por != 'Sin asignar'
              AND atendido_por != 'Ventas Directas de Caja'
            GROUP BY atendido_por
            ORDER BY total_vendido DESC;
        """, (empresa_id, fecha_ap))
        filas_r = cursor.fetchall()
        for r in filas_r:
            rendimiento_personal.append({
                'empleado': r[0],
                'mesas_atendidas': r[1],
                'total_vendido': float(r[2])
            })
            
    cursor.execute("""
        SELECT id, monto_inicial, total_ventas, monto_final, fecha_apertura, fecha_cierre, usuario_apertura, usuario_cierre
        FROM caja_diaria 
        WHERE empresa_id = %s AND estado = 'Cerrada'
        ORDER BY id DESC LIMIT 10;
    """, (empresa_id,))
    historial_cajas = cursor.fetchall()
    cursor.close()
    conex.close()
    
    return render_template(
        'apertura_caja.html',
        caja_abierta=caja_abierta,
        historial_cajas=historial_cajas,
        rendimiento_personal=rendimiento_personal,
        rol_usuario=session.get('rol')
    )

@caja_mesas_bp.route('/admin/sistema/reset-emergencia', methods=['POST'])
def reset_emergencia():
    rol_usuario = str(session.get('rol', '')).lower()
    if rol_usuario not in ['gerente', 'administrador', 'admin']:
        return render_template('acceso_restringido.html'), 403
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')
    tipo_reseteo = request.form.get('tipo_reseteo', 'todo')
    try:
        conex = get_db_connection()
        cursor = conex.cursor()
        asegurar_tablas_globales(cursor, conex)
        empresa_id = obtener_empresa_id_seguro(cursor)
        
        if tipo_reseteo == 'rango' and fecha_inicio and fecha_fin:
            cursor.execute("""
                DELETE FROM historial_ventas 
                WHERE empresa_id = %s AND fecha_venta >= %s AND fecha_venta <= %s::timestamp + INTERVAL '1 day' - INTERVAL '1 second';
            """, (empresa_id, fecha_inicio, fecha_fin))
            cursor.execute("""
                DELETE FROM pedidos_mesa 
                WHERE empresa_id = %s AND estado = 'Facturado' AND id_venta_asociada NOT IN (SELECT id FROM historial_ventas WHERE empresa_id = %s);
            """, (empresa_id, empresa_id))
            flash(f'⚡ Registros purgados con éxito.', 'success')
        else:
            cursor.execute("DELETE FROM pedidos_mesa WHERE empresa_id = %s;", (empresa_id,))
            cursor.execute("DELETE FROM historial_ventas WHERE empresa_id = %s;", (empresa_id,))
            cursor.execute("UPDATE caja_diaria SET estado = 'Cerrada' WHERE empresa_id = %s AND estado = 'Abierta';", (empresa_id,))
            cursor.execute("UPDATE mesas SET estado = 'Disponible', mesero_atendiendo = 'Sin asignar' WHERE empresa_id = %s;", (empresa_id,))
            flash('⚡ ¡Sistema reiniciado con éxito!', 'success')
        conex.commit()
        cursor.close()
        conex.close()
    except Exception as e:
        flash(f'❌ Error: {e}', 'danger')
    return redirect(url_for('caja_mesas.apertura_caja'))

@caja_mesas_bp.route('/admin/imprimir-ticket/<int:id_venta>')
def imprimir_ticket(id_venta):
    link_wa = request.args.get('link_wa')
    factura_electronica = session.pop('dian_result_temp', None)
    
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    empresa_id = obtener_empresa_id_seguro(cursor)
    
    cursor.execute("""
        SELECT id, numero_mesa, total_venta, tipo_pago, efectivo_recibido, devueltas, atendido_por, fecha_venta, id_mesa
        FROM historial_ventas WHERE id = %s AND empresa_id = %s;
    """, (id_venta, empresa_id))
    v = cursor.fetchone()
    if not v:
        cursor.close()
        conex.close()
        return "Venta no encontrada", 404
    venta = {
        'id': v[0],
        'numero_mesa': v[1],
        'total_venta': float(v[2]),
        'tipo_pago': v[3],
        'efectivo_recibido': float(v[4]),
        'devueltas': float(v[5]),
        'atendido_por': v[6],
        'fecha_venta': v[7]
    }
    cursor.execute("""
        SELECT producto, SUM(cantidad) as total_cantidad, precio, SUM(precio * cantidad) as subtotal
        FROM pedidos_mesa 
        WHERE id_venta_asociada = %s AND empresa_id = %s
        GROUP BY producto, precio
        ORDER BY producto ASC;
    """, (id_venta, empresa_id))
    items_raw = cursor.fetchall()
    if not items_raw:
        cursor.execute("""
            SELECT producto, SUM(cantidad) as total_cantidad, precio, SUM(precio * cantidad) as subtotal
            FROM pedidos_mesa 
            WHERE id_mesa = %s AND estado = 'Facturado' AND empresa_id = %s
            GROUP BY producto, precio
            ORDER BY producto ASC;
        """, (v[8], empresa_id))
        items_raw = cursor.fetchall()
    items = []
    for it in items_raw:
        items.append({
            'producto': it[0],
            'cantidad': int(it[1]),
            'precio': float(it[2]),
            'subtotal': float(it[3])
        })
    cursor.close()
    conex.close()
    
    base_url = request.host_url.rstrip('/')
    if "onrender.com" not in base_url and "localhost" not in base_url:
        base_url = "https://igorpos.onrender.com"
    url_qr = f"{base_url}/admin/verificar-factura/{id_venta}"
    
    return render_template(
        'ticket_factura.html', 
        venta=venta, 
        items=items, 
        url_qr=url_qr, 
        link_wa=link_wa,
        factura_electronica=factura_electronica
    )

@caja_mesas_bp.route('/admin/verificar-factura/<int:id_venta>')
def verificar_factura_qr(id_venta):
    conex = get_db_connection()
    cursor = conex.cursor()
    asegurar_tablas_globales(cursor, conex)
    
    cursor.execute("""
        SELECT id, numero_mesa, total_venta, tipo_pago, efectivo_recibido, devueltas, atendido_por, fecha_venta, empresa_id
        FROM historial_ventas WHERE id = %s;
    """, (id_venta,))
    v = cursor.fetchone()
    if not v:
        cursor.close()
        conex.close()
        return render_template('acceso_restringido.html'), 404
        
    venta = {
        'id': v[0],
        'numero_mesa': v[1],
        'total_venta': float(v[2]),
        'tipo_pago': v[3],
        'efectivo_recibido': float(v[4]),
        'devueltas': float(v[5]),
        'atendido_por': v[6],
        'fecha_venta': v[7]
    }
    
    cursor.execute("""
        SELECT producto, cantidad, precio, (precio * cantidad) as subtotal
        FROM pedidos_mesa 
        WHERE id_venta_asociada = %s;
    """, (id_venta,))
    items_raw = cursor.fetchall()
    items = [{'producto': i[0], 'cantidad': i[1], 'precio': float(i[2]), 'subtotal': float(i[3])} for i in items_raw]
    
    cursor.close()
    conex.close()
    
    return render_template('verificar_factura.html', venta=venta, items=items)