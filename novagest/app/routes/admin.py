from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
import psycopg

admin_bp = Blueprint('admin', __name__)

# Conectado formalmente a novagest_db
DB_CONFIG = "dbname=novagest_db user=postgres password=Novagest2026 host=localhost"

def asegurar_tabla_empresas(cursor, conex):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(150) NOT NULL
        );
    """)
    conex.commit()

def asegurar_tabla_productos(cursor, conex):
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
    cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS empresa_id INT;")
    cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS destino VARCHAR(50) DEFAULT 'Cocina';")
    cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock INT DEFAULT 0;")
    cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS categoria VARCHAR(100) DEFAULT 'General';")
    cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS descripcion TEXT;")
    conex.commit()

def asegurar_tabla_usuarios(cursor, conex):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            empresa_id INT,
            nombre VARCHAR(150) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255),
            rol VARCHAR(50) DEFAULT 'Auxiliar de Servicio',
            usuario VARCHAR(150)
        );
    """)
    cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS empresa_id INT;")
    cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS nombre VARCHAR(150);")
    cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email VARCHAR(150);")
    cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password VARCHAR(255);")
    cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);")
    cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rol VARCHAR(50) DEFAULT 'Auxiliar de Servicio';")
    cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS usuario VARCHAR(150);")
    conex.commit()

# --- RUTA PRINCIPAL /admin ---
@admin_bp.route('/admin')
def admin_root():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
    return render_template('admin.html', seccion='dashboard')

# --- PANEL PRINCIPAL (DASHBOARD) ---
@admin_bp.route('/admin/dashboard')
def dashboard():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
    return render_template('admin.html', seccion='dashboard')

# --- NUEVA RUTA DE PLANES Y SUSCRIPCIÓN (Exclusivo Gerente) ---
@admin_bp.route('/admin/planes')
def planes():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    rol_usuario = str(session.get('rol', '')).lower()
    if rol_usuario not in ['gerente', 'administrador', 'admin']:
        return render_template('acceso_restringido.html'), 403
        
    return render_template('planes_pago.html')

