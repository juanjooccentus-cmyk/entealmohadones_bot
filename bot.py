from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# =========================================================
# 🔐 CONFIGURACIÓN DESDE VARIABLES DE ENTORNO (Render)
# =========================================================
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "entre_almohadonesESADzz_564")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "EAALTG2mgqZBYBPmo4wILr1hh7DvyZAxmYAl4cMWAx3WmfZASvkktLLZCZBEx3VJceLBJkRWZC5L71w1Mi5geRWY8KZCyzcalSMc29DS1WQxjyr5OlzwLyxAGohpH7VAoleT9CrZC9ZC5eHOMEnh8wDVWZBWbV1Iu8S6WyYBZA4vHQPLk6Uai0quDyAZAh48BswbDN4N2nfMmzAE1ATF2GdciEM55s35T1WEJMXvmbAgOgIvskwZDZD")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "837114692818661")
API_BUSCADOR = os.environ.get(
    "API_BUSCADOR",
    "https://www.entrealmohadones.es/api_local.php?q={}"
)

# =========================================================
# 🧩 FORMATEO DE RESPUESTA
# =========================================================
def formatear_mensaje(resultados, to):
    """Convierte resultados en mensajes interactivos de WhatsApp."""
    mensajes = []
    for r in resultados[:3]:  # máximo 3 productos
        articulo = r.get('articulo', 'Producto')
        precio = r.get('precio', 'Consultar')
        fuente = r.get('fuente', 'Online')
        descripcion = r.get('descripcion', '')
        url = r.get('url', '')
        imagen = r.get('imagen', '')

        msg = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {
                    "type": "image",
                    "image": {"link": imagen}
                },
                "body": {
                    "text": f"*{articulo}*\n💶 {precio}\n📍 {fuente}\n{descripcion}"
                },
                "footer": {"text": "Consulta disponibilidad o haz tu pedido online"},
                "action": {
                    "buttons": [
                        {
                            "type": "url",
                            "url": url,
                            "title": "Ver en tienda 🛒"
                        }
                    ]
                }
            }
        }
        mensajes.append(msg)
    return mensajes


# =========================================================
# 🌐 WEBHOOK - VERIFICACIÓN META
# =========================================================
@app.route("/webhook", methods=["GET"])
def verify():
    """Verificación inicial con Meta Developers"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
    return "Verification failed", 403


# =========================================================
# 📩 WEBHOOK - RECEPCIÓN DE MENSAJES
# =========================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    """Recibe mensajes desde WhatsApp"""
    data = request.get_json()

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" in value:
                    message = value["messages"][0]
                    phone_number = message["from"]
                    texto = message.get("text", {}).get("body", "").strip().lower()

                    if not texto:
                        continue

                    # 🔍 Consulta al buscador híbrido (Entre Almohadones + proveedores)
                    resp = requests.get(API_BUSCADOR.format(texto))
                    if resp.status_code != 200:
                        raise Exception(f"Error API {resp.status_code}: {resp.text}")

                    result = resp.json()
                    resultados = result.get("resultados", [])

                    if resultados:
                        mensajes = formatear_mensaje(resultados, phone_number)
                        for m in mensajes:
                            requests.post(
                                f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages",
                                headers={
                                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                                    "Content-Type": "application/json"
                                },
                                data=json.dumps(m)
                            )
                    else:
                        texto_fallo = {
                            "messaging_product": "whatsapp",
                            "to": phone_number,
                            "text": {
                                "body": f"No encontré resultados para '{texto}' 😕\n\nPrueba con otro nombre o revisa nuestra web 🏠"
                            }
                        }
                        requests.post(
                            f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages",
                            headers={
                                "Authorization": f"Bearer {ACCESS_TOKEN}",
                                "Content-Type": "application/json"
                            },
                            data=json.dumps(texto_fallo)
                        )

    except Exception as e:
        print("❌ Error en webhook:", e)

    return "OK", 200


# =========================================================
# 🏠 HOME (Diagnóstico rápido)
# =========================================================
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "🤖 Bot Entre Almohadones activo y escuchando WhatsApp",
        "api_buscador": API_BUSCADOR
    })


# =========================================================
# 🚀 ARRANQUE DEL SERVIDOR FLASK
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
