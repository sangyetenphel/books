from flask import redirect, session
from functools import wraps

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    # Copy the original function’s information to the new function
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function