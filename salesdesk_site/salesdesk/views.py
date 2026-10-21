import datetime
from decimal import Decimal

from django.db import transaction as db_tx
from django.db.models import Sum, F, Q, Exists, OuterRef, Value, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from django.shortcuts import render
from django.utils import timezone
from rest_framework import serializers, viewsets, mixins
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS
from rest_framework.response import Response

from .models import (User, MfsAccount, Denomination, Customer, Transaction,
                     OpeningBalance, DayClosing, Company, CompanyEntry)
from .utils import dec

# =====================================================================
# 1. PAGES: each one just returns its template; the JS builds the screen
# =====================================================================
def index(request):           return render(request, 'index.html')
def login_page(request):      return render(request, 'login.html')
def daily_sales_page(request):    return render(request, 'daily_sales.html')
def due_page(request):            return render(request, 'due.html')
def whole_sale_page(request):     return render(request, 'whole_sale.html')
def company_payment_page(request): return render(request, 'company_payment.html')
def day_closing_page(request):    return render(request, 'day_closing.html')
def report_page(request):         return render(request, 'report.html')
def settings_page(request):       return render(request, 'settings.html')

# =====================================================================
# 2. ROLE PERMISSIONS (same table as ACCESS in auth.js)
# =====================================================================
class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == 'owner')

class IsManagerUp(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role in ('owner', 'manager'))

