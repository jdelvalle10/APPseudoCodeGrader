"""Desktop GUI: live webcam preview -> capture -> grade AP CSP pseudocode."""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from grader import GradeResult, grade_image

PREVIEW_W = 640


class App(tk.Tk):
    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.title("AP CSP Pseudocode Grader")
        self.cap = cv2.VideoCapture(camera_index)
        if self.cap.isOpened():  # ask for a high-res stream; handwriting needs pixels
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.frame = None
        self.captured: Image.Image | None = None
        self.busy = False

        left = ttk.Frame(self, padding=8); left.grid(row=0, column=0, sticky="n")
        right = ttk.Frame(self, padding=8); right.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1); self.rowconfigure(0, weight=1)

        self.view = ttk.Label(left); self.view.pack()
        bar = ttk.Frame(left); bar.pack(pady=6)
        self.btn_cap = ttk.Button(bar, text="Capture", command=self.capture); self.btn_cap.pack(side="left", padx=3)
        self.btn_grade = ttk.Button(bar, text="Grade", command=self.grade, state="disabled"); self.btn_grade.pack(side="left", padx=3)
        ttk.Button(bar, text="Retake", command=self.retake).pack(side="left", padx=3)
        ttk.Button(bar, text="Open image…", command=self.open_file).pack(side="left", padx=3)
        self.status = ttk.Label(left, text="Hold the page flat, well lit, filling the frame.", wraplength=PREVIEW_W)
        self.status.pack(anchor="w")

        self.score = ttk.Label(right, text="—", font=("TkDefaultFont", 36, "bold")); self.score.pack(anchor="w")
        self.breakdown = ttk.Label(right, text="", justify="left"); self.breakdown.pack(anchor="w")
        self.text = tk.Text(right, width=70, height=30, wrap="word"); self.text.pack(fill="both", expand=True, pady=6)

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.tick()

    # --- camera -----------------------------------------------------------
    def tick(self):
        if self.captured is None and self.cap.isOpened():
            ok, frame = self.cap.read()
            if ok:
                self.frame = frame
                self.show(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            else:
                self.status.config(text="Camera returned no frame.")
        elif not self.cap.isOpened() and self.captured is None:
            self.status.config(text="No camera found. Use “Open image…” instead.")
        self.after(33, self.tick)

    def show(self, img: Image.Image):
        h = round(img.height * PREVIEW_W / img.width)
        self.photo = ImageTk.PhotoImage(img.resize((PREVIEW_W, h)))
        self.view.config(image=self.photo)

    def capture(self):
        if self.frame is None:
            return
        self.captured = Image.fromarray(cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB))
        self.show(self.captured)
        self.btn_grade.config(state="normal")
        self.status.config(text="Captured. Check that the text is sharp, then press Grade.")

    def retake(self):
        self.captured = None
        self.btn_grade.config(state="disabled")
        self.status.config(text="Live preview.")

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if path:
            self.captured = Image.open(path)
            self.show(self.captured)
            self.btn_grade.config(state="normal")
            self.status.config(text=os.path.basename(path))

    # --- grading ----------------------------------------------------------
    def grade(self):
        if self.busy or self.captured is None:
            return
        if not os.environ.get("ANTHROPIC_API_KEY"):
            messagebox.showerror("Missing API key", "Set the ANTHROPIC_API_KEY environment variable and restart.")
            return
        self.busy = True
        self.btn_grade.config(state="disabled"); self.btn_cap.config(state="disabled")
        self.status.config(text="Grading…")
        img = self.captured
        threading.Thread(target=self._work, args=(img,), daemon=True).start()

    def _work(self, img):
        try:
            result = grade_image(img)
            self.after(0, self.render, result)
        except Exception as e:  # network, auth, malformed response
            self.after(0, self.fail, e)

    def fail(self, err):
        self.busy = False
        self.btn_grade.config(state="normal"); self.btn_cap.config(state="normal")
        self.status.config(text="Error.")
        messagebox.showerror("Grading failed", f"{type(err).__name__}: {err}")

    def render(self, r: GradeResult):
        self.busy = False
        self.btn_grade.config(state="normal"); self.btn_cap.config(state="normal")
        self.text.delete("1.0", "end")
        if not r.readable:
            self.score.config(text="—")
            self.breakdown.config(text="Could not read the page.")
            self.text.insert("end", r.retake_advice)
            self.status.config(text="Retake the photo.")
            return
        self.score.config(text=f"{r.total} / 100")
        self.breakdown.config(text=(
            f"Does what's requested: {r.requested}/50\n"
            f"Pseudocode correctness: {r.correctness}/25\n"
            f"Correct algorithm: {r.algorithm}/25\n"
            f"Model confidence: {r.confidence or 'n/a'}"))
        t = self.text
        t.insert("end", f"PROBLEM (as read)\n{r.problem_text}\n\n")
        t.insert("end", f"STUDENT PSEUDOCODE (as read)\n{r.student_pseudocode}\n\n")
        t.insert("end", f"EXPECTED ALGORITHM\n{r.expected_algorithm}\n\n")
        t.insert("end", f"REQUESTED BEHAVIOR\n{r.feedback['requested']}\n\n")
        t.insert("end", f"CORRECTNESS\n{r.feedback['correctness']}\n\n")
        t.insert("end", f"ALGORITHM\n{r.feedback['algorithm']}\n\n")
        t.insert("end", f"TRACES\n{r.trace_notes}\n")
        self.status.config(text="Done. Verify the transcription above before trusting the grade.")

    def close(self):
        self.cap.release()
        self.destroy()


if __name__ == "__main__":
    App(int(os.environ.get("CAMERA_INDEX", "0"))).mainloop()
