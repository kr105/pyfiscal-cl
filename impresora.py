import cgi
import json
import struct
import sys
from time import sleep
from hashlib import sha256
from http.server import BaseHTTPRequestHandler,HTTPServer


hostName = "192.168.1.190"
hostPort = 9000
device = "/dev/usb/lp0"
hashedDevice = sha256(device.encode('utf-8')).hexdigest()


def genera_cadena(str):
    sys.stdout.buffer.write(bytes.fromhex(str))


def byte_array_to_hex_string(ba):
    res = ''.join(format(x, '02X') for x in ba)
    return res


def byte_array_to_hex_array(ba):
    ha = [ba[i:i+1] for i in range(len(ba))]
    return ha


def str_to_hex_array(str):
    ba = bytes.fromhex(str)
    ha = byte_array_to_hex_array(ba)
    return ha


def checksum_from_bytes(bytes_):
    checksum = 0;

    for x in bytes_:
        checksum = checksum + int.from_bytes(x, 'little')

    checksum = '{:04x}'.format(checksum)

    return checksum


def checksum_from_str(str):
    check = str_to_hex_array(str)
    checksum = checksum_from_bytes(check)

    checksum_final = ''

    for character in checksum:
        checksum_final = checksum_final + format(ord(character), "x")

    return checksum_final


def build_packet(seq, payload):
    #print('seq = ' + str(seq))
    pkt = '02' + format(seq, 'X') + payload + '03'
    pkt = pkt + checksum_from_str(pkt)

    return pkt

def receive_packet():
    while True:
        read = hPrinter.read()
        if not read:
            continue

        # ACK
        if len(read) == 1 and read[0] == 0x06:
            continue

        # NAK
        if len(read) == 1 and read[0] == 0x15:
            print('Recibi NAK!')
            continue

        print('Recibi datos:')
        print(read)

        # No se recibio un paquete completo
        # TODO: Agregar un sistema de buffer o algo
        if len(read) < 8:
            continue

        if not testChecksum(read):
            print('Checksum invalido, ignorando ...')
            continue

        if not read[0] == 0x02 or not read[-5] == 0x03:
            print('Paquete desconocido, ignorando ...')
            continue

        if not read[1] == deviceSeq:
            print('Secuencia no coincide, ignorando ...')
            continue

        estado_impresora = read[2:4]
        estado_fiscal = read[5:7]
        retorno = read[8:-5]

        parse_estado_impresora(estado_impresora)
        parse_estado_fiscal(estado_fiscal)

        break

    return retorno


def send_packet(pkt):
    global deviceSeq

    print('send_packet = ' + pkt)

    hPrinter.write(bytes.fromhex(pkt))

    rtn = receive_packet()

    # Envia ACK
    hPrinter.write(bytes.fromhex('06'))

    deviceSeq = deviceSeq + 1

    if(deviceSeq > 0xFF):
        deviceSeq = 0x81

    hDeviceSeq.seek(0)
    hDeviceSeq.write(deviceSeq.to_bytes(1, 'little'))

    return rtn


def testChecksum(pkt):
    test = pkt[:-4]
    checksum = pkt[-4:]
    checksum = int(checksum, base=16)

    test = byte_array_to_hex_array(test)
    test = checksum_from_bytes(test)
    test = int(test, base=16)

    return checksum == test


