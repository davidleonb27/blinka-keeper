"""Requests from one IP arrive together: the shared counter must neither fail nor lose a hit."""

import threading

from sqlalchemy import select

from custodio.db.models import RateCounterRow
from custodio.services import rate_limits
from custodio.services.context import Runtime

WRITERS = 8
HITS_PER_WRITER = 5
WAIT_SECONDS = 30


def test_simultaneous_hits_on_a_new_window_all_count_and_none_fails(runtime: Runtime) -> None:
    runtime.database.ensure_migrated()
    start = threading.Barrier(WRITERS)
    errors: list[BaseException] = []

    def writer() -> None:
        try:
            start.wait(WAIT_SECONDS)
            for _ in range(HITS_PER_WRITER):
                rate_limits._hit(runtime, "test:race", WRITERS * HITS_PER_WRITER, rate_limits.MINUTE)
        except BaseException as error:  # the thread's failure must reach the test
            errors.append(error)

    threads = [threading.Thread(target=writer) for _ in range(WRITERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(WAIT_SECONDS)

    assert errors == []
    with runtime.database.session() as session:
        counter = session.scalars(select(RateCounterRow).where(RateCounterRow.key == "test:race")).one()
    assert counter.count == WRITERS * HITS_PER_WRITER
