import json
import os
import time
import backoff
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeUnknownStep, UserNotFound, ClientError
from instagrapi.types import DirectThread, DirectMessage, UserShort
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
from functions import completion, end_of_session_summary, summarize


class InstagramSession:

    start_time = time.time()

    exceptions = {
        # email/SMS verification due to suspicious activity
        "challenge": ChallengeUnknownStep,
        "clientError": ClientError,
        # refresh needed
        "loginRequired": LoginRequired,
    }

    def __init__(self, uid, duration: int, blacklist: list, auto: bool):

        try:
            cred = credentials.Certificate(
                "/Users/darenpalmer/Desktop/Dev/instagramAI/firebase-key.json")
            firebase_admin.initialize_app(cred)
        except ValueError:
            pass

        self.uid = uid
        self.duration = duration
        self.blacklist = blacklist
        self.auto = auto
        self.db = firestore.client()

        self.username, self.password = self.get_credentials()

        if self.username is None or self.password is None:
            print("No creds found in db")
            exit()
        print("Logging in...")
        self.client = self.login()

        if self.client.user_id is not None:
            print("Logged in ✨")
            self.db.collection(u'users').document(self.uid).set({
                "cookie": self.client.cookie_dict
            }, merge=True)
        else:
            print("Renewing session...")
            self.client = self.login(self, refresh=True)

    def get_credentials(self):
        user = self.db.collection(u'users').document(self.uid).get().to_dict()
        if user is None:
            return "Error: user not found"
        if user.get("username") is not None and user.get("password") is not None:
            print("Found creds in db: {}".format(user.get("username")))
            return user.get("username"), user.get("password")
        else:
            return None, None

    @backoff.on_exception(backoff.expo, ClientError)
    def login(self, refresh=False):
        def forceRenew():
            print("Logging in (with refresh)")
            client = Client()
            client.login(self.username, self.password)
            client.dump_settings("temp.json")
            # send contents of temp.json to user document in db
            with open("temp.json", "r") as f:
                self.db.collection(u'users').document(self.uid).set({
                    "cookie": f.read()}, merge=True)
                f.close()
            # delete temp.json
            os.remove("temp.json")
            return client

        if refresh:
            return forceRenew()

        print("Trying to login using cookie 🍪")

        cookie = self.db.collection(u'users').document(
            self.uid).get().to_dict().get("cookie")

        if cookie is not None:
            client = Client()

            with open("temp.json", "w") as f:
                o = json.dumps(cookie)
                print(o)
                f.write(o)
                f.close()

            temp = client.load_settings("temp.json")
            # delete temp.json
            os.remove("temp.json")
            client.login_by_sessionid(
                sessionid=temp["authorization_data"]["sessionid"])
            print("Logged in using cookie 🍪")
            return client
        else:
            print("No cookie found, logging in...")
            return self.login(refresh=True)

    def buildContext(self, thread: DirectThread):
        context = ""
        progress = 0
        participants = {
            self.client.user_id: self.client.username,
        }

        for i in thread.users:
            i: UserShort = i
            participants[i.pk] = i.username

        if thread is None:
            return "No unread messages"

        for i in thread.messages:
            i: DirectMessage = i
            print("Progress: {}%".format(round(progress*100)))
            try:
                if i.item_type == "text":
                    content = i.text
                    sender = i.user_id
                    if participants.get(sender) is None:
                        sender = participants[sender] = self.client.username_from_user_id(
                            sender)
                    else:
                        sender = participants.get(sender)
                    if sender is not None and content is not None:
                        try:
                            context += f"{sender}: {content}\n"
                        except requests.HTTPError:
                            print("Error: failed to get username from user id")
                    progress += 1/len(thread.messages)
            except Exception as e:
                print(f"Error: failed to retrieve username or content\n{e}")
                progress += 1/len(thread.messages)
                pass
        return context

    def send_message(self, receiver: DirectThread, content: str):
        try:
            print("Sending message: {} to {}".format(
                content, receiver.thread_title))
            message = self.client.direct_send(
                content, thread_ids=[receiver.id])
        except UserNotFound:
            print("Login Failed, trying again...")
            self.client.username, self.client.password = self.get_credentials()
            self.client.relogin()
            self.send_message(self.client, receiver, content)

    def end_of_session(self):
        # get all messages that were generated during the session
        user = self.db.collection(u'users').document(self.uid).get().to_dict()
        if user is None:
            return "Error: user not found"
        if user.get("messages") is not None:
            messages: dict = user.get("messages")
            allMessages = ""
            for i in messages:
                allMessages += i+'\n{}'.format(messages.get(i))
                allMessages += '\n\n\n'

            if self.username is None:
                return None

            recap = end_of_session_summary(self.username, allMessages)

            return recap

        else:
            return "No messages generated during this session"
