# This is a temporary solution until a proper gettextPOT generation and
# setup.py-install target has been written.

FILES = $(shell find MAGSBS -type f -name '*.py')

all: pot

clean:
	rm -f MAGSBS/*.pyo
	find . -type d -name __pycache__ -exec rm -r '{}' ';'

mo: $(wildcard po/*.po)
	for LANG in $(basename $(notdir $^)); do \
		mkdir -p locale/$$LANG/LC_MESSAGES; \
		msgfmt --output-file=locale/$$LANG/LC_MESSAGES/matuc.mo po/$$LANG; \
	done

pot:
	pygettext --keyword=_ --output=matuc.pot $(FILES)

# merge new strings and old translations
update: pot
	mkdir -p po
	for file in `ls po/*.po`; do \
		msgmerge -F -U $$file matuc.pot; \
	done
