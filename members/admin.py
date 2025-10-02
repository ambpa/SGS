# members/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Member, MemberDocument
# Importiamo i nostri nuovi form personalizzati
from .forms import MemberCreationForm, MemberChangeForm


class MemberDocumentInline(admin.TabularInline):
    """
    Permette di visualizzare e aggiungere documenti
    direttamente nella pagina di dettaglio del Socio. È molto più comodo!
    """
    model = MemberDocument
    extra = 1
    fields = ('document_type', 'file', 'expiration_date', 'is_active', 'description')


@admin.register(Member)
class MemberAdmin(UserAdmin):
    """
    Personalizzazione della vista Admin per il modello Member.
    """
    # Diciamo a Django di usare i nostri form personalizzati
    form = MemberChangeForm
    add_form = MemberCreationForm

    model = Member
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

    # Organizzazione dei campi per la pagina di MODIFICA di un socio esistente
    # MODIFICA CHIAVE: Rimuoviamo il campo 'password' da qui!
    fieldsets = (
        (None, {'fields': ('username', 'password')}),  # aggiunto 'password'
        ('Informazioni Personali', {'fields': ('first_name', 'last_name', 'email')}),
        ('Dati Anagrafici Aggiuntivi', {'fields': ('date_of_birth', 'phone_number', 'address')}),
        ('Permessi', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Date Importanti', {'fields': ('last_login', 'date_joined')}),
    )

    # Organizzazione dei campi per la pagina di CREAZIONE di un nuovo socio.
    # Questa sezione è corretta e non va toccata.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
    )

    inlines = [MemberDocumentInline]


@admin.register(MemberDocument)
class MemberDocumentAdmin(admin.ModelAdmin):
    """
    Vista Admin per gestire i documenti anche separatamente.
    """
    list_display = ('member', 'document_type', 'expiration_date', 'is_active', 'uploaded_at')
    list_filter = ('document_type', 'is_active', 'member')
    search_fields = ('member__first_name', 'member__last_name', 'description')
    autocomplete_fields = ['member']
    list_editable = ('is_active',)