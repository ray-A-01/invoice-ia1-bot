"""Defines modules to interact with the various QuickBooks objects.

Modules
--------
*invoices
"""

__all__ = ['invoices']
__author__ = 'Aniruddha Ray'
__version__ = '1.0.0'

import logging

logging.getLogger('urllib3.connectionpool').propagate = False
logging.getLogger(__name__).addHandler(logging.NullHandler())
