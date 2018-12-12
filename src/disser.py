# coding=utf-8
from enum import IntEnum

from mtranslate.core import translate


# Latex line types
class LatexType(IntEnum):
    ordinary, newpar, comment, header, special, other = range(6)


def is_header(line):
    for header in ['\part', '\chapter', '\section', '\subsection', '\subsubsection', '\paragraph', '\subparagraph']:
        if line.startswith(header):
            return True
    return False


def preprocess_english_latex(text):
    """
    Split into lines and mark each line with a latex type.

    :param text:
    :return:
    """
    content = []  # list of pairs (LatexType, string)
    last_type = LatexType.newpar

    for line_orig in text.splitlines():
        line = line_orig.strip()

        if len(line) == 0:
            # TODO new paragraph
            last_type = LatexType.newpar

        elif line.startswith('%'):  # comment
            last_type = LatexType.comment

        elif line.startswith('\\'):  # header or special command
            if is_header(line):
                last_type = LatexType.header
            else:
                last_type = LatexType.special

        elif line[0].isalnum():  # works for English chars only
            last_type = LatexType.ordinary

        else:
            print 'unknown type:', line_orig
            last_type = LatexType.other

        # add original line
        content.append((last_type, unicode(line_orig, encoding='utf-8')))

    # for t, l in content:
    #     print '-------'
    #     print t, l
    return content


def translate_en_ru(content, leave_orig=True):
    """
    Translate text by paragraphs, leaving original parts commented if specified.

    :param content: list of pairs (LatexType, string)
    :param leave_orig: whether to leave original parts of text (will be commented)
    :return:
    """
    result = []
    line_sep = u'\n'
    par_sep = u'\n\n'
    tran_sep = u'\n'  # separator between translation and original
    orig_comment = u'%'
    par_tran = []  # translated part of paragraph
    par_orig = []  # original part of paragraph

    def flush_par(par_tran, par_orig):
        # print par_tran
        # for p in par_tran:
        #     print p
        # par = str(par_tran)
        par = line_sep.join(par_tran)
        if leave_orig:
            par += tran_sep + line_sep.join(par_orig)
        result.append(par)

    for t, line_orig in content:
        if t is LatexType.newpar:  # flush current paragraph
            # TODO do not flush if last type was newpar
            if len(par_orig) > 0:
                flush_par(par_tran, par_orig)
                par_tran = []
                par_orig = []

        elif t is LatexType.comment:  # Comments are ignored for translation
            par_orig.append(orig_comment + line_orig)

        elif t is LatexType.ordinary:  # Ordinary line we translate as is
            # TODO translate lines altogether replacing \n's with spaces and removing special commands
            # TODO cut math and not translate it?
            line_tran = translate(line_orig, "ru", "en")
            # line_tran = u"переведенная строка [%s]" % line_orig
            # post-process RU
            line_tran = postprocess_russian_latex(line_tran)
            par_tran.append(line_tran)
            par_orig.append(orig_comment + line_orig)

        elif t is LatexType.header:  # Try to parse and translate header
            # TODO Try to parse and translate header
            # Leave as is
            line_tran = line_orig
            par_tran.append(line_tran)
            par_orig.append(orig_comment + line_orig)
            flush_par(par_tran, par_orig)
            par_tran = []
            par_orig = []

        elif t is LatexType.special:  # Leave as is
            # TODO what if math with slash: \[
            line_tran = line_orig
            par_tran.append(line_tran)
            par_orig.append(orig_comment + line_orig)

        elif t is LatexType.other:  # Leave as is
            line_tran = line_orig
            par_tran.append(line_tran)
            par_orig.append(orig_comment + line_orig)

    flush_par(par_tran, par_orig)

    # for line in result:
    #     print '----new paragraph----'
    #     print line
    return par_sep.join(result)


def postprocess_russian_latex(text):

    # replace ~\cite
    text = text.replace(' ~ \\ cite ', '~\\cite')

    # math formulas: prevent floating '\' before command
    text = text.replace('\\ ', '\\')
    # math formulas: prevent floating '_'
    text = text.replace('_ ', '_')
    text = text.replace(' _', '_')

    # sometimes quotes are replaced
    text = text.replace(u'«', '``')
    text = text.replace(u'»', '\'\'')

    text = text.replace(u'т. Д.', u'т.\\,д.')
    text = text.replace(u'т. П.', u'т.\\,п.')

    # TODO if not in math mode: short '-' replace with long '---'

    return text


def main():
    source_path = '../data/source.txt'
    final_path = '../data/final.txt'

    # read source text
    source_text = ""
    with open(source_path, 'r') as f:
        source_text = f.read()

    # preprocess EN latex text
    text = preprocess_english_latex(source_text)

    # translate
    text = translate_en_ru(text)

    # save final text
    with open(final_path, 'w') as f:
        f.write(text.encode('utf-8'))


if __name__ == '__main__':
    main()