def parse_estado_impresora(data):
    data = struct.unpack('>H', data)
    data = data[0]

    offline = ((data & 0x8000) >> 15)
    error_impresora = ((data & 0x4000) >> 14)
    tapa_abierta = ((data & 0x2000) >> 13)
    cajon_abierto = ((data & 0x1000) >> 12)
    estacion_impresion = ((data & 0x400) >> 9) | ((data & 0x200) >> 9)
    sensor_espera = ((data & 0x100) >> 7) | ((data & 0x80) >> 7)
    sensor_inicio_carga_papel = ((data & 0x40) >> 6)
    sensor_fin_carga_papel = ((data & 0x20) >> 5)
    sensor_validacion_papel = ((data & 0x10) >> 4)
    journal_station = ((data & 0x08) >> 2) | ((data & 0x04) >> 2)
    receipt_station = (data & 0x02) | (data & 0x01)

    print('offline = ' + str(offline))
    print('error_impresora = ' + str(error_impresora))
    print('tapa_abierta = ' + str(tapa_abierta))
    print('cajon_abierto = ' + str(cajon_abierto))
    print('estacion_impresion = ' + str(estacion_impresion))
    print('sensor_espera = ' + str(sensor_espera))
    print('sensor_inicio_carga_papel = ' + str(sensor_inicio_carga_papel))
    print('sensor_fin_carga_papel = ' + str(sensor_fin_carga_papel))
    print('sensor_validacion_papel = ' + str(sensor_validacion_papel))
    print('journal_station = ' + str(journal_station))
    print('receipt_station = ' + str(receipt_station))


def parse_estado_fiscal(data):
    data = struct.unpack('>H', data)
    data = data[0]

    modo_funcionamiento = ((data & 0x8000) >> 14) | ((data & 0x4000) >> 14)
    modo_tecnico = ((data & 0x1000) >> 12)
    estado_memoria_fiscal = ((data & 0x800) >> 10) | ((data & 0x400) >> 10)
    jornada_fiscal_abierta = ((data & 0x80) >> 7)
    subestado = ((data & 0x40) >> 4) | ((data & 0x20) >> 4) | ((data & 0x10) >> 4)
    documento_en_progreso = (data & 0x08) | (data & 0x04) | (data & 0x02) | (data & 0x01)

    print('modo_funcionamiento = ' + str(modo_funcionamiento))
    print('modo_tecnico = ' + str(modo_tecnico))
    print('estado_memoria_fiscal = ' + str(estado_memoria_fiscal))
    print('jornada_fiscal_abierta = ' + str(jornada_fiscal_abierta))
    print('subestado = ' + str(subestado))
    print('documento_en_progreso = ' + str(documento_en_progreso))


# 0x02 STX comienzo de paquete
# 0x03 ETX final del paquete
# 0x1A Reservado
# 0x1B ESC caracter de escape
# 0x1C FLD separador de campos
# 0x1D Reservado
# 0x1E Reservado
# 0x1F Reservado 

def avanzar_papel(lineas):
    lineas = '{0:02d}'.format(lineas)
    lines_final = ''

    for character in lineas:
        lines_final = lines_final + format(ord(character), "x")

    pkt = '0701' + '1C' + '0000' + '1C' + lines_final
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


def cortar_papel():
    pkt = '071B02' + '1C' + '0000'
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


def cierre_z(imprimir_encabezadopie):
    imprimir_encabezadopie = bool(imprimir_encabezadopie)
    imprimir_encabezadopie = not imprimir_encabezadopie

    data = (imprimir_encabezadopie << 4)
    data = struct.pack('>H', data)
    data = byte_array_to_hex_string(data)

    pkt = '0801' + '1C' + data
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    retorno = rtn[0:2]
    campo1 = rtn[3:5]

    retorno = struct.unpack('>H', retorno)
    retorno = retorno[0]

    campo1 = struct.unpack('>H', campo1)
    campo1 = campo1[0]

    # print(retorno)
    # print(campo1)

    return rtn


def cierre_cajero(imprimir_encabezadopie):
    imprimir_encabezadopie = bool(imprimir_encabezadopie)
    imprimir_encabezadopie = not imprimir_encabezadopie

    data = (imprimir_encabezadopie << 4)
    data = struct.pack('>H', data)
    data = byte_array_to_hex_string(data)

    pkt = '081B02' + '1C' + '0000'
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    retorno = rtn[0:2]
    campo1 = rtn[3:5]

    retorno = struct.unpack('>H', retorno)
    retorno = retorno[0]

    campo1 = struct.unpack('>H', campo1)
    campo1 = campo1[0]

    # print(retorno)
    # print(campo1)

    return rtn

