docker=/usr/bin/docker
name=ipnetdb-service
image=$(name):latest


all: container


container:
	$(docker) build -t $(image) .


runcontainer:
	$(docker) run --rm --name $(name) --log-opt max-size=50m -ti -p 80:80 $(image)
