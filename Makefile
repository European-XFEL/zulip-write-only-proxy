up:
	git pull
	# See: https://github.com/docker/cli/issues/1073
	docker compose config | sed '/published:/ s/"//g' | sed "/name:/d" | docker stack deploy -c - zwop

down:
	docker stack rm zwop
