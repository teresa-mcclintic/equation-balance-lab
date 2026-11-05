# Equation Balance Lab

An interactive Streamlit app for Prealgebra students.

## Student workflow

1. Enter a first and last name.
2. Choose Level 1 (one-step), Level 2 (two-step), or Level 3 (multi-step).
3. Practice by choosing an inverse operation, applying it to **both sides**, and **writing the resulting equation**.
4. Verify the solution by substitution.
5. Take a separate five-question mastery check for each level.

Mastery requires **4 of 5 problems correct on the first attempt**. Students can correct their work to finish a problem, but a problem completed with corrections does not earn a mastery point. Hints are available in practice only.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

In [Streamlit Community Cloud](https://share.streamlit.io/), select this repository, branch `main`, and entrypoint `app.py`.

## Current limitations

- Names are labels, not authenticated student accounts.
- Student progress and mastery scores live in the active Streamlit session only. **They do not persist across browser sessions** or appear in a teacher dashboard.
- Before classroom reporting, add a durable database, duplicate-name safeguards, restricted teacher access, and downloadable progress reports.
- The level balance scale illustrates equal expressions but is not yet draggable.

## Instructional routine

**Choose an inverse operation → apply it to both sides → write the next equivalent equation → repeat and verify.**