# --- GESTIÓN DE PRODUCTOS (Aislados por empresa_id) ---
@admin_bp.route('/admin/productos', methods=['GET', 'POST'])
def productos():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    rol_usuario = str(session.get('rol', '')).lower()
    if rol_usuario not in ['gerente', 'administrador', 'admin']:
        return render_template('acceso_restringido.html'), 403
    
    empresa_id = session.get('empresa_id') or user_id
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        precio_raw = request.form.get('precio', 0)
        stock_raw = request.form.get('stock', 0)
        categoria = request.form.get('categoria', 'General').strip() or 'General'
        destino = request.form.get('destino', 'Cocina').strip() or 'Cocina'
        descripcion = request.form.get('descripcion', '').strip()
        
        try:
            precio = float(precio_raw) if precio_raw else 0.0
        except (ValueError, TypeError):
            precio = 0.0
            
        try:
            stock = int(stock_raw) if stock_raw else 0
        except (ValueError, TypeError):
            stock = 0
            
        if nombre:
            try:
                conex = psycopg.connect(DB_CONFIG)
                with conex.cursor() as cursor:
                    asegurar_tabla_empresas(cursor, conex)
                    asegurar_tabla_productos(cursor, conex)
                    
                    cursor.execute("""
                        INSERT INTO productos (empresa_id, nombre, precio, stock, categoria, destino, descripcion)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (empresa_id, nombre, precio, stock, categoria, destino, descripcion))
                    conex.commit()
                conex.close()
                flash('¡Producto guardado con éxito!', 'success')
            except Exception as e:
                flash(f'Error al guardar producto: {e}', 'danger')
        return redirect(url_for('admin.productos'))
        
    lista_productos = []
    try:
        conex = psycopg.connect(DB_CONFIG)
        with conex.cursor() as cursor:
            asegurar_tabla_empresas(cursor, conex)
            asegurar_tabla_productos(cursor, conex)
            cursor.execute("""
                SELECT id, nombre, precio, stock, categoria, destino, descripcion 
                FROM productos 
                WHERE empresa_id = %s
                ORDER BY id DESC;
            """, (empresa_id,))
            lista_productos = cursor.fetchall()
        conex.close()
    except Exception as e:
        print(f"Error al consultar productos: {e}")
        
    return render_template('admin.html', productos=lista_productos, seccion='productos')

# --- MODIFICAR STOCK RÁPIDO (+ / -) con seguridad de empresa ---
@admin_bp.route('/admin/productos/stock/<int:producto_id>/<string:accion>', methods=['POST'])
def modificar_stock(producto_id, accion):
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    rol_usuario = str(session.get('rol', '')).lower()
    if rol_usuario not in ['gerente', 'administrador', 'admin']:
        flash('No tienes permisos para modificar inventario.', 'danger')
        return redirect(url_for('admin.productos'))
    
    empresa_id = session.get('empresa_id') or user_id
    
    try:
        conex = psycopg.connect(DB_CONFIG)
        with conex.cursor() as cursor:
            cursor.execute("SELECT stock FROM productos WHERE id = %s AND empresa_id = %s;", (producto_id, empresa_id))
            row = cursor.fetchone()
            if row:
                stock_actual = row[0] or 0
                if accion == 'mas':
                    nuevo_stock = stock_actual + 1
                elif accion == 'menos':
                    nuevo_stock = max(0, stock_actual - 1)
                else:
                    nuevo_stock = stock_actual
                
                cursor.execute("UPDATE productos SET stock = %s WHERE id = %s AND empresa_id = %s;", (nuevo_stock, producto_id, empresa_id))
                conex.commit()
        conex.close()
    except Exception as e:
        print(f"Error al modificar stock: {e}")
        
    return redirect(url_for('admin.productos'))

# --- ELIMINAR O DAR DE BAJA PRODUCTO (Aislado por empresa) ---
@admin_bp.route('/admin/productos/eliminar/<int:producto_id>', methods=['POST'])
def eliminar_producto(producto_id):
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
    
    rol_usuario = str(session.get('rol', '')).lower()
    if rol_usuario not in ['gerente', 'administrador', 'admin']:
        flash('No tienes permisos para eliminar productos.', 'danger')
        return redirect(url_for('admin.productos'))
        
    empresa_id = session.get('empresa_id') or user_id
    
    try:
        conex = psycopg.connect(DB_CONFIG)
        with conex.cursor() as cursor:
            cursor.execute("DELETE FROM productos WHERE id = %s AND empresa_id = %s;", (producto_id, empresa_id))
            conex.commit()
        conex.close()
        flash('¡Producto eliminado con éxito!', 'success')
    except Exception as e:
        flash(f'Error al eliminar producto: {e}', 'danger')
        
    return redirect(url_for('admin.productos'))

# --- GESTIÓN DE USUARIOS / PERSONAL (Aislados por empresa del Gerente) ---
@admin_bp.route('/admin/usuarios', methods=['GET', 'POST'])
def usuarios():
    user_id = session.get('usuario_id') or session.get('user_id')
    if not user_id:
        return redirect('/login')
        
    rol_usuario = str(session.get('rol', '')).lower()
    if rol_usuario not in ['gerente', 'administrador', 'admin']:
        return render_template('acceso_restringido.html'), 403
        
    empresa_id = session.get('empresa_id') or user_id
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        rol = request.form.get('rol', 'Auxiliar de Servicio').strip()
        
        if nombre and email and password:
            try:
                conex = psycopg.connect(DB_CONFIG)
                with conex.cursor() as cursor:
                    asegurar_tabla_empresas(cursor, conex)
                    asegurar_tabla_usuarios(cursor, conex)
                    
                    # 🛑 Validación anti-duplicados para el personal interno
                    cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s);", (email,))
                    usuario_existente = cursor.fetchone()
                    
                    if usuario_existente:
                        flash(f"⚠️ El correo '{email}' ya se encuentra registrado en el sistema.", 'danger')
                    else:
                        password_hash = generate_password_hash(password)
                        cursor.execute("""
                            INSERT INTO usuarios (empresa_id, nombre, email, password, password_hash, rol, usuario)
                            VALUES (%s, %s, %s, %s, %s, %s, %s);
                        """, (empresa_id, nombre, email, password, password_hash, rol, email))
                        conex.commit()
                        flash('¡Usuario creado con éxito y asociado à tu empresa!', 'success')
                conex.close()
            except Exception as e:
                flash(f'Error al crear usuario: {e}', 'danger')
        return redirect(url_for('admin.usuarios'))
        
    lista_usuarios = []
    try:
        conex = psycopg.connect(DB_CONFIG)
        with conex.cursor() as cursor:
            asegurar_tabla_empresas(cursor, conex)
            asegurar_tabla_usuarios(cursor, conex)
            cursor.execute("""
                SELECT id, nombre, email, rol 
                FROM usuarios 
                WHERE empresa_id = %s
                ORDER BY id DESC;
            """, (empresa_id,))
            lista_usuarios = cursor.fetchall()
        conex.close()
    except Exception as e:
        print(f"Error al consultar usuarios: {e}")
        
    return render_template('admin.html', usuarios=lista_usuarios, seccion='usuarios')

# --- REDIRECCIONES DE MÓDULOS SECUNDARIOS ---
@admin_bp.route('/admin/personal')
def personal():
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/admin/cocina')
def cocina():
    return redirect('/pantalla-cocina')

@admin_bp.route('/admin/bar')
def bar():
    return redirect('/pantalla-bar')

@admin_bp.route('/admin/pos')
def pos():
    return redirect(url_for('caja_mesas.gestionar_mesas'))

@admin_bp.route('/admin/apertura_caja')
def apertura_caja():
    return redirect(url_for('caja_mesas.gestionar_mesas'))