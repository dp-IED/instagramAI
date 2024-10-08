from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.chat_models import ChatOpenAI
import os
import json

class LangChainEngine:
  template = """
  You are {username}. Using the user's prompt and context of previous messages, you must draft 3 versions of a message to be sent to the user's contact. You must respond in the same language as the context (disregard the language used in the user prompt). You must use the same tone as the user's past messages and attempt to resemble their text style. Remember to keep responses short: max 3 sentences (these are Instagram DMs you are responding to). You must return the different propositions and seperate them using a /end token. Remember, this will be parsed on the client side and needs to be presented easily so avoid extra text as much as possible. Context: {context}\n\nUser prompt: {user_message}
  """
  
  def __init__(self, username):
    # register api keys
    with open("creds.json") as f:
      creds = json.load(f)
      token = creds.get("openai_key")
      
    os.environ["OPENAI_API_KEY"] = token
    self.username = username
    self.llm = ChatOpenAI()
    self.prompt = ChatPromptTemplate.from_template(self.template)
    self.output_parser = StrOutputParser()
    # retrieve conversation embeddings from database
    self.conversation_embeddings = {}
  
  def write_message_drafts(self, message:str, context: str):
    setup_and_retrieval = {"username": self.username, "context": context, "user_message": message}
    chain = RunnablePassthrough() | self.prompt | self.llm | self.output_parser

    return chain.invoke(setup_and_retrieval).split("/end")