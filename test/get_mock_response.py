#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time

import requests

DATADIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")


def parseargs():
    """ Parse arguments """
    parser = argparse.ArgumentParser(description="Create mock response data")
    parser.add_argument(
        "--userid",
        type=int,
        dest="user_id",
        required=True,
        help="User ID")
    parser.add_argument(
        "--act-baseurl",
        dest="act_baseurl",
        required=True,
        help="API URI")

    return parser.parse_args()


def request(method, user_id, url, **kwargs):
    return requests.request(
        method,
        url,
        headers={
            "ACT-User-ID": str(user_id)
        },
        **kwargs
    )


def create_mock(
        baseurl,
        userid,
        method,
        endpoint,
        filepath=DATADIR,
        filename=None,
        expected_status_code=None,
        **kwargs):

    # Send emtpy json map if posting and json arguments is not defined
    if method.lower() == "post" and "json" not in kwargs:
        kwargs["json"] = {}

    r = request(method, userid, "{}/{}".format(baseurl, endpoint), **kwargs)

    status_code = r.status_code

    if not filename:
        filename = "{}_{}_{}.json".format(
            method.lower(),
            endpoint.replace("/", "_"),
            status_code)

    filename = os.path.join(filepath, filename)

    if os.path.isfile(filename):
        sys.stderr.write("Skipping, {} already exists\n".format(filename))
        return json.loads(open(filename).read())["json"]

    if expected_status_code and not (expected_status_code == status_code):
        sys.stderr.write("Skipping, {} did not match expected status code ({} != {})\n".format(
            filename, expected_status_code, status_code))
        return

    try:
        json_data = r.json()
    except json.decoder.JSONDecodeError:
        json_data = "json.decoder.JSONDecodeError"

    with open(filename, "w") as f:
        f.write(json.dumps({
            "url": r.url,
            "status_code": status_code,
            "json": json_data,
            "text": r.text,
            "params": kwargs
        }))

    return json_data


# Create ObjectType
def create_object_type_mock(name, filename):
    create_mock(args.act_baseurl,
                args.user_id,
                "POST",
                "v1/objectType",
                json={
                    "name": name,
                    "validator": "RegexValidator",
                    "validatorParameter": r".+"
                },
                filename=filename,
                expected_status_code=201,
                )


args = parseargs()


create_object_type_mock("threatActor", "post_v1_objectType_threatActor_201.json")
create_object_type_mock("report", "post_v1_objectType_report_201.json")
create_object_type_mock("ipv4", "post_v1_objectType_ipv4_201.json")

# Get Object Types
object_types = create_mock(args.act_baseurl, args.user_id, "GET", "v1/objectType", DATADIR)

# Get Threat Actor object type
threat_actor = [ot for ot in object_types["data"] if ot["name"] == "threatActor"][0]
report = [ot for ot in object_types["data"] if ot["name"] == "report"][0]
ipv4 = [ot for ot in object_types["data"] if ot["name"] == "ipv4"][0]

# Create factType
create_mock(args.act_baseurl,
            args.user_id,
            "POST",
            "v1/factType",
            json={
                "name": "threatActorAlias",
                "validator": "RegexValidator",
                "validatorParameter": ".+",
                "relevantObjectBindings": [{
                    "sourceObjectType": threat_actor["id"],
                    "destinationObjectType": threat_actor["id"],
                    "bidirectionalBinding": True
                }]
            },
            filename="post_v1_factType_threatActorAlias_201.json",
            )

create_mock(args.act_baseurl,
            args.user_id,
            "POST",
            "v1/factType",
            json={
                "name": "seenIn",
                "validator": "RegexValidator",
                "validatorParameter": ".+",
                "relevantObjectBindings": [{
                    "sourceObjectType": ipv4["id"],
                    "destinationObjectType": report["id"],
                    "bidirectionalBinding": False
                }]
            },
            filename="post_v1_factType_seenIn_201.json",
            )

# Get Fact Types
fact_types = create_mock(args.act_baseurl, args.user_id, "GET", "v1/factType", DATADIR)

# Get Threat Actor object type
threat_actor_alias = [ft for ft in fact_types["data"] if ft["name"] == "threatActorAlias"][0]
seen_in = [ft for ft in fact_types["data"] if ft["name"] == "seenIn"][0]

# Create metaFactType
create_mock(args.act_baseurl,
            args.user_id,
            "POST",
            "v1/factType",
            json={
                "name": "observationTime",
                "validator": "RegexValidator",
                "validatorParameter": ".+",
                "relevantFactBindings": [
                    {"factType": threat_actor_alias["id"]},
                    {"factType": seen_in["id"]},
                ]
            },
            filename="post_v1_factType_meta_201.json"
            )

# create fact
create_mock(
    args.act_baseurl,
    args.user_id,
    "POST",
    "v1/fact",
    json={
        "type": "seenIn",
        "value": "report",
        "accessMode": "Public",
        "sourceObject": "ipv4/127.0.0.1",
        "destinationObject": "report/" +
        "87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7"},
    filename="post_v1_fact_127.0.0.1_201.json")

