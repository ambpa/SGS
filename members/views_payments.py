# members/views_payments.py
# Fase 3a — Pagamenti / rate. Protetto da office_required.

from functools import wraps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Member, Payment, Subscription
from .forms import PaymentForm
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q#, Sum

def office_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if u.is_staff or u.is_superuser or getattr(u, "is_office", False):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped


# ---------------------------------------------------------------------------
#  STORICO PAGAMENTI DI UN SOCIO
# ---------------------------------------------------------------------------
@office_required
def payment_list(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    payments = member.payments.all().order_by('-due_date', '-payment_date')

    # Totali utili in testa alla pagina
    total_paid = sum((p.net_amount for p in payments if p.is_paid), 0)
    total_due = sum((p.net_amount for p in payments if not p.is_paid), 0)

    return render(request, 'payments/payment_list.html', {
        'member': member,
        'payments': payments,
        'total_paid': total_paid,
        'total_due': total_due,
    })


# ---------------------------------------------------------------------------
#  AGGIUNGI PAGAMENTO (dalla scheda socio)
# ---------------------------------------------------------------------------
@office_required
def payment_add(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    messages.info(
        request,
        "I pagamenti si registrano creando un abbonamento. "
        "Usa «Nuovo abbonamento» dalla scheda del socio."
    )
    return redirect('members:payment_list', member_id=member.id)


@office_required
def payment_edit(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    member = payment.member
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment, member=member)
        if form.is_valid():
            form.save()
            messages.success(request, "Pagamento aggiornato.")
            return redirect('members:payment_list', member_id=member.id)
    else:
        form = PaymentForm(instance=payment, member=member)
    return render(request, 'payments/payment_form.html', {
        'form': form, 'member': member, 'title': 'Modifica pagamento', 'object': payment,
    })


@office_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    member_id = payment.member.id
    if request.method == 'POST':
        payment.delete()
        messages.success(request, "Pagamento eliminato.")
        return redirect('members:payment_list', member_id=member_id)
    return render(request, 'payments/payment_confirm_delete.html', {
        'payment': payment, 'member': payment.member,
    })


@office_required
def payment_toggle_paid(request, pk):
    """Segna come pagato / non pagato con un click."""
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        payment.is_paid = not payment.is_paid
        payment.save()
        stato = "pagato" if payment.is_paid else "non pagato"
        messages.success(request, f"Rata segnata come {stato}.")
    return redirect('members:payment_list', member_id=payment.member.id)


@office_required
def payment_all(request):
    """Tutti i pagamenti di tutti i soci, con filtri e totali."""
    today = timezone.now().date()
    status = request.GET.get('status', '')      # paid / unpaid / overdue
    q = request.GET.get('q', '').strip()

    payments = Payment.objects.select_related('member', 'subscription').all()

    if q:
        payments = payments.filter(
            Q(member__first_name__icontains=q) |
            Q(member__last_name__icontains=q) |
            Q(member__card_number__icontains=q)
        )

    if status == 'paid':
        payments = payments.filter(is_paid=True)
    elif status == 'unpaid':
        payments = payments.filter(is_paid=False)
    elif status == 'overdue':
        payments = payments.filter(is_paid=False, due_date__lt=today)

    payments = payments.order_by('-due_date', '-payment_date')

    # Totali (sull'intero filtro corrente)
    tot_paid = sum((p.net_amount for p in payments if p.is_paid), 0)
    tot_unpaid = sum((p.net_amount for p in payments if not p.is_paid), 0)

    return render(request, 'payments/payment_all.html', {
        'payments': payments,
        'tot_paid': tot_paid,
        'tot_unpaid': tot_unpaid,
        'status': status,
        'q': q,
        'active_nav': 'payments',
        'today': today,
    })


@office_required
def payment_due(request):
    """
    Cruscotto scadenze: rate non pagate o abbonamenti in scadenza
    nei prossimi N giorni (default 30).
    """
    today = timezone.now().date()
    giorni = 30
    limite = today + timedelta(days=giorni)

    # Rate non pagate (insoluti) — già scadute o in arrivo
    insoluti = Payment.objects.select_related('member').filter(
        is_paid=False
    ).order_by('due_date')

    # Abbonamenti in scadenza entro N giorni
    subs_in_scadenza = Subscription.objects.select_related('member', 'package').filter(
        end_date__gte=today, end_date__lte=limite
    ).order_by('end_date')

    return render(request, 'payments/payment_due.html', {
        'insoluti': insoluti,
        'subs_in_scadenza': subs_in_scadenza,
        'giorni': giorni,
        'today': today,
        'active_nav': 'payments',
    })
