"""Application layer: use-cases and the pipeline orchestrator.

Defines the stage Protocols (ImageValidator, Preprocessor, Rectifier,
ScaleCalibrator, EdgeDetector, FacadeSegmenter, Vectorizer,
GeometryRegularizer, DrawingExporter) that `app.infrastructure` implements
and that `app.composition` wires together. This layer depends only on
`app.domain` and on the Protocols it defines here — never on concrete
third-party libraries.
"""
