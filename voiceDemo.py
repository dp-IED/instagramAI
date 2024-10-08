from services.Instagram.instagram_session_service import InstagramSession, printDirectMessage
from gtts import gTTS
import os

session = InstagramSession()

def text_to_speech(text):
    tts = gTTS(text=text, lang='en')
    filename = "speech.mp3"
    tts.save(filename)
    os.system(f"afplay {filename}")
  
for thread in session.inbox:
  if thread.muted:
    continue
  
  if thread.last_activity_at.timestamp() < session.start_time - 60 * 60 * 24 * 7: # 7 days
    continue
  
  count = 0
  while thread.messages[count].user_id != session.client.user_id:
    printDirectMessage(thread.messages[count])
    count += 1
  
  text_to_speech(f"New message from {thread.thread_title}: {''.join([i.text for i in thread.messages[count:]])}")
  
  
  