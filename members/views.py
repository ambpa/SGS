# members/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from .models import Member, MemberDocument
from .forms import MemberCreationForm, MemberDocumentForm
from .forms import MemberChangeForm, MemberDocumentFormSet

from django.forms import modelformset_factory
from django.core.paginator import Paginator

from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from .models import Member, Subscription
from .forms import SubscriptionForm


from django.utils import timezone


@login_required
def dashboard(request):
    search_query = request.GET.get('q', '')

    # Recupera tutti i soci filtrando per ricerca
    members_qs = Member.objects.all()
    if search_query:
        members_qs = members_qs.filter(
            first_name__icontains=search_query
        ) | members_qs.filter(
            last_name__icontains=search_query
        ) | members_qs.filter(
            email__icontains=search_query
        )

    # Paginazione (10 per pagina)
    paginator = Paginator(members_qs.order_by('last_name', 'first_name'), 10)
    page_number = request.GET.get('page')
    members = paginator.get_page(page_number)

    # Statistiche
    total_members = Member.objects.count()
    active_members = Member.objects.filter(is_active=True).count()

    # Statistiche documenti
    total_documents = MemberDocument.objects.count()
    today = timezone.now().date()
    expired_certificates = MemberDocument.objects.filter(
        document_type='MEDICAL_CERTIFICATE', expiration_date__lt=today
    ).count()
    active_certificates = MemberDocument.objects.filter(
        document_type='MEDICAL_CERTIFICATE', expiration_date__gte=today
    ).count()

    # Statistiche abbonamenti
    total_subscriptions = Subscription.objects.count()
    active_subscriptions = sum(1 for s in Subscription.objects.all() if s.status == "Attivo")
    expired_subscriptions = sum(1 for s in Subscription.objects.all() if s.status == "Scaduto")

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
        'request': request,
    }

    return render(request, 'dashboard.html', context)



@login_required
def profile(request):
    user = request.user
    messages = []

    # Gestione cambio password
    if request.method == 'POST':
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            password_form.save()
            messages.append({'tags': 'success', 'message': 'Password aggiornata con successo.'})
        else:
            messages.append({'tags': 'danger', 'message': 'Errore nell\'aggiornamento della password.'})
    else:
        password_form = PasswordChangeForm(user)

    # Recupera subscription dell'utente loggato
    today = timezone.now().date()
    subscriptions = Subscription.objects.filter(member_id=user).order_by('-start_date')

    subscriptions_list = []

    for sub in subscriptions:
        if sub.start_date > today:
            status = "Non ancora attivo"
        elif sub.end_date and sub.end_date < today:
            status = "Scaduto"
        else:
            status = "Attivo"
        subscriptions_list.append({
            'subscription': sub,
            'status': status
        })


    context = {
        'user': user,
        'password_form': password_form,
        'messages': messages,
        'subscriptions_list': subscriptions_list,
    }
    print(subscriptions_list)
    return render(request, "members/profile.html", context )

@login_required
def add_member(request):
    """
    Crea un nuovo socio e permette di caricare più documenti associati.
    """
    # Creiamo un formset per i documenti (max 5 documenti per esempio)
    DocumentFormSet = modelformset_factory(
        MemberDocument,
        form=MemberDocumentForm,
        extra=3,      # numero di documenti vuoti visualizzati
        can_delete=True
    )

    if request.method == "POST":
        member_form = MemberCreationForm(request.POST)
        document_formset = DocumentFormSet(request.POST, request.FILES, queryset=MemberDocument.objects.none())

        if member_form.is_valid() and document_formset.is_valid():
            # Salva il socio
            member = member_form.save()

            # Salva tutti i documenti e assegna il socio
            for form in document_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    document = form.save(commit=False)
                    document.member = member
                    document.save()

            messages.success(request, f"Socio '{member}' creato con successo!")
            return redirect('dashboard')  # O la pagina che vuoi
        else:
            messages.error(request, "Errore nella creazione del socio o dei documenti. Controlla i dati inseriti.")
    else:
        member_form = MemberCreationForm()
        document_formset = DocumentFormSet(queryset=MemberDocument.objects.none())

    context = {
        "member_form": member_form,
        "document_formset": document_formset,
    }
    return render(request, "add_member.html", context)


