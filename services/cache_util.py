from django.core.cache import cache
from django.utils.text import slugify


class CacheUtil:
    @staticmethod
    def get_cache_value_or_default(
        cache_key, value_callback=None, require_fresh_data=False, timeout=None
    ):
        cached_data = None
        error_details = None

        if not require_fresh_data:
            cached_data = cache.get(cache_key)

        if not cached_data:
            if value_callback is not None:
                cached_data, error_details = value_callback()
                if cached_data:
                    CacheUtil.set_cache_value(cache_key, cached_data, timeout=timeout)

        return cached_data, error_details

    @staticmethod
    def set_cache_value(cache_key, cached_data, timeout=None):
        if not timeout:
            timeout = 60 * 60 * 24 * 7
        cache.set(cache_key, cached_data, timeout=timeout)

    @staticmethod
    def clear_cache(*cache_keys):
        cache.delete_many(list(cache_keys))
        # for key in list(cache_keys):
        #     cache.set(key, None, timeout=0)

    @staticmethod
    def generate_cache_key(*args):
        if not args:
            args = []

        return ":".join(list(slugify(arg) for arg in args))
