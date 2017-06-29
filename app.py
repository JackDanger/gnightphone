"""
G'night, Phone!

Every night this sends a text to your phone and asks you whatever
questions you've configured. You respond before bed and then put the
damned phone away until you get the rest you need.

"""
import json
from flask_twisted import Twisted
from flask import Flask

app = Flask(__name__)
twisted = Twisted(app)


@app.route('/_status')
def status():
    return json.dumps({'status': 'ok'}, indent=4), 200


@app.route('/')
def root():
    return """
        <h2>
            <a href="https://github.com/JackDanger/gnightphone">G'night, phone!</a>
        </h2>
    """


if __name__ == "__main__":
    print("starting")
    app.run(host='0.0.0.0')
