#!/usr/bin/env python3
"""
Script de pruebas de capacidad para el Worker de procesamiento de videos
Implementa el Plan B del análisis de capacidad
"""

import asyncio
import redis
import json
import time
import os
import psutil
import threading
from datetime import datetime
from typing import List, Dict, Any
import statistics
import argparse
import uuid

class WorkerCapacityTester:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_client = redis.from_url(redis_url)
        self.results = []
        self.monitoring = True
        self.metrics = []
        
    def start_monitoring(self):
        """Iniciar monitoreo de recursos del sistema"""
        def monitor():
            while self.monitoring:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                self.metrics.append({
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "disk_free_gb": disk.free / (1024**3)
                })
                time.sleep(1)
        
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.monitoring = False
    
    def create_test_video_file(self, size_mb: int, filename: str) -> str:
        """Crear archivo de video de prueba"""
        size_bytes = size_mb * 1024 * 1024
        test_content = b"fake video content" * (size_bytes // 17)  # Aproximadamente el tamaño deseado
        
        os.makedirs("test_videos", exist_ok=True)
        filepath = f"test_videos/{filename}"
        
        with open(filepath, 'wb') as f:
            f.write(test_content)
        
        return filepath
    
    def inject_video_task(self, video_path: str, video_id: str = None) -> str:
        """Inyectar tarea de procesamiento directamente en la cola"""
        if not video_id:
            video_id = str(uuid.uuid4())
        
        task_data = {
            "video_id": video_id,
            "video_path": video_path,
            "original_filename": os.path.basename(video_path),
            "owner_id": 1,  # ID de usuario de prueba
            "created_at": datetime.now().isoformat()
        }
        
        # Enviar a la cola de Redis
        self.redis_client.lpush("video_queue", json.dumps(task_data))
        return video_id
    
    def get_queue_length(self) -> int:
        """Obtener longitud actual de la cola"""
        return self.redis_client.llen("video_queue")
    
    def clear_queue(self):
        """Limpiar la cola de tareas"""
        self.redis_client.delete("video_queue")
    
    def wait_for_queue_empty(self, timeout: int = 300) -> bool:
        """Esperar a que la cola se vacíe"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.get_queue_length() == 0:
                return True
            time.sleep(1)
        return False
    
    async def saturation_test(self, video_size_mb: int, concurrency: int, max_tasks: int):
        """Prueba de saturación: subir progresivamente la cantidad de tareas"""
        print(f"🔥 Ejecutando Saturation Test - {video_size_mb}MB, {concurrency} workers, hasta {max_tasks} tareas")
        
        self.clear_queue()
        self.start_monitoring()
        
        # Crear archivo de video de prueba
        video_filename = f"test_video_{video_size_mb}mb.mp4"
        video_path = self.create_test_video_file(video_size_mb, video_filename)
        
        start_time = time.time()
        task_ids = []
        
        # Inyectar tareas progresivamente
        for i in range(max_tasks):
            task_id = self.inject_video_task(video_path, f"task_{i}")
            task_ids.append(task_id)
            
            # Esperar un poco entre inyecciones
            await asyncio.sleep(0.1)
            
            # Monitorear el estado de la cola
            queue_length = self.get_queue_length()
            print(f"   📊 Tarea {i+1}/{max_tasks} inyectada. Cola: {queue_length} tareas")
            
            # Si la cola se está saturando, registrar el punto de saturación
            if queue_length > 50:  # Umbral de saturación
                print(f"   ⚠️ Posible saturación detectada en tarea {i+1}")
        
        # Esperar a que se procesen todas las tareas
        print("   ⏳ Esperando procesamiento de tareas...")
        queue_empty = self.wait_for_queue_empty(timeout=600)  # 10 minutos timeout
        
        end_time = time.time()
        self.stop_monitoring()
        
        # Calcular métricas
        total_time = end_time - start_time
        throughput = max_tasks / (total_time / 60) if total_time > 0 else 0  # tareas por minuto
        
        # Analizar métricas del sistema
        avg_cpu = statistics.mean([m["cpu_percent"] for m in self.metrics]) if self.metrics else 0
        max_cpu = max([m["cpu_percent"] for m in self.metrics]) if self.metrics else 0
        avg_memory = statistics.mean([m["memory_percent"] for m in self.metrics]) if self.metrics else 0
        max_memory = max([m["memory_percent"] for m in self.metrics]) if self.metrics else 0
        
        result = {
            "test_type": "saturation",
            "video_size_mb": video_size_mb,
            "concurrency": concurrency,
            "max_tasks": max_tasks,
            "total_time_minutes": total_time / 60,
            "throughput_tasks_per_minute": throughput,
            "queue_emptied": queue_empty,
            "avg_cpu_percent": avg_cpu,
            "max_cpu_percent": max_cpu,
            "avg_memory_percent": avg_memory,
            "max_memory_percent": max_memory,
            "final_queue_length": self.get_queue_length()
        }
        
        self.results.append(result)
        return result
    
    async def sustained_test(self, video_size_mb: int, concurrency: int, 
                           tasks_per_minute: int, duration_minutes: int):
        """Prueba sostenida: mantener un número fijo de tareas en la cola"""
        print(f"⏱️ Ejecutando Sustained Test - {video_size_mb}MB, {concurrency} workers, "
              f"{tasks_per_minute} tareas/min durante {duration_minutes} minutos")
        
        self.clear_queue()
        self.start_monitoring()
        
        # Crear archivo de video de prueba
        video_filename = f"test_video_{video_size_mb}mb.mp4"
        video_path = self.create_test_video_file(video_size_mb, video_filename)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        task_count = 0
        injection_interval = 60 / tasks_per_minute  # Segundos entre inyecciones
        
        while time.time() < end_time:
            # Inyectar nueva tarea
            task_id = self.inject_video_task(video_path, f"sustained_task_{task_count}")
            task_count += 1
            
            # Monitorear estado
            queue_length = self.get_queue_length()
            print(f"   📊 Tarea {task_count} inyectada. Cola: {queue_length} tareas")
            
            # Esperar antes de la siguiente inyección
            await asyncio.sleep(injection_interval)
        
        # Esperar a que se procesen las tareas restantes
        print("   ⏳ Esperando procesamiento final...")
        final_wait = self.wait_for_queue_empty(timeout=300)
        
        self.stop_monitoring()
        
        # Calcular métricas
        total_time = end_time - start_time
        actual_throughput = task_count / (total_time / 60)
        
        # Analizar estabilidad de la cola
        queue_lengths = [self.get_queue_length() for _ in range(10)]  # Muestras
        queue_stability = statistics.stdev(queue_lengths) if len(queue_lengths) > 1 else 0
        
        result = {
            "test_type": "sustained",
            "video_size_mb": video_size_mb,
            "concurrency": concurrency,
            "target_tasks_per_minute": tasks_per_minute,
            "actual_tasks_per_minute": actual_throughput,
            "duration_minutes": duration_minutes,
            "total_tasks_injected": task_count,
            "queue_stability_std": queue_stability,
            "queue_stable": queue_stability < 5,  # Cola estable si std < 5
            "final_queue_length": self.get_queue_length()
        }
        
        self.results.append(result)
        return result
    
    def generate_report(self) -> Dict[str, Any]:
        """Generar reporte de capacidad del worker"""
        if not self.results:
            return {"error": "No test results available"}
        
        # Agrupar resultados por tipo de prueba
        saturation_results = [r for r in self.results if r["test_type"] == "saturation"]
        sustained_results = [r for r in self.results if r["test_type"] == "sustained"]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "saturation_tests": saturation_results,
            "sustained_tests": sustained_results,
            "summary": {
                "total_tests": len(self.results),
                "saturation_tests": len(saturation_results),
                "sustained_tests": len(sustained_results)
            }
        }
        
        # Análisis de capacidad
        if saturation_results:
            max_throughput = max([r["throughput_tasks_per_minute"] for r in saturation_results])
            report["capacity_analysis"] = {
                "max_throughput_tasks_per_minute": max_throughput,
                "bottleneck_analysis": self._analyze_bottlenecks(saturation_results)
            }
        
        return report
    
    def _analyze_bottlenecks(self, results: List[Dict]) -> Dict[str, Any]:
        """Analizar cuellos de botella"""
        bottlenecks = {
            "cpu_saturation": any(r["max_cpu_percent"] > 90 for r in results),
            "memory_saturation": any(r["max_memory_percent"] > 90 for r in results),
            "queue_overflow": any(r["final_queue_length"] > 0 for r in results)
        }
        
        # Identificar el cuello de botella principal
        if bottlenecks["cpu_saturation"]:
            bottlenecks["primary_bottleneck"] = "CPU"
        elif bottlenecks["memory_saturation"]:
            bottlenecks["primary_bottleneck"] = "Memory"
        elif bottlenecks["queue_overflow"]:
            bottlenecks["primary_bottleneck"] = "Queue Processing"
        else:
            bottlenecks["primary_bottleneck"] = "None detected"
        
        return bottlenecks

async def main():
    parser = argparse.ArgumentParser(description='Worker Capacity Testing para ANB Rising Stars Showcase')
    parser.add_argument('--redis-url', default='redis://localhost:6379/0', help='URL de Redis')
    parser.add_argument('--test-type', choices=['saturation', 'sustained', 'all'], 
                       default='all', help='Tipo de prueba a ejecutar')
    parser.add_argument('--video-size', type=int, default=50, help='Tamaño del video en MB')
    parser.add_argument('--concurrency', type=int, default=2, help='Número de workers concurrentes')
    parser.add_argument('--max-tasks', type=int, default=20, help='Máximo número de tareas para saturation')
    parser.add_argument('--tasks-per-minute', type=int, default=10, help='Tareas por minuto para sustained')
    parser.add_argument('--duration', type=int, default=5, help='Duración en minutos para sustained')
    
    args = parser.parse_args()
    
    tester = WorkerCapacityTester(args.redis_url)
    
    try:
        if args.test_type in ['saturation', 'all']:
            result = await tester.saturation_test(args.video_size, args.concurrency, args.max_tasks)
            print(f"✅ Saturation Test completado: {result}")
        
        if args.test_type in ['sustained', 'all']:
            result = await tester.sustained_test(args.video_size, args.concurrency, 
                                               args.tasks_per_minute, args.duration)
            print(f"✅ Sustained Test completado: {result}")
        
        # Generar reporte
        report = tester.generate_report()
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capacity-planning/worker_results_{timestamp}.json"
        os.makedirs("capacity-planning", exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Resultados del worker guardados en: {filename}")
        
        # Resumen final
        print("\n" + "="*50)
        print("🔧 RESUMEN DE PRUEBAS DE CAPACIDAD DEL WORKER")
        print("="*50)
        
        if "capacity_analysis" in report:
            analysis = report["capacity_analysis"]
            print(f"\n📈 Capacidad máxima: {analysis['max_throughput_tasks_per_minute']:.2f} tareas/minuto")
            
            bottlenecks = analysis["bottleneck_analysis"]
            print(f"\n🔍 Análisis de cuellos de botella:")
            print(f"   • CPU saturado: {'✅' if bottlenecks['cpu_saturation'] else '❌'}")
            print(f"   • Memoria saturada: {'✅' if bottlenecks['memory_saturation'] else '❌'}")
            print(f"   • Cola desbordada: {'✅' if bottlenecks['queue_overflow'] else '❌'}")
            print(f"   • Cuello de botella principal: {bottlenecks['primary_bottleneck']}")
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
    finally:
        # Limpiar archivos de prueba
        import shutil
        if os.path.exists("test_videos"):
            shutil.rmtree("test_videos")

if __name__ == "__main__":
    asyncio.run(main())
