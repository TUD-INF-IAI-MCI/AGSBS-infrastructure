#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import unittest, sys, collections, os, itertools
sys.path.insert(0, '.') # just in case
import MAGSBS.errors as errors
import MAGSBS.mparser as mp

def parse_formulas(doc):
    """Tiny helper to call mp.parse_formulas."""
    return mp.parse_formulas({1: doc.split('\n')})



class test_mparser(unittest.TestCase):

    ##############################################################
    # extract_headings_from_par
    def test_that_an_underlined_h1_is_extracted(self):
        pars = {1:['jo', '===']}
        self.assertEqual(len(mp.extract_headings_from_par(pars)), 1)

    def test_that_an_underlined_h2_is_extracted(self):
        pars = {1:['jo','---']}
        self.assertEqual(len(mp.extract_headings_from_par(pars)), 1)

    def test_that_max_headings_is_used(self):
        pars = {1:['jo','===='], 4:['##test']}
        self.assertEqual(len(mp.extract_headings_from_par(pars, 1)), 1)

    def test_that_headings_with_hashes_are_recognized(self):
        pars = {1:['#h1'], 4:['##h2']}
        self.assertEqual(len(mp.extract_headings_from_par(pars)), 2)

    ##############################################################
    # test extract_page_numbers_from_par

    def test_that_correct_pnum_is_recognized(self):
        pnums = mp.extract_page_numbers_from_par({1:['|| - Seite 80 -']})
        self.assertEqual(len(pnums), 1, "exactly one page number is expected.")
        self.assertEqual(pnums[0].number, 80)

    def test_that_more_than_one_pnum_is_parsed_and_line_numbers_are_correct(self):
        pars = collections.OrderedDict()
        pars[1] = ['|| - Seite 80 -']
        pars[3] = ['|| Some text', 'hopefully ignored']
        pars[5] = ['|| - Seite 81 -']
        pnums = mp.extract_page_numbers_from_par(pars)
        self.assertEqual(len(pnums), 2)
        lnums = [pnum.line_no for pnum in pnums]
        self.assertTrue(1 in lnums and 5 in lnums)


    def test_that_incorrect_pnum_is_not_recognized(self):
        pars = {1:['|| - alles fehlerhaft hier -']}
        self.assertEqual(len(mp.extract_page_numbers_from_par(pars)), 0)

    def test_that_invalid_page_numbers_are_ignored(self):
        pnums = mp.extract_page_numbers_from_par({1:['|| - Seite abc -']})
        self.assertEqual(len(pnums), 0)

    def test_that_lower_case_page_identifiers_are_recognized(self):
        pnums = mp.extract_page_numbers_from_par({999:['|| - seite 80 -']})
        self.assertEqual(len(pnums), 1)

    def test_that_varying_spaces_are_not_an_issue(self):
        pnums = mp.extract_page_numbers_from_par({1:['|| -Seite  80 -'],
            7:['||  - Seite 80-']})
        self.assertEqual(len(pnums), 2)

    def test_that_roman_numbers_work(self):
        pnums = mp.extract_page_numbers_from_par({1:['|| - Seite I -'],
            7:['|| - Seite XVI -'], 20:['|| - Seite CCC -']})
        self.assertEqual(len(pnums), 3)

    def test_invalid_roman_numbers_trigger_exception(self):
        pnums = mp.extract_page_numbers_from_par({1:['|| - Seite IIIIIVC -']})
        self.assertEqual(len(pnums), 0)


    ##############################################################
    # test file2paragraphs
    def test_that_a_simple_paragraph_is_recognized(self):
        pars = mp.file2paragraphs(['Hallo Welt'])
        self.assertEqual(len(pars), 1)
        self.assertEqual(pars[1], ['Hallo Welt'])

    def test_that_a_multiline_paragraph_is_recognized_correctly(self):
        expected = ['Hallo','Welt']
        actual = mp.file2paragraphs('\n'.join(expected))
        self.assertEqual(actual[1], expected)

    def test_that_multiple_paragraphs_are_recognized(self):
        lines = 'Ich\nbin\n\nein\nTest'
        result = mp.file2paragraphs(lines.split('\n'))
        self.assertEqual(result[1], ['Ich', 'bin'])
        self.assertEqual(result[4], ['ein','Test'])

    def test_that_lines_are_joined_and_line_numbers_are_correct(self):
        content = '##bad\\\nexample\n\ndone'
        result = mp.file2paragraphs(content, join_lines=True)
        # paragraph after joined line starts with correct line number
        self.assertTrue(4 in result)
        self.assertFalse('\\' in '\n'.join(result[1]))

    ##############################################################
    # get_chapter_number_from_path
    def test_that_number_is_extracted_from_normal_file_name(self):
        self.assertEqual(2, mp.headings.extract_chapter_from_path("k02.md"))

    def test_that_number_is_extracted_from_relative_paths_and_absolute_paths(self):
        self.assertEqual(mp.headings.extract_chapter_from_path(os.path.join("k04",
            "k04.md")), 4)
        self.assertEqual(mp.headings.extract_chapter_from_path(os.path.join("c:", "k09",
        "k09.md")), 9)
        self.assertEqual(mp.headings.extract_chapter_from_path("k08/k08.md"), 8)

    def test_that_subchapter_files_work(self):
        self.assertEqual(mp.headings.extract_chapter_from_path('k0501.md'), 5)
        self.assertEqual(mp.headings.extract_chapter_from_path('k060201.md'), 6)

    def test_that_non_two_digit_numbers_raise_structural_error(self):
        with self.assertRaises(errors.StructuralError):
            mp.headings.extract_chapter_from_path("k9.md")
            mp.headings.extract_chapter_from_path("k029.md")

    def test_that_totally_wrong_file_names_raise_exception(self):
        with self.assertRaises(errors.StructuralError):
            mp.headings.extract_chapter_from_path("paper.md")
            mp.headings.extract_chapter_from_path("k11_old.md")

    def test_continued_lines_in_hashed_headings_recognized(self):
        headings = mp.headings.extract_headings_from_par(par(
                "### a heading\\\nwhich is too long\n\ncontent\n"))
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0].get_text(), 'a heading\nwhich is too long')

    def test_continued_lines_in_underlined_headings_work(self):
        headings = mp.headings.extract_headings_from_par(par(
                "a heading\\\nwhich is too long\n=====\n\ncontent\n"))
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0].get_text(), 'a heading\nwhich is too long')
        headings = mp.headings.extract_headings_from_par(par(
                "a heading\\\nwhich is too long\\\ntest\n-----\n\ncontent\n"))
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0].get_text(),
                'a heading\nwhich is too long\ntest')

    ############################################################################
    # tests for compute_position()

    def test_that_position_for_formula_at_beginning_of_document_is_correct(self):
        self.assertEqual(mp.compute_position(''), 1)
        self.assertEqual(mp.compute_position('', 1), 1)

    def test_that_pos_for_formula_on_first_line_correct(self):
        self.assertEqual(mp.compute_position('abc'), 4)

    def test_that_pos_after_line_berak_is_correct(self):
        self.assertEqual(mp.compute_position('a\nb\ncd'), 3)

    def test_that_offset_is_ignored_if_line_break_present(self):
        self.assertEqual(mp.compute_position('a\ncd', 99), 3)


    ############################################################################
    # tests of parse_environments

    def test_that_normal_text_does_not_contain_formulas(self):
        self.assertFalse(mp.parse_environments('This is \na bit of\n Text'))

    def test_that_escaped_dollars_are_ignored(self):
        self.assertFalse(mp.parse_environments(r'It has \$\$been\$\$ escaped'))

    def test_one_formula_per_line_works(self):
        formulas = mp.parse_environments('Here is $$\\tau$$.')
        self.assertEqual(len(list(formulas.keys())), 1)
        self.assertTrue(r'\tau' in formulas.values(), "expected \\tau, found: "
                + repr(formulas.values()))

    def test_that_two_formulas_per_line_are_recognized(self):
        formulas = mp.parse_environments('Here is $$\\tau$$ and $$\\pi$$.')
        self.assertEqual(len(formulas.keys()), 2, "expected two formulas, got " + repr(formulas))
        self.assertTrue('\\tau' in formulas.values())
        self.assertTrue('\\pi' in formulas.values())

    def test_that_two_formulas_per_line_have_correct_pos(self):
        formulas = mp.parse_environments('Here is $$\\tau$$ and $$\\pi$$.')
        self.assertTrue((1, 9) in formulas,
                "expected (1,9) as position, found " + repr(formulas.keys()))
        self.assertTrue((1, 22) in formulas,
                "expected (1,22) as position, found " + repr(formulas.keys()))

    def test_that_multiline_environments_have_correct_pos(self):
        formulas = mp.parse_environments('j$$a\nb$$,\n$$c$$')
        self.assertTrue((1, 2) in formulas.keys(), "expected (1, 2) to be in the " +
                "list of formulas, got " + repr(formulas))
        self.assertTrue((3, 1) in formulas.keys())
        # the same with the second environment slightly shiftet
        formulas = mp.parse_environments('j$$a\nb$$,\nchar$$c$$')
        self.assertTrue((1, 2) in formulas.keys(), "expected (1, 2) to be in the " +
                "list of formulas, got " + repr(formulas))
        self.assertTrue((3, 5) in formulas.keys())

    def test_that_three_environments_per_line_work(self):
        formulas = mp.parse_environments("u\nok $$first$$, then $$second$$ and in the end $$third$$.")
        self.assertTrue((2, 4) in formulas)
        self.assertTrue((2, 20) in formulas)
        self.assertTrue((2, 46) in formulas)

