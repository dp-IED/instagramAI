from services.Instagram.instagram_session_service import InstagramSession
import inquirer

session = InstagramSession()
choices = [thread.thread_title for thread in session.inbox]

_prompt = inquirer.List('thread',
                message="Select a thread",
                choices=choices,
            )
  
answers = inquirer.prompt([_prompt])

session.selected_thread = session.inbox[choices.index(answers["thread"])]

print("Selected thread: {}".format(session.selected_thread.thread_title))
session.printDirectMessage(session.selected_thread.messages[0])
print("What would you like to do? ")

prompt = input("Enter a prompt: ")

drafts = session.generate_drafts(prompt)

message_input = inquirer.List('draft', message="Select a draft", choices=drafts)

selected_message = inquirer.prompt([message_input])

session.send_message(selected_message["draft"])