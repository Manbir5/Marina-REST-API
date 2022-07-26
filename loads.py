# Author: Manbir Singh
# Date: June 6, 2022
# Class: CS493
# Description: This program represents a rest API that deals with boats and loads. This file deals with
# API calls to /loads.

from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
from json2html import *
import constants

client = datastore.Client()

bp = Blueprint('loads', __name__, url_prefix='/loads')

@bp.route('', methods=['POST','GET'])
def loads_get_post():
    if request.method == 'POST':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        content = request.get_json()
        if len(content) < 3:
            return (missing_attribute_error(), 400)
        new_load = datastore.entity.Entity(key=client.key(constants.loads))
        new_load.update({"volume": content["volume"], "item": content["item"], "creation_date": content["creation_date"],
                         "carrier": None})
        client.put(new_load)
        response = new_load
        response["id"] = new_load.key.id
        response["self"] = request.base_url + "/" + str(response["id"])
        return (response, 201)
    elif request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        query = client.query(kind=constants.loads)
        loads_for_owner = (list(query.fetch()))
        total_number = len(loads_for_owner)
        if total_number == 0:
            return ({},200)
        else:
            q_limit = int(request.args.get('limit', '5'))
            q_offset = int(request.args.get('offset', '0'))
            g_iterator = query.fetch(limit=q_limit, offset=q_offset)
            pages = g_iterator.pages
            results = list(next(pages))
            if g_iterator.next_page_token:
                next_offset = q_offset + q_limit
                next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
            else:
                next_url = None
            for e in results:
                e["id"] = e.key.id
                e["self"] = request.base_url + "/" + str(e["id"])
                check_for_carrier = e["carrier"]
                if check_for_carrier is not None:
                    check_for_carrier["self"] = request.base_url[0:-5] + str(check_for_carrier["id"])
            output = {"loads": results}
            output["total_items"] = total_number
            if next_url:
                output["next"] = next_url
            return json.dumps(output)
    else:
        return (not_supported_route(), 405)

@bp.route('/<id>', methods=['DELETE','GET','PUT','PATCH'])
def loads_get_delete_put_patch(id):
    if request.method == 'DELETE':
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if load is None:
            return (missing_load_id(), 404)
        if load["carrier"] is not None:
            boat_part = load["carrier"]
            boat_id = boat_part["id"]
            boat_key = client.key(constants.boats, int(boat_id))
            boat = client.get(key=boat_key)
            new_list_of_loads = []
            for item in boat["loads"]:
                if load.key.id != item["id"]:
                    new_list_of_loads.append(item)
            boat.update({"loads": new_list_of_loads})
            client.put(boat)
        client.delete(load_key)
        return ('',204)
    elif request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if load is None:
            return (missing_load_id(), 404)
        load["id"] = load.key.id
        load["self"] = request.base_url
        length_of_load_id = len(id)
        check_for_carrier = load["carrier"]
        if check_for_carrier is not None:
            check_for_carrier["self"] = request.base_url[0:-(length_of_load_id + 6)] + "boats/" +  str(check_for_carrier["id"])
        return (json.dumps(load), 200)
    elif request.method == 'PUT':
        if 'application/json' not in request.accept_mimetypes:
            return (json_not_accepted_in_request(), 406)
        content = request.get_json()
        if len(content) < 3:
            return (missing_attribute_error(), 400)
        if len(content) > 3:
            return (too_many_attributes(), 400)
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if load is None:
            return (missing_load_id(), 404)
        load.update({"volume": content["volume"], "item": content["item"],
                         "creation_date": content["creation_date"]})
        client.put(load)
        url_of_load = request.root_url + "/loads/" + str(load_key.id)
        res = make_response("")
        res.mimetype = 'application/json'
        res.headers.set('Content-Location', url_of_load)
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
        if "volume" not in content and "item" not in content and "creation_date" not in content:
            return(missing_attribute_error(), 400)
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if load is None:
            return (missing_load_id(), 404)
        if "volume" in content:
            load.update({"volume": content["volume"]})
        if "item" in content:
            load.update({"item": content["item"]})
        if "creation_date" in content:
            load.update({"creation_date": content["creation_date"]})
        client.put(load)
        url_of_load = request.root_url + "/load/" + str(load_key.id)
        res = make_response("")
        res.mimetype = 'application/json'
        res.headers.set('Content-Location', url_of_load)
        res.status_code = 204
        return res
    else:
        return (not_supported_route(), 405)

def missing_attribute_error():
    error_message_for_missing_attributes = '{"Error" : "The request object is missing at ' \
                                           'least one of the required attributes"}'
    return (json.loads(error_message_for_missing_attributes))

def missing_load_number():
    error_message_for_missing_attributes = '{"Error" : "No load with this load_id exists"}'
    return (json.loads(error_message_for_missing_attributes))

def missing_load_id():
    error_message_for_missing_id = '{"Error": "No load with this load_id exists"}'
    return (json.loads(error_message_for_missing_id))

def not_supported_route():
    error_message_not_supported_route = '{"Error": "This method is not supported on this URL"}'
    return (json.loads(error_message_not_supported_route))

def json_not_accepted_in_request():
    error_message_json_not_accepted_in_request= '{"Error" : "This MIME type is not supported by this endpoint."}'
    return (json.loads(error_message_json_not_accepted_in_request))

def too_many_attributes():
    error_message_too_many_attributes = '{"Error" : "The request object has too ' \
                                           'many attributes"}'
    return (json.loads(error_message_too_many_attributes))