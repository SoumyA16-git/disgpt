from flask import Flask
from threading import Thread
import logging

import time
import urllib.request

app = Flask('')
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return "DisGPT is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def ping_itself():
    while True:
        time.sleep(300) # Wait 5 minutes
        try:
            # Ping itself to generate traffic
            urllib.request.urlopen("http://127.0.0.1:8080/").read()
        except Exception:
            pass

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    
    # Start the auto-pinger thread as required by the PRD
    pinger = Thread(target=ping_itself)
    pinger.daemon = True
    pinger.start()
