from django.shortcuts import render, redirect
from .models import Servico, Agendamento
import datetime

# --- ADICIONE ESTAS LINHAS NOVAS NO TOPO ---
import json
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
# -----------------------------------------

# --- CONFIGURAÇÃO DO BOT (Ajuste isso) ---
# NOTE: Você deve obter um token de acesso permanente do Facebook/Meta
ACCESS_TOKEN = "SEU_ACCESS_TOKEN_DO_FACEBOOK"
VERIFY_TOKEN = "univesp2025"
WHATSAPP_URL = "https://graph.facebook.com/v19.0/SEU_ID_DO_NUMERO_TELEFONE/messages"
# ------------------------------------------

def listar_servicos(request):
    servicos = Servico.objects.all()
    contexto = {
        'servicos': servicos
    }
    return render(request, 'agendamento/listar_servicos.html', contexto)

def agenda(request, servico_id):
    servico = Servico.objects.get(id=servico_id)
    hoje = datetime.date.today()
    # Filtra agendamentos a partir de hoje
    agendamentos_hoje = Agendamento.objects.filter(data_hora_inicio__date__gte=hoje)
    
    # Lógica de slots de horário para hoje (simplificado)
    horarios_ocupados = [agendamento.data_hora_inicio.strftime('%H:%M') for agendamento in agendamentos_hoje.filter(data_hora_inicio__date=hoje)]
    horarios_disponiveis = []
    
    for i in range(9, 18): # Horários das 09h às 17h
        horario = datetime.time(hour=i).strftime('%H:%M')
        if horario not in horarios_ocupados:
            horarios_disponiveis.append(horario)
            
    contexto = {
        'servico': servico,
        'horarios_disponiveis': horarios_disponiveis,
        'hoje': hoje,
    }
    return render(request, 'agendamento/agenda.html', contexto)


def confirmar_agendamento(request, servico_id, horario):
    servico = Servico.objects.get(id=servico_id)
    
    # Combina a data de hoje com o horário recebido
    data_hora_agendamento = datetime.datetime.combine(datetime.date.today(), datetime.datetime.strptime(horario, '%H:%M').time())

    if request.method == 'POST':
        nome_cliente = request.POST.get('nome_cliente')
        email_cliente = request.POST.get('email_cliente')

        # Cria um novo agendamento
        Agendamento.objects.create(
            servico=servico,
            data_hora_inicio=data_hora_agendamento,
            data_hora_fim=data_hora_agendamento + datetime.timedelta(minutes=servico.duracao_minutos),
            nome_cliente=nome_cliente,
            email_cliente=email_cliente,
        )
        # Redireciona para a lista de serviços após o agendamento
        return redirect('listar_servicos')

    contexto = {
        'servico': servico,
        'horario': horario,
    }
    return render(request, 'agendamento/confirmar_agendamento.html', contexto)

# ----------------------------------------------------------------------
# --- WEBHOOK / BOT DO WHATSAPP (CORREÇÃO DE SINTAXE) ---
# ----------------------------------------------------------------------

def enviar_mensagem_whatsapp(recipient_id, message_text):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": message_text},
    }
    response = requests.post(WHATSAPP_URL, headers=headers, json=data)
    return response.json()

@csrf_exempt
def webhook(request):
    # 1. VALIDAÇÃO DO WEBHOOK (GET)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("WEBHOOK VERIFICADO")
            return HttpResponse(challenge, status=200)
        else:
            return HttpResponse('Erro de validação do token.', status=403)

    # 2. PROCESSAMENTO DE MENSAGENS (POST)
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            
            # Checa se é uma mensagem válida e não um status
            if 'entry' in data and data['entry'] and 'changes' in data['entry'][0] and data['entry'][0]['changes']:
                change = data['entry'][0]['changes'][0]
                if 'messages' in change['value'] and change['value']['messages']:
                    message = change['value']['messages'][0]
                    from_number = message['from']
                    text = message['text']['body'].lower()
                    
                    print(f"Mensagem recebida de {from_number}: {text}")

                    # --- MÁQUINA DE ESTADOS BÁSICA (AQUI ESTAVA O SEU ERRO) ---
                    # Essa lógica deve ser complexa, mas vamos simplificar para não dar erro de sintaxe.
                    
                    if "olá" in text or "oi" in text or "menu" in text:
                        resposta = "Olá! Eu sou o assistente de agendamentos. Digite o número da opção:\n1. Ver Serviços e Agendar\n2. Falar com Atendente"
                        enviar_mensagem_whatsapp(from_number, resposta)
                    elif "1" == text:
                        resposta = "Ótimo! Para ver os serviços, acesse nosso site:\n[LINK DO SEU SITE AQUI] e escolha seu horário."
                        enviar_mensagem_whatsapp(from_number, resposta)
                    elif "2" == text:
                        resposta = "Aguarde um instante, você será redirecionado para a atendente."
                        enviar_mensagem_whatsapp(from_number, resposta)
                    else:
                        # Resposta padrão para qualquer outra coisa
                        resposta = "Não entendi sua mensagem. Digite 'Menu' para ver as opções novamente."
                        enviar_mensagem_whatsapp(from_number, resposta)
                        
            return HttpResponse('OK', status=200)
            
        except json.JSONDecodeError:
            return HttpResponse('Requisição inválida (JSON).', status=400)
        except Exception as e:
            print(f"Erro ao processar webhook: {e}")
            return HttpResponse('Erro interno do servidor.', status=500)
