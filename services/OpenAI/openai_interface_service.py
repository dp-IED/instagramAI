from typing import Any
from openai import OpenAI

import os
import re
import json


class OpenAIInterfaceService:
    def __init__(self, username):
        self.username = username
        with open("creds.json") as f:
                creds = json.load(f)
        self.key = creds.get("openai_key")
        self.client = OpenAI(api_key
        =self.key)
        if self.key is None:
            print("Error: OpenAI key not found")
            exit()
        assert self.client is not None


    def get_chat_summary_brief(self, uname, context):
        completion = self.client.chat.completions.create(model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
                "content": "You must summarize the following chat conversations in one or two sentences max (e.g. Daniela wants you to send her the presentation for Monday's meeting). You are the personal assistant of {}. \n\n\n {}".format(uname)},
            {"role": "user", "content": "Messages: {}".format(
                context)},
        ])["choices"][0]["message"]["content"]
        return completion

    def match_message_to_a_conversationID(self, contact_dict: dict, prompt: str) -> str or bool:
        completion = self.client.chat.completions.create(model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
                "content": "You will be given a python dict with keys as contact names and values of conversationIDs. You must determine where the user request must be routed. Return the conversationID of the conversation that matches the request provided. Be careful not to return the conversationID of a group the targeted user is in if the prompt doesn't explicitly mention the group name. If you are unsure which conversation to pick, pick the one with only the user. Follow this example that doesn't use any extra words: 'id: 1234567890'"},
            {"role": "user", "content": "DICTIONARY: {}\n\nUser request: {}".format(
                contact_dict, prompt)},
        ])["choices"][0]["message"]["content"]
        print(completion)
        match = re.search(r"(\d+)", completion)
        try:
            id = match.group(1)
            return id
        except:
            return False

    def write_message_drafts(self, context, prompt):
        uname = self.username
        payload = "Context: {}\n\nUser prompt: {}".format(context, prompt)
        print(payload)
        completion = self.client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system",
             "content": "You are {}. Using the user's prompt and context of previous messages, you must draft several versions of a message to be sent to the user's contact. Remember to keep responses short(these are Instagram DMs you are responding to). You must respond in the same language as the context does (even if the prompt is in english/another language). You must provide different variations of tone (casual, formal, friendly, etc.). Do not specify which tone you are using. You must return the different propositions and seperate them using a /end token. Remember, this will be parsed on the client side and needs to be presented easily so avoid extra text as much as possible. Follow this example that doesn't use any bulletpoints and extra words: Hi Brian, how are you doing ? Can we meet at 1pm instead ?/end Hello Brian, unfortunately I cannot meet before noon. I suggest 1pm, does that work for you ?/end)".format(uname, uname)},
            {"role": "user",
                "content": payload},
        ])["choices"][0]["message"]["content"]
        return completion.split("/end")

        # find a way to detech when it's the 1+n attempt of a user to find a conversationID in order to reinforce the map
    def create_embeddings():
        pass