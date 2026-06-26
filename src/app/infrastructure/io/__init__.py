"""Pillow-based image ingestion: defensive decoding and validation before
anything else in the pipeline runs. Kept separate from `vision/` (which is
reserved for opencv-based CV operations — rectify, edge detection) because
this sub-package's job is file-safety, not computer vision.
"""