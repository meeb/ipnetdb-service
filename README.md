# ipnetdb-service

Containerised microservice to provide an HTTP JSON API for IPNetDB databases.

This service is designed to be built as a container and deployed in a
containerised application stack or with container orchestration such as with
docker-compose or kubernetes. It provides an HTTP-based JSON API to query
[IPNetDB](https://IPNetDB.com/) network information databases from
https://ipnetdb.com/

**NOTE:** [IPNetDB](https://IPNetDB.com/) databases are free for open source
use but they are not free for commercial or closed source use. Please make sure
you read the licence on https://ipnetdb.com/ to make sure you are compliant
before using this container! You may need to pay for a licence or add
attribution to your project.

The [IPNetDB](https://IPNetDB.com/) databases are not bundled with this
container. They are downloaded directly from [IPNetDB](https://IPNetDB.com/).


## Installation

You can either build this container yourself:

```bash
$ make container
```

Or you can pull a tagged container image directly from here:

```
ghcr.io/meeb/ipnetdb-service:v0.1.0
```


## Running

IPNetDB-Service has no configurable environment variables. The container only
opens an HTTP server on TCP port 80. You can run it via docker with:

```bash
$ docker run --rm --name ipnetdb-service -p 80:80 ghcr.io/meeb/ipnetdb-service:v0.1.0
```

Or for example in a compose stack:

```yaml
  ipnetdb-service:
    image: ghcr.io/meeb/ipnetdb-service:v0.1.0
    container_name: ipnetdb-service
    restart: unless-stopped
    ports:
      - 80:80
```

IPNetDB-Service is suitable to be used with multiple replicas and in Kubernetes
or other container orchestration clusters.


## Behaviour

On start the IPNetDB-Service container will download the latest IPNetDB
databases from https://ipnetdb.com/ . This may take a minute or two and the
service will not be available until this start-up task is complete.

At a random time every Monday the IPNetDB databases will be automatically
updated and reloaded. The container should be self-maintaining and require
no operations time to maintain other than monitoring the healthcheck.

The embedded API server is built on nginx with OpenResty and is capable of
very high throughput.


## Usage

The HTTP API has 4 endpoints, listed below. If you query any other URL,
including the `/` root resource, you will see a help page with a
`404/Not Found` status code.


### GET `/healthcheck`

Performs a healthcheck on the container and returns a `{"health": "ok"}`
along with a `200/OK` status code if the container is healthy. Any other
response means the container is not healthy.

```bash
$ curl -s http://ipnetdb-service/healthcheck | jq
{
  "health": "ok"
}
```


### GET `/index`

Returns the currently loaded IPNetDB database index in JSON format. This
response is identical to the JSON file at https://ipnetdb.com/latest.json
and can be used to determine if the databases currently loaded in the
container are up to date. Returns either a `200/OK` response if an index
is available or a `404/Not Found` if no index is loaded.

```bash
$ curl -s http://ipnetdb-service/index | jq      
{
  "prefix": {
    "url": "https://cdn.ipnetdb.net/ipnetdb_prefix_latest.mmdb",
    "file": "ipnetdb_prefix_latest.mmdb",
    "date": "2021-12-26",
    "sha256": "4f740044b16336c07127a124470da4f1fec57586b8bbece952ca85d3d9e78bea",
    "bytes": 127849480
  },
  "asn": {
    "url": "https://cdn.ipnetdb.net/ipnetdb_asn_latest.mmdb",
    "file": "ipnetdb_asn_latest.mmdb",
    "date": "2021-12-26",
    "sha256": "7659820d2eba672f6b9bc553eccf638690c5ca6cfb1ca12ac254349d893f171f",
    "bytes": 27796664
  }
}
```


### GET `/ip/[any IPv4 or IPv6 address]`

Fetches information on an any IPv4 or IPv6 address. Returns either a `200/OK`
status and information on the IP address or a `404/Not Fouind` status if the IP
has no information in the database. Response is always in JSON. The following
fields are always returned:

`query`: The IP address that was queried
`type`: The type of query issued, set to the string "ip" for IP queries
`status`: Either "found" or "not found"
`result`: A JSON object of the results of the query if found

See https://ipnetdb.com/ for more details on the result fields returned.

```bash
$ curl -s http://ipnetdb-service/ip/1.1.1.1 | jq
{
  "result": {
    "allocation": "1.1.1.0/24",
    "allocation_cc": "AU",
    "allocation_registry": "apnic",
    "allocation_status": "assigned",
    "as": 13335,
    "as_cc": "US",
    "as_entity": "Cloudflare, Inc.",
    "as_name": "CLOUDFLARENET",
    "as_private": false,
    "as_registry": "arin",
    "prefix_asset": {},
    "prefix_assignment": "assigned portable",
    "prefix_bogon": false,
    "prefix_entity": "APNIC and Cloudflare DNS Resolver project",
    "prefix_name": "APNIC-LABS",
    "prefix_origins": [
      13335
    ],
    "prefix_registry": "apnic",
    "prefix": "1.1.1.0/24"
  },
  "query": "1.1.1.1",
  "status": "found",
  "type": "ip"
}
```

An example query for an IPv6 address:

```bash
$ curl -s http://localhost/ip/2001:4860:4860::8888 | jq
{
  "result": {
    "allocation": "2001:4860::/32",
    "allocation_cc": "US",
    "allocation_registry": "arin",
    "allocation_status": "allocated",
    "as": 15169,
    "as_cc": "US",
    "as_entity": "Google LLC",
    "as_name": "GOOGLE",
    "as_private": false,
    "as_registry": "arin",
    "prefix_asset": {},
    "prefix_assignment": "",
    "prefix_bogon": false,
    "prefix_entity": "",
    "prefix_name": "",
    "prefix_origins": [
      15169
    ],
    "prefix_registry": "",
    "prefix": "2001:4860::/32"
  },
  "query": "2001:4860:4860::8888",
  "status": "found",
  "type": "ip"
}
```


An example query to an IP address not in the databases:

```bash
$ curl -s http://ipnetdb-service/ip/0.0.0.0 | jq
{
  "result": {},
  "query": "0.0.0.0",
  "status": "not found",
  "type": "ip"
}
```


### GET `/as/[any AS number]`

Fetches information on an any autonomous systems number. Returns either a
`200/OK` status and information on the ASN or a `404/Not Fouind` status if the
ASN has no information in the database. Response is always in JSON. The
following fields are always returned:

`query`: The ASN that was queried
`type`: The type of query issued, set to the string "as" for ASN queries
`status`: Either "found" or "not found"
`result`: A JSON object of the results of the query if found

See https://ipnetdb.com/ for more details on the result fields returned.

```bash
$ curl -s http://ipnetdb-service/as/12345 | jq  
{
  "result": {
    "name": "AS12345",
    "cc": "IT",
    "entity": "General Software s.r.l.",
    "in_use": true,
    "ipv4_prefixes": [
      "212.47.32.0/19"
    ],
    "as": 12345,
    "ipv6_prefixes": {},
    "peers": [
      28716
    ],
    "private": false,
    "registry": "ripe",
    "status": "allocated"
  },
  "query": "12345",
  "status": "found",
  "type": "as"
}
```

An example query to an ASN not in the databases:

```bash
$ curl -s http://localhost/as/0 | jq
{
  "result": {},
  "query": "0",
  "status": "not found",
  "type": "as"
}
```


# Contributing

All properly formatted and sensible pull requests, issues and comments are
welcome.
