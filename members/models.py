# members/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import os


def member_document_upload_path(instance, filename):
    """
    Genera un percorso dinamico per i file caricati.
    Esempio: documents/member_12/certificato_medico.pdf
    """
    return f'documents/member_{instance.member.id}/{filename}'


# ---------------------------------------------------------------------------
#  TABELLE DI CONFIGURAZIONE (gestite dall'amministratore)
# ---------------------------------------------------------------------------
class Sector(models.Model):
    """
    Settore / disciplina (es. FITNESS, SALA PESI, KARATE).
    Sostituisce l'enum fisso 'Category': cosi' i settori sono configurabili
    dall'admin senza toccare il codice.
    """
    name = models.CharField(_("Settore"), max_length=100, unique=True)
    is_active = models.BooleanField(_("Attivo"), default=True)

    class Meta:
        verbose_name = _("Settore")
        verbose_name_plural = _("Settori")
        ordering = ["name"]

    def __str__(self):
        return self.name


class SportsBody(models.Model):
    """
    Ente di promozione / federazione sportiva (CSEN, FIJLKAM, LIBERTAS, ...).
    """
    name = models.CharField(_("Ente"), max_length=100, unique=True)
    code = models.CharField(_("Sigla"), max_length=20, blank=True)
    is_active = models.BooleanField(_("Attivo"), default=True)

    class Meta:
        verbose_name = _("Ente sportivo")
        verbose_name_plural = _("Enti sportivi")
        ordering = ["name"]

    def __str__(self):
        return self.code or self.name


class Instructor(models.Model):
    """
    Insegnante tecnico. Puo' essere collegato (facoltativamente) a un account
    utente, per dare all'istruttore l'accesso ai propri allievi.
    """
    first_name = models.CharField(_("Nome"), max_length=100)
    last_name = models.CharField(_("Cognome"), max_length=100, blank=True)
    sectors = models.ManyToManyField(
        Sector, blank=True, related_name="instructors", verbose_name=_("Settori")
    )
    user = models.OneToOneField(
        "Member",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="instructor_profile",
        verbose_name=_("Account collegato"),
    )
    is_active = models.BooleanField(_("Attivo"), default=True)

    class Meta:
        verbose_name = _("Insegnante tecnico")
        verbose_name_plural = _("Insegnanti tecnici")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.first_name


