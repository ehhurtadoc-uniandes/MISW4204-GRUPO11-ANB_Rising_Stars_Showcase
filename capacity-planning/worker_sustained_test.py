#!/usr/bin/env python3
"""
Worker Sustained Testing - Plan B
Pruebas sostenidas del worker para medir estabilidad y throughput constante
"""

import asyncio
import json
import time
import uuid
import psutil
import redis
from datetime import datetime
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerSustainedTester:
    """Tester de pruebas sostenidas del worker"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        self.results = []
        
    def create_video_payload(self, video_size_mb: int, video_id: str = None) -> Dict[str, Any]:
        """Crear payload realista para video"""
        if not video_id:
            video_id = str(uuid.uuid4())
            
        return {
            "video_id": video_id,
            "original_path": f"/test_videos/{video_id}.mp4",
            "processed_path": f"/processed_videos/processed_{video_id}.mp4",
            "file_size_mb": video_size_mb,
            "duration_seconds": 30,
            "resolution": "1920x1080",
            "bitrate": "2000k",
            "format": "mp4",
            "created_at": datetime.now().isoformat(),
            "task_id": str(uuid.uuid4())
        }
    
    def inject_jobs_batch(self, batch_size: int, video_size_mb: int) -> List[str]:
        """Inyectar lote de trabajos en la cola"""
        job_ids = []
        
        for i in range(batch_size):
            job_id = str(uuid.uuid4())
            payload = self.create_video_payload(video_size_mb, job_id)
            
            # Enviar a la cola
            self.redis_client.lpush("video_processing_queue", json.dumps(payload))
            job_ids.append(job_id)
            
        return job_ids
    
    def monitor_system_metrics(self) -> Dict[str, float]:
        """Monitorear métricas del sistema"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_usage": disk.percent,
            "disk_free_gb": disk.free / (1024**3)
        }
    
    def run_sustained_test(self, video_size_mb: int, workers: int, duration_minutes: int = 5, 
                         queue_maintenance_size: int = 5) -> Dict[str, Any]:
        """Ejecutar prueba sostenida del worker"""
        logger.info(f"Iniciando prueba sostenida: {video_size_mb}MB, {workers} workers, {duration_minutes} min")
        
        # Limpiar cola
        self.redis_client.delete("video_processing_queue")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        # Métricas de monitoreo
        monitoring_interval = 30  # segundos
        last_monitoring_time = start_time
        
        sustained_results = []
        total_videos_injected = 0
        total_videos_processed = 0
        total_errors = 0
        
        # Métricas acumulativas
        cpu_samples = []
        memory_samples = []
        queue_size_samples = []
        
        logger.info(f"Monitoreando cada {monitoring_interval} segundos por {duration_minutes} minutos")
        
        while time.time() < end_time:
            current_time = time.time()
            elapsed_minutes = (current_time - start_time) / 60
            
            # Mantener cola con trabajos constantes
            current_queue_size = self.redis_client.llen("video_processing_queue")
            
            if current_queue_size < queue_maintenance_size:
                try:
                    # Inyectar trabajos para mantener la cola
                    jobs_to_inject = queue_maintenance_size - current_queue_size
                    job_ids = self.inject_jobs_batch(jobs_to_inject, video_size_mb)
                    total_videos_injected += jobs_to_inject
                    
                    logger.debug(f"Inyectados {jobs_to_inject} trabajos, cola: {current_queue_size + jobs_to_inject}")
                    
                except Exception as e:
                    logger.error(f"Error inyectando trabajos: {e}")
                    total_errors += 1
            
            # Monitorear métricas cada intervalo
            if current_time - last_monitoring_time >= monitoring_interval:
                system_metrics = self.monitor_system_metrics()
                current_queue_size = self.redis_client.llen("video_processing_queue")
                
                # Calcular videos procesados en este intervalo
                videos_processed_this_interval = total_videos_injected - current_queue_size
                total_videos_processed = max(total_videos_processed, videos_processed_this_interval)
                
                # Registrar métricas
                result = {
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_minutes": elapsed_minutes,
                    "queue_size": current_queue_size,
                    "videos_injected": total_videos_injected,
                    "videos_processed": total_videos_processed,
                    "errors": total_errors,
                    "cpu_usage": system_metrics["cpu_usage"],
                    "memory_usage": system_metrics["memory_usage"],
                    "disk_usage": system_metrics["disk_usage"],
                    "memory_available_gb": system_metrics["memory_available_gb"],
                    "disk_free_gb": system_metrics["disk_free_gb"]
                }
                
                sustained_results.append(result)
                
                # Acumular muestras para análisis
                cpu_samples.append(system_metrics["cpu_usage"])
                memory_samples.append(system_metrics["memory_usage"])
                queue_size_samples.append(current_queue_size)
                
                logger.info(f"Minuto {elapsed_minutes:.1f}: Cola={current_queue_size}, "
                          f"Videos={total_videos_processed}, CPU={system_metrics['cpu_usage']:.1f}%, "
                          f"Memory={system_metrics['memory_usage']:.1f}%")
                
                last_monitoring_time = current_time
            
            time.sleep(1)  # Pausa de 1 segundo
        
        # Calcular métricas finales
        total_time = time.time() - start_time
        final_throughput = total_videos_processed / (total_time / 60)
        
        # Análisis de estabilidad
        cpu_std = self._calculate_std(cpu_samples) if cpu_samples else 0
        memory_std = self._calculate_std(memory_samples) if memory_samples else 0
        queue_std = self._calculate_std(queue_size_samples) if queue_size_samples else 0
        
        # Determinar estabilidad
        is_stable = (
            total_errors < (total_videos_injected * 0.05) and  # Menos del 5% de errores
            cpu_std < 20 and  # CPU estable (desviación < 20%)
            memory_std < 15 and  # Memory estable (desviación < 15%)
            queue_std < 5  # Cola estable (desviación < 5)
        )
        
        return {
            "test_type": "sustained",
            "video_size_mb": video_size_mb,
            "workers": workers,
            "duration_minutes": duration_minutes,
            "queue_maintenance_size": queue_maintenance_size,
            "total_videos_injected": total_videos_injected,
            "total_videos_processed": total_videos_processed,
            "total_errors": total_errors,
            "throughput_videos_per_min": final_throughput,
            "stability_analysis": {
                "is_stable": is_stable,
                "cpu_std": cpu_std,
                "memory_std": memory_std,
                "queue_std": queue_std,
                "error_rate": total_errors / total_videos_injected if total_videos_injected > 0 else 0
            },
            "results": sustained_results,
            "summary": self._generate_sustained_summary(sustained_results)
        }
    
    def _calculate_std(self, samples: List[float]) -> float:
        """Calcular desviación estándar"""
        if len(samples) < 2:
            return 0
        
        mean = sum(samples) / len(samples)
        variance = sum((x - mean) ** 2 for x in samples) / len(samples)
        return variance ** 0.5
    
    def _generate_sustained_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generar resumen de prueba sostenida"""
        if not results:
            return {"error": "No results to summarize"}
        
        # Extraer métricas
        cpu_values = [r["cpu_usage"] for r in results]
        memory_values = [r["memory_usage"] for r in results]
        queue_values = [r["queue_size"] for r in results]
        
        return {
            "avg_cpu_usage": sum(cpu_values) / len(cpu_values),
            "max_cpu_usage": max(cpu_values),
            "min_cpu_usage": min(cpu_values),
            "avg_memory_usage": sum(memory_values) / len(memory_values),
            "max_memory_usage": max(memory_values),
            "min_memory_usage": min(memory_values),
            "avg_queue_size": sum(queue_values) / len(queue_values),
            "max_queue_size": max(queue_values),
            "min_queue_size": min(queue_values),
            "total_samples": len(results)
        }
    
    def run_stability_analysis(self, video_sizes: List[int], worker_configs: List[int], 
                              duration_minutes: int = 5) -> Dict[str, Any]:
        """Ejecutar análisis de estabilidad para diferentes configuraciones"""
        logger.info("Iniciando análisis de estabilidad")
        
        stability_results = []
        
        for video_size in video_sizes:
            for workers in worker_configs:
                logger.info(f"Probando estabilidad: {video_size}MB, {workers} workers")
                
                # Ejecutar prueba sostenida
                sustained_result = self.run_sustained_test(video_size, workers, duration_minutes)
                
                # Extraer métricas de estabilidad
                stability_result = {
                    "video_size_mb": video_size,
                    "workers": workers,
                    "duration_minutes": duration_minutes,
                    "is_stable": sustained_result["stability_analysis"]["is_stable"],
                    "throughput_videos_per_min": sustained_result["throughput_videos_per_min"],
                    "error_rate": sustained_result["stability_analysis"]["error_rate"],
                    "cpu_stability": sustained_result["stability_analysis"]["cpu_std"],
                    "memory_stability": sustained_result["stability_analysis"]["memory_std"],
                    "queue_stability": sustained_result["stability_analysis"]["queue_std"],
                    "summary": sustained_result["summary"]
                }
                
                stability_results.append(stability_result)
                
                # Pausa entre configuraciones
                time.sleep(10)
        
        return {
            "analysis_type": "stability_analysis",
            "timestamp": datetime.now().isoformat(),
            "results": stability_results,
            "summary": self._generate_stability_summary(stability_results)
        }
    
    def _generate_stability_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generar resumen de análisis de estabilidad"""
        summary = {
            "stable_configurations": [],
            "unstable_configurations": [],
            "best_stable_config": None,
            "stability_metrics": {}
        }
        
        stable_configs = []
        unstable_configs = []
        
        for result in results:
            if result["is_stable"]:
                stable_configs.append(result)
            else:
                unstable_configs.append(result)
        
        summary["stable_configurations"] = [
            {
                "config": f"{r['video_size_mb']}MB, {r['workers']} workers",
                "throughput": r["throughput_videos_per_min"],
                "stability_score": self._calculate_stability_score(r)
            }
            for r in stable_configs
        ]
        
        summary["unstable_configurations"] = [
            {
                "config": f"{r['video_size_mb']}MB, {r['workers']} workers",
                "issues": self._identify_stability_issues(r)
            }
            for r in unstable_configs
        ]
        
        # Encontrar mejor configuración estable
        if stable_configs:
            best_stable = max(stable_configs, key=lambda x: x["throughput_videos_per_min"])
            summary["best_stable_config"] = {
                "video_size_mb": best_stable["video_size_mb"],
                "workers": best_stable["workers"],
                "throughput": best_stable["throughput_videos_per_min"],
                "stability_score": self._calculate_stability_score(best_stable)
            }
        
        # Métricas de estabilidad
        summary["stability_metrics"] = {
            "total_configurations": len(results),
            "stable_count": len(stable_configs),
            "unstable_count": len(unstable_configs),
            "stability_rate": len(stable_configs) / len(results) if results else 0
        }
        
        return summary
    
    def _calculate_stability_score(self, result: Dict[str, Any]) -> float:
        """Calcular score de estabilidad (0-100)"""
        # Score basado en estabilidad de métricas
        cpu_score = max(0, 100 - result["cpu_stability"])
        memory_score = max(0, 100 - result["memory_stability"])
        queue_score = max(0, 100 - result["queue_stability"])
        error_score = max(0, 100 - (result["error_rate"] * 100))
        
        # Promedio ponderado
        return (cpu_score + memory_score + queue_score + error_score) / 4
    
    def _identify_stability_issues(self, result: Dict[str, Any]) -> List[str]:
        """Identificar problemas de estabilidad"""
        issues = []
        
        if result["cpu_stability"] > 20:
            issues.append("CPU instability")
        if result["memory_stability"] > 15:
            issues.append("Memory instability")
        if result["queue_stability"] > 5:
            issues.append("Queue instability")
        if result["error_rate"] > 0.05:
            issues.append("High error rate")
        
        return issues

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Worker Sustained Testing")
    parser.add_argument("--test-type", choices=["sustained", "stability"], default="sustained",
                       help="Tipo de prueba")
    parser.add_argument("--video-size", type=int, default=50, help="Tamaño del video en MB")
    parser.add_argument("--workers", type=int, default=4, help="Número de workers")
    parser.add_argument("--duration", type=int, default=5, help="Duración en minutos")
    parser.add_argument("--queue-size", type=int, default=5, help="Tamaño de cola a mantener")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="URL de Redis")
    
    args = parser.parse_args()
    
    tester = WorkerSustainedTester(args.redis_url)
    
    if args.test_type == "sustained":
        result = tester.run_sustained_test(args.video_size, args.workers, args.duration, args.queue_size)
    else:  # stability
        result = tester.run_stability_analysis([50, 100], [1, 2, 4], args.duration)
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capacity-planning/worker_sustained_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Resultados guardados en: {filename}")
    
    # Mostrar resumen
    print(f"\n{'='*60}")
    print("RESULTADOS DE PRUEBAS SOSTENIDAS DEL WORKER")
    print(f"{'='*60}")
    
    if args.test_type == "sustained":
        print(f"Video Size: {result['video_size_mb']}MB")
        print(f"Workers: {result['workers']}")
        print(f"Duration: {result['duration_minutes']} minutes")
        print(f"Throughput: {result['throughput_videos_per_min']:.2f} videos/min")
        print(f"Stable: {result['stability_analysis']['is_stable']}")
        print(f"Error Rate: {result['stability_analysis']['error_rate']:.2%}")
    else:
        print(f"Stable Configurations: {len(result['summary']['stable_configurations'])}")
        print(f"Unstable Configurations: {len(result['summary']['unstable_configurations'])}")
        print(f"Stability Rate: {result['summary']['stability_metrics']['stability_rate']:.2%}")
        
        if result['summary']['best_stable_config']:
            best = result['summary']['best_stable_config']
            print(f"Best Stable Config: {best['video_size_mb']}MB, {best['workers']} workers")
            print(f"Best Throughput: {best['throughput']:.2f} videos/min")

if __name__ == "__main__":
    main()
