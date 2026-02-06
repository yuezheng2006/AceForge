# Shared exception for cooperative cancellation of generation jobs.
# Used by api/generate (catches) and cdmf_pipeline_ace_step (raises) to avoid circular imports.


class GenerationCancelled(Exception):
    """Raised when a running generation is cancelled by the user via the cancel API."""
