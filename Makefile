# This is a temporary solution until a proper gettextPOT generation and
# setup.py-install target has been written.

FILES = $(shell find MAGSBS -type f -name '*.py')

all: pot

pot:
	pygettext --keyword=_ --output=matuc.pot $(FILES)

mo: $(wildcard po/*.po)
	for LANG in $(basename $(notdir $^)); do \
		mkdir -p locale/$$LANG/LC_MESSAGES; \
		msgfmt --output-file=locale/$$LANG/LC_MESSAGES/matuc.mo po/$$LANG; \
	done

# merge new strings and old translations
update: pot
	mkdir -p po
	for file in `ls po/*.po`; do \
		msgmerge -F -U $$file matuc.pot; \
	done
