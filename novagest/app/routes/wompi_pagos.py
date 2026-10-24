from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import psycopg

wompi_bp = Blueprint('wompi', __name__)

DB_CONFIG = "dbname=novagest_db user=postgres password=Novagest2026 host=localhost"

# 1. Pantalla donde el Gerente ve los planes y el botón de pago de Wompi
@wompi_bp.route('/planes', methods=['GET'])
def planes_pago():
    # Verificamos que esté logueado
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    return render_template('planes_pago.html')

# 2. Webhook de Wompi: Recibe el pago aprobado y activa el sistema automáticamente
@wompi_bp.route('/api/wompi-webhook', methods=['POST'])
def wompi_webhook():
    try:
        data = request.json
        print("DEBUG WEBHOOK WOMPI RECIBIDO:", data)
        
        # Verificamos la estructura del evento de Wompi para transacciones aprobadas
        if data and data.get('event') == 'transaction.updated':
            transaccion = data.get('data', {}).get('transaction', {})
            estado = transaccion.get('status')
            
            if estado == 'APPROVED':
                # La referencia que enviamos al cobrar debe ser el id de la empresa (empresa_id) o usuario
                referencia = transaccion.get('reference') 
                
                # Extraemos el tipo de plan (por defecto 'monthly')
                tipo_plan = transaccion.get('custom_data', {}).get('plan_type', 'monthly')
                dias_a_sumar = 365 if tipo_plan == 'yearly' else 30
                
                # Calculamos la fecha de expiración en Python de forma segura
                fecha_fin = datetime.now() + timedelta(days=dias_a_sumar)
                
                # Actualizamos en la base de datos
                conex = psycopg.connect(DB_CONFIG)
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