def boleta_abrir(nro_logo = None, densidad = None):

    pkt = '0A01' + '1C' + '0000'

    if not nro_logo == None:
        nro_logo = '{0:03d}'.format(nro_logo)
        nro_logo_final = ''

        for character in nro_logo:
            nro_logo_final = nro_logo_final + format(ord(character), "x")

        pkt = pkt + nro_logo_final

    pkt = pkt + '1C'

    if not densidad == None:
        densidad = '{0:01d}'.format(densidad)
        densidad_final = ''

        for character in densidad:
            densidad_final = densidad_final + format(ord(character), "x")

        pkt = pkt + densidad_final

    pkt = pkt + '1C'

    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    retorno = rtn[0:2]
    campo1 = rtn[3:5]

    retorno = struct.unpack('>H', retorno)
    retorno = retorno[0]

    campo1 = struct.unpack('>H', campo1)
    campo1 = campo1[0]

    # print(retorno)
    # print(campo1)

    return rtn


def header_set(nro_linea, txt_linea):
    nro_linea = '{0:03d}'.format(nro_linea)
    nro_linea_final = ''
    txt_linea_final = ''

    for character in nro_linea:
        nro_linea_final = nro_linea_final + format(ord(character), "x")

    for character in txt_linea:
        txt_linea_final = txt_linea_final + format(ord(character), "x")

    pkt = '0508' + '1C' + '0000' + '1C' + nro_linea_final + '1C' + txt_linea_final
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


def footer_set(nro_linea, txt_linea):
    nro_linea = '{0:03d}'.format(nro_linea)
    nro_linea_final = ''
    txt_linea_final = ''

    for character in nro_linea:
        nro_linea_final = nro_linea_final + format(ord(character), "x")

    for character in txt_linea:
        txt_linea_final = txt_linea_final + format(ord(character), "x")

    pkt = '050A' + '1C' + '0000' + '1C' + nro_linea_final + '1C' + txt_linea_final
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


def informacion_contadores():
    pkt = '0830' + '1C' + '0000'
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


def boleta_item(descripcion, cantidad, precio_unitario, tasa_impuestos, calificador_operacion, excento_iva):
    ext = 0

    if 'M' in calificador_operacion:
        ext = 0
    elif 'm' in calificador_operacion:
        ext = 1
    elif 'R' in calificador_operacion:
        ext = 4
    elif 'r' in calificador_operacion:
        ext = 5

    if excento_iva == True:
        ext = ext + 256

    ext = struct.pack('>H', ext)
    ext = byte_array_to_hex_string(ext)

    descripcion_final = ''

    for character in descripcion:
        descripcion_final = descripcion_final + format(ord(character), "x")

    # TODO: Agregar descripciones adicionales
    # TODO: Limitar largo a descripcion

    cantidad =  "{:5.4f}".format(cantidad)
    precio_unitario = "{:7.4f}".format(precio_unitario)

    cantidad = cantidad.replace('.', '')
    precio_unitario = precio_unitario.replace('.', '')

    cantidad_final = ''
    precio_unitario_final = ''

    for character in cantidad:
        cantidad_final = cantidad_final + format(ord(character), "x")

    for character in precio_unitario:
        precio_unitario_final = precio_unitario_final + format(ord(character), "x")

    pkt = '0A1B02' + '1C' + ext + '1C' + '1C' +'1C' +'1C' +'1C' +'1C' + descripcion_final + '1C' + cantidad_final + '1C' + precio_unitario_final + '1C' + '31393030'
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


def boleta_subtotal(imprime_subtotal):
    data = 0

    if not imprime_subtotal:
        data = 1

    data = struct.pack('>H', data)
    data = byte_array_to_hex_string(data)

    pkt = '0A1B03' + '1C' + data
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


def boleta_pago(tipo, monto):
    monto = '{0:015d}'.format(monto)
    monto_final = ''

    for character in monto:
        monto_final = monto_final + format(ord(character), "x")


    tipo = '{0:03d}'.format(tipo)
    tipo_final = ''

    for character in tipo:
        tipo_final = tipo_final + format(ord(character), "x")

    pkt = '0A05' + '1C' + '0000' + '1C' + tipo_final + '1C' + monto_final
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


