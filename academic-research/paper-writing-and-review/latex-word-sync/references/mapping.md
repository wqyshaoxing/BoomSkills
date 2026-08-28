# Synchronization map

The map is an evidence record, not a request to make two formats visually identical. It answers: which editable object on one side represents which object on the other side, which side is authoritative, and whether its content or format changed.

## Stable anchors

Use these anchors in preference order:

1. A LaTeX source path plus section/subsection title mapped to a Word paragraph ordinal plus heading text.
2. A LaTeX table input path mapped to a Word table ordinal and caption.
3. An `includegraphics` path mapped to a Word drawing ordinal and caption.
4. A LaTeX equation label or equation ordinal mapped to a Word editable OMML equation and displayed number.
5. A bibliography key/entry order mapped to a Word bibliography number and its in-text field targets.

Never match content purely by position when a caption, heading, label, or file path exists. If a target cannot be mapped unambiguously, report it and ask for a choice rather than making a broad replacement.

## Change selection

The manifest hashes every included source file and referenced asset. On a later run, use its delta:

- A changed section file permits changing only its mapped Word paragraph range.
- A changed table file permits changing only its mapped Word table and caption.
- A changed figure asset permits changing only its mapped Word drawing, preserving size/crop unless instructed otherwise.
- A changed bibliography permits updating affected citation fields and bibliography entries, then validating all targets.
- A changed DOCX layout with no source-content change permits presentation-only repair; compare visible text and OMML before and after.

If the source and target changed independently at the same anchor, do not choose a winner silently. Present the conflict and request direction.

## Content comparison

Text extraction alone is insufficient for equations, citations, figures, and table hierarchy. Compare normalized prose only as a diagnostic. The decisive checks are mapped-object counts, numeric cell sequences, equation labels/numbers, caption anchors, asset hashes, reference order, and rendered pages.
