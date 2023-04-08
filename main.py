import time
from flask import Flask, escape, request
from session import Session

flask_app = Flask(__name__)


def start_session(uid, duration, user_info, blacklist):

    session = Session(uid, duration, user_info, blacklist)

    while session.start_time + int(session.duration) > time.time():
        session.db.collection("users").document(
            session.uid).set({"active": True, }, merge=True)
        for i in session.client.direct_threads(selected_filter="unread"):

            context, last_message = session.filterThreads(i)

            if context is None or last_message is None:
                continue

            # summary = session.getSummary(context)
            summary = context

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
    print(uid, duration, user_info, blacklist)
    if uid is None:
        return "Error: uid is required"
    if duration is None:
        return "Error: duration is required"
    if user_info is None:
        return "Error: user_info is required"

    result = start_session(uid, duration, user_info, blacklist)
    return "Session started"


if __name__ == "__main__":
    flask_app.run(debug=True)