# TODO: Parametros
def boleta_cerrar():
    pkt = '0A06' + '1C' + '0001' + '1C1C1C1C1C1C'
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)

    return rtn


def informacion_fiscal_curso(cierre = False):
    data = 0

    if cierre:
        data = 1

    data = struct.pack('>H', data)
    data = byte_array_to_hex_string(data)

    pkt = '080A' + '1C' + data
    pkt = build_packet(deviceSeq, pkt)

    rtn = send_packet(pkt)
    rtn = rtn.split(b'\x1C')

# 01  Fecha de apertura de la jornada fiscal
# 02  Hora de apertura de la jornada fiscal
# 03  Número del último cierre Z
# 04  Número de primer boleta fiscal
# 05  Número de última boleta fiscal
# 06  Número de último documento no fiscal
# 07  Número de último documento no fiscal homologados
# 08  Total de ventas
# 09  Total de impuestos
# 10  Total pagado
# 11  Total de donaciones
# 12  Cantidad de DF
# 13  Cantidad de DNF
# 14  Cantidad de DNFH
# 15  Total Exento
# 16  Total de Nota de Credito
# 17  Total de Pago Cuota Cuenta
# 18  Total de Recepción de Dinero
# 19  Cantidad de Notas de Credito
# 20  Cantidad de Pago Cuota / Cuenta
# 21  Cantidad de Recepciones de Dinero
# 22  Cantidad de Documentos Internos

    fecha_apertura = int(rtn[3])
    hora_apertura = int(rtn[4])
    nro_ultimo_z = int(rtn[5])
    nro_primer_boleta_fiscal = int(rtn[6])
    nro_ultima_boleta_fiscal = int(rtn[7])
    nro_ultimo_dcto_nofiscal = int(rtn[8])
    nro_ultimo_dcto_nofiscal_homo = int(rtn[9])
    total_ventas = int(rtn[10])
    total_impuestos = int(rtn[11])
    total_pagado = int(rtn[12])
    total_donaciones = int(rtn[13])
    cantidad_df = int(rtn[14])
    cantidad_dnf = int(rtn[15])
    cantidad_dnfh = int(rtn[16])
    total_exento = int(rtn[17])
    total_nota_credito = int(rtn[18])
    total_pago_cuota_cuenta = int(rtn[19])
    total_recepcion_dinero = int(rtn[20])
    cantidad_notas_credito = int(rtn[21])
    cantidad_pago_cuota = int(rtn[22])
    cantidad_recepciones_dinero = int(rtn[23])
    cantidad_dcto_internos = int(rtn[24])
    cantidad_retiro_dinero = int(rtn[25])
    total_retiro_dinero = int(rtn[26])

    rtn = {
        'fecha_apertura' : fecha_apertura,
        'hora_apertura' : hora_apertura,
        'nro_ultimo_z' : nro_ultimo_z,
        'nro_primer_boleta_fiscal' : nro_primer_boleta_fiscal,
        'nro_ultima_boleta_fiscal' : nro_ultima_boleta_fiscal,
        'nro_ultimo_dcto_nofiscal' : nro_ultimo_dcto_nofiscal,
        'nro_ultimo_dcto_nofiscal_homo' : nro_ultimo_dcto_nofiscal_homo,
        'total_ventas' : total_ventas,
        'total_impuestos' : total_impuestos,
        'total_pagado' : total_pagado,
        'total_donaciones' : total_donaciones,
        'cantidad_df' : cantidad_df,
        'cantidad_dnf' : cantidad_dnf,
        'cantidad_dnfh' : cantidad_dnfh,
        'total_exento' : total_exento,
        'total_nota_credito' : total_nota_credito,
        'total_pago_cuota_cuenta' : total_pago_cuota_cuenta,
        'total_recepcion_dinero' : total_recepcion_dinero,
        'cantidad_notas_credito' : cantidad_notas_credito,
        'cantidad_pago_cuota' : cantidad_pago_cuota,
        'cantidad_recepciones_dinero' : cantidad_recepciones_dinero,
        'cantidad_dcto_internos' : cantidad_dcto_internos,
        'cantidad_retiro_dinero' : cantidad_retiro_dinero,
        'total_retiro_dinero' : total_retiro_dinero
    }

    return rtn


