setup:
	which pipenv >/dev/null || pip install pipenv
	pipenv check || pipenv install

develop: setup
	pipenv shell -c
