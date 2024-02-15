up:
	git pull
	# See: https://github.com/docker/cli/issues/1073
	docker compose config | sed '/published:/ s/"//g' | sed "/name:/d" | docker stack deploy -c - zwop

down:
	docker stack rm zwop

dev-docker:
	docker build . --tag zwop:dev
	docker run -it --rm -v $(PWD):/app -p 8000:8000 zwop:dev
