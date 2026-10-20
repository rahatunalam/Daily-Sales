from decimal import Decimal

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from shopsettings.models import MfsAccount


class Base(APITestCase):
    def setUp(self):
        cache.clear()  # the login throttle is cache based
        self.owner = User.objects.create_user("OWNER", "owner1234", role="owner")
        self.cashier = User.objects.create_user("RAHAT", "1234", role="cashier", designation="Sales Man")
        self.login("OWNER", "owner1234")

    def login(self, name, pw):
        r = self.client.post("/api/auth/login/", {"name": name, "password": pw}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + r.data["token"])
        return r

    def tx(self, **kw):
        return self.client.post("/api/transactions/", kw, format="json")

    def customer(self, name="Karim", phone="01811 223344"):
        return self.client.post("/api/customers/", {"name": name, "phone": phone}, format="json").data


class AuthTests(Base):
    def test_login_rules(self):
        self.client.credentials()
        bad = self.client.post("/api/auth/login/", {"name": "rahat", "password": "nope"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.data["detail"], "Wrong name or password.")
        ok = self.client.post("/api/auth/login/", {"name": "rahat", "password": "1234"}, format="json")
        self.assertEqual(ok.data["profile"]["designation"], "Sales Man")  # name is not case sensitive

    def test_inactive_user_refused(self):
        self.cashier.is_active = False
        self.cashier.save()
        self.client.credentials()
        r = self.client.post("/api/auth/login/", {"name": "RAHAT", "password": "1234"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("inactive", r.data["detail"])

    def test_profile_and_change_password(self):
        self.login("RAHAT", "1234")
        me = self.client.get("/api/auth/me/").data
        self.assertEqual((me["name"], me["designation"]), ("RAHAT", "Sales Man"))
        cp = lambda **k: self.client.post("/api/auth/change-password/", k, format="json")
        self.assertEqual(cp(current_password="x", new_password="abcd", confirm_password="abcd").status_code, 400)
        self.assertIn("at least 4", cp(current_password="1234", new_password="ab", confirm_password="ab").data["detail"])
        self.assertIn("different", cp(current_password="1234", new_password="1234", confirm_password="1234").data["detail"])
        self.assertIn("do not match", cp(current_password="1234", new_password="abcd", confirm_password="abce").data["detail"])
        r = cp(current_password="1234", new_password="abcd", confirm_password="abcd")
        self.assertEqual(r.status_code, 200)
        self.login("RAHAT", "abcd")

    def test_only_owner_manages_users(self):
        self.assertEqual(self.client.get("/api/users/").status_code, 200)
        self.login("RAHAT", "1234")
        self.assertEqual(self.client.get("/api/users/").status_code, 403)
        self.assertEqual(self.client.get("/api/companies/").status_code, 403)

    def test_owner_user_admin(self):
        r = self.client.post("/api/users/", {"name": "Sumi", "role": "manager", "password": "1234"}, format="json")
        self.assertEqual(r.status_code, 201)
        dup = self.client.post("/api/users/", {"name": "sumi", "role": "manager", "password": "1234"}, format="json")
        self.assertEqual(dup.status_code, 400)
        t = self.client.post(f"/api/users/{r.data['id']}/toggle-active/")
        self.assertFalse(t.data["is_active"])
        me = self.client.post(f"/api/users/{self.owner.pk}/toggle-active/")
        self.assertEqual(me.status_code, 400)


class SalesTests(Base):
    def test_method_rules(self):
        self.assertEqual(self.tx(method="CASH", amount="0").status_code, 400)
        self.assertEqual(self.tx(method="MFS", amount="50").status_code, 400)  # wallet needed
        self.assertEqual(self.tx(method="DUE", amount="50").status_code, 400)  # BR-02
        self.assertEqual(self.tx(method="REFUND", amount="50").status_code, 201)  # BR-04 customer optional
        bk = MfsAccount.objects.get(name="bKash")
        self.assertEqual(self.tx(method="MFS", wallet=bk.pk, amount="50").status_code, 201)

    def test_customer_rules(self):
        self.assertEqual(self.client.post("/api/customers/", {"name": "A", "phone": "123"}, format="json").status_code, 400)
        self.customer("Karim", "01811 223344")
        same_phone = self.client.post("/api/customers/", {"name": "Other", "phone": "01811223344"}, format="json")
        self.assertEqual(same_phone.status_code, 400)  # BR-12
        found = self.client.get("/api/customers/?search=0181").data["results"]
        self.assertEqual(len(found), 1)

    def test_due_flow(self):
        c = self.customer()
        self.assertEqual(self.tx(method="DUE", customer=c["id"], amount="1000").status_code, 201)
        over = self.client.post(f"/api/customers/{c['id']}/receive/", {"amount": "1500"}, format="json")
        self.assertEqual(over.status_code, 400)  # BR-03
        ok = self.client.post(f"/api/customers/{c['id']}/receive/", {"amount": "100"}, format="json")
        self.assertEqual(ok.status_code, 201)
        cust = self.client.get(f"/api/customers/{c['id']}/").data
        self.assertEqual(Decimal(cust["remaining"]), Decimal("900"))
        self.assertEqual(Decimal(self.client.get("/api/customers/due-summary/").data["total_remaining"]), Decimal("900"))
        hist = self.client.get(f"/api/customers/{c['id']}/history/").data
        self.assertEqual([Decimal(r["remaining"]) for r in hist["rows"]], [Decimal("900"), Decimal("1000")])
        self.assertEqual(len(self.client.get("/api/customers/?has_due=true").data["results"]), 1)


class CompanyTests(Base):
    def test_company_flow(self):
        co = self.client.post("/api/companies/", {"name": "Beximco"}, format="json")
        self.assertEqual(co.status_code, 201)
        self.assertEqual(self.client.post("/api/companies/", {"name": "beximco"}, format="json").status_code, 400)
        bill = self.client.post("/api/company-entries/", {"company": co.data["id"], "bill_amount": "10000", "paid_amount": "5000"}, format="json")
        self.assertEqual(bill.status_code, 201)
        self.assertEqual(Decimal(bill.data["due_amount"]), Decimal("5000"))
        too_much = self.client.post("/api/company-entries/", {"company": co.data["id"], "bill_amount": "100", "paid_amount": "9000"}, format="json")
        self.assertEqual(too_much.status_code, 400)  # BR-09
        pay = self.client.post(f"/api/companies/{co.data['id']}/pay/", {"amount": "5000"}, format="json")
        self.assertEqual(pay.status_code, 201)
        self.assertEqual(self.client.post(f"/api/companies/{co.data['id']}/pay/", {"amount": "1"}, format="json").status_code, 400)
        hist = self.client.get(f"/api/companies/{co.data['id']}/history/").data
        self.assertEqual(Decimal(hist["remaining_due"]), Decimal("0"))
        self.assertEqual([Decimal(r["remaining"]) for r in hist["rows"]], [Decimal("5000"), Decimal("0")])
        self.assertEqual(Decimal(self.client.get("/api/companies/summary/").data["total_due"]), Decimal("0"))
        self.assertEqual(len(self.client.get("/api/companies/?search=bex").data["results"]), 1)


class LedgerTests(Base):
    def test_closing_formula_summary_and_report(self):
        """Closing = Opening + Cash + MFS + Card + Due received - Refund - Company payments (Due excluded)."""
        bk = MfsAccount.objects.get(name="bKash")
        c = self.customer()
        self.client.put("/api/opening-balance/", {"amount": "1500"}, format="json")
        self.tx(method="CASH", amount="150")
        self.tx(method="MFS", wallet=bk.pk, amount="50")
        self.tx(method="CARD", amount="25")
        self.tx(method="DUE", customer=c["id"], amount="1000")  # must not change closing
        self.client.post(f"/api/customers/{c['id']}/receive/", {"amount": "100"}, format="json")
        self.tx(method="REFUND", amount="50")
        co = self.client.post("/api/companies/", {"name": "Square"}, format="json").data
        self.client.post("/api/company-entries/", {"company": co["id"], "bill_amount": "5000", "paid_amount": "200"}, format="json")

        s = self.client.get("/api/daily-summary/").data
        rows = {r["label"]: Decimal(r["amount"]) for r in s["rows"]}
        self.assertEqual(rows["bKash"], Decimal("50"))
        self.assertEqual(rows["Nagad"], Decimal("0"))
        self.assertEqual(Decimal(s["total_sales_without_due"]), Decimal("275"))  # 150+50+25+100-50
        self.assertEqual(Decimal(s["total_sales_with_due"]), Decimal("1275"))
        # 1500 + 150 + 50 + 25 + 100 - 50 - 200 = 1575
        self.assertEqual(Decimal(s["closing_balance"]), Decimal("1575"))

        rep = self.client.get("/api/reports/daily/?preset=today").data["rows"][0]
        self.assertEqual(Decimal(rep["closing_balance"]), Decimal("1575"))
        self.assertEqual(Decimal(rep["sales_received"]), Decimal("225"))  # 150 + 50 + 25
        self.assertEqual(Decimal(rep["refund"]), Decimal("50"))
        self.assertEqual(Decimal(rep["company_paid"]), Decimal("200"))
        self.assertEqual(Decimal(rep["due"]), Decimal("1000"))
        self.assertEqual(
            Decimal(rep["opening_balance"]) + Decimal(rep["sales_received"]) + Decimal(rep["due_receive"])
            - Decimal(rep["refund"]) - Decimal(rep["company_paid"]),
            Decimal(rep["closing_balance"]),
        )
        self.assertEqual(Decimal(rep["remaining_due"]), Decimal("900"))
        self.assertEqual(Decimal(rep["company_bill_amount"]), Decimal("5000"))
        self.assertEqual(Decimal(rep["company_bill_paid"]), Decimal("200"))
        self.assertEqual(Decimal(rep["company_remaining_bill"]), Decimal("4800"))

        today = timezone.localdate().isoformat()
        d = self.client.get(f"/api/reports/daily/details/?date={today}").data
        rows = {r["label"]: Decimal(r["amount"]) for r in d["sales_and_due"]["rows"]}
        self.assertEqual((rows["Cash"], rows["bKash"], rows["Due"], rows["Refund"]), (150, 50, 1000, 50))
        self.assertEqual(Decimal(d["sales_and_due"]["total_sales_without_due"]), Decimal("275"))
        self.assertEqual(Decimal(d["sales_and_due"]["total_sales_with_due"]), Decimal("1275"))
        self.assertEqual(
            [(c["company_name"], Decimal(c["paid_amount"])) for c in d["company_payments"]],
            [("Square", Decimal("200"))],
        )
        self.assertEqual(self.client.get("/api/reports/daily/details/").status_code, 400)
        self.assertEqual(self.client.get("/api/reports/daily/details/?date=2020-01-01").data["company_payments"], [])

    def test_day_closing_must_match(self):
        self.client.put("/api/opening-balance/", {"amount": "170"}, format="json")
        closing = self.client.get("/api/day-closing/").data
        self.assertEqual(Decimal(closing["closing_balance"]), Decimal("170"))
        self.assertFalse(closing["closed"])
        wrong = self.client.post("/api/day-closing/", {"counts": [{"value": "100", "quantity": 1}]}, format="json")
        self.assertEqual(wrong.status_code, 400)
        self.assertIn("Short by 70.00", wrong.data["detail"])
        right = self.client.post(
            "/api/day-closing/",
            {"counts": [{"value": "100", "quantity": 1}, {"value": "50", "quantity": 1}, {"value": "20", "quantity": 1}]},
            format="json",
        )
        self.assertEqual(right.status_code, 201, right.content)
        again = self.client.post("/api/day-closing/", {"counts": []}, format="json")
        self.assertEqual(again.status_code, 409)
        self.assertTrue(self.client.get("/api/day-closing/").data["closed"])
        self.assertEqual(self.client.put("/api/opening-balance/", {"amount": "1"}, format="json").status_code, 409)

    def test_decimal_denominations(self):
        r = self.client.post("/api/denominations/", {"value": "0.25"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.post("/api/denominations/", {"value": "0.25"}, format="json").status_code, 400)
        self.client.put("/api/opening-balance/", {"amount": "0.75"}, format="json")
        ok = self.client.post("/api/day-closing/", {"counts": [{"value": "0.25", "quantity": 3}]}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
