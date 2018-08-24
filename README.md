# python-act

python-act is a library used to connect to the [ACT platform](https://github.com/mnemonic-no/act-platform).

The platform has a REST api, and the goal of this library is to expose all functionality in the API.

# Objects and Facts

The act platform is built on two basic types, the object and fact.

Objects are universal elements that can be referenced uniquely by its value. An example of an object can be an IP address.

Facts are assertions or obsersvations that ties objects together. A fact may or may not have a value desribing further the fact.


Facts can be linked on or more objects. Below, the seenIn fact is linked to both an ipv4 object and report object, but the hasTitle fact is only linked to a report.

|Object type|Object value|Fact type|Fact value|Object type|Object value|
| ----------|------------|---------|----------|-----------|------------|
|ipv4       |127.0.0.1   |seenIn   |report    |report     |cbc80bb5c0c0f8944bf73(...)|
|report     |cbc80bb5c0c0f8944bf73(...)|hasTitle|Threat Intel Summary|*n/a*|*n/a*|

# Design principles of the Python API.

* Most functions returns an object that can be chained
* Attributes can be accessed using dot notation (e.g fact.name and fact.type.name)

# Example usage


## Connect to the API

Connct to the API using an URL where the API is exposed and a user ID:

```
>>> import act
>>> c = act.Act("http://localhost:8080", user_id = 1, log_level = "warning")
```

The returned object exposes most of the API in the ACT platform:

* fact - Manage facts
* fact_search - Search facts
* fact_type - Instantiate a fact type
* get_fact_types - Get fact types
* object - Manage objects
* object_search - Searh objects
* object_type - Get object types

Additional arguments to act.Act can be passed on to [requests](http://docs.python-requests.org) using the requests_common_kwargs, which mans you can add for instance `auth` if the instance is behind a reverse proxy with HTTP authentication:

```
>>> c = act.Act("http://localhost:8080", user_id = 1, log_level = "warning", requests_common_kwargs = {"auth": ("act", "<PASSWORD>")})
```

## Create fact

Create a fact by calling `fact()`. The result can be chained using one or more `source()`, `destination()` or `bidirectionial()` to add linked objects.

```
>>> f = c.fact("seenIn", "report").source("ipv4", "127.0.0.1")
>>> f
{'value': 'report', 'id': None, 'timestamp': None, 'organization': None, 'last_seen_timestamp': None, 'type': {'relevant_object_bindings': None, 'id': None, 'name': 'seenIn', 'entity_handler': 'IdentityHandler', 'namespace': None, 'entity_handler_parameter': None, 'validator': 'RegexValidator', 'validator_parameter': '(.|\\n)+'}, 'objects': [{'value': '127.0.0.1', 'type': {'id': None, 'name': 'ipv4', 'entity_handler': 'IdentityHandler', 'namespace': None, 'entity_handler_parameter': None, 'validator': 'RegexValidator', 'validator_parameter': '(.|\\n)+'}, 'statistics': None, 'id': None, 'direction': 'FactIsDestination'}], 'in_reference_to': None, 'access_mode': 'Public'}
```

The fact is not yet added to the platform. User `serialize()` or `json()` to see the parameters that will be sent to the platform when the fact is added.

```
>>> f.serialize()
{'value': 'report', 'type': 'seenIn', 'bindings': [{'objectValue': '127.0.0.1', 'objectType': 'ipv4', 'direction': 'FactIsDestination'}], 'accessMode': 'Public'}
>>> f.json()
'{"value": "report", "type": "seenIn", "bindings": [{"objectValue": "127.0.0.1", "objectType": "ipv4", "direction": "FactIsDestination"}], "accessMode": "Public"}'
```

Since the fact is not yet added it does not have an id.

```
>>> print(f.id)
None
```

Use `add()` to add the fact to the platform.
```
>>> f.add()
{'value': 'report', 'id': 'ca55d514-6914-42f6-aa62-949b2a04f315', 'timestamp': '2018-04-29T08:41:57.580Z', 'organization': {'id': '00000000-0000-0000-0000-000000000001', 'name': 'Test Organization 1'}, 'last_seen_timestamp': '2018-04-29T08:43:32.987Z', 'type': {'relevant_object_bindings': None, 'id': '02f083e3-d9dc-46a0-8bb4-b192fc4ec910', 'name': 'seenIn', 'entity_handler': 'IdentityHandler', 'namespace': None, 'entity_handler_parameter': None, 'validator': 'RegexValidator', 'validator_parameter': '(.|\\n)+'}, 'objects': [{'value': '127.0.0.1', 'id': '0d4e7ad9-a911-4ce3-b7e6-2dcb41ed1b32', 'statistics': None, 'type': {'id': '8a250c06-95f3-4ef5-acee-ffe2ee1d3de5', 'name': 'ipv4', 'entity_handler': 'IdentityHandler', 'namespace': None, 'entity_handler_parameter': None, 'validator': 'RegexValidator', 'validator_parameter': '(.|\\n)+'}, 'direction': 'FactIsDestination'}], 'in_reference_to': {'value': '-', 'type': {'relevant_object_bindings': None, 'id': None, 'name': None, 'entity_handler': 'IdentityHandler', 'namespace': None, 'entity_handler_parameter': None, 'validator': 'RegexValidator', 'validator_parameter': '(.|\\n)+'}, 'id': None}, 'access_mode': 'Public'}
```

The fact will be replaced with the fact added to the platform and it will now have an id.
```
>>> print(f.id)
ca55d514-6914-42f6-aa62-949b2a04f315
```


## Get fact
Use `get()` to get a fact by it's id.
```
>>> f = c.fact(id="0f0cf526-5fad-4984-9ec5-90ac811e8798").get()
```

Properties on objects can be retrieved by dot notation.
```
>>> f.type.name
'seenIn'
>>> f.value
'report'
```

## Retract fact
Use `retract()` to retract a fact.. The fact *must* have an id, either by specyfing it directly, or retriving the fact from a search.

```
>>> f = c.fact(id='1ba6c36a-8300-4ea1-aded-03ee80083dff')
>>> f.retract()
```

## Search Objects

```
>>> objects = c.object_search(object_value="127.0.0.1", after="2016-09-28T21:26:22Z")
>>> len(objects)
1
>>> objects[0].type.name
'ipv4'
>>> objects[0].value
'127.0.0.1'
>>> objects[0].statistics[0].type.name
'DNSRecord'
>>> objects[0].statistics[0].count
131
>>> objects[0].statistics[1].type.name
'seenIn'
>>> objects[0].statistics[1].count
114
```

## Create object type

```
>>> object_type = = c.object_type("fqdn").add()
```



## Search facts
Search fact and limit search by using the parameters.
```
>>> help(c.fact_search)
Help on method fact_search in module act.helpers:

fact_search(keywords='', object_type=[], fact_type=[], object_value=[], fact_value=[], organization=[], source=[], include_retracted=None, before=None, after=None, limit=None) method of act.helpers.Act instance
    Search objects
    Args:
        keywords (str):               Only return Facts matching a keyword query
        object_type (str[] | str):    Only return Facts with objects having a specific
                                      ObjectType
        fact_type (str[] | str):      Only return Facts having a specific FactType
        object_value (str[] | str):   Only return Facts with objects matching a specific
                                      value
        fact_value (str[] | str):     Only return Facts matching a specific value
        organization (str[] | str):   Only return Facts belonging to
                                      a specific Organization
        source (str[] | str):         Only return Facts coming from a specific Source
        include_retracted (bool):     Include retracted Facts (default=False)
        before (timestamp):           Only return Facts added before a specific
                                      timestamp. Timestamp is on this format:
                                      2016-09-28T21:26:22Z
        after (timestamp):            Only return Facts added after a specific
                                      timestamp. Timestamp is on this format:
                                      2016-09-28T21:26:22Z
        limit (integer):              Limit the number of returned Objects
                                      (default 25, 0 means all)

    All arguments are optional.

    Returns ActResultSet of Facts.
```

By default the search will return and ActResultSet with 25 itmes.
```
>>> facts = c.fact_search(fact_type="seenIn", fact_value="report")
>>> len(facts)
25
>>> facts.size
25
>>> facts.count
820304
```
The `complete` property can be used to to check whether the result returned all available items.

```
>>> facts.complete
False
```

Use the limit parameter to get more items.
```
>>> facts = c.fact_search(fact_type="seenIn", fact_value="report", object_value="127.0.0.1", limit=2000)
>>> facts.size
119
>>> facts.complete
True
```

## Get Object types
Get all object types.
```
>>> object_types = c.get_object_types()
>>> len(object_types)
46
>>> len(object_types)
46
>>> object_types[0].name
'technique'
>>> object_types[0].validator
'RegexValidator'
>>> object_types[0].validator_parameter
'(.|\\n)+'
```

## Graph queries
The act platform has support for graph queries using the Gremlin Query language.

Use the `traverse()` function from an object to perform a graph query.

```
>>> c.object("ipv4", "127.0.0.220").traverse('g.bothE("seenIn").bothV().path().unfold()')
>>> type(path[0])
<class 'act.obj.Object'>
>>> type(path[1])
<class 'act.fact.Fact'>
```

You will normally want to use `unfold()` in the gremlin query to make sure you recive objects and facts.

Here is an example querying for threat actor aliases.

The graph of this will look like the screen shot below.

![Threat Actor Aliases](doc/ta-alias.png "Threat Actor aliases to 'APT 29'")

```
>>> aliases = c.object("threatActor", "APT 29").traverse('g.repeat(outE("threatActorAlias").outV()).until(cyclicPath()).path().unfold()')
>>> obj = [obj.value for obj in aliases if isinstance(obj, act.obj.Object)]
>>> obj
['APT 29', 'OfficeMonkeys', 'APT 29', 'APT 29', 'The Dukes', 'APT 29', 'APT 29', 'Hammer Toss', 'APT 29', 'APT 29', 'EuroAPT', 'APT 29', 'APT 29', 'CozyDuke', 'APT 29', 'APT 29', 'Office Monkeys', 'APT 29', 'APT 29', 'CozyCar', 'APT 29', 'APT 29', 'APT29', 'APT 29', 'APT 29', 'Dukes', 'APT 29', 'APT 29', 'Cozy Duke', 'APT 29', 'APT 29', 'Cozer', 'APT 29', 'APT 29', 'CozyBear', 'APT 29', 'APT 29', 'Cozy Bear', 'APT 29', 'APT 29', 'SeaDuke', 'APT 29', 'APT 29', 'Group 100', 'APT 29', 'APT 29', 'Minidionis', 'APT 29', 'APT 29', 'The Dukes', 'APT29', 'APT 29', 'APT 29', 'The Dukes', 'APT29', 'The Dukes', 'APT 29', 'CozyDuke', 'APT29', 'APT 29', 'APT 29', 'CozyDuke', 'APT29', 'CozyDuke', 'APT 29', 'APT29', 'The Dukes', 'APT29', 'APT 29', 'APT29', 'The Dukes', 'APT 29', 'APT 29', 'APT29', 'Cozy Bear', 'APT 29', 'APT 29', 'APT29', 'Cozy Bear', 'APT29', 'APT 29', 'APT29', 'CozyDuke', 'APT 29', 'APT 29', 'APT29', 'CozyDuke', 'APT29', 'APT 29', 'Cozy Bear', 'APT29', 'APT 29', 'APT 29', 'Cozy Bear', 'APT29', 'Cozy Bear', 'APT 29', 'The Dukes', 'APT29', 'Cozy Bear', 'APT 29', 'APT 29', 'The Dukes', 'APT29', 'Cozy Bear', 'APT29', 'APT 29', 'The Dukes', 'APT29', 'CozyDuke', 'APT 29', 'APT 29', 'The Dukes', 'APT29', 'CozyDuke', 'APT29', 'APT 29', 'CozyDuke', 'APT29', 'The Dukes', 'APT29', 'APT 29', 'CozyDuke', 'APT29', 'The Dukes', 'APT 29', 'APT 29', 'CozyDuke', 'APT29', 'Cozy Bear', 'APT 29', 'APT 29', 'CozyDuke', 'APT29', 'Cozy Bear', 'APT29', 'APT 29', 'Cozy Bear', 'APT29', 'The Dukes', 'APT29', 'APT 29', 'Cozy Bear', 'APT29', 'The Dukes', 'APT 29', 'APT 29', 'Cozy Bear', 'APT29', 'CozyDuke', 'APT 29', 'APT 29', 'Cozy Bear', 'APT29', 'CozyDuke', 'APT29']
>>> set(obj)
{'Office Monkeys', 'EuroAPT', 'Minidionis', 'APT29', 'OfficeMonkeys', 'Hammer Toss', 'CozyCar', 'The Dukes', 'Cozer', 'CozyBear', 'Cozy Bear', 'SeaDuke', 'Group 100', 'Dukes', 'CozyDuke', 'Cozy Duke', 'APT 29'}
```

# Tests
Tests (written in pytest) are contained in the test/ folder. Mock objects are available for for most API requests in the test/data/ folder.


This command will execute the tests using both python2 and python3 (requires pytest, python2 and python3).
```
test/run-tests.sh
```