# Modifica socio
@login_required
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
            return redirect("edit_member", member_id=member.id)
    else:
        form = MemberChangeForm(instance=member)
        formset = MemberDocumentFormSet(queryset=member.documents.all())

    return render(request, "member_edit.html", {
        "member": member,
        "form": form,
        "formset": formset,
    })


@login_required
def change_own_password(request):
    """Permette all'utente loggato di cambiare la propria password."""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # mantiene il login attivo
            messages.success(request, "La tua password è stata aggiornata con successo!")
            return redirect("dashboard")  # o dove vuoi reindirizzare
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "change_own_password.html", {"form": form})

@login_required
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


# Modifica documento
@login_required
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

    return render(request, "member_document_form.html", {"form": form, "member": member, "document": document})


# Elimina documento
@login_required
def delete_member_document(request, document_id):
    document = get_object_or_404(MemberDocument, id=document_id)
    member_id = document.member.id
    document.delete()
    return redirect("members:edit_member", member_id=member_id)


from django.shortcuts import render
from django.utils import timezone
from .models import Member


def medical_certificate_status(request):
    # Recupera tutti i soci con i documenti
    members = Member.objects.all().prefetch_related('documents')
    today = timezone.now().date()

    # Prendi i parametri GET per filtro e ricerca
    search_query = request.GET.get('q', '').lower()
    status_filter = request.GET.get('status', '')

    members_status = []

    for member in members:
        # Filtro per ricerca testo (nome, cognome, email, username)
        if search_query:
            if search_query not in member.first_name.lower() \
               and search_query not in member.last_name.lower() \
               and search_query not in member.email.lower() \
               and search_query not in member.username.lower():
                continue

        # Filtra i documenti tipo Certificato Medico
        medical_docs = [d for d in member.documents.all() if d.document_type == 'MEDICAL_CERTIFICATE']

        if medical_docs:
            # Ordina per expiration_date decrescente (None alla fine)
            medical_docs_sorted = sorted(
                medical_docs,
                key=lambda d: d.expiration_date if d.expiration_date else timezone.datetime.min.date(),
                reverse=True
            )
            doc = medical_docs_sorted[0]

            # Controllo stato
            if doc.expiration_date and doc.expiration_date < today:
                status = "Scaduto"
            else:
                status = "Attivo"
        else:
            doc = None
            status = "Assente"

        # Filtro per stato
        if status_filter and status != status_filter:
            continue

        members_status.append({
            'member': member,
            'document': doc,
            'cert_status': status
        })

    context = {
        'members_status': members_status,
    }
    return render(request, 'medical_certificate_status.html', context)


@login_required
def subscription_list(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    subscriptions = member.subscriptions.all().order_by('-end_date')

    context = {
        'member': member,
        'subscriptions': subscriptions,
    }
    return render(request, 'subscription_list.html', context)


@login_required
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

    context = {
        'member': member,
        'form': form
    }
    return render(request, 'subscription_form.html', context)


def subscription_status(request):
    today = timezone.now().date()
    search_query = request.GET.get('q', '').lower()
    status_filter = request.GET.get('status', '')

    subscriptions_status = []

    # Recupera tutte le subscriptions con prefetched member
    subscriptions = Subscription.objects.select_related('member').all()

    for sub in subscriptions:
        member = sub.member

        # Filtro ricerca testo su informazioni utente
        if search_query:
            if search_query not in member.first_name.lower() \
               and search_query not in member.last_name.lower() \
               and search_query not in member.email.lower() \
               and search_query not in member.username.lower():
                continue

        # Calcola stato dell'abbonamento
        if sub.start_date > today:
            status = "Non ancora attivo"
        elif sub.end_date and sub.end_date < today:
            status = "Scaduto"
        else:
            status = "Attivo"

        # Filtro per stato
        if status_filter and status != status_filter:
            continue

        subscriptions_status.append({
            'subscription': sub,
            'member': member,
            'status': status
        })

    context = {
        'subscriptions_status': subscriptions_status
    }
    return render(request, 'subscription_status.html', context)