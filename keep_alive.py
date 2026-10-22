from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Hello, I am alive!"

def run():
    # 監聽 0.0.0.0 和 8080 連接埠
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()