setup:
	pipenv check || pipenv install

develop: setup
	pipenv shell -c
