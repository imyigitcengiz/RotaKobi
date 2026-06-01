from django.test import SimpleTestCase, TestCase

from core_settings.models import WorkSchedulePlan
from core_settings.work_schedule import (
    default_weekly_hours,
    format_plan_summary,
    get_default_work_schedule_plan,
    is_within_work_hours,
    normalize_weekly_hours,
    weekly_hours_from_request,
)


class WorkScheduleNormalizeTests(SimpleTestCase):
    def test_default_has_weekdays(self):
        hours = default_weekly_hours()
        self.assertTrue(hours['monday']['work'])
        self.assertFalse(hours['sunday']['work'])

    def test_invalid_times_disable_day(self):
        raw = {
            'monday': {'work': True, 'start': '18:00', 'end': '09:00'},
        }
        hours = normalize_weekly_hours(raw)
        self.assertFalse(hours['monday']['work'])


class WorkScheduleModelTests(TestCase):
    def test_default_plan_singleton(self):
        p1 = WorkSchedulePlan.objects.create(
            name='A',
            is_default=True,
            weekly_hours=default_weekly_hours(),
        )
        p2 = WorkSchedulePlan.objects.create(
            name='B',
            weekly_hours=default_weekly_hours(),
        )
        from core_settings.work_schedule import set_default_plan

        set_default_plan(p2)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertFalse(p1.is_default)
        self.assertTrue(p2.is_default)
        self.assertEqual(get_default_work_schedule_plan().pk, p2.pk)

    def test_summary(self):
        plan = WorkSchedulePlan.objects.create(
            name='Test',
            weekly_hours=default_weekly_hours(),
        )
        self.assertIn('Pzt', format_plan_summary(plan))
