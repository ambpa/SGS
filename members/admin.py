# members/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Member, MemberDocument
# Importiamo i nostri nuovi form personalizzati
from .forms import MemberCreationForm, MemberChangeForm
from .models import Subscription  # Assumendo che Subscription sia nel file models.py
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Sector, SportsBody, Instructor

class MemberDocumentInline(admin.TabularInline):
    """
    Permette di visualizzare e aggiungere documenti
    direttamente nella pagina di dettaglio del Socio. È molto più comodo!
    """
    model = MemberDocument
    extra = 1
    fields = ('document_type', 'file', 'expiration_date', 'is_active', 'description')


@admin.register(Member)
class MemberAdmin(BaseUserAdmin):
    add_form = MemberCreationForm
    form = MemberChangeForm
    model = Member

    list_display = ("username", "first_name", "last_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "card_number")
    ordering = ("last_name", "first_name")

    # Campi mostrati in MODIFICA (utente esistente)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Ruolo e dati associazione", {
            "fields": ("role", "card_number", "sector", "instructor"),
        }),
    )

    # Campi mostrati in CREAZIONE ("Aggiungi") — include i due campi password
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "role", "first_name", "last_name", "email"),
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

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('member', 'subscription_type', 'sector', 'start_date', 'end_date', 'status_badge')
    list_filter = ('subscription_type', 'sector')
    search_fields = ('member__first_name', 'member__last_name', 'member__email')

    # Mostra lo stato con badge colorato
    def status_badge(self, obj):
        from django.utils.html import format_html
        from django.utils import timezone
        today = timezone.now().date()

        if obj.start_date > today:
            color = 'secondary'
            status = 'Non ancora attivo'
        elif obj.end_date and obj.end_date < today:
            color = 'danger'
            status = 'Scaduto'
        else:
            color = 'success'
            status = 'Attivo'

        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            status
        )

    status_badge.short_description = 'Stato'


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(SportsBody)
class SportsBodyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('first_name', 'last_name')
    filter_horizontal = ('sectors',)