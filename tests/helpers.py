import copy
import json
import time
import unittest
from typing import List
from agency.logger import log

from agency.schema import Message


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
                       max_seconds=5,
                       ignore_order=False,
                       ignore_unexpected_meta_keys=True):
    """
    Asserts that an agents message log is populated as expected.

    Args:
        actual: The actual message log
        expected: The expected message log
        max_seconds: The maximum number of seconds to wait
        ignore_order:
            If True, ignore the order of messages when comparing. Defaults to
            False.
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
                    actual_to_compare = _filter_unexpected_meta_keys(
                        actual_to_compare, expected_msg)
                if actual_to_compare == expected_msg:
                    # we found a match, remove from list
                    actual.remove(actual_msg)
        # if we removed everything from actual, it's a match
        testcase.assertTrue(
            len(actual) == 0,
            "expected messages not found in actual messages" +
            "\nactual: " + json.dumps(actual, indent=2) +
            "\nexpected: " + json.dumps(expected, indent=2))
    else:
        if ignore_unexpected_meta_keys:
            # filter meta keys from actual that are not in expected
            actual = [_filter_unexpected_meta_keys(actual_msg, expected_msg)
                      for actual_msg, expected_msg in zip(actual, expected)]

        for i, (actual_msg, expected_msg) in enumerate(zip(actual, expected)):
            assert actual_msg == expected_msg, \
                f"Messages at index {i} are not equal:" \
                f"\n--- actual ---" \
                f"\n{json.dumps(actual_msg, indent=2)}" \
                f"\n--- expected ---" \
                f"\n{json.dumps(expected_msg, indent=2)}" \
                f"\n--- full actual ---" \
                f"\n{json.dumps(actual, indent=2)}" \
                f"\n--- full expected ---" \
                f"\n{json.dumps(expected, indent=2)}"


def wait_for_messages(actual_list: List,
                      expected_length: int,
                      max_seconds: int,
                      hold_seconds: int = 0.1):
    """Waits for the list of messages to be an expected length."""

    print(f"Waiting {max_seconds} seconds for {expected_length} messages...")
    start_time = time.time()
    equal_length_start_time = None
    while ((time.time() - start_time) < max_seconds):
        time.sleep(0.01)
        actual = list(actual_list)  # cast to list
        if len(actual) > expected_length:
            raise Exception(
                f"too many messages received: {len(actual)} expected: {expected_length}\n{json.dumps(actual, indent=2)}")
        if len(actual) == expected_length:
            if equal_length_start_time is None:
                equal_length_start_time = time.time()
            if (time.time() - equal_length_start_time) >= hold_seconds:
                return
    raise Exception(
        f"too few messages received: {len(actual)} expected: {expected_length}\n{json.dumps(actual, indent=2)}")
