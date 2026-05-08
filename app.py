from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime

# ================= SAFE AI IMPORT =================
from skin_detect import detect_skin_type
from acne_detect import detect_acne_severity

app = Flask(__name__)
app.secret_key = "super_secret_key"

serializer = URLSafeTimedSerializer(app.secret_key)


# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect("userdb.db")
    conn.row_factory = sqlite3.Row
    return conn


# ================= CREATE USERS TABLE =================
def init_users_db():
    conn = sqlite3.connect("userdb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()

init_users_db()


# ================= CREATE SKIN PATTERN TABLE =================
def init_skin_pattern_db():
    conn = sqlite3.connect("userdb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS skin_pattern (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        date TEXT,
        pimples INTEGER,
        sleep_hours INTEGER,
        water_glasses INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_skin_pattern_db()


# ================= CREATE FEEDBACK TABLE =================
def init_feedback_db():
    conn = sqlite3.connect("userdb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        username TEXT,
        rating TEXT,
        comment TEXT
    )
    """)
    conn.commit()
    conn.close()

init_feedback_db()


# ================= HOME =================
@app.route("/")
def homepage():
    conn = sqlite3.connect("userdb.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            AVG(sleep_hours) AS avg_sleep,
            AVG(water_glasses) AS avg_water,
            AVG(pimples) AS avg_pimples
        FROM skin_pattern
    """)
    data = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) AS total_entries FROM skin_pattern")
    total = cursor.fetchone()
    conn.close()

    avg_sleep = round(data["avg_sleep"], 2) if data["avg_sleep"] else 0
    avg_water = round(data["avg_water"], 2) if data["avg_water"] else 0
    avg_pimples = round(data["avg_pimples"], 2) if data["avg_pimples"] else 0
    total_entries = total["total_entries"] if total["total_entries"] else 0

    return render_template(
        "index.html",
        user=session.get("user"),
        email=session.get("email"),
        avg_sleep=avg_sleep,
        avg_water=avg_water,
        avg_pimples=avg_pimples,
        total_entries=total_entries
    )


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        existing_user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing_user:
            flash("Username or Email already registered. Please use another.")
            conn.close()
            return redirect("/register")

        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password)
        )
        conn.commit()
        conn.close()
        flash("Registration successful. Please log in.")
        return redirect("/login")

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and user["password"] == password:
            session["user"] = user["username"]
            session["email"] = user["email"]
            return redirect("/")
        else:
            flash("Invalid username or password")
            return render_template("login.html")

    return render_template("login.html")


# ================= FORGOT PASSWORD =================
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        username = request.form.get("username").strip()
        if not username:
            flash("Please enter your username")
            return redirect("/reset_password")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if not user:
            flash("Username not found, please check again")
            return redirect("/reset_password")

        new_password = request.form.get("password")
        if new_password:
            conn = get_db()
            conn.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
            conn.commit()
            conn.close()
            flash("Password updated successfully! Please log in.", "success")
            return redirect("/login")

        return render_template("reset_password.html", username=username)

    return render_template("reset_password.html", username=None)


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("userdb.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT username, email FROM users WHERE username = ?", (session["user"],))
    user = cursor.fetchone()
    conn.close()

    return render_template("profile.html", user=user["username"], email=user["email"])


@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user" not in session:
        flash("Login required")
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        new_username = request.form["username"]
        new_email = request.form["email"]
        cursor.execute(
            "UPDATE users SET username = ?, email = ? WHERE username = ?",
            (new_username, new_email, session["user"])
        )
        conn.commit()
        session["user"] = new_username
        flash("Profile updated successfully!", "success")
        return redirect("/edit_profile")

    cursor.execute("SELECT username, email FROM users WHERE username = ?", (session["user"],))
    user = cursor.fetchone()
    conn.close()
    return render_template("edit_profile.html", user=user)


@app.route("/delete_account", methods=["POST"])
def delete_account():
    username = session.get("user")
    if not username:
        flash("Login required")
        return redirect("/login")

    conn = sqlite3.connect("userdb.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM skin_pattern WHERE username = ?", (username,))
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    session.clear()
    flash("Your account has been deleted successfully.")
    return redirect("/")


import random

