# members/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, ReadOnlyPasswordHashField
from .models import Member, MemberDocument
from django.forms import modelformset_factory
from django import forms
from .models import Subscription
from datetime import date
from .models import Sector, Instructor

from .models import Payment, Package

# =====================================================================
#  FASE 3-LISTINO — Aggiungi a members/forms.py
#  Import in cima (accanto agli altri): from .models import Package
# =====================================================================

class PackageForm(forms.ModelForm):
    class Meta:
        model = Package
        fields = ['name', 'sector', 'package_type', 'price', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Es. Trimestrale Fitness'}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
        labels = {
            'name': 'Nome pacchetto',
            'sector': 'Settore',
            'package_type': 'Tipo',
            'price': 'Prezzo (€)',
            'is_active': 'Attivo',
        }

class MemberCreationForm(UserCreationForm):
    """
    Form per la creazione di nuovi soci.
    Usa password1 e password2 mascherati (input type=password).
    """
    class Meta(UserCreationForm.Meta):
        model = Member
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'date_of_birth',  # aggiunto
            'phone_number',  # aggiunto
            'address',  # aggiunto
        )
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

class MemberChangeForm(UserChangeForm):
    """
    Form per la modifica dei dati di un socio esistente.
    Mostra la password in sola lettura (hash), con link per cambiarla.
    """
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Le password non sono memorizzate in chiaro. "
            "Puoi cambiarla usando <a href=\"../password/\">questo form</a>."
        ),
    )

    class Meta(UserChangeForm.Meta):
        model = Member
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'date_of_birth', 'phone_number', 'address',
        )
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    #
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     if self.instance and self.instance.id:
    #         password_url = reverse("members:change_member_password", args=[self.instance.id])
    #         self.fields['password'] = ReadOnlyPasswordHashField(
    #             label="Password",
    #             help_text=(
    #                 f"Le password non sono memorizzate in chiaro. "
    #                 f"Puoi cambiarla usando <a href='{password_url}'>questo form</a>."
    #             )
    #         )
    #     else:
    #         self.fields['password'] = ReadOnlyPasswordHashField(
    #             label="Password",
    #             help_text="Le password non sono memorizzate in chiaro."
    #         )

class MemberDocumentForm(forms.ModelForm):
    class Meta:
        model = MemberDocument
        fields = ['document_type', 'file', 'expiration_date', 'description']
        widgets = {
            'expiration_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'min': date.today().strftime('%Y-%m-%d')  # Imposta oggi come minimo
                }
            ),
        }


class AdminMemberDocumentForm(forms.ModelForm):
    class Meta:
        model = MemberDocument
        fields = ['member', 'document_type', 'file', 'expiration_date', 'description']
        widgets = {
            'expiration_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'min': date.today().strftime('%Y-%m-%d')  # Imposta oggi come minimo
                }
            ),
        }

# Formset per più documenti
MemberDocumentFormSet = modelformset_factory(
    MemberDocument,
    form=MemberDocumentForm,
    extra=0,  # default, puoi cambiare quanti documenti visualizzare
    #can_delete=True
)



# ---------------------------------------------------------------------
#  SubscriptionForm — ora si sceglie il PACCHETTO (obbligatorio).
#  Tipo e settore vengono dedotti dal pacchetto nel save() del modello.
# ---------------------------------------------------------------------
class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['package', 'start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'package': 'Pacchetto',
            'start_date': 'Data inizio',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['package'].queryset = (
            Package.objects.filter(is_active=True).select_related('sector')
        )
        self.fields['package'].required = True


# ---------------------------------------------------------------------
#  SubscriptionWithPaymentForm — crea abbonamento E registra il pagamento
#  nella stessa schermata. L'IMPORTO non e' nel form: e' bloccato dal
#  prezzo del pacchetto. Lo sconto resta modificabile.
# ---------------------------------------------------------------------
class SubscriptionWithPaymentForm(forms.Form):
    package = forms.ModelChoiceField(
        queryset=Package.objects.filter(is_active=True).select_related('sector'),
        label="Pacchetto", required=True,
    )
    start_date = forms.DateField(
        label="Data inizio",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    # --- pagamento ---
    payment_date = forms.DateField(
        label="Data pagamento", required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    payment_mode = forms.ChoiceField(
        label="Modalita'", required=False,
    )
    discount = forms.DecimalField(
        label="Sconto", required=False, min_value=0,
        decimal_places=2, max_digits=8, initial=0,
    )
    is_paid = forms.BooleanField(label="Pagato", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Popola le scelte di modalita' dal modello (import locale: evita cicli)
        from .models import Payment
        self.fields['payment_mode'].choices = [('', '---')] + list(Payment.PaymentMode.choices)


class SectorForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Es. FITNESS, SALA PESI, KARATE'}),
        }
        labels = {
            'name': 'Nome settore',
            'is_active': 'Attivo',
        }


class InstructorForm(forms.ModelForm):
    class Meta:
        model = Instructor
        fields = ['first_name', 'last_name', 'sectors', 'is_active']
        widgets = {
            'sectors': forms.CheckboxSelectMultiple(),
        }
        labels = {
            'first_name': 'Nome',
            'last_name': 'Cognome',
            'sectors': 'Settori/discipline',
            'is_active': 'Attivo',
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'payment_type', 'subscription', 'payment_date', 'due_date',
            'amount', 'enrollment_amount', 'discount',
            'payment_mode', 'fee_code', 'is_paid',
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'payment_type': 'Tipo',
            'subscription': 'Abbonamento collegato',
            'payment_date': 'Data pagamento',
            'due_date': 'Scadenza',
            'amount': 'Quota €',
            'enrollment_amount': 'Iscrizione €',
            'discount': 'Sconto €',
            'payment_mode': 'Modalità',
            'fee_code': 'Tariffa',
            'is_paid': 'Pagato',
        }

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subscription'].required = False
        self.fields['enrollment_amount'].required = False
        if member is not None:
            self.fields['subscription'].queryset = member.subscriptions.all()

class SubscriptionWithPaymentAndMemberForm(SubscriptionWithPaymentForm):
    member = forms.ModelChoiceField(
        queryset=None,  # impostato in __init__
        label="Socio", required=True,
    )

    field_order = ['member', 'package', 'start_date',
                   'payment_date', 'payment_mode', 'discount', 'is_paid']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Member
        self.fields['member'].queryset = Member.objects.filter(
            is_dismissed=False
        ).order_by('last_name', 'first_name')
