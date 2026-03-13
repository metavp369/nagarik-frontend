"""
Rate Limiter — IP-based request throttling using slowapi.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
