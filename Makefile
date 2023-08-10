up:
	docker compes config | docker stack deploy -c - zwop

down:
	docker stack rm zwop
