from django.test import TestCase
from django.urls import reverse

class PaginasAgendamentoTests(TestCase):

    def test_pagina_inicial_funciona(self):
        """
        Este teste verifica se a página inicial (lista de serviços)
        carrega corretamente.
        """
        # Pega o endereço da nossa página inicial
        url = reverse('listar_servicos')
        # O robô acessa a página
        response = self.client.get(url)
        # O robô verifica se a página respondeu com "sucesso" (código 200)
        self.assertEqual(response.status_code, 200)