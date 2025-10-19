#!/usr/bin/env python3
"""
Worker Saturation Testing - Plan B
Pruebas de saturación del worker para identificar puntos de saturación
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

class WorkerSaturationTester:
    """Tester de saturación del worker"""
    
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
    
    def run_saturation_ramp_test(self, video_size_mb: int, max_workers: int = 4) -> Dict[str, Any]:
        """Ejecutar prueba de saturación con rampa progresiva"""
        logger.info(f"Iniciando prueba de saturación: {video_size_mb}MB, {max_workers} workers")
        
        # Limpiar cola
        self.redis_client.delete("video_processing_queue")
        
        # Configuración de rampa
        ramp_steps = [1, 2, 5, 10, 20, 50, 100, 200, 500]
        saturation_results = []
        
        for step, batch_size in enumerate(ramp_steps):
            logger.info(f"Paso {step + 1}/{len(ramp_steps)}: Probando con {batch_size} trabajos")
            
            # Inyectar trabajos
            start_time = time.time()
            job_ids = self.inject_jobs_batch(batch_size, video_size_mb)
            injection_time = time.time() - start_time
            
            # Monitorear procesamiento
            initial_queue_size = self.redis_client.llen("video_processing_queue")
            processing_start = time.time()
            
            # Métricas durante procesamiento
            metrics_history = []
            max_cpu = 0
            max_memory = 0
            saturated = False
            
            # Monitorear por hasta 5 minutos
            monitoring_duration = 300  # 5 minutos
            check_interval = 5  # cada 5 segundos
            
            for check in range(0, monitoring_duration, check_interval):
                current_time = time.time()
                elapsed = current_time - processing_start
                
                if elapsed >= monitoring_duration:
                    break
                
                # Obtener métricas
                metrics = self.monitor_system_metrics()
                queue_size = self.redis_client.llen("video_processing_queue")
                
                # Registrar métricas
                metrics_history.append({
                    "timestamp": current_time,
                    "elapsed_seconds": elapsed,
                    "queue_size": queue_size,
                    "cpu_usage": metrics["cpu_usage"],
                    "memory_usage": metrics["memory_usage"],
                    "disk_usage": metrics["disk_usage"]
                })
                
                # Actualizar máximos
                max_cpu = max(max_cpu, metrics["cpu_usage"])
                max_memory = max(max_memory, metrics["memory_usage"])
                
                # Detectar saturación
                if metrics["cpu_usage"] > 90 or metrics["memory_usage"] > 90:
                    saturated = True
                    logger.warning(f"Saturación detectada: CPU={metrics['cpu_usage']:.1f}%, Memory={metrics['memory_usage']:.1f}%")
                    break
                
                # Si la cola se vació, continuar monitoreando por un poco más
                if queue_size == 0 and elapsed > 30:  # 30 segundos después de vaciar
                    break
                
                time.sleep(check_interval)
            
            processing_end = time.time()
            total_processing_time = processing_end - processing_start
            final_queue_size = self.redis_client.llen("video_processing_queue")
            
            # Calcular métricas
            videos_processed = initial_queue_size - final_queue_size
            throughput = videos_processed / (total_processing_time / 60) if total_processing_time > 0 else 0
            
            # Determinar si está saturado
            is_saturated = saturated or max_cpu > 90 or max_memory > 90
            
            result = {
                "step": step + 1,
                "batch_size": batch_size,
                "video_size_mb": video_size_mb,
                "workers": max_workers,
                "injection_time_seconds": injection_time,
                "processing_time_seconds": total_processing_time,
                "videos_processed": videos_processed,
                "videos_remaining": final_queue_size,
                "throughput_videos_per_min": throughput,
                "max_cpu_usage": max_cpu,
                "max_memory_usage": max_memory,
                "saturated": is_saturated,
                "metrics_history": metrics_history[-10:]  # Últimas 10 mediciones
            }
            
            saturation_results.append(result)
            
            # Si está saturado, parar
            if is_saturated:
                logger.info(f"Saturación alcanzada en paso {step + 1} con {batch_size} trabajos")
                break
            
            # Limpiar cola para siguiente paso
            self.redis_client.delete("video_processing_queue")
            time.sleep(10)  # Pausa entre pasos
        
        # Encontrar punto de saturación
        max_sustainable_batch = 0
        max_throughput = 0
        
        for result in saturation_results:
            if not result["saturated"]:
                max_sustainable_batch = max(max_sustainable_batch, result["batch_size"])
                max_throughput = max(max_throughput, result["throughput_videos_per_min"])
        
        return {
            "test_type": "saturation_ramp",
            "video_size_mb": video_size_mb,
            "workers": max_workers,
            "max_sustainable_batch": max_sustainable_batch,
            "max_throughput_videos_per_min": max_throughput,
            "saturation_point": max_sustainable_batch,
            "results": saturation_results,
            "bottlenecks": self._identify_bottlenecks(saturation_results)
        }
    
    def _identify_bottlenecks(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identificar cuellos de botella"""
        bottlenecks = []
        
        for result in results:
            if result["saturated"]:
                bottleneck = {
                    "batch_size": result["batch_size"],
                    "cpu_usage": result["max_cpu_usage"],
                    "memory_usage": result["max_memory_usage"],
                    "bottleneck_type": "CPU" if result["max_cpu_usage"] > 90 else "Memory"
                }
                bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def run_throughput_analysis(self, video_sizes: List[int], worker_configs: List[int]) -> Dict[str, Any]:
        """Ejecutar análisis de throughput para diferentes configuraciones"""
        logger.info("Iniciando análisis de throughput")
        
        throughput_results = []
        
        for video_size in video_sizes:
            for workers in worker_configs:
                logger.info(f"Analizando: {video_size}MB, {workers} workers")
                
                # Ejecutar prueba de saturación
                saturation_result = self.run_saturation_ramp_test(video_size, workers)
                
                # Extraer métricas clave
                throughput_result = {
                    "video_size_mb": video_size,
                    "workers": workers,
                    "max_sustainable_batch": saturation_result["max_sustainable_batch"],
                    "max_throughput_videos_per_min": saturation_result["max_throughput_videos_per_min"],
                    "saturation_point": saturation_result["saturation_point"],
                    "bottlenecks": saturation_result["bottlenecks"],
                    "efficiency": saturation_result["max_throughput_videos_per_min"] / workers if workers > 0 else 0
                }
                
                throughput_results.append(throughput_result)
                
                # Pausa entre configuraciones
                time.sleep(5)
        
        return {
            "analysis_type": "throughput_analysis",
            "timestamp": datetime.now().isoformat(),
            "results": throughput_results,
            "summary": self._generate_throughput_summary(throughput_results)
        }
    
    def _generate_throughput_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generar resumen de throughput"""
        summary = {
            "max_throughput": 0,
            "best_configuration": None,
            "efficiency_ranking": [],
            "bottleneck_analysis": {}
        }
        
        # Encontrar mejor configuración
        for result in results:
            if result["max_throughput_videos_per_min"] > summary["max_throughput"]:
                summary["max_throughput"] = result["max_throughput_videos_per_min"]
                summary["best_configuration"] = {
                    "video_size_mb": result["video_size_mb"],
                    "workers": result["workers"],
                    "throughput": result["max_throughput_videos_per_min"],
                    "efficiency": result["efficiency"]
                }
        
        # Ranking de eficiencia
        efficiency_ranking = sorted(results, key=lambda x: x["efficiency"], reverse=True)
        summary["efficiency_ranking"] = [
            {
                "config": f"{r['video_size_mb']}MB, {r['workers']} workers",
                "efficiency": r["efficiency"],
                "throughput": r["max_throughput_videos_per_min"]
            }
            for r in efficiency_ranking[:5]  # Top 5
        ]
        
        # Análisis de bottlenecks
        bottleneck_types = {}
        for result in results:
            for bottleneck in result["bottlenecks"]:
                bottleneck_type = bottleneck["bottleneck_type"]
                if bottleneck_type not in bottleneck_types:
                    bottleneck_types[bottleneck_type] = 0
                bottleneck_types[bottleneck_type] += 1
        
        summary["bottleneck_analysis"] = bottleneck_types
        
        return summary

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Worker Saturation Testing")
    parser.add_argument("--test-type", choices=["saturation", "throughput"], default="saturation",
                       help="Tipo de prueba")
    parser.add_argument("--video-size", type=int, default=50, help="Tamaño del video en MB")
    parser.add_argument("--workers", type=int, default=4, help="Número de workers")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="URL de Redis")
    
    args = parser.parse_args()
    
    tester = WorkerSaturationTester(args.redis_url)
    
    if args.test_type == "saturation":
        result = tester.run_saturation_ramp_test(args.video_size, args.workers)
    else:  # throughput
        result = tester.run_throughput_analysis([50, 100], [1, 2, 4])
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capacity-planning/worker_saturation_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Resultados guardados en: {filename}")
    
    # Mostrar resumen
    print(f"\n{'='*60}")
    print("RESULTADOS DE SATURACIÓN DEL WORKER")
    print(f"{'='*60}")
    
    if args.test_type == "saturation":
        print(f"Video Size: {result['video_size_mb']}MB")
        print(f"Workers: {result['workers']}")
        print(f"Max Sustainable Batch: {result['max_sustainable_batch']}")
        print(f"Max Throughput: {result['max_throughput_videos_per_min']:.2f} videos/min")
        print(f"Saturation Point: {result['saturation_point']}")
        
        if result['bottlenecks']:
            print(f"\nBottlenecks detectados:")
            for bottleneck in result['bottlenecks']:
                print(f"  - {bottleneck['bottleneck_type']}: {bottleneck['cpu_usage']:.1f}% CPU, {bottleneck['memory_usage']:.1f}% Memory")
    else:
        print(f"Best Configuration: {result['summary']['best_configuration']}")
        print(f"Max Throughput: {result['summary']['max_throughput']:.2f} videos/min")
        print(f"Bottleneck Analysis: {result['summary']['bottleneck_analysis']}")

if __name__ == "__main__":
    main()
