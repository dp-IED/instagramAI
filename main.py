import time
import requests
from flask import escape, request
from session import Session
from celery import Celery


app = Celery('myapp', broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0')


@app.task
def start_session(uid, duration, user_info):
    session = Session(uid, duration, user_info)

    while session.start_time + session.duration > time.time():

        for i in session.client.direct_threads(selected_filter="unread"):
            context, last_message = session.filterThreads(i)
            summary = session.getSummary(context)
            if summary[0] is None:
                print("{} Error: failed to get summary".format(summary[1]))
            elif summary[0] is not None:
                completion = session.getCompletion(summary[0], last_message)
                if completion is None:
                    print("{} Error: failed to get completion".format(
                        completion[1]))
                elif completion[0] is not None:
                    session.send_message(last_message.user_id, completion[0])
                    # add entry to database of messages sent that day
                    session.db.collection("uid").document(session.start_time).set({
                        summary[0]: completion[0],
                    }, merge=True)

    summary = session.end_of_session()
    # save summary to session_ended entry in uid document, triggers event listener on client side
    session.db.collection("uid").document("session_ended").set({
        session.start_time: summary,
    }, merge=True)
    return session


@app.route('/start-session')
def run_my_task():
    uid = request.args.get('uid')
    duration = request.args.get('duration')
    user_info = request.args.get('user_info')
    if uid is None:
        return "Error: uid is required"
    if duration is None:
        return "Error: duration is required"
    if user_info is None:
        return "Error: user_info is required"

    try:
        result = start_session.delay(uid, duration, user_info)
        return "Session started ✅"
    except:
        return "Error: failed to start session"
