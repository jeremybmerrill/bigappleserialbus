from flask import Flask, send_from_directory
app = Flask(__name__, static_folder='static')
app.debug = True

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/<path:filename>')
def send_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route("/apikey")
def hello():
  apikey = open("../apikey.txt", 'r').read().strip()
  return apikey

if __name__ == "__main__":
    app.run()