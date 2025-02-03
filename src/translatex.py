import argparse

from parser import translate


def main():
    parser = argparse.ArgumentParser(description='Latex document translation via google.translate.')
    parser.add_argument('-i', '--input', required=True, help='input Tex file path')
    parser.add_argument('-o', '--output', default='../data/output.tex', help='output Tex file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='print chunks')
    # parser.add_argument('--leave-original', action='store_true', help='output .tex file path')
    parser.add_argument('-s', '--source-lang', default='en', help='source language of input document')
    parser.add_argument('-d', '--dest-lang', default='ru', help='destination language')

    args = parser.parse_args()
    print(args)

    input_path = args.input
    output_path = args.output
    src_lang = args.source_lang
    dst_lang = args.dest_lang

    if src_lang == dst_lang:
        print("Source and destination languages are the same, nothing to do.")
        return

    translate(input_path, output_path, src_lang, dst_lang, verbose=args.verbose)


if __name__ == '__main__':
    main()
