# coding=utf-8
import argparse
import re

from enum import IntEnum

from mtranslate.core import translate


# Latex line types
class LatexType(IntEnum):
    ordinary, newpar, comment, header, special, other = range(6)


MATH_STUB = '***'  # used to replace math formulas before auto-translation

tex_environment = [("\\begin{enumerate}", "\\end{enumerate}")]

# # # TODO see parser https://github.com/alvinwan/texsoup


class TextWithStubs(object):
    def __init__(self, text, as_is=False):
        """

        :param text: raw tex text
        :param as_is: whether to leave piece as is (not translate)
        """
        self.text = text
        self.as_is = as_is

        print '"%s"' % text

        self.decomposed = False
        pass

    def decompose(self):
        """
        Parse raw text, putting labels where pieces need to be processed separately. These pieces can be immutable tex
        commands or TWS's themselves. They are replaced with stubs while translating.

        :return:
        """
        self.decomposed = True
        raise NotImplementedError()

    def compose(self):
        """
        Assemble final text from text with stubs. A full dictionary of stubs should be present.

        :return:
        """
        assert self.decomposed
        raise NotImplementedError()

    def translate(self):
        """
        Translate text with stubs. If a stub corresponds to TWS, it is translated recursively and the results goes
        instead of the stub.

        :return:
        """
        assert self.decomposed
        raise NotImplementedError()


def next_command(text, from_index=0):
    assert isinstance(text, str)

    m = re.match("[\$%]", text)
    i = text.find('\\', __start=from_index)
    j = text.find('%', __start=from_index)
    k = text.find('$', __start=from_index)
    index = min(x for x in [i, j, k])

    # define command
    if index == i:
        pass
    elif index == j:
        pass
    else:
        pass


commands = {
    "": "",
}


def is_leave_as_is(special, text, index):
    assert isinstance(special, str)
    result = False
    if special.startswith('%'):  # comment
        return True
    if special[0] == '\\' and special[1:].isalpha():  # single command, e.g. \newline, \item
        return True



class Translator(object):

    def __init__(self, latex_src):
        self.latex_src = latex_src
        self.latex_final = ""

        self.line_sep = u'\n'
        self.par_sep = u'\n\n'
        self.tran_sep = u'\n'  # separator between translation and original
        self.orig_comment = u'%'

    def parse(self, text):
        """
        Split raw tex text into pieces (TWS's) which should be translated as a whole.

        :param text:
        :return: list of TWS's with corresponding separators
        """
        assert isinstance(text, str)

        tws_list = []
        separator_list = []

        specials_list = re.findall("\\\[\W]|\\\[a-zA-Z]+|%.+|\$[^$]+\$|\$\$[^$]+\$\$", text)

        last_index = -1
        for special in specials_list:
            index = text.find(special, last_index+1)
            if is_leave_as_is(special, text, index):
                pass


            if index > 0:
                tws_list.append(TextWithStubs(text[last_index:index]))
            last_index = index
        if last_index > -1:
            tws_list.append(TextWithStubs(text[last_index:]))


        # TODO cut into TWS's
        # assert len(separator_list) == len(tws_list)-1
        return tws_list, separator_list

    def translate(self, lang_from='en', lang_to='ru', leave_orig=False):
        # TODO determine where to add orig pieces. say, where we meet \n\n. if their number is same
        #  in final text we could insert them after the translation

        # parse text into list of TWS's
        text = self.latex_src
        tws_list, separator_list = self.parse(text)

        # translate each TWS separately
        translated_list = []
        for tws in tws_list:
            tws_translated = tws.translate()
            translated_list.append(tws_translated)

        # concatenate translated pieces
        # TODO alternate tws_list and separator_list
        text = "".join(translated_list)

        self.latex_final = text
        return text


def is_header(line):
    for header in ['\\part', '\\chapter', '\\section', '\\subsection', '\\subsubsection', '\\paragraph', '\\subparagraph']:
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


def cut_math(line):
    """
    Replaces all math formulas $...$ and \[ ... \] with math_stubs.

    :param line:
    :param math_stub:
    :return:
    """
    # TODO add \[ ... \] support
    math_list = []
    result = ""

    math_mode = False

    print line
    pieces = re.split(r"(\$)", line)
    for p in pieces:
        if p == '$':
            math_mode = not math_mode
            continue

        if math_mode:
            math_list.append("$%s$" % p)
            result += MATH_STUB
        else:
            result += p

    # print result
    # print math_list
    return result, math_list