# ---------------------------------------------------------------------------
#  SOCIO / UTENTE
# ---------------------------------------------------------------------------
class Member(AbstractUser):
    """
    Modello utente personalizzato per il socio della palestra/A.S.D.
    Esteso con i dati anagrafici e sportivi presenti nel gestionale Access.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", _("Amministratore")
        STAFF = "STAFF", _("Segreteria")
        INSTRUCTOR = "INSTRUCTOR", _("Istruttore")
        MEMBER = "MEMBER", _("Socio")

    class Sex(models.TextChoices):
        MALE = "M", _("Maschio")
        FEMALE = "F", _("Femmina")

    # Ruolo applicativo (da cui derivano i flag is_staff/is_superuser)
    role = models.CharField(
        _("Ruolo"), max_length=20, choices=Role.choices, default=Role.MEMBER
    )

    # Anagrafica
    first_name = models.CharField(_("Nome"), max_length=150, blank=False)
    last_name = models.CharField(_("Cognome"), max_length=150, blank=False)
    email = models.EmailField(_("Email"), blank=True)

    card_number = models.CharField(
        _("Numero tessera"), max_length=30, unique=True, null=True, blank=True,
        help_text=_("Formato es. BS/23/00202"),
    )
    fiscal_code = models.CharField(_("Codice fiscale"), max_length=16, blank=True)
    sex = models.CharField(_("Sesso"), max_length=1, choices=Sex.choices, blank=True)

    date_of_birth = models.DateField(_("Data di nascita"), null=True, blank=True)
    birth_place = models.CharField(_("Luogo di nascita"), max_length=120, blank=True)

    phone_number = models.CharField(_("Cellulare"), max_length=20, blank=True)
    phone_home = models.CharField(_("Telefono casa"), max_length=20, blank=True)
    address = models.CharField(_("Indirizzo"), max_length=255, blank=True)
    residence_city = models.CharField(_("Comune di residenza"), max_length=120, blank=True)
    province = models.CharField(_("Provincia"), max_length=2, blank=True)
    postal_code = models.CharField(_("CAP"), max_length=5, blank=True)

    photo = models.ImageField(_("Foto"), upload_to="member_photos/", null=True, blank=True)
    notes = models.TextField(_("Note"), blank=True)

    # Stato associativo
    registration_date = models.DateField(_("Data registrazione"), null=True, blank=True)
    is_dismissed = models.BooleanField(_("Dimesso / Cessato"), default=False)

    # Disciplina
    sector = models.ForeignKey(
        Sector, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members", verbose_name=_("Settore"),
    )
    instructor = models.ForeignKey(
        Instructor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members", verbose_name=_("Insegnante tecnico"),
    )

    # Relazione genitore -> minore (vincolo Access: prima il genitore)
    guardian = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="dependents", verbose_name=_("Genitore / tutore"),
    )

    class Meta:
        verbose_name = _("Socio")
        verbose_name_plural = _("Soci")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_minor(self):
        """True se il socio e' minorenne alla data odierna."""
        if not self.date_of_birth:
            return False
        today = timezone.now().date()
        years = today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        return years < 18

    # --- helper di ruolo, comodi nei template e nelle view ---
    @property
    def is_office(self):
        """Personale di segreteria o amministratore."""
        return self.role in (self.Role.ADMIN, self.Role.STAFF) or self.is_staff

    def save(self, *args, **kwargs):
        """
        Deriva automaticamente i flag di Django dal ruolo applicativo,
        per evitare incoerenze (es. un socio con accesso admin).
        """
        if self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        elif self.role == self.Role.STAFF:
            self.is_staff = True
            self.is_superuser = False
        else:  # INSTRUCTOR / MEMBER
            self.is_staff = False
            self.is_superuser = False
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
#  AFFILIAZIONE A ENTI (CSEN / FIJLKAM / LIBERTAS ...)
# ---------------------------------------------------------------------------
class Affiliation(models.Model):
    """
    Affiliazione di un socio a un ente sportivo, con tessera e scadenza.
    Una riga per ente: il socio puo' essere affiliato a piu' enti.
    """
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE,
        related_name="affiliations", verbose_name=_("Socio"),
    )
    body = models.ForeignKey(
        SportsBody, on_delete=models.PROTECT,
        related_name="affiliations", verbose_name=_("Ente"),
    )
    federal_card = models.CharField(_("Tessera federale"), max_length=50, blank=True)
    federal_card_expiry = models.DateField(_("Scadenza tessera"), null=True, blank=True)
    federal_license = models.CharField(_("Licenza federale"), max_length=50, blank=True)
    affiliation_year = models.CharField(
        _("Anno affiliazione"), max_length=20, blank=True,
        help_text=_("Es. 2023/2026"),
    )

    class Meta:
        verbose_name = _("Affiliazione")
        verbose_name_plural = _("Affiliazioni")
        unique_together = ("member", "body")
        ordering = ["body__name"]

    def __str__(self):
        return f"{self.body} - {self.member}"


