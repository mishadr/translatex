# translatex

translatex is a simple tool for automatic translation of your LaTeX document.
It is based on [TexSoup](https://texsoup.alvinwan.com/) for parsing LaTeX and
[googletrans](https://pypi.org/project/googletrans/) for translation.

### Features

* Handles whole LaTeX documents as well as correct LaTeX texts.
* All LaTeX formatting including math formulas are be preserved as is.
* Handles titles, captions, footnotes.

## Getting started

Just clone a git repository:
```
$ git clone https://github.com/mishadr/translatex.git
$ cd translatex
```

### Requirements

* python >= 3.5
* [googletrans](https://pypi.org/project/googletrans/) == 3.1.0a0  (don't use 3.0.0 or 4.0.0rc1)
* [TexSoup](https://github.com/alvinwan/TexSoup) (works for 0.3.1)

### Usage

From `src` folder run

`$ python translatex.py -i '../data/conference_101719.tex' -o '../data/final.tex'`

This translates IEEE conference template and saves the result to `data/final.tex`.


## Comments

The main idea is to stash LaTeX commands such that to translate the rest of the document as plain text.

The final document needs manual revision since there could be many flaws in translation:
* TexSoup still has parsing [issues](https://github.com/alvinwan/TexSoup/issues);
* googletranslate is not ideal, especially in terminology;
* correct parsing and/or translation sometimes strongly depend on text semantics which is out of scope of translatex.
