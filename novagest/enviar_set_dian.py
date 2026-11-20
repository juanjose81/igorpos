import base64
import datetime
import hashlib
import io
import os
import time
import xml.etree.ElementTree as ET
import requests
import zipfile


def enviar_set_pruebas_dian_directo(
    documento_xml_str, consecutivo, tipo_doc="Invoice"
):
  url_dian = "https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc"
  test_set_id = "e2466a37-2348-4cae-9617-c7a9190b2a5f"

  DIAN_USER = "1082898883"
  DIAN_PASSWORD = "fc8eac422eba16e22ffd8c6f94b3f40a6e38162c"

  # Generación estricta del PasswordDigest para WCF de la DIAN
  nonce_bytes = os.urandom(16)
  nonce_base64 = base64.b64encode(nonce_bytes).decode("utf-8")
  created_time = (
      datetime.datetime.now(datetime.timezone.utc)
      .strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4]
      + "Z"
  )

  digest_input = (
      nonce_bytes
      + created_time.encode("utf-8")
      + DIAN_PASSWORD.encode("utf-8")
  )
  sha1_hash = hashlib.sha1(digest_input).digest()
  password_digest = base64.b64encode(sha1_hash).decode("utf-8")

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
  file_zip_base64 = base64.b64encode(zip_buffer.read()).decode("utf-8")

  headers = {
      "Content-Type": (
          'application/soap+xml; charset=utf-8;'
          ' action="http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync"'
      )
  }

  soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" 
               xmlns:wcf="http://wcf.dian.colombia"
               xmlns:wsa="http://www.w3.org/2005/08/addressing"
               xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
               xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
   <soap:Header>
      <wsa:Action soap:mustUnderstand="1">http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync</wsa:Action>
      <wsa:To soap:mustUnderstand="1">{url_dian}</wsa:To>
      <wsse:Security soap:mustUnderstand="true">
         <wsse:UsernameToken>
            <wsse:Username>{DIAN_USER}</wsse:Username>
            <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{password_digest}</wsse:Password>
            <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_base64}</wsse:Nonce>
            <wsu:Created>{created_time}</wsu:Created>
         </wsse:UsernameToken>
      </wsse:Security>
   </soap:Header>
   <soap:Body>
      <wcf:SendTestSetAsync>
         <wcf:fileName>{prefijo_nombre}-{consecutivo}.zip</wcf:fileName>
         <wcf:fileZip>{file_zip_base64}</wcf:fileZip>
         <wcf:testSetId>{test_set_id}</wcf:testSetId>
      </wcf:SendTestSetAsync>
   </soap:Body>
</soap:Envelope>"""

  try:
    response = requests.post(
        url_dian, data=soap_envelope.encode("utf-8"), headers=headers, timeout=30
    )
    if response.status_code == 200:
      return {
          "exito": True,
          "consecutivo": consecutivo,
          "mensaje": "¡Transmitido con éxito a la DIAN!",
      }
    else:
      return {
          "exito": False,
          "consecutivo": consecutivo,
          "mensaje": f"DIAN Rechazó (HTTP {response.status_code}): {response.text[:300]}",
      }
  except Exception as e:
    return {
        "exito": False,
        "consecutivo": consecutivo,
        "mensaje": f"Falla de conexión: {str(e)}",
    }