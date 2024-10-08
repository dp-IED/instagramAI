import pinecone
import spacy
import numpy as np


def send_summary_to_client(summary_point, conversation_id, user_id, metadata=None):
    """
    Sends a summary point to the dynamic summaries service for the given conversation and user IDs.

    Args:
        summary_point (str): The summary point to add to the dynamic summary.
        conversation_id (str): The ID of the conversation to update.
        user_id (str): The ID of the user associated with the conversation.
        metadata (dict): A dictionary of entities associated with the message.

    Returns:
        A tuple of (True, None) if the summary point was successfully added to the index,
        and (False, error_message) if an error occurred.
    """

    # Initialize the Pinecone client
    pinecone.init(api_key="8e61beee-ca3f-41eb-8be1-735a0f65a95f")

    try:
        # Check if the user index exists, and create it if it doesn't
        user_index_name = f"USER_INDEX_{user_id}"
        if not pinecone.Index(index_name=user_index_name).exists():
            pinecone.Index(index_name=user_index_name).create(dim=512)

        # Add a record of the conversation index to the user index
        conversation_index_name = f"SUMMARY_INDEX_{user_id}_{conversation_id}"
        pinecone.Index(index_name=user_index_name).upsert(
            Ids=[conversation_index_name], Vectors=[conversation_index_name], overwrite=False)

        # Initialize the Pinecone index for the current conversation
        if not pinecone.Index(index_name=conversation_index_name).exists():
            pinecone.Index(index_name=conversation_index_name).create(dim=512)
            summary_point_vector = pinecone.Index(
                index_name=conversation_index_name).encode(np.array([summary_point]))[0]
            pinecone.Index(index_name=conversation_index_name).upsert(
                Ids=[f"{user_id}_{conversation_id}"], Vectors=[summary_point_vector], metadata=metadata, overwrite=False)
        else:
            existing_summary_vector = pinecone.Index(index_name=conversation_index_name).query(
                queries=[f"Id == '{user_id}_{conversation_id}'"], k=1)[0][0].vector
            summary_point_vector = pinecone.Index(
                index_name=conversation_index_name).encode(np.array([summary_point]))[0]
            existing_summary = existing_summary_vector[:-
                                                       1] + summary_point_vector
            pinecone.Index(index_name=conversation_index_name).upsert(
                Ids=[f"{user_id}_{conversation_id}"], Vectors=[existing_summary], metadata=metadata, overwrite=True)

        return (True, None)

    except Exception as e:
        error_message = str(e)
        return (False, error_message)
