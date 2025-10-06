# members/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import os
from django.utils import timezone

def member_document_upload_path(instance, filename):
    """
    Genera un percorso dinamico per i file caricati.
    Esempio: documents/member_12/certificato_medico.pdf
    """
    return f'documents/member_{instance.member.id}/{filename}'


class Member(AbstractUser):
    """
    Modello utente personalizzato per il socio della palestra.
    """
    # Rendiamo questi campi obbligatori (blank=False)
    first_name = models.CharField(_("first name"), max_length=150, blank=False)
    last_name = models.CharField(_("last name"), max_length=150, blank=False)
    email = models.EmailField(_("email address"), blank=False)

    # Campi anagrafici aggiuntivi
    date_of_birth = models.DateField(
        verbose_name=_("Data di nascita"),
        null=True,
        blank=True
    )
    phone_number = models.CharField(
        verbose_name=_("Numero di telefono"),
        max_length=20,
        blank=True
    )
    address = models.CharField(
        verbose_name=_("Indirizzo"),
        max_length=255,
        blank=True
    )

    class Meta:
        verbose_name = _("Socio")
        verbose_name_plural = _("Soci")
        ordering = ['last_name', 'first_name']

    def __str__(self):
        # Se nome e cognome esistono, mostra quelli, altrimenti lo username.
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username


class MemberDocument(models.Model):
    """
    Modello per i documenti associati a un socio.
    """

    class DocumentType(models.TextChoices):
        MEDICAL_CERTIFICATE = 'MEDICAL_CERTIFICATE', _('Certificato Medico')
        IDENTITY_CARD = 'IDENTITY_CARD', _('Carta d\'Identità')
        CONTRACT = 'CONTRACT', _('Contratto')
        OTHER = 'OTHER', _('Altro')

    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Socio")
    )
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
        verbose_name=_("Tipo di documento")
    )
    file = models.FileField(
        upload_to=member_document_upload_path,
        verbose_name=_("File")
    )
    # NUOVI CAMPI AGGIUNTI QUI
    expiration_date = models.DateField(
        verbose_name=_("Data di Scadenza"),
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Attivo")
    )
    description = models.TextField(verbose_name=_("Descrizione"), blank=True)
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data di caricamento")
    )

    class Meta:
        verbose_name = _("Documento Socio")
        verbose_name_plural = _("Documenti Soci")
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Documento '{self.get_document_type_display()}' per {self.member}"

    @property
    def filename(self):
        return os.path.basename(self.file.name)





class Subscription(models.Model):
    class SubscriptionType(models.TextChoices):
        ANNUAL = 'ANNUAL', _('Annuale')
        SEMESTRAL = 'SEMESTRAL', _('Semestrale')
        MONTHLY = 'MONTHLY', _('Mensile')

    class Category(models.TextChoices):
        GYM = 'GYM', _('Palestra')
        COURSE_A = 'COURSE_A', _('Corso A')
        KARATE = 'KARATE', _('Karate')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="subscriptions")


    subscription_type = models.CharField(
        max_length=20,
        choices=SubscriptionType.choices,
        verbose_name=_("Tipologia abbonamento")
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        verbose_name=_("Categoria")
    )
    start_date = models.DateField(verbose_name=_("Data inizio"))
    end_date = models.DateField(verbose_name=_("Data fine"))

    class Meta:
        verbose_name = _("Abbonamento")
        verbose_name_plural = _("Abbonamenti")
        ordering = ['-end_date']

    def __str__(self):
        return f"{self.get_subscription_type_display()} - {self.get_category_display()} per {self.member}"

    @property
    def status(self):
        today = timezone.now().date()
        if self.end_date < today:
            return "Scaduto"
        elif self.start_date > today:
            return "Non ancora attivo"
        else:
            return "Attivo"
