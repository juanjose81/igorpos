import hashlib
import uuid
import datetime
import requests

def enviar_factura_dian_api(factura_data, api_key=None, es_demo=True):
    """
    Servicio auxiliar para transmisión de Factura Electrónica.
    En entorno de prueba/demo genera CUFE y token de consulta.
    No bloquea ni altera el flujo principal de la aplicación.
    """
    if es_demo or not api_key:
        cadena_cufe = f"{factura_data.get('numero')}{factura_data.get('total')}{datetime.datetime.now().isoformat()}"
        cufe_generado = hashlib.sha256(cadena_cufe.encode('utf-8')).hexdigest()
        
        token_consulta = str(uuid.uuid4())
        id_fac = factura_data.get('id', '001')
        url_consulta = f"https://demo.igorpos.com/pages/ventas/ver_factura_pdf.php?idFactura={id_fac}&token={token_consulta}"
        
        return {
            "exito": True,
            "cufe": cufe_generado,
            "url_factura": url_consulta,
            "numero_factura": f"FE-{id_fac}",
            "mensaje": "Factura electrónica generada (Entorno de Pruebas)"
        }
    
    endpoint_api = "https://api.proveedortecnologico.com/v1/bills"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": factura_data.get('numero'),
        "customer": {
            "name": factura_data.get('cliente_nombre', 'Consumidor Final'),
            "identification": factura_data.get('cliente_nit', '222222222222')
        },
        "items": factura_data.get('items', []),
        "payment_method": factura_data.get('tipo_pago', 'Efectivo')
    }
    try:
        response = requests.post(endpoint_api, json=payload, headers=headers, timeout=5)
        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "exito": True,
                "cufe": data.get("cufe"),
                "url_factura": data.get("qr_url"),
                "numero_factura": data.get("number"),
                "mensaje": "Factura emitida ante la DIAN exitosamente"
            }
    except Exception as e:
        print(f"Error al conectar API DIAN: {e}")
    return {
        "exito": False,
        "cufe": None,
        "url_factura": None,
        "numero_factura": None,
        "mensaje": "No se pudo transmitir en tiempo real, guardada de forma local."
    }