@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    reply = ""

    if request.method == "POST":
        user_msg = request.form["message"].lower().strip()

        responses = {
            "oily": "Your skin is oily if it looks shiny, has visible pores, and gets greasy by midday. Use oil-free products, a foaming cleanser, niacinamide serum, and a matte sunscreen. Avoid heavy creams.",
            "dry": "Dry skin feels tight, rough, or flaky. Use a gentle cleanser, rich moisturizer (Cetaphil / Nivea / Vaseline), and SPF. At night apply coconut oil or honey mask for deep hydration.",
            "combination": "Combination skin is oily on the T-zone (forehead, nose, chin) and dry on the cheeks. Use a mild cleanser, gel moisturizer, and apply multani mitti only on oily areas.",
            "normal": "Normal skin is well-balanced. Keep it simple: gentle face wash, light moisturizer, and sunscreen daily.",
            "sensitive": "Sensitive skin reacts easily. Use fragrance-free, hypoallergenic products. Avoid harsh scrubs and alcohol-based toners.",
            "skin type": "Not sure about your skin type? Go to the Questionnaire (/questionnaire) and answer a few questions!",
            "acne": "Acne is caused by clogged pores, excess oil, or bacteria. Wash your face twice daily, use niacinamide or salicylic acid, avoid touching your face, and reduce oily/sugary food.",
            "pimple": "For pimples: apply aloe vera gel or rose water on the affected area. Avoid popping them! Track your pimples in the Skin Pattern Tracker (/skin_pattern).",
            "blackhead": "Blackheads are clogged open pores. Use a salicylic acid cleanser, try a multani mitti face pack weekly, and exfoliate gently once a week.",
            "routine": "Morning: Cleanser to Moisturizer to Sunscreen. Night: Cleanser to Serum to Moisturizer. For oily skin use gel products. For dry skin use rich creams.",
            "morning": "Morning routine: Cleanser, Moisturizer, Sunscreen. Always apply sunscreen even on cloudy days!",
            "night": "Night routine: Cleanser, Serum (niacinamide for oily, hyaluronic acid for dry), Moisturizer. Your skin repairs itself at night!",
            "sunscreen": "Sunscreen is the most important skincare step! Use SPF 30 or above every morning.",
            "cleanser": "Use a gentle cleanser twice a day. For oily skin: foaming/gel cleanser. For dry skin: cream or milk cleanser.",
            "moisturizer": "Moisturizer keeps your skin hydrated. Even oily skin needs it! Use gel-based for oily skin and cream-based for dry skin.",
            "natural": "Natural remedies: Oily: Aloe vera, multani mitti, rose water. Dry: Honey mask, coconut oil, milk cream. Combination: Multani mitti on T-zone, aloe vera on dry areas.",
            "remedy": "Natural remedies: Oily: Aloe vera, multani mitti, rose water. Dry: Honey mask, coconut oil, milk cream. Combination: Multani mitti on T-zone, aloe vera on dry areas.",
            "home": "Home remedies: Aloe vera gel soothes and hydrates. Honey is antibacterial great for acne. Multani mitti absorbs excess oil. Coconut oil gives deep moisture for dry skin.",
            "aloe": "Aloe vera is great for all skin types! It soothes irritation, hydrates dry skin, and controls oil. Apply fresh gel at night and wash off in the morning.",
            "honey": "Honey is a natural antibacterial ingredient. Apply raw honey as a face mask for 15 minutes weekly.",
            "turmeric": "Turmeric has anti-inflammatory properties. Mix turmeric with yogurt and apply as a mask occasionally.",
            "product": "Recommended products: Oily: Clean and Clear, Niacinamide Serum, Matte Sunscreen. Dry: Cetaphil, Nivea Cream, Vaseline. Normal: Simple Face Wash, Ponds Moisturizer.",
            "cetaphil": "Cetaphil is ideal for dry and sensitive skin. It is gentle and non-stripping.",
            "niacinamide": "Niacinamide is a powerful ingredient for oily skin. It reduces pores, controls shine, fades dark spots. Use it in your night routine.",
            "yoga": "Yoga recommendations: Oily skin: Kapalbhati, Surya Namaskar. Dry skin: Anulom Vilom, Child Pose. Combination: Twisting Pose, Bridge Pose. Normal: Meditation, Light Yoga.",
            "exercise": "Exercise improves blood circulation, which helps skin glow! Even 20 minutes of walking or yoga daily makes a difference.",
            "sleep": "Sleep is essential for skin repair! Aim for 7-8 hours every night. Poor sleep increases pimples and dullness.",
            "water": "Drink at least 6-8 glasses of water daily. Hydration keeps skin plump and flushes out toxins.",
            "diet": "Your diet directly affects your skin! Reduce oily, sugary, and junk food to control acne. Eat more fruits and vegetables.",
            "stress": "Stress triggers acne and dull skin. Try meditation, deep breathing, or light yoga daily.",
            "questionnaire": "The Questionnaire (/questionnaire) detects your skin type and gives you a personalized routine, products, natural remedies, and yoga tips!",
            "upload": "The Image Upload feature (/upload_skin) uses Machine Learning to detect your skin type from your face photo.",
            "image": "Go to /upload_skin to upload your face photo. The app will detect your skin type using AI.",
            "tracker": "The Skin Pattern Tracker (/skin_pattern) lets you log your daily pimples, sleep hours, water intake, and cycle info.",
            "pattern": "Use the Skin Pattern Tracker (/skin_pattern) to log daily data. Visit View Skin Data (/view_skin_data) to see your progress.",
            "habit": "The Habits Tracker (/habits) scores your daily skincare habits. Score 7+: Excellent, 4-6: Average, Below 4: Poor.",
            "feedback": "You can submit your feedback and product ratings at /feedback.",
            "profile": "You can view and edit your username and email at /profile or /edit_profile.",
            "password": "Forgot your password? Go to /reset_password, enter your username, and set a new password.",
            "login": "To login, go to /login and enter your username and password.",
            "register": "To create an account, go to /register and fill in your username, email, and password.",
            "logout": "To logout, simply go to /logout or click the logout button in the menu.",
            "about": "Skin AI is a smart web app built with Python Flask, SQLite, and Machine Learning.",
            "app": "This app has: Questionnaire, Image Upload, Skin Pattern Tracker, Habits Tracker, Natural Remedies, Yoga tips, and Profile management.",
            "feature": "This app has: Questionnaire, Image Upload, Skin Pattern Tracker, Habits Tracker, Natural Remedies, Yoga tips, and Profile management.",
            "technology": "This app is built using Python Flask, SQLite, Machine Learning (sklearn), OpenCV, and HTML/CSS.",
            "how": "You can detect your skin type in 2 ways: 1) Answer the Questionnaire or 2) Upload a face photo.",
            "hello": "Hello! I am your Skin AI assistant. Ask me anything about skincare, your skin type, routines, or how to use this app!",
            "hi": "Hi there! I am here to help with all your skincare questions. What would you like to know?",
            "hey": "Hey! Ask me about your skin type, daily routine, natural remedies, or any feature of this app!",
            "help": "I can help you with: skin type identification, daily skincare routines, natural home remedies, product recommendations, app features, and yoga and wellness tips.",
            "thank": "You are welcome! Feel free to ask anything else about your skin or this app.",
            "bye": "Goodbye! Remember to follow your skincare routine daily. Take care!",
        }

        reply = ""
        for key, response in responses.items():
            if key in user_msg:
                reply = response
                break

        if not reply:
            reply = "I am not sure about that. You can ask me about skin types, routines, natural remedies, acne, products, yoga, or any feature of this app!"

    return render_template("chatbot.html", reply=reply)


