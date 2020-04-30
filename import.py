import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# manage connections to the database
engine = create_engine(os.getenv("DATABASE_URL")) # DATABASE_URL is an environment variable that indicates where the database lives

db = scoped_session(sessionmaker(bind=engine)) # create a 'scoped session' that ensures different users' interactions with the database are kept separate

f = open('books.csv')
reader = csv.reader(f)

# skip the first row of csv as its header column
next(reader, None)

# loop gives each column a name
for isbn, title, author, year in reader:
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)", {"isbn": isbn, "title": title, "author": author, "year": year})
db.commit()
