import importlib
import json
import os
from datetime import date

from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import translation

from admin_app.admin import AdoptionParentAdmin
from admin_app.models import (
    Adoption,
    AdoptionParent,
    AdoptionParentSponsoring,
    Child,
    Donation,
    GenderChoices,
    ParentStatusChoices,
    Sponsor,
    StatusChoices,
)
from admin_app.payments import (
    AXIS_CHILDREN,
    LINK_ACTIVE,
    STANDING_DUE,
    STANDING_MISSING,
    AmountError,
    adoption_amount_target,
    build_payment_grid,
    create_current_year_payments,
    set_payment_amount,
)

YEAR = 2026
TODAY = date(2026, 11, 6)


class PaymentGridTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._previous_target = os.environ.get("AMOUNT_ADOPTION_PARENTS")
        os.environ["AMOUNT_ADOPTION_PARENTS"] = "186"

    @classmethod
    def tearDownClass(cls):
        if cls._previous_target is None:
            os.environ.pop("AMOUNT_ADOPTION_PARENTS", None)
        else:
            os.environ["AMOUNT_ADOPTION_PARENTS"] = cls._previous_target
        super().tearDownClass()

    def make_parent(self, first, last="Parent", active=True):
        return AdoptionParent.objects.create(
            first_name=first,
            last_name=last,
            street_name="Street",
            address_number=1,
            postcode="1000",
            city="Brussels",
            mail=f"{first}.{last}@example.com".lower(),
            active=active,
        )

    def make_child(self, name, status=StatusChoices.ACTIVE, admission=None, leave=None):
        return Child.objects.create(
            name=name,
            gender=GenderChoices.FEMALE,
            day_of_birth=date(2015, 1, 1),
            date_of_admission=admission or date(2020, 1, 1),
            date_of_leave=leave,
            indian_parent_status=ParentStatusChoices.NONE,
            status=status,
        )

    def link(self, parent, child, active=True):
        return Adoption.objects.create(adoptionparent=parent, child=child, active=active)

    def pay(self, parent, child, year, amount=0, month=1, day=1):
        return AdoptionParentSponsoring.objects.create(
            parent=parent,
            child=child,
            date=date(year, month, day),
            amount=amount,
        )

    def grid(self, **kwargs):
        kwargs.setdefault("year", YEAR)
        kwargs.setdefault("today", TODAY)
        return build_payment_grid(**kwargs)

    def cell(self, grid, group_name, leaf_name, year):
        group = next(item for item in grid.groups if item.name == group_name)
        leaf = next(item for item in group.leaves if item.name == leaf_name)
        return leaf.cells[grid.years.index(year)]

    def names(self, grid):
        return {
            group.name: [leaf.name for leaf in group.leaves]
            for group in grid.groups
        }

    def test_inactive_adoption_and_inactive_parent_are_skipped(self):
        parent = self.make_parent("InactiveLink")
        child = self.make_child("StillHere")
        self.link(parent, child, active=False)

        other = self.make_parent("InactiveParent")
        other_child = self.make_child("OtherChild")
        self.link(other, other_child, active=True)
        AdoptionParent.objects.filter(pk=other.pk).update(active=False)

        result = create_current_year_payments(YEAR)

        self.assertEqual(result.created, 0)
        self.assertEqual(AdoptionParentSponsoring.objects.count(), 0)

    def test_child_who_left_in_a_prior_year_is_skipped(self):
        parent = self.make_parent("Ada")
        marked_left = self.make_child("LeftLastYear", status=StatusChoices.LEFT, leave=date(2025, 4, 1))
        status_still_active = self.make_child("LeaveDateOnly", leave=date(2025, 8, 1))
        self.link(parent, marked_left)
        self.link(parent, status_still_active)

        result = create_current_year_payments(YEAR)

        self.assertEqual(result.created, 0)
        self.assertFalse(AdoptionParentSponsoring.objects.exists())

    def test_child_who_leaves_this_year_is_included(self):
        parent = self.make_parent("Ada")
        left = self.make_child("LeftNow", status=StatusChoices.LEFT, leave=date(2026, 3, 1))
        still_marked_active = self.make_child("Leaving", leave=date(2026, 9, 1))
        self.link(parent, left)
        self.link(parent, still_marked_active)

        result = create_current_year_payments(YEAR)

        self.assertEqual(result.created, 2)
        self.assertEqual(
            set(AdoptionParentSponsoring.objects.values_list("child__name", flat=True)),
            {"LeftNow", "Leaving"},
        )
        self.assertTrue(all(
            payment.date == date(YEAR, 1, 1) and payment.amount == 0
            for payment in AdoptionParentSponsoring.objects.all()
        ))

    def test_support_and_future_admission_are_skipped(self):
        parent = self.make_parent("Ada")
        support = self.make_child("Supported", status=StatusChoices.SUPPORT)
        not_yet = self.make_child("NotYet", admission=date(2027, 2, 1))
        no_leave_date = self.make_child("Gone", status=StatusChoices.LEFT)
        self.link(parent, support)
        self.link(parent, not_yet)
        self.link(parent, no_leave_date)

        result = create_current_year_payments(YEAR)

        self.assertEqual(result.created, 0)
        grid = self.grid()
        self.assertEqual(self.cell(grid, "Ada Parent", "Gone", YEAR).kind, "closed")
        self.assertEqual(self.cell(grid, "Ada Parent", "Supported", YEAR).kind, "closed")
        self.assertEqual(self.cell(grid, "Ada Parent", "NotYet", YEAR).kind, "closed")
        leaf = next(item for item in grid.groups[0].leaves if item.name == "Gone")
        self.assertIn("Left, no leave date", leaf.badges)

    def test_second_click_does_not_duplicate(self):
        parent = self.make_parent("Ada")
        child = self.make_child("Asha")
        self.link(parent, child)
        self.pay(parent, child, YEAR, amount=40, month=6, day=2)

        first = create_current_year_payments(YEAR)
        second = create_current_year_payments(YEAR)

        self.assertEqual(first.created, 0)
        self.assertEqual(first.already, 1)
        self.assertEqual(second.created, 0)
        self.assertEqual(second.already, 1)
        self.assertEqual(AdoptionParentSponsoring.objects.count(), 1)

    def test_payment_after_the_leave_year_stays_visible(self):
        parent = self.make_parent("Ada")
        child = self.make_child("Asha", status=StatusChoices.LEFT, leave=date(2024, 5, 1))
        self.link(parent, child, active=False)
        self.pay(parent, child, 2025, amount=186)

        grid = self.grid()
        shown = self.cell(grid, "Ada Parent", "Asha", 2025)
        later = self.cell(grid, "Ada Parent", "Asha", YEAR)

        self.assertEqual(shown.kind, "payments")
        self.assertEqual(shown.marker, "After leave")
        self.assertEqual(later.kind, "closed")
        self.assertEqual(grid.years[0], YEAR)

    def test_inactive_link_keeps_old_payment_without_a_missing_gap(self):
        parent = self.make_parent("Ada")
        child = self.make_child("Asha")
        self.link(parent, child, active=False)
        self.pay(parent, child, 2024, amount=50)

        grid = self.grid()
        old = self.cell(grid, "Ada Parent", "Asha", 2024)
        current = self.cell(grid, "Ada Parent", "Asha", YEAR)

        self.assertEqual(old.kind, "payments")
        self.assertEqual(old.marker, "Ended")
        self.assertEqual(old.payments[0].amount, "50")
        self.assertEqual(current.kind, "closed")

    def test_active_filter_hides_ended_links(self):
        parent = self.make_parent("Ada")
        current = self.make_child("Current")
        ended = self.make_child("Ended", status=StatusChoices.LEFT, leave=date(2024, 1, 1))
        self.link(parent, current)
        self.link(parent, ended, active=False)
        self.pay(parent, ended, 2024, amount=186)

        grid = self.grid(link=LINK_ACTIVE)

        self.assertEqual(self.names(grid), {"Ada Parent": ["Current"]})

    def test_due_filter_shows_who_should_pay_and_has_not_paid(self):
        parent = self.make_parent("Ada")
        missing = self.make_child("Missing")
        unpaid = self.make_child("Unpaid")
        partial = self.make_child("Partial")
        paid = self.make_child("PaidUp")
        left_earlier = self.make_child("LeftEarlier", status=StatusChoices.LEFT, leave=date(2024, 1, 1))
        leaving = self.make_child("Leaving", status=StatusChoices.LEFT, leave=date(YEAR, 3, 1))
        for child in (missing, unpaid, partial, paid, left_earlier, leaving):
            self.link(parent, child)
        self.pay(parent, unpaid, YEAR, amount=0)
        self.pay(parent, partial, YEAR, amount=40)
        self.pay(parent, paid, YEAR, amount=186)
        self.pay(parent, left_earlier, YEAR, amount=0)

        grid = self.grid(standing=STANDING_DUE)

        self.assertEqual(
            self.names(grid),
            {"Ada Parent": ["Leaving", "Missing", "Partial", "Unpaid"]},
        )

    def test_child_status_filter_matches_several_statuses(self):
        parent = self.make_parent("Ada")
        active = self.make_child("Active")
        support = self.make_child("Helped", status=StatusChoices.SUPPORT)
        left = self.make_child("Gone", status=StatusChoices.LEFT, leave=date(2024, 1, 1))
        for child in (active, support, left):
            self.link(parent, child)

        grid = self.grid(child_status=[StatusChoices.SUPPORT, StatusChoices.LEFT])

        self.assertEqual(self.names(grid), {"Ada Parent": ["Gone", "Helped"]})

    def test_missing_filter_shows_only_eligible_pairs_without_a_row(self):
        parent = self.make_parent("Ada")
        missing = self.make_child("Missing")
        unpaid = self.make_child("Unpaid")
        ended = self.make_child("Ended")
        self.link(parent, missing)
        self.link(parent, unpaid)
        self.link(parent, ended, active=False)
        self.pay(parent, unpaid, YEAR, amount=0)

        grid = self.grid(standing=STANDING_MISSING)

        self.assertEqual(self.names(grid), {"Ada Parent": ["Missing"]})
        self.assertEqual(self.cell(grid, "Ada Parent", "Missing", YEAR).kind, "missing")

    def test_filters_do_not_change_who_receives_a_payment(self):
        parent = self.make_parent("Ada")
        visible = self.make_child("Visible")
        hidden = self.make_child("Hidden")
        self.link(parent, visible)
        self.link(parent, hidden)

        filtered = self.grid(name="Visible")
        self.assertEqual(self.names(filtered), {"Ada Parent": ["Visible"]})

        result = create_current_year_payments(YEAR)

        self.assertEqual(result.created, 2)
        self.assertEqual(
            set(AdoptionParentSponsoring.objects.values_list("child__name", flat=True)),
            {"Visible", "Hidden"},
        )

    def test_visible_rows_determine_the_year_sum(self):
        parent = self.make_parent("Ada")
        visible = self.make_child("Visible")
        other = self.make_child("Other")
        self.link(parent, visible)
        self.link(parent, other)
        self.pay(parent, visible, YEAR, amount=100)
        self.pay(parent, other, YEAR, amount=50)

        grid = self.grid(name="Visible")

        self.assertEqual(grid.groups[0].sums[0].total, 100)

    def test_child_axis_nests_parents_under_the_child(self):
        parent = self.make_parent("Ada")
        other = self.make_parent("Bea")
        child = self.make_child("Asha")
        self.link(parent, child)
        self.link(other, child)

        grid = self.grid(axis=AXIS_CHILDREN)

        self.assertEqual(self.names(grid), {"Asha": ["Ada Parent", "Bea Parent"]})

    def test_amount_edit_saves_without_going_through_admin_notifications(self):
        parent = self.make_parent("Ada")
        child = self.make_child("Asha")
        payment = self.pay(parent, child, YEAR, amount=0)

        payload = set_payment_amount(payment, "186")

        payment.refresh_from_db()
        self.assertEqual(payment.amount, 186)
        self.assertEqual(payload["color"], "#16a34a")
        self.assertGreater(payment.history.count(), 1)
        with self.assertRaises(AmountError):
            set_payment_amount(payment, -5)

    def test_full_payment_is_186_before_2025_and_225_from_2025(self):
        previous = os.environ.get("AMOUNT_ADOPTION_PARENTS")
        os.environ["AMOUNT_ADOPTION_PARENTS"] = "225"
        try:
            parent = self.make_parent("Ada")
            child = self.make_child("Asha")
            self.link(parent, child)
            self.pay(parent, child, 2024, amount=186)
            self.pay(parent, child, 2025, amount=186)
            grid = self.grid(year=2026)

            old = self.cell(grid, "Ada Parent", "Asha", 2024)
            current = self.cell(grid, "Ada Parent", "Asha", 2025)

            self.assertEqual(adoption_amount_target(2024), 186)
            self.assertEqual(old.status, "paid")
            self.assertEqual(old.target, 186)
            self.assertEqual(adoption_amount_target(2025), 225)
            self.assertEqual(current.status, "partial")
            self.assertEqual(current.target, 225)
        finally:
            if previous is None:
                os.environ.pop("AMOUNT_ADOPTION_PARENTS", None)
            else:
                os.environ["AMOUNT_ADOPTION_PARENTS"] = previous

    def test_yearly_runner_and_parent_action_are_gone(self):
        import admin_app.tasks as tasks
        self.assertFalse(hasattr(tasks, "add_yearly_adoption_parent_payments"))
        self.assertNotIn("add_new_sponsoring", AdoptionParentAdmin.actions)

    def test_migration_disables_the_scheduled_task(self):
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        schedule = IntervalSchedule.objects.create(every=1, period=IntervalSchedule.DAYS)
        yearly = PeriodicTask.objects.create(
            name="yearly adoption payments",
            task="admin_app.tasks.add_yearly_adoption_parent_payments",
            interval=schedule,
            enabled=True,
        )
        other = PeriodicTask.objects.create(
            name="something else",
            task="admin_app.tasks.other",
            interval=schedule,
            enabled=True,
        )
        migration = importlib.import_module(
            "admin_app.migrations.0019_disable_yearly_adoption_payment_task"
        )
        migration.disable_yearly_payment_task(apps, None)

        yearly.refresh_from_db()
        other.refresh_from_db()
        self.assertFalse(yearly.enabled)
        self.assertTrue(other.enabled)


class PaymentGridViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._previous_target = os.environ.get("AMOUNT_ADOPTION_PARENTS")
        os.environ["AMOUNT_ADOPTION_PARENTS"] = "186"

    @classmethod
    def tearDownClass(cls):
        if cls._previous_target is None:
            os.environ.pop("AMOUNT_ADOPTION_PARENTS", None)
        else:
            os.environ["AMOUNT_ADOPTION_PARENTS"] = cls._previous_target
        super().tearDownClass()

    def setUp(self):
        translation.activate("en")
        self.user = User.objects.create_superuser("admin", "admin@example.com", "secret")
        self.client.force_login(self.user)
        self.parent = AdoptionParent.objects.create(
            first_name="Ada",
            last_name="Parent",
            street_name="Street",
            address_number=1,
            postcode="1000",
            city="Brussels",
            mail="ada.parent@example.com",
        )
        self.visible = Child.objects.create(
            name="Visible",
            gender=GenderChoices.FEMALE,
            day_of_birth=date(2015, 1, 1),
            date_of_admission=date(2020, 1, 1),
            indian_parent_status=ParentStatusChoices.NONE,
            status=StatusChoices.ACTIVE,
        )
        self.hidden = Child.objects.create(
            name="Hidden",
            gender=GenderChoices.MALE,
            day_of_birth=date(2016, 1, 1),
            date_of_admission=date(2020, 1, 1),
            indian_parent_status=ParentStatusChoices.NONE,
            status=StatusChoices.ACTIVE,
        )
        Adoption.objects.create(adoptionparent=self.parent, child=self.visible, active=True)
        Adoption.objects.create(adoptionparent=self.parent, child=self.hidden, active=True)

    def test_filtered_page_still_creates_every_eligible_payment(self):
        url = reverse("admin:adoption_payment_grid")
        response = self.client.post(
            f"{url}?q=Visible",
            {"action": "create_year"},
            HTTP_HOST="care-india.be",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            set(AdoptionParentSponsoring.objects.values_list("child__name", flat=True)),
            {"Visible", "Hidden"},
        )

    def test_grid_page_renders_the_current_year_first(self):
        pay_year = date.today().year
        AdoptionParentSponsoring.objects.create(
            parent=self.parent,
            child=self.visible,
            date=date(pay_year - 1, 1, 1),
            amount=10,
        )
        request = RequestFactory().get(reverse("admin:adoption_payment_grid"))
        request.user = self.user
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        from admin_app.admin import AdoptionParentSponsoringAdmin
        from admin_app.sites import saranalaya_admin_site

        view = AdoptionParentSponsoringAdmin(AdoptionParentSponsoring, saranalaya_admin_site)
        response = view.payment_grid_view(request)
        response.render()
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["grid"].filters.standing, "due")
        self.assertIn("Visible", content)
        self.assertIn("By parent", content)
        self.assertIn("By child", content)
        self.assertIn("Payment list", content)
        self.assertIn("Still to pay", content)
        self.assertLess(
            content.index(f'class="pay-year">{pay_year}'),
            content.index(f'class="pay-year">{pay_year - 1}'),
        )

    def test_payment_list_links_back_to_parent_and_child_views(self):
        from django.template.loader import render_to_string
        from admin_app.admin import AdoptionParentSponsoringAdmin

        self.assertEqual(
            AdoptionParentSponsoringAdmin.list_before_template,
            "admin/adoption_payment_switcher.html",
        )
        content = render_to_string("admin/adoption_payment_switcher.html", {})

        self.assertIn("By parent", content)
        self.assertIn("By child", content)
        self.assertIn("axis=parents", content)
        self.assertIn("axis=children", content)
        self.assertIn("standing=due", content)

    def test_inline_amount_save(self):
        payment = AdoptionParentSponsoring.objects.create(
            parent=self.parent,
            child=self.visible,
            date=date(date.today().year, 1, 1),
            amount=0,
        )
        url = reverse("admin:adoption_payment_amount", args=[payment.pk])
        response = self.client.post(
            url,
            data=json.dumps({"amount": 90}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.amount, 90)
        rejected = self.client.post(
            url,
            data=json.dumps({"amount": -1}),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 400)


class DonationGridTests(TestCase):
    def setUp(self):
        translation.activate("en")
        self.user = User.objects.create_superuser("admin", "admin@example.com", "secret")
        self.client.force_login(self.user)
        self.year = date.today().year

    def make_sponsor(self, first, last="Giver", firm="", letters=True):
        return Sponsor.objects.create(
            first_name=first,
            last_name=last,
            firm=firm,
            street_name="Street",
            address_number=1,
            postcode="1000",
            city="Brussels",
            mail=f"{first}.{last}@example.com".lower(),
            letters=letters,
        )

    def donate(self, sponsor, year, amount, month=3, day=12, description=""):
        return Donation.objects.create(
            sponsor=sponsor,
            date=date(year, month, day),
            amount=amount,
            description=description,
        )

    def test_grid_lists_sponsors_and_donations_without_payment_colors(self):
        ada = self.make_sponsor("Ada", firm="Acme")
        self.make_sponsor("Bea", letters=False)
        self.donate(ada, self.year, 40)
        self.donate(ada, self.year, 15, month=11, day=2)
        self.donate(ada, self.year - 1, 10, month=1, day=8)

        response = self.client.get(reverse("admin:admin_app_sponsor_changelist"))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Giver")
        self.assertContains(response, "Bea Giver")
        self.assertContains(response, "Acme")
        self.assertContains(response, "No letters")
        self.assertContains(response, "€40")
        self.assertContains(response, "€15")
        self.assertContains(response, "€10")
        self.assertContains(response, "Add sponsor")
        self.assertContains(response, "Add donation")
        self.assertNotContains(response, "pay-cell-unpaid")
        self.assertNotContains(response, "pay-cell-partial")
        self.assertNotContains(response, "pay-cell-paid")
        self.assertLess(
            content.index(f'class="pay-year">{self.year}'),
            content.index(f'class="pay-year">{self.year - 1}'),
        )

    def test_name_filter_limits_rows_and_keeps_every_sponsor_in_the_add_list(self):
        self.make_sponsor("Ada")
        self.make_sponsor("Bea")

        response = self.client.get(reverse("admin:admin_app_sponsor_changelist"), {"q": "Bea"})

        self.assertEqual([row.name for row in response.context["grid"].rows], ["Bea Giver"])
        self.assertEqual(
            [choice.name for choice in response.context["grid"].sponsor_choices],
            ["Ada Giver", "Bea Giver"],
        )

    def test_donation_tab_opens_the_same_grid(self):
        from django.conf import settings
        from django.utils.encoding import force_str

        response = self.client.get(reverse("admin:admin_app_donation_changelist"))
        self.assertRedirects(
            response,
            reverse("admin:admin_app_sponsor_changelist"),
            fetch_redirect_response=False,
        )
        titles = [
            force_str(item["title"])
            for item in settings.UNFOLD["SIDEBAR"]["navigation"][0]["items"]
        ]
        self.assertIn("Sponsors", titles)
        self.assertNotIn("Donations", titles)

        request = RequestFactory().get("/admin/")
        request.user = self.user
        from admin_app.sites import saranalaya_admin_site

        names = [
            model["object_name"]
            for app in saranalaya_admin_site.get_app_list(request)
            for model in app["models"]
        ]
        self.assertIn("Sponsor", names)
        self.assertNotIn("Donation", names)

    def test_add_sponsor_and_donation_from_the_grid(self):
        sponsor = self.make_sponsor("Ada")
        created = self.client.post(
            reverse("admin:sponsor_quick_create"),
            data=json.dumps({
                "first_name": "Cleo",
                "last_name": "Giver",
                "mail": "cleo.giver@example.com",
                "street_name": "Lane",
                "address_number": 4,
                "postcode": "2000",
                "city": "Antwerp",
                "letters": False,
            }),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200)
        cleo = Sponsor.objects.get(first_name="Cleo")
        self.assertEqual(cleo.city, "Antwerp")
        self.assertFalse(cleo.letters)
        self.assertEqual(cleo.country, "Belgium")

        rejected = self.client.post(
            reverse("admin:sponsor_quick_create"),
            data=json.dumps({"first_name": "No"}),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 400)

        donation = self.client.post(
            reverse("admin:sponsor_donation_create"),
            data=json.dumps({
                "sponsor": sponsor.pk,
                "amount": 25,
                "date": f"{self.year}-05-01",
                "description": "Spring gift",
            }),
            content_type="application/json",
        )
        self.assertEqual(donation.status_code, 200)
        saved = Donation.objects.get(sponsor=sponsor)
        self.assertEqual(saved.amount, 25)
        self.assertEqual(saved.description, "Spring gift")

        missing = self.client.post(
            reverse("admin:sponsor_donation_create"),
            data=json.dumps({"sponsor": 0, "amount": 5, "date": f"{self.year}-05-01"}),
            content_type="application/json",
        )
        self.assertEqual(missing.status_code, 400)

    def test_edit_donation_amount_and_reject_a_negative_amount(self):
        sponsor = self.make_sponsor("Ada")
        donation = self.donate(sponsor, self.year, 10)
        url = reverse("admin:sponsor_donation_amount", args=[donation.pk])

        response = self.client.post(
            url,
            data=json.dumps({"amount": 80, "date": f"{self.year}-06-02", "description": "Updated"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        donation.refresh_from_db()
        self.assertEqual(donation.amount, 80)
        self.assertEqual(donation.date, date(self.year, 6, 2))
        self.assertEqual(donation.description, "Updated")

        rejected = self.client.post(
            url,
            data=json.dumps({"amount": -1, "date": f"{self.year}-06-02"}),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 400)
        donation.refresh_from_db()
        self.assertEqual(donation.amount, 80)

    def test_address_list_uses_the_visible_sponsors(self):
        self.make_sponsor("Ada")
        self.make_sponsor("Bea")
        url = reverse("admin:admin_app_sponsor_changelist")

        from admin_app.donations import visible_sponsor_ids

        self.assertEqual(
            list(Sponsor.objects.filter(pk__in=visible_sponsor_ids("Ada")).values_list("first_name", flat=True)),
            ["Ada"],
        )
        empty = self.client.post(url, {"action": "address", "q": "nobody-xyz"}, follow=True)
        contexts = empty.context if isinstance(empty.context, (list, tuple)) else [empty.context]
        messages = []
        for context in contexts:
            if not context:
                continue
            try:
                messages.extend(str(message) for message in context["messages"])
            except (KeyError, TypeError):
                continue
        self.assertTrue(
            "No sponsors to export." in empty.content.decode()
            or any("No sponsors to export." in message for message in messages)
        )

        pdf = self.client.post(url, {"action": "address", "q": "Ada"})
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
