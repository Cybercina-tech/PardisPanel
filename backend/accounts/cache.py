"""Account-aware cache key namespacing."""


def account_scoped_key(key, key_prefix, version):
    """Django ``KEY_FUNCTION`` that partitions the cache by account.

    Anonymous and cross-account contexts share one namespace, which is what
    throttle counters and other genuinely global entries want; a request running
    as a desk gets its own, so one customer's cached prices can never be served
    to another.
    """
    from .scoping import get_current_account_id

    return "%s:%s:%s:%s" % (key_prefix, version, get_current_account_id(), key)
