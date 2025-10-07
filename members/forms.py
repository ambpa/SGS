# members/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, ReadOnlyPasswordHashField
from .models import Member, MemberDocument
from django.forms import modelformset_factory
from django import forms
from .models import Subscription
from datetime import date


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
    #extra=0,  # default, puoi cambiare quanti documenti visualizzare
    #can_delete=True
)



class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['subscription_type', 'category', 'start_date',]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }

