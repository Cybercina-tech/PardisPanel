"""Media paths that keep one account's uploads out of another's namespace."""
from django.utils.deconstruct import deconstructible


@deconstructible
class AccountUploadPath:
    """``upload_to`` callable that prefixes the owning account's id.

    Without it two customers who both upload ``logo.png`` land in the same
    directory and the storage backend silently suffixes one of them; worse, a
    guessable path lets anyone with the media URL read another desk's branding.
    Rows written before this existed keep their stored path — only new uploads
    move under ``accounts/<id>/``.
    """

    def __init__(self, prefix):
        self.prefix = prefix.strip("/")

    def __call__(self, instance, filename):
        account_id = getattr(instance, "account_id", None) or "shared"
        return "accounts/%s/%s/%s" % (account_id, self.prefix, filename)

    def __eq__(self, other):
        return isinstance(other, AccountUploadPath) and other.prefix == self.prefix

    def __hash__(self):
        return hash((type(self), self.prefix))
