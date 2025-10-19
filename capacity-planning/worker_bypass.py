#!/usr/bin/env python3
"""
Worker Bypass - Plan B Implementation
Bypass de la web para inyección directa en la cola Redis
"""

import asyncio
import json
import time
import uuid
import psutil
import redis
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class WorkerMetrics:
    """Métricas del worker"""
    videos_processed: int = 0
    total_time: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    queue_size: int = 0
    errors: int = 0

class WorkerBypass:
    """Bypass de la web para inyección directa en la cola"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.metrics = WorkerMetrics()
        self.start_time = None
        self.job_ids = []
        
    def create_test_video_payload(self, video_size_mb: int, video_id: str = None) -> Dict[str, Any]:
        """Crear payload realista para procesamiento de video"""
        if not video_id:
            video_id = str(uuid.uuid4())
            
        # Simular archivo de video realista
        payload = {
            "video_id": video_id,
            "original_path": f"/test_videos/{video_id}.mp4",
            "processed_path": f"/processed_videos/processed_{video_id}.mp4",
            "file_size_mb": video_size_mb,
            "duration_seconds": 30,  # Duración típica
            "resolution": "1920x1080",
            "bitrate": "2000k",
            "format": "mp4",
            "created_at": datetime.now().isoformat(),
            "task_id": str(uuid.uuid4())
        }
        return payload
    
    def inject_jobs_to_queue(self, num_jobs: int, video_size_mb: int = 50) -> List[str]:
        """Inyectar trabajos directamente en la cola Redis"""
        job_ids = []
        
        for i in range(num_jobs):
            job_id = str(uuid.uuid4())
            payload = self.create_test_video_payload(video_size_mb, job_id)
            
            # Enviar a la cola de procesamiento
            self.redis_client.lpush("video_processing_queue", json.dumps(payload))
            job_ids.append(job_id)
            
        logger.info(f"Inyectados {num_jobs} trabajos en la cola (tamaño: {video_size_mb}MB)")
        return job_ids
    
    def monitor_queue_size(self) -> int:
        """Monitorear tamaño de la cola"""
        return self.redis_client.llen("video_processing_queue")
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Obtener métricas del sistema"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available_gb": memory.available / (1024**3)
        }
    
    def simulate_worker_processing(self, job_id: str, video_size_mb: int) -> Dict[str, Any]:
        """Simular procesamiento de video por el worker"""
        start_time = time.time()
        
        # Simular tiempo de procesamiento basado en tamaño del archivo
        # Tiempo base + tiempo proporcional al tamaño
        base_time = 2.0  # 2 segundos base
        size_factor = video_size_mb * 0.1  # 0.1 segundos por MB
        processing_time = base_time + size_factor
        
        # Simular procesamiento (reducido para demo)
        time.sleep(min(processing_time, 0.5))  # Máximo 0.5 segundos para demo
        
        end_time = time.time()
        actual_time = end_time - start_time
        
        # Simular métricas del worker
        system_metrics = self.get_system_metrics()
        
        result = {
            "job_id": job_id,
            "status": "completed",
            "processing_time": actual_time,
            "video_size_mb": video_size_mb,
            "throughput_mb_per_sec": video_size_mb / actual_time if actual_time > 0 else 0,
            "cpu_usage": system_metrics["cpu_usage"],
            "memory_usage": system_metrics["memory_usage"],
            "completed_at": datetime.now().isoformat()
        }
        
        return result

class WorkerCapacityTester:
    """Tester de capacidad del worker"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.bypass = WorkerBypass(redis_url)
        self.results = []
        
    def run_saturation_test(self, video_size_mb: int, max_workers: int = 4) -> Dict[str, Any]:
        """Ejecutar prueba de saturación del worker"""
        logger.info(f"Iniciando prueba de saturación: {video_size_mb}MB, {max_workers} workers")
        
        # Limpiar cola
        self.bypass.redis_client.delete("video_processing_queue")
        
        # Inyectar trabajos progresivamente
        saturation_results = []
        job_batch_sizes = [1, 2, 5, 10, 20, 50, 100]
        
        for batch_size in job_batch_sizes:
            logger.info(f"Probando con {batch_size} trabajos en cola")
            
            # Inyectar trabajos
            job_ids = self.bypass.inject_jobs_to_queue(batch_size, video_size_mb)
            
            # Monitorear procesamiento
            start_time = time.time()
            initial_queue_size = self.bypass.monitor_queue_size()
            
            # Esperar a que se procesen (simular workers)
            processing_time = 0
            while self.bypass.monitor_queue_size() > 0 and processing_time < 300:  # 5 min max
                time.sleep(1)
                processing_time += 1
                
                # Obtener métricas del sistema
                system_metrics = self.bypass.get_system_metrics()
                
                if system_metrics["cpu_usage"] > 90:  # Punto de saturación
                    logger.warning(f"Saturación detectada en CPU: {system_metrics['cpu_usage']}%")
                    break
            
            end_time = time.time()
            final_queue_size = self.bypass.monitor_queue_size()
            
            # Calcular métricas
            total_time = end_time - start_time
            videos_processed = initial_queue_size - final_queue_size
            throughput = videos_processed / (total_time / 60) if total_time > 0 else 0
            
            result = {
                "batch_size": batch_size,
                "video_size_mb": video_size_mb,
                "workers": max_workers,
                "videos_processed": videos_processed,
                "total_time_seconds": total_time,
                "throughput_videos_per_min": throughput,
                "queue_remaining": final_queue_size,
                "cpu_usage": system_metrics["cpu_usage"],
                "memory_usage": system_metrics["memory_usage"],
                "saturated": system_metrics["cpu_usage"] > 90
            }
            
            saturation_results.append(result)
            
            # Si está saturado, parar
            if result["saturated"]:
                logger.info(f"Saturación alcanzada con {batch_size} trabajos")
                break
                
            # Limpiar cola para siguiente prueba
            self.bypass.redis_client.delete("video_processing_queue")
            time.sleep(2)  # Pausa entre pruebas
        
        return {
            "test_type": "saturation",
            "video_size_mb": video_size_mb,
            "workers": max_workers,
            "results": saturation_results,
            "max_sustainable_batch": max([r["batch_size"] for r in saturation_results if not r["saturated"]]),
            "max_throughput": max([r["throughput_videos_per_min"] for r in saturation_results])
        }
    
    def run_sustained_test(self, video_size_mb: int, workers: int, duration_minutes: int = 5) -> Dict[str, Any]:
        """Ejecutar prueba sostenida del worker"""
        logger.info(f"Iniciando prueba sostenida: {video_size_mb}MB, {workers} workers, {duration_minutes} min")
        
        # Limpiar cola
        self.bypass.redis_client.delete("video_processing_queue")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        sustained_results = []
        videos_processed = 0
        errors = 0
        
        # Mantener cola con trabajos constantes
        while time.time() < end_time:
            current_time = time.time()
            
            # Inyectar trabajos si la cola está vacía
            queue_size = self.bypass.monitor_queue_size()
            if queue_size < 5:  # Mantener 5 trabajos en cola
                try:
                    self.bypass.inject_jobs_to_queue(5, video_size_mb)
                    videos_processed += 5
                except Exception as e:
                    logger.error(f"Error inyectando trabajos: {e}")
                    errors += 1
            
            # Obtener métricas cada 30 segundos
            if int(current_time - start_time) % 30 == 0:
                system_metrics = self.bypass.get_system_metrics()
                
                result = {
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_minutes": (current_time - start_time) / 60,
                    "queue_size": queue_size,
                    "videos_processed": videos_processed,
                    "errors": errors,
                    "cpu_usage": system_metrics["cpu_usage"],
                    "memory_usage": system_metrics["memory_usage"]
                }
                
                sustained_results.append(result)
                logger.info(f"Minuto {result['elapsed_minutes']:.1f}: {videos_processed} videos, CPU: {system_metrics['cpu_usage']:.1f}%")
            
            time.sleep(1)
        
        # Calcular métricas finales
        total_time = time.time() - start_time
        final_throughput = videos_processed / (total_time / 60)
        
        return {
            "test_type": "sustained",
            "video_size_mb": video_size_mb,
            "workers": workers,
            "duration_minutes": duration_minutes,
            "videos_processed": videos_processed,
            "errors": errors,
            "throughput_videos_per_min": final_throughput,
            "results": sustained_results,
            "stable": errors < (videos_processed * 0.05)  # Menos del 5% de errores
        }
    
    def run_capacity_analysis(self) -> Dict[str, Any]:
        """Ejecutar análisis completo de capacidad"""
        logger.info("Iniciando análisis completo de capacidad del worker")
        
        # Configuraciones de prueba
        video_sizes = [50, 100]  # MB
        worker_configs = [1, 2, 4]  # Número de workers
        
        capacity_results = []
        
        for video_size in video_sizes:
            for workers in worker_configs:
                logger.info(f"Probando: {video_size}MB, {workers} workers")
                
                # Prueba de saturación
                saturation_result = self.run_saturation_test(video_size, workers)
                
                # Prueba sostenida (80% de la capacidad máxima)
                max_batch = saturation_result["max_sustainable_batch"]
                sustained_batch = int(max_batch * 0.8)
                
                if sustained_batch > 0:
                    sustained_result = self.run_sustained_test(video_size, workers, 3)  # 3 minutos
                else:
                    sustained_result = {"stable": False, "throughput_videos_per_min": 0}
                
                # Combinar resultados
                combined_result = {
                    "video_size_mb": video_size,
                    "workers": workers,
                    "saturation": saturation_result,
                    "sustained": sustained_result,
                    "capacity_videos_per_min": sustained_result.get("throughput_videos_per_min", 0),
                    "stable": sustained_result.get("stable", False)
                }
                
                capacity_results.append(combined_result)
                
                # Pausa entre configuraciones
                time.sleep(5)
        
        return {
            "analysis_type": "worker_capacity",
            "timestamp": datetime.now().isoformat(),
            "results": capacity_results,
            "summary": self._generate_capacity_summary(capacity_results)
        }
    
    def _generate_capacity_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generar resumen de capacidad"""
        summary = {
            "max_throughput": 0,
            "best_configuration": None,
            "bottlenecks": [],
            "recommendations": []
        }
        
        for result in results:
            throughput = result["capacity_videos_per_min"]
            if throughput > summary["max_throughput"]:
                summary["max_throughput"] = throughput
                summary["best_configuration"] = {
                    "video_size_mb": result["video_size_mb"],
                    "workers": result["workers"],
                    "throughput": throughput
                }
        
        # Identificar bottlenecks
        for result in results:
            if not result["stable"]:
                summary["bottlenecks"].append({
                    "config": f"{result['video_size_mb']}MB, {result['workers']} workers",
                    "issue": "Unstable performance"
                })
        
        return summary

def main():
    """Función principal para ejecutar pruebas"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Worker Capacity Testing - Plan B")
    parser.add_argument("--test-type", choices=["saturation", "sustained", "full"], default="full",
                       help="Tipo de prueba a ejecutar")
    parser.add_argument("--video-size", type=int, default=50, help="Tamaño del video en MB")
    parser.add_argument("--workers", type=int, default=4, help="Número de workers")
    parser.add_argument("--duration", type=int, default=5, help="Duración en minutos")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="URL de Redis")
    
    args = parser.parse_args()
    
    # Crear tester
    tester = WorkerCapacityTester(args.redis_url)
    
    if args.test_type == "saturation":
        result = tester.run_saturation_test(args.video_size, args.workers)
    elif args.test_type == "sustained":
        result = tester.run_sustained_test(args.video_size, args.workers, args.duration)
    else:  # full
        result = tester.run_capacity_analysis()
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capacity-planning/worker_capacity_results_{timestamp}.json"
    
    import json
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Resultados guardados en: {filename}")
    print(f"\n{'='*50}")
    print("RESULTADOS DE CAPACIDAD DEL WORKER")
    print(f"{'='*50}")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
