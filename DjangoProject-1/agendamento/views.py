import os
import json
import requests # NOVO: Para fazer requisições HTTP para a Meta
import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

# IMPORTANTE: Adicionar o modelo Cliente (mesmo que as migrações tenham falhado)
from .models import Servico, Agendamento, Cliente 


# --- VARIÁVEIS DE AMBIENTE (SEGREDO) ---
# O Render nos obriga a ler segredos dessa forma.
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
# NOVO: Variável APP_SECRET que discutimos (para segurança futura)
APP_SECRET = os.environ.get("APP_SECRET") 
API_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"


# --- FUNÇÕES EXISTENTES DO DJANGO (Não mexer) ---

def listar_servicos(request):
    servicos = Servico.objects.all()
    contexto = {
        'servicos': servicos
    }
    return render(request, 'agendamento/listar_servicos.html', contexto)

def agenda(request, servico_id):
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


# --- FUNÇÃO WEBHOOK ATUALIZADA (O CÉREBRO DO BOT) ---

@csrf_exempt
def webhook(request):
    # Este é o token que você inventou no painel do Facebook
    VERIFY_TOKEN = "univesp2025"

    # 1. VERIFICAÇÃO DO WEBHOOK (GET)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("WEBHOOK VERIFICADO")
            return HttpResponse(challenge, status=200)
        else:
            return HttpResponse('erro de validação', status=403)

    # 2. RECEBIMENTO E RESPOSTA DA MENSAGEM (POST)
    if request.method == 'POST':
        
        # --- CORREÇÃO CRÍTICA AQUI ---
        try:
            # Tenta decodificar o corpo da requisição com UTF-8
            data = json.loads(request.body.decode('utf-8')) 
        except json.JSONDecodeError as e:
            print(f"ERRO DE DECODIFICAÇÃO JSON: {e}")
            # Se a decodificação falhar, não podemos processar. Retorna 400.
            return HttpResponse(status=400) 
        
        print("MENSAGEM DO WHATSAPP RECEBIDA:")
        print(data)  

        try:
            # Garante que é um tipo de mensagem válida (e não um status de leitura)
            if 'messages' in data['entry'][0]['changes'][0]['value']:
                
                # Extrai dados essenciais
                message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
                from_number = message_data['from']
                message_type = message_data['type']
                
                # A Meta só envia o 'text' se for uma mensagem de texto simples
                if message_type == 'text':
                    text_content = message_data['text']['body']
                    print(f"Mensagem de {from_number}: {text_content}")

                    # --- LÓGICA DE RESPOSTA ---
                    # 1. Headers (Inclui seu token secreto)
                    headers = {
                        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                        "Content-Type": "application/json",
                    }

                    # 2. Corpo da Resposta (Mensagem de Boas-Vindas)
                    response_body = {
                        "messaging_product": "whatsapp",
                        "to": from_number,
                        "type": "text",
                        "text": {
                            "body": "🤖 Olá! Sou o assistente de agendamento. Vamos começar seu agendamento!"
                        }
                    }

                    # 3. ENVIO: Tenta enviar a mensagem para a Meta
                    response = requests.post(API_URL, headers=headers, json=response_body)
                    
                    if response.status_code == 200:
                        print("Resposta enviada com sucesso para a Meta.")
                    else:
                        # Este erro é crítico, precisamos saber se o token está errado
                        print(f"ERRO ao enviar para Meta: Status {response.status_code} - {response.text}")
                    # --- FIM DA LÓGICA DE RESPOSTA ---

            return HttpResponse(status=200) # Sempre responda 200 para a Meta, mesmo se der erro

        except Exception as e:
            # Erro geral de processamento (pode ser o formato do payload inesperado)
            print(f"ERRO ao processar payload: {e}")
            return HttpResponse(status=200)

    return HttpResponse('método não permitido', status=405)
