# Author: Manbir Singh
# Date: June 6, 2022
# Description: This program represents a rest API that deals with boats and loads. This file deals with
# API calls to /boats.

from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import constants
import main

client = datastore.Client()

bp = Blueprint('boats', __name__, url_prefix='/boats')

@bp.route('/decode', methods=['GET'])
def decode_jwt():
    payload = main.verify_jwt(request)
    return payload

@bp.route('', methods=['POST','GET'])
def boats_get_post():
    if request.method == 'POST':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        payload = main.verify_jwt(request)
        readable_payload = decode_jwt()
        owner = readable_payload["sub"]
        content = request.get_json()
        if len(content) != 3:
            return (missing_attribute_error(), 400)
        new_boat = datastore.entity.Entity(key=client.key(constants.boats))
        new_boat.update({"name": content["name"], "type": content["type"],
          "length": content["length"], "loads": [], "owner": owner})
        client.put(new_boat)
        response = new_boat
        response["id"] = new_boat.key.id
        response["self"] = request.base_url + "/" + str(response["id"])
        return (response, 201)
    elif request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        payload = main.verify_jwt(request)
        readable_payload = decode_jwt()
        owner = readable_payload["sub"]
        query = client.query(kind=constants.boats)
        query.add_filter("owner", "=", owner)
        boats_for_owner = (list(query.fetch()))
        total_number = len(boats_for_owner)
        if total_number == 0:
            return ({},200)
        else:
            q_limit = int(request.args.get('limit', '5'))
            q_offset = int(request.args.get('offset', '0'))
            l_iterator = query.fetch(limit=q_limit, offset=q_offset)
            pages = l_iterator.pages
            results = list(next(pages))
            if l_iterator.next_page_token:
                next_offset = q_offset + q_limit
                next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
            else:
                next_url = None
            for e in results:
                e["id"] = e.key.id
                e["self"] = request.base_url + "/" + str(e["id"])
                if e["loads"] != []:
                    for each_load in e["loads"]:
                        each_load["self"] = request.root_url + "/loads/" + str(each_load["id"])
            output = {"boats": results}
            output["total_items"] = total_number
            if next_url:
                output["next"] = next_url
            return json.dumps(output)
    else:
        return (not_supported_route(), 405)

@bp.route('/<id>', methods=['DELETE','GET','PUT','PATCH'])
def boats_get_delete_put_patch(id):
    if request.method == 'DELETE':
        payload = main.verify_jwt(request)
        readable_payload = decode_jwt()
        owner = readable_payload["sub"]
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        if boat is None:
            return (missing_boat_id(), 404)
        elif boat["owner"] != owner:
            return (wrong_owner(), 403)
        if len(boat["loads"]) != 0:
            load_part = boat["loads"]
            for each in load_part:
                load_id = each["id"]
                load_key = client.key(constants.loads, int(load_id))
                load = client.get(key=load_key)
                load.update({"carrier": None})
                client.put(load)
        client.delete(boat_key)
        return ('',204)
    elif request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        payload = main.verify_jwt(request)
        readable_payload = decode_jwt()
        owner = readable_payload["sub"]
        if boat is None:
            return (missing_boat_id(), 404)
        elif boat["owner"] != owner:
            return (wrong_owner_for_get(), 403)
        boat["id"] = boat.key.id
        boat["self"] = request.base_url
        if boat["loads"] != []:
            for each_load in boat["loads"]:
                each_load["self"] = request.root_url + "loads/" + str(each_load["id"])
        return (json.dumps(boat), 200)
    elif request.method == 'PUT':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        content = request.get_json()
        if len(content) < 3:
            return (missing_attribute_error(), 400)
        if len(content) > 3:
            return (too_many_attributes(), 400)
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        payload = main.verify_jwt(request)
        readable_payload = decode_jwt()
        owner = readable_payload["sub"]
        if boat is None:
            return (missing_boat_id(), 404)
        elif boat["owner"] != owner:
            return (wrong_owner_for_relationship(), 403)
        if content["name"] != boat["name"]:
            query = client.query(kind=constants.boats)
            query.add_filter("name", "=", content["name"])
            check_for_existing_name = (list(query.fetch()))
            if len(check_for_existing_name) != 0:
                return (boat_name_already_exists(), 403)
        boat.update({"name": content["name"], "type": content["type"],
                         "length": content["length"]})
        client.put(boat)
        url_of_boat = request.root_url + "/boats/" + str(boat_key.id)
        res = make_response("")
        res.mimetype = 'application/json'
        res.headers.set('Content-Location', url_of_boat)
        res.status_code = 303
        return res
    elif request.method == 'PATCH':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        content = request.get_json()
        if len(content) == 0:
            return (missing_attribute_error(), 400)
        if len(content) > 3:
            return (too_many_attributes(), 400)
        if "name" not in content and "type" not in content and "length" not in content:
            return(missing_attribute_error(), 400)
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        payload = main.verify_jwt(request)
        readable_payload = decode_jwt()
        owner = readable_payload["sub"]
        if boat is None:
            return (missing_boat_id(), 404)
        elif boat["owner"] != owner:
            return (wrong_owner_for_relationship(), 403)
        if "name" in content:
            if content["name"] != boat["name"]:
                query = client.query(kind=constants.boats)
                query.add_filter("name", "=", content["name"])
                check_for_existing_name = (list(query.fetch()))
                if len(check_for_existing_name) != 0:
                    return (boat_name_already_exists(), 403)
            boat.update({"name": content["name"]})
        if "type" in content:
            boat.update({"type": content["type"]})
        if "length" in content:
            boat.update({"length": content["length"]})
        client.put(boat)
        url_of_boat = request.root_url + "/boats/" + str(boat_key.id)
        res = make_response("")
        res.mimetype = 'application/json'
        res.headers.set('Content-Location', url_of_boat)
        res.status_code = 204
        return res
    else:
        return (not_supported_route(), 405)

