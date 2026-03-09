from flask import Flask

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def shutdown(path):
    return "This service is down for maintenance.", 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
