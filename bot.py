from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# ================================
# 🔐 CONFIGURACIÓN
# ================================
VERIFY_TOKEN = "entrealmohadones_secret"  # Usa el mismo en Meta Developers
ACCESS_TOKEN = "{{ACCESS_TOKEN_DE_META}}"  # lo pondrás luego en Meta
PHONE_NUMBER_ID = "{{PHONE_NUMBER_ID}}"    # lo copias de tu panel de WhatsApp Cloud API
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
# 🌐 WEBHOOK
# ================================
@app.route("/webhook", methods=["GET"])
def verify():
    """Verificación inicial de Meta"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
    return "Verification failed", 403


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

                    # Buscar en la API de precios
                    resp = requests.get(API_BUSCADOR.format(texto))
                    result = resp.json()

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
    except Exception as e:
        print("Error:", e)

    return "OK", 200


@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Bot Entre Almohadones activo y escuchando WhatsApp"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
