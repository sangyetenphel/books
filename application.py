import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash,check_password_hash
from helpers import login_required

app = Flask(__name__)

# Prevent sorting the json objects returned via our API
app.config['JSON_SORT_KEYS'] = False

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
def index():
    """Log user in."""

    if request.method == "POST":

        #Forget any user_id
        session.clear()

        username = request.form.get('username').title()
        password = request.form.get('password')

        # Query db to check if username and passsword is correct
        user_row = db.execute('SELECT * FROM users WHERE username = :username', {'username': username}).fetchone()
        if user_row == None or not check_password_hash(user_row.password, password):
            flash("Invalid username and/or password!", 'danger')
            return redirect('/')
        else:
            # store the user_id in a session
            session['user_id'] = user_row[0]
            return render_template('search.html')
    else:
        return render_template('index.html')


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    """Register a user."""

    # User reached route via POST (as by submiting a form via POST)
    if request.method == "POST":

        # Get user info
        username = request.form.get('username').title()
        password = request.form.get('password')
        re_password = request.form.get('re-password')

        # Check if passwords match
        if password != re_password:
            flash("Passwords don't match!")
            return redirect('/signup')

        # Check if username is available
        if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount == 0:
            db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": username, "password": generate_password_hash(password)})
            db.commit()

            # Store the user_id in session
            # user = db.execute('SELECT id from users WHERE username = :username', {'username': username}).fetchone()
            # user_id = user.id
            # session['user_id'] = user_id

            flash("Registered!", 'success')
            return redirect(url_for('index'))
        else:
            return render_template('error.html', msg="Username already taken.")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template('signup.html')


@app.route('/search', methods=["GET", "POST"])
@login_required
def search():
    """Search for books."""

    if request.method == "POST":
        # Get what the user searched for
        keyword = request.form.get('keyword')

        # Use postgresql lower() to make "case-insensitive" query
        books = db.execute("SELECT * FROM books WHERE isbn like :keyword or LOWER(title) like LOWER(:keyword) or LOWER(author) like LOWER(:keyword)", {"keyword": '%'+keyword+'%'}).fetchall()

        return render_template("result.html", books=books)
    else:
        return render_template('search.html')


@app.route('/book/<isbn>')
def book(isbn):
    """Display a book's information."""

    # Fetch data from books table
    book = db.execute('SELECT * FROM books WHERE isbn = :isbn', {'isbn': isbn}).fetchone()

    # Fetch review from reviews table
    # reviews = db.execute('SELECT * FROM reviews WHERE isbn = :isbn', {'isbn': isbn}).fetchall()
    reviews = db.execute('SELECT * FROM users JOIN reviews ON reviews.user_id = users.id WHERE isbn = :isbn', {'isbn': isbn}).fetchall()

    # Fetch data from goodreads API
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "44pj9meLB351CJgAy0SA8w", "isbns": isbn})
    goodreads = res.json()

    return render_template("book.html", book=book, reviews = reviews, goodreads=goodreads)


@app.route('/review/<isbn>', methods=['POST'])
def review(isbn):
    """Insert user review into database."""

    # Check if a review for the book doesn't alredy exist
    if db.execute('SELECT * FROM reviews WHERE isbn = :isbn AND user_id = :user_id', {'isbn': isbn, 'user_id': session.get('user_id')}).rowcount == 0:

        # Get user reviews
        rating = request.form.get('rating')
        review = request.form.get('review')

        db.execute('INSERT INTO reviews (rating, review, isbn, user_id) VALUES (:rating, :review, :isbn, :user_id)', {'rating': rating, 'review': review, 'isbn': isbn, 'user_id': session.get('user_id')})

        # So that changes to the database takes place
        db.commit()

        return redirect(url_for('book', isbn=isbn))

    # if user already gave a review for the book
    else:
        flash("You already reviewed this book!", 'danger')
        return redirect(url_for('book', isbn=isbn))

@app.route('/api/<isbn>')
def book_api(isbn):
    """Return details about a book."""

    # Make sure the api exists
    book = db.execute('SELECT * FROM books WHERE isbn = :isbn', {'isbn': isbn}).fetchone()
    if book is None:
        return jsonify({"error": "ISBN not found"}), 404

    # Get the reviews count of the isbn
    review_count = db.execute('SELECT COUNT(*) FROM reviews WHERE isbn = :isbn', {'isbn': isbn}).fetchone()[0]

    # Get the average rating of the isbn
    row = db.execute('SELECT AVG(rating) FROM reviews WHERE isbn = :isbn', {'isbn': isbn}).fetchone()[0]
    average_score = str(round(row, 2))

    # Get book information
    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
        "review_count": review_count,
        "average_score": average_score
    })

@app.route('/logout')
def logout():
    """ Logout user out """

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
