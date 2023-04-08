import requests


def standard_session():
    r = requests.post("http://127.0.0.1:5000/start-session",
                      headers={
                          "Content-Type": "application/json"
                      },
                      json={
                          "uid": "97hjKsoJYZoENG1sZAdu",
                          "duration": 3600,
                          "user_info": {
                              "name": "Daren Palmer",
                              "age": 18,
                              "position": "Student/Developer",
                              "company": "University College London (UCL)",
                              "location": "London, UK",
                              "username": "daren_palmer",
                          },
                          "blacklist": [],
                      })
    print(r.text)


standard_session()
