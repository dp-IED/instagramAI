import json
import os
import string
import time
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from instagrapi.types import DirectThread, DirectMessage
import requests
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from flask import escape


def get_credentials():
    try:
        with open("test/secrets.txt", "r") as f:
            username = f.readline().strip()
            password = f.readline().strip()
            f.close()
    except FileNotFoundError:
        username = None
        password = None

    return username, password


def login(username, password, db, forceRenew=False):

    def freshClient(username, password, db):
        print("Loggins in and refreshing user cookie...")
        client = Client()
        client.login(username, password)
        client.dump_settings(db)
        print("Session file saved to " + db)
        return client

    if forceRenew or not os.path.exists(db):
        return freshClient(username, password, db)
    elif os.path.exists(db):
        with open(db, 'r') as f:
            cookie = f.read()
            return Client(json.loads(cookie))
    else:
        return freshClient(username, password, db)


def send_message(client, receiver, content):
    try:
        user = client.user_info_by_username(receiver)
        user_id = user.pk
        print(user_id, user)
        thread = client.direct_send(content, [user_id])
        print(f"Sent message to {receiver}!\nContent: {content}")
    except LoginRequired:
        print("Login Failed, trying again...")
        client.username, client.password = get_credentials()
        client.relogin()
        send_message(client, receiver, content)


def send_test_message(client):

    receiver = "daren_palmer"
    content = "test"

    send_message(client, receiver, content)


def initialisation():
    username, password = get_credentials()

    if username is None or password is None:
        print("Please enter your username and password in test/secrets.txt")
        exit()
    print("Logging in...")

    client = login(username, password,
                   db="test/instagram_session.json")

    if client.user_id is not None:
        print("Logged in ✨")
        return client
    else:
        print("Renewing session...")
        return login(username, password,
                     db="test/instagram_session.json", forceRenew=True)


def filterThreads(client, thread: DirectThread):
    last_message = thread.messages[0]

    # check if threads.users is in blacklist
    def blacklistFilter():
        blacklist = []
        for user in thread.users:
            if user.username in blacklist:
                return False
        return True

    # if there is text content to the last message, get the context
    if last_message.item_type == "text" and blacklistFilter():
        thread = thread.messages
        thread.reverse()
        print("Starting to get context...")
    else:
        print("This message has not text, skipping...")

    return buildContext(client, thread), last_message


def buildContext(client: Client, thread):
    context = ""
    progress = 0
    parties = {
        client.user_id: client.username,
    }
    for i in thread:
        print("Progress: {}%".format(progress*100))
        if i.item_type == "text":
            content = i.text
            sender = i.user_id
            if parties.get(sender) is None:
                parties[sender] = client.username_from_user_id(sender)
            else:
                sender = parties.get(sender)
            if sender is not None and content is not None:
                try:
                    context += f"{sender}: {content}\n"
                except requests.HTTPError:
                    print("Error: failed to get username from user id")
                progress += 1/len(thread)
            else:
                print("Error: failed to retrieve username or content")
                progress += 1/len(thread)
                pass
    return context


def getSummary(context):
    summaryRequest = requests.post(
        json={
            "text": str(context)}, url="http://localhost:1234/summarize")
    if summaryRequest.status_code == 200:

        return summaryRequest.text
    else:
        return (None, summaryRequest.status_code)


def getCompletion(summary, last_message):

    # get completion from server
    name = "Daren Palmer"
    age = 18
    position = "Student"
    company = "University College London (UCL)"
    location = "London, UK"
    uname = "daren_palmer"
    completionRequest = requests.post(json={
        "name": name,
        "age": age,
        "position": position,
        "company": company,
        "location": location,
        "uname": uname,
        "context": summary,
        "last_message": last_message,
    }, url="http://localhost:1234/completion")
    if completionRequest.status_code == 200:
        return completionRequest.text
    else:
        return (None, completionRequest.status_code)


def test(client):
    print("New Test Session ⚠️")
    c = int(
        input("[1] - Send a test message to yourself\n[2] - Listen for new messages\n"))
    if c == 1:
        try:
            send_test_message(client)
        except LoginRequired:
            print("Login Failed, trying again...")
            client.username, client.password = get_credentials()
            client.relogin()
    elif c == 2:
        count = 0
        while count <= 12:
            try:
                for i in client.direct_threads(
                    selected_filter="unread"
                ):
                    # filter the threads: if it's blacklisted, skip it, if the last message is not text, skip it
                    unsummarizedContext, last_message = filterThreads(
                        client, i)
                    # summarize the context
                    summmary = getSummary(unsummarizedContext)
                    completion = getCompletion(summmary, last_message)
                    return completion
            except LoginRequired:
                print("Login Failed, trying again...")
                client.username, client.password = get_credentials()
                if client.username is None or client.password is None:
                    print("Please enter your username and password in test/secrets.txt")
                    exit()
                else:
                    try:
                        client.relogin()
                    except LoginRequired:
                        client = login(client.username, client.password,
                                       forceRenew=True, db="test/instagram_session.json")
            count += 1
            time.sleep(5)


class Session:

    def initialisation():
        username, password = get_credentials()

        if username is None or password is None:
            print("Please enter your username and password in test/secrets.txt")
            exit()
        print("Logging in...")

        client = login(username, password,
                       db)

        if client.user_id is not None:
            print("Logged in ✨")
            return client
        else:
            print("Renewing session...")
            return login(username, password,
                         db, forceRenew=True)

    def send_message(client, receiver, content):
        try:
            user = client.user_info_by_username(receiver)
            user_id = user.pk
            print(user_id, user)
            thread = client.direct_send(content, [user_id])
            print(f"Sent message to {receiver}!\nContent: {content}")
        except LoginRequired:
            print("Login Failed, trying again...")
            client.username, client.password = get_credentials()
            client.relogin()
            send_message(client, receiver, content)

    def __init__(self, username: string, password: string, duration: int, userInfo: dict):
        cred = credentials.ApplicationDefault()
        try:
            firebase_admin.initialize_app(cred)
        except ValueError:
            pass

        db = firestore.client()

        request_json = request.form
        uid = request_json['uid']

        cred = credentials.ApplicationDefault()
        try:
            firebase_admin.initialize_app(cred)
        except ValueError:
            pass

        db = firestore.client()
        self.client = login(username, password)
        self.duration = duration
        self.userInfo = userInfo
