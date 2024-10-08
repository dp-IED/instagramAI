import json
import os 
import json
import tiktoken # for token counting
import numpy as np
from collections import defaultdict

## Helpers to check compliance with the dataset format (OpenAI)

def testCompliance(dataset):
  # Format error checks
  format_errors = defaultdict(int)
  for ex in dataset:
      if not isinstance(ex, dict):
          format_errors["data_type"] += 1
          continue
          
      messages = ex.get("messages", None)
      if not messages:
          format_errors["missing_messages_list"] += 1
          continue
          
      for message in messages:
          if "role" not in message or "content" not in message:
              format_errors["message_missing_key"] += 1
          
          if any(k not in ("role", "content", "name", "function_call") for k in message):
              format_errors["message_unrecognized_key"] += 1
          
          if message.get("role", None) not in ("system", "user", "assistant", "function"):
              format_errors["unrecognized_role"] += 1
              
          content = message.get("content", None)
          function_call = message.get("function_call", None)
          
          if (not content and not function_call) or not isinstance(content, str):
              format_errors["missing_content"] += 1
      
      if not any(message.get("role", None) == "assistant" for message in messages):
          format_errors["example_missing_assistant_message"] += 1

  if format_errors:
      print("Found errors:")
      for k, v in format_errors.items():
          print(f"{k}: {v}")
  else:
      print("No errors found")

encoding = tiktoken.get_encoding("cl100k_base")

# not exact!
# simplified from https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
def num_tokens_from_messages(messages, tokens_per_message=3, tokens_per_name=1):
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3
    return num_tokens

def num_assistant_tokens_from_messages(messages):
    num_tokens = 0
    for message in messages:
        if message["role"] == "assistant":
            num_tokens += len(encoding.encode(message["content"]))
    return num_tokens

def print_distribution(values, name):
    print(f"\n#### Distribution of {name}:")
    print(f"min / max: {min(values)}, {max(values)}")
    print(f"mean / median: {np.mean(values)}, {np.median(values)}")
    print(f"p5 / p95: {np.quantile(values, 0.1)}, {np.quantile(values, 0.9)}")
    
    
def tokenCount(dataset):
  # Warnings and tokens counts
  n_missing_system = 0
  n_missing_user = 0
  n_messages = []
  convo_lens = []
  assistant_message_lens = []
  overlength = []

  for ex in dataset:
      messages = ex["messages"]
      if not any(message["role"] == "system" for message in messages):
          n_missing_system += 1
      if not any(message["role"] == "user" for message in messages):
          n_missing_user += 1
      n_messages.append(len(messages))
      convo_lens.append(num_tokens_from_messages(messages))
      if num_tokens_from_messages(messages) > 4096:
          overlength.append(messages)
      assistant_message_lens.append(num_assistant_tokens_from_messages(messages))
      
  print("Num examples missing system message:", n_missing_system)
  print("Num examples missing user message:", n_missing_user)
  print_distribution(n_messages, "num_messages_per_example")
  print_distribution(convo_lens, "num_total_tokens_per_example")
  print_distribution(assistant_message_lens, "num_assistant_tokens_per_example")
  n_too_long = sum(l > 4096 for l in convo_lens)
  print(f"\n{n_too_long} examples may be over the 4096 token limit, they will be truncated during fine-tuning") 
  for conv in overlength:
      print(conv) # seq len is 4097, so we need to truncate to 4096 and add a new entry

# Helper to convert the encoding of the string

def encodingUtil(string):
  return string

# walk through the directories in the folder and get all the files that end with .json
files = []
for (dirpath, dirnames, filenames) in os.walk('messages/inbox'):
  for filename in filenames:
    if filename.endswith('.json'):
      files.append(os.sep.join([dirpath, filename]))
      
def handleEncoding(original):
  return original.encode('utf-16', 'surrogatepass').decode('utf-16')

dataset = []

print(len(files))
# only do the first file of the list
for f in files:
  root = {
      'role': 'system',
      'content': 'You are a user called daren talking with some friends on Instagram. Given a message answer using the prompt and using the same language as the context.'
    }
  dataset_entries = [
    [root], 
  ]
  with open(f, 'r') as json_file:
    data = json.load(json_file)
    if len(data['participants']) != 2:
      continue
    i = 0
    context = ""
    prevUser = ""
    
    # we want to make data in this format
    # {'role': 'user', 'content': someone's message}
    # {'role': 'assistant', 'content': _id's response}
    
    while i < len(data['messages']):
      # progress bar
      print("Processing file: {} of {}".format(files.index(f)+1, len(files)))
      print("Processing message: {} of {}".format(i+1, len(data['messages'])))
      print("\r")
      
      nTokens = num_tokens_from_messages(dataset_entries[len(dataset_entries) - 1])
      if nTokens == 4096:
        dataset_entries.append([root])
        nTokens = 0
        
      if "content" in data['messages'][i]:
        if data['messages'][i]['sender_name'] == "daren" and context != "" and prevUser != "daren":
          dataset_entries[len(dataset_entries) - 1].append({
            'role': 'user',
            'content': handleEncoding(context)
          })
          dataset_entries[len(dataset_entries) - 1].append({
            'role': 'assistant',
            'content': handleEncoding(data['messages'][i]['content'])
          })
          context = ""
          prevUser = "daren"
            
        elif data['messages'][i]['sender_name'] == "daren" and prevUser == "daren": # if the user sent two messages in a row, we add it to the context‡
          context += "{}: {}\n".format(handleEncoding(data['messages'][i]['sender_name']), handleEncoding(data['messages'][i]['content']))
          
        elif data['messages'][i]['sender_name'] != "daren" :
          prevUser = data['messages'][i]['sender_name']
          context += "{}: {}\n".format(handleEncoding(data['messages'][i]['sender_name']), handleEncoding(data['messages'][i]['content']))

      i += 1
      
  for entry in dataset_entries:
    if isinstance(entry, list) and len(entry) > 1:
      dataset.append({
        'messages': entry
      })

dataset.reverse()
print(len(dataset))

testCompliance(dataset)
tokenCount(dataset)

# Export dataset to a JSON Lines file
output_file = "/Users/darenpalmer/Desktop/Dev/instagramAI/dataset.jsonl"  # Ensure the file extension is .jsonl
with open(output_file, 'w', encoding='utf-8') as f:
    for entry in dataset:
        # Write each entry as a separate line in the file
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
print(f"Dataset exported to {output_file} in JSON Lines format")
