# Dependencies and tool selection

The mapping script needs only a Python 3.9+ standard-library runtime. Resolve the interpreter at runtime and do not hard-code its path.

- Initial semantic conversion: Pandoc. Use a reference DOCX with `--reference-doc`; it is a draft generator, not a layout verifier.
- DOCX inspection and precise repairs: Python with `lxml` and `python-docx`; edit OOXML only when `python-docx` cannot preserve the required fields, OMML, or table rules.
- DOCX render and visual verification: use any available office renderer that preserves Word layout, then inspect rendered pages.
- LaTeX build: use an available TeX engine; use XeLaTeX when the project uses `fontspec`, Unicode, or system fonts.
- PDF visual verification: use a PDF renderer such as Poppler to make page images for inspection.
- Citation data: keep BibTeX and Word citation-field data as independent structured data. Do not infer bibliography keys from formatted reference prose.

At the start of a task, detect the available programs and record the selected pipeline in the manifest's `toolchain` note. Do not install or modify a global dependency unless the user authorizes it.
