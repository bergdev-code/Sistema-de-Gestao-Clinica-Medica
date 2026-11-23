import time

from django.db import connection


class TempoMiddleware:
    """Mostra no terminal quanto cada página levou e quantas consultas fez ao banco.

    Exemplo:  [TEMPO] GET /consultas/ -> 840 ms | 9 consultas ao banco = 610 ms
    Use só para investigar lentidão; depois pode remover do MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        duracoes = []

        def medir(execute, sql, params, many, context):
            inicio = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                duracoes.append(time.perf_counter() - inicio)

        inicio = time.perf_counter()
        with connection.execute_wrapper(medir):
            resposta = self.get_response(request)
        total = (time.perf_counter() - inicio) * 1000
        print(f"[TEMPO] {request.method} {request.path} -> {total:.0f} ms | "
              f"{len(duracoes)} consultas ao banco = {sum(duracoes) * 1000:.0f} ms")
        return resposta
