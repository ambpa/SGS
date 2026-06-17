# members/views.py
import json
from datetime import date,timedelta
from functools import wraps

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Max, Count
from django.db.models.functions import TruncDay
from django.forms import modelformset_factory
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

from .models import Member, MemberDocument, Subscription
from .forms import (
    MemberCreationForm, MemberChangeForm, MemberDocumentForm,
    MemberDocumentFormSet, SubscriptionForm, AdminMemberDocumentForm,
)


# ---------------------------------------------------------------------------
#  CONTROLLO ACCESSI
# ---------------------------------------------------------------------------
def office_required(view_func):
    """
    Consente l'accesso solo al personale di segreteria/amministratore.
    Sostituisce @staff_member_required (che reindirizza all'admin) con un
    controllo coerente con l'app. Un socio normale riceve 403.
    """
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if user.is_staff or user.is_superuser or getattr(user, "is_office", False):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped


def _is_office(user):
    return user.is_staff or user.is_superuser or getattr(user, "is_office", False)


# ---------------------------------------------------------------------------
#  DASHBOARD
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    user = request.user

    # 🟩 CASO 1: Admin o staff
    if _is_office(user):
        search_query = request.GET.get('q', '')

        members_qs = Member.objects.all()
        if search_query:
            members_qs = members_qs.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        paginator = Paginator(members_qs.order_by('last_name', 'first_name'), 10)
        page_number = request.GET.get('page')
        members = paginator.get_page(page_number)

        total_members = Member.objects.count()
        active_members = Member.objects.filter(is_active=True).count()
        total_documents = MemberDocument.objects.count()

        today = timezone.now().date()
        expired_certificates = 0
        active_certificates = 0

        expired_certificates = 0
        active_certificates = 0
        suspended_certificates = 0

        for member in Member.objects.prefetch_related('documents', 'subscriptions'):
            latest_cert = (
                member.documents
                .filter(document_type='MEDICAL_CERTIFICATE')
                .order_by('-expiration_date')
                .first()
            )
            if latest_cert:
                if latest_cert.expiration_date and latest_cert.expiration_date < today:
                    expired_certificates += 1
                else:
                    active_certificates += 1
            else:
                # Nessun certificato caricato: "sospeso" SOLO se ha almeno un abbonamento
                if member.subscriptions.exists():
                    suspended_certificates += 1

        from collections import defaultdict

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        SCADENZA_GIORNI = 30  # soglia "in scadenza" (configurabile in futuro)
        limite = today + timedelta(days=SCADENZA_GIORNI)

        active_subscriptions = 0
        expired_subscriptions = 0
        expiring_subscriptions = 0

        for sub in Subscription.objects.all():
            if sub.start_date and sub.start_date > today:
                continue  # non ancora attivo
            if sub.end_date and sub.end_date < today:
                expired_subscriptions += 1
            else:
                active_subscriptions += 1
                # in scadenza: attivo e fine entro la soglia
                if sub.end_date and today <= sub.end_date <= limite:
                    expiring_subscriptions += 1

        total_subscriptions = Subscription.objects.count()

        member_stats = (
            Member.objects
            .annotate(day=TruncDay('date_joined'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        labels = [m['day'].strftime('%d %b %Y') for m in member_stats if m['day']]
        data = [m['count'] for m in member_stats if m['day']]

        subs = Subscription.objects.all()
        if start_date:
            subs = subs.filter(start_date__gte=parse_date(start_date))
        if end_date:
            subs = subs.filter(start_date__lte=parse_date(end_date))

        subscription_stats = (
            subs
            .annotate(date=TruncDay('start_date'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        sub_labels = [s['date'].strftime('%d %b %Y') for s in subscription_stats if s['date']]
        sub_data = [s['count'] for s in subscription_stats if s['date']]

        category_stats = (
            Subscription.objects
            .values('sector__name')
            .annotate(count=Count('id'))
        )
        cat_labels = [c['sector__name'] or '—' for c in category_stats]
        cat_data = [c['count'] for c in category_stats]

        context = {
            'members': members,
            'total_members': total_members,
            'active_members': active_members,
            'total_documents': total_documents,
            'expired_certificates': expired_certificates,
            'active_certificates': active_certificates,
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'expired_subscriptions': expired_subscriptions,
            'expiring_subscriptions': expiring_subscriptions,
            'total_subscriptions': total_subscriptions,
            'scadenza_giorni': SCADENZA_GIORNI,
            'labels': json.dumps(labels),
            'data': json.dumps(data),
            'sub_labels': sub_labels,
            'sub_data': sub_data,
            'cat_labels': cat_labels,
            'cat_data': cat_data,
            'request': request,
            'suspended_certificates': suspended_certificates,
        }
        return render(request, 'dashboard.html', context)

    # 🟦 CASO 2: Socio
    subscriptions = Subscription.objects.filter(member=user).order_by("-start_date")
    today = date.today()
    return render(request, "user_dashboard.html", {
        "member": user,
        "subscriptions": subscriptions,
        "today": today,
    })


# ---------------------------------------------------------------------------
#  PROFILO / PASSWORD
# ---------------------------------------------------------------------------
@login_required
def profile(request):
    user = request.user
    feedback = []  # rinominato: non sovrascrivere il modulo 'messages'

    if request.method == 'POST':
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, user)
            feedback.append({'tags': 'success', 'message': 'Password aggiornata con successo.'})
        else:
            feedback.append({'tags': 'danger', 'message': "Errore nell'aggiornamento della password."})
    else:
        password_form = PasswordChangeForm(user)

    today = timezone.now().date()
    subscriptions = Subscription.objects.filter(member=user).order_by('-start_date')

    subscriptions_list = []
    for sub in subscriptions:
        if sub.start_date and sub.start_date > today:
            status = "Non ancora attivo"
        elif sub.end_date and sub.end_date < today:
            status = "Scaduto"
        else:
            status = "Attivo"
        subscriptions_list.append({'subscription': sub, 'status': status})

    context = {
        'user': user,
        'password_form': password_form,
        'messages': feedback,
        'subscriptions_list': subscriptions_list,
    }
    return render(request, "members/profile.html", context)


@login_required
def change_own_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            django_messages.success(request, "La tua password è stata aggiornata con successo!")
            return redirect("dashboard")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "change_own_password.html", {"form": form})


# ---------------------------------------------------------------------------
#  GESTIONE SOCI  (solo segreteria)
# ---------------------------------------------------------------------------
@office_required
def add_member(request):
    DocumentFormSet = modelformset_factory(MemberDocument, form=MemberDocumentForm)

    if request.method == "POST":
        member_form = MemberCreationForm(request.POST)
        document_formset = DocumentFormSet(
            request.POST, request.FILES, queryset=MemberDocument.objects.none()
        )
        if member_form.is_valid() and document_formset.is_valid():
            member = member_form.save()
            for form in document_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    document = form.save(commit=False)
                    document.member = member
                    document.save()
            django_messages.success(request, f"Socio '{member}' creato con successo!")
            return redirect('dashboard')
        django_messages.error(request, "Errore nella creazione del socio o dei documenti.")
    else:
        member_form = MemberCreationForm()
        document_formset = DocumentFormSet(queryset=MemberDocument.objects.none())

    return render(request, "add_member.html", {
        "member_form": member_form,
        "document_formset": document_formset,
    })


@office_required
def edit_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    if request.method == "POST":
        form = MemberChangeForm(request.POST, instance=member)
        formset = MemberDocumentFormSet(request.POST, request.FILES, queryset=member.documents.all())
        if form.is_valid() and formset.is_valid():
            form.save()
            docs = formset.save(commit=False)
            for doc in docs:
                doc.member = member
                doc.save()
            for obj in formset.deleted_objects:
                obj.delete()
            django_messages.success(request, "Modifiche salvate.")
            return redirect("members:edit_member", member_id=member.id)
    else:
        form = MemberChangeForm(instance=member)
        formset = MemberDocumentFormSet(queryset=member.documents.all())

    return render(request, "member_edit.html", {
        "member": member, "form": form, "formset": formset,
    })


# ---------------------------------------------------------------------------
#  DOCUMENTI
# ---------------------------------------------------------------------------
@office_required
def add_member_document(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    if request.method == "POST":
        form = MemberDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.member = member
            document.save()
            return redirect("members:edit_member", member_id=member.id)
    else:
        form = MemberDocumentForm()
    return render(request, "member_document_form.html", {"form": form, "member": member})


@office_required
def edit_member_document(request, document_id):
    document = get_object_or_404(MemberDocument, id=document_id)
    member = document.member
    if request.method == "POST":
        form = MemberDocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()
            return redirect("members:edit_member", member_id=member.id)
    else:
        form = MemberDocumentForm(instance=document)
    return render(request, "member_document_form.html",
                  {"form": form, "member": member, "document": document})


@office_required
def delete_member_document(request, document_id):
    document = get_object_or_404(MemberDocument, id=document_id)
    member_id = document.member.id
    document.delete()
    return redirect("members:edit_member", member_id=member_id)


@office_required
def add_document_admin(request):
    if request.method == 'POST':
        form = AdminMemberDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()
            django_messages.success(request, f"Documento aggiunto correttamente a {document.member}.")
            return redirect('members:edit_member', member_id=document.member.id)
    else:
        form = AdminMemberDocumentForm()
    return render(request, 'member_document_form.html',
                  {'form': form, 'title': "Aggiungi documento a socio"})


# ---------------------------------------------------------------------------
#  STATO CERTIFICATI MEDICI  (solo segreteria)
# ---------------------------------------------------------------------------
@office_required
def medical_certificate_status(request):
    members = Member.objects.all().prefetch_related('documents')
    today = timezone.now().date()
    search_query = request.GET.get('q', '').lower()
    status_filter = request.GET.get('status', '')

    members_status = []
    for member in members:
        if search_query:
            haystack = " ".join([
                member.first_name or "", member.last_name or "",
                member.email or "", member.username or "",
            ]).lower()
            if search_query not in haystack:
                continue

        medical_docs = [d for d in member.documents.all()
                        if d.document_type == 'MEDICAL_CERTIFICATE']
        if medical_docs:
            medical_docs_sorted = sorted(
                medical_docs,
                key=lambda d: d.expiration_date if d.expiration_date else date.min,
                reverse=True,
            )
            doc = medical_docs_sorted[0]
            if doc.expiration_date and doc.expiration_date < today:
                status = "Scaduto"
            else:
                status = "Attivo"
        else:
            doc = None
            status = "Assente"

        if status_filter and status != status_filter:
            continue

        members_status.append({'member': member, 'document': doc, 'cert_status': status})

    return render(request, 'medical_certificate_status.html', {'members_status': members_status})


# ---------------------------------------------------------------------------
#  ABBONAMENTI
# ---------------------------------------------------------------------------
@office_required
def subscription_list(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    subscriptions = member.subscriptions.all().order_by('-end_date')
    return render(request, 'subscription_list.html',
                  {'member': member, 'subscriptions': subscriptions})


@office_required
def add_subscription(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.member = member
            subscription.save()
            return redirect('members:subscription_list', member_id=member.id)
    else:
        form = SubscriptionForm()
    return render(request, 'subscription_form.html', {'member': member, 'form': form})


@office_required
def subscription_status(request):
    today = timezone.now().date()
    search_query = request.GET.get('q', '').lower()
    status_filter = request.GET.get('status', '')

    subscriptions_status = []
    subscriptions = Subscription.objects.select_related('member').all()
    for sub in subscriptions:
        member = sub.member
        if search_query:
            haystack = " ".join([
                member.first_name or "", member.last_name or "",
                member.email or "", member.username or "",
            ]).lower()
            if search_query not in haystack:
                continue

        if sub.start_date and sub.start_date > today:
            status = "Non ancora attivo"
        elif sub.end_date and sub.end_date < today:
            status = "Scaduto"
        else:
            status = "Attivo"

        if status_filter and status != status_filter:
            continue

        subscriptions_status.append({'subscription': sub, 'member': member, 'status': status})

    return render(request, 'subscription_status.html',
                  {'subscriptions_status': subscriptions_status})


@office_required
def add_subscription_admin(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        selected_member_id = request.POST.get("member")
        if form.is_valid() and selected_member_id:
            member = get_object_or_404(Member, id=selected_member_id)
            subscription = form.save(commit=False)
            subscription.member = member
            subscription.save()
            django_messages.success(request, f"Abbonamento aggiunto con successo per {member}.")
            return redirect("dashboard")
    else:
        form = SubscriptionForm()

    members = Member.objects.all().order_by("last_name", "first_name")
    return render(request, "subscription_form_admin.html", {"form": form, "members": members})


# ---------------------------------------------------------------------------
#  ENDPOINT JSON PER I GRAFICI  (solo segreteria)
# ---------------------------------------------------------------------------
@office_required
def subscription_data(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    subs = Subscription.objects.all()
    if start_date:
        subs = subs.filter(start_date__gte=parse_date(start_date))
    if end_date:
        subs = subs.filter(start_date__lte=parse_date(end_date))

    subscription_stats = (
        subs
        .annotate(date=TruncDay('start_date'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    labels = [s['date'].strftime('%b %Y') for s in subscription_stats if s['date']]
    data = [s['count'] for s in subscription_stats if s['date']]
    return JsonResponse({'labels': labels, 'data': data})


@office_required
def subscriptions_by_category(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    qs = Subscription.objects.all()
    if start_date and 'to' in start_date:
        parts = start_date.split('to')
        start_date = parts[0].strip()
        end_date = parts[1].strip() if len(parts) > 1 else None

    if start_date:
        qs = qs.filter(start_date__gte=parse_date(start_date))
    if end_date:
        qs = qs.filter(start_date__lte=parse_date(end_date))

    stats = (
        qs.values('sector__name')
        .annotate(count=Count('id'))
        .order_by('sector__name')
    )
    labels = [item['sector__name'] or '—' for item in stats]
    data = [item['count'] for item in stats]
    return JsonResponse({'labels': labels, 'data': data})
