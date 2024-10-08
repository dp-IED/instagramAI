import spacy
# Called immediately after receiving a message from the user, this function extracts entities

# This function takes a string of text and a list of entity types to extract (defaulting to
# ["PERSON", "ORG", "GPE", "DATE"] if no entity types are specified), loads the small English
# model with Spacy, and then disables all other pipeline components except for the NER component.
# It adds labels for the specified entity types, processes the input text, and extracts named
# entities of the specified types using the doc.ents property. The function then returns a
# list of dictionaries containing the text and label of each extracted entity.



def entity_extraction(text, entity_types=["PERSON", "ORG", "GPE", "DATE"]):
    nlp = spacy.load("en_core_web_sm")
    nlp.disable_pipes([pipe for pipe in nlp.pipe_names if pipe != "ner"])
    for ent in entity_types:
        nlp.get_pipe("ner").add_label(ent)
    doc = nlp(text)
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    return entities
