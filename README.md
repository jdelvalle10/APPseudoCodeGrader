# AP CSP Pseudocode Grader

Point a webcam at a page that has a programming problem and a student's AP CSP pseudocode solution. The app returns a 0-100 grade:

| Component | Points |
|---|---|
| Does what the problem requests | 50 |
| Pseudocode correctness (valid AP CSP syntax, no logic errors) | 25 |
| Uses the correct algorithm | 25 |

The total is summed in code (`grader.py`) from the three sub-scores, each clamped to its range. The model never picks the total.

## Run
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # required
python app.py                       # CAMERA_INDEX=1 python app.py for another camera
```
Tkinter ships with most Python installs (Linux: `sudo apt install python3-tk`). Use **Open image…** if no camera is available. `GRADER_MODEL` overrides the model.

## Test (offline, no API key)
`python -m pytest test_grader.py`

## Limits
- The page is read and graded by a vision model, so handwriting can be misread. Always check the "as read" transcription shown next to the grade.
- "Correct algorithm" is derived by the model from the problem text. Problems that allow several approaches are judged leniently.
- Grades are advisory. A human should review before they count.
- The page image is sent to the Anthropic API.
