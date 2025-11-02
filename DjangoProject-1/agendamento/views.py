from django.shortcuts import render, redirect
from .models import Servico, Agendamento
import datetime

# --- ADICIONE ESTAS LINHAS NOVAS NO TOPO ---
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
# -----------------------------------------

def listar_servicos(request):
    # ... (código existente, não precisa mexer)
    servicos = Servico.objects.all()
    contexto = {
        'servicos': servicos
    }
    return render(request, 'agendamento/listar_servicos.html', contexto)

def agenda(request, servico_id):
    # ... (código existente, não precisa mexer)
    servico = Servico.objects.get(id=servico_id)
    hoje = datetime.date.today()
    agendamentos_hoje = Agendamento.objects.filter(data_hora_inicio__date=hoje)
    horarios_ocupados = [agendamento.data_hora_inicio.strftime('%H:%M') for agendamento in agendamentos_hoje]
    horarios_disponiveis = []
    for i in range(9, 18):
        horario = datetime.time(hour=i).strftime('%H:%M')
        if horario not in horarios_ocupados:
            horarios_disponiveis.append(horario)
    contexto = {
        'servico': servico,
        'dia': hoje.strftime('%d/%m/%Y'),
        'horarios': horarios_disponiveis
    }
    return render(request, 'agendamento/agenda.html', contexto)

def confirmar_agendamento(request, servico_id, horario):
    # ... (código existente, não precisa mexer)
    servico = Servico.objects.get(id=servico_id)
    data_hora = datetime.datetime.strptime(f"{datetime.date.today()} {horario}", "%Y-%m-%d %H:%M")
    if request.method == 'POST':
        nome_cliente = request.POST.get('nome')
        email_cliente = request.POST.get('email')
        Agendamento.objects.create(
            servico=servico,
            data_hora_inicio=data_hora,
            data_hora_fim=data_hora + datetime.timedelta(minutes=servico.duracao_minutos),
            nome_cliente=nome_cliente,
            email_cliente=email_cliente,
        )
        return redirect('listar_servicos')
    contexto = {
        'servico': servico,
        'horario': horario,
    }
    return render(request, 'agendamento/confirmar_agendamento.html', contexto)

# --- ADICIONE A FUNÇÃO INTEIRA ABAIXO ---
@csrf_exempt # Desliga uma proteção de segurança SÓ para esta função
def webhook(request):
    # Este é o token que você inventou no painel do Facebook
    VERIFY_TOKEN = "univesp2025"

    # Se o Facebook está tentando validar nosso endereço
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("WEBHOOK VERIFICADO")
            return HttpResponse(challenge, status=200)
        else:
            return HttpResponse('erro de validação', status=403)

    # Se o Facebook está nos enviando uma mensagem de um usuário
    if request.method == 'POST':
        data = json.loads(request.body)
        print("MENSAGEM DO WHATSAPP RECEBIDA:")
        print(data) # Mostra a mensagem no nosso terminal do VS Code
        return HttpResponse(status=200)

    return HttpResponse('método não permitido', status=405)