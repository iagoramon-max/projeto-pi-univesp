import os
import json
import requests
import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

# IMPORTANTE: Incluir Cliente nos imports
from .models import Servico, Agendamento, Cliente 


# --- VARIÁVEIS DE AMBIENTE (SEGREDO) ---
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
APP_SECRET = os.environ.get("APP_SECRET") 
API_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"


# --- FUNÇÕES EXISTENTES DO DJANGO ---
def listar_servicos(request):
    servicos = Servico.objects.all()
    contexto = {
        'servicos': servicos
    }
    return render(request, 'agendamento/listar_servicos.html', contexto)

def agenda(request, servico_id):
    # ... (código agenda, não alterado)
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
    # ... (código confirmar_agendamento, não alterado)
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


# --- FUNÇÃO WEBHOOK COMPLETA E CORRIGIDA ---

@csrf_exempt
def webhook(request):
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
        
        # Tentativa de decodificação à prova de falhas
        try:
            data = json.loads(request.body.decode('utf-8')) 
        except json.JSONDecodeError as e:
            print(f"ERRO DE DECODIFICAÇÃO JSON: {e}")
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
                
                # --- 1. ENCONTRAR OU CRIAR O CLIENTE ---
                cliente, created = Cliente.objects.get_or_create(
                    telefone=from_number
                )
                
                # Se for a primeira mensagem, define a mensagem de boas-vindas
                if created:
                    cliente.status = 0
                
                if message_type == 'text':
                    text_content = message_data['text']['body'].strip()
                    print(f"Mensagem de {from_number}: {text_content}")

                    # --- 2. MÁQUINA DE ESTADOS (STATE MACHINE) ---
                    
                    if cliente.status == 0:
                        # STATUS 0: CLIENTE NOVO. PEDE O NOME.
                        response_text = f"Olá, sou o assistente de agendamento. Para começarmos, qual é o seu nome completo?"
                        cliente.status = 1 
                        cliente.save()
                    
                    elif cliente.status == 1:
                        # STATUS 1: ESPERANDO NOME. SALVA E PEDE O SERVIÇO.
                        cliente.nome = text_content # Salva o nome fornecido
                        cliente.save()
                        
                        # Lista de serviços
                        servicos = Servico.objects.all()
                        lista_servicos = "\n".join([f"({s.id}) {s.nome} - R${s.valor:.2f}" for s in servicos])
                        
                        response_text = (
                            f"Obrigado, {cliente.nome}! Agora, escolha o serviço digitando apenas o número:\n"
                            "---------------------------------------\n"
                            f"{lista_servicos}\n"
                            "---------------------------------------"
                        )
                        cliente.status = 2 
                        cliente.save()
                        
                    elif cliente.status == 2:
                        # STATUS 2: ESPERANDO SERVIÇO. VALIDA ESCOLHA E PEDE A DATA.
                        try:
                            servico_id = int(text_content)
                            servico_escolhido = Servico.objects.get(id=servico_id)
                            
                            # Salva a escolha e avança
                            cliente.servico_escolhido = servico_escolhido
                            cliente.status = 3
                            cliente.save()
                            
                            response_text = (
                                f"Ótimo! Você escolheu *{servico_escolhido.nome}*. "
                                "Agora, digite a data que você prefere para o agendamento (Ex: 05/12)."
                            )
                        except (ValueError, Servico.DoesNotExist):
                            # Se o usuário digitou algo que não é número ou um ID inválido
                            response_text = "❌ Opção inválida. Por favor, digite apenas o número do serviço que deseja agendar."
                            
                    elif cliente.status == 3:
                        # STATUS 3: ESPERANDO DATA. VALIDA E PEDE O HORÁRIO.
                        # Aqui você colocaria a validação de data
                        data_string = text_content.strip()
                        
                        response_text = (
                            f"Perfeito! Para *{data_string}*, quais horários você gostaria de reservar?\n"
                            "Digite apenas o número de uma opção (Ex: 10:00, 11:30, etc.)."
                        )
                        # Este é o último status que vamos implementar hoje, Mestre.
                        cliente.status = 4 
                        cliente.save()
                        
                    else:
                        # Para qualquer outro status, informa que a sessão está ativa
                        response_text = "Desculpe, ainda estamos finalizando seu agendamento. Por favor, digite 'cancelar' para começar de novo."


                    # --- 3. PREPARAR RESPOSTA PARA A META ---
                    headers = {
                        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                        "Content-Type": "application/json",
                    }
                    response_body = {
                        "messaging_product": "whatsapp",
                        "to": from_number,
                        "type": "text",
                        "text": {
                            "body": response_text
                        }
                    }

                    # 4. ENVIO: Tenta enviar a mensagem para a Meta
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
