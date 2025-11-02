from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_servicos, name='listar_servicos'),
    path('agenda/<int:servico_id>/', views.agenda, name='agenda'),
    path('agendar/<int:servico_id>/<str:horario>/', views.confirmar_agendamento, name='confirmar_agendamento'),
    path('webhook/', views.webhook, name='webhook'), # <-- Adicione esta linha
]