from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg
from app.database import get_db_connection
from itsdangerous import URLSafeTimedSerializer
import os
import resend

auth_bp = Blueprint('auth', __name__)

# Serializador para tokens seguros de recuperación (expiran en 15 minutos)
serializer = URLSafeTimedSerializer('clave_super_secreta_igorpos')

# Configuramos la API Key de Resend para producción
resend.api_key = os.getenv('RESEND_API_KEY')

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


# 🛡️ BLOQUEO GLOBAL EN TIEMPO REAL (DÍA 8 EN ADELANTE)
@auth_bp.before_app_request
def verificar_estado_suscripcion_global():
    ruta = request.path
    # Rutas libres donde no se aplica el bloqueo para permitir iniciar sesión o pagar
    rutas_libres = ['/login', '/registro', '/logout', '/recuperar-password', '/static']
    if any(ruta.startswith(r) for r in rutas_libres) or '/wompi/' in ruta or '/planes' in ruta:
        return None
        
    user_id = session.get('user_id') or session.get('usuario_id')
    if not user_id:
        return None
        
    empresa_id = session.get('empresa_id') or user_id
    rol = str(session.get('rol', '')).lower()
    
    try:
        conex = get_db_connection()
        with conex.cursor() as cursor:
            cursor.execute("""
                SELECT trial_ends_at, subscription_ends_at, plan_status 
                FROM usuarios WHERE id = %s
            """, (empresa_id,))
            res = cursor.fetchone()
        conex.close()
        
        if res:
            g_trial, g_sub, g_status = res
            now = datetime.now()
            
            # Verificamos si expiró el trial de 7 días exactos
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
                
            # ACCIÓN DE BLOQUEO SI ESTÁ VENCIDO
            if g_status in ['EXPIRED', 'CANCELLED']:
                if rol in ['gerente', 'administrador', 'admin']:
                    flash("⚠️ Tu período de prueba de 7 días ha finalizado. Realiza el pago para desbloquear el sistema.", "warning")
                    return redirect(url_for('wompi.planes_pago'))
                else:
                    session.clear()
                    flash("🚫 La suscripción de la empresa está vencida. Comunícate con el Gerente para renovar el servicio.", "danger")
                    return redirect(url_for('auth.login'))
    except Exception as e:
        print(f"Error en validación global de suscripción: {e}")
        
    return None


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
        
        # Calculamos los 7 días exactos de prueba gratis
        trial_end = datetime.now() + timedelta(days=7)
        
        try:
            conex = get_db_connection()
            with conex.cursor() as cursor:
                cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s);", (email,))
                usuario_existente = cursor.fetchone()
                
                if usuario_existente:
                    conex.close()
                    flash("Esta cuenta ya existe. Por favor, inicia sesión o usa otro correo.", 'danger')
                    return render_template('registro.html')
                
                cursor.execute(
                    """INSERT INTO usuarios 
                    (nombre_restaurante, nombre, email, password, password_hash, telefono, rol, trial_ends_at, plan_status) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (nombre_restaurante, nombre, email, password, password_hash, telefono, rol, trial_end, 'TRIAL')
                )
                nuevo_id = cursor.fetchone()[0]
                
                cursor.execute(
                    "UPDATE usuarios SET empresa_id = %s WHERE id = %s",
                    (nuevo_id, nuevo_id)
                )
                conex.commit()
            conex.close()
            flash('¡Restaurante registrado con éxito! Tienes 7 días de prueba gratis. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
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
                cursor.execute("""
                    SELECT u.id, u.email, u.password_hash, u.rol, u.nombre, u.empresa_id, 
                    u.trial_ends_at, u.subscription_ends_at, u.plan_status 
                    FROM usuarios u WHERE LOWER(u.email) = LOWER(%s)
                """, (email,))
                user = cursor.fetchone()
            conex.close()
            
            if not user or not user[2] or not check_password_hash(user[2], password):
                flash("El usuario o contraseña es incorrecto.", 'danger')
            else:
                user_id = user[0]
                rol = user[3]
                empresa_id = user[5] or user[0]
                
                # Buscamos al GERENTE para revisar el estado real de la empresa
                conex = get_db_connection()
                with conex.cursor() as cursor:
                    cursor.execute("""
                        SELECT trial_ends_at, subscription_ends_at, plan_status 
                        FROM usuarios WHERE id = %s
                    """, (empresa_id,))
                    gerente_data = cursor.fetchone()
                conex.close()
                
                if gerente_data:
                    g_trial, g_sub, g_status = gerente_data
                    now = datetime.now()
                    
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
                            
                session['user_id'] = user_id
                session['usuario_id'] = user_id 
                session['email'] = user[1]
                session['rol'] = rol
                session['nombre'] = user[4]
                session['empresa_id'] = empresa_id
                
                return redirect(url_for('admin.dashboard'))
                
        except Exception as e:
            flash(f"Error en el servidor: {e}", 'danger')
            
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# --- RECUPERACIÓN DE CONTRASEÑA ---
@auth_bp.route('/recuperar-password', methods=['GET', 'POST'])
def solicitar_recuperacion():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        try:
            conex = get_db_connection()
            with conex.cursor() as cursor:
                cursor.execute("""
                    SELECT id, nombre, rol FROM usuarios 
                    WHERE LOWER(email) = LOWER(%s) 
                    AND LOWER(rol) IN ('gerente', 'administrador', 'admin');
                """, (email,))
                usuario = cursor.fetchone()
            conex.close()
            
            if usuario:
                token = serializer.dumps(email, salt='recuperar-clave-salt')
                link_recuperacion = url_for('auth.restablecer_password', token=token, _external=True)
                try:
                    params = {
                        "from": "IGOR POS <onboarding@resend.dev>",
                        "to": [email],
                        "subject": "🔑 Recuperación de Contraseña - IGOR POS",
                        "html": f"""
                        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                            <h2 style="color: #2563eb;">🔑 Recuperación de Contraseña - IGOR POS</h2>
                            <p>Hola, <b>{usuario[1]}</b>:</p>
                            <p>Has solicitado restablecer tu contraseña de Gerente en IGOR POS.</p>
                            <p><a href="{link_recuperacion}" style="background-color: #2563eb; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Restablecer Contraseña</a></p>
                        </div>
                        """
                    }
                    resend.Emails.send(params)
                except Exception as resend_err:
                    print(f"Error Resend: {resend_err}")
                    
            flash('Si el correo está registrado como Gerente, se han enviado las instrucciones.', 'success')
            return redirect(url_for('auth.solicitar_recuperacion'))
        except Exception:
            flash('Si el correo está registrado como Gerente, se han enviado las instrucciones.', 'success')
            return redirect(url_for('auth.solicitar_recuperacion'))
            
    return render_template('recuperar_solicitud.html')


@auth_bp.route('/restablecer-password/<token>', methods=['GET', 'POST'])
def restablecer_password(token):
    try:
        email = serializer.loads(token, salt='recuperar-clave-salt', max_age=900)
    except Exception:
        flash('El enlace es inválido o ya ha expirado.', 'danger')
        return redirect(url_for('auth.solicitar_recuperacion'))
        
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password', '').strip()
        if not nueva_password:
            flash('La contraseña no puede estar vacía.', 'danger')
            return redirect(request.url)
            
        try:
            password_hash = generate_password_hash(nueva_password)
            conex = get_db_connection()
            with conex.cursor() as cursor:
                cursor.execute("""
                    UPDATE usuarios 
                    SET password = %s, password_hash = %s 
                    WHERE LOWER(email) = LOWER(%s);
                """, (nueva_password, password_hash, email))
                conex.commit()
            conex.close()
            
            flash('¡Contraseña restablecida con éxito! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Error al actualizar: {e}', 'danger')
            
    return render_template('recuperar_cambiar.html')