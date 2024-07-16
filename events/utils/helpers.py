import re

def emailIsValid(email):
    return len(email) > 6 and re.search("/^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/", email) != []