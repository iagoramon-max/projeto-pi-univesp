from django.db import models
from django.contrib.auth.models import User

class Profissional(models.Model):
    """
    Armazena os dados do profissional autônomo.
    Cada profissional é um usuário do sistema.
    """
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nome_completo = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    # Adicione outros campos se precisar, como especialidade, etc.

    def __str__(self):
        return self.nome_completo

class Servico(models.Model):
    """
    Armazena os serviços que um profissional oferece.
    """
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    duracao_minutos = models.IntegerField(default=60) # Duração padrão de 60 minutos

    def __str__(self):
        return self.nome

class Agendamento(models.Model):
    """
    O registro de um agendamento feito por um cliente.
    """
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField()
    nome_cliente = models.CharField(max_length=255)
    email_cliente = models.EmailField()
    telefone_cliente = models.CharField(max_length=20, blank=True, null=True)
    confirmado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nome_cliente} - {self.servico.nome} em {self.data_hora_inicio.strftime('%d/%m/%Y %H:%M')}"