################################################################################

class TestParseFormulas(unittest.TestCase):
    def test_all_formula_types_recognized(self):
        formulas = parse_formulas('test $first$ and $$second$$')
        self.assertEqual(len(formulas.keys()), 2)
        self.assertTrue((1, 6) in formulas)
        self.assertTrue((1, 18) in formulas)

    def test_positions_of_formulas_are_exact(self):
        formulas = parse_formulas('test $first$ and $$second$$ $third$')
        self.assertEqual(len(formulas.keys()), 3)
        self.assertTrue((1, 6) in formulas)
        self.assertTrue((1, 18) in formulas)
        self.assertTrue((1, 29) in formulas, "expected (1,29) to exist, got " +
                repr(list(formulas.keys())))
        self.assertTrue('third' in formulas.values(), "'third' expected i" +
                "in formulas; found: " + repr(formulas.values()))

    def test_positions_of_formulas_are_correct_with_line_breaks(self):
        formulas = parse_formulas('test \n$first$ an\nd $$second$$ $third$')
        self.assertEqual(len(formulas.keys()), 3)
        self.assertTrue((2, 1) in formulas)
        self.assertTrue((3, 3) in formulas)
        self.assertTrue((3, 14) in formulas,
                "in formulas; found: " + repr(formulas.keys()))

    def test_that_formulas_are_in_correct_order(self):
        formulas = parse_formulas('test \n$first$ an\nd $$second$$ $third$')
        self.assertEqual(list(formulas.values()), ['first', 'second', 'third'])

    def test_that_multiple_paragraphs_are_parsed_correctly(self):
        pars = {1: ['hi', '$foo$ and $bar$'], 4: ['$$gamma$$ and $$beta$$']}
        formulas = mp.parse_formulas(pars)
        self.assertTrue((2, 1) in formulas)
        self.assertTrue((2, 11) in formulas)
        self.assertTrue((4, 1) in formulas)
        self.assertTrue((4, 15) in formulas)


