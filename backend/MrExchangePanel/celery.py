import os

from celery import Celery
from celery.signals import task_postrun, task_prerun

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MrExchangePanel.settings")

app = Celery("MrExchangePanel")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Scope token per in-flight task id; a prefork worker may run several at once.
_task_scope_tokens = {}


@task_prerun.connect
def _open_task_scope(task_id=None, task=None, **_):
    """Run every task across all accounts unless it narrows itself.

    A task has no request and therefore no account, and account scoping fails
    closed — so without this a beat sweep would silently process nothing. Tasks
    are trusted server-side code (never user input), and the ones that act for a
    single desk narrow themselves with ``act_as_account``.

    The token is parked on the task instance rather than a module global because
    a prefork worker can run tasks concurrently in threads.
    """
    from accounts.scoping import UNSCOPED, set_current_account_id

    _task_scope_tokens[task_id] = set_current_account_id(UNSCOPED)


@task_postrun.connect
def _close_task_scope(task_id=None, **_):
    from accounts.scoping import reset_current_account

    token = _task_scope_tokens.pop(task_id, None)
    if token is not None:
        try:
            reset_current_account(token)
        except ValueError:
            pass