# ================= QUESTIONNAIRE AI =================
@app.route("/questionnaire", methods=["GET", "POST"])
def questionnaire():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        def score(name):
            return int(request.form.get(name, 0))

        oil = (score("oil_after_wash") + score("midday_shine") + score("acne_frequency") + score("pore_visibility"))
        dry = (score("tightness") + score("flakiness") + (2 - score("low_water_intake")) + score("needs_heavy_moisturizer"))
        sensitive = (score("product_reaction") + score("redness") + score("itching"))

        if oil >= 5 and dry <= 2:
            skin_type = "Oily Skin"
        elif dry >= 5 and oil <= 2:
            skin_type = "Dry Skin"
        elif oil >= 4 and dry >= 4:
            skin_type = "Combination Skin"
        elif oil <= 2 and dry <= 2:
            skin_type = "Normal Skin"
        else:
            skin_type = "Balanced Skin"

        if sensitive >= 4:
            skin_type += " (Sensitive)"

        recommendations = {
            "Oily Skin": (
                "Use oil-free cleanser and avoid heavy creams.",
                "Morning: Foaming cleanser to Gel moisturizer to Sunscreen | Night: Cleanser to Niacinamide serum",
                ["Clean & Clear", "Niacinamide Serum", "Matte Sunscreen"],
                ["Apply aloe vera gel at night", "Use multani mitti once a week", "Use rose water as toner", "Use coffee powder scrub to reduce excess oil", "Apply papaya pulp to remove dead skin", "Avoid heavy creams"]
            ),
            "Dry Skin": (
                "Hydrate well and use rich moisturizers.",
                "Morning: Gentle cleanser to Moisturizer to Sunscreen | Night: Cleanser to Heavy cream",
                ["Cetaphil", "Nivea Cream", "Vaseline"],
                ["Apply honey face mask weekly", "Use coconut oil before sleep", "Drink warm water regularly", "Use aloe vera gel for hydration", "Use beetroot paste for natural glow", "Apply milk cream (malai) for moisture", "Avoid harsh soaps"]
            ),
            "Combination Skin": (
                "Balance oil control and hydration.",
                "Morning: Cleanser to Gel moisturizer to Sunscreen | Night: Cleanser to Light cream",
                ["Cetaphil Oily Cleanser", "Aloe Vera Gel"],
                ["Use multani mitti only on oily areas", "Apply aloe vera on dry areas", "Avoid harsh soaps", "Use papaya face pack", "Try coffee scrub on T-zone", "Avoid strong chemical products"]
            ),
            "Normal Skin": (
                "Maintain a consistent routine.",
                "Morning: Cleanser to Moisturizer to Sunscreen | Night: Cleanser to Light moisturizer",
                ["Simple Face Wash", "Pond's Moisturizer"],
                ["Use mild natural cleanser", "Drink enough water daily", "Avoid excessive product use", "Maintain a balanced skincare routine", "Use papaya or fruit-based face packs", "Use beetroot juice for glow", "Stay hydrated"]
            ),
            "Balanced Skin": (
                "Avoid over-treatment and stay hydrated.",
                "Morning: Gentle cleanser to Moisturizer to Sunscreen | Night: Cleanser to Light cream",
                ["Simple Cleanser", "Light Moisturizer"],
                ["Use turmeric + yogurt mask occasionally", "Maintain healthy diet", "Keep skincare simple"]
            )
        }

        care_kits = {
            "Oily Skin": "Oil Control Kit: Cleanser + Niacinamide + Sunscreen",
            "Dry Skin": "Deep Hydration Kit: Gentle Cleanser + Rich Cream + SPF",
            "Combination Skin": "Balance Care Kit: Mild Cleanser + Gel Moisturizer + SPF",
            "Normal Skin": "Daily Glow Kit: Cleanser + Moisturizer + SPF",
            "Balanced Skin": "Maintenance Kit: Gentle Cleanser + Light Cream + SPF"
        }

        base_type = skin_type.replace(" (Sensitive)", "")
        kit_name = care_kits.get(base_type, "Basic Skincare Kit")
        recommendation, routine, products, natural_remedies = recommendations.get(base_type)

        yoga_recommendations = {
            "Dry Skin": ["Anulom Vilom", "Child Pose"],
            "Oily Skin": ["Kapalbhati", "Surya Namaskar"],
            "Combination Skin": ["Twisting Pose", "Bridge Pose"],
            "Normal Skin": ["Meditation", "Stretching"],
            "Balanced Skin": ["Meditation", "Light Yoga"]
        }

        yoga = yoga_recommendations.get(base_type, [])

        return render_template(
            "result.html",
            skin_type=skin_type,
            recommendation=recommendation,
            routine=routine,
            yoga=yoga,
            products=products,
            natural_remedies=natural_remedies,
            kit_name=kit_name,
            oil_score=oil,
            dry_score=dry,
            sensitive_score=sensitive
        )

    return render_template("questionnaire.html")


