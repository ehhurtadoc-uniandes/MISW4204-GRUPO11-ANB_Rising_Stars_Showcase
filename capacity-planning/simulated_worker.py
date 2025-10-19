#!/usr/bin/env python3
"""
Simulated Worker - Worker simulado para procesar trabajos de la cola
"""

import json
import time
import redis
import threading
from datetime import datetime
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimulatedWorker:
    """Worker simulado que procesa trabajos de la cola Redis"""
    
    def __init__(self, worker_id: str, redis_url: str = "redis://localhost:6379"):
        self.worker_id = worker_id
        self.redis_client = redis.from_url(redis_url)
        self.is_running = False
        self.processed_jobs = 0
        self.total_processing_time = 0.0
        
    def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesar un trabajo individual"""
        job_id = job_data.get("video_id", "unknown")
        video_size_mb = job_data.get("file_size_mb", 50)
        
        logger.info(f"Worker {self.worker_id} procesando job {job_id} ({video_size_mb}MB)")
        
        start_time = time.time()
        
        # Simular tiempo de procesamiento basado en tamaño del archivo
        # Tiempo base + tiempo proporcional al tamaño
        base_time = 1.0  # 1 segundo base
        size_factor = video_size_mb * 0.05  # 0.05 segundos por MB
        processing_time = base_time + size_factor
        
        # Simular procesamiento
        time.sleep(min(processing_time, 2.0))  # Máximo 2 segundos
        
        end_time = time.time()
        actual_time = end_time - start_time
        
        result = {
            "job_id": job_id,
            "worker_id": self.worker_id,
            "status": "completed",
            "processing_time": actual_time,
            "video_size_mb": video_size_mb,
            "throughput_mb_per_sec": video_size_mb / actual_time if actual_time > 0 else 0,
            "completed_at": datetime.now().isoformat()
        }
        
        self.processed_jobs += 1
        self.total_processing_time += actual_time
        
        logger.info(f"Worker {self.worker_id} completó job {job_id} en {actual_time:.2f}s")
        return result
    
    def run_worker(self):
        """Ejecutar worker en bucle continuo"""
        self.is_running = True
        logger.info(f"Worker {self.worker_id} iniciado")
        
        while self.is_running:
            try:
                # Obtener trabajo de la cola (bloqueante por 1 segundo)
                job_data = self.redis_client.brpop("video_processing_queue", timeout=1)
                
                if job_data:
                    # job_data es una tupla (queue_name, job_json)
                    job_json = job_data[1]
                    job_data = json.loads(job_json)
                    
                    # Procesar el trabajo
                    result = self.process_job(job_data)
                    
                    # Opcional: guardar resultado en otra cola
                    self.redis_client.lpush("processed_jobs", json.dumps(result))
                    
                else:
                    # No hay trabajos, continuar
                    continue
                    
            except Exception as e:
                logger.error(f"Error en worker {self.worker_id}: {e}")
                time.sleep(1)
        
        logger.info(f"Worker {self.worker_id} detenido")
    
    def stop_worker(self):
        """Detener el worker"""
        self.is_running = False
        logger.info(f"Worker {self.worker_id} solicitando parada")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del worker"""
        avg_processing_time = self.total_processing_time / self.processed_jobs if self.processed_jobs > 0 else 0
        
        return {
            "worker_id": self.worker_id,
            "processed_jobs": self.processed_jobs,
            "total_processing_time": self.total_processing_time,
            "avg_processing_time": avg_processing_time,
            "is_running": self.is_running
        }

class WorkerPool:
    """Pool de workers simulados"""
    
    def __init__(self, num_workers: int, redis_url: str = "redis://localhost:6379"):
        self.num_workers = num_workers
        self.redis_url = redis_url
        self.workers = []
        self.threads = []
        
    def start_workers(self):
        """Iniciar todos los workers"""
        logger.info(f"Iniciando pool de {self.num_workers} workers")
        
        for i in range(self.num_workers):
            worker_id = f"worker_{i+1}"
            worker = SimulatedWorker(worker_id, self.redis_url)
            self.workers.append(worker)
            
            # Crear thread para el worker
            thread = threading.Thread(target=worker.run_worker, daemon=True)
            thread.start()
            self.threads.append(thread)
            
            logger.info(f"Worker {worker_id} iniciado en thread")
    
    def stop_workers(self):
        """Detener todos los workers"""
        logger.info("Deteniendo todos los workers")
        
        for worker in self.workers:
            worker.stop_worker()
        
        # Esperar a que terminen los threads
        for thread in self.threads:
            thread.join(timeout=5)
        
        logger.info("Todos los workers detenidos")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del pool"""
        total_processed = sum(worker.processed_jobs for worker in self.workers)
        total_time = sum(worker.total_processing_time for worker in self.workers)
        avg_time = total_time / total_processed if total_processed > 0 else 0
        
        return {
            "num_workers": self.num_workers,
            "total_processed_jobs": total_processed,
            "total_processing_time": total_time,
            "avg_processing_time": avg_time,
            "throughput_jobs_per_min": total_processed / (total_time / 60) if total_time > 0 else 0,
            "worker_stats": [worker.get_stats() for worker in self.workers]
        }

def main():
    """Función principal para ejecutar workers"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulated Worker Pool")
    parser.add_argument("--workers", type=int, default=2, help="Número de workers")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="URL de Redis")
    parser.add_argument("--duration", type=int, default=60, help="Duración en segundos")
    
    args = parser.parse_args()
    
    # Crear pool de workers
    pool = WorkerPool(args.workers, args.redis_url)
    
    try:
        # Iniciar workers
        pool.start_workers()
        
        # Ejecutar por la duración especificada
        logger.info(f"Ejecutando por {args.duration} segundos...")
        time.sleep(args.duration)
        
        # Obtener estadísticas
        stats = pool.get_pool_stats()
        logger.info(f"Estadísticas del pool: {stats}")
        
    except KeyboardInterrupt:
        logger.info("Interrumpido por usuario")
    finally:
        # Detener workers
        pool.stop_workers()

if __name__ == "__main__":
    main()