class OwnerWriteOnly(BasePermission):
    """Everyone signed in can read; only the owner can change."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.method in SAFE_METHODS or request.user.role == 'owner'

class Conflict(APIException):
    status_code = 409
    default_detail = 'This day is already closed.'

def parse_date(s):
    if not s:
        return timezone.localdate()
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        raise ValidationError('Pick a date (YYYY-MM-DD).')

# =====================================================================
# 3. LOGIN AND USERS
# =====================================================================
def profile(u):
    return {'id': u.id, 'name': u.name, 'role': u.role, 'designation': u.designation}

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    name = str(request.data.get('name') or '').strip()
    user = User.objects.filter(name__iexact=name).first()
    if not user or not user.check_password(request.data.get('password') or ''):
        raise ValidationError('Wrong name or password.')
    if not user.is_active:
        raise ValidationError('This user is inactive. Ask the owner to activate it.')
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'profile': profile(user)})

@api_view(['POST'])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=204)

@api_view(['GET'])
def me(request):
    return Response(profile(request.user))

@api_view(['POST'])
def change_password(request):
    b, user = request.data, request.user
    if not user.check_password(b.get('current_password') or ''):
        raise ValidationError('Current password is wrong.')
    new = str(b.get('new_password') or '')
    if len(new) < 4:
        raise ValidationError('New password must be at least 4 characters.')
    if new == b.get('current_password'):
        raise ValidationError('New password must be different from the current one.')
    if new != b.get('confirm_password'):
        raise ValidationError('New password and confirm password do not match.')
    user.set_password(new)
    user.save()
    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    return Response({'detail': 'Password changed.', 'token': token.key})

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'role', 'designation', 'is_active', 'password']
        read_only_fields = ['is_active']

    def create(self, data):
        password = data.pop('password', '')
        if not password:
            raise ValidationError('Password is required.')
        data.setdefault('designation', data.get('role', ''))
        return User.objects.create_user(password=password, **data)

    def update(self, instance, data):
        password = data.pop('password', '')
        for k, v in data.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsOwner]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        if user.pk == request.user.pk:
            raise ValidationError('You cannot deactivate yourself.')
        user.is_active = not user.is_active
        user.save()
        return Response(self.get_serializer(user).data)

# =====================================================================
# 4. BALANCE RULES (daily figures, summary)
# =====================================================================
D0 = Decimal('0')
ZERO = Value(D0, output_field=DecimalField())
METHODS = ['CASH', 'MFS', 'CARD', 'DUE', 'DUE_RECEIVED', 'REFUND', 'WHOLESALE', 'WHOLESALE_RECEIVED']
LEDGER = {'due': ('DUE', 'DUE_RECEIVED'), 'wholesale': ('WHOLESALE', 'WHOLESALE_RECEIVED')}
FLAG = {'due': 'due_ledger', 'wholesale': 'wholesale_ledger'}

def _blank():
    return {**{m: D0 for m in METHODS}, 'bill': D0, 'paid': D0}

def all_figures():
    """{date: {CASH.., bill, paid, opening, closing}} with the balance carried day to day.
    .order_by() clears Meta.ordering, which would otherwise break the GROUP BY."""
    days = {}
    slot = lambda d: days.setdefault(d, _blank())

    rows = (Transaction.objects.annotate(day=TruncDate('occurred_at'))
            .values('day', 'method').annotate(total=Sum('amount')).order_by())
    for r in rows:
        slot(r['day'])[r['method']] += r['total']

    rows = (CompanyEntry.objects.annotate(day=TruncDate('created_at'))
            .values('day').annotate(b=Sum('bill_amount'), p=Sum('paid_amount')).order_by())
    for r in rows:
        s = slot(r['day'])
        s['bill'] += r['b']
        s['paid'] += r['p']

    openings = {o.date: o.amount for o in OpeningBalance.objects.all()}
    for d in openings:
        slot(d)
    slot(timezone.localdate())

    out, balance = {}, D0
    for d in sorted(days):
        s = days[d]
        opening = openings.get(d, balance)
        closing = (opening + s['CASH'] + s['MFS'] + s['CARD'] + s['DUE_RECEIVED']
                   + s['WHOLESALE_RECEIVED'] - s['REFUND'] - s['paid'])
        balance = closing
        out[d] = {**s, 'date': d, 'opening': opening, 'closing': closing}
    return out

def figure_for(d):
    figs = all_figures()
    if d in figs:
        return figs[d]
    earlier = [k for k in figs if k < d]
    o = figs[max(earlier)]['closing'] if earlier else D0
    return {**_blank(), 'date': d, 'opening': o, 'closing': o}

def summary_for(d):
    f = figure_for(d)
    rows = [{'label': 'Cash', 'amount': f['CASH']}]
    for w in MfsAccount.objects.order_by('id'):
        amt = (Transaction.objects.filter(method='MFS', wallet=w, occurred_at__date=d)
               .aggregate(s=Sum('amount'))['s'] or D0)
        rows.append({'label': w.name, 'amount': amt})
    rows += [
        {'label': 'Card', 'amount': f['CARD']},
        {'label': 'Due', 'amount': f['DUE']},
        {'label': 'Due received', 'amount': f['DUE_RECEIVED']},
        {'label': 'Whole Sale', 'amount': f['WHOLESALE']},
        {'label': 'Whole Sale received', 'amount': f['WHOLESALE_RECEIVED']},
        {'label': 'Refund', 'amount': f['REFUND']},
    ]
    # Whole Sale received is part of the Whole Sale bill, so it is not added again.
    without = f['CASH'] + f['MFS'] + f['CARD'] + f['DUE_RECEIVED'] - f['REFUND']
    return {'date': d, 'rows': rows,
            'total_sales_without_due': without,
            'total_sales_with_due': without + f['DUE'] + f['WHOLESALE'],
            'opening_balance': f['opening'], 'closing_balance': f['closing']}

# =====================================================================
# 5. SETTINGS DATA: MFS wallets and note/coin values
# =====================================================================
class MfsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MfsAccount
        fields = ['id', 'name', 'account']

class MfsViewSet(viewsets.ModelViewSet):
    queryset = MfsAccount.objects.order_by('id')
    serializer_class = MfsSerializer
    permission_classes = [OwnerWriteOnly]
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

class DenominationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Denomination
        fields = ['id', 'value']

class DenominationViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                          mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Denomination.objects.all()
    serializer_class = DenominationSerializer
    permission_classes = [OwnerWriteOnly]
    pagination_class = None

# =====================================================================
# 6. CUSTOMERS (Due and Whole Sale) AND TRANSACTIONS (Daily Sales)
# =====================================================================
def customer_qs(ledger):
    sale, got = LEDGER[ledger]
    return Customer.objects.annotate(
        due_total=Coalesce(Sum('transactions__amount', filter=Q(transactions__method=sale)),
                           ZERO, output_field=DecimalField()),
        received_total=Coalesce(Sum('transactions__amount', filter=Q(transactions__method=got)),
                                ZERO, output_field=DecimalField()),
    ).annotate(remaining=F('due_total') - F('received_total'))

def cust_out(c):
    return {'id': c.id, 'name': c.name, 'phone': c.phone, 'due_total': c.due_total,
            'received_total': c.received_total, 'remaining': c.remaining}

def receive_payment(customer, amount, ledger, user):
    if amount <= 0:
        raise ValidationError('Enter the amount received.')
    remaining = customer_qs(ledger).get(pk=customer.pk).remaining
    if amount > remaining:
        raise ValidationError(f'That is more than the {remaining:.2f} due.')
    return Transaction.objects.create(method=LEDGER[ledger][1], amount=amount,
                                      customer=customer, created_by=user)

class TransactionSerializer(serializers.ModelSerializer):
    wallet_name = serializers.CharField(source='wallet.name', read_only=True, default=None)
    customer_name = serializers.CharField(source='customer.name', read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = ['id', 'occurred_at', 'method', 'wallet', 'wallet_name',
                  'customer', 'customer_name', 'amount']

class CustomerViewSet(viewsets.GenericViewSet):
    def get_ledger(self, request, body=False):
        src = request.data if body else request.query_params
        ledger = src.get('ledger') or 'due'
        if ledger not in LEDGER:
            raise ValidationError('Unknown ledger.')
        return ledger

    def list(self, request):
        ledger = self.get_ledger(request)
        qs = Customer.objects.all()
        if request.query_params.get('scope') == 'ledger':
            has_tx = Transaction.objects.filter(customer=OuterRef('pk'), method__in=LEDGER[ledger])
            qs = qs.filter(Q(**{FLAG[ledger]: True}) | Exists(has_tx))
        s = (request.query_params.get('search') or '').strip()
        if s:
            digits = ''.join(ch for ch in s if ch.isdigit())
            cond = Q(name__icontains=s)
            if digits:
                cond |= Q(phone_digits__contains=digits)
            qs = qs.filter(cond)
        # annotate AFTER filtering, so the filters do not inflate the sums
        qs = customer_qs(ledger).filter(pk__in=qs.values('pk')).order_by('name')
        if str(request.query_params.get('has_due')).lower() in ('1', 'true', 'yes'):
            qs = qs.filter(remaining__gt=0)
        page = self.paginate_queryset(qs)
        return self.get_paginated_response([cust_out(c) for c in page])

    def create(self, request):
        b = request.data
        name, phone = str(b.get('name') or '').strip(), str(b.get('phone') or '').strip()
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if not name:
            raise ValidationError('Enter the customer name.')
        if len(digits) < 6:
            raise ValidationError('Enter a valid phone number.')
        if Customer.objects.filter(name__iexact=name).exists():
            raise ValidationError('A customer with this name already exists.')
        if Customer.objects.filter(phone_digits=digits).exists():
            raise ValidationError('A customer with this phone number already exists.')
        ledger = b.get('ledger') if b.get('ledger') in LEDGER else None
        c = Customer.objects.create(name=name, phone=phone, **({FLAG[ledger]: True} if ledger else {}))
        return Response(cust_out(customer_qs(ledger or 'due').get(pk=c.pk)), status=201)

    @action(detail=False, methods=['get'], url_path='due-summary')
    def due_summary(self, request):
        ledger = self.get_ledger(request)
        t = customer_qs(ledger).aggregate(r=Sum('received_total'), m=Sum('remaining'))
        return Response({'total_received': t['r'] or 0, 'total_remaining': t['m'] or 0})

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        ledger = self.get_ledger(request)
        c = customer_qs(ledger).filter(pk=pk).first()
        if not c:
            return Response({'detail': 'Not found.'}, status=404)
        run, rows = D0, []
        for t in Transaction.objects.filter(customer=c, method__in=LEDGER[ledger]).order_by('occurred_at', 'id'):
            due = t.amount if t.method == LEDGER[ledger][0] else D0
            paid = D0 if due else t.amount
            run += due - paid
            rows.append({'date': t.occurred_at, 'due': due, 'paid': paid, 'remaining': run})
        rows.reverse()                                   # newest first
        return Response({'customer': {'id': c.id, 'name': c.name, 'phone': c.phone},
                         'remaining': c.remaining, 'rows': rows})

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        ledger = self.get_ledger(request, body=True)
        c = Customer.objects.filter(pk=pk).first()
        if not c:
            return Response({'detail': 'Not found.'}, status=404)
        t = receive_payment(c, dec(request.data.get('amount')), ledger, request.user)
        return Response(TransactionSerializer(t).data)

class TransactionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        q, p = Transaction.objects.select_related('wallet', 'customer'), self.request.query_params
        if p.get('date'):
            q = q.filter(occurred_at__date=parse_date(p['date']))
        if p.get('from'):
            q = q.filter(occurred_at__date__gte=parse_date(p['from']))
        if p.get('to'):
            q = q.filter(occurred_at__date__lte=parse_date(p['to']))
        if p.get('method'):
            q = q.filter(method=p['method'])
        return q

    @db_tx.atomic
    def create(self, request):
        b = request.data
        method, amount = b.get('method'), dec(b.get('amount'))
        if method not in dict(Transaction.METHODS):
            raise ValidationError('Pick a payment method.')
        if amount <= 0:
            raise ValidationError('Enter an amount first.')
        wallet = customer = None
        if method == 'MFS':
            wallet = MfsAccount.objects.filter(pk=b.get('wallet')).first()
            if not wallet:
                raise ValidationError('Pick the wallet (bKash, Nagad...).')
        if method in ('DUE', 'WHOLESALE', 'DUE_RECEIVED', 'REFUND'):
            customer = Customer.objects.filter(pk=b.get('customer')).first()
            if not customer and method != 'REFUND':      # the customer is optional on a refund
                raise ValidationError('Search and pick the customer.')
        if method == 'DUE_RECEIVED':
            return Response(TransactionSerializer(
                receive_payment(customer, amount, 'due', request.user)).data)
        paid = dec(b.get('paid_amount')) if method == 'WHOLESALE' else D0
        if paid > amount:
            raise ValidationError('Paid amount cannot be more than the bill amount.')
        t = Transaction.objects.create(method=method, amount=amount, wallet=wallet,
                                       customer=customer, created_by=request.user)
        if paid > 0:
            Transaction.objects.create(method='WHOLESALE_RECEIVED', amount=paid,
                                       customer=customer, created_by=request.user)
        return Response(TransactionSerializer(t).data, status=201)

# =====================================================================
# 7. OPENING BALANCE, SUMMARY, DAY CLOSING, REPORTS
# =====================================================================
@api_view(['GET', 'PUT'])
def opening_balance(request):
    if request.method == 'PUT':
        d = parse_date(request.data.get('date'))
        if DayClosing.objects.filter(date=d).exists():
            raise Conflict()
        amount = dec(request.data.get('amount'))
        if amount < 0:
            raise ValidationError('Enter a valid amount.')
        OpeningBalance.objects.update_or_create(date=d, defaults={'amount': amount})
        return Response({'date': d, 'amount': amount, 'explicit': True})
    d = parse_date(request.query_params.get('date'))
    return Response({'date': d, 'amount': figure_for(d)['opening'],
                     'explicit': OpeningBalance.objects.filter(date=d).exists()})

@api_view(['GET'])
def daily_summary(request):
    return Response(summary_for(parse_date(request.query_params.get('date'))))

@api_view(['GET', 'POST'])
@permission_classes([IsManagerUp])
def day_closing(request):
    src = request.data if request.method == 'POST' else request.query_params
    d = parse_date(src.get('date'))
    f = figure_for(d)
    closed = DayClosing.objects.filter(date=d).first()
    if request.method == 'POST':
        if closed:
            raise Conflict()
        allowed = {x.value for x in Denomination.objects.all()}
        counts, total = {}, D0
        for c in request.data.get('counts') or []:
            value = dec(c.get('value'))
            if value not in allowed:
                raise ValidationError(f'{c.get("value")} is not a denomination in Money Setting.')
            qty = int(c.get('quantity') or 0)
            counts[str(value)] = counts.get(str(value), 0) + qty
            total += value * qty
        diff = total - f['closing']
        if diff != 0:
            raise ValidationError(f'{"Over by" if diff > 0 else "Short by"} {abs(diff):.2f}. '
                                  'The total must match the closing balance.')
        DayClosing.objects.create(date=d, counted_total=total, counts=counts, closed_by=request.user)
        return Response({'date': d, 'closing_balance': f['closing'], 'counted_total': total, 'closed': True})
    saved = {Decimal(k): v for k, v in (closed.counts if closed else {}).items()}
    counts = [{'value': x.value, 'quantity': saved.get(x.value, 0)} for x in Denomination.objects.all()]
    total = closed.counted_total if closed else D0
    return Response({'date': d, 'opening_balance': f['opening'], 'closing_balance': f['closing'],
                     'counts': counts, 'counted_total': total,
                     'difference': total - f['closing'], 'closed': bool(closed)})

@api_view(['GET'])
@permission_classes([IsManagerUp])
def daily_report(request):
    p, today = request.query_params, timezone.localdate()
    one = datetime.timedelta(days=1)
    start = end = today
    if p.get('preset') == 'yesterday':
        start = end = today - one
    elif p.get('preset') == 'last7':
        start = today - 6 * one
    elif p.get('from') or p.get('to'):
        start, end = parse_date(p.get('from')), parse_date(p.get('to'))
    rows = []
    for d, x in sorted(all_figures().items(), reverse=True):
        if start <= d <= end:
            rows.append({'date': d, 'day': d.strftime('%a'), 'opening_balance': x['opening'],
                         'sales_received': x['CASH'] + x['MFS'] + x['CARD'],
                         'due_receive': x['DUE_RECEIVED'], 'whole_sale_received': x['WHOLESALE_RECEIVED'],
                         'refund': x['REFUND'], 'company_paid': x['paid'],
                         'closing_balance': x['closing'], 'due': x['DUE'] + x['WHOLESALE']})
    return Response({'from': start, 'to': end, 'rows': rows})

@api_view(['GET'])
@permission_classes([IsManagerUp])
def daily_report_details(request):
    d = parse_date(request.query_params.get('date'))
    s = summary_for(d)
    pays = (CompanyEntry.objects.filter(created_at__date=d, paid_amount__gt=0)
            .values('company', 'company__name').annotate(paid=Sum('paid_amount'))
            .order_by('company__name'))
    company_payments = [{'company_id': r['company'], 'company_name': r['company__name'],
                         'paid_amount': r['paid']} for r in pays]
    return Response({'date': d,
                     'sales_and_due': {'rows': s['rows'],
                                       'total_sales_with_due': s['total_sales_with_due'],
                                       'total_sales_without_due': s['total_sales_without_due']},
                     'company_payments': company_payments,
                     'company_paid_total': sum((c['paid_amount'] for c in company_payments), D0)})

# =====================================================================
# 8. COMPANY PAYMENT
# =====================================================================
def company_qs():
    return Company.objects.annotate(
        bill_total=Coalesce(Sum('entries__bill_amount'), ZERO, output_field=DecimalField()),
        paid_total=Coalesce(Sum('entries__paid_amount'), ZERO, output_field=DecimalField()),
    ).annotate(due=F('bill_total') - F('paid_total')).order_by('name')

class CompanySerializer(serializers.ModelSerializer):
    bill_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    paid_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'bill_total', 'paid_total', 'due']

class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsManagerUp]
    search_fields = ['name']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return company_qs()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(self.get_serializer(company_qs().get(pk=obj.pk)).data, status=201)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        t = CompanyEntry.objects.aggregate(b=Sum('bill_amount'), p=Sum('paid_amount'))
        b, p = t['b'] or 0, t['p'] or 0
        return Response({'total_bill': b, 'total_paid': p, 'total_due': b - p})

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        company = self.get_object()
        amount = dec(request.data.get('amount'))
        if amount <= 0:
            raise ValidationError('Enter the paid amount.')
        if amount > company.due:
            raise ValidationError(f'That is more than the {company.due:.2f} due.')
        CompanyEntry.objects.create(company=company, paid_amount=amount)
        return Response({'company': company.id, 'paid_amount': amount})

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        company = self.get_object()
        rows, running = [], D0
        for e in company.entries.all():
            running += e.bill_amount - e.paid_amount
            rows.append({'date': e.created_at, 'bill_amount': e.bill_amount,
                         'paid_amount': e.paid_amount, 'remaining': running})
        return Response({'company': {'id': company.id, 'name': company.name},
                         'remaining_due': running, 'rows': rows})

class CompanyEntryViewSet(viewsets.GenericViewSet):
    permission_classes = [IsManagerUp]
    queryset = CompanyEntry.objects.all()

    def create(self, request):
        co = Company.objects.filter(pk=request.data.get('company')).first()
        if not co:
            raise ValidationError('Select a company.')
        bill, paid = dec(request.data.get('bill_amount')), dec(request.data.get('paid_amount'))
        if bill <= 0:
            raise ValidationError('Enter the bill amount.')
        limit = bill + company_qs().get(pk=co.pk).due
        if paid > limit:
            raise ValidationError(f'Paid amount is more than the total due of {limit:.2f}.')
        e = CompanyEntry.objects.create(company=co, bill_amount=bill, paid_amount=paid)
        return Response({'id': e.id, 'company': co.id, 'company_name': co.name,
                         'bill_amount': bill, 'paid_amount': paid, 'due_amount': bill - paid},
                        status=201)