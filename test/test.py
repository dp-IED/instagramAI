import json
import os
from instagrapi import Client


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


username, password = get_credentials()

if username is None or password is None:
    print("Please enter your username and password in test/secrets.txt")
    exit()
print("Logging in...")

client = login(username, password, session_file="test/instagram_session.json")

if client.user_id is not None:
    print("Logged in ✨")
    client.direct_messages()
else:
    print("Renewing session...")
    login(username, password,
          session_file="test/instagram_session.json", forceRenew=True)
