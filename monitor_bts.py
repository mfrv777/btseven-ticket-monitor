import os
import time
import requests
from bs4 import BeautifulSoup


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

URL = "https://www.ticketmaster.pe/event/bts-world-tour-arirang"

FECHAS = ["07/10", "09/10", "10/10"]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ==========================================================
# TELEGRAM
# ==========================================================

def enviar_telegram(mensaje):

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: faltan los secretos de Telegram.")
        return

    url_telegram = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_TOKEN}/sendMessage"
    )

    datos = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "disable_web_page_preview": False
    }

    try:
        respuesta = requests.post(
            url_telegram,
            data=datos,
            timeout=20
        )

        if respuesta.status_code == 200:
            print("Telegram enviado correctamente.")
        else:
            print(
                "Error enviando Telegram:",
                respuesta.status_code
            )

    except Exception as error:
        print("Error de Telegram:", error)


# ==========================================================
# LEER TICKETMASTER
# ==========================================================

def obtener_texto():

    try:
        respuesta = requests.get(
            URL,
            headers=HEADERS,
            timeout=20
        )

        print(
            "Codigo de respuesta:",
            respuesta.status_code
        )

        if respuesta.status_code != 200:
            return None

        soup = BeautifulSoup(
            respuesta.text,
            "html.parser"
        )

        return soup.get_text(
            " ",
            strip=True
        )

    except Exception as error:

        print(
            "Error leyendo Ticketmaster:",
            error
        )

        return None


# ==========================================================
# OBTENER BLOQUE DE CADA FECHA
# ==========================================================

def obtener_bloque(texto, fecha):

    titulo = "VENTA GENERAL " + fecha
    inicio = texto.find(titulo)

    if inicio == -1:
        return None

    indice_fecha = FECHAS.index(fecha)

    if indice_fecha < len(FECHAS) - 1:

        siguiente_fecha = FECHAS[indice_fecha + 1]
        siguiente_titulo = "VENTA GENERAL " + siguiente_fecha

        fin = texto.find(
            siguiente_titulo,
            inicio + len(titulo)
        )

        if fin == -1:
            fin = inicio + 250

    else:

        posibles_finales = [
            "ACERCA DEL EVENTO",
            "MAPA DE UBICACIONES",
            "TÉRMINOS",
            "TERMINOS"
        ]

        finales = []

        for marcador in posibles_finales:

            posicion = texto.find(
                marcador,
                inicio + len(titulo)
            )

            if posicion != -1:
                finales.append(posicion)

        if finales:
            fin = min(finales)
        else:
            fin = inicio + 250

    return texto[inicio:fin]


# ==========================================================
# DETECTAR ESTADO
# ==========================================================

def detectar_estado(bloque):

    if bloque is None:
        return "NO_ENCONTRADO"

    bloque = bloque.upper()

    # AGOTADO siempre tiene prioridad.
    if "AGOTADO" in bloque:
        return "AGOTADO"

    # Señal más clara.
    if "DISPONIBLE" in bloque:
        return "DISPONIBLE"

    # Posibles nuevas formas de habilitar la compra.
    palabras_compra = [
        "SELECCIONAR",
        "COMPRAR ENTRADAS",
        "ELEGIR ENTRADAS",
        "CONTINUAR"
    ]

    for palabra in palabras_compra:
        if palabra in bloque:
            return "POSIBLE_COMPRA"

    # AGOTADO desapareció, pero no sabemos por qué.
    return "CAMBIO"


# ==========================================================
# OBTENER LOS 3 ESTADOS
# ==========================================================

def obtener_estados():

    texto = obtener_texto()

    if texto is None:
        return None

    estados = {}

    for fecha in FECHAS:

        bloque = obtener_bloque(
            texto,
            fecha
        )

        estados[fecha] = detectar_estado(
            bloque
        )

    return estados


# ==========================================================
# CREAR MENSAJE
# ==========================================================

def crear_mensaje(disponibles, posibles, cambios):

    lineas = []

    if disponibles or posibles:

        lineas.append(
            "🚨💜 BTS LIMA — ALERTA DE ENTRADAS 💜🚨"
        )
        lineas.append("")

        if disponibles:

            lineas.append(
                "✨ Ticketmaster muestra DISPONIBLE:"
            )

            for fecha in disponibles:
                lineas.append(f"🎟️ {fecha}")

        if posibles:

            if disponibles:
                lineas.append("")

            lineas.append(
                "✨ Posible apertura de compra:"
            )

            for fecha in posibles:
                lineas.append(f"🎟️ {fecha}")

        lineas.append("")
        lineas.append(
            "⚡ Entra a Ticketmaster AHORA."
        )
        lineas.append(
            "Las entradas pueden agotarse rapido."
        )

    if cambios:

        if lineas:
            lineas.append("")
            lineas.append("━━━━━━━━━━━━━━━━━━")
            lineas.append("")

        lineas.append(
            "⚠️💜 BTS LIMA — CAMBIO DETECTADO"
        )
        lineas.append("")
        lineas.append(
            "Ya no aparece AGOTADO en:"
        )

        for fecha in cambios:
            lineas.append(f"👀 {fecha}")

        lineas.append("")
        lineas.append(
            "No pude confirmar con certeza "
            "el nuevo estado."
        )
        lineas.append(
            "Revisa Ticketmaster por precaucion."
        )

    lineas.append("")
    lineas.append("🔗 Ticketmaster:")
    lineas.append(URL)
    lineas.append("")
    lineas.append(
        "💜 Corre, ARMY. Revisa rapido."
    )

    return "\n".join(lineas)


# ==========================================================
# PROGRAMA PRINCIPAL
# ==========================================================

def revisar_ticketmaster():

    print("==============================")
    print("      BTS LIMA - MONITOR")
    print("==============================")

    estados = obtener_estados()

    if estados is None:
        print("No se pudo completar la revision.")
        return

    print("\nESTADO ACTUAL\n")

    sospechosas = []

    for fecha in FECHAS:

        estado = estados.get(fecha)

        print(fecha, "->", estado)

        if estado in [
            "DISPONIBLE",
            "POSIBLE_COMPRA",
            "CAMBIO"
        ]:
            sospechosas.append(fecha)

    # Todo normal: no manda nada.
    if not sospechosas:

        print("\nTodo sigue AGOTADO.")
        print("No se enviara Telegram.")
        return

    # Segunda comprobacion para reducir falsas alarmas.
    print(
        "\nPosible cambio detectado. "
        "Esperando 15 segundos para confirmar..."
    )

    time.sleep(15)

    segunda_revision = obtener_estados()

    if segunda_revision is None:
        print("Fallo la segunda comprobacion.")
        return

    disponibles = []
    posibles = []
    cambios = []

    for fecha in sospechosas:

        estado = segunda_revision.get(fecha)

        if estado == "DISPONIBLE":
            disponibles.append(fecha)

        elif estado == "POSIBLE_COMPRA":
            posibles.append(fecha)

        elif estado == "CAMBIO":
            cambios.append(fecha)

        elif estado == "AGOTADO":
            print(
                fecha,
                "volvio a AGOTADO. "
                "No se enviara falsa alarma."
            )

    if disponibles or posibles or cambios:

        mensaje = crear_mensaje(
            disponibles,
            posibles,
            cambios
        )

        enviar_telegram(mensaje)

    else:

        print(
            "La segunda revision no confirmo cambios."
        )


revisar_ticketmaster()
