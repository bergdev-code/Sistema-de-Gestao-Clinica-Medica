"""Testes do app. Rode com:  python manage.py test func_django

Observação: as tabelas dos models com managed = False (médicos, agendamentos,
prontuários...) pertencem ao seu banco e o Django NÃO as cria no banco de teste.
A classe BaseClinica abaixo as cria só no banco de teste (nunca no seu banco real).
"""
import datetime as dt

from django.core.cache import cache
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from func_django import views
from func_django.models import (
    Agendamento, Alergia, Especialidade, HorarioMedico, Medico,
    MedicoEspecialidade, Pagamento, Perfil, Prontuario, StatusAgendamento,
    StatusPagamento, Usuario, func_django,
)

SENHA = "Senha@123"


# ---------------------------------------------------------------------------
# Regras puras (não precisam de banco)
# ---------------------------------------------------------------------------
class RegrasPuras(SimpleTestCase):
    def test_cpf_aceita_11_numeros_e_confere_digitos_quando_ligado(self):
        self.assertTrue(views.cpf_valido("12345678901"))
        self.assertFalse(views.cpf_valido("123"))
        with override_settings(CLINICA_VALIDAR_DIGITO_CPF=True):
            self.assertTrue(views.cpf_valido("52998224725"))
            self.assertFalse(views.cpf_valido("52998224726"))
            self.assertFalse(views.cpf_valido("11111111111"))

    def test_dias_da_semana(self):
        self.assertEqual(views.indice_dia_semana("Segunda-feira"), 0)
        self.assertEqual(views.indice_dia_semana("sábado"), 5)
        self.assertIsNone(views.indice_dia_semana("xyz"))

    def test_perfil_administrativo_nao_vira_administrador(self):
        self.assertEqual(views.chave_perfil("Admin"), "administrador")
        self.assertNotEqual(views.chave_perfil("Administrativo"), "administrador")

    def test_matriz_de_permissoes(self):
        a = views.acoes_do_perfil
        self.assertEqual(a("Recepcionista", "prontuarios"), set())          # sem conteúdo clínico
        self.assertEqual(a("Administrador", "prontuarios"), {"ver", "excluir"})
        self.assertIn("criar", a("Médico", "prontuarios"))
        self.assertEqual(a("Paciente", "pacientes"), set())
        self.assertEqual(a("Médico", "usuarios"), set())


# ---------------------------------------------------------------------------
# Base com banco
# ---------------------------------------------------------------------------
def _criar_tabelas_externas():
    existentes = set(connection.introspection.table_names())
    with connection.schema_editor() as editor:
        for modelo in (Medico, Especialidade, StatusAgendamento, Agendamento,
                       Alergia, Prontuario, MedicoEspecialidade, HorarioMedico):
            if modelo._meta.db_table not in existentes:
                editor.create_model(modelo)


class BaseClinica(TestCase):
    @classmethod
    def setUpClass(cls):
        _criar_tabelas_externas()  # antes de o TestCase abrir a transação
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.perfis = {n: Perfil.objects.create(nome_perfil=n)
                      for n in ("Administrador", "Recepcionista", "Médico", "Paciente")}
        cls.st = {n: StatusAgendamento.objects.create(descricao=n)
                  for n in ("Solicitada", "Agendada", "Cancelada")}
        cls.sp = {n: StatusPagamento.objects.create(descricao=n)
                  for n in ("Pendente", "Concluído", "Cancelado")}
        cls.med_a = Medico.objects.create(crm="111111", nome="Dr A", telefone="81999990001")
        cls.med_b = Medico.objects.create(crm="222222", nome="Dr B", telefone="81999990002")
        cls.esp = Especialidade.objects.create(nome="Clínica")
        MedicoEspecialidade.objects.create(medico=cls.med_a, especialidade=cls.esp)
        cls.p1 = func_django.objects.create(cpf="11111111111", nome="Paciente Um")
        cls.p2 = func_django.objects.create(cpf="22222222222", nome="Paciente Dois")
        cls._usuario("admin", "Administrador")
        cls._usuario("recep", "Recepcionista")
        cls._usuario("medicoa", "Médico", medico=cls.med_a)
        cls._usuario("pac", "Paciente", paciente=cls.p1)
        cls._usuario("pacdois", "Paciente", paciente=cls.p2)
        # consulta aceita do paciente 1 com o médico A (liga o médico ao paciente)
        cls.consulta = cls.nova_consulta(cls.p1, cls.med_a, dias=7, status="Agendada")
        Prontuario.objects.create(paciente=cls.p1, medico=cls.med_a, diagnostico="DIAGNOSTICO-SECRETO")

    @classmethod
    def _usuario(cls, nome, perfil, **vinculos):
        salt = "ab" * 16
        return Usuario.objects.create(
            username=nome, email=f"{nome}@teste.com", salt=salt,
            senha_hash=views.gerar_hash(SENHA, salt), id_perfil=cls.perfis[perfil], **vinculos)

    @classmethod
    def nova_consulta(cls, paciente, medico, dias=7, hora=10, status="Agendada"):
        quando = timezone.make_aware(
            dt.datetime.combine(timezone.localdate() + dt.timedelta(days=dias), dt.time(hora, 0)))
        return Agendamento.objects.create(
            paciente=paciente, medico=medico, data_hora=quando, status=cls.st[status], tipo="Consulta")

    def setUp(self):
        cache.clear()  # zera o bloqueio de tentativas de login entre os testes

    def entrar(self, usuario, senha=SENHA):
        return self.client.post("/", {"identificador": usuario, "senha": senha})


