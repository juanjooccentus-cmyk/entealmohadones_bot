from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# ================================
# 🔐 CONFIGURACIÓN
# ================================
VERIFY_TOKEN = "entre_almohadonesESADzz_564"  # Usa el mismo en Meta Developers
ACCESS_TOKEN = "EAALTG2mgqZBYBPsZBzZA6zlaZB2FM8dZBmqjRdUpkXXcHDf0AGzart1bNKxZAZCyPB3AHSfXV6jhieqB060V6AlIaZAzi1Qri87CpYrnG5XDbdy1a0IXD8U3Gm3cjl6ltuM2jzwRUErRU3PweIG5KVKHWCYOw1Uv0RZCaVbPfpMZBzTx7X6w0B8CL3oRox7GChv40aGWXtjaJCb6cvWTZCBWJJHZB7d2AZAyccZBHwTCAUNMFDZB1IZD"
PHONE_NUMBER_ID = "837114692818661"
API_BUSCADOR = "https://entrealmohadones-api.onrender.com/precio?articulo={}"

# ================================
# 🧩 FORMATEO DE RESPUESTA
# ================================
def formatear_mensaje(resultados, to):
    mensajes = []
    for r in resultados[:3]:  # máximo 3 productos
        msg = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {
                    "type": "image",
                    "image": {"link": r.get("imagen")}
                },
                "body": {
                    "text": f"*{r.get('articulo','')}*\n💶 {r.get('precio','Consultar')}\n📍 {r.get('fuente','')}\n🛍️ {r.get('descripcion','')}"
                },
                "footer": {
                    "text": "Consulta disponibilidad o haz tu pedido online"
                },
                "action": {
                    "buttons": [
                        {
                            "type": "url",
                            "url": r.get("url"),
                            "title": "Ver en tienda 🛒"
                        }
                    ]
                }
            }
        }
        mensajes.append(msg)
    return mensajes


# ================================
# 🌐 WEBHOOK (VERIFICACIÓN + MENSAJES)
# ================================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # ✅ Verificación inicial de Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook verificado correctamente con Meta.")
            return challenge, 200
        else:
            print("❌ Verificación fallida: token incorrecto o modo no válido.")
            return "Verification failed", 403

    elif request.method == "POST":
        # ✅ Mensajes entrantes de WhatsApp
        data = request.get_json()
        print("📩 Mensaje recibido:", json.dumps(data, indent=2, ensure_ascii=False))

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

                        print(f"🔎 Consultando API con: {texto}")
                        resp = requests.get(API_BUSCADOR.format(texto))
                        result = resp.json()
                        print("📦 Respuesta API:", json.dumps(result, indent=2, ensure_ascii=False))

                        if "resultados" in result:
                            mensajes = formatear_mensaje(result["resultados"], phone_number)
                            for m in mensajes:
                                requests.post(
                                    f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages",
                                    headers={
                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                        "Content-Type": "application/json"
                                    },
                                    data=json.dumps(m)
                                )
                                print(f"✅ Enviado mensaje con imagen y botón a {phone_number}")
                        else:
                            texto_fallo = {
                                "messaging_product": "whatsapp",
                                "to": phone_number,
                                "text": {"body": f"No encontré resultados para '{texto}' 😕"}
                            }
                            requests.post(
                                f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages",
                                headers={
                                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                                    "Content-Type": "application/json"
                                },
                                data=json.dumps(texto_fallo)
                            )
                            print(f"⚠️ No se encontraron resultados para {texto}")

        except Exception as e:
            print("❌ Error procesando mensaje:", e)

        return "OK", 200


# ================================
# 🏠 HOME (comprobación rápida)
# ================================
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "🤖 Bot Entre Almohadones activo y escuchando WhatsApp"
    })


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))  # Render define su propio puerto
    app.run(host="0.0.0.0", port=port)
