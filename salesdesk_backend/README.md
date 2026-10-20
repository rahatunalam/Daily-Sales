# Sales Desk backend

Django 6.1.2 + Django REST framework + PostgreSQL. It serves the Sales Desk app:
Daily Sales, Due, Company Payment, Day Closing, Report, Settings, login and profile.

## Run it

```bash
docker compose up -d db                 # PostgreSQL 17 on localhost:5432
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && export $(grep -v '^#' .env | xargs)
python manage.py migrate                # also seeds bKash, Nagad and the notes 1000 to 10
python manage.py seed_demo              # users OWNER/owner1234 and RAHAT/1234, a customer, two companies
python manage.py runserver
```

- Interactive docs: `http://localhost:8000/api/docs/` (OpenAPI at `/api/schema/`)
- Tests (use a real PostgreSQL): `python manage.py test tests`
- Time zone is `Asia/Dhaka`; "today" and every daily total use that zone.

## Authentication

Token based. Send `Authorization: Token <token>` on every call except login.
Errors always look like `{"detail": "...", "errors": {field: [...]}}`.

| Method | URL | Purpose |
| --- | --- | --- |
| POST | `/api/auth/login/` | `{name, password}` returns `{token, profile}`. Name is not case sensitive. Inactive users are refused. 10 tries a minute. |
| POST | `/api/auth/logout/` | Deletes the token. |
| GET | `/api/auth/me/` | Profile icon: `{id, name, role, designation}`. |
| POST | `/api/auth/change-password/` | `{current_password, new_password, confirm_password}` (BR-14). Returns a new token. |

## Endpoints by screen

Lists are paginated (`page`, `page_size`) except MFS accounts and denominations.

**Daily Sales**

| Method | URL | Notes |
| --- | --- | --- |
| GET / PUT | `/api/opening-balance/?date=` | PUT `{amount, date?}`. Without a value the previous closing is used (BR-08). Refused once the day is closed. |
| POST | `/api/transactions/` | `{method, amount, wallet?, customer?}`. Methods: `CASH, MFS, CARD, DUE, DUE_RECEIVED, REFUND`. MFS needs `wallet`; DUE and DUE_RECEIVED need `customer`; REFUND customer is optional. |
| GET | `/api/transactions/` | Filters `date, from, to, method, customer`. Newest first. Lines cannot be edited or deleted. |
| GET | `/api/daily-summary/?date=` | Rows (Cash, each wallet, Card, Due, Due received, Refund), `total_sales_with_due`, `total_sales_without_due`, opening and closing balance. |
| GET | `/api/mfs-accounts/` | Wallet choice for MFS. |

**Due and customers**

| Method | URL | Notes |
| --- | --- | --- |
| GET | `/api/customers/?search=&has_due=true` | Search by part of a name or phone. Each row has `due_total, received_total, remaining`. |
| POST | `/api/customers/` | Add Customer `{name, phone}`. Phone 6+ digits; name and phone must be unique (BR-12). |
| POST | `/api/customers/{id}/receive/` | `{amount}` cannot exceed the remaining due (BR-03). |
| GET | `/api/customers/{id}/history/` | View: date, due, paid, running remaining (newest first). |
| GET | `/api/customers/due-summary/` | Cards: `total_received`, `total_remaining`. |

**Company Payment** (owner and manager)

| Method | URL | Notes |
| --- | --- | --- |
| GET / POST | `/api/companies/?search=` | Company list and details table (`bill_total, paid_total, due`). POST `{name}` is Add Company. |
| GET | `/api/companies/summary/` | `total_due` for the Total due remaining card. |
| POST | `/api/company-entries/` | Bill Amount page `{company, bill_amount, paid_amount}`. `due_amount = bill - paid`. Paid cannot exceed bill plus earlier due (BR-09). |
| POST | `/api/companies/{id}/pay/` | `{amount}` cannot exceed the due. |
| GET | `/api/companies/{id}/history/` | Remaining due and every entry (oldest first) with running remaining. |

**Day Closing** (owner and manager)

| Method | URL | Notes |
| --- | --- | --- |
| GET | `/api/day-closing/?date=` | Opening, closing, one count row per denomination, counted total, difference, `closed`. |
| POST | `/api/day-closing/` | `{date?, counts: [{value, quantity}]}`. Closes only when the total equals the closing balance, else 400 "Short by / Over by" (BR-11). A closed day returns 409. |

**Report** (owner and manager)

| Method | URL | Notes |
| --- | --- | --- |
| GET | `/api/reports/daily/?preset=today` (or `yesterday`, `last7`) or `?from=&to=` | One row per active day, newest first: `opening_balance, sales_received (cash + MFS + card), due_receive, refund, company_paid, closing_balance, due (credit given, not cash)`. Running `remaining_due` and `company_*` figures stay in each row for the Due and Company screens. |
| GET | `/api/reports/daily/details/?date=YYYY-MM-DD` | Details button: `sales_and_due` (rows, `total_sales_with_due`, `total_sales_without_due`) and `company_payments` (`company_name`, `paid_amount`, summed per company, paid above 0 only) with `company_paid_total`. Refund is a positive number; show it as a minus. |

**Settings** (everyone reads, owner changes)

| Method | URL | Notes |
| --- | --- | --- |
| GET / POST / PATCH | `/api/mfs-accounts/` | Add MFS `{name, account}`. |
| GET / POST / DELETE | `/api/denominations/` | Money Setting `{value}`; decimals such as 0.25 are allowed. |
| GET / POST / PATCH | `/api/users/` | Add User `{name, role, designation, password}`; owner only. Blank password on PATCH keeps the old one. |
| POST | `/api/users/{id}/toggle-active/` | Activate or deactivate; you cannot deactivate yourself. |

## Business rules in code

`ledger/services.py` holds the money rules:

```
Closing = Opening + Cash + MFS + Card + Due received - Refund - Company payments
Total sales without due = Cash + MFS + Card + Due received - Refund
Total sales with due    = Total sales without due + Due sales
```

Due sales never change the closing balance. Overpaying a due or a company bill is blocked inside a database
transaction with a row lock, so two clicks at once cannot overpay.

## Roles

| Role | Can use |
| --- | --- |
| Owner | Everything, including users, MFS and denominations |
| Manager | Sales, dues, Company Payment, Day Closing, Report |
| Cashier | Sales, customers, dues, summary |

This matrix is one open question in the BRD; change it in `accounts/permissions.py` and the views.

## Notes

- Report and balances are calculated from the ledger on each call. That is fine for one shop; cache or
  pre-compute daily rows if the history grows to many years.
- Closing a day blocks later opening-balance changes for that day. It does not yet block new sales on a closed day.
- Passwords use Django's hashers. The minimum length is 4 (`MIN_PASSWORD_LENGTH`); raise it for production.
