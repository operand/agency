import copy
import json
import multiprocessing
import time
import unittest
from typing import List

from agency.agent import Agent, _QueueProtocol
from agency.schema import Message
from agency.space import Space

multiprocessing.set_start_method('spawn', force=True)


# The following class and helper methods can be used together to provide
# observability across processes and threads for testing purposes.


class ObservableAgent(Agent):
    """
    Agent class that accepts a custom _message_log for inspection in tests.

    This class also ignores its own broadcasts by default for convenience.
    """

    def __init__(self,
                 id: str,
                 outbound_queue: _QueueProtocol,
                 receive_own_broadcasts: bool = False,
                 _message_log: List[Message] = []):
        super().__init__(id, outbound_queue=outbound_queue,
                         receive_own_broadcasts=receive_own_broadcasts)
        self._message_log = _message_log


def add_agent(space: Space, agent_type: ObservableAgent, agent_id: str, **agent_kwargs) -> List[Message]:
    """
    Adds an agent to a space and returns a reference to its _message_log for
    testing.
    """
    _message_log = multiprocessing.Manager().list()  # thread and process safe
    space.add(agent_type, agent_id, **agent_kwargs, _message_log=_message_log)
    return _message_log


def _filter_unexpected_meta_keys(actual: Message, expected: Message) -> Message:
    """Filters meta keys from actual that are not in expected"""

    if "meta" not in actual:
        return actual
    if "meta" not in expected:
        actual.pop("meta")
        return actual

    actual_meta = actual.get("meta")
    expected_meta = expected.get("meta")
    filtered_meta = {key: actual_meta[key]
                     for key in expected_meta if key in actual_meta}
    actual["meta"] = filtered_meta
    return actual


def assert_message_log(actual: List[Message],
                       expected: List[Message],
                       max_seconds=2,
                       ignore_order=False,
                       ignore_unexpected_meta_keys=True):
    """
    Asserts that a list of messages is populated as expected.

    Args:
        actual: The actual messages
        expected: The expected messages
        max_seconds: The maximum number of seconds to wait
        ignore_order: If True, ignore the order of messages when comparing
        ignore_unexpected_meta_keys:
            If True, ignore meta keys in actual that are not in expected.
            Defaults to True.
    """

    wait_for_messages(actual, len(expected), max_seconds)

    testcase = unittest.TestCase()
    testcase.maxDiff = None

    if ignore_order:
        # double check that the lengths are equal
        testcase.assertEqual(len(actual), len(expected))
        # check that each expected message is in actual
        for expected_msg in expected:
           for actual_msg in actual:
                actual_to_compare = copy.deepcopy(actual_msg)
                if ignore_unexpected_meta_keys:
                    # filter unexpected meta keys before comparison
                    actual_to_compare = _filter_unexpected_meta_keys(actual_to_compare, expected_msg)
                if actual_to_compare == expected_msg:
                    # we found a match, remove from list
                    actual.remove(actual_msg)
        # if we removed everything from actual, it's a match
        testcase.assertTrue(len(actual) == 0)
    else:
        if ignore_unexpected_meta_keys:
            # filter meta keys from actual that are not in expected
            actual = [_filter_unexpected_meta_keys(actual_msg, expected_msg)
                      for actual_msg, expected_msg in zip(actual, expected)]
        testcase.assertListEqual(actual, expected)


def wait_for_messages(actual_list: List,
                      expected_length: int,
                      max_seconds=2):
    """Waits for the list of messages to be populated."""

    print(f"Waiting {max_seconds} seconds for {expected_length} messages...")
    start_time = time.time()
    while ((time.time() - start_time) < max_seconds):
        time.sleep(0.01)
        actual = list(actual_list)  # cast to list
        if len(actual) > expected_length:
            raise Exception(
                f"too many messages received: {len(actual)} expected: {expected_length}\n{json.dumps(actual, indent=2)}")
        if len(actual) == expected_length:
            return
    raise Exception(
        f"too few messages received: {len(actual)} expected: {expected_length}\n{json.dumps(actual, indent=2)}")
