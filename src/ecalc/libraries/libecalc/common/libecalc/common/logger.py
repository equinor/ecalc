import logging

"""
We provide a logger object for the library with the logger named 'libecalc'
It is the user of the library's responsibility to configure it:

https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library

TLDR;
A library do not and shall NOT configure a logger itself. It reserves a logging namespace called "libecalc",
that applications that use the library will need to configure themselves. Therefore we explicitly add a NullHandler
to make sure that the logger is not activated.
"""
logger = logging.getLogger(
    "libecalc",
)
logger.addHandler(logging.NullHandler())