# ---------------------------------------------------------------------------
# Acesso e permissões
# ---------------------------------------------------------------------------
class AcessoEPermissoes(BaseClinica):
    def test_login_painel_e_conta_carregam_para_todos_os_perfis(self):
        for usuario in ("admin", "recep", "medicoa", "pac"):
            self.client.logout()
            resposta = self.entrar(usuario)
            self.assertEqual(resposta.status_code, 302, usuario)
            self.assertEqual(self.client.get("/painel/").status_code, 200, usuario)
            self.assertEqual(self.client.get("/conta/").status_code, 200, usuario)

    def test_painel_da_recepcao_mostra_atalhos(self):
        self.entrar("recep")
        self.assertContains(self.client.get("/painel/"), "Pacientes")

    def test_anonimo_vai_para_o_login_e_volta_depois(self):
        resposta = self.client.get("/pacientes/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("next=%2Fpacientes%2F", resposta["Location"])
        resposta = self.client.post("/", {"identificador": "recep", "senha": SENHA, "next": "/pacientes/"})
        self.assertEqual(resposta["Location"], "/pacientes/")

    def test_next_para_outro_site_e_ignorado(self):
        resposta = self.client.post("/", {"identificador": "recep", "senha": SENHA, "next": "https://evil.example/"})
        self.assertEqual(resposta["Location"], "/painel/")

    def test_bloqueia_apos_varias_senhas_erradas(self):
        for _ in range(views.LIMITE_TENTATIVAS):
            self.entrar("recep", "errada")
        self.assertEqual(self.entrar("recep", SENHA).status_code, 429)

    def test_recepcao_nao_acessa_prontuarios(self):
        self.entrar("recep")
        self.assertEqual(self.client.get("/prontuarios/").status_code, 403)
        ficha = self.client.get(f"/pacientes/{self.p1.cpf}/")
        self.assertEqual(ficha.status_code, 200)
        self.assertNotContains(ficha, "DIAGNOSTICO-SECRETO")

    def test_medico_ve_so_os_seus_pacientes_e_prontuarios(self):
        self.entrar("medicoa")
        lista = self.client.get("/pacientes/")
        self.assertContains(lista, "Paciente Um")
        self.assertNotContains(lista, "Paciente Dois")
        self.assertEqual(self.client.get(f"/pacientes/{self.p2.cpf}/").status_code, 404)
        self.assertContains(self.client.get(f"/pacientes/{self.p1.cpf}/"), "DIAGNOSTICO-SECRETO")

    def test_medico_nao_ve_solicitacao_ainda_nao_aceita(self):
        outro = func_django.objects.create(cpf="33333333333", nome="So Solicitou")
        self.nova_consulta(outro, self.med_a, dias=9, status="Solicitada")
        self.entrar("medicoa")
        self.assertNotContains(self.client.get("/pacientes/"), "So Solicitou")

    def test_paciente_so_ve_o_que_e_seu(self):
        self.entrar("pac")
        self.assertEqual(self.client.get("/pacientes/").status_code, 403)
        self.assertEqual(self.client.get("/usuarios/").status_code, 403)
        self.assertEqual(self.client.get("/consultas/").status_code, 200)

    def test_so_admin_gerencia_usuarios_e_nao_exclui_a_si_mesmo(self):
        self.entrar("recep")
        self.assertEqual(self.client.get("/usuarios/").status_code, 403)
        self.client.logout()
        self.entrar("admin")
        self.assertEqual(self.client.get("/usuarios/").status_code, 200)
        eu = Usuario.objects.get(username="admin")
        self.client.post(f"/usuarios/{eu.pk}/excluir/")
        self.assertTrue(Usuario.objects.filter(pk=eu.pk).exists())

    def test_excluir_exige_post_e_id_invalido_da_404(self):
        self.entrar("admin")
        self.assertEqual(self.client.get(f"/especialidades/{self.esp.pk}/excluir/").status_code, 405)
        self.assertEqual(self.client.post("/especialidades/abc/excluir/").status_code, 404)


# ---------------------------------------------------------------------------
# Prontuário
# ---------------------------------------------------------------------------
class ProntuarioTests(BaseClinica):
    def test_medico_grava_sempre_em_seu_nome(self):
        self.entrar("medicoa")
        self.client.post("/prontuarios/novo/", {
            "paciente": self.p1.cpf, "medico": self.med_b.crm, "diagnostico": "Gripe"})
        novo = Prontuario.objects.get(diagnostico="Gripe")
        self.assertEqual(novo.medico_id, self.med_a.crm)

    def test_medico_nao_grava_para_paciente_que_nao_e_dele(self):
        self.entrar("medicoa")
        self.client.post("/prontuarios/novo/", {"paciente": self.p2.cpf, "diagnostico": "Indevido"})
        self.assertFalse(Prontuario.objects.filter(diagnostico="Indevido").exists())

    def test_admin_nao_cria_prontuario(self):
        self.entrar("admin")
        self.assertEqual(self.client.get("/prontuarios/novo/").status_code, 403)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
class ConsultaTests(BaseClinica):
    def test_aceitar_define_medico_e_horario(self):
        sol = self.nova_consulta(self.p2, self.med_a, dias=10, hora=0, status="Solicitada")
        self.entrar("recep")
        self.assertEqual(self.client.get(f"/consultas/{sol.pk}/aceitar/").status_code, 200)
        self.client.post(f"/consultas/{sol.pk}/aceitar/", {"medico": self.med_a.crm, "horario": "09:30"})
        sol.refresh_from_db()
        self.assertEqual(sol.status.descricao, "Agendada")
        self.assertEqual(timezone.localtime(sol.data_hora).strftime("%H:%M"), "09:30")

    def test_horario_fora_da_agenda_do_medico_e_recusado(self):
        sol = self.nova_consulta(self.p2, self.med_a, dias=10, hora=0, status="Solicitada")
        dia = views.DIAS_SEMANA[timezone.localtime(sol.data_hora).weekday()]
        HorarioMedico.objects.create(medico=self.med_a, dia_semana=dia,
                                     hora_inicio=dt.time(8, 0), hora_fim=dt.time(12, 0))
        self.entrar("recep")
        self.client.post(f"/consultas/{sol.pk}/aceitar/", {"medico": self.med_a.crm, "horario": "20:00"})
        sol.refresh_from_db()
        self.assertEqual(sol.status.descricao, "Solicitada")
        self.client.post(f"/consultas/{sol.pk}/aceitar/", {"medico": self.med_a.crm, "horario": "09:00"})
        sol.refresh_from_db()
        self.assertEqual(sol.status.descricao, "Agendada")

    def test_paciente_cancela_a_propria_e_nao_a_dos_outros(self):
        outra = self.nova_consulta(self.p2, self.med_a, dias=11, status="Agendada")
        self.entrar("pac")
        self.assertEqual(self.client.post(f"/consultas/{outra.pk}/cancelar/").status_code, 404)
        self.client.post(f"/consultas/{self.consulta.pk}/cancelar/")
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.status.descricao, "Cancelada")

    def test_nao_cancela_com_pagamento_concluido(self):
        Pagamento.objects.create(agendamento=self.consulta, descricao="x", valor=60,
                                 forma_pagamento="Pix", status_pagamento=self.sp["Concluído"],
                                 data_pagamento=timezone.localdate())
        self.entrar("recep")
        self.client.post(f"/consultas/{self.consulta.pk}/cancelar/")
        self.consulta.refresh_from_db()
        self.assertEqual(self.consulta.status.descricao, "Agendada")

    def test_solicitacao_repetida_nao_duplica(self):
        self.entrar("pac")
        dados = {"tipo": "Consulta", "especialidade": self.esp.pk,
                 "data": (timezone.localdate() + dt.timedelta(days=20)).isoformat()}
        self.client.post("/consultas/solicitar/", dados)
        self.client.post("/consultas/solicitar/", dados)
        self.assertEqual(Agendamento.objects.filter(paciente=self.p1, status=self.st["Solicitada"]).count(), 1)