# ================= HABITS =================
@app.route("/habits")
def habits():
    if "user" not in session:
        return redirect("/login")
    return render_template("habits.html")


# ================= HABIT RESULT =================
@app.route("/habit_result", methods=["POST"])
def habit_result():
    if "user" not in session:
        return redirect("/login")

    water = int(request.form.get("water"))
    sunscreen = int(request.form.get("sunscreen"))
    cleanser = int(request.form.get("cleanser"))
    sleep = int(request.form.get("sleep"))

    score = 0
    if water >= 6: score += 2
    if sunscreen == 1: score += 2
    if cleanser == 1: score += 2
    if sleep == 1: score += 2

    if score >= 7:
        status = "Excellent Skin Habits"
    elif score >= 4:
        status = "Average Skin Habits"
    else:
        status = "Poor Skin Habits - Improve Routine"

    return render_template("habit_result.html", score=score, status=status)


# ================= IMAGE AI SKIN DETECTION =================
@app.route("/upload_skin", methods=["GET", "POST"])
def upload_skin():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        if 'skin_image' not in request.files:
            return "No file part!", 400

        image = request.files['skin_image']
        if image.filename == "":
            return "No file selected!", 400

        filename = secure_filename(image.filename)
        os.makedirs("static/uploads", exist_ok=True)
        image_path = os.path.join("static/uploads", filename)
        image.save(image_path)

        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return render_template("upload_skin.html", error="Invalid image!")

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 40, 60], dtype=np.uint8)
        upper = np.array([20, 150, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        skin_ratio = np.sum(mask > 0) / (img.shape[0] * img.shape[1])

        if skin_ratio < 0.25:
            return render_template("upload_skin.html", error="This image does not appear to be skin!")

        skin_type = detect_skin_type(image_path)
        recommended_products = ["Face Wash", "Moisturizer", "Sunscreen"]

        if skin_type == "Dry Skin":
            natural = ["Use aloe vera gel for hydration", "Apply honey face mask weekly", "Avoid harsh soaps"]
            kit = "Hydration Care Kit: Face Wash + Moisturizer + Sunscreen"
        elif skin_type == "Combination Skin":
            natural = ["Use multani mitti only on oily areas", "Apply aloe vera on dry areas", "Avoid harsh soaps"]
            kit = "Balance Care Kit: Mild Cleanser + Gel Moisturizer + SPF"
        elif skin_type == "Oily Skin":
            natural = ["Use multani mitti face pack twice a week", "Apply rose water as toner", "Avoid heavy creams"]
            kit = "Oil Control Kit: Foaming Cleanser + Toner + Light Gel Moisturizer"
        else:
            natural = ["Maintain a balanced skincare routine", "Stay hydrated", "Avoid experimenting with harsh products"]
            kit = "Basic Care Kit: Cleanser + Moisturizer + Sunscreen"

        natural_remedies = natural
        kit_name = kit

        return render_template("result.html",
                               skin_type=skin_type,
                               recommendation="AI detected skin type using Machine Learning model.",
                               routine="Follow dermatologist recommended routine.",
                               yoga=["Surya Namaskar", "Meditation"],
                               products=recommended_products,
                               natural=natural,
                               kit=kit,
                               natural_remedies=natural_remedies,
                               kit_name=kit_name)

    return render_template("upload_skin.html")


# ================= AI PREDICTION FUNCTION =================
def predict_high_risk_days():
    conn = get_db()
    data = conn.execute("SELECT pimples FROM skin_pattern").fetchall()
    conn.close()
    risky_days = []
    for row in data:
        if row["pimples"] >= 3:
            risky_days.append(row["cycle_day"])
    return list(set(risky_days))


# ===================== SKIN PATTERN ROUTES =====================
@app.route('/skin_pattern')
def skin_pattern():
    return render_template("skin_pattern.html")


@app.route('/save_skin_pattern', methods=['POST'])
def save_skin_pattern():
    username = session.get("user")
    if not username:
        flash("You must be logged in to save data.")
        return redirect("/login")

    date = request.form.get("date")
    cycle_start = request.form.get("cycle_start_date")
    cycle_end = request.form.get("cycle_end_date")
    pimples = request.form.get("pimples")
    pimple_occurrence = request.form.get("pimple_occurrence")
    sleep_hours = request.form.get("sleep_hours")
    water_glasses = request.form.get("water_glasses")

    if not all([date, cycle_start, pimples, pimple_occurrence, sleep_hours, water_glasses]):
        flash("All fields except cycle_end are required!")
        return redirect("/skin_pattern")

    cycle_day = (datetime.strptime(date, "%Y-%m-%d") - datetime.strptime(cycle_start, "%Y-%m-%d")).days + 1
    if cycle_day < 1:
        cycle_day = 1

    conn = get_db()
    conn.execute("""
        INSERT INTO skin_pattern
        (username, date, cycle_start_date, cycle_end_date, cycle_day, pimples, pimple_occurrence, sleep_hours, water_glasses)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (username, date, cycle_start, cycle_end, cycle_day, pimples, pimple_occurrence, sleep_hours, water_glasses))
    conn.commit()
    conn.close()
    flash("Skin pattern data saved successfully! Go to 'View Skin Data' to see your updated records.")
    return redirect("/skin_pattern")


# ================= VIEW SAVED DATA =================
@app.route("/view_skin_data")
def view_skin_data():
    username = session.get("user")
    if not username:
        flash("Login required")
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, date, cycle_day, pimples, sleep_hours, water_glasses
        FROM skin_pattern WHERE username = ? ORDER BY date DESC
    """, (username,))
    rows = cursor.fetchall()

    data = []
    for r in rows:
        data.append({
            "id": r[0], "date": r[1], "cycle_day": r[2],
            "pimples": int(r[3]), "sleep_hours": int(r[4]), "water_glasses": int(r[5])
        })

    from collections import defaultdict
    from datetime import datetime as dt

    monthly_data = defaultdict(lambda: {"pimples": [], "sleep": [], "water": []})
    for r in rows:
        date_obj = dt.strptime(r[1], "%Y-%m-%d")
        month_key = date_obj.strftime("%Y-%m")
        monthly_data[month_key]["pimples"].append(int(r[3]))
        monthly_data[month_key]["sleep"].append(int(r[4]))
        monthly_data[month_key]["water"].append(int(r[5]))

    sorted_months = sorted(monthly_data.keys(), reverse=True)
    improvement_message = ""

    if len(sorted_months) >= 2:
        current_month = sorted_months[0]
        previous_month = sorted_months[1]

        def avg(lst):
            return sum(lst) / len(lst) if lst else 0

        messages = []
        if avg(monthly_data[current_month]["water"]) > avg(monthly_data[previous_month]["water"]):
            messages.append("Water intake improved compared to last month")
        elif avg(monthly_data[current_month]["water"]) < avg(monthly_data[previous_month]["water"]):
            messages.append("Water intake reduced compared to last month")
        if avg(monthly_data[current_month]["sleep"]) > avg(monthly_data[previous_month]["sleep"]):
            messages.append("Sleep improved compared to last month")
        elif avg(monthly_data[current_month]["sleep"]) < avg(monthly_data[previous_month]["sleep"]):
            messages.append("Sleep reduced compared to last month")
        if avg(monthly_data[current_month]["pimples"]) < avg(monthly_data[previous_month]["pimples"]):
            messages.append("Pimples reduced compared to last month")
        elif avg(monthly_data[current_month]["pimples"]) > avg(monthly_data[previous_month]["pimples"]):
            messages.append("Pimples increased compared to last month")
        if not messages:
            messages.append("No major changes compared to last month.")
        improvement_message = " | ".join(messages)
    elif len(sorted_months) == 1:
        improvement_message = "Add more monthly data to see progress comparison."

    personalized_tips = []
    if len(rows) >= 1:
        latest = rows[0]
        if int(latest[5]) < 5: personalized_tips.append("Increase water intake to at least 6-8 glasses daily.")
        if int(latest[4]) < 7: personalized_tips.append("Try to sleep at least 7-8 hours for better skin recovery.")
        if int(latest[3]) >= 3: personalized_tips.append("Consider reducing oily or sugary food intake.")
    if not personalized_tips:
        personalized_tips.append("Great job! Your latest entry looks good. Keep it up!")

    cursor.execute("""
        SELECT date, sleep_hours, water_glasses, pimples 
        FROM skin_pattern WHERE username = ? ORDER BY date ASC
    """, (username,))
    graph_rows = cursor.fetchall()
    graph_data = {
        "dates": [r[0] for r in graph_rows],
        "sleep": [r[1] for r in graph_rows],
        "water": [r[2] for r in graph_rows],
        "pimples": [r[3] for r in graph_rows]
    }

    conn.close()
    return render_template(
        "view_skin_data.html",
        records=data,
        improvement=improvement_message,
        tips=personalized_tips,
        graph_data=graph_data
    )


@app.route('/edit/<int:record_id>', methods=['GET', 'POST'])
def edit(record_id):
    username = session.get("user")
    if not username:
        flash("Login required")
        return redirect("/login")

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM skin_pattern WHERE id = ? AND username = ?", (record_id, username))
    record = cursor.fetchone()

    if not record:
        conn.close()
        return "Record not found"

    if request.method == 'POST':
        cursor.execute("""
            UPDATE skin_pattern
            SET date=?, pimples=?, cycle_day=?, sleep_hours=?, water_glasses=?
            WHERE id=? AND username=?
        """, (request.form['date'], request.form['pimples'], request.form['cycle_day'],
              request.form['sleep'], request.form['water'], record_id, username))
        conn.commit()
        conn.close()
        return redirect('/view_skin_data')

    conn.close()
    return render_template('edit.html', record=record)


@app.route('/delete/<int:record_id>')
def delete(record_id):
    username = session.get("user")
    if not username:
        flash("Login required")
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM skin_pattern WHERE id = ? AND username = ?", (record_id, username))
    conn.commit()
    conn.close()
    return redirect('/view_skin_data')


@app.route("/privacy_policy")
def privacy_policy():
    return render_template("privacy_policy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


# ================= ACNE SEVERITY DETECTOR =================
@app.route("/acne_detect", methods=["GET", "POST"])
def acne_detect():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        if 'acne_image' not in request.files:
            return render_template("upload_acne.html", error="No file uploaded!")

        image = request.files['acne_image']
        if image.filename == "":
            return render_template("upload_acne.html", error="No file selected!")

        filename = secure_filename(image.filename)
        os.makedirs("static/uploads", exist_ok=True)
        image_path = os.path.join("static/uploads", filename)
        image.save(image_path)

        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return render_template("upload_acne.html", error="Invalid image file!")

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 40, 60], dtype=np.uint8)
        upper = np.array([20, 150, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        skin_ratio = np.sum(mask > 0) / (img.shape[0] * img.shape[1])

        if skin_ratio < 0.05:
            return render_template("upload_acne.html", error="Please upload a clear face photo!")

        result = detect_acne_severity(image_path)

        if "error" in result:
            return render_template("upload_acne.html", error="Detection failed: " + result["error"])

        return render_template("acne_result.html", result=result)

    return render_template("upload_acne.html")


# ================= FEEDBACK =================
@app.route("/feedback")
def feedback():
    if "user" not in session:
        return redirect("/login")
    return render_template("feedback.html")


# ================= SAVE FEEDBACK =================
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    product = request.form["product"]
    rating = request.form["rating"]
    comment = request.form["comment"]
    return render_template("feedback.html", success=True)


# ================= GROQ CHATBOT API =================
@app.route("/groq_chat", methods=["POST"])
def groq_chat():
    import urllib.request
    import json

    user_msg = request.get_json().get("message", "").strip()
    if not user_msg:
        return {"reply": "Please type a question!"}

    system_prompt = """You are a helpful skincare assistant for the Skin AI web application. Answer only about skincare, skin types, routines, natural remedies, products, yoga for skin, and this app features. Keep answers short and friendly.

App features: Questionnaire (/questionnaire), Image Upload (/upload_skin), Skin Pattern Tracker (/skin_pattern), Habits Tracker (/habits), View Skin Data (/view_skin_data), Feedback (/feedback), Profile (/profile).
Tech stack: Python Flask, SQLite, sklearn ML model, OpenCV, HTML/CSS."""

    payload = json.dumps({
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "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"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            reply = result["choices"][0]["message"]["content"]
            return {"reply": reply}
    except Exception as e:
        return {"reply": "I'm having trouble connecting. Please try again!"}


# ================= HOME LINKS API =================
@app.route("/home_links")
def home_links():
    if "user" not in session:
        return redirect("/login")
    return {
        "Skin Pattern Tracker": "/skin_pattern",
        "Upload Skin Image": "/upload_skin",
        "Questionnaire AI": "/questionnaire",
        "Daily Habits Tracker": "/habits",
        "View Skin Data": "/view_skin_data",
        "Feedback": "/feedback",
        "Logout": "/logout"
    }


# ================= 404 ERROR PAGE =================
@app.errorhandler(404)
def page_not_found(e):
    return "<h2>404 - Page Not Found</h2><p>The page you requested does not exist.</p>", 404


# ================= RUN APP =================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")