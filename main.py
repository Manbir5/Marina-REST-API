# Author: Manbir Singh
# Date: June 6, 2022
# Class: CS493
# Description: This program represents a complete rest API that deals with users, boats and loads.
# This file imports the other two components and sets the route for the root url.

from google.cloud import datastore
from flask import Flask, request, jsonify, _request_ctx_stack, make_response
import json
import constants
import boats
import loads
import users

import requests
from os import environ as env

from functools import wraps

from six.moves.urllib.request import urlopen
from flask_cors import cross_origin
from jose import jwt
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth

from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.register_blueprint(loads.bp)
app.register_blueprint(boats.bp)
app.register_blueprint(users.bp)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)

client = datastore.Client()
BOATS = "boats"
USERS = "users"

# Update the values of the following 3 variables
CLIENT_ID = '0UqR7wkDo4ZJpEnvPZFZUyR6ubrplQcG'
CLIENT_SECRET = 'wwTvRRm_n-S1NkT-eO68RlwtJ40QWysoYUdF1mO-MCtFWYR-LFzmLNyYaNvOrGgZ'
DOMAIN = 'cs493-singmanb-wk7.us.auth0.com'
# For example
# DOMAIN = 'fall21.us.auth0.com'

ALGORITHMS = ["RS256"]

# This code is adapted from https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga=2.46956069.349333901.1589042886-466012638.1589042885#create-the-jwt-validation-decorator

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


# Verify the JWT in the request's Authorization header
def verify_jwt(request):
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization'].split()
        token = auth_header[1]
    else:
        raise AuthError({"code": "no auth header",
                         "description":
                             "Authorization header is missing"}, 401)

    jsonurl = urlopen("https://" + DOMAIN + "/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.JWTError:
        raise AuthError({"code": "invalid_header",
                         "description":
                             "Invalid header. "
                             "Use an RS256 signed JWT Access Token"}, 401)
    if unverified_header["alg"] == "HS256":
        raise AuthError({"code": "invalid_header",
                         "description":
                             "Invalid header. "
                             "Use an RS256 signed JWT Access Token"}, 401)
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer="https://" + DOMAIN + "/"
            )
        except jwt.ExpiredSignatureError:
            raise AuthError({"code": "token_expired",
                             "description": "token is expired"}, 401)
        except jwt.JWTClaimsError:
            raise AuthError({"code": "invalid_claims",
                             "description":
                                 "incorrect claims,"
                                 " please check the audience and issuer"}, 401)
        except Exception:
            raise AuthError({"code": "invalid_header",
                             "description":
                                 "Unable to parse authentication"
                                 " token."}, 401)

        return payload
    else:
        raise AuthError({"code": "no_rsa_key",
                         "description":
                             "No RSA key in JWKS"}, 401)


@app.route('/decode', methods=['GET'])
def decode_jwt():
    payload = verify_jwt(request)
    return payload

@app.route('/')
def index():
    return render_template(
        "home.html",
        session=session.get("user"),
        pretty=json.dumps(session.get("user"), indent=4),
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    query = client.query(kind=USERS)
    query.add_filter("unique_id", "=", token["userinfo"]["sub"])
    check_for_existing_user = (list(query.fetch()))
    if len(check_for_existing_user) == 0:
        new_user = datastore.entity.Entity(key=client.key(USERS))
        new_user.update({"first_name": token["userinfo"]["given_name"], "last_name": token["userinfo"]["family_name"],
                         "email": token["userinfo"]["email"], "unique_id": token["userinfo"]["sub"]})
        client.put(new_user)
    return redirect("/")

@app.route('/login', methods=['POST', 'GET'])
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": "https://singmanb-hw2.uk.r.appspot.com/",
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
