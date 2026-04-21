# This is a temporary solution until we can somehow pyproject.toml to do the
# translation meging for us.

FILES = $(shell find MAGSBS -type f -name '*.py')
# pygettext ironically detected fewer strings for translation than xgettext.
GETTEXT ?= xgettext
ifeq ($(shell which $(GETTEXT)),)
$(error Couldn't find $(GETTEXT)! Install it first.")
endif
MSGMERGE ?= msgmerge
ifeq ($(shell which $(MSGMERGE)),)
$(error Couldn't find msgmerge! Install it first.")
endif

all: update

clean:
	rm -f MAGSBS/*.pyo
	find . -type d -name __pycache__ -exec rm -r '{}' ';'

mo: $(wildcard po/*.po)
	for LANG in $(basename $(notdir $^)); do \
		mkdir -p locale/$$LANG/LC_MESSAGES; \
		msgfmt --output-file=locale/$$LANG/LC_MESSAGES/matuc.mo po/$$LANG; \
	done

pot:
	$(GETTEXT) -L Python -o matuc.pot $(FILES)

# merge new strings and old translations
update: pot
	mkdir -p po
	for file in `ls po/*.po`; do \
		$(MSGMERGE) -F -U $$file matuc.pot; \
	done
