import time
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from instagrapi.types import DirectThread, DirectMessage
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests


class Session:

    def __init__(self, uid, duration: int, userInfo: dict):

        start_time = time.time()

        cred = credentials.ApplicationDefault()

        try:
            firebase_admin.initialize_app(cred)
        except ValueError:
            pass

        self.uid = uid
        self.duration = duration
        self.userInfo = userInfo
        self.db = firestore.client()

        self.username, self.password = self.get_credentials()

        if self.username is None or self.password is None:
            print("No creds found in db")
            exit()
        print("Logging in...")

        self.client = self.login(self)
        client = self.login(self)

        if client.user_id is not None:
            print("Logged in ✨")
        else:
            print("Renewing session...")
            self.client = self.login(self, forceRenew=True)

    def get_credentials(self):
        user = self.db.collection(u'users').document(self.uid).get().to_dict()
        if user is None:
            return "Error: user not found"
        if user.get("username") is not None and user.get("password") is not None:
            return user.get("username"), user.get("password")
        else:
            return None, None

    def login(self, forceRenew=False):
        def forceRenew():
            client = Client()
            client.login(self.username, self.password)
            client.dump_settings("temp.json")
            # send contents of temp.json to user document in db
            with open("temp.json", "r") as f:
                self.db.collection(u'users').document(self.uid).update({
                    "cookie": f.read()}, merge=True)
                f.close()
            return client

        if forceRenew:
            return forceRenew()
        else:
            cookie = self.db.collection(u'users').document(
                self.uid).get().to_dict().get("cookie")
            if cookie is not None:
                # write cookie to temp.json
                client = Client()

                with open("temp.json", "w") as f:
                    f.write(cookie)
                    f.close()

                client.load_settings("temp.json")
                return client
            else:
                self.login(forceRenew=True)

    def filterThreads(self, thread: DirectThread):
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

        return self.buildContext(self.client, thread), last_message

    def buildContext(self, thread):
        context = ""
        progress = 0
        parties = {
            self.client.user_id: self.client.username,
        }
        for i in thread:
            i: DirectMessage = i
            print("Progress: {}%".format(progress*100))
            if i.item_type == "text":
                content = i.text
                sender = i.user_id
                if parties.get(sender) is None:
                    parties[sender] = self.client.username_from_user_id(sender)
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

    def getSummary(self, context):
        summaryRequest = requests.post(
            json={
                "text": str(context)}, url=self.host)
        if summaryRequest.status_code == 200:

            return summaryRequest.text
        else:
            return (None, summaryRequest.status_code)

    def getCompletion(self, summary, last_message):

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
        }, url=self.host)
        if completionRequest.status_code == 200:
            return (completionRequest.text, completionRequest.status_code)
        else:
            return (None, completionRequest.status_code)

    def send_message(self, receiver, content):
        try:
            user = self.client.user_info_by_username(receiver)
            user_id = user.pk
            thread = self.client.direct_send(content, [user_id])
        except LoginRequired:
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

            end_of_session_summary = requests.post(json={
                "username": self.username,
                "allMessages": allMessages,
            }, url=f"{self.host}/end_of_session_summary")

            if end_of_session_summary.status_code == 200:
                return end_of_session_summary.text
        else:
            return "No messages generated during this session"
