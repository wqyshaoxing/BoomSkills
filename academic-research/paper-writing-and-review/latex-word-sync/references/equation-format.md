# Equation fidelity contract

Use this reference whenever a LaTeX--Word synchronization contains inline or display mathematics.

## Preserve notation semantics

Before conversion, make a notation map from the LaTeX source and the author’s stated convention. Preserve the source exactly unless the author changes it:

- Scalars are normally italic, such as x and d_k.
- Vectors and matrices retain their case and boldness, such as \mathbf{x}, \mathbf{Q}, and \mathbf{W}.
- Operators and labels remain upright, such as \operatorname{softmax} and \mathrm{T}.
- Preserve superscripts, subscripts, primes, accents, fractions, roots, delimiters, and sets such as \mathbb{R}.

Never infer that an uppercase letter can be lowercased, or that a bold matrix can become a plain variable, merely because a PDF extractor emitted flattened text. Recover the intended notation from the LaTeX source when it exists; otherwise confirm the notation against the source PDF and mark any remaining ambiguity for the author.

## Build editable Word equations

Use OMML, not equation screenshots, Unicode approximations, or prose-font runs. Convert LaTeX math commands to the corresponding OMML structure so that bold vectors/matrices, scripts, fractions, roots, delimiters, and alignment remain editable.

When the author explicitly selects Times New Roman for the manuscript, use it for surrounding editable text and use it in OMML only through a tested, schema-valid override. Retain OMML style properties that distinguish bold vectors/matrices and upright operators; preserve Word’s native mathematical typography when forcing a prose font would damage the equation.

For a display equation:

1. Center the formula within the current one- or two-column text width.
2. If it has a number, position the number independently at the right edge with a center/right tab or the target template’s approved equation layout. The number must not shift the formula off center.
3. For multi-line displays, retain an aligned relation column, such as = or \leq, while keeping the display block centered.
4. Recheck the geometry after switching between a single-column and two-column section.

## Remove accidental Word markers

If Word displays black squares in the editing margin, inspect the generated DOCX for paragraph or style properties that were not requested:

- w:numPr can create unintended list behavior.
- w:keepNext and w:keepLines create visible pagination markers when formatting marks are enabled.

Remove unrequested properties from both direct paragraph formatting and inherited styles. Preserve figure/caption pagination by sizing or placing the object correctly, rather than by leaving unexpected list or pagination flags in ordinary manuscript text. This does not prohibit an author-approved pagination setting; record any retained setting in the manifest.

## Equation QA

For every changed display equation, compare the LaTeX source, OMML XML, and rendered Word page. Reject a conversion if any of the following occur:

- A matrix/vector loses case or boldness.
- An operator, transpose, subscript, superscript, or delimiter changes meaning.
- The equation is left aligned or its number changes its center position.
- A multi-line equation is visually misaligned.
- A black margin square, stray bullet, or list marker appears without author approval.
