from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.database import get_db_connection

wompi_bp = Blueprint('wompi', __name__)

# 1. Pantalla donde el Gerente ve los planes y el botón de pago de Wompi
@wompi_bp.route('/planes', methods=['GET'])
def planes_pago():
    # Capturamos si viene un plan seleccionado por URL
    tipo_seleccionado = request.args.get('tipo')
    if tipo_seleccionado:
        session['pending_plan'] = tipo_seleccionado

    # Si no está logueado, lo mandamos a iniciar sesión o registrarse
    if 'user_id' not in session and 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Validamos si el usuario logueado es GERENTE / Administrador
    rol = str(session.get('rol', '')).lower()
    if rol not in ['gerente', 'administrador', 'admin']:
        return redirect(url_for('admin.dashboard'))
    
    return render_template('planes_pago.html')

# 2. Ruta puente para interceptar el clic en los planes antes de ir a Wompi
@wompi_bp.route('/seleccionar-plan/<tipo>', methods=['GET'])
def seleccionar_plan(tipo):
    session['pending_plan'] = tipo
    
    # Si no ha iniciado sesión, lo mandamos al login para que se autentique como gerente
    if 'user_id' not in session and 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    # Si ya tiene sesión activa y es gerente, lo mandamos directo al link de Wompi correspondiente
    link_wompi = "https://checkout.wompi.co/l/dYxdWp" if tipo == 'yearly' else "https://checkout.wompi.co/l/5tp88O"
    return redirect(link_wompi)

# 3. Webhook de Wompi: Recibe el pago aprobado y activa el sistema automáticamente[cite: 5]
@wompi_bp.route('/api/wompi-webhook', methods=['POST'])
def wompi_webhook():
    try:
        data = request.json
        print("DEBUG WEBHOOK WOMPI RECIBIDO:", data)
        
        if data and data.get('event') == 'transaction.updated':
            transaccion = data.get('data', {}).get('transaction', {})
            estado = transaccion.get('status')
            
            if estado == 'APPROVED':
                referencia = transaccion.get('reference') 
                tipo_plan = transaccion.get('custom_data', {}).get('plan_type', 'monthly')
                dias_a_sumar = 365 if tipo_plan == 'yearly' else 30
                
                fecha_fin = datetime.now() + timedelta(days=dias_a_sumar)
                
                conex = get_db_connection()
                with conex.cursor() as cursor:
                    cursor.execute("""
                        UPDATE usuarios 
                        SET plan_status = 'ACTIVE', 
                            plan_type = %s,
                            subscription_ends_at = %s
                        WHERE id = %s OR empresa_id = %s;
                    """, (tipo_plan, fecha_fin, int(referencia), int(referencia)))
                    conex.commit()
                conex.close()
                
                print(f"DEBUG: ¡Suscripción activada con éxito para la empresa/usuario {referencia}!")
                return jsonify({"status": "success", "message": "Suscripción actualizada"}), 200
        return jsonify({"status": "ignored"}), 200
    except Exception as e:
        print(f"DEBUG ERROR EN WEBHOOK WOMPI: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500