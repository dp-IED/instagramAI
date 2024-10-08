import pinecone
from services.OpenAI.openai_interface_service import OpenAIInterfaceService
import json

client = OpenAIInterfaceService("daren_palmer")

def update_pinecone(user_id, id, content, metadata=None, override=False):
    with open("creds.json") as f:
        creds = json.load(f)
    pinecone.init(api_key=creds.get("pinecone_key"),
                  environment="us-central1-gcp")
    user_index_name = f"user-{user_id}"
    if user_index_name not in pinecone.list_indexes():
        pinecone.create_index(name=user_index_name, dimension=512)
    user_index = pinecone.Index(index_name=user_index_name)

    user_index.upsert(ids=[id], vectors=[content],
                      overwrite=override, metadata=metadata)

if __name__ == "__main__":
    update_pinecone("123", "456787654567", "Hi Dad", {"123": "123"}, True)
