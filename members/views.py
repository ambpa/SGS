# members/views.py
from django.shortcuts import  get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max
from django.contrib import messages
from .models import MemberDocument
from .forms import MemberCreationForm, MemberDocumentForm
from .forms import MemberChangeForm, MemberDocumentFormSet

from django.forms import modelformset_factory
from django.core.paginator import Paginator

from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from .models import Subscription
from .forms import SubscriptionForm

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.views import LoginView

from .forms import AdminMemberDocumentForm
from django.urls import reverse
from datetime import date



@login_required
def dashboard(request):

    user = request.user

    # 🟩 CASO 1: Admin o staff
    if user.is_staff or user.is_superuser:
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

        # Statistiche generali
        total_members = Member.objects.count()
        active_members = Member.objects.filter(is_active=True).count()
        total_documents = MemberDocument.objects.count()

        # Statistiche certificati considerando solo l'ultimo per socio
        today = timezone.now().date()
        expired_certificates = 0
        active_certificates = 0

        for member in Member.objects.all():
            latest_cert = member.documents.filter(document_type='MEDICAL_CERTIFICATE').order_by('-expiration_date').first()
            if latest_cert:
                if latest_cert.expiration_date and latest_cert.expiration_date < today:
                    expired_certificates += 1
                else:
                    active_certificates += 1

        # Statistiche abbonamenti considerando solo l'ultimo per categoria per socio
        from collections import defaultdict
        member_categories = defaultdict(dict)
        active_subscriptions = 0
        expired_subscriptions = 0

        for sub in Subscription.objects.select_related('member').all():
            member_id = sub.member.id
            category = sub.category
            # tieni solo l'abbonamento con la data di fine maggiore per ogni socio/categoria
            if category not in member_categories[member_id] or sub.end_date > member_categories[member_id][category].end_date:
                member_categories[member_id][category] = sub

        # Conta abbonamenti attivi e scaduti
        for member_subs in member_categories.values():
            for sub in member_subs.values():
                if sub.start_date > today:
                    continue  # non ancora attivo
                elif sub.end_date < today:
                    expired_subscriptions += 1
                else:
                    active_subscriptions += 1

        total_subscriptions = Subscription.objects.count()

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
    # CASO 2: Cliente (utente palestra)
    else:
        # Recupera i suoi abbonamenti
        subscriptions = Subscription.objects.filter(member=user).order_by("-start_date")

        # Filtra solo l’ultimo per categoria
        latest_per_category = (
            subscriptions.values("category")
            .annotate(last_end=Max("end_date"))
            .order_by()
        )

        # Decommentare se si vogliono passare solo gli ultimi abbonamenti
        # valid_subscriptions = [
        #     sub for sub in subscriptions if any(
        #         s["last_end"] == sub.end_date and s["category"] == sub.category
        #         for s in latest_per_category
        #     )
        # ]
        today = date.today()  # 👈 questa è la variabile che serve al template

        return render(request, "user_dashboard.html", {
            "member": user,
            "subscriptions": subscriptions,
            "today": today,
        })


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
        #extra=1,      # numero di documenti vuoti visualizzati
        #can_delete=True
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
            return render(request, "member_edit.html", {
                "member": member,  # <-- questo deve essere sempre un oggetto Member con id
                "form": form,
                "formset": formset,
            })
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


@login_required
@staff_member_required
def add_document_admin(request):
    """
    Permette solo all'amministratore di aggiungere un documento
    scegliendo a quale socio associarlo.
    """
    if request.method == 'POST':
        form = AdminMemberDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()
            messages.success(request, f"Documento aggiunto correttamente a {document.member}.")
            return redirect('members:edit_member', member_id=document.member.id)
    else:
        form = AdminMemberDocumentForm()

    context = {
        'form': form,
        'title': "Aggiungi documento a socio"
    }
    return render(request, 'member_document_form.html', context)



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

@login_required
@staff_member_required
def add_subscription_admin(request):
    """Permette all'admin di scegliere il socio a cui associare un nuovo abbonamento."""
    from .forms import SubscriptionForm
    from .models import Member, Subscription

    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        selected_member_id = request.POST.get("member")

        if form.is_valid() and selected_member_id:
            member = get_object_or_404(Member, id=selected_member_id)
            subscription = form.save(commit=False)
            subscription.member = member
            subscription.save()
            messages.success(request, f"Abbonamento aggiunto con successo per {member}.")
            return redirect("dashboard")
    else:
        form = SubscriptionForm()

    members = Member.objects.all().order_by("last_name", "first_name")

    context = {
        "form": form,
        "members": members,
    }
    return render(request, "subscription_form_admin.html", context)


