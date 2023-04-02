import json
import os
import time
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from instagrapi.types import DirectThread, DirectMessage
import requests


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


def login(username, password, session_file, forceRenew=False):

    def freshClient(username, password, session_file):
        print("Loggins in and refreshing user cookie...")
        client = Client()
        client.login(username, password)
        client.dump_settings(session_file)
        print("Session file saved to " + session_file)
        return client

    if forceRenew or not os.path.exists(session_file):
        return freshClient(username, password, session_file)
    elif os.path.exists(session_file):
        with open(session_file, 'r') as f:
            cookie = f.read()
            return Client(json.loads(cookie))
    else:
        return freshClient(username, password, session_file)


def send_message(client, receiver, content):
    user = client.user_info_by_username(receiver)
    user_id = user.pk
    print(user_id, user)
    thread = client.direct_send(content, [user_id])
    print(f"Sent message to {receiver}!\nContent: {content}")


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
                   session_file="test/instagram_session.json")

    if client.user_id is not None:
        print("Logged in ✨")
        return client
    else:
        print("Renewing session...")
        return login(username, password,
                     session_file="test/instagram_session.json", forceRenew=True)


def getAndPrepDM(client, thread: DirectThread):

    # i is a DirectThread Object
    last_message = thread.messages[0]
    # if there is text content to the last message, get the context
    if last_message.item_type == "text":
        thread = thread.messages
        thread.reverse()
        print("Starting to get context...")
    else:
        print("This message has not text, skipping...")

    return buildContext(client, thread)


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
                    unsummarizedContext = getAndPrepDM(client, i)
                    # send the context to the server
                    summaryRequest = requests.post(
                        json={
                            "text": str(unsummarizedContext)}, url="http://localhost:1234/summarize")
                    if summaryRequest.status_code == 200:
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
                            "context": summaryRequest.text,
                            "last_message": last_message.text,
                        }, url="http://localhost:1234/completion")
                        if completionRequest.status_code == 200:
                            print(completionRequest.text)
                        else:
                            print("Error: failed to get completion from server\nStatus code: {}".format(
                                completionRequest.status_code
                            ))
                    else:
                        print("Error: failed to get summary from server\nStatus code: {}".format(
                            summaryRequest.status_code))

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
                                       forceRenew=True, session_file="test/instagram_session.json")
            count += 1
            time.sleep(5)


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


client = initialisation()
while True:
    test(client)
