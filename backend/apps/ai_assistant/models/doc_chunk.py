"""DocChunk — one searchable piece of a document, with its embedding.

The document index lives in the instance's own database: no separate vector database, and
it is backed up, restored and inspected like every other table. It is derived data —
`manage.py index_docs --reset` rebuilds it from the files.
"""
from django.db import models


class DocChunk(models.Model):
    collection = models.CharField(max_length=100)
    doc_id = models.CharField(max_length=500, help_text="The source document, workspace-relative")
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    content_hash = models.CharField(max_length=32)
    metadata = models.JSONField(default=dict, blank=True)
    embedding = models.BinaryField(help_text="Unit vector, little-endian float32 (mimic.knn.pack)")
    dim = models.PositiveIntegerField()
    embed_model = models.CharField(max_length=100)
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["collection", "doc_id", "chunk_index"],
                                    name="doc_chunk_unique_position"),
        ]
        indexes = [models.Index(fields=["collection", "doc_id"], name="doc_chunk_collection_doc")]
        ordering = ["collection", "doc_id", "chunk_index"]

    def __str__(self):
        return f"{self.doc_id} [{self.chunk_index}]"
