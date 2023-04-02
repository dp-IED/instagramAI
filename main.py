from datetime import time
import random
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from instagram_private_api import Client, ClientError, ClientCookieExpiredError, ClientLoginRequiredError
from flask import jsonify
import json
import os
from spacy.lang.en.stop_words import STOP_WORDS
import spacy
import heapq
from collections import Counter
import openai
from flask import Flask, request
from flask import escape

# create a Flask instance

app = Flask(__name__)

with open("OpenAI.txt", "r") as f:
    openai.api_key = f.read()
    f.close()


@app.route('/summarize', methods=['POST'])
def summarize():
    nlp = spacy.load('en_core_web_sm')
    text = str(escape(request.json['text']))
    num_sentences = 3
    # Tokenize the text and remove stop words
    doc = nlp(text.lower())
    sentences = [sent.text for sent in doc.sents]

    word_frequencies = Counter(
        [word.text for word in doc if not word.is_stop and not word.is_punct])

    # Calculate sentence scores based on word frequencies
    sentence_scores = {}
    for i, sent in enumerate(sentences):
        for word in nlp(sent.lower()):
            if word.text in word_frequencies:
                if i not in sentence_scores:
                    sentence_scores[i] = word_frequencies[word.text]
                else:
                    sentence_scores[i] += word_frequencies[word.text]

    # Select the top N sentences with highest scores
    summary_sentences = heapq.nlargest(
        num_sentences, sentence_scores, key=sentence_scores.get)
    summary_sentences = sorted(summary_sentences)
    summary = [sentences[i] for i in summary_sentences]
    print("Summary provided 🦾")
    return ' '.join(summary)


@app.route('/completion', methods=['POST'])
def completion():
    if request.json is not None:
        name = request.json['name']
        age = request.json['age']
        position = request.json['position']
        company = request.json['company']
        location = request.json['location']
        uname = request.json['uname']
        context = request.json['context']
        last_message = request.json['last_message']
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are {}, an {} year old {} at {}. You live in {}, you. You are chatting with {}. The context is: {}. Be friendly, most messages will be nice so look out for irony. If an event is being scheduled, try to get enough information to add it to your calendar.".format(
                    name, age, position, company, location, uname, context)},
                {"role": "user", "content": "Last message: {}".format(
                    last_message)},
            ]
        )["choices"][0]["message"]["content"]
        print("Sending completion 🧠")
        return completion


def get_dms(api, db, uid):
    dms = api.direct_v2_inbox()['inbox']['threads']
    print("Getting DMs 📩")
    new_dms = []
    for dm in dms:
        print(dm)
        if dm['has_newer']:
            print("New DMs found 📩")
            new_dms.append(dm)
    if new_dms:
        db.collection(u'users').document(uid).set({"dms": new_dms}, merge=True)


@app.route('/login', methods=['POST'])
def login():

    request_json = request.form

    if not request_json or 'username' not in request_json or 'password' not in request_json:
        return jsonify({'error': 'Missing credentials'}), 400

    username = request_json['username']
    password = request_json['password']
    uid = request_json['uid']

    cred = credentials.ApplicationDefault()
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass

    db = firestore.client()

    # backup the current settings for future use

    def saveCreds(api, db, uid):
        settings = api.settings
        db.collection(u'users').document(uid).set({
            "cookie": settings
        }, merge=True)

    def session(api, db, uid):
        # Start session
        start = time.time()
        length_of_session_in_MS = request_json["time"]
        while start + length_of_session_in_MS > time.time():
            random_time = random.randint(60, 120)
            get_dms(api, db, uid)
            time.sleep(random_time)

    try:
        # 1. Try to get the user's cookie from the database.
        cookie = db.collection(u'users').document(
            uid).get().to_dict()['cookie']
    except KeyError:
        cookie = None
    # 2. If the cookie is not None, then try to use it to login.
        if cookie is not None:
            device_id = cookie.get('device_id')
            try:

                api = Client(username, password, settings=cookie,
                             device_id=device_id)
                status = "Logged in to Instagram 📲"
                session(api, db, uid)
                return "listening for new dms", 200

    # 3. If the cookie has expired, then use the on_login callback to update the cookie in the database.
            except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
                print(
                    'ClientCookieExpiredError/ClientLoginRequiredError: {0!s}'.format(e))

    # 4. If the cookie is None, then login with the user's credentials.
        else:
            api = Client(
                username, password,
                on_login=lambda x: saveCreds(x, db, uid))
            session(api, db, uid)
            print("Listening Ended... Please refresh the page to start again 📲")
        return "listening for new dms", 200
    except ClientError as e:
        # 5. If the login fails, then return a 400 error.
        return jsonify({'error': f'Login failed: {e}'}), 400


if __name__ == '__main__':
    app.run(port=1234)
