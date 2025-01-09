# Example test pagination api

## Setup
1. get a conda-store token

2. save it as an env var

```bash
export CS_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzY0NTYyNzksInByaW1hcnlfbmFtZXNwYWNlIjoidGVzdCIsInJvbGVfYmluZGluZ3MiOnsiKi8qIjpbImFkbWluIl19fQ.sosEyBJg2eIKuphdyn881V-RIBvz5baZmuEdfogWZSo
```
3. verify token is valid

```bash
$ curl --header "Authorization: bearer ${CS_TOKEN}" http://localhost:8080/conda-store/api/v1/permission/ | jq 
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   785  100   785    0     0   127k      0 --:--:-- --:--:-- --:--:--  153k
{
  "status": "ok",
  "data": {
    "authenticated": true,
    "primary_namespace": "test",
    "entity_permissions": {
      "default/*": [
        "environment::read",
        "namespace-role-mapping::read",
        "namespace::read"
      ],
      "filesystem/*": [
        "environment::read",
        "namespace-role-mapping::read",
        "namespace::read"
      ],
      "*/*": [
        "build::cancel",
        "build::delete",
        "environment::delete",
        "environment::read",
        "environment::solve",
        "environment::update",
        "environment:create",
        "namespace-role-mapping::create",
        "namespace-role-mapping::delete",
        "namespace-role-mapping::read",
        "namespace-role-mapping::update",
        "namespace::create",
        "namespace::delete",
        "namespace::read",
        "namespace::update",
        "setting::read",
        "setting::update"
      ]
    },
    "entity_roles": {
      "default/*": [
        "viewer"
      ],
      "filesystem/*": [
        "viewer"
      ],
      "*/*": [
        "admin"
      ]
    },
    "expiration": "2025-01-09T20:57:59Z"
  },
  "message": null
}
```

## Sample queries

Basic get environment
```bash
$ curl --header "Authorization: bearer ${CS_TOKEN}" http://localhost:8080/conda-store/api/v1/environment/ | jq
```

Get 5 batch of results
```bash
$ curl --header "Authorization: bearer ${CS_TOKEN}" http://localhost:8080/conda-store/api/v1/environment/?limit=5 | jq
```

Page thru the results
```bash
# get the first page
$ curl --header "Authorization: bearer ${CS_TOKEN}" http://localhost:8080/conda-store/api/v1/environment/\?limit\=2 | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   461  100   461    0     0  14422      0 --:--:-- --:--:-- --:--:-- 14870
{
  "data": [
    {
      "id": 1,
      "namespace": {
        "id": 2,
        "name": "filesystem",
        "metadata_": {},
        "role_mappings": []
      },
      "name": "python-flask-env",
      "current_build_id": 1,
      "current_build": null,
      "description": ""
    },
    {
      "id": 15,
      "namespace": {
        "id": 1,
        "name": "default",
        "metadata_": {},
        "role_mappings": []
      },
      "name": "complicated-environment",
      "current_build_id": 17,
      "current_build": null,
      "description": ""
    }
  ],
  "status": "ok",
  "message": null,
  "cursor": "eyJsYXN0X2lkIjoxNSwiY291bnQiOjYsImxhc3RfdmFsdWUiOnt9fQ==",
  "count": 6
}

# use the cursor from the previous result to get the next page
$ curl --header "Authorization: bearer ${CS_TOKEN}" http://localhost:8080/conda-store/api/v1/environment/\?limit\=2\&encoded_cursor\=eyJsYXN0X2lkIjoxNSwiY291bnQiOjYsImxhc3RfdmFsdWUiOnt9fQ== | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   421  100   421    0     0  13185      0 --:--:-- --:--:-- --:--:-- 13580
{
  "data": [
    {
      "id": 16,
      "namespace": {
        "id": 20,
        "name": "test1",
        "metadata_": {},
        "role_mappings": []
      },
      "name": "a",
      "current_build_id": 18,
      "current_build": null,
      "description": ""
    },
    {
      "id": 17,
      "namespace": {
        "id": 20,
        "name": "test1",
        "metadata_": {},
        "role_mappings": []
      },
      "name": "b",
      "current_build_id": 19,
      "current_build": null,
      "description": ""
    }
  ],
  "status": "ok",
  "message": null,
  "cursor": "eyJsYXN0X2lkIjoxNywiY291bnQiOjQsImxhc3RfdmFsdWUiOnt9fQ==",
  "count": 4
}
```