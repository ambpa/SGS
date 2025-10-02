# members/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, ReadOnlyPasswordHashField
from .models import Member


class MemberCreationForm(UserCreationForm):
    """
    Form per la creazione di nuovi soci.
    Usa password1 e password2 mascherati (input type=password).
    """
    class Meta(UserCreationForm.Meta):
        model = Member
        fields = ('username', 'first_name', 'last_name', 'email')


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
        fields = '__all__'
