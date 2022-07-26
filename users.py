# Author: Manbir Singh
# Description: This program represents a rest API that deals with boats and loads. This file deals with
# API calls to /users.

from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
from json2html import *
import constants

client = datastore.Client()

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('', methods=['GET'])
def users_get():
    if request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        query = client.query(kind=constants.users)
        list_of_users = (list(query.fetch()))
        total_number = len(list_of_users)
        if total_number == 0:
            return ({},200)
        else:
            for user in list_of_users:
                user["id"] = user.key.id
                user["self"] = request.base_url + "/" + str(user["id"])
            res = make_response(json.dumps(list_of_users))
            res.status_code = 200
            return res
    else:
        return (not_supported_route(), 405)

@bp.route('/<id>', methods=['GET'])
def users_get_one(id):
    if request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        user_key = client.key(constants.users, int(id))
        user = client.get(key=user_key)
        if user is None:
            return (missing_user_id(), 404)
        user["id"] = user.key.id
        user["self"] = request.base_url
        return (json.dumps(user), 200)
    else:
        return (not_supported_route(), 405)

def missing_attribute_error():
    error_message_for_missing_attributes = '{"Error" : "The request object is missing at ' \
                                           'least one of the required attributes"}'
    return (json.loads(error_message_for_missing_attributes))

def missing_user_id():
    error_message_for_missing_id = '{"Error": "No user with this user_id exists"}'
    return (json.loads(error_message_for_missing_id))

def not_supported_route():
    error_message_not_supported_route = '{"Error": "This method is not supported on this URL"}'
    return (json.loads(error_message_not_supported_route))

def json_not_accepted_in_request():
    error_message_json_not_accepted_in_request= '{"Error" : "This MIME type is not supported by this endpoint."}'
    return (json.loads(error_message_json_not_accepted_in_request))