# ---------------------------------------------------------------------------
# Financeiro
# ---------------------------------------------------------------------------
class FinanceiroTests(BaseClinica):
    def test_dinheiro_so_uma_vez_e_so_recepcao(self):
        self.entrar("admin")
        self.client.post(f"/pagamentos/dinheiro/{self.consulta.pk}/")
        self.assertEqual(Pagamento.objects.count(), 0)  # admin não registra dinheiro
        self.client.logout()
        self.entrar("recep")
        self.client.post(f"/pagamentos/dinheiro/{self.consulta.pk}/")
        self.client.post(f"/pagamentos/dinheiro/{self.consulta.pk}/")
        self.assertEqual(Pagamento.objects.filter(agendamento=self.consulta).count(), 1)

    def test_paciente_paga_uma_vez_e_recepcao_confirma(self):
        self.entrar("pac")
        dados = {"agendamento": self.consulta.pk, "valor": "60.00", "forma_pagamento": "Pix"}
        self.client.post("/financeiro/pagar/", dados)
        self.client.post("/financeiro/pagar/", dados)  # repetido: recusado
        pag = Pagamento.objects.get(agendamento=self.consulta)
        self.assertEqual(pag.status_pagamento.descricao, "Pendente")
        self.client.logout()
        self.entrar("recep")
        self.client.post(f"/financeiro/{pag.pk}/confirmar/")
        pag.refresh_from_db()
        self.assertEqual(pag.status_pagamento.descricao, "Concluído")
        self.assertContains(self.client.get("/financeiro/"), "Concluído")

    def test_pagar_consulta_em_cartoes_funciona(self):
        self.entrar("pac")
        self.assertEqual(self.client.get("/financeiro/pagamento/").status_code, 200)

    def test_paciente_nao_confirma_nem_cancela_pagamento(self):
        pag = Pagamento.objects.create(agendamento=self.consulta, descricao="x", valor=60,
                                       forma_pagamento="Pix", status_pagamento=self.sp["Pendente"],
                                       data_pagamento=timezone.localdate())
        self.entrar("pac")
        self.assertEqual(self.client.post(f"/financeiro/{pag.pk}/confirmar/").status_code, 403)
        self.assertEqual(self.client.post(f"/financeiro/{pag.pk}/cancelar/").status_code, 403)