class MyServer(BaseHTTPRequestHandler):
    def do_POST(self):
            if self.path=="/api":
                content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
                post_data = self.rfile.read(content_length) # <--- Gets the data itself
                post_data = post_data.decode('utf-8')

                try:
                    post_data = json.loads(post_data)
                except json.JSONDecodeError(msg, doc, pos):
                    print('Error decodificando JSON: ' + post_data)
                    return

                self.send_response(200)

                metodo = post_data['metodo']

                if metodo == 'AvanzaPapel':
                    lineas = post_data['parametros']['lineas']
                    avanzar_papel(lineas)
                elif metodo == 'CortaPapel':
                    cortar_papel()
                elif metodo == 'CierreCajero':
                    cierre_cajero(1)
                elif metodo == 'CierreZ':
                    cierre_z(1)
                elif metodo == 'InformacionFiscalCurso':
                    rtn = informacion_fiscal_curso()
                    rtn = json.dumps(rtn)
                    self.wfile.write(rtn.encode());
                elif metodo == 'HeaderSet':
                    linea = post_data['parametros']['linea']
                    texto = post_data['parametros']['texto']
                    header_set(linea, texto)
                elif metodo == 'FooterSet':
                    linea = post_data['parametros']['linea']
                    texto = post_data['parametros']['texto']
                    header_set(linea, texto)
                elif metodo == 'BoletaAbrir':
                    boleta_abrir()
                elif metodo == 'BoletaItem':
                    descripcion = post_data['parametros']['descripcion']
                    cantidad = post_data['parametros']['cantidad']
                    precio = post_data['parametros']['precio']
                    impuesto = post_data['parametros']['impuesto']
                    calificador = post_data['parametros']['calificador']
                    excentoiva = post_data['parametros']['excentoiva']
                    boleta_item(descripcion, cantidad, precio, impuesto, calificador, excentoiva)
                elif metodo == 'BoletaSubtotal':
                    boleta_subtotal(False)
                elif metodo == 'BoletaPago':
                    tipopago = post_data['parametros']['tipopago']
                    cantidad = post_data['parametros']['cantidad']
                    boleta_pago(tipopago, cantidad)
                elif metodo == 'BoletaCerrar':
                    boleta_cerrar()

# Read sequence from previous session
try:
    hDeviceSeq = open(hashedDevice + '.dat', 'r+b')
except FileNotFoundError:
    hDeviceSeq = open(hashedDevice + '.dat', 'w+b')

hDeviceSeq.seek(0)
deviceSeq = hDeviceSeq.read(1)

if(len(deviceSeq) == 0):
    deviceSeq = 0x81
else:
    deviceSeq = int.from_bytes(deviceSeq, 'little')


# Open printer device
try:
    hPrinter = open(device, 'r+b')
except FileNotFoundError:
    print('No se puede encontrar la impresora en \'' + device + '\'')
    sys.exit()

myServer = HTTPServer((hostName, hostPort), MyServer)

try:
    myServer.serve_forever()
except KeyboardInterrupt:
    pass

myServer.server_close()

# avanzar_papel(5)
# cortar_papel()
# informacion_contadores()
# cierre_z(1)
# cierre_cajero(1)

# for x in range(2):
#     header_set(6, 'Num Cliente: 666')
#     header_set(10, 'Nro. interno boleta: 6969')
#     footer_set(1, 'Atendido por: Juan Soto')

#     boleta_abrir()
#     boleta_item('Pago servicios Floreria Margarita', 1.0, 28590, 0.19, 'M', 'N')
#     boleta_subtotal(False)

#     boleta_pago(1, 28590)
#     boleta_cerrar()

# informacion_fiscal_curso()