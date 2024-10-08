import time
from flask import Flask, escape, request
from session import InstagramSession

flask_app = Flask(__name__)


def start_session(uid, duration, user_info, blacklist, auto=False):

    def answer_message(session, i):
        if summary is None:
            print("{} Error: failed to get summary".format(summary))

        print("Getting completion...")
        print("Last message: ", last_message.text)
        completion = session.getCompletion(
            summary, last_message.text, i.thread_title)

        if completion is None:
            print("{} Error: failed to get completion".format(
                completion))

        print(
            f"Do you want to send: {completion} to {i.thread_title} ? The last message was: {last_message.text}\n\n[1] Yes\n[2] No\n[3] Exit\n")
        choice = int(input())
        if choice == 1:
            session.send_message(
                i, completion)
            print("Message sent")
        elif choice == 2:
            print("Message not sent")
            pass
        elif choice == 3:
            print("Exiting...")
            exit()
        else:
            print("Invalid choice")
            pass
        # add entry to database of messages sent that day
        session.db.collection("users").document(session.uid).collection("messages").document().set({
            "message": completion,
            "thread": i.thread_title,
            "time": time.time(),
        }, merge=True)

    session = InstagramSession(uid, duration, user_info, blacklist)

    if session.client is not None:
        print("Session started")

    while session.start_time + int(session.duration) > time.time():
        session.db.collection("users").document(
            session.uid).set({"active": True, }, merge=True)

        if session.auto:
            try:

                for i in session.client.direct_threads(selected_filter="unread"):
                    context, last_message = session.filterThreads(i)
                    if context is None or last_message is None:
                        continue

                    # summary = session.getSummary(context)
                    summary = context
                    answer_message(session, i)

            except session.exceptions["loginRequired"]:
                session.client = session.login(refresh=True)

        elif not session.auto:
            try:

                conversations = session.client.direct_threads(
                    selected_filter="unread")
                for i in conversations:
                    print(
                        f"[{conversations.index(i)+1}]{i.thread_title}: {i.messages[0].text}")
                print("Select conversation to reply to:")
                choice = int(input())-1
                context, last_message = session.filterThreads(
                    conversations[choice])
                if context is None:
                    print("Error: failed to get context")
                    pass
                if last_message is None:
                    print("Error: failed to get last message")
                summary = context
                answer_message(session, conversations[choice])

            except session.exceptions["loginRequired"]:
                session.client = session.login(refresh=True)

    summary = session.end_of_session()
    if summary is None:
        return "Error: failed to get summary: check if username has been set in db"
    # save summary to session_ended entry in uid document, triggers event listener on client side
    session.db.collection("uid").document("session_ended").set({
        session.start_time: summary,
    }, merge=True)


@ flask_app.route('/start-session', methods=['POST'])
def run_my_task():
    uid = request.json['uid']
    duration = request.json['duration']
    user_info = request.json['user_info']
    blacklist = request.json['blacklist']
    mode = request.json['auto']
    print(uid, duration, user_info, blacklist, mode)
    if uid is None:
        return "Error: uid is required"
    if duration is None:
        return "Error: duration is required"
    if user_info is None:
        return "Error: user_info is required"
    if blacklist is None:
        return "Error: blacklist is required"
    if mode is None:
        return "Error: mode is required"

    print("Starting session...")
    result = start_session(uid, duration, user_info, blacklist, mode)
    return "Session started"


if __name__ == "__main__":
    flask_app.run(host="127.0.0.1", port=8080, debug=True)
