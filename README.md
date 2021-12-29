# ipnetdb-service

Containerised microservice to provide an HTTP JSON API for IPNetDB databases.

This service is designed to be built as a container and deployed in an
application stack or with container orchestration for example with
docker-compose or kubernetes. It provides an HTTP-based JSON API to query
IPNetDB network information databases from https://IPNetDB.com/

On start the container will download the latest IPNetDB databases and then
update the databases every Monday.

*NOTE:* IPNetDB databases from https://IPNetDB.com/ are free for open source
use they are not free for commercial or closed source use. Please make sure you
read the licence on https://IPNetDB.com/ to make sure you are compliant before
using this container!

