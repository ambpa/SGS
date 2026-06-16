# members/views_subscriptions.py
# Fase 3-aggancio/1 — creazione abbonamento + pagamento nella stessa schermata.

from functools import wraps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Member, Subscription, Payment
from .forms import SubscriptionWithPaymentForm
from .forms import SubscriptionWithPaymentAndMemberForm

def office_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if u.is_staff or u.is_superuser or getattr(u, "is_office", False):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped


@office_required
def add_subscription_with_payment(request, member_id):
    """
    Crea un abbonamento per il socio e registra contestualmente il pagamento.
    L'importo è bloccato dal prezzo del pacchetto; lo sconto è inserito a mano.
    Relazione uno-a-uno: un abbonamento ha un solo pagamento.
    """
    member = get_object_or_404(Member, id=member_id)

    if request.method == 'POST':
        form = SubscriptionWithPaymentForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            package = cd['package']

            # 1) crea l'abbonamento (tipo/settore/fine dedotti dal pacchetto nel save)
            subscription = Subscription(
                member=member,
                package=package,
                start_date=cd['start_date'],
            )
            subscription.save()

            # 2) crea il pagamento collegato (uno-a-uno)
            #    importo bloccato dal pacchetto; sconto a parte
            Payment.objects.create(
                member=member,
                subscription=subscription,
                payment_date=cd.get('payment_date'),
                amount=package.price,
                discount=cd.get('discount') or 0,
                payment_mode=cd.get('payment_mode') or '',
                is_paid=cd.get('is_paid', False),
            )

            messages.success(
                request,
                f"Abbonamento «{package.name}» creato"
                + (" e pagamento registrato." if cd.get('is_paid') else " (pagamento da saldare).")
            )
            return redirect('members:subscription_list', member_id=member.id)
    else:
        form = SubscriptionWithPaymentForm()

    return render(request, 'subscriptions/subscription_with_payment_form.html', {
        'form': form, 'member': member,
    })

@office_required
def add_subscription_with_payment_admin(request):
    """
    Come add_subscription_with_payment, ma parte SENZA socio: lo si sceglie
    nel form. Usata dal menu laterale "Abbonamenti".
    """
    if request.method == 'POST':
        form = SubscriptionWithPaymentAndMemberForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            member = cd['member']
            package = cd['package']

            subscription = Subscription(
                member=member,
                package=package,
                start_date=cd['start_date'],
            )
            subscription.save()

            Payment.objects.create(
                member=member,
                subscription=subscription,
                payment_date=cd.get('payment_date'),
                amount=package.price,
                discount=cd.get('discount') or 0,
                payment_mode=cd.get('payment_mode') or '',
                is_paid=cd.get('is_paid', False),
            )

            messages.success(
                request,
                f"Abbonamento «{package.name}» creato per {member}"
                + (" e pagamento registrato." if cd.get('is_paid') else " (pagamento da saldare).")
            )
            return redirect('members:subscription_list', member_id=member.id)
    else:
        form = SubscriptionWithPaymentAndMemberForm()

    return render(request, 'subscriptions/subscription_with_payment_admin_form.html', {
        'form': form,
    })