################################################################################

# flatten a list
flatten = lambda x: list(itertools.chain.from_iterable(x))
seralize_doc = lambda x: '\n'.join(flatten(x.values()))

def parcdblk(string):
    """Get a paragraph dictionary with code block already removed."""
    return mp.rm_codeblocks(
            mp.file2paragraphs(string.split('\n')))

def par(string):
    """Transform a string (with paragraphs into a paragraph dictionary."""
    return mp.file2paragraphs(string.split('\n'))

def format_ln(line, lines):
    """Format error message, see usage for explanation."""
    return "expected paragraph starting at line {}, but doesn't exist; got: {}".format(
            line, ', '.join(map(str, lines)))


class TestCodeBlockRemoval(unittest.TestCase):
    def test_that_normal_paragraphs_are_untouched(self):
        data = parcdblk('ja\nso\nist\nes\n\n\nok\nhier\npassiert\nnichts')
        self.assertTrue(1 in data, format_ln(1, data.keys()))
        self.assertTrue(7 in data, format_ln(7, data.keys()))

    def test_that_tilde_code_blocks_at_beginning_and_end_are_removed(self):
        data = parcdblk('~~~~\nsome_code\nok\n~~~~\n\nla\nle\nlu\n\n~~~~\nmore_code\nb\n~~~~\n')
        self.assertFalse('some_code' in '\n'.join(flatten(data.values())))
        self.assertTrue(6 in data, format_ln(6, data.keys()))
        self.assertFalse('more_code' in '\n'.join(flatten(data.values())))

    def test_tilde_that_code_blocks_in_the_middle_work(self):
        data = parcdblk('heading\n======\n\ndum-\nmy\n\n~~~~\nremoved\n~~~~\n\ntest\ndone\n')
        self.assertFalse('removed' in '\n'.join(flatten(data.values())))
        # code block exists and is empty
        self.assertTrue(7 in data, format_ln(7, data.keys()))
        self.assertEqual(''.join(flatten(data[7])).strip(), '',
                "The code block in the middle should be empty; document is: " \
                    + repr(data))

    def test_backprime_tilde_code_blocks_at_beginning_and_end_are_removed(self):
        data = parcdblk('```\nsome_code\nok\n```\n\nla\nle\nlu\n\n```\nmore_code\nb\n```\n')
        self.assertFalse('some_code' in '\n'.join(flatten(data.values())))
        self.assertTrue(6 in data, format_ln(6, data.keys()))
        self.assertFalse('more_code' in '\n'.join(flatten(data.values())))

    def test_backprime_that_code_blocks_in_the_middle_work(self):
        data = parcdblk('heading\n======\n\ndum-\nmy\n\n```\nremoved\n```\n\ntest\ndone\n')
        self.assertFalse('removed' in '\n'.join(flatten(data.values())))
        # code block exists and is empty
        self.assertTrue(7 in data, format_ln(7, data.keys()))
        self.assertEqual(''.join(flatten(data[7])).strip(), '',
                "The code block in the middle should be empty; document is: " \
                    + repr(data))

    def test_that_backprime_blocks_with_prg_language_are_removed(self):
        data = parcdblk('```rust\nsome_code\nok\n```\n\nla\nle\nlu\n\n```\nmore_code\nb\n```\n')
        self.assertFalse('some_code' in '\n'.join(flatten(data.values())))
        self.assertTrue(6 in data, format_ln(6, data.keys()))
        self.assertFalse('more_code' in '\n'.join(flatten(data.values())))



    def test_that_indentedcode_blocks_at_beginning_and_end_are_removed(self):
        data = parcdblk('\tsome_code\n\tok\n\nla\nle\nlu\n\n\tmore_code\n\tb\n')
        self.assertFalse('some_code' in '\n'.join(flatten(data.values())))
        self.assertTrue(4 in data, format_ln(6, data.keys()))
        self.assertFalse('more_code' in '\n'.join(flatten(data.values())))

    def test_that_indented_code_blocks_in_the_middle_work(self):
        data = parcdblk('heading\n======\n\ndum-\nmy\n\n\tremoved\n\ntest\ndone\n')
        self.assertFalse('removed' in '\n'.join(flatten(data.values())),
                "code block should have been removed; document: " + repr(data))
        # code block exists and is empty
        self.assertTrue(7 in data, format_ln(7, data.keys()))
        self.assertEqual(''.join(flatten(data[7])).strip(), '',
                "The code block in the middle should be empty; document is: " \
                    + repr(data))

    def test_that_indented_block_not_removed_if_itemize_before(self):
        four_spaces = parcdblk('- some\n- list\n- items\n\n    this is part\n    of the last list item\n')
        self.assertTrue('this is part' in seralize_doc(four_spaces),
                "'this is part' was not found in document: " + repr(seralize_doc(four_spaces)))
        self.assertTrue('of the last' in seralize_doc(four_spaces))
        three_spaces = parcdblk('- some\n- list\n- items\n\n   this is part\n   of the last list item\n')
        self.assertTrue('this is part' in seralize_doc(four_spaces) and
                'of the last' in seralize_doc(four_spaces))

        one_tab = parcdblk('- some\n- list\n- items\n\n\tthis is part\n\tof the last list item\n')
        self.assertTrue('this is part' in seralize_doc(one_tab) and
                'of the last' in seralize_doc(one_tab))

    def test_that_even_indented_tilde_blocks_are_removed(self):
        data = parcdblk('-  blah\n\n    ~~~~\n    ok, here we go\n    ~~~~\n\njup')
        self.assertFalse('ok, here' in seralize_doc(data))
        self.assertTrue(7 in data)

    def test_multi_paragraph_code_works(self):
        data = parcdblk('dummy\n\n~~~~\n1\n2\n3\n\n4\n5\n6\n~~~~\n\nflup\n')
        self.assertEqual(data[1], ['dummy'])
        self.assertTrue(3 in data)
        self.assertTrue(8 in data)
        self.assertTrue(all(l == '' for l in data[8]))

    def test_inine_in_a_paragraph_on_its_own_works(self):
        data = parcdblk('test\n\n`<IP>:<port>`\n\nend\n')
        for start in (1, 3, 5):
            self.assertTrue(start in data,
                "Expected {} in data, but not found.  Got: ".format(start, data))
        self.assertEqual(data[3][0].strip(), '')

