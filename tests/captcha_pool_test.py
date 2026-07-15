import datetime
import unittest

from main import (
    _available_preheated_captchas,
    _click_captcha_preheat_slots,
    _get_captcha_preheat_deadline,
    _remaining_captcha_preheat_seconds,
    _reuse_unsubmitted_captcha,
    _shared_captcha_preheat_is_serial,
    _should_wait_for_background_followup,
    _should_wait_for_click_preheat,
    _store_shared_captcha,
)
from utils.reserve import reserve


class CaptchaPoolTest(unittest.TestCase):
    def test_simultaneous_reservation_limit_is_terminal(self):
        self.assertTrue(
            reserve._is_terminal_submit_failure("同时预约数量已达上限3次")
        )

    def test_only_serial_followups_wait_for_background_first_captcha(self):
        self.assertFalse(_should_wait_for_background_followup("serial", 1))
        self.assertTrue(_should_wait_for_background_followup("serial", 2))
        self.assertTrue(_should_wait_for_background_followup("serial", 3))
        self.assertFalse(_should_wait_for_background_followup("burst", 2))

    def test_only_multi_slot_shared_pool_uses_serial_preheat(self):
        self.assertFalse(_shared_captcha_preheat_is_serial(1))
        self.assertTrue(_shared_captcha_preheat_is_serial(2))
        self.assertTrue(_shared_captcha_preheat_is_serial(3))

    def test_multi_slot_background_preheat_never_blocks_token(self):
        self.assertTrue(_should_wait_for_click_preheat(1, True))
        self.assertFalse(_should_wait_for_click_preheat(2, True))
        self.assertFalse(_should_wait_for_click_preheat(3, True))
        self.assertFalse(_should_wait_for_click_preheat(1, False))

    def test_single_slot_keeps_one_click_captcha_preheat(self):
        self.assertEqual(_click_captcha_preheat_slots(1), (1,))
        self.assertEqual(_click_captcha_preheat_slots(2), (1, 2, 3))
        self.assertEqual(_click_captcha_preheat_slots(3), (1, 2, 3))

    def test_soft_deadline_stops_with_one_result_but_retries_when_empty(self):
        soft_deadline = datetime.datetime(2026, 7, 15, 19, 59, 58)
        retry_deadline = datetime.datetime(2026, 7, 15, 20, 0, 40)
        now = soft_deadline + datetime.timedelta(milliseconds=1)

        self.assertGreater(
            _remaining_captcha_preheat_seconds(
                now,
                soft_deadline,
                retry_deadline,
                True,
                {1: "", 2: "", 3: ""},
            ),
            0,
        )
        self.assertEqual(
            _remaining_captcha_preheat_seconds(
                now,
                soft_deadline,
                retry_deadline,
                True,
                {1: "captcha-1", 2: "", 3: ""},
            ),
            0,
        )

    def test_multi_slot_deadline_is_two_seconds_before_a_or_c_token_node(self):
        target = datetime.datetime(2026, 7, 15, 20, 0, 0)

        self.assertEqual(
            _get_captcha_preheat_deadline(
                target,
                target - datetime.timedelta(milliseconds=1531),
                3,
                "A",
            ),
            target - datetime.timedelta(milliseconds=3531),
        )
        self.assertEqual(
            _get_captcha_preheat_deadline(
                target,
                target + datetime.timedelta(milliseconds=14),
                2,
                "C",
            ),
            target - datetime.timedelta(milliseconds=1986),
        )
        self.assertEqual(
            _get_captcha_preheat_deadline(
                target,
                target - datetime.timedelta(milliseconds=1531),
                1,
                "A",
            ),
            target,
        )
        self.assertEqual(
            _get_captcha_preheat_deadline(target, target, 3, "B"),
            target,
        )

    def test_unused_captchas_roll_over_in_original_order(self):
        pool = {1: "captcha-1", 2: "captcha-2", 3: "captcha-3"}

        self.assertEqual(
            _available_preheated_captchas(pool, {"captcha-1"}),
            ["captcha-2", "captcha-3"],
        )
        self.assertEqual(
            _available_preheated_captchas(pool, {"captcha-1", "captcha-2"}),
            ["captcha-3"],
        )
        self.assertEqual(
            _available_preheated_captchas(pool, set(pool.values())),
            [],
        )

    def test_zero_shared_pool_stores_onsite_captcha_in_consumed_slot(self):
        pool = {1: "used-1", 2: "used-2", 3: "used-3"}
        consumed = set(pool.values())

        self.assertEqual(_store_shared_captcha(pool, consumed, "onsite-1"), 1)
        self.assertEqual(
            _available_preheated_captchas(pool, consumed),
            ["onsite-1"],
        )
        self.assertEqual(_store_shared_captcha(pool, consumed, "onsite-1"), 1)

    def test_unsubmitted_captcha_is_reused_but_posted_captcha_is_not(self):
        self.assertEqual(
            _reuse_unsubmitted_captcha(False, "captcha-2"),
            "captcha-2",
        )
        self.assertEqual(_reuse_unsubmitted_captcha(True, "captcha-2"), "")


if __name__ == "__main__":
    unittest.main()
