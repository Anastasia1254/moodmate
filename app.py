import os
from flask import Flask, render_template, request, redirect, session, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)


db = client.moodmate_user

users_collection = db.users
moods_collection = db.moods
mood_types_collection = db.mood_types
tips_collection = db.tips

mood_types = [
    {"name": "happy", "emoji": "😊"},
    {"name": "sad", "emoji": "😔"},
    {"name": "stressed", "emoji": "😣"},
    {"name": "exhausted", "emoji": "😩"},
    {"name": "neutral", "emoji": "😐"}
]

for mood in mood_types:
    if not mood_types_collection.find_one({"name": mood["name"]}):
        mood_types_collection.insert_one(mood)

tips = [
    {"mood_name": "happy", "tip_text": "Поділися гарним настроєм із кимось 💛"},
    {"mood_name": "sad", "tip_text": "Спробуй прогулятися і подихати свіжим повітрям 🌿"},
    {"mood_name": "stressed", "tip_text": "Зроби коротку дихальну вправу 🧘‍♀️"},
    {"mood_name": "exhausted", "tip_text": "Ляж спати і добре відпочинь 😴"},
    {"mood_name": "neutral", "tip_text": "Спробуй зробити щось приємне для себе ✨"}
]

for tip in tips:
    mood = mood_types_collection.find_one({"name": tip["mood_name"]})
    if mood and not tips_collection.find_one({"tip_text": tip["tip_text"]}):
        tips_collection.insert_one({"mood_type_id": mood["_id"], "tip_text": tip["tip_text"]})

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("mood"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        if users_collection.find_one({"email": email}):
            return "Користувач з таким email вже існує"
        user_id = users_collection.insert_one({
            "name": name,
            "email": email,
            "password": password,
            "created_at": datetime.utcnow()
        }).inserted_id
        session["user_id"] = str(user_id)
        return redirect(url_for("mood"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = users_collection.find_one({"email": email, "password": password})
        if user:
            session["user_id"] = str(user["_id"])
            return redirect(url_for("mood"))
        return "Неправильний email або пароль"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))

@app.route("/mood", methods=["GET", "POST"])
def mood():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    mood_types_list = list(mood_types_collection.find())
    
    if request.method == "POST":
        mood_id = request.form["mood_id"]
        note = request.form.get("note", "")
        moods_collection.insert_one({
            "user_id": ObjectId(session["user_id"]),
            "mood_type_id": ObjectId(mood_id),
            "note": note,
            "created_at": datetime.utcnow()
        })
        tip = tips_collection.find_one({"mood_type_id": ObjectId(mood_id)})
        tip_text = tip["tip_text"] if tip else ""
        return render_template("tip.html", tip=tip_text)
    
    return render_template("mood.html", mood_types=mood_types_list)

@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_moods = list(moods_collection.find({"user_id": ObjectId(session["user_id"])}))
    for m in user_moods:
        mood_type = mood_types_collection.find_one({"_id": m["mood_type_id"]})
        m["mood_name"] = mood_type["name"]
        m["emoji"] = mood_type["emoji"]
        tip = tips_collection.find_one({"mood_type_id": m["mood_type_id"]})
        m["tip_text"] = tip["tip_text"] if tip else ""
    return render_template("history.html", moods=user_moods)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
