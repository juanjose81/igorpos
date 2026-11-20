import hashlib
import uuid
import datetime
import requests
import zipfile
import io
import base64

def enviar_factura_dian_api(factura_data, api_key=None, es_demo=True):
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

def enviar_set_pruebas_dian(documento_xml_str, consecutivo, tipo_doc="Invoice"):
    url_dian = "https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc"
    test_set_id = "e2466a37-2348-4cae-9617-c7a9190b2a5f"
    
    if tipo_doc == "Invoice":
        prefijo_nombre = "FV"
    elif tipo_doc == "CreditNote":
        prefijo_nombre = "NC"
    else:
        prefijo_nombre = "ND"
        
    nombre_archivo = f"{prefijo_nombre}-{consecutivo}.xml"
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(nombre_archivo, documento_xml_str)
    
    zip_buffer.seek(0)
    file_zip_base64 = base64.b64encode(zip_buffer.read()).decode('utf-8')
    
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync"
    }
    
    soap_envelope = '<?xml version="1.0" encoding="utf-8"?>' + \
                    '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wcf="http://wcf.dian.colombia">' + \
                    '<soapenv:Header/>' + \
                    '<soapenv:Body>' + \
                    '<wcf:SendTestSetAsync>' + \
                    f'<wcf:fileName>{prefijo_nombre}-{consecutivo}.zip</wcf:fileName>' + \
                    f'<wcf:fileZip>{file_zip_base64}</wcf:fileZip>' + \
                    f'<wcf:testSetId>{test_set_id}</wcf:testSetId>' + \
                    '</wcf:SendTestSetAsync>' + \
                    '</soapenv:Body>' + \
                    '</soapenv:Envelope>'
    
    try:
        response = requests.post(url_dian, data=soap_envelope.encode('utf-8'), headers=headers, timeout=30)
        if response.status_code == 200:
            return {
                "exito": True,
                "consecutivo": consecutivo,
                "mensaje": "Documento de prueba transmitido exitosamente a la DIAN"
            }
        else:
            return {
                "exito": False,
                "consecutivo": consecutivo,
                "mensaje": f"Error HTTP de la DIAN: {response.status_code}"
            }
    except Exception as e:
        print(f"Excepción en conexión SOAP con la DIAN: {e}")
        return {
            "exito": False,
            "consecutivo": consecutivo,
            "mensaje": f"Falla de conexión: {str(e)}"
        }