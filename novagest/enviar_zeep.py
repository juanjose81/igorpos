import base64
import datetime
import hashlib
import io
import os
import requests
import zipfile

WSDL_URL = "https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc"
TEST_SET_ID = "ddcabf60-ba4c-49c4-8cd9-e1eb7dc8fda9"
DIAN_USER = "1082898883"
DIAN_PASSWORD = "fc8eac422eba16e22ffd8c6f94b3f40a6e38162c"

nonce_bytes = os.urandom(16)
nonce_base64 = base64.b64encode(nonce_bytes).decode("utf-8")
created_time = (
    datetime.datetime.now(datetime.timezone.utc)
    .strftime("%Y-%m-%dT%H:%M:%SZ")
)

digest_input = (
    nonce_bytes
    + created_time.encode("utf-8")
    + DIAN_PASSWORD.encode("utf-8")
)
sha1_hash = hashlib.sha1(digest_input).digest()
password_digest = base64.b64encode(sha1_hash).decode("utf-8")

prefix = "FV"
consecutivo = 99000000
file_name = f"{prefix}-{consecutivo}.xml"

xml_prueba = """<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>1</cbc:CustomizationID>
    <cbc:ProfileID>DIAN 2.1: Factura Electrónica de Venta</cbc:ProfileID>
    <cbc:ID>SETP99000000</cbc:ID>
    <cbc:IssueDate>2026-11-05</cbc:IssueDate>
    <cbc:IssueTime>19:36:00-05:00</cbc:IssueTime>
    <cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>
    <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
    <cac:AccountingSupplierParty>
        <cbc:AdditionalAccountID>1</cbc:AdditionalAccountID>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="3" schemeName="13">1082898883</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>IGOR POS</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cbc:AdditionalAccountID>2</cbc:AdditionalAccountID>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="3" schemeName="13">222222222222</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>CLIENTE PRUEBAS DIAN</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="COP">100000.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="COP">0.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">100000.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">100000.00</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:InvoicedQuantity unitCode="EA">1.00</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="COP">100000.00</cbc:LineExtensionAmount>
        <cac:Item>
            <cbc:Description>Servicio de Prueba</cbc:Description>
            <cac:SellersItemIdentification>
                <cbc:ID>P001</cbc:ID>
            </cac:SellersItemIdentification>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="COP">100000.00</cbc:PriceAmount>
        </cac:Price>
    </cac:InvoiceLine>
</Invoice>"""

zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
    zip_file.writestr(file_name, xml_prueba)
zip_buffer.seek(0)
file_zip_base64 = base64.b64encode(zip_buffer.read()).decode("utf-8")

headers = {
    "Content-Type": 'application/soap+xml; charset=utf-8; action="http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync"'
}

soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" 
               xmlns:wcf="http://wcf.dian.colombia"
               xmlns:wsa="http://www.w3.org/2005/08/addressing"
               xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
               xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
   <soap:Header>
      <wsa:Action soap:mustUnderstand="1">http://wcf.dian.colombia/IWcfDianCustomerServices/SendTestSetAsync</wsa:Action>
      <wsa:To soap:mustUnderstand="1">{WSDL_URL}</wsa:To>
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
         <wcf:fileName>{prefix}-{consecutivo}.zip</wcf:fileName>
         <wcf:fileZip>{file_zip_base64}</wcf:fileZip>
         <wcf:testSetId>{TEST_SET_ID}</wcf:testSetId>
      </wcf:SendTestSetAsync>
   </soap:Body>
</soap:Envelope>"""

try:
    response = requests.post(WSDL_URL, data=soap_envelope.encode("utf-8"), headers=headers, timeout=30)
    if response.status_code == 200:
        print({"exito": True, "consecutivo": consecutivo, "respuesta": response.text})
    else:
        print({"exito": False, "consecutivo": consecutivo, "mensaje": f"HTTP {response.status_code}: {response.text[:500]}"})
except Exception as e:
    print({"exito": False, "consecutivo": consecutivo, "mensaje": str(e)})