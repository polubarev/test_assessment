import logging

# Ensure a default null handler for library consumers; app config will override
logging.getLogger(__name__).addHandler(logging.NullHandler())