def embed_math(text, math_list):
    """

    :param text:
    :param math_list:
    :return:
    """
    # FIXME what if len(math_list) != number of stubs?
    for math in math_list:
        text = text.replace(MATH_STUB, math, 1)

    # print text
    return text


def translate_en_ru(content, leave_orig):
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

    def flush_par(par_tran, par_orig, do_translation):
        if do_translation:  # translate whole paragraph
            line = u' '.join(par_tran)

            line_wo_math, math_list = cut_math(line)
            translated = translate(line_wo_math, "ru", "en")
            translated = postprocess_russian(translated)

            line_w_math = embed_math(translated, math_list)

            par = postprocess_russian_latex(line_w_math)
        else:
            par = line_sep.join(par_tran)

        if leave_orig:
            par += tran_sep + line_sep.join(par_orig)
        result.append(par)

    for t, line_orig in content:
        if t is LatexType.newpar:  # flush current paragraph
            # TODO do not flush if last type was newpar
            if len(par_orig) > 0:
                flush_par(par_tran, par_orig, True)
                par_tran = []
                par_orig = []

        elif t is LatexType.comment:  # Comments are ignored for translation
            par_orig.append(orig_comment + line_orig)

        elif t is LatexType.ordinary:  # Ordinary line we translate as is
            par_tran.append(line_orig.strip())
            par_orig.append(orig_comment + line_orig)

        elif t is LatexType.header:  # Try to parse and translate header
            # TODO Try to parse and translate header
            # Leave as is
            line_tran = line_orig
            par_tran.append(line_tran)
            par_orig.append(orig_comment + line_orig)
            flush_par(par_tran, par_orig, False)
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

    flush_par(par_tran, par_orig, True)

    # for line in result:
    #     print '----new paragraph----'
    #     print line
    return par_sep.join(result)


def postprocess_russian(text):
    """
    Process russian text disregarding latex constructions
    :param text:
    :return:
    """

    # sometimes quotes are replaced
    text = text.replace(u'«', '``')
    text = text.replace(u'»', '\'\'')

    text = text.replace(u'т. Д.', u'т.\\,д.')
    text = text.replace(u'т. П.', u'т.\\,п.')

    # not in math mode: short '-' replace with long '---'
    text = text.replace(u' - ', u'~--- ')  # shouldn't be used in cases like $x$-abcd

    return text


def postprocess_russian_latex(text):
    """
    Process russian text regarding latex constructions

    :param text:
    :return:
    """

    # replace ~\cite
    text = text.replace('\\ cite ', '\\cite')
    text = text.replace(' ~ \\cite', '~\\cite')

    return text


def main():
    # parser = argparse.ArgumentParser(description='Latex document translation via google.translate.')
    # parser.add_argument('-i', '--input', required=True, help='input .tex file path')
    # parser.add_argument('-o', '--output', default='output.tex', help='output .tex file path')
    # parser.add_argument('--leave-original', action='store_true', help='output .tex file path')
    # # TODO options: lang choice; leave_comments;
    # # parser.add_argument('--input-lang', default='EN', help='language of input document')
    # # parser.add_argument('--output-lang', default='RU', help='language of output document')
    #
    # args = parser.parse_args()
    #
    # # Assuming all parameters are provided and take valid values.
    # source_path = args.input
    # final_path = args.output
    # leave_orig = args.leave_original

    source_path = '../data/source.txt'
    final_path = '../data/final.txt'
    leave_orig = True

    ###
    # TODO
    # * parse latex commands to exclude them from auto-translation. e.g. itemizing
    #   \begin{..} -> special processing for environments
    #   \textbf{}, \caption{}, \section{}, ... -> parse and translate
    #   \ref{}, \cite{}, ... -> leave as is
    #   \newline, ... -> leave as is
    #
    # * allow to specify custom translation of terms, e.g. graph model -> модель графа
    ###
    # read source text
    with open(source_path, 'r') as f:
        source_text = f.read()

    text = Translator(source_text).translate(leave_orig=True)

    # save final text
    with open(final_path, 'w') as f:
        f.write(text.encode('utf-8'))


if __name__ == '__main__':
    main()
    # text = "know $2+2=4$~\cite{somepaper}? % comment"
    # print re.findall("\\\[\W]|\\\[a-zA-Z]+|%.+|\$[^$]+\$|\$\$[^$]+\$\$", text)
