from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg
from app.database import get_db_connection

auth_bp = Blueprint('auth', __name__)

# Función automática para crear la tabla y asegurar sus columnas si ya existe
def asegurar_tabla():
    try:
        conex = get_db_connection()
        with conex.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    nombre_restaurante VARCHAR(150),
                    nombre VARCHAR(150),
                    email VARCHAR(150) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    password_hash VARCHAR(255),
                    telefono VARCHAR(50),
                    rol VARCHAR(50),
                    empresa_id INT,
                    trial_ends_at TIMESTAMP,
                    subscription_ends_at TIMESTAMP,
                    plan_status VARCHAR(50) DEFAULT 'TRIAL',
                    plan_type VARCHAR(50)
                );
            """)
            # Aseguramos columnas base y de suscripción por si la tabla ya existía previamente
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS nombre_restaurante VARCHAR(150);")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS nombre VARCHAR(150);")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email VARCHAR(150);")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password VARCHAR(255);")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS telefono VARCHAR(50);")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rol VARCHAR(50);")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS empresa_id INT;")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP;")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS subscription_ends_at TIMESTAMP;")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS plan_status VARCHAR(50) DEFAULT 'TRIAL';")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS plan_type VARCHAR(50);")
            conex.commit()
        conex.close()
    except Exception as e:
        print(f"Error al crear tabla automático: {e}")

# Se ejecuta al iniciar el módulo
asegurar_tabla()

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre_restaurante = request.form.get('nombre_restaurante')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        telefono = request.form.get('telefono')
        
        nombre = nombre_restaurante 
        rol = 'gerente'
        password_hash = generate_password_hash(password)
        
        # Calculamos los 7 días de prueba gratis para la empresa
        trial_end = datetime.now() + timedelta(days=7)
        
        try:
            conex = get_db_connection()
            with conex.cursor() as cursor:
                # 🛑 1. VALIDACIÓN ANTI-DUPLICADOS: Verificamos si el correo ya existe en la BD
                cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s);", (email,))
                usuario_existente = cursor.fetchone()
                
                if usuario_existente:
                    conex.close()
                    flash(f"⚠️ El correo '{email}' ya se encuentra registrado en el sistema. Prueba con otro.", 'danger')
                    return render_template('registro.html')
                
                # 2. Si no existe, insertamos el usuario gerente incluyendo los campos del trial
                cursor.execute(
                    """INSERT INTO usuarios 
                    (nombre_restaurante, nombre, email, password, password_hash, telefono, rol, trial_ends_at, plan_status) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (nombre_restaurante, nombre, email, password, password_hash, telefono, rol, trial_end, 'TRIAL')
                )
                nuevo_id = cursor.fetchone()[0]
                
                # 3. Actualizamos su empresa_id para que sea único e independiente basado en su propio id
                cursor.execute(
                    "UPDATE usuarios SET empresa_id = %s WHERE id = %s",
                    (nuevo_id, nuevo_id)
                )
                conex.commit()
            conex.close()
            print("DEBUG: ¡Empresa y usuario registrado con éxito con 7 días de trial!")
            flash('¡Restaurante registrado con éxito! Tienes 7 días de prueba gratis. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            print(f"DEBUG ERROR EN REGISTRO: {e}")
            flash(f'Error al registrar: {e}', 'danger')
            return render_template('registro.html')
            
    return render_template('registro.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        try:
            conex = get_db_connection()
            with conex.cursor() as cursor:
                # Consultamos también los datos de suscripción del gerente de la empresa (CORREGIDO: Se agregó SELECT)
                cursor.execute("""
                    SELECT u.id, u.email, u.password_hash, u.rol, u.nombre, u.empresa_id, 
                    u.trial_ends_at, u.subscription_ends_at, u.plan_status 
                    FROM usuarios u WHERE LOWER(u.email) = LOWER(%s)
                """, (email,))
                user = cursor.fetchone()
            conex.close()
            
            if not user:
                print(f"DEBUG: El correo '{email}' no existe en la base de datos.")
                flash(f"El correo '{email}' no existe en la base de datos.", 'danger')
            else:
                if check_password_hash(user[2], password):
                    print("DEBUG: ¡Contraseña correcta!")
                    
                    user_id = user[0]
                    rol = user[3]
                    empresa_id = user[5] or user[0]
                    trial_ends_at = user[6]
                    subscription_ends_at = user[7]
                    plan_status = user[8] or 'TRIAL'
                    
                    # Buscamos al GERENTE de esta empresa para revisar el estado real de pago/trial de la compañía
                    conex = get_db_connection()
                    with conex.cursor() as cursor:
                        # (CORREGIDO: Se agregó SELECT)
                        cursor.execute("""
                            SELECT trial_ends_at, subscription_ends_at, plan_status 
                            FROM usuarios WHERE id = %s
                        """, (empresa_id,))
                        gerente_data = cursor.fetchone()
                    conex.close()
                    
                    if gerente_data:
                        g_trial, g_sub, g_status = gerente_data
                        now = datetime.now()
                        
                        # Verificamos si el trial expiró y no hay suscripción activa
                        if g_status == 'TRIAL' and g_trial and now > g_trial:
                            g_status = 'EXPIRED'
                            conex = get_db_connection()
                            with conex.cursor() as cursor:
                                cursor.execute("UPDATE usuarios SET plan_status = 'EXPIRED' WHERE id = %s", (empresa_id,))
                                conex.commit()
                            conex.close()
                        elif g_status == 'ACTIVE' and g_sub and now > g_sub:
                            g_status = 'EXPIRED'
                            conex = get_db_connection()
                            with conex.cursor() as cursor:
                                cursor.execute("UPDATE usuarios SET plan_status = 'EXPIRED' WHERE id = %s", (empresa_id,))
                                conex.commit()
                            conex.close()
                            
                        # 🛑 BLOQUEO O REDIRECCIÓN SI ESTÁ VENCIDO
                        if g_status in ['EXPIRED', 'CANCELLED']:
                            if rol == 'gerente':
                                flash("⚠️ Tu período de prueba o suscripción ha vencido. Por favor realiza el pago para continuar.", "warning")
                                session['user_id'] = user_id
                                session['usuario_id'] = user_id
                                session['email'] = user[1]
                                session['rol'] = rol
                                session['nombre'] = user[4]
                                session['empresa_id'] = empresa_id
                                return redirect(url_for('wompi.planes_pago'))
                            else:
                                flash("🚫 La suscripción de la empresa está vencida. Comunícate con el Gerente para renovar el servicio.", "danger")
                                return render_template('login.html')
                                
                    # Si todo está OK, guardamos sesión y entra normal
                    session['user_id'] = user_id
                    session['usuario_id'] = user_id 
                    session['email'] = user[1]
                    session['rol'] = rol
                    session['nombre'] = user[4]
                    session['empresa_id'] = empresa_id
                    
                    print("DEBUG: ¡Login exitoso y suscripción válida!")
                    return redirect(url_for('admin.dashboard'))
                else:
                    print("DEBUG: Contraseña incorrecta.")
                    flash("Contraseña incorrecta.", 'danger')
        except Exception as e:
            print(f"DEBUG ERROR EN LOGIN: {e}")
            flash(f"Error en el servidor: {e}", 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))