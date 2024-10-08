from services.OpenAI.openai_interface_service import OpenAIInterfaceService
from langdetect import detect
from transformers import pipeline


client = OpenAIInterfaceService("daren_palmer")


def summarize(uname, text: str):
    summarizer = pipeline("summarization")
    summary = summarizer(f"You are {uname}\ {text}", max_length=130,
                         min_length=30, do_sample=False)
    return summary


def completion(name, age, position, company, location, friend, context, last_message):
    print("Answering context: {}".format(context))
    completion = client.chat.completions.create(model="gpt-3.5-turbo", # replace with Olama
    messages=[
        {"role": "system", "content": "You are {}, an {} year old {} at {}. You live in {}. You are in an instagram conversation with {}. Use chat form when answering (no signatures or 'kind regards'/'sincerely', use emojis wisely). Be friendly, funny and don't be scared to be edgy/use irony. Do not set any plans, do not schedule any meetings or lunches etc. Ask to answer at a later time if you are lacking essential information to answer the message (eg. the date of an event, the name of a file, the members of a team, other info that. Avoid answers like 'I do not understand what you are saying, please clarify', use the context as much as possible. Do not include your username in the answers, simply respond with the content of the message you would like to send. Use the context extensively and avoid answers like 'I am unsure what you mean'/'could you rephrase'Answer in {}).".format(
            name, age, position, company, location, friend, detect(context))},
        {"role": "user", "content": "The previous messages: {}\n This is the last message you received: {}\nAnswer in {}".format(
            context, last_message, detect(context))},
    ])["choices"][0]["message"]["content"]
    print("Sending completion 🧠")
    return completion


def end_of_session_summary(username, allMessages):
    completion = client.get_chat_summary_brief(username, allMessages)
    return completion
