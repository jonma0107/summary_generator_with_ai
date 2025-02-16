from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User
from django.shortcuts import redirect, render


def user_login(request):
  if request.method == 'POST':
    username = request.POST.get('username')
    password = request.POST.get('password')
    group = request.POST.get('group')
    user = authenticate(username=username, password=password)
    if user is not None:
      # Verificar si el usuario pertenece al grupo especificado
      if group in [group.name for group in user.groups.all()]:
        login(request, user)
        return redirect('/index/')
      else:
        # El usuario no pertenece al grupo especificado
        error_message = 'User does not belong to the specified group'
        return render(request, 'login.html', {'error_message': error_message})
    else:
      error_message = 'Invalid username or password'
      return render(request, 'login.html', {'error_message': error_message})
  return render(request, 'login.html')


def user_signup(request):
  if request.method == 'POST':
    username = request.POST.get('username')
    email = request.POST.get('email')
    group = request.POST.get('group')
    password = request.POST.get('password')
    repeatPassword = request.POST.get('repeatPassword')

    if password == repeatPassword and group:
      try:
        user = User.objects.create_user(
            username=username, password=password, email=email)
        # Asigna el grupo al usuario
        if group == 'App' or group == 'summary' or group == 'Portfolio':
          user.groups.add(Group.objects.get(name=group))
        user.save()
        login(request, user)
        return redirect('/index/')
      except Exception as e:
        # Captura cualquier excepción que pueda ocurrir durante la creación
        # del usuario
        error_message = 'Error creating user: {}'.format(str(e))
        return render(
            request, 'signup.html', {
                'error_message': error_message})
    else:
      error_message = 'Passwords do not match or group not selected'
      return render(request, 'signup.html', {'error_message': error_message})

  return render(request, 'signup.html')


def user_logout(request):
  logout(request)
  return redirect('/')
