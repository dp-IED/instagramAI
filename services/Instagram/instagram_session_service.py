import json
import os
import time
from typing import List
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeUnknownStep, UserNotFound, ClientError
from instagrapi.types import DirectThread, DirectMessage, UserShort
from services.LangChain.langchain_engine_service import LangChainEngine
import requests

class InstagramSession:

    start_time = time.time()

    def __init__(self, blacklist: list = []):
        self.selected_thread: DirectThread = None
        self.blacklist = blacklist

        self.username, self.password = self.get_credentials()

        if self.username is None or self.password is None:
            print("Add your creds in creds.json")
            exit()
            
        print("Logging in...")
       
        self.client, self.inbox = self.login()
        self.username = self.client.username
        self.ai = LangChainEngine(self.username)
        
        if self.client is None:
            print("Error: Failed to login")
            exit()

        if self.client is not None:
            print("(Logged in) Welcome back {} ✨".format(self.client.username))
            
    def get_credentials(self):
        try: 
            with open("creds.json") as f:
                creds = json.load(f)
            return creds.get("username"), creds.get("password")
        except FileNotFoundError:
            print("Error: creds.json not found")
            return None, None
    
    def login(self):
        if os.path.exists("session.json"):
            cl = Client()
            cl.load_settings("session.json")
            cl.login(self.username, self.password)
            self.client = cl
            try: 
                inbox = self.get_unread_inbox()
                if inbox is not None:
                    print("Reusing session...")
                    return cl, inbox
            except LoginRequired:
                cl = Client()   
                cl.login(self.username, self.password)
                cl.dump_settings("session.json")
                self.client = cl
                inbox = self.client.direct_threads()
                
                if inbox is not None:
                        return cl, inbox
                else:
                    return None, None
        
    def get_unread_inbox(self, count = None) -> List[DirectThread]:
        if count is not None:
            return self.client.direct_threads(selected_filter="unread")
        return self.client.direct_threads(selected_filter="unread", amount=count)

    def get_contact_map(self) -> dict:
        contact_map = {}
        for conv in self.client.direct_threads():
            contact_map[conv.thread_title] = {
                "conversationID": conv.id,
                "users": [i.username for i in conv.users]
            }
        return contact_map

    def get_context(self, id: int) -> str:
        context = []
        progress = 0
        participants = {
            self.client.user_id: self.client.username,
        }

        thread = self.client.direct_thread(id)

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
                            context.append(f"{sender}: {content}")
                        except requests.HTTPError:
                            print("Error: failed to get username from user id")
                    progress += 1/len(thread.messages)
                else:
                    context.append(f"{self.client.username_from_user_id(i.user_id)} sent a {i.item_type}")
                    progress += 1/len(thread.messages)
            except Exception as e:
                print(f"Error: failed to retrieve username or content \n{e}")
                progress += 1/len(thread.messages)
                pass
        return reversed(context)

    def send_message(self, content: str) -> bool:
        if self.selected_thread is None:
            print("Error: No thread selected")
            return False
        
        
        try:
            print("Sending message: {} to {}".format(
                content, self.selected_thread.thread_title))
            message = self.client.direct_send(
                content, thread_ids=[self.selected_thread.id])
            return True
        except UserNotFound:
            print("Login Failed, trying again...")
            self.client.username, self.client.password = self.get_credentials()
            self.client.relogin()
            self.send_message(self.client, content)
        except Exception as e:
            print(str(e))
            return False

    def generate_drafts(self, prompt):
        if prompt is None:
            print("Error: No prompt provided")
            return
        
        if self.selected_thread is None:
            print("Error: No thread selected")
            return
        print("Generating drafts...")
        context = self.get_context(self.selected_thread.id)
        if context is None:
            print("Error: Failed to retrieve context")
            return
        return self.ai.write_message_drafts(
            context=context, message=prompt)
        
    def printDirectMessage(self, message: DirectMessage): 
        if message.item_type == "text":
            print("{}: {}".format(self.client.username_from_user_id(message.user_id), message.text))
        else:
            print("{} sent a {}".format(self.client.username_from_user_id(message.user_id), message.item_type))
        
    