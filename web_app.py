from flask import Flask, jsonify, request
import threading
import os
from bot import bot, scheduler, send_updates, get_proxies
from supabase_db import get_proxies as db_get_proxies

app = Flask(__name__)

# Bot status tracking
bot_status = {"running": False, "scheduler": False}

@app.route('/')
def home():
    return jsonify({
        "status": "healthy",
        "service": "TgProxBot API",
        "bot_running": bot_status["running"],
        "scheduler_running": bot_status["scheduler"]
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/status')
def api_status():
    return jsonify(bot_status)

@app.route('/api/proxies')
def api_proxies():
    try:
        count = request.args.get('count', 10, type=int)
        proxies = db_get_proxies(min(count, 50))
        return jsonify({"proxies": proxies, "count": len(proxies)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/send-update', methods=['POST'])
def api_send_update():
    try:
        send_updates()
        return jsonify({"message": "Update sent successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_bot():
    global bot_status
    try:
        from bot import main as bot_main
        bot_status["running"] = True
        bot_main()
    except Exception as e:
        print(f"Bot error: {e}")
        bot_status["running"] = False

if __name__ == '__main__':
    # Start bot in background thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)