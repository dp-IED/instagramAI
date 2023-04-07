from spacy.lang.en.stop_words import STOP_WORDS
import spacy
import heapq
from collections import Counter
import openai
from flask import escape


def summarize(request):
    nlp = spacy.load('en_core_web_sm')
    text = escape(request.json['text'])
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


def completion(request):

    openai.api_key = "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"

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