# ---------------------------------------------------------------------------
# Cadastros e edição
# ---------------------------------------------------------------------------
class CadastroTests(BaseClinica):
    def test_recepcao_cadastra_paciente_com_mascara_e_edita(self):
        self.entrar("recep")
        self.client.post("/pacientes/novo/", {
            "cpf": "444.444.444-44", "nome": "Com Mascara", "telefone": "(81) 99999-0000"})
        pac = func_django.objects.get(cpf="44444444444")
        self.assertEqual(pac.telefone, "81999990000")
        self.client.post(f"/pacientes/{pac.cpf}/editar/", {"nome": "Nome Corrigido", "telefone": "8133334444"})
        pac.refresh_from_db()
        self.assertEqual(pac.nome, "Nome Corrigido")
        self.assertEqual(pac.cpf, "44444444444")  # a chave não muda

    def test_medico_nao_edita_paciente_mas_registra_alergia(self):
        self.entrar("medicoa")
        self.assertEqual(self.client.get(f"/pacientes/{self.p1.cpf}/editar/").status_code, 403)
        self.client.post(f"/pacientes/{self.p1.cpf}/alergias/nova/", {"descricao": "Dipirona"})
        self.assertTrue(Alergia.objects.filter(paciente=self.p1, descricao="Dipirona").exists())

    def test_cadastro_publico_cria_paciente_e_login(self):
        resposta = self.client.post("/cadastro/", {
            "username": "novo", "email": "novo@teste.com", "senha": "Senha@1234", "confirmar_senha": "Senha@1234",
            "cpf": "555.555.555-55", "nome": "Novo Paciente", "telefone": "(81) 98888-7777",
            "data_nascimento": "1990-05-10"})
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Usuario.objects.filter(username="novo", paciente_id="55555555555").exists())

    def test_horario_do_medico_valida_fim_depois_do_inicio(self):
        self.entrar("admin")
        self.client.post("/horarios/novo/", {"medico": self.med_a.crm, "dia_semana": "Segunda-feira",
                                             "hora_inicio": "10:00", "hora_fim": "09:00"})
        self.assertEqual(HorarioMedico.objects.count(), 0)
