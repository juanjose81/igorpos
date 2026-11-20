import time
from enviar_set_dian import enviar_set_pruebas_dian_directo

consecutivos_facturas = range(99000000, 99000030)
consecutivos_nc = range(99000500, 99000510)
consecutivos_nd = range(99000600, 99000610)

def generar_xml_factura(consecutivo):
    return f"""<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>1</cbc:CustomizationID>
    <cbc:ProfileID>DIAN 2.1: Factura Electrónica de Venta</cbc:ProfileID>
    <cbc:ID>SETP{consecutivo}</cbc:ID>
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

def generar_xml_nc(consecutivo):
    return f"""<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>1</cbc:CustomizationID>
    <cbc:ProfileID>DIAN 2.1: Nota Crédito de Factura Electrónica</cbc:ProfileID>
    <cbc:ID>NC{consecutivo}</cbc:ID>
    <cbc:IssueDate>2026-11-05</cbc:IssueDate>
    <cbc:IssueTime>19:36:00-05:00</cbc:IssueTime>
    <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
    <cac:DiscrepancyResponse>
        <cbc:ReferenceID>SETP99000000</cbc:ReferenceID>
        <cbc:Description>Anulación de factura de prueba</cbc:Description>
    </cac:DiscrepancyResponse>
    <cac:AccountingSupplierParty>
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
    <cac:CreditNoteLine>
        <cbc:ID>1</cbc:ID>
        <cbc:CreditedQuantity unitCode="EA">1.00</cbc:CreditedQuantity>
        <cbc:LineExtensionAmount currencyID="COP">100000.00</cbc:LineExtensionAmount>
        <cac:Item>
            <cbc:Description>Servicio de Prueba NC</cbc:Description>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="COP">100000.00</cbc:PriceAmount>
        </cac:Price>
    </cac:CreditNoteLine>
</CreditNote>"""

def generar_xml_nd(consecutivo):
    return f"""<DebitNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
    <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>1</cbc:CustomizationID>
    <cbc:ProfileID>DIAN 2.1: Nota Débito de Factura Electrónica</cbc:ProfileID>
    <cbc:ID>ND{consecutivo}</cbc:ID>
    <cbc:IssueDate>2026-11-05</cbc:IssueDate>
    <cbc:IssueTime>19:36:00-05:00</cbc:IssueTime>
    <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
    <cac:RequestedMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="COP">50000.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="COP">0.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">50000.00</cbc:TaxInclusiveAmount>
        <cbc:PayableAmount currencyID="COP">50000.00</cbc:PayableAmount>
    </cac:RequestedMonetaryTotal>
    <cac:AccountingSupplierParty>
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
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="3" schemeName="13">222222222222</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>CLIENTE PRUEBAS DIAN</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:DebitNoteLine>
        <cbc:ID>1</cbc:ID>
        <cbc:DebitedQuantity unitCode="EA">1.00</cbc:DebitedQuantity>
        <cbc:LineExtensionAmount currencyID="COP">50000.00</cbc:LineExtensionAmount>
        <cac:Item>
            <cbc:Description>Servicio de Prueba ND</cbc:Description>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="COP">50000.00</cbc:PriceAmount>
        </cac:Price>
    </cac:DebitNoteLine>
</DebitNote>"""

print("=== INICIANDO TRANSMISIÓN DE SET DE PRUEBAS A LA DIAN ===")

print("\n--- Transmitiendo Facturas ---")
for cons in consecutivos_facturas:
    xml_data = generar_xml_factura(cons)
    resultado = enviar_set_pruebas_dian_directo(xml_data, cons, "Invoice")
    if resultado["exito"]:
        print(f"Factura {cons}: {resultado['mensaje']}")
    else:
        print(f"Factura {cons}: {resultado['mensaje']}")
    time.sleep(0.5)

print("\n--- Transmitiendo Notas Crédito ---")
for cons in consecutivos_nc:
    xml_data = generar_xml_nc(cons)
    resultado = enviar_set_pruebas_dian_directo(xml_data, cons, "CreditNote")
    if resultado["exito"]:
        print(f"Nota Crédito {cons}: {resultado['mensaje']}")
    else:
        print(f"Nota Crédito {cons}: {resultado['mensaje']}")
    time.sleep(0.5)

print("\n--- Transmitiendo Notas Débito ---")
for cons in consecutivos_nd:
    xml_data = generar_xml_nd(cons)
    resultado = enviar_set_pruebas_dian_directo(xml_data, cons, "DebitNote")
    if resultado["exito"]:
        print(f"Nota Débito {cons}: {resultado['mensaje']}")
    else:
        print(f"Nota Débito {cons}: {resultado['mensaje']}")
    time.sleep(0.5)

print("\n==================================================")
print("✅ ¡TRANSMISIÓN FINALIZADA! Revisa el portal de la DIAN.")
print("==================================================")