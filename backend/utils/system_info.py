"""Diagnosticos basicos de hardware, usados quando o KORA roda em modo local."""

import platform

import psutil


def get_system_info() -> dict:
    memoria = psutil.virtual_memory()
    disco = psutil.disk_usage("/")

    return {
        "sistema_operacional": platform.system(),
        "versao_so": platform.version(),
        "arquitetura": platform.machine(),
        "processador": platform.processor(),
        "cpu_nucleos_fisicos": psutil.cpu_count(logical=False),
        "cpu_nucleos_logicos": psutil.cpu_count(logical=True),
        "cpu_uso_percentual": psutil.cpu_percent(interval=0.5),
        "memoria_total_gb": round(memoria.total / (1024 ** 3), 2),
        "memoria_disponivel_gb": round(memoria.available / (1024 ** 3), 2),
        "memoria_uso_percentual": memoria.percent,
        "disco_total_gb": round(disco.total / (1024 ** 3), 2),
        "disco_livre_gb": round(disco.free / (1024 ** 3), 2),
    }


if __name__ == "__main__":
    for chave, valor in get_system_info().items():
        print(f"{chave}: {valor}")
