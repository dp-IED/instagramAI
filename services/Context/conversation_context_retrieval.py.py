import pinecone
import spacy


def conversation_context_retrieval(conversation_id, user_id):
    """
    Retrieves the context and metadata associated with a conversation from Pinecone.

    Args:
        conversation_id (str): The ID of the conversation to retrieve the context for.
        user_id (str): The ID of the user associated with the conversation.

    Returns:
        A tuple of (context, metadata) if the context was successfully retrieved from Pinecone,
        and (False, err?: String) if an error occurred.
    """

    # Initialize the Pinecone client
    pinecone.init(api_key="8e61beee-ca3f-41eb-8be1-735a0f65a95f")

    try:
        # Check if the conversation index exists, and return None if it doesn't
        conversation_index_name = f"SUMMARY_INDEX_{user_id}_{conversation_id}"
        if not pinecone.Index(index_name=conversation_index_name).exists():
            return (False, "Conversation index does not exist")

        # Query Pinecone for the context and metadata
        query_result = pinecone.Index(index_name=conversation_index_name).query(
            queries=[f"Id == '{user_id}_{conversation_id}'"], k=1)
        if len(query_result) > 0:
            context = query_result[0][0].vector.tobytes().decode('utf-8')
            metadata = query_result[0][0].metadata
            return (context, metadata)

        return (False, "No context found for the given conversation ID")

    except Exception as e:
        print(f"Error retrieving context from Pinecone: {e}")
        return (False, e)
