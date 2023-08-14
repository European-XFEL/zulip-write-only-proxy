up:
	git pull
	docker compose config | docker stack deploy -c - zwop

down:
	docker stack rm zwop
