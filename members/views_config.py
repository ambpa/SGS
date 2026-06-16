# members/views_config.py
# Fase 2 — Configurazione: settori e insegnanti.
# Protetto da office_required (segreteria/admin), coerente con views.py.

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Sector, Instructor
from .forms import SectorForm, InstructorForm, Package, PackageForm


def office_required(view_func):
    """Accesso riservato a segreteria/amministratore."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if u.is_staff or u.is_superuser or getattr(u, "is_office", False):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped


# ---------------------------------------------------------------------------
#  HUB CONFIGURAZIONE
# ---------------------------------------------------------------------------
@office_required
def config_home(request):
    context = {
        'active_nav': 'config',
        'sector_count': Sector.objects.count(),
        'instructor_count': Instructor.objects.count(),
        'package_count': Package.objects.count(),   # <-- AGGIUNTO
    }
    return render(request, 'config/config_home.html', context)

# ---------------------------------------------------------------------------
#  SETTORI
# ---------------------------------------------------------------------------
@office_required
def sector_list(request):
    sectors = Sector.objects.all().order_by('name')
    return render(request, 'config/sector_list.html', {
        'sectors': sectors, 'active_nav': 'config',
    })


@office_required
def sector_add(request):
    if request.method == 'POST':
        form = SectorForm(request.POST)
        if form.is_valid():
            sector = form.save()
            messages.success(request, f"Settore «{sector.name}» creato.")
            return redirect('members:sector_list')
    else:
        form = SectorForm()
    return render(request, 'config/sector_form.html', {
        'form': form, 'active_nav': 'config', 'title': 'Nuovo settore',
    })


@office_required
def sector_edit(request, pk):
    sector = get_object_or_404(Sector, pk=pk)
    if request.method == 'POST':
        form = SectorForm(request.POST, instance=sector)
        if form.is_valid():
            form.save()
            messages.success(request, f"Settore «{sector.name}» aggiornato.")
            return redirect('members:sector_list')
    else:
        form = SectorForm(instance=sector)
    return render(request, 'config/sector_form.html', {
        'form': form, 'active_nav': 'config',
        'title': f'Modifica settore', 'object': sector,
    })


@office_required
def sector_delete(request, pk):
    sector = get_object_or_404(Sector, pk=pk)
    if request.method == 'POST':
        name = sector.name
        try:
            sector.delete()
            messages.success(request, f"Settore «{name}» eliminato.")
        except Exception:
            messages.error(request, f"Impossibile eliminare «{name}»: è usato da soci o abbonamenti.")
        return redirect('members:sector_list')
    return render(request, 'config/confirm_delete.html', {
        'object': sector, 'object_type': 'settore',
        'cancel_url': 'members:sector_list', 'active_nav': 'config',
    })


# ---------------------------------------------------------------------------
#  INSEGNANTI
# ---------------------------------------------------------------------------
@office_required
def instructor_list(request):
    instructors = Instructor.objects.all().prefetch_related('sectors').order_by('last_name', 'first_name')
    return render(request, 'config/instructor_list.html', {
        'instructors': instructors, 'active_nav': 'config',
    })


@office_required
def instructor_add(request):
    if request.method == 'POST':
        form = InstructorForm(request.POST)
        if form.is_valid():
            instr = form.save()
            messages.success(request, f"Insegnante «{instr}» creato.")
            return redirect('members:instructor_list')
    else:
        form = InstructorForm()
    return render(request, 'config/instructor_form.html', {
        'form': form, 'active_nav': 'config', 'title': 'Nuovo insegnante',
    })


@office_required
def instructor_edit(request, pk):
    instr = get_object_or_404(Instructor, pk=pk)
    if request.method == 'POST':
        form = InstructorForm(request.POST, instance=instr)
        if form.is_valid():
            form.save()
            messages.success(request, f"Insegnante «{instr}» aggiornato.")
            return redirect('members:instructor_list')
    else:
        form = InstructorForm(instance=instr)
    return render(request, 'config/instructor_form.html', {
        'form': form, 'active_nav': 'config',
        'title': 'Modifica insegnante', 'object': instr,
    })


@office_required
def instructor_delete(request, pk):
    instr = get_object_or_404(Instructor, pk=pk)
    if request.method == 'POST':
        name = str(instr)
        try:
            instr.delete()
            messages.success(request, f"Insegnante «{name}» eliminato.")
        except Exception:
            messages.error(request, f"Impossibile eliminare «{name}»: è collegato a dei soci.")
        return redirect('members:instructor_list')
    return render(request, 'config/confirm_delete.html', {
        'object': instr, 'object_type': 'insegnante',
        'cancel_url': 'members:instructor_list', 'active_nav': 'config',
    })

@office_required
def package_list(request):
    packages = Package.objects.select_related('sector').all()
    return render(request, 'config/package_list.html', {
        'packages': packages, 'active_nav': 'config',
    })


@office_required
def package_add(request):
    if request.method == 'POST':
        form = PackageForm(request.POST)
        if form.is_valid():
            pkg = form.save()
            messages.success(request, f"Pacchetto «{pkg.name}» creato.")
            return redirect('members:package_list')
    else:
        form = PackageForm()
    return render(request, 'config/package_form.html', {
        'form': form, 'active_nav': 'config', 'title': 'Nuovo pacchetto',
    })


@office_required
def package_edit(request, pk):
    pkg = get_object_or_404(Package, pk=pk)
    if request.method == 'POST':
        form = PackageForm(request.POST, instance=pkg)
        if form.is_valid():
            form.save()
            messages.success(request, f"Pacchetto «{pkg.name}» aggiornato.")
            return redirect('members:package_list')
    else:
        form = PackageForm(instance=pkg)
    return render(request, 'config/package_form.html', {
        'form': form, 'active_nav': 'config', 'title': 'Modifica pacchetto', 'object': pkg,
    })


@office_required
def package_delete(request, pk):
    pkg = get_object_or_404(Package, pk=pk)
    if request.method == 'POST':
        name = pkg.name
        try:
            pkg.delete()
            messages.success(request, f"Pacchetto «{name}» eliminato.")
        except Exception:
            messages.error(request, f"Impossibile eliminare «{name}»: è in uso.")
        return redirect('members:package_list')
    return render(request, 'config/confirm_delete.html', {
        'object': pkg, 'object_type': 'pacchetto',
        'cancel_url': 'members:package_list', 'active_nav': 'config',
    })