@bp.route('/<boat_id>/loads/<load_id>', methods=['PUT','DELETE'])
def boats_manage_loads(boat_id, load_id):
    if request.method == 'PUT':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        boat_key = client.key(constants.boats, int(boat_id))
        boat = client.get(key=boat_key)
        load_key = client.key(constants.loads, int(load_id))
        load = client.get(key=load_key)
        if boat is None:
            return (load_or_boat_does_not_exist(), 404)
        if load is None:
            return (load_or_boat_does_not_exist(), 404)
        if load["carrier"] is not None:
            return (existing_boat_error(), 403)
        payload = main.verify_jwt(request)
        readable_payload = decode_jwt()
        owner = readable_payload["sub"]
        if boat["owner"] != owner:
            return (wrong_owner_for_relationship(), 403)
        load.update({"carrier": {"id" : boat.key.id, "name": boat["name"]}})
        client.put(load)
        new_list_of_loads = boat["loads"]
        new_list_of_loads.append({"id": load.key.id})
        boat.update({"loads": new_list_of_loads})
        client.put(boat)
        return ('', 204)
    elif request.method == 'DELETE':
        boat_key = client.key(constants.boats, int(boat_id))
        boat = client.get(key=boat_key)
        load_key = client.key(constants.loads, int(load_id))
        load = client.get(key=load_key)
        if boat is None or load is None:
            return (invalid_load(), 404)
        if load["carrier"] is None:
            return (invalid_load(), 404)
        payload = main.verify_jwt(request)
        readable_payload = decode_jwt()
        owner = readable_payload["sub"]
        if boat["owner"] != owner:
            return (wrong_owner_for_relationship(), 403)
        load.update({"carrier": None})
        client.put(load)
        new_list_of_loads = []
        for item in boat["loads"]:
            if load.key.id != item["id"]:
                new_list_of_loads.append(item)
        boat["loads"] = new_list_of_loads
        client.put(boat)
        return ('', 204)
    else:
        return (not_supported_route(), 405)


def missing_attribute_error():
    error_message_for_missing_attributes = '{"Error" : "The request object is missing at least ' \
                                           'one of the required attributes"}'
    return (json.loads(error_message_for_missing_attributes))

def missing_boat_id():
    error_message_for_missing_id = '{"Error": "No boat with this boat_id exists"}'
    return (json.loads(error_message_for_missing_id))

def load_or_boat_does_not_exist():
    error_message_for_missing_id = '{"Error": "The specified boat and/or load does not exist"}'
    return (json.loads(error_message_for_missing_id))

def existing_boat_error():
    error_message_for_existing_boat = '{"Error": "The load is already loaded on another boat"}'
    return (json.loads(error_message_for_existing_boat))

def invalid_load():
    error_message_for_existing_boat = '{"Error": "No boat with this boat_id is loaded with the load with this load_id"}'
    return (json.loads(error_message_for_existing_boat))

def wrong_owner():
    error_message_for_wrong_owner = '{"Error": "You do not have permission to delete this boat as you are not the' \
                                   ' owner of this boat."}'
    return (json.loads(error_message_for_wrong_owner))

def wrong_owner_for_relationship():
    error_message_for_wrong_owner_for_rel = '{"Error": "You do not have permission to change this boat as you are not the' \
                                   ' owner of this boat."}'
    return (json.loads(error_message_for_wrong_owner_for_rel))

def wrong_owner_for_get():
    error_message_for_wrong_owner_for_get = '{"Error": "You do not have permission to view this boat as you are not the owner' \
                                            ' of this boat."}'
    return (json.loads(error_message_for_wrong_owner_for_get))

def not_supported_route():
    error_message_not_supported_route = '{"Error": "This method is not supported on this URL"}'
    return (json.loads(error_message_not_supported_route))

def json_not_accepted_in_request():
    error_message_json_not_accepted_in_request= '{"Error" : "This MIME type is not supported by this endpoint."}'
    return (json.loads(error_message_json_not_accepted_in_request))

def boat_name_already_exists():
    error_message_boat_name_already_exists= '{"Error" : "A boat with this name already exists. Please use' \
                                            ' another name if possible."}'
    return (json.loads(error_message_boat_name_already_exists))

def too_many_attributes():
    error_message_too_many_attributes = '{"Error" : "The request object has too ' \
                                           'many attributes"}'
    return (json.loads(error_message_too_many_attributes))
