"""
Worker RQ Customizado com Gerenciamento de Memória
Previne OOM monitorando uso de memória durante execução de jobs
"""
import psutil
import signal
import sys
import os
from rq import Worker
from rq.job import Job
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CustomWorker(Worker):
    """
    Worker RQ Customizado com gerenciamento de memória aprimorado e shutdown gracioso
    """
    
    def __init__(self, *args, max_memory_mb: int = 3500, max_jobs: int = 100, **kwargs):
        """
        Inicializa o worker customizado
        
        Args:
            max_memory_mb: Memória máxima em MB antes de rejeitar jobs (padrão: 3.5GB)
            max_jobs: Máximo de jobs antes de reiniciar worker (padrão: 100)
        """
        # Armazenar max_jobs antes de passar para pai
        self.max_jobs = max_jobs
        super().__init__(*args, **kwargs)
        self.max_memory_mb = max_memory_mb
        self.jobs_processed = 0
        
        # Configurar shutdown gracioso
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Trata shutdown gracioso em SIGTERM/SIGINT"""
        logger.info(f"🛑 Sinal {signum} recebido, encerrando graciosamente...")
        self.request_stop()
    
    def execute_job(self, job: Job, queue) -> bool:
        """
        Executa job com monitoramento de memória
        
        Args:
            job: Instância do Job RQ
            queue: Instância da fila
            
        Returns:
            bool: True se job executou com sucesso
        """
        try:
            # Verificar memória antes da execução
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb:
                error_msg = f"Limite de memória excedido: {memory_mb:.2f}MB > {self.max_memory_mb}MB"
                logger.error(f"❌ {error_msg}")
                
                job.set_status('failed')
                job.meta['error'] = error_msg
                job.meta['memory_mb'] = memory_mb
                job.save()
                
                return False
            
            # Log início do job
            logger.info(
                f"▶️  Iniciando job {job.id} | "
                f"Memória: {memory_mb:.2f}MB | "
                f"Jobs processados: {self.jobs_processed}/{self.max_jobs}"
            )
            
            # Executar job
            result = super().execute_job(job, queue)
            
            # Atualizar contador
            self.jobs_processed += 1
            
            # Log conclusão
            memory_after = process.memory_info().rss / 1024 / 1024
            logger.info(
                f"✅ Job {job.id} concluído | "
                f"Memória: {memory_after:.2f}MB | "
                f"Delta: {memory_after - memory_mb:+.2f}MB"
            )
            
            # Verificar se atingiu max jobs
            if self.jobs_processed >= self.max_jobs:
                logger.warning(
                    f"⚠️  Máximo de jobs atingido ({self.max_jobs}), "
                    "worker será reiniciado após job atual"
                )
                # Usar request_stop com argumentos dummy para evitar erro
                self.request_stop(None, None)
            
            return result
            
        except Exception as e:
            logger.exception(f"❌ Erro ao executar job {job.id}: {e}")
            job.set_status('failed')
            job.meta['error'] = str(e)
            job.save()
            return False
    
    def work(self, *args, **kwargs):
        """Sobrescreve método work para adicionar log de inicialização"""
        logger.info(
            f"🚀 Worker iniciado | "
            f"Memória Máx: {self.max_memory_mb}MB | "
            f"Jobs Máx: {self.max_jobs}"
        )
        return super().work(*args, **kwargs)


def _get_redis_url() -> str:
    """
    Obtém URL do Redis de forma segura.
    Tenta primeiro via módulo de secrets, depois variáveis de ambiente.
    """
    # 1. Tentar via módulo de secrets
    try:
        from app.core.secrets import get_redis_url
        return get_redis_url()
    except Exception as e:
        logger.warning(f"Falha ao carregar URL do Redis via secrets: {e}")
    
    # 2. Fallback: variáveis de ambiente
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    
    # 3. Senha: priorizar arquivo de secret, depois env var
    redis_password = ""
    secret_path = os.getenv("REDIS_PASSWORD_FILE", "/run/secrets/redis_password")
    
    if os.path.exists(secret_path):
        try:
            with open(secret_path, "r") as f:
                redis_password = f.read().strip()
        except Exception as e:
            logger.warning(f"Não foi possível ler secret do Redis: {e}")
    
    if not redis_password:
        redis_password = os.getenv("REDIS_PASSWORD", "")
    
    return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"


def main():
    """Ponto de entrada principal para worker customizado"""
    from redis import Redis
    
    redis_url = _get_redis_url()
    redis_conn = Redis.from_url(redis_url)
    
    # Criar worker
    worker = CustomWorker(
        ['transcription_tasks'],
        connection=redis_conn,
        max_memory_mb=int(os.getenv('WORKER_MAX_MEMORY_MB', '3500')),
        max_jobs=int(os.getenv('WORKER_MAX_JOBS', '100'))
    )
    
    # Iniciar worker
    worker.work(with_scheduler=True, burst=False)


if __name__ == '__main__':
    main()
