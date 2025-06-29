from django.test import TestCase

from ..utils import ZeepValue, zeepobj_to_dict


class ZeepobjToDictTest(TestCase):
    def test_flatten_dict(self) -> None:
        inp: ZeepValue = {
            "name": "Alice",
            "age": 30,
            "height": 5.6,
            "is_active": None,
            "hobbies": ["reading", "cycling", None],
            "preferences": {
                "theme": "dark",
                "notifications": {"email": True, "sms": False},
                "languages": ["English", "Spanish", "French"],
            },
            "metrics": [
                {"day": "Monday", "steps": 12000},
                {"day": "Tuesday", "steps": 15000},
                {"day": "Wednesday", "steps": None},
            ],
        }
        out = zeepobj_to_dict(inp)
        self.maxDiff = None
        self.assertEqual(
            out,
            {
                "name": "Alice",
                "age": 30,
                "height": 5.6,
                "hobbies[0]": "reading",
                "hobbies[1]": "cycling",
                "preferences.theme": "dark",
                "preferences.notifications.email": True,
                "preferences.notifications.sms": False,
                "preferences.languages[0]": "English",
                "preferences.languages[1]": "Spanish",
                "preferences.languages[2]": "French",
                "metrics[0].day": "Monday",
                "metrics[0].steps": 12000,
                "metrics[1].day": "Tuesday",
                "metrics[1].steps": 15000,
                "metrics[2].day": "Wednesday",
            },
        )
