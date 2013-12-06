
all: prep test run

prep:
	@pip install -r requirements.txt > /dev/null
	@pip install -r requirements-tests.txt > /dev/null
	@find . -name "*.pyc" -delete

test: prep unittest lint

unittest:
	#@nosetests --with-coverage --cover-html --cover-erase --cover-branches --cover-package=autoroute

lint:
	@find . -name '*.py' -exec flake8 {} \;

verboselint:
	@find . -name '*.py' -exec flake8 --show-pep8 --show-source {} \;

run: prep
	@python autoroute.py

# remove the doc folder
clean:
	@find . -name "*.pyc" -delete
	@rm -r cover

template:
	@aws/process-template.py

.PHONY: clean all test run prep lint unittest template
