# translatex

**translatex** is a simple tool for automatic translation of your TeX document.
It is based on [pylatexenc](https://github.com/phfaist/pylatexenc) for parsing LaTeX and
[translatepy](https://github.com/Animenosekai/translate) for automatic translation.

### Features

* Handles a whole TeX document, translating text inside it.
* All TeX formatting including math formulas is preserved as is.

## Getting started

Just clone a git repository:
```
$ git clone https://github.com/mishadr/translatex.git
$ cd translatex
```

### Requirements

* python >= 3.8
* [pylatexenc](https://github.com/phfaist/pylatexenc) == 2.10
* [translatepy](https://github.com/Animenosekai/translate) == 2.3

### Usage

From `src` folder run

`$ python translatex.py -i '../data/example.tex' -o '../data/output.tex' -s en -d ru`

This translates an example latex file from English to Russian (by default) and saves the result .tex file to `data/output.tex`.
The final document needs manual revision since there could be many flaws in translation:
* automatic translation is not ideal, especially in terminology;
* correct parsing and/or translation sometimes strongly depend on text semantics which is out of scope of translatex.


### How it works

1. Parse latex into a nodes tree
2. Filter which nodes contain text to be translated
3. Mask non-translatable nodes
4. Form chunks of text as requests to a translator
5. Get response from translator and parse it to detect which text belongs to which node
6. Update translatable nodes and return a new latex code

## Comments

Potential errors.
* Parser may fail if a latex document is incorrect 
* Yandex translator API may change over time so requests can be banned, translation quality and stability can change
* If the result document is not compiled, some additional packages might be needed (e.g. `\usepackage[T2A]{fontenc}`)

In case of questions feel free to contact me.