# ---------------------------------------------------------------------------
#  DOCUMENTI (certificato medico, ecc.)  -- invariato nella sostanza
# ---------------------------------------------------------------------------
class MemberDocument(models.Model):
    """Documenti associati a un socio."""

    class DocumentType(models.TextChoices):
        MEDICAL_CERTIFICATE = 'MEDICAL_CERTIFICATE', _('Certificato Medico')
        IDENTITY_CARD = 'IDENTITY_CARD', _("Carta d'Identità")
        CONTRACT = 'CONTRACT', _('Contratto')
        OTHER = 'OTHER', _('Altro')

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE,
        related_name="documents", verbose_name=_("Socio"),
    )
    document_type = models.CharField(
        max_length=50, choices=DocumentType.choices,
        default=DocumentType.OTHER, verbose_name=_("Tipo di documento"),
    )
    file = models.FileField(upload_to=member_document_upload_path, verbose_name=_("File"))
    expiration_date = models.DateField(_("Data di Scadenza"), null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Attivo"))
    description = models.TextField(verbose_name=_("Descrizione"), blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Data di caricamento"))

    class Meta:
        verbose_name = _("Documento Socio")
        verbose_name_plural = _("Documenti Soci")
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Documento '{self.get_document_type_display()}' per {self.member}"

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def is_expired(self):
        return bool(self.expiration_date and self.expiration_date < timezone.now().date())


# ---------------------------------------------------------------------------
#  ABBONAMENTO / ISCRIZIONE A UNA DISCIPLINA  -- come prima, con settore FK
# ---------------------------------------------------------------------------
class Subscription(models.Model):
    """
    Iscrizione di un socio a una disciplina/abbonamento.
    La 'category' enum e' stata sostituita da una FK a Sector (configurabile).
    """

    class SubscriptionType(models.TextChoices):
        MONTHLY = 'MONTHLY', _('Mensile')
        QUARTERLY = 'QUARTERLY', _('Trimestrale')
        FOURMONTH = 'FOURMONTH', _('Quadrimestrale')
        SEMESTRAL = 'SEMESTRAL', _('Semestrale')
        ANNUAL = 'ANNUAL', _('Annuale')

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE,
        related_name="subscriptions", verbose_name=_("Socio"),
    )
    subscription_type = models.CharField(
        max_length=20, choices=SubscriptionType.choices,
        verbose_name=_("Tipologia abbonamento"),
    )
    sector = models.ForeignKey(
        Sector, on_delete=models.PROTECT,
        related_name="subscriptions", verbose_name=_("Settore"),
        null=True, blank=True,
    )
    start_date = models.DateField(verbose_name=_("Data inizio"))
    end_date = models.DateField(verbose_name=_("Data fine"), null=True, blank=True)

    package = models.ForeignKey(
        'Package', on_delete=models.PROTECT,
        related_name="subscriptions", verbose_name=_("Pacchetto"),
        null=True, blank=True,   # nullable per non rompere i record esistenti
    )

    class Meta:
        verbose_name = _("Abbonamento")
        verbose_name_plural = _("Abbonamenti")
        ordering = ['-end_date']

    def __str__(self):
        sector = self.sector.name if self.sector else "—"
        return f"{self.get_subscription_type_display()} - {sector} per {self.member}"

    @property
    def status(self):
        today = timezone.now().date()
        if self.end_date and self.end_date < today:
            return "Scaduto"
        elif self.start_date > today:
            return "Non ancora attivo"
        return "Attivo"

    def save(self, *args, **kwargs):
        # Se c'è un pacchetto, eredita settore e tipo da lì.
        if self.package_id:
            if not self.sector_id:
                self.sector = self.package.sector
            self.subscription_type = self.package.package_type

        # Calcolo data fine: dal pacchetto se presente, altrimenti come prima.
        if self.start_date and not self.end_date:
            delta = None
            if self.package_id and self.package.duration:
                delta = self.package.duration
            else:
                from dateutil.relativedelta import relativedelta
                delta = {
                    self.SubscriptionType.MONTHLY: relativedelta(months=1),
                    self.SubscriptionType.QUARTERLY: relativedelta(months=3),
                    self.SubscriptionType.FOURMONTH: relativedelta(months=4),
                    self.SubscriptionType.SEMESTRAL: relativedelta(months=6),
                    self.SubscriptionType.ANNUAL: relativedelta(years=1),
                }.get(self.subscription_type)
            if delta:
                self.end_date = self.start_date + delta
        super().save(*args, **kwargs)

    # 3) AGGIUNGI questa property a Subscription (comoda nei template):
    @property
    def is_paid(self):
        """True se esiste un pagamento collegato e segnato come pagato."""
        p = self.payments.first()
        return bool(p and p.is_paid)

    @property
    def payment(self):
        """Il pagamento collegato (uno solo), o None."""
        return self.payments.first()


# ---------------------------------------------------------------------------
#  STORICO PAGAMENTI / QUOTE  (la griglia della schermata "Quota associativa")
# ---------------------------------------------------------------------------
class Payment(models.Model):
    """
    Singolo evento di pagamento / rata del socio.
    Rispecchia la griglia Access: Tipo, data pagamento, scadenza, prossima
    scadenza, quota, sconto, modalita', stato pagato/insoluto.
    """

    class PaymentType(models.TextChoices):
        ENROLLMENT = 'ENROLLMENT', _('Iscrizione')
        MONTHLY = 'MONTHLY', _('Mensile')
        QUARTERLY = 'QUARTERLY', _('Trimestrale')
        FOURMONTH = 'FOURMONTH', _('Quadrimestrale')

    class PaymentMode(models.TextChoices):
        CASH = 'C', _('Contanti')
        BANK = 'B', _('Bonifico / POS')

    member = models.ForeignKey(
        Member, on_delete=models.CASCADE,
        related_name="payments", verbose_name=_("Socio"),
    )
    subscription = models.OneToOneField(
        Subscription, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="payments",   # manteniamo il nome 'payments'
        verbose_name=_("Abbonamento"),

    )

    payment_type = models.CharField(
        _("Tipo"), max_length=20, choices=PaymentType.choices,
    )
    payment_date = models.DateField(_("Data pagamento"), null=True, blank=True)
    due_date = models.DateField(_("Scadenza"), null=True, blank=True)
    next_due_date = models.DateField(_("Prossima scadenza"), null=True, blank=True)

    amount = models.DecimalField(_("Quota €"), max_digits=8, decimal_places=2, default=0)
    enrollment_amount = models.DecimalField(
        _("Iscrizione €"), max_digits=8, decimal_places=2, null=True, blank=True,
    )
    discount = models.DecimalField(_("Sconto €"), max_digits=8, decimal_places=2, default=0)
    payment_mode = models.CharField(
        _("Modalità"), max_length=2, choices=PaymentMode.choices, blank=True,
    )
    fee_code = models.CharField(_("Tariffa"), max_length=5, blank=True)  # A / B / C ...
    is_paid = models.BooleanField(_("Pagato"), default=True)

    class Meta:
        verbose_name = _("Pagamento")
        verbose_name_plural = _("Pagamenti")
        ordering = ["-due_date", "-payment_date"]

    def __str__(self):
        return f"{self.get_payment_type_display()} {self.amount}€ - {self.member}"

    @property
    def net_amount(self):
        return (self.amount or 0) - (self.discount or 0)

    @property
    def is_overdue(self):
        """Rata scaduta e non pagata."""
        if self.is_paid:
            return False
        return bool(self.due_date and self.due_date < timezone.now().date())

    def save(self, *args, **kwargs):
        # Deduci tipo e importo dall'abbonamento collegato (se presente).
        if self.subscription_id:
            sub = self.subscription
            # tipo dedotto dall'abbonamento
            mapping = {
                'MONTHLY': self.PaymentType.MONTHLY,
                'QUARTERLY': self.PaymentType.QUARTERLY,
                'FOURMONTH': self.PaymentType.FOURMONTH,
                'SEMESTRAL': self.PaymentType.QUARTERLY,  # fallback ragionevole
                'ANNUAL': self.PaymentType.ENROLLMENT,
            }
            if not self.payment_type:
                self.payment_type = mapping.get(sub.subscription_type, self.payment_type)
            # importo bloccato dal prezzo del pacchetto (lo sconto resta a parte)
            if sub.package_id and (self.amount is None or self.amount == 0):
                self.amount = sub.package.price

        # Calcolo prossima scadenza (come da Fase 3a)
        if not self.next_due_date:
            base = self.due_date or self.payment_date
            if base:
                from dateutil.relativedelta import relativedelta
                deltas = {
                    self.PaymentType.MONTHLY: relativedelta(months=1),
                    self.PaymentType.QUARTERLY: relativedelta(months=3),
                    self.PaymentType.FOURMONTH: relativedelta(months=4),
                    self.PaymentType.ENROLLMENT: relativedelta(years=1),
                }
                delta = deltas.get(self.payment_type)
                if delta:
                    self.next_due_date = base + delta
        super().save(*args, **kwargs)


class Package(models.Model):
    """
    Voce di listino: un pacchetto vendibile, legato a un settore.
    Es. "Trimestrale Fitness" / tipo trimestrale / 120 / settore Fitness.
    In una fase successiva da qui deriveranno tipo e prezzo di
    abbonamenti e pagamenti.
    """

    class PackageType(models.TextChoices):
        MONTHLY = 'MONTHLY', _('Mensile')
        QUARTERLY = 'QUARTERLY', _('Trimestrale')
        FOURMONTH = 'FOURMONTH', _('Quadrimestrale')
        SEMESTRAL = 'SEMESTRAL', _('Semestrale')
        ANNUAL = 'ANNUAL', _('Annuale')

    name = models.CharField(_("Nome pacchetto"), max_length=120)
    sector = models.ForeignKey(
        Sector, on_delete=models.PROTECT,
        related_name="packages", verbose_name=_("Settore"),
    )
    package_type = models.CharField(
        _("Tipo"), max_length=20, choices=PackageType.choices,
    )
    price = models.DecimalField(_("Prezzo"), max_digits=8, decimal_places=2)
    is_active = models.BooleanField(_("Attivo"), default=True)

    class Meta:
        verbose_name = _("Pacchetto")
        verbose_name_plural = _("Listino pacchetti")
        ordering = ["sector__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_package_type_display()} - {self.price})"

    @property
    def duration(self):
        """relativedelta corrispondente al tipo (per le scadenze, uso futuro)."""
        from dateutil.relativedelta import relativedelta
        return {
            self.PackageType.MONTHLY: relativedelta(months=1),
            self.PackageType.QUARTERLY: relativedelta(months=3),
            self.PackageType.FOURMONTH: relativedelta(months=4),
            self.PackageType.SEMESTRAL: relativedelta(months=6),
            self.PackageType.ANNUAL: relativedelta(years=1),
        }.get(self.package_type)