# create fact
create_mock(
    args.act_baseurl,
    args.user_id,
    "POST",
    "v1/fact",
    json={
        "type": "seenIn",
        "value": "report",
        "accessMode": "Public",
        "sourceObject": "ipv4/127.0.0.2",
        "destinationObject": "report/" +
        "87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7"},
    filename="post_v1_fact_127.0.0.2_201.json")

# Give time for fact to be created so it is searchable
time.sleep(2)

facts = create_mock(args.act_baseurl,
                    args.user_id,
                    "POST",
                    "v1/fact/search",
                    json={
                        "factType": ["seenIn"],
                        "factValue": ["report"],
                        "limit": 1
                    },
                    expected_status_code=200
                    )

# Get fact ID from search above
fact_id = facts["data"][0]["id"]

# Get fact
create_mock(
    args.act_baseurl,
    args.user_id,
    "GET",
    "v1/fact/uuid/{}".format(fact_id),
    filename="get_v1_fact_uuid_200.json")

# Create Meta Fact
create_mock(
    args.act_baseurl,
    args.user_id,
    "POST",
    "v1/fact/uuid/{}/meta".format(fact_id),
    json={
        "type": "observationTime",
        "value": "2016-09-28T21:26:22Z",
        "accessMode": "Public",
    },
    filename="post_v1_fact_uuid_meta_201.json",
    expected_status_code=201
)

time.sleep(1)

# Get Meta Facts
create_mock(
    args.act_baseurl,
    args.user_id,
    "GET",
    "v1/fact/uuid/{}/meta".format(fact_id),
    filename="get_v1_fact_uuid_meta_200.json",
    expected_status_code=200
)

# Add comment
facts = create_mock(args.act_baseurl,
                    args.user_id,
                    "POST",
                    "v1/fact/uuid/{}/comments".format(fact_id),
                    json={
                        "comment": "Test comment"
                    },
                    filename="post_v1_fact_uuid_comments_201.json")

# Get comment
facts = create_mock(args.act_baseurl,
                    args.user_id,
                    "GET",
                    "v1/fact/uuid/{}/comments".format(fact_id),
                    filename="get_v1_fact_uuid_comments_200.json")

# Get ACL
create_mock(
    args.act_baseurl,
    args.user_id,
    "GET",
    "v1/fact/uuid/{}/access".format(fact_id),
    filename="get_v1_fact_uuid_access_200.json")

# Get Object by Type/Value
obj = create_mock(
    args.act_baseurl,
    args.user_id,
    "GET",
    "v1/object/{}/{}".format("ipv4", "127.0.0.1"),
    filename="get_v1_object_200.json")

obj_id = obj["data"]["id"]

# Get facts bound to object by Type/Value
create_mock(
    args.act_baseurl,
    args.user_id,
    "POST",
    "v1/object/{}/{}/facts".format("ipv4", "127.0.0.1"),
    filename="post_v1_object_facts_200.json")


# Get Object by id
create_mock(
    args.act_baseurl,
    args.user_id,
    "GET",
    "v1/object/uuid/{}".format(obj_id),
    filename="get_v1_object_uuid_200.json")

# Get Facts bound to object by id
create_mock(
    args.act_baseurl,
    args.user_id,
    "POST",
    "v1/object/uuid/{}/facts".format(obj_id),
    filename="post_v1_object_uuid_facts_200.json")

# Search objects
create_mock(args.act_baseurl,
            args.user_id,
            "POST",
            "v1/object/search",
            json={
                "factType": ["seenIn"],
                "factValue": ["report"],
                "limit": 1
            })

# Traverse by object type/value
create_mock(args.act_baseurl,
            args.user_id,
            "POST",
            "v1/object/{}/{}/traverse".format("ipv4", "127.0.0.1"),
            json={"query": 'g.bothE("seenIn").bothV().path().unfold()'},
            filename="post_v1_object_traverse_200.json")

# Traverse from object id
create_mock(args.act_baseurl,
            args.user_id,
            "POST",
            "v1/object/uuid/{}/traverse".format(obj_id),
            json={"query": 'g.bothE("seenIn").bothV().path().unfold()'},
            filename="post_v1_object_uuid_traverse_200.json")

# Retract fact
create_mock(
    args.act_baseurl,
    args.user_id,
    "POST",
    "v1/fact/uuid/{}/retract".format(fact_id),
    filename="post_v1_fact_uuid_retract_201.json")

# Get origins
create_mock(
    args.act_baseurl,
    args.user_id,
    "GET",
    "v1/origin?includeDeleted=False&limit=0",
    filename="get_v1_origin_200.json")

# Create origin
create_mock(args.act_baseurl,
    args.user_id,
    "POST",
    "v1/origin",
    json={
        "name": "my-origin",
        "description": "My origin",
        "trust": 0.8
    },
    filename="post_v1_origin_myorigin_201.json",
    )
