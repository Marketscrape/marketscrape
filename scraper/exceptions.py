class NoProductsFound(Exception):
    """Raised when no products matching the given criteria are found."""
    pass

class InvalidSimilarityThreshold(Exception):
    """Raised when an invalid similarity threshold is provided."""
    pass

class InvalidDataFormat(Exception):
    """Raised when the data format is invalid or does not match the expected format."""
    pass
